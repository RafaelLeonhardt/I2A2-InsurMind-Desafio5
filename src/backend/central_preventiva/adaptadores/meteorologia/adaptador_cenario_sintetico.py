"""Adaptador que devolve o cenário sintético de contingência de granizo (RESIL-10..12)."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from central_preventiva.aplicacao.portas_meteorologia import AreaMonitorada, RespostaColetaInmet

IDENTIFICADOR_CENARIO_GRANIZO = "granizo-demonstrativo"
"""Identificador determinístico do único cenário sintético de contingência do MVP (Épico 1)."""

_INTENSIDADE_CENARIO = "31.0"
"""Mesma intensidade do evento de granizo semeado pelo Épico 1 (`semeador.py`)."""

_JANELA_CENARIO = timedelta(hours=6)
"""Mesma duração de janela (14h–20h) do evento de granizo semeado pelo Épico 1."""


class AdaptadorCenarioSintetico:
    """Implementa `ColetorMeteorologico` devolvendo o cenário sintético de granizo (AD-013).

    Usa o horário corrente (injetável para teste) para o período do evento, em vez de
    reproduzir literalmente os valores históricos do conjunto semeado (`semeador.py`) — isso
    evitaria colidir com `UNIQUE(tipo, area, periodo_inicio, periodo_fim)` (migração 0003) e
    nunca produzir um evento novo ao ativar o cenário durante uma demonstração. O
    `NormalizadorInmet` (2.1) normaliza este payload com `proveniencia = sintetico` a partir
    do marcador `_sintetico`, sem nenhuma alteração nesta história.
    """

    def __init__(self, agora: Callable[[], datetime] = lambda: datetime.now(UTC)) -> None:
        """Guarda o relógio injetável usado para datar o período do cenário."""

        self._agora = agora

    async def coletar(self, area: AreaMonitorada) -> RespostaColetaInmet:
        """Devolve o payload bruto determinístico do cenário sintético de granizo."""

        instante = self._agora()
        periodo_inicio = instante - _JANELA_CENARIO
        return RespostaColetaInmet(
            status_code=200,
            corpo={
                "_sintetico": True,
                "CD_ESTACAO": area.codigo_estacao_inmet,
                "TIPO_EVENTO_SINTETICO": "granizo",
                "INTENSIDADE": _INTENSIDADE_CENARIO,
                "PERIODO_INICIO": periodo_inicio.isoformat(),
                "PERIODO_FIM": instante.isoformat(),
                "INSTANTE_OBSERVADO": instante.isoformat(),
            },
        )
