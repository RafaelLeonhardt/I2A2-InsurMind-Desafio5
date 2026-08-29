"""Fábrica da aplicação FastAPI executada somente na interface local."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from central_preventiva.adaptadores.http.contexto import (
    criar_roteador as criar_roteador_contexto,
)
from central_preventiva.adaptadores.http.dados_sinteticos import (
    criar_roteador as criar_roteador_dados_sinteticos,
)
from central_preventiva.adaptadores.http.prontidao import (
    criar_roteador as criar_roteador_prontidao,
)
from central_preventiva.adaptadores.http.saude import roteador as roteador_saude
from central_preventiva.composicao.configuracao import Configuracao, obter_configuracao


def criar_aplicacao(configuracao: Configuracao | None = None) -> FastAPI:
    """Compõe a API mínima após validar os limites de execução local."""

    configuracao_ativa = configuracao or obter_configuracao()
    aplicacao = FastAPI(
        title="Central Preventiva",
        summary="API local da prova de conceito educacional.",
        description=(
            "Disponibiliza somente os recursos implementados da Central Preventiva, "
            "com dados sintéticos e sem envio real."
        ),
        version="0.1.0",
    )
    aplicacao.add_middleware(
        CORSMiddleware,
        allow_origins=[configuracao_ativa.origem_frontend],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Accept", "Content-Type", "Idempotency-Key"],
    )
    aplicacao.include_router(roteador_saude, prefix="/api/v1")
    aplicacao.include_router(
        criar_roteador_dados_sinteticos(configuracao_ativa),
        prefix="/api/v1",
    )
    aplicacao.include_router(
        criar_roteador_prontidao(configuracao_ativa),
        prefix="/api/v1",
    )
    aplicacao.include_router(
        criar_roteador_contexto(configuracao_ativa),
        prefix="/api/v1",
    )
    return aplicacao
