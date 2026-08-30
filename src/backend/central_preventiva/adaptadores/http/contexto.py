"""Recurso REST/JSON de consulta do segurado sintético padrão."""

from uuid import uuid4

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from central_preventiva.adaptadores.persistencia.repositorio_segurados import (
    RepositorioSegurados,
)
from central_preventiva.aplicacao.contexto import (
    PortasContexto,
    SeguradoPadraoAusente,
    consultar_segurado_padrao,
)
from central_preventiva.composicao.configuracao import Configuracao

TIPO_PROBLEMA = "application/problem+json"
CAMINHO_SEGURADO_PADRAO = "/segurados/padrao"


class RespostaSeguradoPadrao(BaseModel):
    """Resposta pública do segurado sintético padrão."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="Identificador opaco do segurado sintético padrão.")
    nome: str = Field(description="Nome do segurado sintético padrão.")


class ProblemaContexto(BaseModel):
    """Falha da consulta do segurado padrão, com ocorrência, impacto e próxima ação segura."""

    model_config = ConfigDict(extra="forbid")

    codigo: str = Field(description="Código estável que identifica o tipo da falha.")
    correlacao_id: str = Field(description="Identificador único desta ocorrência de falha.")
    ocorrencia: str = Field(description="O que aconteceu, em português brasileiro.")
    impacto: str = Field(description="Efeito prático da falha para quem consultou o recurso.")
    proxima_acao: str = Field(description="Próxima ação segura recomendada para contornar a falha.")


def problema(
    status: int,
    codigo: str,
    ocorrencia: str,
    impacto: str,
    proxima_acao: str,
) -> JSONResponse:
    """Monta a resposta `problem+json` correlacionada de uma falha de contexto."""

    corpo = ProblemaContexto(
        codigo=codigo,
        correlacao_id=str(uuid4()),
        ocorrencia=ocorrencia,
        impacto=impacto,
        proxima_acao=proxima_acao,
    )
    return JSONResponse(
        status_code=status,
        media_type=TIPO_PROBLEMA,
        content=corpo.model_dump(),
    )


def criar_roteador(configuracao: Configuracao) -> APIRouter:
    """Compõe o recurso de contexto sobre o banco operacional configurado."""

    roteador = APIRouter(tags=["Segurados"])
    portas = PortasContexto(segurados=RepositorioSegurados(configuracao.caminho_banco))

    @roteador.get(
        CAMINHO_SEGURADO_PADRAO,
        response_model=RespostaSeguradoPadrao,
        status_code=200,
        summary="Consultar o segurado sintético padrão",
        description=(
            "Devolve o segurado sintético padrão usado na visão de Segurado da demonstração."
        ),
        responses={
            200: {"description": "Segurado sintético padrão encontrado."},
            503: {
                "description": "Dados sintéticos ainda não restaurados.",
                "model": ProblemaContexto,
            },
        },
    )
    async def consultar() -> RespostaSeguradoPadrao | JSONResponse:  # pyright: ignore[reportUnusedFunction]
        """Traduz `consultar_segurado_padrao` para o contrato REST/JSON público."""

        try:
            segurado = consultar_segurado_padrao(portas)
        except SeguradoPadraoAusente:
            return problema(
                503,
                "segurado_padrao_ausente",
                "O segurado sintético padrão ainda não existe no banco operacional.",
                "A visão de Segurado não pode exibir o segurado ativo.",
                "Execute a inicialização/restauração dos dados sintéticos e tente novamente.",
            )

        return RespostaSeguradoPadrao(id=str(segurado.id), nome=segurado.nome)

    return roteador
