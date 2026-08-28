"""Contrato mínimo da saúde do processo backend."""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class SaudeDoProcesso:
    """Representa somente a disponibilidade do processo da API."""

    status: Literal["disponivel"] = "disponivel"
    ambiente: Literal["educacional"] = "educacional"


def consultar_saude() -> SaudeDoProcesso:
    """Retorna a disponibilidade local do processo sem sondar integrações futuras."""

    return SaudeDoProcesso()
