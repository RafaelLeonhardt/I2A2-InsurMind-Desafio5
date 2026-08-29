"""Modelo de domínio mínimo de um segurado sintético."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Segurado:
    """Identidade mínima de um segurado sintético (id e nome)."""

    id: UUID
    nome: str
