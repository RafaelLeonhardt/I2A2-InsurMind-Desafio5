"""Recurso REST/JSON de consulta dos resultados consolidados da simulação (RESULT-02,09).

`GET /execucoes/{id}/resultados` é uma leitura pura sobre `ServicoConsolidacaoResultados`
(RESULT-06/07): reconstrói do DuckDB a cada chamada, sem repetir transição nem reabrir estado
terminal nenhum. Enquanto a simulação não chega a `concluida`/`falhou_simulacao`, a resposta
vem com `concluido=false` e os totais vazios — nunca um total parcial apresentado como final
(Edge Case da spec, consulta durante `simulando`).
"""

from uuid import UUID, uuid4

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from central_preventiva.adaptadores.persistencia.repositorio_entregas_simuladas import (
    RepositorioEntregasSimuladas,
)
from central_preventiva.adaptadores.persistencia.repositorio_execucao_preventiva import (
    RepositorioExecucaoPreventiva,
)
from central_preventiva.adaptadores.persistencia.repositorio_mensagens import (
    RepositorioMensagens,
)
from central_preventiva.aplicacao.consolidacao_resultados import (
    DivergenciaTotais,
    ExecucaoInexistente,
    MensagemNaoSimulavel,
    PortasConsolidacaoResultados,
    ResultadoConsolidado,
    ServicoConsolidacaoResultados,
)
from central_preventiva.composicao.configuracao import Configuracao

TIPO_PROBLEMA = "application/problem+json"
CAMINHO_RESULTADOS = "/execucoes/{execucao_id}/resultados"


class RespostaTotalPorChave(BaseModel):
    """Uma contagem agregada por canal ou por estado."""

    model_config = ConfigDict(extra="forbid")

    chave: str = Field(description="Canal ou estado agregado.")
    total: int = Field(description="Quantidade de mensagens nesta chave.")


class RespostaMensagemNaoSimulavel(BaseModel):
    """Uma mensagem que nunca foi nem será simulada nesta execução, com o motivo."""

    model_config = ConfigDict(extra="forbid")

    mensagem_id: UUID = Field(description="Identificador da mensagem.")
    canal: str = Field(description="Canal da mensagem.")
    estado: str = Field(description="Estado terminal da mensagem que a excluiu da simulação.")
    motivo: str = Field(description="Motivo legível pelo qual a mensagem não foi simulada.")


class RespostaDivergenciaTotais(BaseModel):
    """Inconsistência entre mensagens `simulada_entregue` e entregas persistidas (RESULT-09).

    Nunca esperada em operação normal; reportada com os dois lados e a execução como
    correlação, nunca reconciliada silenciosamente.
    """

    model_config = ConfigDict(extra="forbid")

    execucao_id: UUID = Field(description="Execução em que a divergência foi detectada.")
    mensagens_simulada_entregue: int = Field(
        description="Quantidade de mensagens no estado `simulada_entregue`."
    )
    entregas_persistidas: int = Field(
        description="Quantidade de linhas persistidas em `entregas_simuladas`."
    )


class RespostaResultadosConsolidados(BaseModel):
    """Resultados consolidados de uma execução, ou o progresso real enquanto ela não termina."""

    model_config = ConfigDict(extra="forbid")

    execucao_id: UUID = Field(description="Identificador da execução consultada.")
    estado: str = Field(description="Estado agregado atual da execução.")
    concluido: bool = Field(
        description=(
            "Se a simulação já terminou (`concluida` ou `falhou_simulacao`). Enquanto "
            "falso, os totais abaixo vêm vazios — não representam um resultado final."
        )
    )
    totais_por_canal: list[RespostaTotalPorChave] = Field(
        description="Totais de todas as mensagens do lote, por canal."
    )
    totais_por_estado: list[RespostaTotalPorChave] = Field(
        description="Totais de todas as mensagens do lote, por estado."
    )
    nao_simulaveis: list[RespostaMensagemNaoSimulavel] = Field(
        description=(
            "Mensagens rejeitadas, excluídas ou em exceção técnica, com o motivo; nunca "
            "somadas às entregas simuladas."
        )
    )
    divergencia: RespostaDivergenciaTotais | None = Field(
        description=(
            "Preenchida somente se a contagem de mensagens simuladas divergir da "
            "contagem de entregas persistidas; nula em operação normal."
        )
    )


class ProblemaResultados(BaseModel):
    """Falha da consulta de resultados, com ocorrência, impacto e próxima ação segura."""

    model_config = ConfigDict(extra="forbid")

    codigo: str = Field(description="Código estável que identifica o tipo da falha.")
    correlacao_id: str = Field(description="Identificador único desta ocorrência de falha.")
    ocorrencia: str = Field(description="O que aconteceu, em português brasileiro.")
    impacto: str = Field(description="Efeito prático da falha para quem consultou o recurso.")
    proxima_acao: str = Field(description="Próxima ação segura recomendada para contornar a falha.")


def problema(
    status: int, codigo: str, ocorrencia: str, impacto: str, proxima_acao: str
) -> JSONResponse:
    """Monta a resposta `problem+json` correlacionada de uma falha da consulta."""

    corpo = ProblemaResultados(
        codigo=codigo,
        correlacao_id=str(uuid4()),
        ocorrencia=ocorrencia,
        impacto=impacto,
        proxima_acao=proxima_acao,
    )
    return JSONResponse(status_code=status, media_type=TIPO_PROBLEMA, content=corpo.model_dump())


def _resposta_nao_simulavel(item: MensagemNaoSimulavel) -> RespostaMensagemNaoSimulavel:
    """Traduz uma mensagem não simulável persistida para o contrato público."""

    return RespostaMensagemNaoSimulavel(
        mensagem_id=item.mensagem_id,
        canal=str(item.canal),
        estado=str(item.estado),
        motivo=item.motivo,
    )


def _resposta_divergencia(
    divergencia: DivergenciaTotais | None,
) -> RespostaDivergenciaTotais | None:
    """Traduz a divergência detectada para o contrato público, ou devolve nula."""

    if divergencia is None:
        return None
    return RespostaDivergenciaTotais(
        execucao_id=divergencia.execucao_id,
        mensagens_simulada_entregue=divergencia.mensagens_simulada_entregue,
        entregas_persistidas=divergencia.entregas_persistidas,
    )


def _resposta_resultado(resultado: ResultadoConsolidado) -> RespostaResultadosConsolidados:
    """Traduz o resultado consolidado do caso de uso para o contrato público."""

    return RespostaResultadosConsolidados(
        execucao_id=resultado.execucao_id,
        estado=str(resultado.estado),
        concluido=resultado.concluido,
        totais_por_canal=[
            RespostaTotalPorChave(chave=str(canal), total=total)
            for canal, total in resultado.totais_por_canal
        ],
        totais_por_estado=[
            RespostaTotalPorChave(chave=str(estado), total=total)
            for estado, total in resultado.totais_por_estado
        ],
        nao_simulaveis=[
            _resposta_nao_simulavel(item) for item in resultado.nao_simulaveis
        ],
        divergencia=_resposta_divergencia(resultado.divergencia),
    )


def montar_servico_consolidacao_resultados(
    configuracao: Configuracao,
) -> ServicoConsolidacaoResultados:
    """Compõe o serviço de consolidação sobre os repositórios reais do DuckDB local."""

    caminho = configuracao.caminho_banco
    return ServicoConsolidacaoResultados(
        PortasConsolidacaoResultados(
            execucoes=RepositorioExecucaoPreventiva(caminho),
            mensagens=RepositorioMensagens(caminho),
            entregas=RepositorioEntregasSimuladas(caminho),
        )
    )


def criar_roteador(configuracao: Configuracao) -> APIRouter:
    """Compõe o recurso de consulta dos resultados consolidados de uma execução."""

    roteador = APIRouter(tags=["Resultados"])
    servico = montar_servico_consolidacao_resultados(configuracao)

    @roteador.get(
        CAMINHO_RESULTADOS,
        response_model=RespostaResultadosConsolidados,
        status_code=200,
        summary="Consultar os resultados consolidados da simulação de uma execução",
        description=(
            "Devolve os totais por canal e por estado de todas as mensagens do lote, com as "
            "rejeitadas, excluídas e em exceção técnica separadas em `nao_simulaveis` — nunca "
            "somadas às entregas simuladas. Enquanto a simulação não chega a `concluida` ou "
            "`falhou_simulacao`, `concluido` vem falso e os totais vêm vazios, para nunca "
            "apresentar um total parcial como final. Uma divergência entre a contagem de "
            "mensagens simuladas e as entregas persistidas é reportada em `divergencia`, "
            "nunca corrigida silenciosamente."
        ),
        responses={
            200: {"description": "Execução encontrada."},
            404: {"description": "Execução inexistente.", "model": ProblemaResultados},
            422: {
                "description": "O identificador da execução não é um UUID válido.",
                "model": ProblemaResultados,
            },
        },
    )
    async def consultar_resultados(  # pyright: ignore[reportUnusedFunction]
        execucao_id: str,
    ) -> RespostaResultadosConsolidados | JSONResponse:
        """Traduz `ServicoConsolidacaoResultados.consolidar` para o contrato público."""

        try:
            execucao_uuid = UUID(execucao_id)
        except ValueError:
            return problema(
                422,
                "execucao_id_invalido",
                f"'{execucao_id}' não é um identificador de execução válido.",
                "Nenhum resultado pode ser exibido.",
                "Consulte a execução pelo identificador UUID retornado pela API.",
            )

        try:
            resultado = servico.consolidar(execucao_uuid)
        except ExecucaoInexistente:
            return problema(
                404,
                "execucao_inexistente",
                f"A execução '{execucao_id}' não existe.",
                "Nenhum resultado pode ser exibido.",
                "Consulte a execução pelo identificador UUID retornado pela API.",
            )

        return _resposta_resultado(resultado)

    return roteador
