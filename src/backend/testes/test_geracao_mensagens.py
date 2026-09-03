"""Testes da geração automática do lote (GERAR-04, 05, 06, 10, 11, 12).

O repositório de mensagens é o real, sobre um banco temporário com as migrações aplicadas:
a garantia de não duplicar mensagem é a `UNIQUE (elegibilidade_id, canal)` do próprio banco
(AD-010), então testá-la só com dublê provaria pouco. O grafo também é o real, compilado; só
o redator é falso, para que nenhum teste toque a OpenAI.
"""

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from central_preventiva.adaptadores.ia.agente_redator import RespostaRedator
from central_preventiva.adaptadores.ia.verificador_disponibilidade_openai import (
    ResultadoDisponibilidade,
)
from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.adaptadores.persistencia.repositorio_avaliacoes_criticas import (
    RepositorioAvaliacoesCriticas,
)
from central_preventiva.adaptadores.persistencia.repositorio_contextos_agente import (
    RegistroContextoAgente,
)
from central_preventiva.adaptadores.persistencia.repositorio_elegibilidade import (
    ContagemElegibilidade,
    RegistroElegibilidade,
)
from central_preventiva.adaptadores.persistencia.repositorio_execucao_preventiva import (
    SnapshotExecucao,
)
from central_preventiva.adaptadores.persistencia.repositorio_mensagens import (
    RepositorioMensagens,
)
from central_preventiva.aplicacao.geracao_mensagens import (
    IMPACTO_ITEM_SEM_MENSAGEM,
    PortasGeracaoMensagens,
    ServicoGeracaoMensagens,
)
from central_preventiva.aplicacao.grafos.geracao_mensagem import (
    DependenciasGrafo,
    construir_grafo,
)
from central_preventiva.aplicacao.portas_persistencia import RespostaRegistrada
from central_preventiva.aplicacao.preflight_ia import (
    PortasPreflightIA,
    ServicoPreflightIA,
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
from central_preventiva.dominio.estados_execucao import EstadoExecucao
from central_preventiva.dominio.estados_mensagem import EstadoMensagem
from central_preventiva.dominio.evento_meteorologico import (
    EventoMeteorologico,
    ProvenienciaEvento,
    TipoEventoMeteorologico,
)
from central_preventiva.dominio.montador_contexto_agente import (
    ContextoAgente,
    MontadorContextoAgente,
)
from central_preventiva.dominio.validador_saida_canal import (
    Canal,
    LimitesCanal,
    SaidaCanal,
    ValidadorSaidaCanal,
)

EXECUCAO_ID = UUID("11111111-1111-1111-1111-111111111111")
EVENTO_ID = UUID("22222222-2222-2222-2222-222222222222")
REGRA_ID = UUID("33333333-3333-3333-3333-333333333333")
VERSAO_PROMPT = "v1"

LIMITES = LimitesCanal(whatsapp=1024, sms=160, assunto_email=78, corpo_email=2000)

CORPO_VALIDO = "Chuva forte prevista hoje na sua região. Evite áreas alagadas."

EVENTO = EventoMeteorologico(
    id=EVENTO_ID,
    tipo=TipoEventoMeteorologico.CHUVA_INTENSA,
    area="9990001",
    periodo_inicio=datetime(2026, 9, 3, 12, 0, tzinfo=UTC),
    periodo_fim=datetime(2026, 9, 3, 18, 0, tzinfo=UTC),
    intensidade=62.5,
    proveniencia=ProvenienciaEvento.REAL_INMET,
    instante_observado=datetime(2026, 9, 3, 18, 0, tzinfo=UTC),
)


def contexto_de(canal: str) -> ContextoAgente:
    """Contexto mínimo já montado por 3.1 para o canal informado."""

    return ContextoAgente(
        evento="chuva_intensa",
        localizacao_aproximada="9990001",
        coberturas_relevantes=("alagamento",),
        canal=canal,
        orientacoes_seguranca=("Evite áreas alagadas.",),
    )


def registro(
    canal: str = "sms",
    elegivel: bool = True,
    id_registro: UUID | None = None,
    execucao_id: UUID = EXECUCAO_ID,
) -> RegistroElegibilidade:
    """Monta uma linha de elegibilidade já persistida, no formato que 2.5 devolve."""

    return RegistroElegibilidade(
        id=id_registro if id_registro is not None else uuid4(),
        execucao_id=execucao_id,
        evento_id=EVENTO_ID,
        regra_id=REGRA_ID,
        regra_versao=1,
        segurado_id=uuid4(),
        nome_segurado="Pessoa Teste",
        apolice_id=uuid4(),
        codigo_ibge_area="9990001",
        elegivel=elegivel,
        criterios=(
            Criterio(OPERANDO_AREA_AFETADA, "9990001", True, "Área corresponde."),
            Criterio(OPERANDO_COBERTURA_EXIGIDA, "alagamento", True, "Possui cobertura."),
        ),
        canal=canal,
        justificativa="Atende integralmente aos critérios da regra ativa.",
        criado_em=datetime(2026, 9, 3, 19, 0, tzinfo=UTC),
    )


class ElegibilidadesFalsas:
    """Repositório de elegibilidades dublê, filtrando pela execução consultada."""

    def __init__(self, registros: list[RegistroElegibilidade]) -> None:
        self.registros = registros

    def listar_por_execucao(self, execucao_id: UUID) -> list[RegistroElegibilidade]:
        return [item for item in self.registros if item.execucao_id == execucao_id]

    def contar_por_execucao(self, execucao_id: UUID) -> ContagemElegibilidade:
        proprios = self.listar_por_execucao(execucao_id)
        return ContagemElegibilidade(
            incluidos=sum(1 for item in proprios if item.elegivel),
            excluidos=sum(1 for item in proprios if not item.elegivel),
        )

    def copiar_para_execucao(
        self, execucao_origem_id: UUID, nova_execucao_id: UUID, conexao: Any = None
    ) -> int:
        return 0


class ContextosFalsos:
    """Repositório de contextos dublê: só resolve os itens programados pelo teste."""

    def __init__(self, contextos: dict[UUID, ContextoAgente] | None = None) -> None:
        self.contextos = dict(contextos or {})

    def obter_por_elegibilidade(self, elegibilidade_id: UUID) -> RegistroContextoAgente | None:
        contexto = self.contextos.get(elegibilidade_id)
        if contexto is None:
            return None
        return RegistroContextoAgente(
            id=uuid4(),
            execucao_id=EXECUCAO_ID,
            elegibilidade_id=elegibilidade_id,
            contexto=contexto,
            categorias_usadas=(),
            categorias_nao_usadas=(),
        )

    def salvar(
        self,
        execucao_id: UUID,
        elegibilidade_id: UUID,
        contexto: ContextoAgente,
        categorias_usadas: tuple[str, ...],
        categorias_nao_usadas: tuple[str, ...],
    ) -> UUID:
        self.contextos[elegibilidade_id] = contexto
        return uuid4()

    def listar_por_execucao(self, execucao_id: UUID) -> list[RegistroContextoAgente]:
        registros = [self.obter_por_elegibilidade(item) for item in self.contextos]
        return [item for item in registros if item is not None]


class ExcecoesEspias:
    """Repositório de exceções dublê: guarda cada registro para inspeção do teste."""

    def __init__(self) -> None:
        self.registradas: list[tuple[UUID, str, int, str]] = []

    def registrar(self, execucao_id: UUID, causa: str, tentativas: int, impacto: str) -> None:
        self.registradas.append((execucao_id, causa, tentativas, impacto))


class RedatorFalso:
    """Dublê do agente redator: uma resposta por chamada, ou erro de transporte."""

    def __init__(
        self,
        respostas: list[RespostaRedator] | None = None,
        erros: dict[str, Exception] | None = None,
    ) -> None:
        self._respostas = respostas
        self._erros = erros or {}
        self.canais_chamados: list[Canal] = []

    @property
    def modelo(self) -> str:
        return "gpt-4o-mini"

    async def gerar(self, contexto: ContextoAgente, canal: Canal) -> RespostaRedator:
        self.canais_chamados.append(canal)
        erro = self._erros.get(contexto.localizacao_aproximada)
        if erro is not None:
            raise erro
        if self._respostas is None:
            corpo = f"{CORPO_VALIDO} ({canal.value}, {len(self.canais_chamados)})"
            assunto = "Alerta preventivo" if canal is Canal.EMAIL else None
            return RespostaRedator(SaidaCanal(corpo=corpo, assunto=assunto), 100, 30)
        return self._respostas[min(len(self.canais_chamados) - 1, len(self._respostas) - 1)]


class CriticoFalso:
    """Dublê do agente crítico: uma avaliação por chamada, ou erro de transporte."""

    def __init__(
        self,
        avaliacoes: list[AvaliacaoCritica | None] | None = None,
        erro: Exception | None = None,
    ) -> None:
        self._avaliacoes: list[AvaliacaoCritica | None] = (
            avaliacoes if avaliacoes is not None else [AvaliacaoCritica(True, ())]
        )
        self._erro = erro
        self.chamadas = 0

    @property
    def modelo(self) -> str:
        return "gpt-4o-mini"

    async def avaliar(
        self, conteudo: SaidaCanal, canal: Canal, contexto: ContextoAgente
    ) -> AvaliacaoCritica | None:
        self.chamadas += 1
        if self._erro is not None:
            raise self._erro
        return self._avaliacoes[min(self.chamadas - 1, len(self._avaliacoes) - 1)]


async def sem_espera(_: float) -> None:
    """Substitui o backoff real para que o teste não durma de fato."""


class Cenario:
    """Reúne o caso de uso real, o repositório real e os dublês do teste."""

    def __init__(
        self,
        registros: list[RegistroElegibilidade],
        tmp_path: Path,
        redator: RedatorFalso | None = None,
        contextos: dict[UUID, ContextoAgente] | None = None,
        critico: CriticoFalso | None = None,
    ) -> None:
        caminho = tmp_path / "central_preventiva.duckdb"
        ExecutorMigracoes(caminho).aplicar_pendentes()
        self.redator = redator if redator is not None else RedatorFalso()
        self.critico = critico if critico is not None else CriticoFalso()
        self.mensagens = RepositorioMensagens(caminho)
        self.avaliacoes = RepositorioAvaliacoesCriticas(caminho)
        self.elegibilidades = ElegibilidadesFalsas(registros)
        self.contextos = ContextosFalsos(
            contextos
            if contextos is not None
            else {item.id: contexto_de(item.canal) for item in registros}
        )
        self.excecoes = ExcecoesEspias()
        self.servico = ServicoGeracaoMensagens(
            PortasGeracaoMensagens(
                elegibilidades=self.elegibilidades,
                contextos=self.contextos,
                mensagens=self.mensagens,
                avaliacoes=self.avaliacoes,
                excecoes=self.excecoes,
                grafo=construir_grafo(
                    DependenciasGrafo(
                        redator=self.redator,
                        validador=ValidadorSaidaCanal(LIMITES),
                        critico=self.critico,
                        esperar=sem_espera,
                    )
                ),
                versao_prompt=VERSAO_PROMPT,
            )
        )

    def gerar_lote(self, execucao_id: UUID = EXECUCAO_ID) -> None:
        """Dispara a geração do lote inteiro, sem nenhuma ação por mensagem."""

        asyncio.run(self.servico.gerar_lote(execucao_id))


def test_duas_elegibilidades_incluidas_geram_duas_mensagens_sem_acao_manual(
    tmp_path: Path,
) -> None:
    """GERAR-04: um único disparo de lote gera a mensagem de cada item, em seu canal."""

    primeiro = registro(canal="sms")
    segundo = registro(canal="email")
    cenario = Cenario([primeiro, segundo], tmp_path)

    cenario.gerar_lote()

    mensagens = cenario.mensagens.listar_por_execucao(EXECUCAO_ID)
    assert len(mensagens) == 2
    assert {(item.elegibilidade_id, item.canal) for item in mensagens} == {
        (primeiro.id, Canal.SMS),
        (segundo.id, Canal.EMAIL),
    }
    assert {item.estado for item in mensagens} == {EstadoMensagem.AGUARDANDO_REVISAO}
    assert cenario.redator.canais_chamados == [Canal.SMS, Canal.EMAIL]


def test_mensagem_gerada_permanece_associada_a_toda_a_origem(tmp_path: Path) -> None:
    """GERAR-05: execução, elegibilidade, canal — e, por ela, evento, regra, segurado, apólice."""

    incluido = registro(canal="whatsapp")
    cenario = Cenario([incluido], tmp_path)

    cenario.gerar_lote()

    mensagem = cenario.mensagens.listar_por_execucao(EXECUCAO_ID)[0]
    assert mensagem.execucao_id == EXECUCAO_ID
    assert mensagem.elegibilidade_id == incluido.id
    assert mensagem.canal is Canal.WHATSAPP
    origem = cenario.elegibilidades.registros[0]
    assert origem.id == mensagem.elegibilidade_id
    assert origem.evento_id == EVENTO_ID
    assert origem.regra_id == REGRA_ID
    assert origem.segurado_id == incluido.segurado_id
    assert origem.apolice_id == incluido.apolice_id


def test_item_excluido_do_publico_nao_gera_mensagem(tmp_path: Path) -> None:
    """GERAR-04: só o público incluído recebe mensagem."""

    incluido = registro(canal="sms")
    excluido = registro(canal="email", elegivel=False)
    cenario = Cenario([incluido, excluido], tmp_path)

    cenario.gerar_lote()

    mensagens = cenario.mensagens.listar_por_execucao(EXECUCAO_ID)
    assert [item.elegibilidade_id for item in mensagens] == [incluido.id]


def test_item_sem_contexto_minimo_e_pulado_sem_chamar_a_openai(tmp_path: Path) -> None:
    """Edge case da spec: item sem contexto falha isolado, sem gerar com contexto incompleto."""

    com_contexto = registro(canal="sms")
    sem_contexto = registro(canal="email")
    cenario = Cenario(
        [sem_contexto, com_contexto],
        tmp_path,
        contextos={com_contexto.id: contexto_de("sms")},
    )

    cenario.gerar_lote()

    mensagens = cenario.mensagens.listar_por_execucao(EXECUCAO_ID)
    assert [item.elegibilidade_id for item in mensagens] == [com_contexto.id]
    assert cenario.redator.canais_chamados == [Canal.SMS]
    assert cenario.excecoes.registradas == [
        (EXECUCAO_ID, f"contexto_ausente:{sem_contexto.id}", 1, IMPACTO_ITEM_SEM_MENSAGEM)
    ]


def test_saida_valida_persiste_a_versao_e_avanca_ate_aguardando_revisao(tmp_path: Path) -> None:
    """GERAR-10 + CRIT-05: versão inicial, duração, modelo, prompt e métricas persistidos;
    com o crítico aprovando, a mensagem atravessa `criticando` e para em
    `aguardando_revisao` (3.3 estende o estado final que 3.2 deixava em `criticando`)."""

    incluido = registro(canal="sms")
    cenario = Cenario(
        [incluido],
        tmp_path,
        RedatorFalso([RespostaRedator(SaidaCanal(corpo=CORPO_VALIDO), 210, 64)]),
    )

    cenario.gerar_lote()

    mensagem = cenario.mensagens.listar_por_execucao(EXECUCAO_ID)[0]
    assert mensagem.estado is EstadoMensagem.AGUARDANDO_REVISAO
    versao = cenario.mensagens.obter_versao_atual(mensagem.id)
    assert versao is not None
    assert versao.numero_tentativa == 1
    assert versao.conteudo == SaidaCanal(corpo=CORPO_VALIDO)
    assert versao.valida is True
    assert versao.motivo_invalidez is None
    assert versao.modelo == "gpt-4o-mini"
    assert versao.versao_prompt == VERSAO_PROMPT
    assert versao.tokens_entrada == 210
    assert versao.tokens_saida == 64
    assert versao.duracao_ms > 0


def test_saida_acima_do_limite_permanece_em_gerando_com_motivo_persistido(
    tmp_path: Path,
) -> None:
    """GERAR-09: saída inválida não avança para `criticando` e registra o motivo."""

    incluido = registro(canal="sms")
    cenario = Cenario(
        [incluido],
        tmp_path,
        RedatorFalso([RespostaRedator(SaidaCanal(corpo="a" * 161), 90, 200)]),
    )

    cenario.gerar_lote()

    mensagem = cenario.mensagens.listar_por_execucao(EXECUCAO_ID)[0]
    assert mensagem.estado is EstadoMensagem.GERANDO
    versao = cenario.mensagens.obter_versao_atual(mensagem.id)
    assert versao is not None
    assert versao.valida is False
    assert versao.motivo_invalidez == "limite_excedido:corpo:161:160"


def test_saida_vazia_permanece_em_gerando_com_campo_obrigatorio_ausente(
    tmp_path: Path,
) -> None:
    """Edge case da spec: corpo em branco é campo obrigatório ausente, não sucesso."""

    incluido = registro(canal="sms")
    cenario = Cenario(
        [incluido], tmp_path, RedatorFalso([RespostaRedator(SaidaCanal(corpo="  "), 1, 1)])
    )

    cenario.gerar_lote()

    mensagem = cenario.mensagens.listar_por_execucao(EXECUCAO_ID)[0]
    assert mensagem.estado is EstadoMensagem.GERANDO
    versao = cenario.mensagens.obter_versao_atual(mensagem.id)
    assert versao is not None
    assert versao.valida is False
    assert versao.motivo_invalidez == "campo_obrigatorio_ausente:corpo"


def test_falha_de_transporte_isola_o_item_e_o_lote_continua(tmp_path: Path) -> None:
    """AD-8: falha da OpenAI depois da preparação afeta só a mensagem, não o lote."""

    com_falha = registro(canal="sms")
    seguinte = registro(canal="email")
    cenario = Cenario(
        [com_falha, seguinte],
        tmp_path,
        RedatorFalso(erros={"falha": TimeoutError("conexão expirou")}),
        contextos={
            com_falha.id: ContextoAgente(
                evento="chuva_intensa",
                localizacao_aproximada="falha",
                coberturas_relevantes=("alagamento",),
                canal="sms",
                orientacoes_seguranca=("Evite áreas alagadas.",),
            ),
            seguinte.id: contexto_de("email"),
        },
    )

    cenario.gerar_lote()

    por_item = {
        item.elegibilidade_id: item
        for item in cenario.mensagens.listar_por_execucao(EXECUCAO_ID)
    }
    assert por_item[com_falha.id].estado is EstadoMensagem.FALHOU_INTEGRACAO_IA
    assert por_item[seguinte.id].estado is EstadoMensagem.AGUARDANDO_REVISAO
    assert cenario.mensagens.obter_versao_atual(por_item[com_falha.id].id) is None
    causas = [causa for _, causa, _, _ in cenario.excecoes.registradas]
    assert causas == [f"falha_integracao_ia:{com_falha.id}:TimeoutError: conexão expirou"]


def test_dois_itens_no_mesmo_canal_geram_mensagens_proprias(tmp_path: Path) -> None:
    """Edge case da spec: mesmo canal e evento, sem reaproveitar conteúdo entre itens."""

    primeiro = registro(canal="whatsapp")
    segundo = registro(canal="whatsapp")
    cenario = Cenario([primeiro, segundo], tmp_path)

    cenario.gerar_lote()

    mensagens = cenario.mensagens.listar_por_execucao(EXECUCAO_ID)
    assert {item.elegibilidade_id for item in mensagens} == {primeiro.id, segundo.id}
    conteudos = {
        cenario.mensagens.obter_versao_atual(item.id).conteudo.corpo  # pyright: ignore[reportOptionalMemberAccess]
        for item in mensagens
    }
    assert len(conteudos) == 2


def test_reinvocar_o_lote_nao_duplica_mensagem_nem_regera(tmp_path: Path) -> None:
    """GERAR-06, GERAR-11, GERAR-12: a `UNIQUE` do banco torna a reinvocação um no-op."""

    primeiro = registro(canal="sms")
    segundo = registro(canal="email")
    cenario = Cenario([primeiro, segundo], tmp_path)
    cenario.gerar_lote()
    ids_iniciais = {item.id for item in cenario.mensagens.listar_por_execucao(EXECUCAO_ID)}

    cenario.gerar_lote()

    mensagens = cenario.mensagens.listar_por_execucao(EXECUCAO_ID)
    assert {item.id for item in mensagens} == ids_iniciais
    assert len(mensagens) == 2
    assert cenario.redator.canais_chamados == [Canal.SMS, Canal.EMAIL]
    assert {item.estado for item in mensagens} == {EstadoMensagem.AGUARDANDO_REVISAO}


def test_canal_nao_suportado_e_isolado_como_excecao_do_item(tmp_path: Path) -> None:
    """A falha de um item nunca interrompe o lote, nem com canal fora dos três suportados."""

    invalido = registro(canal="pombo-correio")
    valido = registro(canal="sms")
    cenario = Cenario(
        [invalido, valido],
        tmp_path,
        contextos={invalido.id: contexto_de("sms"), valido.id: contexto_de("sms")},
    )

    cenario.gerar_lote()

    mensagens = cenario.mensagens.listar_por_execucao(EXECUCAO_ID)
    assert [item.elegibilidade_id for item in mensagens] == [valido.id]
    assert cenario.excecoes.registradas == [
        (
            EXECUCAO_ID,
            f"canal_desconhecido:{invalido.id}:pombo-correio",
            1,
            IMPACTO_ITEM_SEM_MENSAGEM,
        )
    ]


class VerificadorDisponivel:
    """Verificador dublê que sempre confirma a disponibilidade da OpenAI."""

    async def verificar(self) -> ResultadoDisponibilidade:
        return ResultadoDisponibilidade(disponivel=True, causa=None)


class ExecucoesFalsas:
    """Repositório de execuções dublê, com transição e marcos em memória."""

    def __init__(self, snapshot: SnapshotExecucao) -> None:
        self.snapshots = {snapshot.id: snapshot}
        self.marcos: list[tuple[UUID, str, str | None]] = []

    def buscar(self, execucao_id: UUID) -> SnapshotExecucao | None:
        return self.snapshots.get(execucao_id)

    def transicionar(
        self, execucao_id: UUID, versao_esperada: int, novo_estado: EstadoExecucao
    ) -> None:
        atual = self.snapshots[execucao_id]
        self.snapshots[execucao_id] = SnapshotExecucao(
            id=atual.id, estado=novo_estado, versao=atual.versao + 1
        )

    def registrar_marco(self, execucao_id: UUID, marco: str, causa: str | None = None) -> None:
        self.marcos.append((execucao_id, marco, causa))

    def criar_correlacionada(
        self, estado_inicial: EstadoExecucao, execucao_origem_id: UUID, apos_criar: Any = None
    ) -> UUID:
        raise NotImplementedError


class EventosFalsos:
    """Repositório de eventos dublê, resolvendo apenas o evento do cenário."""

    def buscar_por_id(self, id: UUID) -> EventoMeteorologico | None:
        return EVENTO if id == EVENTO_ID else None


class IdempotenciaFalsa:
    """Armazenamento de idempotência dublê, com a semântica do repositório real."""

    def __init__(self) -> None:
        self.registros: dict[tuple[str, str], RespostaRegistrada] = {}

    def buscar(self, chave: str, operacao: str) -> RespostaRegistrada | None:
        return self.registros.get((chave, operacao))

    def registrar(
        self, chave: str, operacao: str, hash_requisicao: str, status: int, corpo: str
    ) -> None:
        self.registros[(chave, operacao)] = RespostaRegistrada(
            hash_requisicao=hash_requisicao, status=status, corpo=corpo
        )


def test_preflight_bem_sucedido_aciona_a_geracao_do_lote_automaticamente(
    tmp_path: Path,
) -> None:
    """GERAR-04.1: entrar em `processando_mensagens` aciona o redator de todo o público.

    Marina não dispara nada por mensagem: o mesmo comando que confirma a disponibilidade da
    OpenAI (3.1) deixa as mensagens do lote geradas e persistidas.
    """

    primeiro = registro(canal="sms")
    segundo = registro(canal="email")
    cenario = Cenario([primeiro, segundo], tmp_path)
    execucoes = ExecucoesFalsas(
        SnapshotExecucao(id=EXECUCAO_ID, estado=EstadoExecucao.AGUARDANDO_GERACAO, versao=1)
    )
    preflight = ServicoPreflightIA(
        PortasPreflightIA(
            verificador=VerificadorDisponivel(),
            montador=MontadorContextoAgente(),
            execucoes=execucoes,
            excecoes=cenario.excecoes,
            elegibilidades=cenario.elegibilidades,
            contextos=cenario.contextos,
            eventos=EventosFalsos(),
            idempotencia=IdempotenciaFalsa(),
            esperar=sem_espera,
            acionar_geracao=cenario.servico.gerar_lote,
        )
    )

    resultado = asyncio.run(preflight.preparar(EXECUCAO_ID, 1, "chave-1", "hash-1"))

    assert resultado.estado == EstadoExecucao.PROCESSANDO_MENSAGENS
    mensagens = cenario.mensagens.listar_por_execucao(EXECUCAO_ID)
    assert {(item.elegibilidade_id, item.canal) for item in mensagens} == {
        (primeiro.id, Canal.SMS),
        (segundo.id, Canal.EMAIL),
    }
    assert {item.estado for item in mensagens} == {EstadoMensagem.AGUARDANDO_REVISAO}


def test_preflight_bloqueado_nao_aciona_nenhuma_geracao(tmp_path: Path) -> None:
    """PREFL-03: indisponibilidade termina a execução sem nenhuma chamada de geração."""

    incluido = registro(canal="sms")
    cenario = Cenario([incluido], tmp_path)
    execucoes = ExecucoesFalsas(
        SnapshotExecucao(id=EXECUCAO_ID, estado=EstadoExecucao.AGUARDANDO_GERACAO, versao=1)
    )

    class VerificadorIndisponivel:
        async def verificar(self) -> ResultadoDisponibilidade:
            return ResultadoDisponibilidade(disponivel=False, causa="A OpenAI foi recusada.")

    preflight = ServicoPreflightIA(
        PortasPreflightIA(
            verificador=VerificadorIndisponivel(),
            montador=MontadorContextoAgente(),
            execucoes=execucoes,
            excecoes=cenario.excecoes,
            elegibilidades=cenario.elegibilidades,
            contextos=cenario.contextos,
            eventos=EventosFalsos(),
            idempotencia=IdempotenciaFalsa(),
            esperar=sem_espera,
            acionar_geracao=cenario.servico.gerar_lote,
        )
    )

    resultado = asyncio.run(preflight.preparar(EXECUCAO_ID, 1, "chave-2", "hash-2"))

    assert resultado.estado == EstadoExecucao.FALHOU_PREPARACAO_IA
    assert cenario.mensagens.listar_por_execucao(EXECUCAO_ID) == []
    assert cenario.redator.canais_chamados == []


def _versao_id(cenario: Cenario) -> UUID:
    """Identificador da versão atual da única mensagem do cenário."""

    mensagem = cenario.mensagens.listar_por_execucao(EXECUCAO_ID)[0]
    versao = cenario.mensagens.obter_versao_atual(mensagem.id)
    assert versao is not None
    return versao.id


def test_aprovacao_do_critico_persiste_a_avaliacao_e_avanca_para_aguardando_revisao(
    tmp_path: Path,
) -> None:
    """CRIT-05: aprovada pelo crítico e pelos validadores, a mensagem avança para
    `aguardando_revisao`, com a avaliação agêntica persistida à parte da versão."""

    incluido = registro(canal="sms")
    cenario = Cenario([incluido], tmp_path, critico=CriticoFalso([AvaliacaoCritica(True, ())]))

    cenario.gerar_lote()

    mensagem = cenario.mensagens.listar_por_execucao(EXECUCAO_ID)[0]
    assert mensagem.estado is EstadoMensagem.AGUARDANDO_REVISAO
    avaliacao = cenario.avaliacoes.obter_por_versao(_versao_id(cenario))
    assert avaliacao is not None
    assert avaliacao.avaliacao == AvaliacaoCritica(aprovada=True, motivos=())
    assert avaliacao.agente == "critico"
    assert avaliacao.modelo == "gpt-4o-mini"
    assert avaliacao.duracao_ms > 0
    assert cenario.excecoes.registradas == []


def test_reprovacao_do_critico_persiste_motivos_e_mensagem_permanece_em_criticando(
    tmp_path: Path,
) -> None:
    """CRIT-06: os motivos ficam estruturados e associados à versão avaliada, e o item
    permanece disponível para a próxima tentativa automática (3.4) — não avança."""

    incluido = registro(canal="sms")
    motivos = (
        MotivoCritica(CategoriaCritica.TOM, "O texto usa tom alarmista, não preventivo."),
    )
    cenario = Cenario(
        [incluido], tmp_path, critico=CriticoFalso([AvaliacaoCritica(False, motivos)])
    )

    cenario.gerar_lote()

    mensagem = cenario.mensagens.listar_por_execucao(EXECUCAO_ID)[0]
    assert mensagem.estado is EstadoMensagem.CRITICANDO
    avaliacao = cenario.avaliacoes.obter_por_versao(_versao_id(cenario))
    assert avaliacao is not None
    assert avaliacao.avaliacao == AvaliacaoCritica(aprovada=False, motivos=motivos)
    assert avaliacao.avaliacao.motivos[0].categoria is CategoriaCritica.TOM
    assert (
        avaliacao.avaliacao.motivos[0].justificativa
        == "O texto usa tom alarmista, não preventivo."
    )


def test_saida_invalida_do_critico_nao_persiste_avaliacao_nem_avanca(tmp_path: Path) -> None:
    """CRIT-07: saída não interpretável é falha da tentativa — nenhuma avaliação
    persistida, nenhuma aprovação, e a mensagem não alcança `aguardando_revisao`."""

    incluido = registro(canal="sms")
    cenario = Cenario([incluido], tmp_path, critico=CriticoFalso([None]))

    cenario.gerar_lote()

    mensagem = cenario.mensagens.listar_por_execucao(EXECUCAO_ID)[0]
    assert mensagem.estado is EstadoMensagem.CRITICANDO
    assert mensagem.estado is not EstadoMensagem.AGUARDANDO_REVISAO
    assert cenario.avaliacoes.obter_por_versao(_versao_id(cenario)) is None


def test_falha_de_transporte_do_critico_leva_a_falhou_integracao_ia_sem_terminal_novo(
    tmp_path: Path,
) -> None:
    """Edge case da spec: transporte do crítico segue o padrão de `falhou_integracao_ia`
    já estabelecido em 3.2 para o redator, com exceção operacional registrada."""

    incluido = registro(canal="sms")
    cenario = Cenario(
        [incluido], tmp_path, critico=CriticoFalso(erro=TimeoutError("conexão expirou"))
    )

    cenario.gerar_lote()

    mensagem = cenario.mensagens.listar_por_execucao(EXECUCAO_ID)[0]
    assert mensagem.estado is EstadoMensagem.FALHOU_INTEGRACAO_IA
    assert cenario.avaliacoes.obter_por_versao(_versao_id(cenario)) is None
    assert cenario.excecoes.registradas == [
        (
            EXECUCAO_ID,
            f"falha_integracao_ia_critica:{incluido.id}:TimeoutError: conexão expirou",
            1,
            IMPACTO_ITEM_SEM_MENSAGEM,
        )
    ]


def test_mensagem_reprovada_deterministicamente_nunca_recebe_avaliacao_critica(
    tmp_path: Path,
) -> None:
    """CRIT-04: a reprovação determinística de 3.2 prevalece — a mensagem não sai de
    `gerando`, o crítico não é chamado e nenhuma avaliação é persistida, mesmo com um
    crítico configurado para aprovar tudo."""

    incluido = registro(canal="sms")
    cenario = Cenario(
        [incluido],
        tmp_path,
        RedatorFalso([RespostaRedator(SaidaCanal(corpo="a" * 161), 90, 200)]),
        critico=CriticoFalso([AvaliacaoCritica(True, ())]),
    )

    cenario.gerar_lote()

    mensagem = cenario.mensagens.listar_por_execucao(EXECUCAO_ID)[0]
    assert mensagem.estado is EstadoMensagem.GERANDO
    assert cenario.critico.chamadas == 0
    assert cenario.avaliacoes.obter_por_versao(_versao_id(cenario)) is None


def test_reinvocar_o_lote_nao_reavalia_a_versao_ja_avaliada(tmp_path: Path) -> None:
    """Terceiro Edge Case da 3.3: o replay reaproveita a avaliação persistida, sem nenhuma
    nova chamada ao crítico e sem uma segunda avaliação da mesma versão."""

    incluido = registro(canal="sms")
    cenario = Cenario([incluido], tmp_path, critico=CriticoFalso([AvaliacaoCritica(True, ())]))
    cenario.gerar_lote()
    versao_id = _versao_id(cenario)
    primeira = cenario.avaliacoes.obter_por_versao(versao_id)

    cenario.gerar_lote()

    assert cenario.critico.chamadas == 1
    assert cenario.avaliacoes.obter_por_versao(versao_id) == primeira
    assert len(cenario.mensagens.listar_por_execucao(EXECUCAO_ID)) == 1


def test_reprovacao_de_um_item_nao_impede_a_aprovacao_do_seguinte(tmp_path: Path) -> None:
    """CRIT-05, CRIT-06: cada item segue a própria decisão do crítico dentro do lote."""

    reprovado = registro(canal="sms")
    aprovado = registro(canal="email")
    cenario = Cenario(
        [reprovado, aprovado],
        tmp_path,
        critico=CriticoFalso(
            [
                AvaliacaoCritica(
                    False, (MotivoCritica(CategoriaCritica.CLAREZA, "Instrução ambígua."),)
                ),
                AvaliacaoCritica(True, ()),
            ]
        ),
    )

    cenario.gerar_lote()

    por_item = {
        item.elegibilidade_id: item
        for item in cenario.mensagens.listar_por_execucao(EXECUCAO_ID)
    }
    assert por_item[reprovado.id].estado is EstadoMensagem.CRITICANDO
    assert por_item[aprovado.id].estado is EstadoMensagem.AGUARDANDO_REVISAO
