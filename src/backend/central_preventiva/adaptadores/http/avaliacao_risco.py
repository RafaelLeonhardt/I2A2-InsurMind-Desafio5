"""Recurso REST/JSON de detalhe da decisão de risco de uma execução (RISCO-11, RISCO-12)."""

from datetime import datetime
from uuid import UUID, uuid4

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from central_preventiva.adaptadores.persistencia.repositorio_avaliacoes_risco import (
    RepositorioAvaliacoesRisco,
)
from central_preventiva.composicao.configuracao import Configuracao

TIPO_PROBLEMA = "application/problem+json"
CAMINHO_AVALIACAO_RISCO = "/execucoes/{execucao_id}/avaliacao-risco"


class RespostaCriterio(BaseModel):
    """Um critério avaliado: operando, valor observado, resultado e justificativa."""

    model_config = ConfigDict(extra="forbid")

    operando: str = Field(description="O que foi comparado (ex.: área aplicável, intensidade).")
    valor_observado: str = Field(description="Valor observado no evento para este critério.")
    atende: bool = Field(description="Se o valor observado atende ao critério.")
    justificativa: str = Field(description="Explicação em português brasileiro do resultado.")


class RespostaAvaliacaoRisco(BaseModel):
    """Snapshot público da avaliação de relevância meteorológica de uma execução."""

    model_config = ConfigDict(extra="forbid")

    execucao_id: UUID = Field(description="Identificador da execução avaliada.")
    evento_id: UUID = Field(description="Identificador do evento meteorológico avaliado.")
    regra_id: UUID | None = Field(
        description="Identificador da regra aplicada, ou nulo se não havia regra ativa."
    )
    regra_versao: int | None = Field(
        description="Versão da regra no momento da avaliação, ou nulo se não havia regra ativa."
    )
    relevante: bool = Field(description="Se o evento foi considerado relevante.")
    criterios: list[RespostaCriterio] = Field(description="Critérios avaliados, na ordem aplicada.")
    motivo: str = Field(description="Motivo tipado do resultado.")
    criado_em: datetime = Field(description="Instante RFC 3339 em UTC da avaliação.")


class ProblemaAvaliacaoRisco(BaseModel):
    """Falha da consulta de avaliação de risco, com ocorrência, impacto e próxima ação segura."""

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
    """Monta a resposta `problem+json` correlacionada de uma falha de avaliação de risco."""

    corpo = ProblemaAvaliacaoRisco(
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
    """Compõe o recurso de detalhe da avaliação de risco sobre o banco operacional configurado."""

    roteador = APIRouter(tags=["Risco"])
    avaliacoes_repo = RepositorioAvaliacoesRisco(configuracao.caminho_banco)

    @roteador.get(
        CAMINHO_AVALIACAO_RISCO,
        response_model=RespostaAvaliacaoRisco,
        status_code=200,
        summary="Consultar o detalhe da decisão de risco de uma execução",
        description=(
            "Devolve o operando, o valor observado, o resultado e a justificativa de cada "
            "critério da decisão de risco já tomada para a execução, sem recalcular nada."
        ),
        responses={
            200: {"description": "Avaliação de risco encontrada."},
            404: {
                "description": "A execução ainda não tem avaliação de risco.",
                "model": ProblemaAvaliacaoRisco,
            },
            422: {
                "description": "O identificador da execução não é um UUID válido.",
                "model": ProblemaAvaliacaoRisco,
            },
        },
    )
    async def consultar_avaliacao_risco(  # pyright: ignore[reportUnusedFunction]
        execucao_id: str,
    ) -> RespostaAvaliacaoRisco | JSONResponse:
        """Traduz `RepositorioAvaliacoesRisco.obter_por_execucao` para o contrato público.

        `execucao_id` é recebido como `str` (não `UUID`) para que um formato inválido
        produza a resposta `problem+json` própria deste recurso, em vez do `422`
        genérico e sem descrições (`HTTPValidationError`) que o FastAPI geraria por
        coerção automática de tipo.
        """

        try:
            execucao_uuid = UUID(execucao_id)
        except ValueError:
            return problema(
                422,
                "execucao_id_invalido",
                f"'{execucao_id}' não é um identificador de execução válido.",
                "Nenhum detalhe de decisão de risco pode ser exibido.",
                "Consulte a execução pelo identificador UUID retornado pela API.",
            )

        avaliacao = avaliacoes_repo.obter_por_execucao(execucao_uuid)
        if avaliacao is None:
            return problema(
                404,
                "avaliacao_risco_inexistente",
                f"A execução '{execucao_id}' ainda não tem avaliação de risco.",
                "Nenhum detalhe de decisão de risco pode ser exibido.",
                "Aguarde a execução alcançar a etapa de avaliação de risco e consulte de novo.",
            )

        return RespostaAvaliacaoRisco(
            execucao_id=avaliacao.execucao_id,
            evento_id=avaliacao.evento_id,
            regra_id=avaliacao.regra_id,
            regra_versao=avaliacao.regra_versao,
            relevante=avaliacao.relevante,
            criterios=[
                RespostaCriterio(
                    operando=criterio.operando,
                    valor_observado=criterio.valor_observado,
                    atende=criterio.atende,
                    justificativa=criterio.justificativa,
                )
                for criterio in avaliacao.criterios
            ],
            motivo=avaliacao.motivo,
            criado_em=avaliacao.criado_em,
        )

    return roteador
