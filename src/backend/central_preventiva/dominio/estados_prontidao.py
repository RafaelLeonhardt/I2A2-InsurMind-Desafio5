"""Estados canônicos da prontidão de uma dependência e sua classificação terminal."""

from enum import StrEnum


class EstadoProntidao(StrEnum):
    """Enumera os estados possíveis da prontidão de uma dependência."""

    VERIFICANDO = "verificando"
    DISPONIVEL = "disponivel"
    DEGRADADA = "degradada"
    INDISPONIVEL = "indisponivel"


ESTADOS_TERMINAIS: frozenset[EstadoProntidao] = frozenset(
    {
        EstadoProntidao.DISPONIVEL,
        EstadoProntidao.DEGRADADA,
        EstadoProntidao.INDISPONIVEL,
    }
)
"""Estados a partir dos quais a verificação de prontidão não avança mais."""


def eh_terminal(estado: EstadoProntidao) -> bool:
    """Informa se o estado encerra a verificação de prontidão."""

    return estado in ESTADOS_TERMINAIS
