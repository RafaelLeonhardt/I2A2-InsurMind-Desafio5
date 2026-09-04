"""Testes da revisão humana do lote de comunicação (REVISAO-01..14).

Os repositórios de mensagem, avaliação crítica, decisão humana e execução são os reais, sobre
um banco temporário migrado: concorrência otimista, atomicidade da transação única e as
`CHECK` da migração `0013` são garantias do próprio banco — testá-las com dublê provaria
pouco. Elegibilidades, contextos e eventos são dublês, como em 3.2/3.3/3.4, porque só
fornecem o snapshot de origem já coberto por 2.5/3.1.
"""

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from central_preventiva.adaptadores.ia.agente_redator import RespostaRedator
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
    RepositorioExcecoesOperacionais,
    RepositorioExecucaoPreventiva,
)
from central_preventiva.adaptadores.persistencia.repositorio_idempotencia import (
    RepositorioIdempotencia,
)
from central_preventiva.adaptadores.persistencia.repositorio_mensagens import (
    LIMITE_TENTATIVAS_MENSAGEM,
    RepositorioMensagens,
)
from central_preventiva.adaptadores.persistencia.transacao import TransacaoDuckDB
from central_preventiva.aplicacao.geracao_mensagens import (
    PortasGeracaoMensagens,
    ServicoGeracaoMensagens,
)
from central_preventiva.aplicacao.grafos.geracao_mensagem import (
    DependenciasGrafo,
    construir_grafo,
)
from central_preventiva.aplicacao.portas_persistencia import ConflitoIdempotencia
from central_preventiva.aplicacao.revisao_lote import (
    MOTIVO_LIMITE_DE_TENTATIVAS,
    MOTIVO_MENSAGEM_INEXISTENTE,
    MOTIVO_MENSAGEM_JA_DECIDIDA,
    PRIORIDADE_APROVACAO_LIMPA,
    PRIORIDADE_EXCECAO,
    PRIORIDADE_REPROVACAO_HISTORICA,
    PRIORIDADE_SEM_PENDENCIA,
    ConflitoVersaoDecisao,
    DecisaoRecusada,
    DecisaoRequisitada,
    EstadoNaoRevisavel,
    ExecucaoInexistente,
    JustificativaObrigatoria,
    PortasRevisaoLote,
    ResultadoDecisaoLote,
    ServicoRevisaoLote,
)
from central_preventiva.dominio.avaliacao_critica import (
    AvaliacaoCritica,
    CategoriaCritica,
    MotivoCritica,
)
from central_preventiva.dominio.avaliador_elegibilidade import (
    OPERANDO_AREA_AFETADA,
    OPERANDO_COBERTURA_EXIGIDA,
)
from central_preventiva.dominio.avaliador_risco import Criterio
from central_preventiva.dominio.decisao_humana import ResultadoDecisaoHumana
from central_preventiva.dominio.estados_execucao import EstadoExecucao
from central_preventiva.dominio.estados_mensagem import EstadoMensagem
from central_preventiva.dominio.evento_meteorologico import (
    EventoMeteorologico,
    ProvenienciaEvento,
    TipoEventoMeteorologico,
)
from central_preventiva.dominio.montador_contexto_agente import ContextoAgente
from central_preventiva.dominio.validador_saida_canal import (
    Canal,
    LimitesCanal,
    SaidaCanal,
    ValidadorSaidaCanal,
)

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


class RedatorFalso:
    """Dublê do agente redator: um corpo válido novo a cada chamada."""

    def __init__(self) -> None:
        self.chamadas = 0

    @property
    def modelo(self) -> str:
        return MODELO

    async def gerar(
        self,
        contexto: ContextoAgente,
        canal: Canal,
        motivos_anteriores: tuple[MotivoCritica, ...] = (),
    ) -> RespostaRedator:
        self.chamadas += 1
        return RespostaRedator(
            SaidaCanal(corpo=f"Texto regenerado {self.chamadas}."), 100, 30
        )


class CriticoFalso:
    """Dublê do agente crítico: aprova toda avaliação pedida."""

    @property
    def modelo(self) -> str:
        return MODELO

    async def avaliar(
        self, conteudo: SaidaCanal, canal: Canal, contexto: ContextoAgente
    ) -> AvaliacaoCritica | None:
        return AvaliacaoCritica(True, ())


async def sem_espera(_: float) -> None:
    """Substitui o backoff real para que o teste não durma de fato."""


class Cenario:
    """Reúne o caso de uso real, os repositórios reais e os dublês de origem."""

    def __init__(
        self,
        tmp_path: Path,
        estado: EstadoExecucao = EstadoExecucao.AGUARDANDO_REVISAO,
        retomar_automaticamente: bool = True,
    ) -> None:
        self.caminho = tmp_path / "central_preventiva.duckdb"
        ExecutorMigracoes(self.caminho).aplicar_pendentes()
        self.mensagens = RepositorioMensagens(self.caminho)
        self.avaliacoes = RepositorioAvaliacoesCriticas(self.caminho)
        self.decisoes = RepositorioDecisoesHumanas(self.caminho)
        self.execucoes = RepositorioExecucaoPreventiva(self.caminho)
        self.idempotencia = RepositorioIdempotencia(self.caminho)
        self.elegibilidades = ElegibilidadesFalsas()
        self.contextos = ContextosFalsos()
        self.redator = RedatorFalso()
        with abrir_conexao(self.caminho) as conexao:
            conexao.execute(
                "INSERT INTO execucao_preventiva (id, estado, versao) VALUES (?, ?, 1)",
                [EXECUCAO_ID, estado.value],
            )
        self.geracao = ServicoGeracaoMensagens(
            PortasGeracaoMensagens(
                elegibilidades=self.elegibilidades,
                contextos=self.contextos,
                mensagens=self.mensagens,
                avaliacoes=self.avaliacoes,
                excecoes=RepositorioExcecoesOperacionais(self.caminho),
                execucoes=self.execucoes,
                grafo=construir_grafo(
                    DependenciasGrafo(
                        redator=self.redator,
                        validador=ValidadorSaidaCanal(
                            LimitesCanal(
                                whatsapp=1024, sms=160, assunto_email=78, corpo_email=2000
                            )
                        ),
                        critico=CriticoFalso(),
                        esperar=sem_espera,
                    )
                ),
                versao_prompt=VERSAO_PROMPT,
            )
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
                idempotencia=self.idempotencia,
                transacao=TransacaoDuckDB(self.caminho),
                acionar_regeneracao=(
                    self.geracao.retomar_mensagens_pendentes
                    if retomar_automaticamente
                    else None
                ),
            )
        )

    def decidir(
        self,
        *decisoes: DecisaoRequisitada,
        chave: str = "chave-1",
        hash_requisicao: str = "hash-1",
        execucao_id: UUID = EXECUCAO_ID,
    ) -> ResultadoDecisaoLote:
        """Envia uma decisão em lote pelo caso de uso real, como o roteador faria."""

        return asyncio.run(
            self.servico.decidir_lote(
                execucao_id, decisoes, PERFIL, chave, hash_requisicao
            )
        )

    def versao_de(self, mensagem_id: UUID) -> int:
        """Lê a versão de concorrência otimista atual da mensagem."""

        registro = self.mensagens.obter(mensagem_id)
        assert registro is not None
        return registro.versao

    def estado_de(self, mensagem_id: UUID) -> EstadoMensagem:
        """Lê o estado de conteúdo atual da mensagem."""

        registro = self.mensagens.obter(mensagem_id)
        assert registro is not None
        return registro.estado

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


# --- T4: decisão em lote (REVISAO-05..14) ---------------------------------------------


@pytest.mark.parametrize(
    ("resultado", "estado_esperado"),
    [
        (ResultadoDecisaoHumana.APROVAR, EstadoMensagem.APROVADA),
        (ResultadoDecisaoHumana.REJEITAR, EstadoMensagem.REJEITADA),
        (ResultadoDecisaoHumana.EXCLUIR, EstadoMensagem.EXCLUIDA),
    ],
)
def test_cada_decisao_terminal_move_a_mensagem_para_o_estado_correspondente(
    resultado: ResultadoDecisaoHumana, estado_esperado: EstadoMensagem, tmp_path: Path
) -> None:
    """REVISAO-05: aprovar, rejeitar e excluir levam a mensagem ao terminal de revisão do
    AD-4; nenhuma delas altera o texto gerado."""

    cenario = Cenario(tmp_path)
    mensagem_id = cenario.semear_mensagem()
    conteudo_antes = cenario.mensagens.listar_versoes(mensagem_id)[-1].conteudo

    decisao = cenario.decidir(
        DecisaoRequisitada(
            mensagem_id, cenario.versao_de(mensagem_id), resultado, "Motivo registrado."
        )
    )

    assert decisao.aplicadas == (mensagem_id,)
    assert decisao.recusadas == ()
    assert cenario.estado_de(mensagem_id) is estado_esperado
    assert cenario.mensagens.listar_versoes(mensagem_id)[-1].conteudo == conteudo_antes


def test_decisao_persiste_perfil_resultado_justificativa_e_versao_decidida(
    tmp_path: Path,
) -> None:
    """REVISAO-07: a decisão humana fica registrada com perfil, data, resultado,
    justificativa e a versão decidida, distinta da aprovação do agente crítico."""

    cenario = Cenario(tmp_path)
    mensagem_id = cenario.semear_mensagem()
    versao_mensagem = cenario.mensagens.listar_versoes(mensagem_id)[-1]

    cenario.decidir(
        DecisaoRequisitada(
            mensagem_id,
            cenario.versao_de(mensagem_id),
            ResultadoDecisaoHumana.REJEITAR,
            "Tom inadequado para o público.",
        )
    )

    decisoes = cenario.decisoes.obter_por_mensagem(mensagem_id)
    assert len(decisoes) == 1
    registrada = decisoes[0]
    assert registrada.perfil_responsavel == PERFIL
    assert registrada.resultado is ResultadoDecisaoHumana.REJEITAR
    assert registrada.justificativa == "Tom inadequado para o público."
    assert registrada.versao_mensagem_id == versao_mensagem.id
    assert registrada.criado_em is not None
    critica = cenario.avaliacoes.obter_por_versao(versao_mensagem.id)
    assert critica is not None
    assert critica.avaliacao.aprovada is True
    assert critica.agente == "critico"


@pytest.mark.parametrize(
    "resultado",
    [
        ResultadoDecisaoHumana.REJEITAR,
        ResultadoDecisaoHumana.EXCLUIR,
        ResultadoDecisaoHumana.REGENERAR,
    ],
)
@pytest.mark.parametrize("justificativa", [None, "", "   "])
def test_decisao_sem_justificativa_e_bloqueada_antes_de_qualquer_mutacao(
    resultado: ResultadoDecisaoHumana, justificativa: str | None, tmp_path: Path
) -> None:
    """REVISAO-06: rejeitar, excluir e regenerar sem justificativa ficam bloqueadas, e nada
    é mutado — nem a mensagem do envio, nem a outra decisão válida que veio junto."""

    cenario = Cenario(tmp_path)
    sem_motivo = cenario.semear_mensagem(canal=Canal.SMS, nome="Sem motivo")
    valida = cenario.semear_mensagem(canal=Canal.EMAIL, nome="Válida")

    with pytest.raises(JustificativaObrigatoria) as captura:
        cenario.decidir(
            DecisaoRequisitada(
                valida, cenario.versao_de(valida), ResultadoDecisaoHumana.APROVAR, None
            ),
            DecisaoRequisitada(
                sem_motivo, cenario.versao_de(sem_motivo), resultado, justificativa
            ),
        )

    assert captura.value.mensagem_id == sem_motivo
    assert captura.value.resultado is resultado
    assert cenario.estado_de(sem_motivo) is EstadoMensagem.AGUARDANDO_REVISAO
    assert cenario.estado_de(valida) is EstadoMensagem.AGUARDANDO_REVISAO
    assert cenario.decisoes.obter_por_mensagem(sem_motivo) == []
    assert cenario.decisoes.obter_por_mensagem(valida) == []
    assert cenario.estado_execucao() is EstadoExecucao.AGUARDANDO_REVISAO


def test_aprovacao_nao_exige_justificativa(tmp_path: Path) -> None:
    """REVISAO-06: a obrigatoriedade vale para rejeitar, excluir e regenerar — aprovar não."""

    cenario = Cenario(tmp_path)
    mensagem_id = cenario.semear_mensagem()

    decisao = cenario.decidir(
        DecisaoRequisitada(
            mensagem_id, cenario.versao_de(mensagem_id), ResultadoDecisaoHumana.APROVAR, None
        )
    )

    assert decisao.aplicadas == (mensagem_id,)
    assert cenario.estado_de(mensagem_id) is EstadoMensagem.APROVADA


def test_regeneracao_transiciona_a_mensagem_e_o_agregado_atomicamente(
    tmp_path: Path,
) -> None:
    """REVISAO-08: com `tentativas < 3`, a regeneração leva a mensagem a `gerando`,
    incrementa a tentativa uma única vez e devolve o agregado a `processando_mensagens`."""

    cenario = Cenario(tmp_path, retomar_automaticamente=False)
    mensagem_id = cenario.semear_mensagem()
    outra = cenario.semear_mensagem(canal=Canal.EMAIL, nome="Outra")

    decisao = cenario.decidir(
        DecisaoRequisitada(
            mensagem_id,
            cenario.versao_de(mensagem_id),
            ResultadoDecisaoHumana.REGENERAR,
            "Texto longo demais para SMS.",
        )
    )

    registro = cenario.mensagens.obter(mensagem_id)
    assert registro is not None
    assert registro.estado is EstadoMensagem.GERANDO
    assert registro.tentativa_atual == 2
    assert decisao.estado is EstadoExecucao.PROCESSANDO_MENSAGENS
    assert decisao.regeneracoes_ativas == (mensagem_id,)
    assert cenario.estado_de(outra) is EstadoMensagem.AGUARDANDO_REVISAO


def test_reenvio_idempotente_da_regeneracao_nao_conta_a_tentativa_duas_vezes(
    tmp_path: Path,
) -> None:
    """REVISAO-08: reenviar a mesma solicitação com a mesma `Idempotency-Key` devolve a
    resposta registrada e não incrementa a tentativa de novo, nem grava uma segunda decisão."""

    cenario = Cenario(tmp_path, retomar_automaticamente=False)
    mensagem_id = cenario.semear_mensagem()
    versao_esperada = cenario.versao_de(mensagem_id)
    pedido = DecisaoRequisitada(
        mensagem_id, versao_esperada, ResultadoDecisaoHumana.REGENERAR, "Refazer o texto."
    )

    primeira = cenario.decidir(pedido)
    segunda = cenario.decidir(pedido)

    registro = cenario.mensagens.obter(mensagem_id)
    assert registro is not None
    assert registro.tentativa_atual == 2
    assert primeira == segunda
    assert len(cenario.decisoes.obter_por_mensagem(mensagem_id)) == 1


def test_mesma_chave_com_outro_conteudo_e_conflito_de_idempotencia(tmp_path: Path) -> None:
    """AD-002: a mesma chave reusada para outro envio é conflito, não replay silencioso."""

    cenario = Cenario(tmp_path)
    primeira_mensagem = cenario.semear_mensagem(canal=Canal.SMS, nome="Primeira")
    segunda_mensagem = cenario.semear_mensagem(canal=Canal.EMAIL, nome="Segunda")
    cenario.decidir(
        DecisaoRequisitada(
            primeira_mensagem,
            cenario.versao_de(primeira_mensagem),
            ResultadoDecisaoHumana.APROVAR,
            None,
        ),
        chave="chave-repetida",
        hash_requisicao="hash-do-primeiro-envio",
    )

    with pytest.raises(ConflitoIdempotencia):
        cenario.decidir(
            DecisaoRequisitada(
                segunda_mensagem,
                cenario.versao_de(segunda_mensagem),
                ResultadoDecisaoHumana.APROVAR,
                None,
            ),
            chave="chave-repetida",
            hash_requisicao="hash-do-segundo-envio",
        )

    assert cenario.estado_de(segunda_mensagem) is EstadoMensagem.AGUARDANDO_REVISAO


def test_regeneracao_recusada_no_limite_de_tentativas_sem_afetar_as_demais(
    tmp_path: Path,
) -> None:
    """REVISAO-09: uma mensagem que já consumiu as três tentativas tem `regenerar` recusada
    com motivo específico, e as demais decisões válidas do mesmo envio seguem aplicadas."""

    cenario = Cenario(tmp_path)
    esgotada = cenario.semear_mensagem(
        canal=Canal.SMS,
        tentativas=((True, False), (True, False), (True, True)),
        nome="Esgotada",
    )
    com_folga = cenario.semear_mensagem(canal=Canal.EMAIL, nome="Com folga")

    decisao = cenario.decidir(
        DecisaoRequisitada(
            esgotada,
            cenario.versao_de(esgotada),
            ResultadoDecisaoHumana.REGENERAR,
            "Quero outra versão.",
        ),
        DecisaoRequisitada(
            com_folga, cenario.versao_de(com_folga), ResultadoDecisaoHumana.APROVAR, None
        ),
    )

    assert decisao.recusadas == (DecisaoRecusada(esgotada, MOTIVO_LIMITE_DE_TENTATIVAS),)
    assert decisao.aplicadas == (com_folga,)
    registro = cenario.mensagens.obter(esgotada)
    assert registro is not None
    assert registro.estado is EstadoMensagem.AGUARDANDO_REVISAO
    assert registro.tentativa_atual == LIMITE_TENTATIVAS_MENSAGEM
    assert cenario.decisoes.obter_por_mensagem(esgotada) == []
    assert cenario.estado_de(com_folga) is EstadoMensagem.APROVADA


def test_mensagem_no_limite_ainda_pode_ser_aprovada_rejeitada_ou_excluida(
    tmp_path: Path,
) -> None:
    """REVISAO-09: só a regeneração fica indisponível no limite; as outras três decisões
    continuam disponíveis para a mesma mensagem."""

    cenario = Cenario(tmp_path)
    esgotada = cenario.semear_mensagem(
        canal=Canal.SMS,
        tentativas=((True, False), (True, False), (True, True)),
        nome="Esgotada",
    )

    decisao = cenario.decidir(
        DecisaoRequisitada(
            esgotada,
            cenario.versao_de(esgotada),
            ResultadoDecisaoHumana.REJEITAR,
            "Prefiro não enviar.",
        )
    )

    assert decisao.recusadas == ()
    assert decisao.aplicadas == (esgotada,)
    assert cenario.estado_de(esgotada) is EstadoMensagem.REJEITADA


def test_conflito_de_versao_em_um_item_aborta_o_envio_inteiro(tmp_path: Path) -> None:
    """Teste independente do REVISAO-12: em um envio de 3 mensagens com uma
    `versao_esperada` desatualizada, nenhuma das 3 decisões é aplicada."""

    cenario = Cenario(tmp_path)
    primeira = cenario.semear_mensagem(canal=Canal.SMS, nome="Primeira")
    segunda = cenario.semear_mensagem(canal=Canal.EMAIL, nome="Segunda")
    desatualizada = cenario.semear_mensagem(canal=Canal.WHATSAPP, nome="Desatualizada")

    with pytest.raises(ConflitoVersaoDecisao) as captura:
        cenario.decidir(
            DecisaoRequisitada(
                primeira, cenario.versao_de(primeira), ResultadoDecisaoHumana.APROVAR, None
            ),
            DecisaoRequisitada(
                desatualizada,
                cenario.versao_de(desatualizada) + 7,
                ResultadoDecisaoHumana.REJEITAR,
                "Não serve.",
            ),
            DecisaoRequisitada(
                segunda,
                cenario.versao_de(segunda),
                ResultadoDecisaoHumana.EXCLUIR,
                "Fora do lote.",
            ),
        )

    assert captura.value.mensagens == (desatualizada,)
    for mensagem_id in (primeira, segunda, desatualizada):
        assert cenario.estado_de(mensagem_id) is EstadoMensagem.AGUARDANDO_REVISAO
        assert cenario.decisoes.obter_por_mensagem(mensagem_id) == []
    assert cenario.estado_execucao() is EstadoExecucao.AGUARDANDO_REVISAO


def test_conflito_de_versao_desfaz_ate_a_regeneracao_ja_gravada_na_transacao(
    tmp_path: Path,
) -> None:
    """REVISAO-12: a atomicidade vale também para o incremento de tentativa — o item
    regenerado antes do conflito volta à tentativa e ao estado originais."""

    cenario = Cenario(tmp_path)
    regenerada = cenario.semear_mensagem(canal=Canal.SMS, nome="Regenerada")
    desatualizada = cenario.semear_mensagem(canal=Canal.EMAIL, nome="Desatualizada")

    with pytest.raises(ConflitoVersaoDecisao):
        cenario.decidir(
            DecisaoRequisitada(
                regenerada,
                cenario.versao_de(regenerada),
                ResultadoDecisaoHumana.REGENERAR,
                "Refazer.",
            ),
            DecisaoRequisitada(
                desatualizada,
                cenario.versao_de(desatualizada) + 3,
                ResultadoDecisaoHumana.APROVAR,
                None,
            ),
        )

    registro = cenario.mensagens.obter(regenerada)
    assert registro is not None
    assert registro.estado is EstadoMensagem.AGUARDANDO_REVISAO
    assert registro.tentativa_atual == 1
    assert cenario.decisoes.obter_por_mensagem(regenerada) == []
    assert cenario.estado_execucao() is EstadoExecucao.AGUARDANDO_REVISAO


def test_item_ja_decidido_e_recusado_sem_impedir_as_demais_do_mesmo_envio(
    tmp_path: Path,
) -> None:
    """Segundo Edge Case da spec: uma mensagem já decidida antes é recusada do envio com
    motivo próprio, e isso não aborta as decisões válidas que vieram junto — é o oposto do
    conflito de `versao_esperada`, que aborta tudo."""

    cenario = Cenario(tmp_path)
    ja_decidida = cenario.semear_mensagem(
        canal=Canal.SMS, estado=EstadoMensagem.REJEITADA, nome="Já decidida"
    )
    pendente = cenario.semear_mensagem(canal=Canal.EMAIL, nome="Pendente")

    decisao = cenario.decidir(
        DecisaoRequisitada(
            ja_decidida, cenario.versao_de(ja_decidida), ResultadoDecisaoHumana.APROVAR, None
        ),
        DecisaoRequisitada(
            pendente, cenario.versao_de(pendente), ResultadoDecisaoHumana.APROVAR, None
        ),
    )

    assert decisao.recusadas == (DecisaoRecusada(ja_decidida, MOTIVO_MENSAGEM_JA_DECIDIDA),)
    assert decisao.aplicadas == (pendente,)
    assert cenario.estado_de(ja_decidida) is EstadoMensagem.REJEITADA
    assert cenario.estado_de(pendente) is EstadoMensagem.APROVADA


def test_mensagem_de_outra_execucao_e_recusada_como_inexistente(tmp_path: Path) -> None:
    """AD-011: um identificador desconhecido e um de outra execução recebem a mesma recusa."""

    cenario = Cenario(tmp_path)
    pendente = cenario.semear_mensagem()

    decisao = cenario.decidir(
        DecisaoRequisitada(uuid4(), 1, ResultadoDecisaoHumana.APROVAR, None),
        DecisaoRequisitada(
            pendente, cenario.versao_de(pendente), ResultadoDecisaoHumana.APROVAR, None
        ),
    )

    assert [item.motivo for item in decisao.recusadas] == [MOTIVO_MENSAGEM_INEXISTENTE]
    assert decisao.aplicadas == (pendente,)


def test_execucao_inexistente_recusa_a_decisao(tmp_path: Path) -> None:
    """AD-011: decidir sobre execução que não existe não aplica nada."""

    cenario = Cenario(tmp_path)

    with pytest.raises(ExecucaoInexistente):
        cenario.decidir(execucao_id=uuid4())


def test_execucao_fora_de_revisao_recusa_a_decisao(tmp_path: Path) -> None:
    """Terceiro Edge Case da spec: com o agregado em `processando_mensagens` (regeneração
    ativa), nenhuma decisão nova é aceita até a guarda ser satisfeita."""

    cenario = Cenario(tmp_path, estado=EstadoExecucao.PROCESSANDO_MENSAGENS)
    mensagem_id = cenario.semear_mensagem()

    with pytest.raises(EstadoNaoRevisavel) as captura:
        cenario.decidir(
            DecisaoRequisitada(
                mensagem_id,
                cenario.versao_de(mensagem_id),
                ResultadoDecisaoHumana.APROVAR,
                None,
            )
        )

    assert captura.value.estado is EstadoExecucao.PROCESSANDO_MENSAGENS
    assert cenario.estado_de(mensagem_id) is EstadoMensagem.AGUARDANDO_REVISAO


def test_sem_nenhuma_aprovada_a_execucao_conclui_sem_simulacao(tmp_path: Path) -> None:
    """REVISAO-13: todas as revisáveis decididas e nenhuma aprovada conclui a execução, com
    os motivos de rejeição e exclusão permanecendo consultáveis."""

    cenario = Cenario(tmp_path)
    rejeitada = cenario.semear_mensagem(canal=Canal.SMS, nome="Rejeitada")
    excluida = cenario.semear_mensagem(canal=Canal.EMAIL, nome="Excluída")

    decisao = cenario.decidir(
        DecisaoRequisitada(
            rejeitada,
            cenario.versao_de(rejeitada),
            ResultadoDecisaoHumana.REJEITAR,
            "Não distingue do alerta oficial.",
        ),
        DecisaoRequisitada(
            excluida,
            cenario.versao_de(excluida),
            ResultadoDecisaoHumana.EXCLUIR,
            "Público errado.",
        ),
    )

    assert decisao.estado is EstadoExecucao.CONCLUIDA
    assert decisao.mensagens_aprovadas == ()
    assert cenario.estado_execucao() is EstadoExecucao.CONCLUIDA
    lote = cenario.servico.obter_lote(EXECUCAO_ID)
    assert lote is not None
    motivos = {
        item.mensagem_id: tuple(decisao.justificativa for decisao in item.decisoes)
        for item in lote.itens
    }
    assert motivos[rejeitada] == ("Não distingue do alerta oficial.",)
    assert motivos[excluida] == ("Público errado.",)


def test_lote_inteiro_em_excecao_conclui_quando_marina_reconhece(tmp_path: Path) -> None:
    """Primeiro Edge Case da spec: sem nenhuma mensagem aprovável, o reconhecimento do lote
    (envio sem decisões) conclui a execução sem simulação."""

    cenario = Cenario(tmp_path)
    cenario.semear_mensagem(
        canal=Canal.SMS,
        tentativas=((True, False), (True, False), (True, False)),
        estado=EstadoMensagem.FALHOU_CONTEUDO,
        nome="Conteúdo",
    )
    cenario.semear_mensagem(
        canal=Canal.EMAIL,
        tentativas=(),
        estado=EstadoMensagem.FALHOU_INTEGRACAO_IA,
        nome="Integração",
    )

    decisao = cenario.decidir()

    assert decisao.aplicadas == ()
    assert decisao.estado is EstadoExecucao.CONCLUIDA
    assert cenario.estado_execucao() is EstadoExecucao.CONCLUIDA


def test_com_ao_menos_uma_aprovada_a_execucao_vai_para_aguardando_confirmacao(
    tmp_path: Path,
) -> None:
    """REVISAO-14: o lote consolidado leva a execução a `aguardando_confirmacao` contendo só
    o que o crítico e Marina aprovaram — um item aprovado pelo crítico e rejeitado por Marina
    fica de fora."""

    cenario = Cenario(tmp_path)
    aprovada = cenario.semear_mensagem(canal=Canal.SMS, nome="Aprovada pelos dois")
    rejeitada = cenario.semear_mensagem(canal=Canal.EMAIL, nome="Rejeitada por Marina")
    em_excecao = cenario.semear_mensagem(
        canal=Canal.WHATSAPP,
        tentativas=((True, False), (True, False), (True, False)),
        estado=EstadoMensagem.FALHOU_CONTEUDO,
        nome="Exceção",
    )

    decisao = cenario.decidir(
        DecisaoRequisitada(
            aprovada, cenario.versao_de(aprovada), ResultadoDecisaoHumana.APROVAR, None
        ),
        DecisaoRequisitada(
            rejeitada,
            cenario.versao_de(rejeitada),
            ResultadoDecisaoHumana.REJEITAR,
            "Aprovada pelo crítico, mas inadequada para este público.",
        ),
    )

    assert decisao.estado is EstadoExecucao.AGUARDANDO_CONFIRMACAO
    assert decisao.mensagens_aprovadas == (aprovada,)
    assert em_excecao not in decisao.mensagens_aprovadas
    assert cenario.estado_execucao() is EstadoExecucao.AGUARDANDO_CONFIRMACAO
    lote = cenario.servico.obter_lote(EXECUCAO_ID)
    assert lote is not None
    estados = {item.mensagem_id: item.estado for item in lote.itens}
    assert estados[aprovada] is EstadoMensagem.APROVADA
    assert estados[rejeitada] is EstadoMensagem.REJEITADA


def test_agregado_nao_avanca_enquanto_uma_revisavel_segue_sem_decisao(
    tmp_path: Path,
) -> None:
    """REVISAO-10: com uma mensagem ainda em `aguardando_revisao`, o lote continua aberto —
    nenhuma conclusão nem confirmação é liberada."""

    cenario = Cenario(tmp_path)
    decidida = cenario.semear_mensagem(canal=Canal.SMS, nome="Decidida")
    cenario.semear_mensagem(canal=Canal.EMAIL, nome="Ainda pendente")

    decisao = cenario.decidir(
        DecisaoRequisitada(
            decidida, cenario.versao_de(decidida), ResultadoDecisaoHumana.APROVAR, None
        )
    )

    assert decisao.estado is EstadoExecucao.AGUARDANDO_REVISAO
    assert cenario.estado_execucao() is EstadoExecucao.AGUARDANDO_REVISAO


def test_ciclo_completo_de_regeneracao_humana_devolve_o_lote_a_revisao(
    tmp_path: Path,
) -> None:
    """REVISAO-08/REVISAO-10/REVISAO-11, ciclo inteiro: a decisão devolve a mensagem a
    `gerando` e o agregado a `processando_mensagens`; a nova tentativa roda pela mesma
    reentrada de 3.4; e só quando ela alcança seu novo terminal o agregado volta a
    `aguardando_revisao` — exigindo então uma decisão humana própria da versão nova."""

    cenario = Cenario(tmp_path)
    regenerada = cenario.semear_mensagem(canal=Canal.SMS, nome="Regenerada")
    outra = cenario.semear_mensagem(canal=Canal.EMAIL, nome="Aprovada depois")

    primeira = cenario.decidir(
        DecisaoRequisitada(
            regenerada,
            cenario.versao_de(regenerada),
            ResultadoDecisaoHumana.REGENERAR,
            "Quero outra formulação.",
        )
    )

    assert primeira.estado is EstadoExecucao.PROCESSANDO_MENSAGENS
    registro = cenario.mensagens.obter(regenerada)
    assert registro is not None
    assert registro.estado is EstadoMensagem.AGUARDANDO_REVISAO
    assert registro.tentativa_atual == 2
    assert cenario.redator.chamadas == 1
    versoes = cenario.mensagens.listar_versoes(regenerada)
    assert [versao.numero_tentativa for versao in versoes] == [1, 2]
    assert versoes[-1].conteudo.corpo == "Texto regenerado 1."
    assert cenario.estado_execucao() is EstadoExecucao.AGUARDANDO_REVISAO

    decisoes_da_regeneracao = cenario.decisoes.obter_por_mensagem(regenerada)
    assert [item.resultado for item in decisoes_da_regeneracao] == [
        ResultadoDecisaoHumana.REGENERAR
    ]
    assert decisoes_da_regeneracao[0].versao_mensagem_id == versoes[0].id

    segunda = cenario.decidir(
        DecisaoRequisitada(
            regenerada,
            cenario.versao_de(regenerada),
            ResultadoDecisaoHumana.APROVAR,
            None,
        ),
        DecisaoRequisitada(
            outra, cenario.versao_de(outra), ResultadoDecisaoHumana.APROVAR, None
        ),
        chave="chave-2",
        hash_requisicao="hash-2",
    )

    assert segunda.estado is EstadoExecucao.AGUARDANDO_CONFIRMACAO
    assert set(segunda.mensagens_aprovadas) == {regenerada, outra}
    assert [item.resultado for item in cenario.decisoes.obter_por_mensagem(regenerada)] == [
        ResultadoDecisaoHumana.REGENERAR,
        ResultadoDecisaoHumana.APROVAR,
    ]
    assert cenario.decisoes.obter_por_mensagem(regenerada)[-1].versao_mensagem_id == (
        versoes[-1].id
    )


def test_guarda_nao_libera_confirmacao_com_regeneracao_ainda_em_curso(
    tmp_path: Path,
) -> None:
    """REVISAO-10: enquanto a regeneração não termina, o agregado permanece em
    `processando_mensagens` mesmo com todas as outras mensagens já decididas e aprovadas —
    nenhuma confirmação é liberada antes da guarda ser satisfeita."""

    cenario = Cenario(tmp_path, retomar_automaticamente=False)
    regenerada = cenario.semear_mensagem(canal=Canal.SMS, nome="Regenerada")
    aprovada = cenario.semear_mensagem(canal=Canal.EMAIL, nome="Aprovada")

    decisao = cenario.decidir(
        DecisaoRequisitada(
            aprovada, cenario.versao_de(aprovada), ResultadoDecisaoHumana.APROVAR, None
        ),
        DecisaoRequisitada(
            regenerada,
            cenario.versao_de(regenerada),
            ResultadoDecisaoHumana.REGENERAR,
            "Refazer antes de confirmar.",
        ),
    )

    assert decisao.estado is EstadoExecucao.PROCESSANDO_MENSAGENS
    assert cenario.estado_execucao() is EstadoExecucao.PROCESSANDO_MENSAGENS
    assert cenario.estado_de(regenerada) is EstadoMensagem.GERANDO
    assert cenario.estado_de(aprovada) is EstadoMensagem.APROVADA

    asyncio.run(cenario.geracao.retomar_mensagens_pendentes(EXECUCAO_ID))

    assert cenario.estado_de(regenerada) is EstadoMensagem.AGUARDANDO_REVISAO
    assert cenario.estado_execucao() is EstadoExecucao.AGUARDANDO_REVISAO
