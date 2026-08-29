"""Recurso REST/JSON de prontidão das dependências."""

from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from central_preventiva.adaptadores.prontidao.sonda_backend import SondaBackend
from central_preventiva.adaptadores.prontidao.sonda_banco_dados import SondaBancoDados
from central_preventiva.adaptadores.prontidao.sonda_inmet import SondaInmet
from central_preventiva.adaptadores.prontidao.sonda_openai import SondaOpenAI
from central_preventiva.aplicacao.prontidao import (
    PortasProntidao,
    RegistroProntidao,
    consultar_prontidao,
)
from central_preventiva.composicao.configuracao import Configuracao

TIPO_PROBLEMA = "application/problem+json"
CAMINHO_DEPENDENCIAS = "/prontidao/dependencias"


class RespostaDependencia(BaseModel):
    """Estado de prontidão de uma única dependência, pronto para exibição."""

    model_config = ConfigDict(extra="forbid")

    nome: str
    estado: str
    verificado_em: datetime | None
    causa: str | None
    impacto: str
    acao_disponivel: str


class RespostaDependencias(BaseModel):
    """Resposta pública consolidada das 4 dependências."""

    model_config = ConfigDict(extra="forbid")

    dependencias: list[RespostaDependencia]


class ProblemaProntidao(BaseModel):
    """Falha da operação de prontidão, com ocorrência, impacto e próxima ação segura."""

    model_config = ConfigDict(extra="forbid")

    codigo: str
    correlacao_id: str
    ocorrencia: str
    impacto: str
    proxima_acao: str


def problema(
    status: int,
    codigo: str,
    ocorrencia: str,
    impacto: str,
    proxima_acao: str,
) -> JSONResponse:
    """Monta a resposta `problem+json` correlacionada de uma falha de prontidão."""

    corpo = ProblemaProntidao(
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
    """Compõe o recurso de prontidão sobre as sondas reais e um registro por processo."""

    roteador = APIRouter(tags=["Prontidão"])
    registro = RegistroProntidao()

    chave_openai = configuracao.chave_openai
    portas = PortasProntidao(
        backend=SondaBackend(),
        banco_dados=SondaBancoDados(configuracao.caminho_banco),
        inmet=SondaInmet(configuracao.url_base_inmet),
        openai=SondaOpenAI(chave_openai.get_secret_value()) if chave_openai else None,
    )

    @roteador.get(
        CAMINHO_DEPENDENCIAS,
        response_model=RespostaDependencias,
        status_code=200,
        summary="Consultar a prontidão das dependências",
        description=(
            "Devolve o estado mais recente de backend, banco de dados, INMET e OpenAI. "
            "Backend e banco de dados são recomputados a cada chamada; INMET e OpenAI, na "
            "primeira consulta, disparam a verificação em segundo plano e retornam "
            "'verificando'."
        ),
        responses={200: {"description": "Estado de prontidão das 4 dependências."}},
    )
    async def consultar() -> RespostaDependencias:  # pyright: ignore[reportUnusedFunction]
        """Traduz `consultar_prontidao` para o contrato REST/JSON público."""

        estados = await consultar_prontidao(portas, registro)
        return RespostaDependencias(
            dependencias=[
                RespostaDependencia(
                    nome=estado.nome,
                    estado=str(estado.estado),
                    verificado_em=estado.verificado_em,
                    causa=estado.causa,
                    impacto=estado.impacto,
                    acao_disponivel=estado.acao_disponivel,
                )
                for estado in estados
            ]
        )

    return roteador
