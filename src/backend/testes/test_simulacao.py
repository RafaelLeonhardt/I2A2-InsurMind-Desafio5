"""Testes do caso de uso da simulação local (SIMUL-04..10).

Os repositórios de mensagem, avaliação crítica, execução, elegibilidade, entrega simulada e
idempotência são os reais, sobre um banco temporário migrado: a atomicidade da transação
única, a concorrência otimista e a `UNIQUE (mensagem_id)` da migração `0014` são garantias do
próprio DuckDB — testá-las com dublê provaria pouco. É a mesma escolha de 3.5.
"""

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.adaptadores.persistencia.repositorio_avaliacoes_criticas import (
    RepositorioAvaliacoesCriticas,
)
from central_preventiva.adaptadores.persistencia.repositorio_contextos_agente import (
    RepositorioContextosAgente,
)
from central_preventiva.adaptadores.persistencia.repositorio_elegibilidade import (
    RepositorioElegibilidades,
)
from central_preventiva.adaptadores.persistencia.repositorio_entregas_simuladas import (
    ROTULO_SIMULADA,
    RepositorioEntregasSimuladas,
)
from central_preventiva.adaptadores.persistencia.repositorio_execucao_preventiva import (
    ConflitoVersao,
    RepositorioExcecoesOperacionais,
    RepositorioExecucaoPreventiva,
)
from central_preventiva.adaptadores.persistencia.repositorio_idempotencia import (
    RepositorioIdempotencia,
)
from central_preventiva.adaptadores.persistencia.repositorio_mensagens import (
    RepositorioMensagens,
)
from central_preventiva.adaptadores.persistencia.repositorio_meteorologia import (
    RepositorioEventosMeteorologicos,
)
from central_preventiva.adaptadores.persistencia.serializacao_criterios import (
    serializar_criterios,
)
from central_preventiva.adaptadores.persistencia.transacao import TransacaoDuckDB
from central_preventiva.aplicacao.portas_persistencia import ConflitoIdempotencia
from central_preventiva.aplicacao.simulacao import (
    IMPACTO_FALHA_SIMULACAO,
    MARCO_FALHOU_SIMULACAO,
    MARCO_SIMULACAO_CONCLUIDA,
    PREFIXO_CAUSA_FALHA_LOCAL,
    TENTATIVAS_FALHA_LOCAL,
    EstadoNaoConfirmavel,
    ExecucaoInexistente,
    FalhaLocalSimulacao,
    NenhumaMensagemAprovada,
    OrigemNaoRetentavel,
    PortasSimulacao,
    ReconhecimentoObrigatorio,
    ResultadoSimulacao,
    ServicoSimulacao,
    SnapshotInvalido,
)
from central_preventiva.dominio.avaliacao_critica import CategoriaCritica, MotivoCritica
from central_preventiva.dominio.avaliador_elegibilidade import (
    OPERANDO_AREA_AFETADA,
    OPERANDO_COBERTURA_EXIGIDA,
)
from central_preventiva.dominio.avaliador_risco import Criterio
from central_preventiva.dominio.estados_execucao import EstadoExecucao
from central_preventiva.dominio.estados_mensagem import EstadoMensagem
from central_preventiva.dominio.evento_meteorologico import (
    EventoMeteorologico,
    ProvenienciaEvento,
    TipoEventoMeteorologico,
)
from central_preventiva.dominio.montador_contexto_agente import ContextoAgente
from central_preventiva.dominio.validador_saida_canal import Canal, SaidaCanal

EXECUCAO_ID = UUID("11111111-1111-1111-1111-111111111111")
EVENTO_ID = UUID("22222222-2222-2222-2222-222222222222")
REGRA_ID = UUID("33333333-3333-3333-3333-333333333333")
REGRA_VERSAO = 2
MODELO = "gpt-4o-mini"
VERSAO_PROMPT = "v1"
CHAVE = "chave-idempotente-1"
HASH = "hash-1"

EVENTO = EventoMeteorologico(
    id=EVENTO_ID,
    tipo=TipoEventoMeteorologico.CHUVA_INTENSA,
    area="9990001",
    periodo_inicio=datetime(2026, 9, 4, 12, 0, tzinfo=UTC),
    periodo_fim=datetime(2026, 9, 4, 18, 0, tzinfo=UTC),
    intensidade=62.5,
    proveniencia=ProvenienciaEvento.REAL_INMET,
    instante_observado=datetime(2026, 9, 4, 18, 0, tzinfo=UTC),
)

CRITERIOS = (
    Criterio(OPERANDO_AREA_AFETADA, "9990001", True, "Área corresponde."),
    Criterio(OPERANDO_COBERTURA_EXIGIDA, "alagamento", True, "Possui cobertura."),
)

MOTIVO_TOM = MotivoCritica(CategoriaCritica.TOM, "O texto usa tom alarmista.")

CONTEXTO = ContextoAgente(
    evento="chuva_intensa",
    localizacao_aproximada="9990001",
    coberturas_relevantes=("alagamento",),
    canal="sms",
    orientacoes_seguranca=("Evite áreas alagadas.",),
)


class Cenario:
    """Reúne o caso de uso real, os repositórios reais e o banco temporário migrado."""

    def __init__(
        self,
        tmp_path: Path,
        estado: EstadoExecucao = EstadoExecucao.AGUARDANDO_CONFIRMACAO,
    ) -> None:
        """Migra o banco do teste e compõe o serviço sobre os repositórios reais."""

        self.caminho = tmp_path / "central_preventiva.duckdb"
        ExecutorMigracoes(self.caminho).aplicar_pendentes()
        self.mensagens = RepositorioMensagens(self.caminho)
        self.avaliacoes = RepositorioAvaliacoesCriticas(self.caminho)
        self.execucoes = RepositorioExecucaoPreventiva(self.caminho)
        self.entregas = RepositorioEntregasSimuladas(self.caminho)
        self.excecoes = RepositorioExcecoesOperacionais(self.caminho)
        self.elegibilidades = RepositorioElegibilidades(self.caminho)
        self.contextos = RepositorioContextosAgente(self.caminho)
        self.eventos = RepositorioEventosMeteorologicos(self.caminho)
        self.idempotencia = RepositorioIdempotencia(self.caminho)
        self.eventos.salvar(EVENTO)
        with abrir_conexao(self.caminho) as conexao:
            self._inserir_regra(conexao, REGRA_ID, REGRA_VERSAO)
            conexao.execute(
                "INSERT INTO execucao_preventiva (id, estado, versao) VALUES (?, ?, 1)",
                [EXECUCAO_ID, estado.value],
            )
        self.servico = ServicoSimulacao(
            PortasSimulacao(
                execucoes=self.execucoes,
                mensagens=self.mensagens,
                avaliacoes=self.avaliacoes,
                entregas=self.entregas,
                excecoes=self.excecoes,
                elegibilidades=self.elegibilidades,
                eventos=self.eventos,
                idempotencia=self.idempotencia,
                transacao=TransacaoDuckDB(self.caminho),
            )
        )

    @staticmethod
    def _inserir_regra(conexao: object, regra_id: UUID, versao: int) -> None:
        """Insere a regra versionada que o snapshot de elegibilidade referencia (2.4/2.5)."""

        conexao.execute(  # pyright: ignore[reportAttributeAccessIssue]
            "INSERT INTO regras (id, evento_tipo, limiar_meteorologico, area_aplicavel, "
            "apolice_tipo, cobertura_exigida, antecedencia_horas, canal, versao, estado) "
            "VALUES (?, 'chuva_intensa', 50.0, '9990001', 'residencial', 'alagamento', 6, "
            "'sms', ?, 'ativa')",
            [regra_id, versao],
        )

    def regra(self, versao: int) -> UUID:
        """Insere uma regra versionada extra e devolve o identificador dela."""

        regra_id = uuid4()
        with abrir_conexao(self.caminho) as conexao:
            self._inserir_regra(conexao, regra_id, versao)
        return regra_id

    def elegibilidade(
        self,
        execucao_id: UUID = EXECUCAO_ID,
        canal: str = "sms",
        nome: str = "Pessoa Teste",
        elegivel: bool = True,
        regra_id: UUID = REGRA_ID,
    ) -> UUID:
        """Insere um item do público elegível, no formato que 2.5 grava."""

        id_registro = uuid4()
        with abrir_conexao(self.caminho) as conexao:
            conexao.execute(
                "INSERT INTO elegibilidades_historicas "
                "(id, execucao_id, evento_id, regra_id, segurado_id, "
                "apolice_id, elegivel, criterios, canal, nome_segurado, justificativa) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, "
                "'Atende integralmente aos critérios da regra ativa.')",
                [
                    id_registro,
                    execucao_id,
                    EVENTO_ID,
                    regra_id,
                    uuid4(),
                    uuid4(),
                    elegivel,
                    serializar_criterios(CRITERIOS),
                    canal,
                    nome,
                ],
            )
        return id_registro

    def semear_mensagem(
        self,
        canal: Canal = Canal.SMS,
        estado: EstadoMensagem = EstadoMensagem.APROVADA,
        aprovada_pelo_critico: bool = True,
        corpo: str = "Chuva forte hoje na sua região. Evite áreas alagadas.",
        assunto: str | None = None,
        nome: str = "Pessoa Teste",
    ) -> UUID:
        """Semeia uma mensagem com uma tentativa avaliada e o estado final indicado."""

        elegibilidade_id = self.elegibilidade(canal=canal.value, nome=nome)
        mensagem_id = self.mensagens.criar(EXECUCAO_ID, elegibilidade_id, canal)
        versao_id = self.mensagens.salvar_versao(
            mensagem_id=mensagem_id,
            numero_tentativa=1,
            conteudo=SaidaCanal(corpo=corpo, assunto=assunto),
            duracao_ms=742.5,
            modelo=MODELO,
            versao_prompt=VERSAO_PROMPT,
            tokens_entrada=210,
            tokens_saida=64,
            valida=True,
            motivo_invalidez=None,
        )
        self.avaliacoes.salvar(
            versao_mensagem_id=versao_id,
            aprovada=aprovada_pelo_critico,
            motivos=() if aprovada_pelo_critico else (MOTIVO_TOM,),
            modelo=MODELO,
            duracao_ms=90.0,
        )
        atual = self.mensagens.obter(mensagem_id)
        assert atual is not None
        if atual.estado is not estado:
            self.mensagens.transicionar(mensagem_id, atual.versao, estado)
        return mensagem_id

    def confirmar(
        self,
        versao_esperada: int = 1,
        reconhecimento: bool = True,
        chave: str = CHAVE,
        hash_requisicao: str = HASH,
        injecao_falha_teste: object = None,
        execucao_id: UUID = EXECUCAO_ID,
    ) -> ResultadoSimulacao:
        """Confirma a simulação pelo caso de uso real, como o roteador faria."""

        return self.servico.confirmar(
            execucao_id,
            versao_esperada,
            reconhecimento,
            chave,
            hash_requisicao,
            injecao_falha_teste,  # pyright: ignore[reportArgumentType]
        )

    def estado_execucao(self, execucao_id: UUID = EXECUCAO_ID) -> EstadoExecucao:
        """Lê o estado agregado real persistido da execução."""

        snapshot = self.execucoes.buscar(execucao_id)
        assert snapshot is not None
        return snapshot.estado

    def estado_de(self, mensagem_id: UUID) -> EstadoMensagem:
        """Lê o estado de conteúdo atual da mensagem."""

        registro = self.mensagens.obter(mensagem_id)
        assert registro is not None
        return registro.estado

    def versao_de(self, mensagem_id: UUID) -> int:
        """Lê a versão de concorrência otimista atual da mensagem."""

        registro = self.mensagens.obter(mensagem_id)
        assert registro is not None
        return registro.versao

    def excecoes_registradas(self) -> list[tuple[str, int, str]]:
        """Lê as exceções operacionais persistidas da execução (causa, tentativas, impacto)."""

        with abrir_conexao(self.caminho) as conexao:
            linhas = conexao.execute(
                "SELECT causa, tentativas, impacto, mensagem_id FROM excecoes_operacionais "
                "WHERE execucao_id = ?",
                [EXECUCAO_ID],
            ).fetchall()
        for _, _, _, mensagem_id in linhas:
            assert mensagem_id is None, "a falha da simulação é da execução, não de um item"
        return [
            (str(causa), int(tentativas), str(impacto))
            for causa, tentativas, impacto, _ in linhas
        ]

    def marcos(self) -> list[tuple[str, str | None]]:
        """Lê os marcos persistidos da execução, em ordem cronológica."""

        return [
            (marco.marco, marco.causa) for marco in self.execucoes.listar_marcos(EXECUCAO_ID)
        ]


def falha_local() -> None:
    """Ponto de injeção do teste: força uma falha local dentro da transação 1."""

    raise RuntimeError("falha local sintética durante a simulação")


# --- Reclamação atômica e criação das entregas (SIMUL-04, SIMUL-05, SIMUL-06) -------------


def test_confirmacao_cria_uma_entrega_por_mensagem_aprovada_e_conclui_a_execucao(
    tmp_path: Path,
) -> None:
    """SIMUL-05: uma entrega simulada por mensagem e canal, mensagens em `simulada_entregue`
    só após a transação, e a execução concluída."""

    cenario = Cenario(tmp_path)
    sms = cenario.semear_mensagem(Canal.SMS, corpo="Chuva forte hoje. Evite alagamentos.")
    email = cenario.semear_mensagem(
        Canal.EMAIL,
        corpo="Prezada, previsão de chuva intensa na sua região.",
        assunto="Aviso preventivo",
        nome="Outra Pessoa",
    )

    resultado = cenario.confirmar()

    entregas = cenario.entregas.listar_por_execucao(EXECUCAO_ID)
    por_mensagem = {entrega.mensagem_id: entrega for entrega in entregas}
    assert resultado.estado is EstadoExecucao.CONCLUIDA
    assert set(resultado.mensagens_simuladas) == {sms, email}
    assert len(resultado.entregas_criadas) == 2
    assert set(por_mensagem) == {sms, email}
    assert por_mensagem[sms].canal is Canal.SMS
    assert por_mensagem[sms].apresentacao.corpo == "Chuva forte hoje. Evite alagamentos."
    assert por_mensagem[sms].apresentacao.assunto is None
    assert por_mensagem[email].canal is Canal.EMAIL
    assert por_mensagem[email].apresentacao.assunto == "Aviso preventivo"
    assert por_mensagem[email].apresentacao.rotulo == ROTULO_SIMULADA
    assert cenario.estado_de(sms) is EstadoMensagem.SIMULADA_ENTREGUE
    assert cenario.estado_de(email) is EstadoMensagem.SIMULADA_ENTREGUE
    assert cenario.estado_execucao() is EstadoExecucao.CONCLUIDA
    assert (MARCO_SIMULACAO_CONCLUIDA, None) in cenario.marcos()


def test_rejeitada_excluida_e_em_excecao_nao_integram_a_simulacao(tmp_path: Path) -> None:
    """SIMUL-04, Independent Test da P1: com 3 aprovadas, 1 rejeitada, 1 excluída e 1 em
    exceção, exatamente 3 entregas são criadas e as demais nem aparecem."""

    cenario = Cenario(tmp_path)
    aprovadas = [
        cenario.semear_mensagem(Canal.SMS, nome="Aprovada 1"),
        cenario.semear_mensagem(Canal.EMAIL, assunto="Aviso", nome="Aprovada 2"),
        cenario.semear_mensagem(Canal.WHATSAPP, nome="Aprovada 3"),
    ]
    rejeitada = cenario.semear_mensagem(
        Canal.SMS, estado=EstadoMensagem.REJEITADA, nome="Rejeitada"
    )
    excluida = cenario.semear_mensagem(
        Canal.SMS, estado=EstadoMensagem.EXCLUIDA, nome="Excluída"
    )
    em_excecao = cenario.semear_mensagem(
        Canal.SMS, estado=EstadoMensagem.FALHOU_CONTEUDO, nome="Em exceção"
    )

    resultado = cenario.confirmar()

    entregas = cenario.entregas.listar_por_execucao(EXECUCAO_ID)
    assert len(entregas) == 3
    assert {entrega.mensagem_id for entrega in entregas} == set(aprovadas)
    assert set(resultado.mensagens_simuladas) == set(aprovadas)
    assert cenario.estado_de(rejeitada) is EstadoMensagem.REJEITADA
    assert cenario.estado_de(excluida) is EstadoMensagem.EXCLUIDA
    assert cenario.estado_de(em_excecao) is EstadoMensagem.FALHOU_CONTEUDO


def test_mensagem_regenerada_entre_a_decisao_e_a_confirmacao_fica_de_fora(
    tmp_path: Path,
) -> None:
    """Primeiro Edge Case da spec: a mensagem que era `aprovada` quando o modal abriu e voltou
    ao ciclo de conteúdo antes do clique é excluída, não simulada com dado desatualizado."""

    cenario = Cenario(tmp_path)
    aprovada = cenario.semear_mensagem(Canal.SMS, nome="Segue aprovada")
    regenerada = cenario.semear_mensagem(Canal.SMS, nome="Regenerada")
    versao_no_modal = cenario.versao_de(regenerada)
    cenario.mensagens.transicionar(regenerada, versao_no_modal, EstadoMensagem.GERANDO)

    resultado = cenario.confirmar()

    entregas = cenario.entregas.listar_por_execucao(EXECUCAO_ID)
    assert [entrega.mensagem_id for entrega in entregas] == [aprovada]
    assert resultado.mensagens_simuladas == (aprovada,)
    assert cenario.estado_de(regenerada) is EstadoMensagem.GERANDO
    assert cenario.versao_de(regenerada) == versao_no_modal + 1


def test_mensagem_aprovada_por_marina_sem_aprovacao_do_critico_fica_de_fora(
    tmp_path: Path,
) -> None:
    """SIMUL-04 exige a aprovação dupla real: só a decisão de Marina não basta, a avaliação
    crítica da última versão também precisa estar aprovada."""

    cenario = Cenario(tmp_path)
    aprovada = cenario.semear_mensagem(Canal.SMS, nome="Dupla aprovação")
    sem_critico = cenario.semear_mensagem(
        Canal.SMS, aprovada_pelo_critico=False, nome="Crítico reprovou"
    )

    resultado = cenario.confirmar()

    entregas = cenario.entregas.listar_por_execucao(EXECUCAO_ID)
    assert [entrega.mensagem_id for entrega in entregas] == [aprovada]
    assert resultado.mensagens_simuladas == (aprovada,)
    assert cenario.estado_de(sem_critico) is EstadoMensagem.APROVADA


def test_nenhum_conector_real_de_canal_e_alcancavel_pelo_codigo_da_simulacao() -> None:
    """SIMUL-05 e Out of Scope: a simulação é inteiramente local. Nenhum cliente HTTP, SMTP ou
    de provedor de mensageria aparece no caso de uso nem no repositório de entregas."""

    modulos = [
        Path("central_preventiva/aplicacao/simulacao.py"),
        Path("central_preventiva/adaptadores/persistencia/repositorio_entregas_simuladas.py"),
    ]
    proibidos = [
        "httpx",
        "requests",
        "urllib",
        "smtplib",
        "twilio",
        "sendgrid",
        "boto3",
        "graph.facebook.com",
        "api.whatsapp",
    ]

    for modulo in modulos:
        fonte = modulo.read_text(encoding="utf-8")
        encontrados = [termo for termo in proibidos if termo in fonte]
        assert encontrados == [], f"{modulo} referencia conector externo: {encontrados}"


# --- Gate da confirmação (SIMUL-01, SIMUL-03, segundo Edge Case) --------------------------


def test_confirmacao_sem_reconhecimento_e_recusada_antes_de_qualquer_efeito(
    tmp_path: Path,
) -> None:
    """SIMUL-03: o backend recusa o comando sem o reconhecimento marcado, como defesa em
    profundidade — nada é reclamado, nada é criado."""

    cenario = Cenario(tmp_path)
    mensagem = cenario.semear_mensagem()

    with pytest.raises(ReconhecimentoObrigatorio) as capturado:
        cenario.confirmar(reconhecimento=False)

    assert capturado.value.execucao_id == EXECUCAO_ID
    assert cenario.entregas.listar_por_execucao(EXECUCAO_ID) == []
    assert cenario.estado_execucao() is EstadoExecucao.AGUARDANDO_CONFIRMACAO
    assert cenario.estado_de(mensagem) is EstadoMensagem.APROVADA


def test_confirmacao_sem_nenhuma_aprovada_e_recusada_sem_simulacao_vazia(
    tmp_path: Path,
) -> None:
    """Segundo Edge Case da spec: sem nenhuma aprovada no momento da confirmação, o comando é
    rejeitado com erro claro, sem criar simulação vazia nem reclamar o agregado."""

    cenario = Cenario(tmp_path)
    rejeitada = cenario.semear_mensagem(estado=EstadoMensagem.REJEITADA)

    with pytest.raises(NenhumaMensagemAprovada) as capturado:
        cenario.confirmar()

    assert capturado.value.execucao_id == EXECUCAO_ID
    assert cenario.entregas.listar_por_execucao(EXECUCAO_ID) == []
    assert cenario.estado_execucao() is EstadoExecucao.AGUARDANDO_CONFIRMACAO
    assert cenario.estado_de(rejeitada) is EstadoMensagem.REJEITADA


def test_execucao_inexistente_recusa_a_confirmacao(tmp_path: Path) -> None:
    """AD-011: um identificador desconhecido não confirma nada nem revela existência."""

    cenario = Cenario(tmp_path)
    cenario.semear_mensagem()

    with pytest.raises(ExecucaoInexistente):
        cenario.confirmar(execucao_id=uuid4())

    assert cenario.entregas.listar_por_execucao(EXECUCAO_ID) == []


@pytest.mark.parametrize(
    "estado",
    [
        EstadoExecucao.AGUARDANDO_REVISAO,
        EstadoExecucao.PROCESSANDO_MENSAGENS,
        EstadoExecucao.CONCLUIDA,
    ],
)
def test_confirmacao_so_parte_de_aguardando_confirmacao(
    tmp_path: Path, estado: EstadoExecucao
) -> None:
    """SIMUL-01/SIMUL-02: `aguardando_confirmacao` é o gate agregado separado entre a decisão
    de conteúdo e a simulação; fora dele a confirmação não roda."""

    cenario = Cenario(tmp_path, estado=estado)
    cenario.semear_mensagem()

    with pytest.raises(EstadoNaoConfirmavel) as capturado:
        cenario.confirmar()

    assert capturado.value.estado is estado
    assert cenario.entregas.listar_por_execucao(EXECUCAO_ID) == []


# --- Idempotência e concorrência (SIMUL-07, SIMUL-08) -------------------------------------


def test_repetir_a_mesma_chave_devolve_a_simulacao_registrada_sem_criar_segunda_entrega(
    tmp_path: Path,
) -> None:
    """SIMUL-07: o replay do comando devolve a simulação já registrada e não cria entrega."""

    cenario = Cenario(tmp_path)
    cenario.semear_mensagem()
    primeira = cenario.confirmar()

    segunda = cenario.confirmar()

    assert segunda == primeira
    assert len(cenario.entregas.listar_por_execucao(EXECUCAO_ID)) == 1
    assert cenario.estado_execucao() is EstadoExecucao.CONCLUIDA


def test_mesma_chave_com_outro_conteudo_e_conflito_de_idempotencia(tmp_path: Path) -> None:
    """AD-002: a chave é escopada pelo conteúdo da requisição; reusá-la com outro conteúdo é
    conflito, nunca a resposta da primeira."""

    cenario = Cenario(tmp_path)
    cenario.semear_mensagem()
    cenario.confirmar()

    with pytest.raises(ConflitoIdempotencia):
        cenario.confirmar(hash_requisicao="outro-hash")

    assert len(cenario.entregas.listar_por_execucao(EXECUCAO_ID)) == 1


def test_confirmacao_com_versao_desatualizada_nao_reclama_nem_cria_entrega(
    tmp_path: Path,
) -> None:
    """SIMUL-08/AD-008: `versao_esperada` desatualizada é conflito; nenhuma mensagem é
    reclamada e o agregado não sai de `aguardando_confirmacao`."""

    cenario = Cenario(tmp_path)
    mensagem = cenario.semear_mensagem()

    with pytest.raises(ConflitoVersao):
        cenario.confirmar(versao_esperada=99)

    assert cenario.entregas.listar_por_execucao(EXECUCAO_ID) == []
    assert cenario.estado_execucao() is EstadoExecucao.AGUARDANDO_CONFIRMACAO
    assert cenario.estado_de(mensagem) is EstadoMensagem.APROVADA


def test_segunda_confirmacao_com_chave_nova_nao_cria_um_segundo_conjunto_de_entregas(
    tmp_path: Path,
) -> None:
    """SIMUL-08: das duas confirmações do mesmo lote, só a primeira reclama o agregado; a
    outra é recusada (409 no roteador), sem nenhuma duplicação parcial."""

    cenario = Cenario(tmp_path)
    cenario.semear_mensagem(Canal.SMS, nome="Primeira")
    cenario.semear_mensagem(Canal.SMS, nome="Segunda")
    primeira = cenario.confirmar(chave="chave-a")

    with pytest.raises(EstadoNaoConfirmavel) as capturado:
        cenario.confirmar(chave="chave-b", hash_requisicao="hash-b")

    assert capturado.value.estado is EstadoExecucao.CONCLUIDA
    assert len(primeira.entregas_criadas) == 2
    assert len(cenario.entregas.listar_por_execucao(EXECUCAO_ID)) == 2


# --- Falha local: rollback e segunda transação (SIMUL-09) ---------------------------------


def test_falha_local_desfaz_as_entregas_e_preserva_as_mensagens_como_aprovada(
    tmp_path: Path,
) -> None:
    """SIMUL-09: a transação 1 volta atrás primeiro — nenhuma entrega parcial, toda mensagem
    ainda `aprovada` e na mesma versão — e só depois o agregado vai a `falhou_simulacao`."""

    cenario = Cenario(tmp_path)
    primeira = cenario.semear_mensagem(Canal.SMS, nome="Primeira")
    segunda = cenario.semear_mensagem(Canal.EMAIL, assunto="Aviso", nome="Segunda")
    versoes_antes = (cenario.versao_de(primeira), cenario.versao_de(segunda))

    with pytest.raises(FalhaLocalSimulacao) as capturado:
        cenario.confirmar(injecao_falha_teste=falha_local)

    assert capturado.value.execucao_id == EXECUCAO_ID
    assert cenario.entregas.listar_por_execucao(EXECUCAO_ID) == []
    assert cenario.estado_de(primeira) is EstadoMensagem.APROVADA
    assert cenario.estado_de(segunda) is EstadoMensagem.APROVADA
    assert (cenario.versao_de(primeira), cenario.versao_de(segunda)) == versoes_antes
    assert cenario.estado_execucao() is EstadoExecucao.FALHOU_SIMULACAO


def test_falha_local_persiste_excecao_sanitizada_e_nunca_falha_de_canal(
    tmp_path: Path,
) -> None:
    """SIMUL-09: a `Exceção` registrada é local e sanitizada — nomeia o tipo do erro, nunca o
    conteúdo simulado nem um desfecho fictício de provedor de canal."""

    cenario = Cenario(tmp_path)
    cenario.semear_mensagem(corpo="Chuva forte hoje na sua região.")

    with pytest.raises(FalhaLocalSimulacao):
        cenario.confirmar(injecao_falha_teste=falha_local)

    causa, tentativas, impacto = cenario.excecoes_registradas()[0]
    assert causa == f"{PREFIXO_CAUSA_FALHA_LOCAL}:RuntimeError"
    assert tentativas == TENTATIVAS_FALHA_LOCAL
    assert impacto == IMPACTO_FALHA_SIMULACAO
    assert "Chuva forte" not in causa
    for termo in ("whatsapp", "sms", "email", "provedor", "canal"):
        assert termo not in causa.lower()
    assert (MARCO_FALHOU_SIMULACAO, causa) in cenario.marcos()


def test_transacao_de_falha_e_idempotente_e_nao_persiste_a_excecao_duas_vezes(
    tmp_path: Path,
) -> None:
    """SIMUL-09: a segunda transação é idempotente. Repeti-la sobre um agregado já em
    `falhou_simulacao` não levanta erro, não reabre o terminal e não grava outra `Exceção`.

    O gancho é chamado diretamente porque o caminho público guarda antes: uma vez terminal, a
    execução recusa a confirmação em `EstadoNaoConfirmavel` e nunca chega à transação 2 de
    novo — que é justamente o replay que este teste precisa exercitar.
    """

    cenario = Cenario(tmp_path)
    cenario.semear_mensagem()
    with pytest.raises(FalhaLocalSimulacao):
        cenario.confirmar(injecao_falha_teste=falha_local)

    cenario.servico._registrar_falha_local(  # pyright: ignore[reportPrivateUsage]
        EXECUCAO_ID, RuntimeError("segunda passagem pela mesma falha")
    )

    assert len(cenario.excecoes_registradas()) == 1
    assert cenario.estado_execucao() is EstadoExecucao.FALHOU_SIMULACAO
    assert [marco for marco, _ in cenario.marcos()] == [MARCO_FALHOU_SIMULACAO]


def test_confirmacao_repetida_depois_da_falha_local_nao_reabre_nem_duplica(
    tmp_path: Path,
) -> None:
    """SIMUL-09 + AD-009: reenviar a confirmação com chave nova depois da falha é recusado no
    gate de estado; o terminal não reabre e nenhuma segunda exceção é gravada."""

    cenario = Cenario(tmp_path)
    mensagem = cenario.semear_mensagem()
    with pytest.raises(FalhaLocalSimulacao):
        cenario.confirmar(injecao_falha_teste=falha_local)

    with pytest.raises(EstadoNaoConfirmavel) as capturado:
        cenario.confirmar(chave="chave-b", hash_requisicao="hash-b")

    assert capturado.value.estado is EstadoExecucao.FALHOU_SIMULACAO
    assert len(cenario.excecoes_registradas()) == 1
    assert cenario.entregas.listar_por_execucao(EXECUCAO_ID) == []
    assert cenario.estado_de(mensagem) is EstadoMensagem.APROVADA


# --- Nova tentativa correlacionada (SIMUL-10, AD-009, AD-012) -----------------------------


def preparar_origem_terminal(tmp_path: Path) -> Cenario:
    """Monta uma execução que falhou na simulação, com público elegível preservado."""

    cenario = Cenario(tmp_path)
    cenario.semear_mensagem(Canal.SMS, nome="Incluída")
    cenario.elegibilidade(canal="email", nome="Excluída", elegivel=False)
    with pytest.raises(FalhaLocalSimulacao):
        cenario.confirmar(injecao_falha_teste=falha_local)
    return cenario


def test_nova_tentativa_cria_execucao_correlacionada_e_mantem_a_origem_terminal(
    tmp_path: Path,
) -> None:
    """SIMUL-10/AD-009: a nova execução nasce em `aguardando_geracao` com `execucao_origem_id`
    próprio; a origem permanece em `falhou_simulacao`, nunca reaberta."""

    cenario = preparar_origem_terminal(tmp_path)

    nova_id = cenario.servico.solicitar_nova_tentativa(EXECUCAO_ID, "chave-retry", HASH)

    nova = cenario.execucoes.buscar(nova_id)
    assert nova is not None
    assert nova_id != EXECUCAO_ID
    assert nova.estado is EstadoExecucao.AGUARDANDO_GERACAO
    assert nova.execucao_origem_id == EXECUCAO_ID
    assert cenario.estado_execucao() is EstadoExecucao.FALHOU_SIMULACAO
    correlacionadas = cenario.execucoes.listar_correlacionadas(EXECUCAO_ID)
    assert [correlacionada.id for correlacionada in correlacionadas] == [nova_id]


def test_nova_tentativa_copia_incluidas_e_excluidas_com_o_mesmo_snapshot(
    tmp_path: Path,
) -> None:
    """AD-012: toda elegibilidade da origem — incluída e excluída — é duplicada para a nova
    execução, com conteúdo de snapshot idêntico, não um placeholder qualquer."""

    cenario = preparar_origem_terminal(tmp_path)

    nova_id = cenario.servico.solicitar_nova_tentativa(EXECUCAO_ID, "chave-retry", HASH)

    originais = {
        linha.elegivel: linha
        for linha in cenario.elegibilidades.listar_por_execucao(EXECUCAO_ID)
    }
    copiadas = cenario.elegibilidades.listar_por_execucao(nova_id)
    assert len(copiadas) == 2
    assert {linha.elegivel for linha in copiadas} == {True, False}
    assert {linha.id for linha in copiadas}.isdisjoint(
        {linha.id for linha in originais.values()}
    )
    for copia in copiadas:
        original = originais[copia.elegivel]
        assert copia.nome_segurado == original.nome_segurado
        assert copia.justificativa == original.justificativa
        assert copia.canal == original.canal
        assert copia.criterios == original.criterios
        assert copia.evento_id == original.evento_id
        assert copia.regra_id == original.regra_id
        assert copia.regra_versao == original.regra_versao
        assert copia.segurado_id == original.segurado_id
        assert copia.apolice_id == original.apolice_id


def test_retentativa_de_origem_que_chegou_a_simulando_gera_contexto_e_mensagem_sem_colidir(
    tmp_path: Path,
) -> None:
    """AD-012, cenário que esta história torna obrigatório: a origem chegou a `simulando`, logo
    já tem contexto e mensagem por elegibilidade. A nova execução monta os seus sobre as
    *cópias*, sem violar a `UNIQUE (elegibilidade_id)` de `contextos_agente` nem a
    `UNIQUE (elegibilidade_id, canal)` de `mensagens`."""

    cenario = Cenario(tmp_path)
    mensagem_origem = cenario.semear_mensagem(Canal.SMS, nome="Incluída")
    registro_origem = cenario.mensagens.obter(mensagem_origem)
    assert registro_origem is not None
    cenario.contextos.salvar(
        EXECUCAO_ID,
        registro_origem.elegibilidade_id,
        CONTEXTO,
        ("evento", "canal"),
        ("documentos",),
    )
    with pytest.raises(FalhaLocalSimulacao):
        cenario.confirmar(injecao_falha_teste=falha_local)

    nova_id = cenario.servico.solicitar_nova_tentativa(EXECUCAO_ID, "chave-retry", HASH)

    copiada = cenario.elegibilidades.listar_por_execucao(nova_id)[0]
    contexto_novo = cenario.contextos.salvar(
        nova_id, copiada.id, CONTEXTO, ("evento", "canal"), ("documentos",)
    )
    mensagem_nova = cenario.mensagens.criar(nova_id, copiada.id, Canal.SMS)

    assert contexto_novo is not None
    assert mensagem_nova != mensagem_origem
    assert len(cenario.contextos.listar_por_execucao(nova_id)) == 1
    assert len(cenario.contextos.listar_por_execucao(EXECUCAO_ID)) == 1
    assert [item.id for item in cenario.mensagens.listar_por_execucao(nova_id)] == [
        mensagem_nova
    ]
    assert [item.id for item in cenario.mensagens.listar_por_execucao(EXECUCAO_ID)] == [
        mensagem_origem
    ]


def test_replay_da_nova_tentativa_devolve_a_mesma_execucao_sem_criar_outra(
    tmp_path: Path,
) -> None:
    """SIMUL-10: o replay do comando não duplica execução nem cópia de elegibilidade."""

    cenario = preparar_origem_terminal(tmp_path)
    primeira = cenario.servico.solicitar_nova_tentativa(EXECUCAO_ID, "chave-retry", HASH)

    segunda = cenario.servico.solicitar_nova_tentativa(EXECUCAO_ID, "chave-retry", HASH)

    assert segunda == primeira
    assert len(cenario.execucoes.listar_correlacionadas(EXECUCAO_ID)) == 1
    assert len(cenario.elegibilidades.listar_por_execucao(primeira)) == 2


def test_nova_tentativa_com_a_mesma_chave_e_requisicao_diferente_e_conflito(
    tmp_path: Path,
) -> None:
    """AD-002: chave reusada com outro conteúdo é conflito, não a resposta da primeira."""

    cenario = preparar_origem_terminal(tmp_path)
    cenario.servico.solicitar_nova_tentativa(EXECUCAO_ID, "chave-retry", HASH)

    with pytest.raises(ConflitoIdempotencia):
        cenario.servico.solicitar_nova_tentativa(EXECUCAO_ID, "chave-retry", "outro-hash")

    assert len(cenario.execucoes.listar_correlacionadas(EXECUCAO_ID)) == 1


@pytest.mark.parametrize(
    "estado",
    [EstadoExecucao.AGUARDANDO_CONFIRMACAO, EstadoExecucao.CONCLUIDA],
)
def test_nova_tentativa_so_parte_de_falhou_simulacao(
    tmp_path: Path, estado: EstadoExecucao
) -> None:
    """SIMUL-10: a nova tentativa de simulação só parte do terminal `falhou_simulacao`."""

    cenario = Cenario(tmp_path, estado=estado)
    cenario.semear_mensagem()

    with pytest.raises(OrigemNaoRetentavel) as capturado:
        cenario.servico.solicitar_nova_tentativa(EXECUCAO_ID, "chave-retry", HASH)

    assert capturado.value.estado is estado
    assert cenario.execucoes.listar_correlacionadas(EXECUCAO_ID) == []


def test_nova_tentativa_de_execucao_inexistente_e_recusada(tmp_path: Path) -> None:
    """AD-011: identificador desconhecido não cria execução nem revela existência."""

    cenario = preparar_origem_terminal(tmp_path)

    with pytest.raises(ExecucaoInexistente):
        cenario.servico.solicitar_nova_tentativa(uuid4(), "chave-retry", HASH)

    assert cenario.execucoes.listar_correlacionadas(EXECUCAO_ID) == []


def test_origem_sem_nenhuma_elegibilidade_preservada_rejeita_a_nova_tentativa(
    tmp_path: Path,
) -> None:
    """SIMUL-10: a validação dos snapshots roda antes de criar qualquer registro."""

    cenario = Cenario(tmp_path, estado=EstadoExecucao.FALHOU_SIMULACAO)

    with pytest.raises(SnapshotInvalido) as capturado:
        cenario.servico.solicitar_nova_tentativa(EXECUCAO_ID, "chave-retry", HASH)

    assert "nenhuma elegibilidade" in capturado.value.motivo
    assert cenario.execucoes.listar_correlacionadas(EXECUCAO_ID) == []


def test_snapshot_com_versao_de_regra_nao_suportada_rejeita_sem_criar_execucao(
    tmp_path: Path,
) -> None:
    """SIMUL-10: versão de regra fora do suportado invalida o snapshot da origem."""

    cenario = Cenario(tmp_path, estado=EstadoExecucao.FALHOU_SIMULACAO)
    cenario.elegibilidade(regra_id=cenario.regra(versao=0))

    with pytest.raises(SnapshotInvalido) as capturado:
        cenario.servico.solicitar_nova_tentativa(EXECUCAO_ID, "chave-retry", HASH)

    assert "versão de regra não suportada" in capturado.value.motivo
    assert cenario.execucoes.listar_correlacionadas(EXECUCAO_ID) == []
    assert cenario.elegibilidades.contar_por_execucao(EXECUCAO_ID).incluidos == 1


def test_snapshot_sem_regra_versionada_resolvivel_rejeita_sem_criar_execucao(
    tmp_path: Path,
) -> None:
    """SIMUL-10: uma elegibilidade cuja regra versionada não é mais resolvível deixa o
    snapshot incompleto, e a nova tentativa é recusada antes de criar qualquer registro."""

    cenario = Cenario(tmp_path, estado=EstadoExecucao.FALHOU_SIMULACAO)
    cenario.elegibilidade(regra_id=uuid4())

    with pytest.raises(SnapshotInvalido) as capturado:
        cenario.servico.solicitar_nova_tentativa(EXECUCAO_ID, "chave-retry", HASH)

    assert "regra versionada" in capturado.value.motivo
    assert cenario.execucoes.listar_correlacionadas(EXECUCAO_ID) == []


def test_snapshot_com_evento_de_referencia_ausente_rejeita_sem_criar_execucao(
    tmp_path: Path,
) -> None:
    """SIMUL-10: o evento versionado referenciado precisa existir antes de qualquer cópia."""

    cenario = Cenario(tmp_path, estado=EstadoExecucao.FALHOU_SIMULACAO)
    cenario.elegibilidade()
    with abrir_conexao(cenario.caminho) as conexao:
        conexao.execute("DELETE FROM eventos_meteorologicos WHERE id = ?", [EVENTO_ID])

    with pytest.raises(SnapshotInvalido) as capturado:
        cenario.servico.solicitar_nova_tentativa(EXECUCAO_ID, "chave-retry", HASH)

    assert "evento de referência não existe" in capturado.value.motivo
    assert cenario.execucoes.listar_correlacionadas(EXECUCAO_ID) == []
