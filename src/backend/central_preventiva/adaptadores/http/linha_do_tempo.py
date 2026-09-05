"""Recurso REST/JSON da linha do tempo ponta a ponta e da busca de execuções (TIMELINE-01,
08, 09).

`GET /execucoes/{execucao_id}/linha-do-tempo` é uma leitura pura sobre `ServicoLinhaDoTempo`:
reconstrói a cronologia completa do DuckDB a cada chamada, sem repetir nenhuma transição.
`GET /execucoes` busca execuções por segurado/canal/estado, todos opcionais e combináveis,
antes de abrir uma linha do tempo específica — nenhum dos dois altera qualquer dado.
"""

from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from central_preventiva.adaptadores.persistencia.repositorio_avaliacoes_criticas import (
    RepositorioAvaliacoesCriticas,
)
from central_preventiva.adaptadores.persistencia.repositorio_avaliacoes_risco import (
    RepositorioAvaliacoesRisco,
)
from central_preventiva.adaptadores.persistencia.repositorio_decisoes_humanas import (
    RepositorioDecisoesHumanas,
)
from central_preventiva.adaptadores.persistencia.repositorio_elegibilidade import (
    RepositorioElegibilidades,
)
from central_preventiva.adaptadores.persistencia.repositorio_entregas_simuladas import (
    RepositorioEntregasSimuladas,
)
from central_preventiva.adaptadores.persistencia.repositorio_execucao_preventiva import (
    RepositorioExcecoesOperacionais,
    RepositorioExecucaoPreventiva,
)
from central_preventiva.adaptadores.persistencia.repositorio_mensagens import (
    RepositorioMensagens,
)
from central_preventiva.adaptadores.persistencia.repositorio_visualizacoes_comunicado import (
    RepositorioVisualizacoesComunicado,
)
from central_preventiva.aplicacao.linha_do_tempo import (
    ExecucaoResumo,
    LinhaDoTempo,
    MarcoLinhaDoTempo,
    PortasLinhaDoTempo,
    ServicoLinhaDoTempo,
)
from central_preventiva.composicao.configuracao import Configuracao
from central_preventiva.dominio.validador_saida_canal import Canal

TIPO_PROBLEMA = "application/problem+json"
CAMINHO_LINHA_DO_TEMPO = "/execucoes/{execucao_id}/linha-do-tempo"
CAMINHO_BUSCA_EXECUCOES = "/execucoes"


class RespostaMarcoLinhaDoTempo(BaseModel):
    """Um evento normalizado da cronologia, de qualquer uma das fontes agregadas."""

    model_config = ConfigDict(extra="forbid")

    timestamp: str = Field(description="Instante RFC 3339 em UTC do marco, canônico.")
    ator: str = Field(description="Quem ou o que produziu o marco (sistema, ia, segurado...).")
    acao: str = Field(description="A ação registrada neste marco.")
    resultado: str = Field(description="O resultado ou desfecho da ação.")
    correlacao: str = Field(description="Identificador para correlacionar este marco a outro.")
    tipo: str = Field(description="Categoria do marco (execucao, risco, geracao, ...).")
    mensagem_id: UUID | None = Field(
        description="Mensagem a que este marco pertence, para agrupamento visual; nulo se "
        "o marco for da execução como um todo."
    )


class RespostaLinhaDoTempo(BaseModel):
    """A cronologia completa de uma execução, com a cadeia de correlação."""

    model_config = ConfigDict(extra="forbid")

    execucao_id: UUID = Field(description="Identificador da execução consultada.")
    estado: str = Field(description="Estado agregado atual da execução.")
    marcos: list[RespostaMarcoLinhaDoTempo] = Field(
        description="Todos os marcos da execução, em ordem cronológica."
    )
    execucao_origem_id: UUID | None = Field(
        description="Execução terminal que originou esta, ou nula se não correlacionada."
    )
    retentativas: list[UUID] = Field(
        description="Execuções criadas como nova tentativa a partir desta."
    )


class RespostaExecucaoResumo(BaseModel):
    """Um resultado da busca de execuções, mínimo o bastante para decidir qual abrir."""

    model_config = ConfigDict(extra="forbid")

    execucao_id: UUID = Field(description="Identificador da execução.")
    estado: str = Field(description="Estado agregado atual da execução.")


class RespostaBuscaExecucoes(BaseModel):
    """Execuções correspondentes ao filtro informado, sem nenhum efeito colateral."""

    model_config = ConfigDict(extra="forbid")

    resultados: list[RespostaExecucaoResumo] = Field(
        description="Execuções correspondentes; lista vazia quando nenhuma corresponde."
    )


class ProblemaLinhaDoTempo(BaseModel):
    """Falha da linha do tempo/busca, com ocorrência, impacto e próxima ação segura."""

    model_config = ConfigDict(extra="forbid")

    codigo: str = Field(description="Código estável que identifica o tipo da falha.")
    correlacao_id: str = Field(description="Identificador único desta ocorrência de falha.")
    ocorrencia: str = Field(description="O que aconteceu, em português brasileiro.")
    impacto: str = Field(description="Efeito prático da falha para quem consultou o recurso.")
    proxima_acao: str = Field(description="Próxima ação segura recomendada para contornar a falha.")


def problema(
    status: int, codigo: str, ocorrencia: str, impacto: str, proxima_acao: str
) -> JSONResponse:
    """Monta a resposta `problem+json` correlacionada de uma falha."""

    corpo = ProblemaLinhaDoTempo(
        codigo=codigo,
        correlacao_id=str(uuid4()),
        ocorrencia=ocorrencia,
        impacto=impacto,
        proxima_acao=proxima_acao,
    )
    return JSONResponse(status_code=status, media_type=TIPO_PROBLEMA, content=corpo.model_dump())


def _resposta_marco(marco: MarcoLinhaDoTempo) -> RespostaMarcoLinhaDoTempo:
    """Traduz um marco agregado para o contrato público."""

    return RespostaMarcoLinhaDoTempo(
        timestamp=marco.timestamp.isoformat(),
        ator=marco.ator,
        acao=marco.acao,
        resultado=marco.resultado,
        correlacao=marco.correlacao,
        tipo=marco.tipo,
        mensagem_id=marco.mensagem_id,
    )


def _resposta_linha_do_tempo(linha_do_tempo: LinhaDoTempo) -> RespostaLinhaDoTempo:
    """Traduz a linha do tempo agregada para o contrato público."""

    return RespostaLinhaDoTempo(
        execucao_id=linha_do_tempo.execucao_id,
        estado=str(linha_do_tempo.estado),
        marcos=[_resposta_marco(marco) for marco in linha_do_tempo.marcos],
        execucao_origem_id=linha_do_tempo.execucao_origem_id,
        retentativas=list(linha_do_tempo.retentativas),
    )


def _resposta_resumo(resumo: ExecucaoResumo) -> RespostaExecucaoResumo:
    """Traduz um resumo de execução para o contrato público."""

    return RespostaExecucaoResumo(execucao_id=resumo.execucao_id, estado=str(resumo.estado))


def montar_servico_linha_do_tempo(configuracao: Configuracao) -> ServicoLinhaDoTempo:
    """Compõe o serviço de linha do tempo sobre os repositórios reais do DuckDB local."""

    caminho = configuracao.caminho_banco
    return ServicoLinhaDoTempo(
        PortasLinhaDoTempo(
            execucoes=RepositorioExecucaoPreventiva(caminho),
            avaliacoes_risco=RepositorioAvaliacoesRisco(caminho),
            elegibilidades=RepositorioElegibilidades(caminho),
            mensagens=RepositorioMensagens(caminho),
            avaliacoes_criticas=RepositorioAvaliacoesCriticas(caminho),
            decisoes=RepositorioDecisoesHumanas(caminho),
            excecoes=RepositorioExcecoesOperacionais(caminho),
            entregas=RepositorioEntregasSimuladas(caminho),
            visualizacoes=RepositorioVisualizacoesComunicado(caminho),
        )
    )


def criar_roteador(configuracao: Configuracao) -> APIRouter:
    """Compõe o recurso da linha do tempo ponta a ponta e da busca de execuções."""

    roteador = APIRouter(tags=["Linha do tempo"])
    servico = montar_servico_linha_do_tempo(configuracao)

    @roteador.get(
        CAMINHO_LINHA_DO_TEMPO,
        response_model=RespostaLinhaDoTempo,
        status_code=200,
        summary="Consultar a linha do tempo ponta a ponta de uma execução",
        description=(
            "Devolve, em ordem cronológica, todos os marcos já persistidos da execução — "
            "coleta, avaliação de risco, elegibilidade, gerações, críticas, decisões "
            "humanas, exceções, simulação e visualização —, cada um com timestamp UTC, "
            "ator, ação, resultado e correlação, além da cadeia de execuções "
            "correlacionadas (origem e retentativas)."
        ),
        responses={
            200: {"description": "Execução encontrada."},
            404: {"description": "Execução inexistente.", "model": ProblemaLinhaDoTempo},
            422: {
                "description": "O identificador da execução não é um UUID válido.",
                "model": ProblemaLinhaDoTempo,
            },
        },
    )
    async def consultar_linha_do_tempo(  # pyright: ignore[reportUnusedFunction]
        execucao_id: str,
    ) -> RespostaLinhaDoTempo | JSONResponse:
        """Traduz `ServicoLinhaDoTempo.montar` para o contrato REST/JSON público."""

        try:
            execucao_uuid = UUID(execucao_id)
        except ValueError:
            return problema(
                422,
                "execucao_id_invalido",
                f"'{execucao_id}' não é um identificador de execução válido.",
                "Nenhuma linha do tempo pode ser exibida.",
                "Consulte a execução pelo identificador UUID retornado pela API.",
            )

        linha_do_tempo = servico.montar(execucao_uuid)
        if linha_do_tempo is None:
            return problema(
                404,
                "execucao_inexistente",
                f"A execução '{execucao_id}' não existe.",
                "Nenhuma linha do tempo pode ser exibida.",
                "Consulte a execução pelo identificador UUID retornado pela API.",
            )
        return _resposta_linha_do_tempo(linha_do_tempo)

    @roteador.get(
        CAMINHO_BUSCA_EXECUCOES,
        response_model=RespostaBuscaExecucoes,
        status_code=200,
        summary="Buscar execuções por segurado, canal ou estado",
        description=(
            "Filtra execuções por segurado sintético (nome ou identificador), canal "
            "(`whatsapp`, `email` ou `sms`) e/ou estado (`EstadoExecucao` ou "
            "`EstadoMensagem` disponível), todos opcionais e combináveis por E. Não altera "
            "nenhum dado. Nenhum resultado correspondente devolve lista vazia, nunca erro."
        ),
        responses={
            200: {"description": "Busca realizada (pode ser lista vazia)."},
            422: {
                "description": "O canal informado não pertence ao conjunto fechado.",
                "model": ProblemaLinhaDoTempo,
            },
        },
    )
    async def buscar_execucoes(  # pyright: ignore[reportUnusedFunction]
        segurado: Annotated[
            str | None, Query(description="Nome ou identificador do segurado sintético.")
        ] = None,
        canal: Annotated[
            str | None, Query(description="Canal: `whatsapp`, `email` ou `sms`.")
        ] = None,
        estado: Annotated[
            str | None,
            Query(description="Um `EstadoExecucao` ou `EstadoMensagem` disponível."),
        ] = None,
    ) -> RespostaBuscaExecucoes | JSONResponse:
        """Traduz `ServicoLinhaDoTempo.buscar_execucoes` para o contrato público."""

        canal_valido: Canal | None = None
        if canal is not None:
            try:
                canal_valido = Canal(canal)
            except ValueError:
                return problema(
                    422,
                    "canal_invalido",
                    f"'{canal}' não é um canal válido.",
                    "Nenhuma busca foi realizada.",
                    "Informe `whatsapp`, `email` ou `sms`.",
                )

        resultados = servico.buscar_execucoes(
            segurado=segurado, canal=canal_valido, estado=estado
        )
        return RespostaBuscaExecucoes(
            resultados=[_resposta_resumo(resumo) for resumo in resultados]
        )

    return roteador
