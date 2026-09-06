"""Recurso REST/JSON da lista de segurados sintéticos disponíveis (SELETOR-01).

`GET /segurados` lista todos os segurados do conjunto sintético semeado, para popular o
seletor demonstrativo "Visualizar como" — nenhum dado sensível, só id e nome. Lista vazia
quando o seed ainda não foi restaurado; a interface explica a ausência (nenhum erro HTTP
dedicado, ver design.md).
"""

from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from central_preventiva.adaptadores.persistencia.repositorio_segurados import (
    RepositorioSegurados,
)
from central_preventiva.composicao.configuracao import Configuracao

CAMINHO_LISTA_SEGURADOS = "/segurados"


class RespostaSeguradoListado(BaseModel):
    """Um segurado sintético disponível para seleção."""

    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(description="Identificador do segurado sintético.")
    nome: str = Field(description="Nome do segurado sintético.")


class RespostaListaSegurados(BaseModel):
    """A lista completa de segurados sintéticos do seed."""

    model_config = ConfigDict(extra="forbid")

    segurados: list[RespostaSeguradoListado] = Field(
        description="Todos os segurados sintéticos do seed, ordenados por nome."
    )


def criar_roteador(configuracao: Configuracao) -> APIRouter:
    """Compõe o recurso da lista de segurados sintéticos disponíveis."""

    roteador = APIRouter(tags=["Segurados"])
    repositorio = RepositorioSegurados(configuracao.caminho_banco)

    @roteador.get(
        CAMINHO_LISTA_SEGURADOS,
        response_model=RespostaListaSegurados,
        status_code=200,
        summary="Listar os segurados sintéticos disponíveis",
        description=(
            "Devolve todos os segurados do conjunto sintético semeado, ordenados por "
            "nome, para popular o seletor demonstrativo 'Visualizar como'. Lista vazia "
            "quando os dados sintéticos ainda não foram restaurados."
        ),
        responses={
            200: {"description": "Consulta realizada, com ou sem segurados."},
        },
    )
    async def listar_segurados() -> RespostaListaSegurados:  # pyright: ignore[reportUnusedFunction]
        """Traduz `RepositorioSegurados.listar_sinteticos` para o contrato público."""

        segurados = repositorio.listar_sinteticos()
        return RespostaListaSegurados(
            segurados=[
                RespostaSeguradoListado(id=segurado.id, nome=segurado.nome)
                for segurado in segurados
            ]
        )

    return roteador
