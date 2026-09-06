"""Fábrica da aplicação FastAPI executada somente na interface local."""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from central_preventiva.adaptadores.http.alerta_segurado import (
    criar_roteador as criar_roteador_alerta_segurado,
)
from central_preventiva.adaptadores.http.apolice_segurado import (
    criar_roteador as criar_roteador_apolice_segurado,
)
from central_preventiva.adaptadores.http.avaliacao_risco import (
    criar_roteador as criar_roteador_avaliacao_risco,
)
from central_preventiva.adaptadores.http.avaliacoes_criticas import (
    criar_roteador as criar_roteador_avaliacoes_criticas,
)
from central_preventiva.adaptadores.http.contexto import (
    criar_roteador as criar_roteador_contexto,
)
from central_preventiva.adaptadores.http.dados_sinteticos import (
    criar_roteador as criar_roteador_dados_sinteticos,
)
from central_preventiva.adaptadores.http.detalhe_resultado import (
    criar_roteador as criar_roteador_detalhe_resultado,
)
from central_preventiva.adaptadores.http.elegibilidade import (
    criar_roteador as criar_roteador_elegibilidade,
)
from central_preventiva.adaptadores.http.execucao_preventiva import (
    criar_roteador as criar_roteador_execucao_preventiva,
)
from central_preventiva.adaptadores.http.execucao_preventiva import montar_portas_execucao
from central_preventiva.adaptadores.http.explicacao_comunicado import (
    criar_roteador as criar_roteador_explicacao_comunicado,
)
from central_preventiva.adaptadores.http.linha_do_tempo import (
    criar_roteador as criar_roteador_linha_do_tempo,
)
from central_preventiva.adaptadores.http.lista_alertas_segurado import (
    criar_roteador as criar_roteador_lista_alertas_segurado,
)
from central_preventiva.adaptadores.http.mensagens import (
    criar_roteador as criar_roteador_mensagens,
)
from central_preventiva.adaptadores.http.meteorologia import (
    criar_roteador as criar_roteador_meteorologia,
)
from central_preventiva.adaptadores.http.meteorologia import (
    montar_portas_coleta,
)
from central_preventiva.adaptadores.http.preflight_ia import (
    criar_roteador as criar_roteador_preflight_ia,
)
from central_preventiva.adaptadores.http.prontidao import (
    criar_roteador as criar_roteador_prontidao,
)
from central_preventiva.adaptadores.http.proveniencia import (
    criar_roteador as criar_roteador_proveniencia,
)
from central_preventiva.adaptadores.http.regras import (
    criar_roteador as criar_roteador_regras,
)
from central_preventiva.adaptadores.http.resultados import (
    criar_roteador as criar_roteador_resultados,
)
from central_preventiva.adaptadores.http.revisao_lote import (
    criar_roteador as criar_roteador_revisao_lote,
)
from central_preventiva.adaptadores.http.saude import roteador as roteador_saude
from central_preventiva.adaptadores.http.simulacao import (
    criar_roteador as criar_roteador_simulacao,
)
from central_preventiva.adaptadores.http.visualizacao_comunicado import (
    criar_roteador as criar_roteador_visualizacao_comunicado,
)
from central_preventiva.aplicacao.coleta_meteorologica import ServicoColetaMeteorologica
from central_preventiva.aplicacao.gerenciador_execucoes import GerenciadorExecucoes
from central_preventiva.composicao.agendador_meteorologico import AgendadorMeteorologico
from central_preventiva.composicao.configuracao import Configuracao, obter_configuracao


@asynccontextmanager
async def _lifespan(aplicacao: FastAPI) -> AsyncGenerator[None]:
    """Retoma execuções não terminais e inicia o agendador meteorológico no boot,
    cancelando-o de forma limpa no shutdown (AD-006).

    A retomada (RUNNER-07) roda antes do agendador começar a produzir novas coletas,
    para que nenhuma execução pendente de antes do reinício compita por atenção com
    coletas novas antes de ser resolvida.
    """

    configuracao_ativa: Configuracao = aplicacao.state.configuracao
    gerenciador = GerenciadorExecucoes(montar_portas_execucao(configuracao_ativa))
    await gerenciador.retomar_pendentes()

    portas = montar_portas_coleta(configuracao_ativa)
    agendador = AgendadorMeteorologico(ServicoColetaMeteorologica(portas), portas.areas)
    tarefa = asyncio.create_task(agendador.executar_em_segundo_plano())
    try:
        yield
    finally:
        tarefa.cancel()
        with suppress(asyncio.CancelledError):
            await tarefa


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
        lifespan=_lifespan,
    )
    aplicacao.state.configuracao = configuracao_ativa
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
    aplicacao.include_router(
        criar_roteador_meteorologia(configuracao_ativa),
        prefix="/api/v1",
    )
    aplicacao.include_router(
        criar_roteador_avaliacao_risco(configuracao_ativa),
        prefix="/api/v1",
    )
    aplicacao.include_router(
        criar_roteador_regras(configuracao_ativa),
        prefix="/api/v1",
    )
    aplicacao.include_router(
        criar_roteador_elegibilidade(configuracao_ativa),
        prefix="/api/v1",
    )
    aplicacao.include_router(
        criar_roteador_execucao_preventiva(configuracao_ativa),
        prefix="/api/v1",
    )
    aplicacao.include_router(
        criar_roteador_preflight_ia(configuracao_ativa),
        prefix="/api/v1",
    )
    aplicacao.include_router(
        criar_roteador_mensagens(configuracao_ativa),
        prefix="/api/v1",
    )
    aplicacao.include_router(
        criar_roteador_avaliacoes_criticas(configuracao_ativa),
        prefix="/api/v1",
    )
    aplicacao.include_router(
        criar_roteador_proveniencia(configuracao_ativa),
        prefix="/api/v1",
    )
    aplicacao.include_router(
        criar_roteador_revisao_lote(configuracao_ativa),
        prefix="/api/v1",
    )
    aplicacao.include_router(
        criar_roteador_simulacao(configuracao_ativa),
        prefix="/api/v1",
    )
    aplicacao.include_router(
        criar_roteador_resultados(configuracao_ativa),
        prefix="/api/v1",
    )
    aplicacao.include_router(
        criar_roteador_detalhe_resultado(configuracao_ativa),
        prefix="/api/v1",
    )
    aplicacao.include_router(
        criar_roteador_visualizacao_comunicado(configuracao_ativa),
        prefix="/api/v1",
    )
    aplicacao.include_router(
        criar_roteador_linha_do_tempo(configuracao_ativa),
        prefix="/api/v1",
    )
    aplicacao.include_router(
        criar_roteador_alerta_segurado(configuracao_ativa),
        prefix="/api/v1",
    )
    aplicacao.include_router(
        criar_roteador_lista_alertas_segurado(configuracao_ativa),
        prefix="/api/v1",
    )
    aplicacao.include_router(
        criar_roteador_apolice_segurado(configuracao_ativa),
        prefix="/api/v1",
    )
    aplicacao.include_router(
        criar_roteador_explicacao_comunicado(configuracao_ativa),
        prefix="/api/v1",
    )
    return aplicacao
