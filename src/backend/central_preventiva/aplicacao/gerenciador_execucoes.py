"""Orquestrador da execução preventiva ponta a ponta: coleta → risco → elegibilidade
(RUNNER-01..12, AD-7)."""

import asyncio
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from central_preventiva.aplicacao.coleta_meteorologica import AreaMonitoradaInexistente
from central_preventiva.aplicacao.portas_meteorologia import AreaMonitorada
from central_preventiva.aplicacao.portas_persistencia import (
    ConflitoIdempotencia,
    RespostaRegistrada,
)
from central_preventiva.dominio.avaliador_risco import RegraSnapshot, ResultadoAvaliacaoRisco
from central_preventiva.dominio.estados_execucao import EstadoExecucao, eh_terminal
from central_preventiva.dominio.evento_meteorologico import EventoMeteorologico

OPERACAO_INICIAR_EXECUCAO = "iniciar_execucao"

MARCO_COLETA_CONCLUIDA = "coleta_concluida"
MARCO_AVALIACAO_RISCO_CONCLUIDA = "avaliacao_risco_concluida"
MARCO_AVALIACAO_ELEGIBILIDADE_CONCLUIDA = "avaliacao_elegibilidade_concluida"
MARCO_PUBLICO_ELEGIVEL_FORMADO = "publico_elegivel_formado"

CAUSA_COLETA_INTERROMPIDA_NO_BOOT = (
    "Execução interrompida por reinício do backend durante a coleta."
)
"""A coleta é síncrona ponta a ponta (limitação conhecida desde 2.1/2.2): uma execução
achada em `coletando` no boot nunca tem a área monitorada disponível para retomar de
fato, e nunca ficaria presa por si mesma em produção. Termina em `falhou_coleta` para
nunca permanecer indefinidamente em processamento (RUNNER-11)."""


class _SnapshotExecucao(Protocol):
    """Forma mínima do snapshot devolvido por `RepositorioExecucaoPreventiva.obter`."""

    @property
    def estado(self) -> EstadoExecucao: ...
    @property
    def versao(self) -> int: ...


class _Marco(Protocol):
    """Forma mínima de um marco devolvido por `listar_marcos`."""

    @property
    def marco(self) -> str: ...


class _AvaliacaoRisco(Protocol):
    """Forma mínima do snapshot devolvido por `RepositorioAvaliacoesRisco.obter_por_execucao`."""

    @property
    def evento_id(self) -> UUID: ...
    @property
    def regra_id(self) -> UUID | None: ...


class _Regra(Protocol):
    """Forma mínima de uma regra devolvida por `RepositorioRegras.obter_por_id`."""

    @property
    def id(self) -> UUID: ...
    @property
    def evento_tipo(self) -> object: ...
    @property
    def limiar_meteorologico(self) -> float: ...
    @property
    def area_aplicavel(self) -> str: ...
    @property
    def apolice_tipo(self) -> str: ...
    @property
    def cobertura_exigida(self) -> str: ...
    @property
    def versao(self) -> int: ...


class _ContagemElegibilidade(Protocol):
    """Forma mínima da contagem devolvida por `ServicoAvaliacaoElegibilidade.avaliar_publico`."""

    @property
    def incluidos(self) -> int: ...


class _RepositorioExecucaoPreventiva(Protocol):
    """Porta mínima de `execucao_preventiva`/`marcos_execucao` de que este orquestrador
    depende (AD-008, RUNNER-02, RUNNER-07)."""

    def criar(self, estado_inicial: EstadoExecucao) -> UUID: ...
    def obter(self, execucao_id: UUID) -> _SnapshotExecucao: ...
    def transicionar(
        self, execucao_id: UUID, versao_esperada: int, novo_estado: EstadoExecucao
    ) -> None: ...
    def listar_nao_terminais(self) -> list[UUID]: ...
    def registrar_marco(self, execucao_id: UUID, marco: str, causa: str | None = None) -> None: ...
    def listar_marcos(self, execucao_id: UUID) -> list[_Marco]: ...


class _RepositorioAreasMonitoradas(Protocol):
    """Porta mínima de leitura de área monitorada de que este orquestrador depende."""

    def buscar_por_id(self, id: UUID) -> AreaMonitorada | None: ...


class _RepositorioEventosMeteorologicos(Protocol):
    """Porta mínima de leitura de evento meteorológico de que este orquestrador depende."""

    def buscar_por_id(self, id: UUID) -> EventoMeteorologico | None: ...


class _RepositorioAvaliacoesRisco(Protocol):
    """Porta mínima de leitura da avaliação de risco já persistida (2.3), para retomar a
    elegibilidade a partir do snapshot imutável (AD-11), sem recalcular o risco."""

    def obter_por_execucao(self, execucao_id: UUID) -> _AvaliacaoRisco | None: ...


class _RepositorioRegras(Protocol):
    """Porta mínima de leitura de uma versão específica de regra (2.4), para reconstruir
    o `RegraSnapshot` completo a partir do `regra_id` já snapshotado em 2.3."""

    def obter_por_id(self, regra_id: UUID) -> _Regra | None: ...


class _RepositorioIdempotencia(Protocol):
    """Porta mínima de idempotência (AD-002) de que este orquestrador depende."""

    def buscar(self, chave: str, operacao: str) -> RespostaRegistrada | None: ...
    def registrar(
        self, chave: str, operacao: str, hash_requisicao: str, status: int, corpo: str
    ) -> None: ...


class _ServicoColeta(Protocol):
    """Porta mínima do caso de uso de coleta (2.1/2.2) de que este orquestrador depende."""

    async def coletar_para_execucao(
        self, execucao_id: UUID, versao_esperada: int, area: AreaMonitorada
    ) -> EventoMeteorologico | None: ...


class _ServicoRisco(Protocol):
    """Porta mínima do caso de uso de avaliação de risco (2.3) de que este orquestrador
    depende — já transiciona a execução para `sem_risco`/`avaliando_elegibilidade`."""

    def avaliar_evento(
        self, execucao_id: UUID, versao_esperada: int, evento: EventoMeteorologico
    ) -> ResultadoAvaliacaoRisco: ...


class _ServicoElegibilidade(Protocol):
    """Porta mínima do caso de uso de avaliação de elegibilidade (2.5) de que este
    orquestrador depende — nunca transiciona a execução (decisão deliberada de 2.5,
    deferida a esta história)."""

    def avaliar_publico(
        self, execucao_id: UUID, evento: EventoMeteorologico, regra: RegraSnapshot
    ) -> _ContagemElegibilidade: ...


@dataclass(frozen=True, slots=True)
class PortasGerenciadorExecucoes:
    """Agrupa as portas de que o orquestrador da execução preventiva depende."""

    execucoes: _RepositorioExecucaoPreventiva
    areas: _RepositorioAreasMonitoradas
    eventos: _RepositorioEventosMeteorologicos
    avaliacoes_risco: _RepositorioAvaliacoesRisco
    regras: _RepositorioRegras
    idempotencia: _RepositorioIdempotencia
    coleta: _ServicoColeta
    risco: _ServicoRisco
    elegibilidade: _ServicoElegibilidade


class GerenciadorExecucoes:
    """Encadeia coleta → risco → elegibilidade automaticamente para uma execução,
    persistindo cada transição como marco; retoma execuções não terminais no boot
    (AD-7 — este é o componente que o ADR nomeia e esta história finalmente implementa).
    """

    def __init__(self, portas: PortasGerenciadorExecucoes) -> None:
        """Guarda as portas de que este orquestrador depende."""

        self._portas = portas
        self._tarefas_em_andamento: set[asyncio.Task[None]] = set()

    async def iniciar(self, area_id: UUID, chave_idempotencia: str, hash_requisicao: str) -> UUID:
        """Cria a execução em `coletando` e devolve o `execucao_id` imediatamente.

        A cadeia completa (coleta → risco → elegibilidade) roda como uma task `asyncio`
        desacoplada (AD-006, mesmo padrão do `AgendadorMeteorologico`), para que a
        resposta HTTP (`202`) nunca espere pela coleta real. Idempotente por
        `chave_idempotencia` (AD-002): repetir a mesma chave com o mesmo
        `hash_requisicao` devolve o `execucao_id` já criado, sem criar uma segunda
        execução; hash diferente levanta `ConflitoIdempotencia`.
        """

        registrada = self._portas.idempotencia.buscar(chave_idempotencia, OPERACAO_INICIAR_EXECUCAO)
        if registrada is not None:
            if registrada.hash_requisicao != hash_requisicao:
                raise ConflitoIdempotencia(
                    chave=chave_idempotencia, operacao=OPERACAO_INICIAR_EXECUCAO
                )
            return UUID(registrada.corpo)

        area = self._portas.areas.buscar_por_id(area_id)
        if area is None:
            raise AreaMonitoradaInexistente(area_id)

        execucao_id = self._portas.execucoes.criar(EstadoExecucao.COLETANDO)
        self._portas.idempotencia.registrar(
            chave_idempotencia,
            OPERACAO_INICIAR_EXECUCAO,
            hash_requisicao,
            202,
            str(execucao_id),
        )

        tarefa = asyncio.create_task(self._processar_coleta_e_continuar(execucao_id, area))
        self._tarefas_em_andamento.add(tarefa)
        tarefa.add_done_callback(self._tarefas_em_andamento.discard)

        return execucao_id

    async def _processar_coleta_e_continuar(self, execucao_id: UUID, area: AreaMonitorada) -> None:
        """Executa a coleta vinculada à execução e, em caso de sucesso, prossegue a
        orquestração via `continuar`. Falhas de negócio (retentativas esgotadas,
        rejeição de normalização) já terminam a execução dentro de
        `coletar_para_execucao`; qualquer outra exceção é uma falha técnica (RUNNER-11).
        """

        try:
            snap = self._portas.execucoes.obter(execucao_id)
            evento = await self._portas.coleta.coletar_para_execucao(execucao_id, snap.versao, area)
        except Exception as erro:  # noqa: BLE001 - falha técnica não recuperável (RUNNER-11)
            self._registrar_falha_processamento(execucao_id, erro)
            return

        if evento is None:
            self._portas.execucoes.registrar_marco(execucao_id, EstadoExecucao.FALHOU_COLETA.value)
            return

        self._portas.execucoes.registrar_marco(execucao_id, MARCO_COLETA_CONCLUIDA)
        await self.continuar(execucao_id, evento)

    async def continuar(self, execucao_id: UUID, evento: EventoMeteorologico | None = None) -> None:
        """Continua a orquestração a partir do estado atual da execução (RUNNER-01/07).

        Chamada tanto pela cadeia recém-iniciada (com `evento` já em mãos, evitando uma
        releitura) quanto pela retomada no boot (sem `evento` — reconstruído do snapshot
        já persistido em `avaliacoes_risco`, nunca recalculado). Para em qualquer
        terminal ou em `aguardando_geracao`; qualquer exceção não prevista vira uma
        falha técnica explícita (RUNNER-11), nunca um travamento silencioso.
        """

        try:
            await self._continuar(execucao_id, evento)
        except Exception as erro:  # noqa: BLE001 - falha técnica não recuperável (RUNNER-11)
            self._registrar_falha_processamento(execucao_id, erro)

    async def _continuar(self, execucao_id: UUID, evento: EventoMeteorologico | None) -> None:
        snap = self._portas.execucoes.obter(execucao_id)
        if eh_terminal(snap.estado) or snap.estado == EstadoExecucao.AGUARDANDO_GERACAO:
            return

        if snap.estado == EstadoExecucao.COLETANDO:
            if evento is None:
                raise RuntimeError(CAUSA_COLETA_INTERROMPIDA_NO_BOOT)
            resultado = self._portas.risco.avaliar_evento(execucao_id, snap.versao, evento)
            self._portas.execucoes.registrar_marco(execucao_id, MARCO_AVALIACAO_RISCO_CONCLUIDA)
            snap = self._portas.execucoes.obter(execucao_id)
            if not resultado.relevante:
                self._portas.execucoes.registrar_marco(execucao_id, snap.estado.value)
                return

        if snap.estado != EstadoExecucao.AVALIANDO_ELEGIBILIDADE:
            return

        marcos = {marco.marco for marco in self._portas.execucoes.listar_marcos(execucao_id)}
        if MARCO_PUBLICO_ELEGIVEL_FORMADO in marcos:
            self._concluir_aguardando_geracao(execucao_id, snap.versao)
            return

        avaliacao = self._portas.avaliacoes_risco.obter_por_execucao(execucao_id)
        if avaliacao is None or avaliacao.regra_id is None:
            raise RuntimeError("Avaliação de risco ausente ou sem regra ao retomar a execução.")

        if evento is None:
            evento = self._portas.eventos.buscar_por_id(avaliacao.evento_id)
            if evento is None:
                raise RuntimeError("Evento meteorológico ausente ao retomar a execução.")

        regra_completa = self._portas.regras.obter_por_id(avaliacao.regra_id)
        if regra_completa is None:
            raise RuntimeError("Regra usada na avaliação de risco não existe mais.")

        regra_snapshot = RegraSnapshot(
            id=regra_completa.id,
            evento_tipo=regra_completa.evento_tipo,  # type: ignore[arg-type]
            limiar_meteorologico=regra_completa.limiar_meteorologico,
            area_aplicavel=regra_completa.area_aplicavel,
            apolice_tipo=regra_completa.apolice_tipo,
            cobertura_exigida=regra_completa.cobertura_exigida,
            versao=regra_completa.versao,
        )

        contagem = self._portas.elegibilidade.avaliar_publico(execucao_id, evento, regra_snapshot)
        self._portas.execucoes.registrar_marco(execucao_id, MARCO_AVALIACAO_ELEGIBILIDADE_CONCLUIDA)

        snap = self._portas.execucoes.obter(execucao_id)
        if contagem.incluidos > 0:
            self._portas.execucoes.registrar_marco(execucao_id, MARCO_PUBLICO_ELEGIVEL_FORMADO)
            self._concluir_aguardando_geracao(execucao_id, snap.versao)
        else:
            self._portas.execucoes.transicionar(
                execucao_id, snap.versao, EstadoExecucao.SEM_ELEGIVEIS
            )
            self._portas.execucoes.registrar_marco(execucao_id, EstadoExecucao.SEM_ELEGIVEIS.value)

    def _concluir_aguardando_geracao(self, execucao_id: UUID, versao_esperada: int) -> None:
        """Completa a transição para `aguardando_geracao` (RUNNER-04).

        Separado do resto de `_continuar` porque é também o ponto de retomada do edge
        case da spec: um reinício exatamente entre gravar `publico_elegivel_formado` e
        esta transição encontra o marco já persistido e só precisa completar o último
        passo, sem reavaliar elegibilidade nem duplicar o marco.
        """

        self._portas.execucoes.transicionar(
            execucao_id, versao_esperada, EstadoExecucao.AGUARDANDO_GERACAO
        )
        self._portas.execucoes.registrar_marco(execucao_id, EstadoExecucao.AGUARDANDO_GERACAO.value)

    def _registrar_falha_processamento(self, execucao_id: UUID, erro: BaseException) -> None:
        """Transiciona a execução para o terminal técnico explícito (RUNNER-11).

        Reusa `falhou_coleta` como o único terminal técnico do trecho determinístico
        (Tech Decision do Design: nenhum novo valor de `EstadoExecucao` — a distinção
        entre "falha técnica" e as decisões de negócio `sem_risco`/`sem_elegiveis` mora
        na causa registrada, não em um estado novo). A causa sempre nomeia a exceção
        real, então "falhou_coleta" durante a avaliação de risco não é ambíguo na prática.
        """

        try:
            snap = self._portas.execucoes.obter(execucao_id)
        except Exception:  # noqa: BLE001 - execução pode não existir mais; nada a fazer
            return
        if eh_terminal(snap.estado):
            return

        causa = f"{type(erro).__name__}: {erro}"
        try:
            self._portas.execucoes.transicionar(
                execucao_id, snap.versao, EstadoExecucao.FALHOU_COLETA
            )
        except Exception:  # noqa: BLE001 - conflito de versão/transição concorrente
            return
        self._portas.execucoes.registrar_marco(
            execucao_id, EstadoExecucao.FALHOU_COLETA.value, causa=causa
        )

    async def retomar_pendentes(self) -> None:
        """Retoma, no boot, toda execução ainda fora de um estado terminal (RUNNER-07).

        Uma execução em `coletando` não pode ser retomada de fato — a área monitorada
        original não está disponível fora da chamada de `iniciar` que a criou — e
        termina em `falhou_coleta` para nunca ficar presa indefinidamente (RUNNER-11,
        mesma limitação estrutural já conhecida desde 2.1/2.2: a coleta é síncrona
        ponta a ponta). `aguardando_geracao` não é retomado por esta história — é o
        checkpoint em que 2.6 termina.
        """

        for execucao_id in self._portas.execucoes.listar_nao_terminais():
            snap = self._portas.execucoes.obter(execucao_id)
            if snap.estado == EstadoExecucao.AGUARDANDO_GERACAO:
                continue
            if snap.estado == EstadoExecucao.COLETANDO:
                self._registrar_falha_processamento(
                    execucao_id, RuntimeError(CAUSA_COLETA_INTERROMPIDA_NO_BOOT)
                )
                continue
            await self.continuar(execucao_id)
