"""Caso de uso de consulta do segurado sintético padrão."""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from central_preventiva.dominio.identificadores_demonstracao import SEGURADO_PADRAO
from central_preventiva.dominio.segurado import Segurado


class PortaSegurados(Protocol):
    """Consulta um segurado sintético pelo seu identificador."""

    def buscar_por_id(self, id: UUID) -> Segurado | None:
        """Retorna o segurado com o id informado, ou `None` se não existir."""
        ...


@dataclass(frozen=True, slots=True)
class PortasContexto:
    """Agrupa as portas necessárias ao caso de uso de contexto demonstrativo."""

    segurados: PortaSegurados


class SeguradoPadraoAusente(Exception):
    """Indica que o segurado sintético padrão ainda não existe no banco operacional."""

    def __init__(self) -> None:
        """Monta a mensagem em português da ausência do segurado padrão."""

        super().__init__(
            "O segurado sintético padrão ainda não existe. Execute a inicialização/restauração "
            "dos dados sintéticos e tente novamente."
        )


def consultar_segurado_padrao(portas: PortasContexto) -> Segurado:
    """Consulta o segurado sintético padrão, levantando `SeguradoPadraoAusente` se ausente."""

    encontrado = portas.segurados.buscar_por_id(SEGURADO_PADRAO)
    if encontrado is None:
        raise SeguradoPadraoAusente
    return encontrado
