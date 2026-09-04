"""Testes da revisão humana do lote de comunicação (REVISAO-01..14).

Os repositórios de mensagem, avaliação crítica, decisão humana e execução são os reais, sobre
um banco temporário migrado: concorrência otimista, atomicidade da transação única e as
`CHECK` da migração `0013` são garantias do próprio banco — testá-las com dublê provaria
pouco. Elegibilidades, contextos e eventos são dublês, como em 3.2/3.3/3.4, porque só
fornecem o snapshot de origem já coberto por 2.5/3.1.
"""

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.adaptadores.persistencia.repositorio_avaliacoes_criticas import (
    RepositorioAvaliacoesCriticas,
)
from central_preventiva.adaptadores.persistencia.repositorio_contextos_agente import (
    RegistroContextoAgente,
)
from central_preventiva.adaptadores.persistencia.repositorio_decisoes_humanas import (
    RepositorioDecisoesHumanas,
)
from central_preventiva.adaptadores.persistencia.repositorio_elegibilidade import (
    RegistroElegibilidade,
)
from central_preventiva.adaptadores.persistencia.repositorio_execucao_preventiva import (
    RepositorioExecucaoPreventiva,
)
from central_preventiva.adaptadores.persistencia.repositorio_mensagens import (
    LIMITE_TENTATIVAS_MENSAGEM,
    RepositorioMensagens,
)
from central_preventiva.aplicacao.revisao_lote import (
    PRIORIDADE_APROVACAO_LIMPA,
    PRIORIDADE_EXCECAO,
    PRIORIDADE_REPROVACAO_HISTORICA,
    PRIORIDADE_SEM_PENDENCIA,
    PortasRevisaoLote,
    ServicoRevisaoLote,
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
PERFIL = "Administrador"
MODELO = "gpt-4o-mini"
VERSAO_PROMPT = "v1"

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

MOTIVO_TOM = MotivoCritica(CategoriaCritica.TOM, "O texto usa tom alarmista.")


class ElegibilidadesFalsas:
    """Repositório de elegibilidades dublê, filtrando pela execução consultada."""

    def __init__(self) -> None:
        self.registros: list[RegistroElegibilidade] = []

    def listar_por_execucao(self, execucao_id: UUID) -> list[RegistroElegibilidade]:
        return [item for item in self.registros if item.execucao_id == execucao_id]


class ContextosFalsos:
    """Repositório de contextos dublê, com a proveniência por item já montada (3.1)."""

    def __init__(self) -> None:
        self.categorias: dict[UUID, tuple[tuple[str, ...], tuple[str, ...]]] = {}

    def obter_por_elegibilidade(self, elegibilidade_id: UUID) -> RegistroContextoAgente | None:
        categorias = self.categorias.get(elegibilidade_id)
        if categorias is None:
            return None
        return RegistroContextoAgente(
            id=uuid4(),
            execucao_id=EXECUCAO_ID,
            elegibilidade_id=elegibilidade_id,
            contexto=ContextoAgente(
                evento="chuva_intensa",
                localizacao_aproximada="9990001",
                coberturas_relevantes=("alagamento",),
                canal="sms",
                orientacoes_seguranca=("Evite áreas alagadas.",),
            ),
            categorias_usadas=categorias[0],
            categorias_nao_usadas=categorias[1],
        )


class EventosFalsos:
    """Repositório de eventos dublê, resolvendo apenas o evento do cenário."""

    def buscar_por_id(self, id: UUID) -> EventoMeteorologico | None:  # noqa: A002
        return EVENTO if id == EVENTO_ID else None


class Cenario:
    """Reúne o caso de uso real, os repositórios reais e os dublês de origem."""

    def __init__(
        self,
        tmp_path: Path,
        estado: EstadoExecucao = EstadoExecucao.AGUARDANDO_REVISAO,
    ) -> None:
        self.caminho = tmp_path / "central_preventiva.duckdb"
        ExecutorMigracoes(self.caminho).aplicar_pendentes()
        self.mensagens = RepositorioMensagens(self.caminho)
        self.avaliacoes = RepositorioAvaliacoesCriticas(self.caminho)
        self.decisoes = RepositorioDecisoesHumanas(self.caminho)
        self.execucoes = RepositorioExecucaoPreventiva(self.caminho)
        self.elegibilidades = ElegibilidadesFalsas()
        self.contextos = ContextosFalsos()
        with abrir_conexao(self.caminho) as conexao:
            conexao.execute(
                "INSERT INTO execucao_preventiva (id, estado, versao) VALUES (?, ?, 1)",
                [EXECUCAO_ID, estado.value],
            )
        self.servico = ServicoRevisaoLote(
            PortasRevisaoLote(
                execucoes=self.execucoes,
                mensagens=self.mensagens,
                elegibilidades=self.elegibilidades,
                avaliacoes=self.avaliacoes,
                decisoes=self.decisoes,
                contextos=self.contextos,
                eventos=EventosFalsos(),
            )
        )

    def elegibilidade(self, canal: str = "sms", nome: str = "Pessoa Teste") -> UUID:
        """Semeia um item do público elegível incluído, no formato que 2.5 devolve."""

        registro = RegistroElegibilidade(
            id=uuid4(),
            execucao_id=EXECUCAO_ID,
            evento_id=EVENTO_ID,
            regra_id=REGRA_ID,
            regra_versao=REGRA_VERSAO,
            segurado_id=uuid4(),
            nome_segurado=nome,
            apolice_id=uuid4(),
            codigo_ibge_area="9990001",
            elegivel=True,
            criterios=(
                Criterio(OPERANDO_AREA_AFETADA, "9990001", True, "Área corresponde."),
                Criterio(OPERANDO_COBERTURA_EXIGIDA, "alagamento", True, "Possui cobertura."),
            ),
            canal=canal,
            justificativa="Atende integralmente aos critérios da regra ativa.",
            criado_em=datetime(2026, 9, 4, 19, 0, tzinfo=UTC),
        )
        self.elegibilidades.registros.append(registro)
        self.contextos.categorias[registro.id] = (
            ("evento", "localizacao_aproximada", "coberturas_relevantes", "canal"),
            ("documentos", "dados_financeiros"),
        )
        return registro.id

    def semear_mensagem(
        self,
        canal: Canal = Canal.SMS,
        tentativas: tuple[tuple[bool, bool | None], ...] = ((True, True),),
        estado: EstadoMensagem = EstadoMensagem.AGUARDANDO_REVISAO,
        nome: str = "Pessoa Teste",
    ) -> UUID:
        """Semeia uma mensagem com suas tentativas persistidas e o estado final indicado.

        Cada tentativa é `(saida_valida, aprovada_pelo_critico | None)`; `None` significa
        tentativa sem avaliação crítica (recusa determinística, que nunca chega ao crítico).
        """

        elegibilidade_id = self.elegibilidade(canal=canal.value, nome=nome)
        mensagem_id = self.mensagens.criar(EXECUCAO_ID, elegibilidade_id, canal)
        for numero, (valida, aprovada) in enumerate(tentativas, start=1):
            if numero > 1:
                atual = self.mensagens.obter(mensagem_id)
                assert atual is not None
                self.mensagens.incrementar_tentativa(mensagem_id, atual.versao)
            versao_id = self.mensagens.salvar_versao(
                mensagem_id=mensagem_id,
                numero_tentativa=numero,
                conteudo=SaidaCanal(corpo=f"Conteúdo da tentativa {numero}."),
                duracao_ms=120.0 + numero,
                modelo=MODELO,
                versao_prompt=VERSAO_PROMPT,
                tokens_entrada=100,
                tokens_saida=30,
                valida=valida,
                motivo_invalidez=None if valida else "corpo acima do limite do canal",
            )
            if aprovada is not None:
                self.avaliacoes.salvar(
                    versao_mensagem_id=versao_id,
                    aprovada=aprovada,
                    motivos=() if aprovada else (MOTIVO_TOM,),
                    modelo=MODELO,
                    duracao_ms=90.0,
                )
        atual = self.mensagens.obter(mensagem_id)
        assert atual is not None
        if atual.estado is not estado:
            self.mensagens.transicionar(mensagem_id, atual.versao, estado)
        return mensagem_id

    def estado_execucao(self) -> EstadoExecucao:
        """Lê o estado agregado real persistido da execução do cenário."""

        snapshot = self.execucoes.buscar(EXECUCAO_ID)
        assert snapshot is not None
        return snapshot.estado


def test_execucao_inexistente_nao_devolve_lote(tmp_path: Path) -> None:
    """AD-011: um identificador desconhecido não devolve lote nem indício de existência."""

    cenario = Cenario(tmp_path)

    assert cenario.servico.obter_lote(uuid4()) is None


def test_lote_ordena_itens_em_excecao_antes_dos_aprovados(tmp_path: Path) -> None:
    """Teste independente do REVISAO-02: com 4 mensagens (2 aprovadas pelo crítico, 1 em
    `falhou_conteudo`, 1 em `falhou_integracao_ia`), os dois itens com exceção aparecem
    antes dos dois aprovados."""

    cenario = Cenario(tmp_path)
    aprovada_um = cenario.semear_mensagem(canal=Canal.SMS, nome="Aprovada 1")
    conteudo = cenario.semear_mensagem(
        canal=Canal.EMAIL,
        tentativas=((True, False), (True, False), (True, False)),
        estado=EstadoMensagem.FALHOU_CONTEUDO,
        nome="Falhou conteúdo",
    )
    aprovada_dois = cenario.semear_mensagem(canal=Canal.WHATSAPP, nome="Aprovada 2")
    integracao = cenario.semear_mensagem(
        canal=Canal.SMS,
        tentativas=(),
        estado=EstadoMensagem.FALHOU_INTEGRACAO_IA,
        nome="Falhou integração",
    )

    lote = cenario.servico.obter_lote(EXECUCAO_ID)

    assert lote is not None
    identificadores = [item.mensagem_id for item in lote.itens]
    assert set(identificadores[:2]) == {conteudo, integracao}
    assert set(identificadores[2:]) == {aprovada_um, aprovada_dois}
    assert [item.prioridade for item in lote.itens] == [
        PRIORIDADE_EXCECAO,
        PRIORIDADE_EXCECAO,
        PRIORIDADE_APROVACAO_LIMPA,
        PRIORIDADE_APROVACAO_LIMPA,
    ]


def test_lote_ordena_reprovacao_historica_entre_excecao_e_aprovacao_limpa(
    tmp_path: Path,
) -> None:
    """REVISAO-02 (Tech Decision): exceções primeiro, depois o item aprovado na tentativa
    final mas reprovado em uma anterior, depois a aprovação limpa; um item já decidido não
    exige atenção nenhuma e fecha a lista."""

    cenario = Cenario(tmp_path)
    limpa = cenario.semear_mensagem(canal=Canal.SMS, nome="Limpa")
    decidida = cenario.semear_mensagem(
        canal=Canal.EMAIL, estado=EstadoMensagem.APROVADA, nome="Já decidida"
    )
    historica = cenario.semear_mensagem(
        canal=Canal.WHATSAPP,
        tentativas=((True, False), (True, True)),
        nome="Reprovada antes",
    )
    excecao = cenario.semear_mensagem(
        canal=Canal.SMS,
        tentativas=((False, None), (False, None), (False, None)),
        estado=EstadoMensagem.FALHOU_CONTEUDO,
        nome="Exceção",
    )

    lote = cenario.servico.obter_lote(EXECUCAO_ID)

    assert lote is not None
    assert [item.mensagem_id for item in lote.itens] == [excecao, historica, limpa, decidida]
    assert [item.prioridade for item in lote.itens] == [
        PRIORIDADE_EXCECAO,
        PRIORIDADE_REPROVACAO_HISTORICA,
        PRIORIDADE_APROVACAO_LIMPA,
        PRIORIDADE_SEM_PENDENCIA,
    ]
    assert [item.reprovacao_historica for item in lote.itens] == [True, True, False, False]


def test_cabecalho_do_lote_traz_evento_regra_publico_canais_aprovacoes_e_excecoes(
    tmp_path: Path,
) -> None:
    """REVISAO-01: o lote apresenta evento, regra, público, distribuição por canal,
    aprovações agênticas e exceções."""

    cenario = Cenario(tmp_path)
    cenario.semear_mensagem(canal=Canal.SMS, nome="A")
    cenario.semear_mensagem(canal=Canal.SMS, nome="B")
    cenario.semear_mensagem(canal=Canal.EMAIL, nome="C")
    cenario.semear_mensagem(
        canal=Canal.WHATSAPP,
        tentativas=((True, False), (True, False), (True, False)),
        estado=EstadoMensagem.FALHOU_CONTEUDO,
        nome="D",
    )

    lote = cenario.servico.obter_lote(EXECUCAO_ID)

    assert lote is not None
    assert lote.execucao_id == EXECUCAO_ID
    assert lote.estado is EstadoExecucao.AGUARDANDO_REVISAO
    assert lote.evento == EVENTO
    assert lote.regra_id == REGRA_ID
    assert lote.regra_versao == REGRA_VERSAO
    assert lote.total_publico_incluido == 4
    assert lote.distribuicao_por_canal == (("email", 1), ("sms", 2), ("whatsapp", 1))
    assert lote.aprovacoes_agenticas == 3
    assert lote.itens_em_excecao == 1


def test_item_expoe_destinatario_conteudo_versoes_verificacoes_origem_e_proveniencia(
    tmp_path: Path,
) -> None:
    """REVISAO-03: o revisor de um item traz destinatário sintético, conteúdo, versões,
    verificações determinísticas, avaliações críticas, dados de origem e proveniência."""

    cenario = Cenario(tmp_path)
    mensagem_id = cenario.semear_mensagem(canal=Canal.SMS, nome="Marina Teste")

    lote = cenario.servico.obter_lote(EXECUCAO_ID)

    assert lote is not None
    item = lote.itens[0]
    origem = cenario.elegibilidades.registros[0]
    assert item.mensagem_id == mensagem_id
    assert item.canal == "sms"
    assert item.estado is EstadoMensagem.AGUARDANDO_REVISAO
    assert item.destinatario.nome_segurado == "Marina Teste"
    assert item.destinatario.elegibilidade_id == origem.id
    assert item.destinatario.segurado_id == origem.segurado_id
    assert item.destinatario.apolice_id == origem.apolice_id
    assert item.destinatario.codigo_ibge_area == "9990001"
    assert item.destinatario.canal == "sms"
    assert item.origem.evento_id == EVENTO_ID
    assert item.origem.regra_id == REGRA_ID
    assert item.origem.regra_versao == REGRA_VERSAO
    assert item.origem.criterios == origem.criterios
    assert item.origem.justificativa == origem.justificativa
    assert item.proveniencia is not None
    assert item.proveniencia.categorias_usadas == (
        "evento",
        "localizacao_aproximada",
        "coberturas_relevantes",
        "canal",
    )
    assert item.proveniencia.categorias_nao_usadas == ("documentos", "dados_financeiros")
    assert len(item.versoes) == 1
    versao = item.versoes[0]
    assert versao.conteudo == SaidaCanal(corpo="Conteúdo da tentativa 1.")
    assert versao.valida is True
    assert versao.motivo_invalidez is None
    assert versao.modelo == MODELO
    assert versao.versao_prompt == VERSAO_PROMPT
    assert versao.avaliacao is not None
    assert versao.avaliacao.avaliacao.aprovada is True
    assert versao.avaliacao.agente == "critico"


def test_revisor_mostra_as_duas_versoes_com_o_veredito_de_cada_uma(tmp_path: Path) -> None:
    """Teste independente do REVISAO-03: uma mensagem com 2 versões (uma reprovada, uma
    aprovada) mostra ambas, com o destinatário sintético separado do conteúdo gerado."""

    cenario = Cenario(tmp_path)
    cenario.semear_mensagem(
        canal=Canal.SMS, tentativas=((True, False), (True, True)), nome="Duas versões"
    )

    lote = cenario.servico.obter_lote(EXECUCAO_ID)

    assert lote is not None
    item = lote.itens[0]
    assert [versao.numero_tentativa for versao in item.versoes] == [1, 2]
    assert [versao.conteudo.corpo for versao in item.versoes] == [
        "Conteúdo da tentativa 1.",
        "Conteúdo da tentativa 2.",
    ]
    primeira, segunda = item.versoes
    assert primeira.avaliacao is not None
    assert primeira.avaliacao.avaliacao.aprovada is False
    assert primeira.avaliacao.avaliacao.motivos == (MOTIVO_TOM,)
    assert segunda.avaliacao is not None
    assert segunda.avaliacao.avaliacao.aprovada is True
    assert item.destinatario.nome_segurado == "Duas versões"
    assert item.aprovada_pelo_critico is True


def test_versao_recusada_pela_validacao_deterministica_nao_tem_avaliacao_critica(
    tmp_path: Path,
) -> None:
    """REVISAO-03: a verificação determinística (3.2) e a avaliação crítica (3.3) são
    distintas no item — uma saída recusada pelo validador nunca chega ao crítico."""

    cenario = Cenario(tmp_path)
    cenario.semear_mensagem(
        canal=Canal.SMS,
        tentativas=((False, None), (True, True)),
        nome="Recusa determinística",
    )

    lote = cenario.servico.obter_lote(EXECUCAO_ID)

    assert lote is not None
    primeira, segunda = lote.itens[0].versoes
    assert primeira.valida is False
    assert primeira.motivo_invalidez == "corpo acima do limite do canal"
    assert primeira.avaliacao is None
    assert segunda.valida is True
    assert segunda.avaliacao is not None


def test_item_no_limite_de_tentativas_nao_pode_regenerar(tmp_path: Path) -> None:
    """REVISAO-09: com as três tentativas consumidas, a regeneração fica indisponível; com
    tentativa livre, disponível. O limite vem do backend, não de uma constante da interface."""

    cenario = Cenario(tmp_path)
    esgotada = cenario.semear_mensagem(
        canal=Canal.SMS,
        tentativas=((True, False), (True, False), (True, True)),
        nome="Esgotada",
    )
    com_folga = cenario.semear_mensagem(canal=Canal.EMAIL, nome="Com folga")

    lote = cenario.servico.obter_lote(EXECUCAO_ID)

    assert lote is not None
    por_id = {item.mensagem_id: item for item in lote.itens}
    assert por_id[esgotada].tentativa_atual == LIMITE_TENTATIVAS_MENSAGEM
    assert por_id[esgotada].pode_regenerar is False
    assert por_id[esgotada].decidivel is True
    assert por_id[com_folga].tentativa_atual == 1
    assert por_id[com_folga].pode_regenerar is True
    assert por_id[com_folga].limite_tentativas == LIMITE_TENTATIVAS_MENSAGEM


def test_item_em_excecao_nao_e_decidivel_e_nao_conta_como_aprovacao_agentica(
    tmp_path: Path,
) -> None:
    """REVISAO-01/REVISAO-10: um item terminal de conteúdo aparece no lote com o motivo
    consultável, mas não espera decisão de Marina nem conta como aprovação do crítico."""

    cenario = Cenario(tmp_path)
    cenario.semear_mensagem(
        canal=Canal.SMS,
        tentativas=((True, False), (True, False), (True, False)),
        estado=EstadoMensagem.FALHOU_CONTEUDO,
        nome="Exceção",
    )

    lote = cenario.servico.obter_lote(EXECUCAO_ID)

    assert lote is not None
    item = lote.itens[0]
    assert item.em_excecao is True
    assert item.decidivel is False
    assert item.pode_regenerar is False
    assert item.aprovada_pelo_critico is False
    assert lote.aprovacoes_agenticas == 0
    assert item.versoes[-1].avaliacao is not None
    assert item.versoes[-1].avaliacao.avaliacao.motivos == (MOTIVO_TOM,)


def test_execucao_sem_mensagens_devolve_lote_vazio(tmp_path: Path) -> None:
    """Uma execução ainda sem mensagens devolve o lote vazio, não `None`: ela existe."""

    cenario = Cenario(tmp_path, estado=EstadoExecucao.PROCESSANDO_MENSAGENS)

    lote = cenario.servico.obter_lote(EXECUCAO_ID)

    assert lote is not None
    assert lote.itens == ()
    assert lote.distribuicao_por_canal == ()
    assert lote.evento is None
    assert lote.estado is EstadoExecucao.PROCESSANDO_MENSAGENS
