"""Testes do `AgendadorMeteorologico`: dispara no boot, dorme o intervalo, cancela limpo."""

import asyncio
from contextlib import suppress
from pathlib import Path
from uuid import UUID

import httpx
import pytest
from fastapi.testclient import TestClient

from central_preventiva.adaptadores.meteorologia.cliente_inmet import AdaptadorInmetFalso
from central_preventiva.adaptadores.meteorologia.normalizador_inmet import NormalizadorInmet
from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.aplicacao.coleta_meteorologica import (
    PortasColetaMeteorologica,
    ServicoColetaMeteorologica,
)
from central_preventiva.aplicacao.portas_meteorologia import (
    AreaMonitorada,
    EstadoSincronizacao,
    OrigemSincronizacao,
    RespostaColetaInmet,
    Sincronizacao,
)
from central_preventiva.composicao.agendador_meteorologico import AgendadorMeteorologico
from central_preventiva.composicao.api import criar_aplicacao
from central_preventiva.composicao.configuracao import Configuracao

AREA = AreaMonitorada(
    id=UUID("22222222-2222-2222-2222-222222222222"),
    codigo_estacao_inmet="A701",
    nome_estacao="Estação de Teste",
    codigo_ibge_area="9990001",
    ativa=True,
)
RESPOSTA_VALIDA = RespostaColetaInmet(
    status_code=200,
    corpo={"CHUVA": "10.0", "DT_MEDICAO": "2026-08-30", "HR_MEDICAO": "1200"},
)


class AreasAtivasFalsas:
    """Porta de áreas monitoradas falsa, sempre devolvendo a mesma lista fixa de ativas."""

    def __init__(self, ativas: tuple[AreaMonitorada, ...]) -> None:
        self._ativas = ativas

    def buscar_por_codigo_estacao(self, codigo_estacao_inmet: str) -> AreaMonitorada | None:
        return None

    def buscar_por_id(self, id: UUID) -> AreaMonitorada | None:
        return None

    def listar_ativas(self) -> tuple[AreaMonitorada, ...]:
        return self._ativas


class SincronizacoesFalsas:
    """Porta de sincronizações falsa, mínima o suficiente para `executar_coleta`."""

    def criar(
        self,
        requisicao_id: UUID,
        area_monitorada_id: UUID,
        origem: OrigemSincronizacao,
        estado: EstadoSincronizacao,
    ) -> Sincronizacao:
        from datetime import UTC, datetime
        from uuid import uuid4

        return Sincronizacao(
            id=uuid4(),
            requisicao_id=requisicao_id,
            area_monitorada_id=area_monitorada_id,
            origem=origem,
            estado=estado,
            registros_validos=0,
            motivo_falha=None,
            iniciado_em=datetime.now(UTC),
            finalizado_em=None,
        )

    def atualizar_estado(
        self,
        id: UUID,
        estado: EstadoSincronizacao,
        registros_validos: int = 0,
        motivo_falha: str | None = None,
    ) -> None:
        pass

    def listar_recentes(self) -> tuple[Sincronizacao, ...]:
        return ()


class EventosFalsos:
    """Porta de eventos meteorológicos falsa, apenas registrando os eventos salvos."""

    def __init__(self) -> None:
        self.salvos: list[object] = []

    def salvar(self, evento: object) -> None:
        self.salvos.append(evento)

    def listar(self) -> tuple[object, ...]:
        return tuple(self.salvos)


class IdempotenciaFalsaInerte:
    """Porta de idempotência falsa, não usada pelo caminho automático."""

    def buscar(self, chave: str, operacao: str) -> None:
        return None

    def registrar(
        self, chave: str, operacao: str, hash_requisicao: str, status: int, corpo: str
    ) -> None:
        raise AssertionError("a coleta automática não deveria usar idempotência")


class TentativasFalsasInertes:
    """Porta de tentativas falsa, apenas absorvendo os registros do retry bem-sucedido."""

    def registrar_tentativa(
        self,
        sincronizacao_id: UUID,
        numero_tentativa: int,
        codigo_resultado: object,
        iniciado_em: object,
        finalizado_em: object,
    ) -> None:
        pass

    def listar_tentativas(self, sincronizacao_id: UUID) -> tuple[object, ...]:
        return ()


class ExecucoesFalsasInertes:
    """Porta de execuções falsa, não usada pelo caminho de coleta automática bem-sucedida."""

    def criar(self, estado_inicial: object) -> UUID:
        raise AssertionError("a coleta automática bem-sucedida não deveria criar execução")

    def transicionar(self, execucao_id: UUID, versao_esperada: int, novo_estado: object) -> None:
        raise AssertionError("a coleta automática bem-sucedida não deveria transicionar execução")


class ExcecoesFalsasInertes:
    """Porta de exceções operacionais falsa, não usada pelo caminho de sucesso."""

    def registrar(self, execucao_id: UUID, causa: str, tentativas: int, impacto: str) -> None:
        raise AssertionError("a coleta automática bem-sucedida não deveria registrar exceção")


class CenariosAtivadosFalsosInertes:
    """Porta de cenários sintéticos ativados falsa, não usada pelo agendador automático."""

    def registrar(self, sincronizacao_id: UUID, identificador_cenario: str) -> None:
        raise AssertionError("o agendador automático não ativa cenários sintéticos")


class RelogioControlavel:
    """Relógio dublê: registra os intervalos aguardados e só libera quando mandado."""

    def __init__(self) -> None:
        self.chamadas: list[float] = []
        self._evento = asyncio.Event()

    async def aguardar(self, segundos: float) -> None:
        self.chamadas.append(segundos)
        await self._evento.wait()
        self._evento.clear()

    def liberar(self) -> None:
        self._evento.set()


def montar_agendador(
    relogio: RelogioControlavel,
    coletor: AdaptadorInmetFalso,
    intervalo_segundos: float | None = 900,
) -> AgendadorMeteorologico:
    """Monta o agendador de teste.

    `intervalo_segundos=None` propaga o padrão de produção de `AgendadorMeteorologico`
    (não o hardcoded 900 deste helper) — usado para provar que o intervalo real de
    produção é o que está em vigor, sem o teste referenciar a própria constante.
    """

    portas = PortasColetaMeteorologica(
        idempotencia=IdempotenciaFalsaInerte(),  # type: ignore[arg-type]
        areas=AreasAtivasFalsas((AREA,)),
        coletor=coletor,
        normalizador=NormalizadorInmet(),
        eventos=EventosFalsos(),  # type: ignore[arg-type]
        sincronizacoes=SincronizacoesFalsas(),  # type: ignore[arg-type]
        tentativas=TentativasFalsasInertes(),  # type: ignore[arg-type]
        execucoes=ExecucoesFalsasInertes(),
        excecoes=ExcecoesFalsasInertes(),
        cenario_sintetico=coletor,
        cenarios_ativados=CenariosAtivadosFalsosInertes(),  # type: ignore[arg-type]
    )
    servico = ServicoColetaMeteorologica(portas)
    if intervalo_segundos is None:
        return AgendadorMeteorologico(servico, portas.areas, relogio=relogio)
    return AgendadorMeteorologico(
        servico, portas.areas, relogio=relogio, intervalo_segundos=intervalo_segundos
    )


def test_dispara_coleta_imediatamente_ao_iniciar_sem_esperar_o_primeiro_intervalo() -> None:
    async def cenario() -> None:
        relogio = RelogioControlavel()
        coletor = AdaptadorInmetFalso(resposta=RESPOSTA_VALIDA)
        agendador = montar_agendador(relogio, coletor)

        tarefa = asyncio.create_task(agendador.executar_em_segundo_plano())
        for _ in range(50):
            if coletor.chamadas:
                break
            await asyncio.sleep(0)

        assert len(coletor.chamadas) == 1

        tarefa.cancel()
        with suppress(asyncio.CancelledError):
            await tarefa

    asyncio.run(cenario())


def test_dorme_exatamente_o_intervalo_configurado_entre_coletas() -> None:
    async def cenario() -> None:
        relogio = RelogioControlavel()
        coletor = AdaptadorInmetFalso(resposta=RESPOSTA_VALIDA)
        agendador = montar_agendador(relogio, coletor, intervalo_segundos=900)

        tarefa = asyncio.create_task(agendador.executar_em_segundo_plano())
        for _ in range(50):
            if relogio.chamadas:
                break
            await asyncio.sleep(0)

        assert relogio.chamadas == [900]
        assert len(coletor.chamadas) == 1

        relogio.liberar()
        for _ in range(50):
            if len(coletor.chamadas) == 2:
                break
            await asyncio.sleep(0)

        assert len(coletor.chamadas) == 2
        assert relogio.chamadas == [900, 900]

        tarefa.cancel()
        with suppress(asyncio.CancelledError):
            await tarefa

    asyncio.run(cenario())


def test_intervalo_padrao_de_producao_e_900_segundos() -> None:
    """Sem `intervalo_segundos` explícito, o agendador usa o padrão real de produção.

    O valor esperado (900) é fixado aqui, não importado de `INTERVALO_SEGUNDOS_COLETA` —
    do contrário, alterar a constante de produção mudaria a asserção junto com ela e o
    teste nunca discriminaria uma regressão no intervalo real (15 minutos, INMET-03).
    """

    async def cenario() -> None:
        relogio = RelogioControlavel()
        coletor = AdaptadorInmetFalso(resposta=RESPOSTA_VALIDA)
        agendador = montar_agendador(relogio, coletor, intervalo_segundos=None)

        tarefa = asyncio.create_task(agendador.executar_em_segundo_plano())
        for _ in range(50):
            if relogio.chamadas:
                break
            await asyncio.sleep(0)

        assert relogio.chamadas == [900]

        tarefa.cancel()
        with suppress(asyncio.CancelledError):
            await tarefa

    asyncio.run(cenario())


def test_task_e_cancelavel_de_forma_limpa_sem_excecao_nao_tratada() -> None:
    async def cenario() -> None:
        relogio = RelogioControlavel()
        coletor = AdaptadorInmetFalso(resposta=RESPOSTA_VALIDA)
        agendador = montar_agendador(relogio, coletor)

        tarefa = asyncio.create_task(agendador.executar_em_segundo_plano())
        for _ in range(50):
            if relogio.chamadas:
                break
            await asyncio.sleep(0)

        tarefa.cancel()
        with suppress(asyncio.CancelledError):
            await tarefa

        assert tarefa.cancelled() or tarefa.done()
        if tarefa.done() and not tarefa.cancelled():
            assert tarefa.exception() is None

    asyncio.run(cenario())


def _configuracao_para(caminho: Path) -> Configuracao:
    """Monta a configuração local determinística, sem depender do `.env` real."""

    return Configuracao(
        host_api="127.0.0.1",
        origem_frontend="http://127.0.0.1:5173",
        caminho_banco=caminho,
        url_base_inmet="https://inmet.exemplo.invalido",
        _env_file=None,
    )


def test_lifespan_da_aplicacao_inicia_e_cancela_o_agendador_sem_excecao(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`composicao/api.py` inicia a task no `lifespan` e a cancela no encerramento."""

    async def _send_bloqueado(
        self: httpx.AsyncClient, request: httpx.Request, **_: object
    ) -> httpx.Response:
        raise AssertionError(f"chamada de rede real bloqueada em teste: {request.url}")

    monkeypatch.setattr(httpx.AsyncClient, "send", _send_bloqueado)

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()

    with TestClient(criar_aplicacao(_configuracao_para(caminho))) as cliente:
        resposta = cliente.get("/api/v1/saude")
        assert resposta.status_code == 200
