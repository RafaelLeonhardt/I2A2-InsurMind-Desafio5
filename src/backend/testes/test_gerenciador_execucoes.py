"""Testes do `GerenciadorExecucoes`: coleta → risco → elegibilidade até um checkpoint
(RUNNER-01..09)."""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

import pytest

from central_preventiva.aplicacao.coleta_meteorologica import AreaMonitoradaInexistente
from central_preventiva.aplicacao.gerenciador_execucoes import (
    CAUSA_COLETA_INTERROMPIDA_NO_BOOT,
    MARCO_AVALIACAO_ELEGIBILIDADE_CONCLUIDA,
    MARCO_AVALIACAO_RISCO_CONCLUIDA,
    MARCO_COLETA_CONCLUIDA,
    MARCO_PUBLICO_ELEGIVEL_FORMADO,
    GerenciadorExecucoes,
    PortasGerenciadorExecucoes,
)
from central_preventiva.aplicacao.portas_meteorologia import AreaMonitorada
from central_preventiva.aplicacao.portas_persistencia import (
    ConflitoIdempotencia,
    RespostaRegistrada,
)
from central_preventiva.dominio.avaliador_risco import RegraSnapshot, ResultadoAvaliacaoRisco
from central_preventiva.dominio.estados_execucao import EstadoExecucao, eh_terminal
from central_preventiva.dominio.evento_meteorologico import (
    EventoMeteorologico,
    ProvenienciaEvento,
    TipoEventoMeteorologico,
)

AREA_ID = uuid4()
AREA = AreaMonitorada(
    id=AREA_ID,
    codigo_estacao_inmet="A001",
    nome_estacao="Estação Sintética",
    codigo_ibge_area="9990001",
    ativa=True,
)

EVENTO = EventoMeteorologico(
    id=uuid4(),
    tipo=TipoEventoMeteorologico.CHUVA_INTENSA,
    area=AREA.codigo_ibge_area,
    periodo_inicio=datetime(2026, 3, 10, 6, 0),
    periodo_fim=datetime(2026, 3, 10, 18, 0),
    intensidade=72.5,
    proveniencia=ProvenienciaEvento.SINTETICO,
    instante_observado=datetime(2026, 3, 9, 18, 0),
)

REGRA_ID = uuid4()
REGRA_COMPLETA = RegraSnapshot(
    id=REGRA_ID,
    evento_tipo=TipoEventoMeteorologico.CHUVA_INTENSA,
    limiar_meteorologico=50.0,
    area_aplicavel=AREA.codigo_ibge_area,
    apolice_tipo="residencial",
    cobertura_exigida="alagamento",
    versao=1,
)

RESULTADO_RELEVANTE = ResultadoAvaliacaoRisco(relevante=True, criterios=(), motivo="ok")
RESULTADO_IRRELEVANTE = ResultadoAvaliacaoRisco(
    relevante=False, criterios=(), motivo="fora do limiar"
)


@dataclass(frozen=True, slots=True)
class SnapshotFalso:
    id: UUID
    estado: EstadoExecucao
    versao: int


@dataclass(frozen=True, slots=True)
class MarcoFalso:
    marco: str
    causa: str | None = None


@dataclass(frozen=True, slots=True)
class AvaliacaoRiscoFalsa:
    evento_id: UUID
    regra_id: UUID | None


@dataclass(frozen=True, slots=True)
class RegraFalsa:
    id: UUID
    evento_tipo: TipoEventoMeteorologico
    limiar_meteorologico: float
    area_aplicavel: str
    apolice_tipo: str
    cobertura_exigida: str
    versao: int


@dataclass(frozen=True, slots=True)
class ContagemFalsa:
    incluidos: int


class RepositorioExecucoesFalso:
    def __init__(self) -> None:
        self._estados: dict[UUID, EstadoExecucao] = {}
        self._versoes: dict[UUID, int] = {}
        self._marcos: dict[UUID, list[MarcoFalso]] = {}
        self.transicoes: list[tuple[UUID, EstadoExecucao]] = []

    def criar(self, estado_inicial: EstadoExecucao) -> UUID:
        execucao_id = uuid4()
        self._estados[execucao_id] = estado_inicial
        self._versoes[execucao_id] = 1
        self._marcos[execucao_id] = []
        return execucao_id

    def semear(self, execucao_id: UUID, estado: EstadoExecucao, versao: int = 1) -> None:
        self._estados[execucao_id] = estado
        self._versoes[execucao_id] = versao
        self._marcos.setdefault(execucao_id, [])

    def obter(self, execucao_id: UUID) -> SnapshotFalso:
        return SnapshotFalso(
            id=execucao_id,
            estado=self._estados[execucao_id],
            versao=self._versoes[execucao_id],
        )

    def transicionar(
        self, execucao_id: UUID, versao_esperada: int, novo_estado: EstadoExecucao
    ) -> None:
        if self._versoes[execucao_id] != versao_esperada:
            raise RuntimeError("versão inesperada")
        if eh_terminal(self._estados[execucao_id]):
            raise RuntimeError("execução já terminal")
        self._estados[execucao_id] = novo_estado
        self._versoes[execucao_id] += 1
        self.transicoes.append((execucao_id, novo_estado))

    def listar_nao_terminais(self) -> list[UUID]:
        return [eid for eid, estado in self._estados.items() if not eh_terminal(estado)]

    def registrar_marco(self, execucao_id: UUID, marco: str, causa: str | None = None) -> None:
        self._marcos[execucao_id].append(MarcoFalso(marco=marco, causa=causa))

    def listar_marcos(self, execucao_id: UUID) -> list[MarcoFalso]:
        return list(self._marcos[execucao_id])


class RepositorioAreasFalso:
    def __init__(self, areas: list[AreaMonitorada]) -> None:
        self._areas = {area.id: area for area in areas}

    def buscar_por_id(self, id: UUID) -> AreaMonitorada | None:
        return self._areas.get(id)


class RepositorioEventosFalso:
    def __init__(self, eventos: list[EventoMeteorologico]) -> None:
        self._eventos = {evento.id: evento for evento in eventos}

    def buscar_por_id(self, id: UUID) -> EventoMeteorologico | None:
        return self._eventos.get(id)


class RepositorioAvaliacoesRiscoFalso:
    def __init__(self) -> None:
        self._por_execucao: dict[UUID, AvaliacaoRiscoFalsa] = {}

    def semear(self, execucao_id: UUID, avaliacao: AvaliacaoRiscoFalsa) -> None:
        self._por_execucao[execucao_id] = avaliacao

    def obter_por_execucao(self, execucao_id: UUID) -> AvaliacaoRiscoFalsa | None:
        return self._por_execucao.get(execucao_id)


class RepositorioRegrasFalso:
    def __init__(self, regras: list[RegraFalsa]) -> None:
        self._regras = {regra.id: regra for regra in regras}

    def obter_por_id(self, regra_id: UUID) -> RegraFalsa | None:
        return self._regras.get(regra_id)


class RepositorioIdempotenciaFalso:
    def __init__(self) -> None:
        self._respostas: dict[tuple[str, str], RespostaRegistrada] = {}

    def buscar(self, chave: str, operacao: str) -> RespostaRegistrada | None:
        return self._respostas.get((chave, operacao))

    def registrar(
        self, chave: str, operacao: str, hash_requisicao: str, status: int, corpo: str
    ) -> None:
        self._respostas[(chave, operacao)] = RespostaRegistrada(
            hash_requisicao=hash_requisicao, status=status, corpo=corpo
        )


@dataclass
class ServicoColetaFalso:
    evento: EventoMeteorologico | None = EVENTO
    excecao: BaseException | None = None
    chamadas: list[tuple[UUID, int, UUID]] = field(default_factory=list)

    async def coletar_para_execucao(
        self, execucao_id: UUID, versao_esperada: int, area: AreaMonitorada
    ) -> EventoMeteorologico | None:
        self.chamadas.append((execucao_id, versao_esperada, area.id))
        if self.excecao is not None:
            raise self.excecao
        return self.evento


@dataclass
class ServicoRiscoFalso:
    resultado: ResultadoAvaliacaoRisco = RESULTADO_RELEVANTE
    excecao: BaseException | None = None
    chamadas: list[tuple[UUID, int, UUID]] = field(default_factory=list)
    execucoes: RepositorioExecucoesFalso | None = None
    avaliacoes_risco: RepositorioAvaliacoesRiscoFalso | None = None
    regra_id: UUID = REGRA_ID
    proximo_estado_relevante: EstadoExecucao = EstadoExecucao.AVALIANDO_ELEGIBILIDADE

    def avaliar_evento(
        self, execucao_id: UUID, versao_esperada: int, evento: EventoMeteorologico
    ) -> ResultadoAvaliacaoRisco:
        self.chamadas.append((execucao_id, versao_esperada, evento.id))
        if self.excecao is not None:
            raise self.excecao
        assert self.execucoes is not None
        if self.resultado.relevante:
            novo_estado = self.proximo_estado_relevante
            assert self.avaliacoes_risco is not None
            self.avaliacoes_risco.semear(
                execucao_id,
                AvaliacaoRiscoFalsa(evento_id=evento.id, regra_id=self.regra_id),
            )
        else:
            novo_estado = EstadoExecucao.SEM_RISCO
        self.execucoes.transicionar(execucao_id, versao_esperada, novo_estado)
        return self.resultado


@dataclass
class ServicoElegibilidadeFalso:
    incluidos: int = 1
    excecao: BaseException | None = None
    chamadas: list[tuple[UUID, UUID, UUID]] = field(default_factory=list)

    def avaliar_publico(
        self, execucao_id: UUID, evento: EventoMeteorologico, regra: RegraSnapshot
    ) -> ContagemFalsa:
        self.chamadas.append((execucao_id, evento.id, regra.id))
        if self.excecao is not None:
            raise self.excecao
        return ContagemFalsa(incluidos=self.incluidos)


@dataclass
class ServicoGeracaoFalso:
    """Dublê da geração de mensagens: registra as execuções cuja retomada foi pedida."""

    retomadas: list[UUID] = field(default_factory=list)

    async def retomar_mensagens_pendentes(self, execucao_id: UUID) -> None:
        self.retomadas.append(execucao_id)


def montar_gerenciador(
    *,
    coleta: ServicoColetaFalso | None = None,
    risco: ServicoRiscoFalso | None = None,
    elegibilidade: ServicoElegibilidadeFalso | None = None,
    areas: list[AreaMonitorada] | None = None,
    eventos: list[EventoMeteorologico] | None = None,
    regras: list[RegraFalsa] | None = None,
    geracao: ServicoGeracaoFalso | None = None,
) -> tuple[
    GerenciadorExecucoes,
    RepositorioExecucoesFalso,
    RepositorioAvaliacoesRiscoFalso,
    ServicoColetaFalso,
    ServicoRiscoFalso,
    ServicoElegibilidadeFalso,
]:
    execucoes = RepositorioExecucoesFalso()
    avaliacoes_risco = RepositorioAvaliacoesRiscoFalso()
    coleta = coleta or ServicoColetaFalso()
    risco = risco or ServicoRiscoFalso()
    if risco.execucoes is None:
        risco.execucoes = execucoes
    if risco.avaliacoes_risco is None:
        risco.avaliacoes_risco = avaliacoes_risco
    elegibilidade = elegibilidade or ServicoElegibilidadeFalso()

    portas = PortasGerenciadorExecucoes(
        execucoes=execucoes,  # type: ignore[arg-type]
        areas=RepositorioAreasFalso(areas if areas is not None else [AREA]),  # type: ignore[arg-type]
        eventos=RepositorioEventosFalso(eventos if eventos is not None else [EVENTO]),  # type: ignore[arg-type]
        avaliacoes_risco=avaliacoes_risco,  # type: ignore[arg-type]
        regras=RepositorioRegrasFalso(
            regras
            if regras is not None
            else [
                RegraFalsa(
                    id=REGRA_ID,
                    evento_tipo=REGRA_COMPLETA.evento_tipo,
                    limiar_meteorologico=REGRA_COMPLETA.limiar_meteorologico,
                    area_aplicavel=REGRA_COMPLETA.area_aplicavel,
                    apolice_tipo=REGRA_COMPLETA.apolice_tipo,
                    cobertura_exigida=REGRA_COMPLETA.cobertura_exigida,
                    versao=REGRA_COMPLETA.versao,
                )
            ]
        ),  # type: ignore[arg-type]
        idempotencia=RepositorioIdempotenciaFalso(),  # type: ignore[arg-type]
        coleta=coleta,  # type: ignore[arg-type]
        risco=risco,  # type: ignore[arg-type]
        elegibilidade=elegibilidade,  # type: ignore[arg-type]
        geracao=geracao if geracao is not None else ServicoGeracaoFalso(),
    )
    return GerenciadorExecucoes(portas), execucoes, avaliacoes_risco, coleta, risco, elegibilidade


async def _aguardar_tarefas(gerenciador: GerenciadorExecucoes) -> None:
    tarefas = list(gerenciador._tarefas_em_andamento)  # noqa: SLF001 - teste aguarda a task fire-and-forget
    if tarefas:
        await asyncio.gather(*tarefas)


def test_iniciar_com_area_inexistente_levanta_erro_sem_criar_execucao() -> None:
    gerenciador, execucoes, *_ = montar_gerenciador(areas=[])

    async def rodar() -> None:
        with pytest.raises(AreaMonitoradaInexistente):
            await gerenciador.iniciar(AREA_ID, "chave-1", "hash-1")

    asyncio.run(rodar())
    assert execucoes.listar_nao_terminais() == []


def test_coleta_com_evento_relevante_e_publico_elegivel_avanca_ate_aguardando_geracao() -> None:
    gerenciador, execucoes, _, coleta, risco, elegibilidade = montar_gerenciador(
        elegibilidade=ServicoElegibilidadeFalso(incluidos=3)
    )

    async def rodar() -> UUID:
        execucao_id = await gerenciador.iniciar(AREA_ID, "chave-1", "hash-1")
        await _aguardar_tarefas(gerenciador)
        return execucao_id

    execucao_id = asyncio.run(rodar())

    snapshot = execucoes.obter(execucao_id)
    assert snapshot.estado == EstadoExecucao.AGUARDANDO_GERACAO
    marcos = [m.marco for m in execucoes.listar_marcos(execucao_id)]
    assert MARCO_COLETA_CONCLUIDA in marcos
    assert MARCO_AVALIACAO_RISCO_CONCLUIDA in marcos
    assert MARCO_AVALIACAO_ELEGIBILIDADE_CONCLUIDA in marcos
    assert MARCO_PUBLICO_ELEGIVEL_FORMADO in marcos
    assert marcos[-1] == EstadoExecucao.AGUARDANDO_GERACAO.value
    assert len(coleta.chamadas) == 1
    assert len(risco.chamadas) == 1
    assert len(elegibilidade.chamadas) == 1


def test_evento_nao_relevante_para_em_sem_risco_sem_chamar_elegibilidade() -> None:
    gerenciador, execucoes, _, _, _, elegibilidade = montar_gerenciador(
        risco=ServicoRiscoFalso(resultado=RESULTADO_IRRELEVANTE)
    )

    async def rodar() -> UUID:
        execucao_id = await gerenciador.iniciar(AREA_ID, "chave-1", "hash-1")
        await _aguardar_tarefas(gerenciador)
        return execucao_id

    execucao_id = asyncio.run(rodar())

    snapshot = execucoes.obter(execucao_id)
    assert snapshot.estado == EstadoExecucao.SEM_RISCO
    marcos = [m.marco for m in execucoes.listar_marcos(execucao_id)]
    assert marcos[-1] == EstadoExecucao.SEM_RISCO.value
    assert elegibilidade.chamadas == []


def test_evento_relevante_sem_elegiveis_para_em_sem_elegiveis() -> None:
    gerenciador, execucoes, *_ = montar_gerenciador(
        elegibilidade=ServicoElegibilidadeFalso(incluidos=0)
    )

    async def rodar() -> UUID:
        execucao_id = await gerenciador.iniciar(AREA_ID, "chave-1", "hash-1")
        await _aguardar_tarefas(gerenciador)
        return execucao_id

    execucao_id = asyncio.run(rodar())

    snapshot = execucoes.obter(execucao_id)
    assert snapshot.estado == EstadoExecucao.SEM_ELEGIVEIS
    marcos = [m.marco for m in execucoes.listar_marcos(execucao_id)]
    assert marcos[-1] == EstadoExecucao.SEM_ELEGIVEIS.value
    assert MARCO_PUBLICO_ELEGIVEL_FORMADO not in marcos


def test_falha_interna_nao_recuperavel_na_coleta_termina_em_falhou_coleta_com_causa() -> None:
    gerenciador, execucoes, *_ = montar_gerenciador(
        coleta=ServicoColetaFalso(excecao=RuntimeError("falha síncrona inesperada"))
    )

    async def rodar() -> UUID:
        execucao_id = await gerenciador.iniciar(AREA_ID, "chave-1", "hash-1")
        await _aguardar_tarefas(gerenciador)
        return execucao_id

    execucao_id = asyncio.run(rodar())

    snapshot = execucoes.obter(execucao_id)
    assert snapshot.estado == EstadoExecucao.FALHOU_COLETA
    marcos = execucoes.listar_marcos(execucao_id)
    assert marcos[-1].marco == EstadoExecucao.FALHOU_COLETA.value
    assert marcos[-1].causa is not None
    assert "falha síncrona inesperada" in marcos[-1].causa


def test_falha_interna_nao_recuperavel_na_avaliacao_de_risco_termina_em_falhou_coleta() -> None:
    gerenciador, execucoes, *_ = montar_gerenciador(
        risco=ServicoRiscoFalso(excecao=RuntimeError("erro inesperado no risco"))
    )

    async def rodar() -> UUID:
        execucao_id = await gerenciador.iniciar(AREA_ID, "chave-1", "hash-1")
        await _aguardar_tarefas(gerenciador)
        return execucao_id

    execucao_id = asyncio.run(rodar())

    snapshot = execucoes.obter(execucao_id)
    assert snapshot.estado == EstadoExecucao.FALHOU_COLETA
    marcos = execucoes.listar_marcos(execucao_id)
    assert marcos[-1].causa is not None
    assert "erro inesperado no risco" in marcos[-1].causa


def test_falha_interna_nao_recuperavel_na_elegibilidade_termina_em_falhou_coleta() -> None:
    gerenciador, execucoes, *_ = montar_gerenciador(
        elegibilidade=ServicoElegibilidadeFalso(excecao=RuntimeError("erro na elegibilidade"))
    )

    async def rodar() -> UUID:
        execucao_id = await gerenciador.iniciar(AREA_ID, "chave-1", "hash-1")
        await _aguardar_tarefas(gerenciador)
        return execucao_id

    execucao_id = asyncio.run(rodar())

    snapshot = execucoes.obter(execucao_id)
    assert snapshot.estado == EstadoExecucao.FALHOU_COLETA
    marcos = execucoes.listar_marcos(execucao_id)
    assert marcos[-1].causa is not None
    assert "erro na elegibilidade" in marcos[-1].causa


def test_retomar_pendentes_em_avaliando_elegibilidade_nao_recria_evento_nem_recalcula() -> None:
    gerenciador, execucoes, avaliacoes_risco, coleta, _, elegibilidade = montar_gerenciador(
        elegibilidade=ServicoElegibilidadeFalso(incluidos=2)
    )
    execucao_id = execucoes.criar(EstadoExecucao.AVALIANDO_ELEGIBILIDADE)
    avaliacoes_risco.semear(
        execucao_id, AvaliacaoRiscoFalsa(evento_id=EVENTO.id, regra_id=REGRA_ID)
    )

    asyncio.run(gerenciador.retomar_pendentes())

    snapshot = execucoes.obter(execucao_id)
    assert snapshot.estado == EstadoExecucao.AGUARDANDO_GERACAO
    assert coleta.chamadas == []
    assert len(elegibilidade.chamadas) == 1
    assert elegibilidade.chamadas[0] == (execucao_id, EVENTO.id, REGRA_ID)


def test_retomar_pendentes_com_marco_publico_ja_formado_so_completa_a_transicao() -> None:
    gerenciador, execucoes, avaliacoes_risco, _, _, elegibilidade = montar_gerenciador()
    execucao_id = execucoes.criar(EstadoExecucao.AVALIANDO_ELEGIBILIDADE)
    avaliacoes_risco.semear(
        execucao_id, AvaliacaoRiscoFalsa(evento_id=EVENTO.id, regra_id=REGRA_ID)
    )
    execucoes.registrar_marco(execucao_id, MARCO_PUBLICO_ELEGIVEL_FORMADO)

    asyncio.run(gerenciador.retomar_pendentes())

    snapshot = execucoes.obter(execucao_id)
    assert snapshot.estado == EstadoExecucao.AGUARDANDO_GERACAO
    assert elegibilidade.chamadas == []


def test_retomar_pendentes_em_coletando_termina_em_falhou_coleta_com_causa_do_reinicio() -> None:
    gerenciador, execucoes, *_ = montar_gerenciador()
    execucao_id = execucoes.criar(EstadoExecucao.COLETANDO)

    asyncio.run(gerenciador.retomar_pendentes())

    snapshot = execucoes.obter(execucao_id)
    assert snapshot.estado == EstadoExecucao.FALHOU_COLETA
    marcos = execucoes.listar_marcos(execucao_id)
    assert marcos[-1].causa == f"RuntimeError: {CAUSA_COLETA_INTERROMPIDA_NO_BOOT}"


def test_retomar_pendentes_ignora_execucoes_ja_em_aguardando_geracao() -> None:
    gerenciador, execucoes, *_ = montar_gerenciador()
    execucao_id = execucoes.criar(EstadoExecucao.AGUARDANDO_GERACAO)

    asyncio.run(gerenciador.retomar_pendentes())

    snapshot = execucoes.obter(execucao_id)
    assert snapshot.estado == EstadoExecucao.AGUARDANDO_GERACAO
    assert execucoes.listar_marcos(execucao_id) == []


def test_iniciar_repetido_com_mesma_chave_devolve_o_mesmo_execucao_id_sem_recriar() -> None:
    gerenciador, execucoes, *_ = montar_gerenciador()

    async def rodar() -> tuple[UUID, UUID]:
        primeiro = await gerenciador.iniciar(AREA_ID, "chave-repetida", "hash-x")
        await _aguardar_tarefas(gerenciador)
        segundo = await gerenciador.iniciar(AREA_ID, "chave-repetida", "hash-x")
        return primeiro, segundo

    primeiro, segundo = asyncio.run(rodar())

    assert primeiro == segundo
    assert len(execucoes.listar_nao_terminais()) + 1 >= 1


def test_iniciar_repetido_com_hash_diferente_levanta_conflito_idempotencia() -> None:
    gerenciador, *_ = montar_gerenciador()

    async def rodar() -> None:
        await gerenciador.iniciar(AREA_ID, "chave-repetida", "hash-x")
        with pytest.raises(ConflitoIdempotencia):
            await gerenciador.iniciar(AREA_ID, "chave-repetida", "hash-y")

    asyncio.run(rodar())


def test_retomar_pendentes_em_processando_mensagens_retoma_as_mensagens_da_execucao() -> None:
    """REGEN-08: uma execução interrompida em `processando_mensagens` é retomada no boot,
    no nível da mensagem — o buraco que 2.6 deixou aberto e que a 3.2 registrou como risco.
    O estado da execução não é mexido: o que ficou pela metade é o ciclo de cada item."""

    geracao = ServicoGeracaoFalso()
    gerenciador, execucoes, *_ = montar_gerenciador(geracao=geracao)
    execucao_id = execucoes.criar(EstadoExecucao.PROCESSANDO_MENSAGENS)

    asyncio.run(gerenciador.retomar_pendentes())

    assert geracao.retomadas == [execucao_id]
    snapshot = execucoes.obter(execucao_id)
    assert snapshot.estado == EstadoExecucao.PROCESSANDO_MENSAGENS
    assert execucoes.listar_marcos(execucao_id) == []


def test_retomar_pendentes_nao_retoma_mensagens_de_execucao_fora_de_processando() -> None:
    """REGEN-09: a retomada de mensagens é escopada à execução que estava de fato gerando —
    uma execução em `aguardando_geracao` ou em `coletando` nunca aciona o ciclo de conteúdo."""

    geracao = ServicoGeracaoFalso()
    gerenciador, execucoes, *_ = montar_gerenciador(geracao=geracao)
    execucoes.criar(EstadoExecucao.AGUARDANDO_GERACAO)
    execucoes.criar(EstadoExecucao.COLETANDO)

    asyncio.run(gerenciador.retomar_pendentes())

    assert geracao.retomadas == []
