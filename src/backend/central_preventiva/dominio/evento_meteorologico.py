"""Modelo de domínio de um evento meteorológico normalizado."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class TipoEventoMeteorologico(StrEnum):
    """Tipos aceitos de evento, alinhados ao `CHECK` de `eventos_meteorologicos.tipo`."""

    CHUVA_INTENSA = "chuva_intensa"
    GRANIZO = "granizo"


class ProvenienciaEvento(StrEnum):
    """Origem do evento, alinhada ao `CHECK` de `eventos_meteorologicos.proveniencia`."""

    REAL_INMET = "real_inmet"
    SINTETICO = "sintetico"


@dataclass(frozen=True, slots=True)
class EventoMeteorologico:
    """Evento meteorológico interno, já normalizado a partir de uma fonte externa ou sintética."""

    id: UUID
    tipo: TipoEventoMeteorologico
    area: str
    periodo_inicio: datetime
    periodo_fim: datetime
    intensidade: float
    proveniencia: ProvenienciaEvento
    instante_observado: datetime
