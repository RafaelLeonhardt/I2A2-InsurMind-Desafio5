"""Recurso REST/JSON de restauração dos dados sintéticos da demonstração."""

from datetime import datetime
from hashlib import sha256
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from central_preventiva.adaptadores.persistencia.repositorio_execucoes import RepositorioExecucoes
from central_preventiva.adaptadores.persistencia.repositorio_idempotencia import (
    RepositorioIdempotencia,
)
from central_preventiva.adaptadores.persistencia.semeador import SemeadorDadosSinteticos
from central_preventiva.aplicacao.portas_persistencia import (
    ConflitoIdempotencia,
    ExecucaoAtivaImpedeRestauracao,
    NaoInicializado,
)
from central_preventiva.aplicacao.restauracao import (
    PortasRestauracao,
    restaurar_dados_sinteticos,
)
from central_preventiva.composicao.configuracao import Configuracao

TIPO_PROBLEMA = "application/problem+json"
CAMINHO_RESTAURACOES = "/dados-sinteticos/restauracoes"


class RespostaRestauracao(BaseModel):
    """Resposta pública de uma restauração concluída."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["restaurado"]
    restaurado_em: datetime


class ProblemaRestauracao(BaseModel):
    """Falha da restauração, com ocorrência, impacto e próxima ação segura."""

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
    """Monta a resposta `problem+json` correlacionada de uma falha da restauração."""

    corpo = ProblemaRestauracao(
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
    """Compõe o recurso de restauração sobre o banco operacional configurado."""

    roteador = APIRouter(tags=["Dados sintéticos"])
    portas = PortasRestauracao(
        idempotencia=RepositorioIdempotencia(configuracao.caminho_banco),
        execucoes=RepositorioExecucoes(configuracao.caminho_banco),
        dados=SemeadorDadosSinteticos(configuracao.caminho_banco),
    )

    @roteador.post(
        CAMINHO_RESTAURACOES,
        response_model=RespostaRestauracao,
        status_code=201,
        summary="Restaurar os dados sintéticos da demonstração",
        description=(
            "Repõe o conjunto sintético versionado em uma única transação. "
            "Exige o cabeçalho `Idempotency-Key` em toda requisição."
        ),
        responses={
            201: {"description": "Dados sintéticos restaurados."},
            409: {
                "description": "Restauração recusada sem qualquer mutação.",
                "model": ProblemaRestauracao,
            },
            422: {
                "description": "Requisição sem o cabeçalho `Idempotency-Key`.",
                "model": ProblemaRestauracao,
            },
            500: {
                "description": "Falha ao concluir a transação de restauração.",
                "model": ProblemaRestauracao,
            },
        },
    )
    async def restaurar(  # pyright: ignore[reportUnusedFunction]
        requisicao: Request,
        idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    ) -> RespostaRestauracao | JSONResponse:
        """Traduz o caso de uso de restauração para o contrato REST/JSON público."""

        if idempotency_key is None or not idempotency_key.strip():
            return problema(
                422,
                "idempotency_key_ausente",
                "A requisição de restauração não informou o cabeçalho Idempotency-Key.",
                "Nenhuma alteração foi feita nos dados sintéticos.",
                "Repita a requisição incluindo um cabeçalho Idempotency-Key único.",
            )

        hash_requisicao = sha256(await requisicao.body()).hexdigest()

        try:
            resultado = restaurar_dados_sinteticos(portas, idempotency_key, hash_requisicao)
        except ConflitoIdempotencia:
            return problema(
                409,
                "conflito_idempotencia",
                "A chave de idempotência já foi usada com outro conteúdo de requisição.",
                "Nenhuma restauração foi executada e os dados permanecem como estavam.",
                "Gere uma nova Idempotency-Key para solicitar outra restauração.",
            )
        except ExecucaoAtivaImpedeRestauracao:
            return problema(
                409,
                "execucao_ativa_impede_restauracao",
                "Há uma execução preventiva ativa em estado não terminal.",
                "Nenhuma restauração foi executada e os dados permanecem como estavam.",
                "Aguarde a conclusão da execução em andamento e solicite a restauração de novo.",
            )
        except NaoInicializado:
            return problema(
                409,
                "nao_inicializado",
                "Os dados sintéticos ainda não foram inicializados neste banco.",
                "Nenhuma restauração foi executada porque não há conjunto versionado a repor.",
                "Execute o comando de inicialização antes de solicitar a restauração.",
            )
        except Exception:
            return problema(
                500,
                "falha_restauracao",
                "A transação de restauração não pôde ser concluída.",
                "O conjunto de dados anterior foi preservado íntegro e continua consultável.",
                "Verifique o banco operacional local e solicite a restauração novamente.",
            )

        return RespostaRestauracao(status=resultado.status, restaurado_em=resultado.restaurado_em)

    return roteador
