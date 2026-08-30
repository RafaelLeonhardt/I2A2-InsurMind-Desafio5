"""Task `asyncio` única de coleta meteorológica automática (AD-006)."""

import asyncio
from typing import Protocol
from uuid import uuid4

from central_preventiva.aplicacao.coleta_meteorologica import ServicoColetaMeteorologica
from central_preventiva.aplicacao.portas_meteorologia import (
    INTERVALO_SEGUNDOS_COLETA,
    OrigemSincronizacao,
    RepositorioAreasMonitoradas,
)


class RelogioAgendador(Protocol):
    """Abstrai a espera entre coletas, para permitir um dublê determinístico em teste."""

    async def aguardar(self, segundos: float) -> None:
        """Aguarda o intervalo informado antes do próximo ciclo."""
        ...


class RelogioReal:
    """Relógio real, apoiado em `asyncio.sleep`."""

    async def aguardar(self, segundos: float) -> None:
        """Aguarda o intervalo real de produção via `asyncio.sleep`."""

        await asyncio.sleep(segundos)


class AgendadorMeteorologico:
    """Dispara a coleta meteorológica automática uma vez no boot e a cada intervalo.

    Roda como a única task `asyncio` in-process do agendamento (AD-006): sem biblioteca
    de agendamento nova, cancelável de forma limpa no `shutdown` do `lifespan`.
    """

    def __init__(
        self,
        servico: ServicoColetaMeteorologica,
        areas: RepositorioAreasMonitoradas,
        relogio: RelogioAgendador | None = None,
        intervalo_segundos: float = INTERVALO_SEGUNDOS_COLETA,
    ) -> None:
        """Guarda as dependências e o relógio (real por padrão, dublê em teste)."""

        self._servico = servico
        self._areas = areas
        self._relogio = relogio if relogio is not None else RelogioReal()
        self._intervalo_segundos = intervalo_segundos

    async def executar_em_segundo_plano(self) -> None:
        """Laço `while True`: coleta todas as áreas ativas, aguarda o intervalo, repete.

        Dispara a primeira coleta imediatamente, sem esperar o primeiro intervalo.
        `asyncio.CancelledError` é deixado propagar (comportamento padrão de
        cancelamento cooperativo): o chamador no `lifespan` a suprime ao cancelar
        a task, sem nunca gerar uma exceção não tratada.
        """

        while True:
            await self._coletar_areas_ativas()
            await self._relogio.aguardar(self._intervalo_segundos)

    async def _coletar_areas_ativas(self) -> None:
        """Executa uma coleta automática para cada área monitorada ativa."""

        for area in self._areas.listar_ativas():
            await self._servico.executar_coleta(area, uuid4(), OrigemSincronizacao.AUTOMATICA)
