"""Recurso REST/JSON da lista detalhada de segurados sintéticos para o admin (LISTASEG-01..03).

`GET /segurados/detalhado` devolve nome, área, apólice mais recente e canal preferencial de
cada segurado sintético do seed — usado pela superfície "Segurados" do perfil Administrador
(História 6.4) para auditar a base sobre a qual as regras preventivas operam. Distinto de
`GET /segurados` (`lista_segurados.py`, SELETOR-01), que continua devolvendo só id/nome para
popular o seletor demonstrativo "Visualizar como" do perfil Segurado — este recurso novo não
o altera nem o substitui.
"""

from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from central_preventiva.adaptadores.persistencia.repositorio_segurados import (
    RepositorioSegurados,
)
from central_preventiva.composicao.configuracao import Configuracao

CAMINHO_LISTA_SEGURADOS_DETALHADO = "/segurados/detalhado"


class RespostaSeguradoDetalhado(BaseModel):
    """Um segurado sintético com os dados básicos exibidos ao administrador."""

    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(description="Identificador do segurado sintético.")
    nome: str = Field(description="Nome do segurado sintético.")
    codigo_ibge_area: str = Field(
        description="Código IBGE da área do segurado (proxy sintético de bairro/região)."
    )
    apolice_numero: str | None = Field(
        description="Número da apólice mais recente do segurado, ou nulo se ele não tiver "
        "nenhuma apólice."
    )
    canal_preferido: str = Field(
        description="Canal de comunicação preferencial do segurado (`whatsapp`/`email`/`sms`)."
    )


class RespostaListaSeguradosDetalhado(BaseModel):
    """A lista detalhada de todos os segurados sintéticos do seed."""

    model_config = ConfigDict(extra="forbid")

    segurados: list[RespostaSeguradoDetalhado] = Field(
        description="Todos os segurados sintéticos do seed, com área, apólice mais "
        "recente e canal, ordenados por nome."
    )


def criar_roteador(configuracao: Configuracao) -> APIRouter:
    """Compõe o recurso da lista detalhada de segurados sintéticos para o admin."""

    roteador = APIRouter(tags=["Segurados"])
    repositorio = RepositorioSegurados(configuracao.caminho_banco)

    @roteador.get(
        CAMINHO_LISTA_SEGURADOS_DETALHADO,
        response_model=RespostaListaSeguradosDetalhado,
        status_code=200,
        summary="Listar os segurados sintéticos com dados detalhados para o admin",
        description=(
            "Devolve nome, área, apólice mais recente e canal preferencial de cada "
            "segurado do conjunto sintético semeado, ordenados por nome, para a "
            "superfície 'Segurados' do perfil Administrador auditar a base. Lista vazia "
            "quando os dados sintéticos ainda não foram restaurados; apólice nula quando "
            "o segurado não tiver nenhuma apólice."
        ),
        responses={
            200: {"description": "Consulta realizada, com ou sem segurados."},
        },
    )
    async def listar_segurados_detalhado() -> RespostaListaSeguradosDetalhado:  # pyright: ignore[reportUnusedFunction]
        """Traduz `RepositorioSegurados.listar_sinteticos_detalhado` para o contrato público."""

        segurados = repositorio.listar_sinteticos_detalhado()
        return RespostaListaSeguradosDetalhado(
            segurados=[
                RespostaSeguradoDetalhado(
                    id=segurado.id,
                    nome=segurado.nome,
                    codigo_ibge_area=segurado.codigo_ibge_area,
                    apolice_numero=segurado.apolice_numero,
                    canal_preferido=segurado.canal_preferido,
                )
                for segurado in segurados
            ]
        )

    return roteador
