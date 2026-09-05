"""Recurso REST/JSON do comunicado e da primeira visualização (VISU-01, 04, 05).

`GET /segurados/{segurado_id}/comunicados/{entrega_simulada_id}` devolve o comunicado — sem
registrar visualização nenhuma, é a consulta que o frontend usa antes de renderizar. `POST
.../visualizacao` é o comando que o frontend dispara só depois do conteúdo já ter sido
renderizado com sucesso (Tech Decision do `design.md`) — nunca no `GET`, para nunca contar um
prefetch de rota como visualização real.

Nenhum cabeçalho `Idempotency-Key` é exigido aqui, deliberadamente: a operação já é idempotente
por construção via `UNIQUE (entrega_simulada_id)` (VISU-02/03) — repetir o comando não tem
corpo que varie nem risco de "mesma chave, conteúdo diferente" que a cerimônia de
`chaves_idempotencia` (AD-002) existe para resolver.

Uma entrega inexistente e uma entrega que pertence a outro segurado devolvem exatamente o mesmo
`404` genérico nas duas rotas (VISU-05, AD-011) — mesmo padrão de não-enumeração de 4.2.
"""

from datetime import datetime
from uuid import UUID, uuid4

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from central_preventiva.adaptadores.persistencia.repositorio_elegibilidade import (
    RepositorioElegibilidades,
)
from central_preventiva.adaptadores.persistencia.repositorio_entregas_simuladas import (
    RepositorioEntregasSimuladas,
)
from central_preventiva.adaptadores.persistencia.repositorio_mensagens import (
    RepositorioMensagens,
)
from central_preventiva.adaptadores.persistencia.repositorio_visualizacoes_comunicado import (
    RepositorioVisualizacoesComunicado,
    VisualizacaoComunicado,
)
from central_preventiva.aplicacao.visualizacao_comunicado import (
    Comunicado,
    MensagemNaoElegivelParaComunicado,
    PortasVisualizacaoComunicado,
    ServicoVisualizacaoComunicado,
)
from central_preventiva.composicao.configuracao import Configuracao

TIPO_PROBLEMA = "application/problem+json"
CAMINHO_COMUNICADO = "/segurados/{segurado_id}/comunicados/{entrega_simulada_id}"
CAMINHO_VISUALIZACAO = (
    "/segurados/{segurado_id}/comunicados/{entrega_simulada_id}/visualizacao"
)


class RespostaVisualizacaoComunicado(BaseModel):
    """A primeira visualização registrada de um comunicado."""

    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(description="Identificador da visualização.")
    visualizada_em: datetime = Field(
        description="Instante RFC 3339 em UTC da primeira visualização."
    )


class RespostaComunicado(BaseModel):
    """O comunicado exibível ao segurado sintético: conteúdo, canal e visualização."""

    model_config = ConfigDict(extra="forbid")

    entrega_simulada_id: UUID = Field(description="Identificador da entrega simulada.")
    mensagem_id: UUID = Field(description="Mensagem que originou o comunicado.")
    canal: str = Field(description="Canal do comunicado (`whatsapp`, `email` ou `sms`).")
    assunto: str | None = Field(description="Assunto apresentado, só no canal de e-mail.")
    corpo: str = Field(description="Corpo apresentado, cópia exata do conteúdo aprovado.")
    rotulo: str = Field(description="Rótulo fixo da natureza da entrega: sempre 'simulada'.")
    criado_em: datetime = Field(description="Instante RFC 3339 em UTC de criação da entrega.")
    visualizacao: RespostaVisualizacaoComunicado | None = Field(
        description="Primeira visualização já registrada, ou nula se ainda não visualizado."
    )


class ProblemaComunicado(BaseModel):
    """Falha do comunicado, com ocorrência, impacto e próxima ação segura."""

    model_config = ConfigDict(extra="forbid")

    codigo: str = Field(description="Código estável que identifica o tipo da falha.")
    correlacao_id: str = Field(description="Identificador único desta ocorrência de falha.")
    ocorrencia: str = Field(description="O que aconteceu, em português brasileiro.")
    impacto: str = Field(description="Efeito prático da falha para quem consultou o recurso.")
    proxima_acao: str = Field(description="Próxima ação segura recomendada para contornar a falha.")


def problema(
    status: int, codigo: str, ocorrencia: str, impacto: str, proxima_acao: str
) -> JSONResponse:
    """Monta a resposta `problem+json` correlacionada de uma falha do comunicado."""

    corpo = ProblemaComunicado(
        codigo=codigo,
        correlacao_id=str(uuid4()),
        ocorrencia=ocorrencia,
        impacto=impacto,
        proxima_acao=proxima_acao,
    )
    return JSONResponse(status_code=status, media_type=TIPO_PROBLEMA, content=corpo.model_dump())


def _problema_nao_encontrado(entrega_simulada_id: str) -> JSONResponse:
    """Resposta idêntica para entrega inexistente e entrega de outro segurado (AD-011)."""

    return problema(
        404,
        "comunicado_nao_encontrado",
        f"O comunicado '{entrega_simulada_id}' não existe para este segurado.",
        "Nenhum comunicado pode ser exibido.",
        "Consulte o comunicado pelo identificador retornado pela API de resultados.",
    )


def _problema_identificador_invalido() -> JSONResponse:
    """Resposta de identificador que não é um UUID válido."""

    return problema(
        422,
        "identificador_invalido",
        "O identificador do segurado ou da entrega não é um UUID válido.",
        "Nenhum comunicado pode ser exibido.",
        "Consulte o comunicado pelos identificadores retornados pela API.",
    )


def _resposta_visualizacao(
    visualizacao: VisualizacaoComunicado | None,
) -> RespostaVisualizacaoComunicado | None:
    """Traduz a visualização persistida para o contrato público, ou devolve nula."""

    if visualizacao is None:
        return None
    return RespostaVisualizacaoComunicado(
        id=visualizacao.id, visualizada_em=visualizacao.visualizada_em
    )


def _resposta_comunicado(comunicado: Comunicado) -> RespostaComunicado:
    """Traduz o comunicado resolvido pelo caso de uso para o contrato público."""

    return RespostaComunicado(
        entrega_simulada_id=comunicado.entrega_simulada_id,
        mensagem_id=comunicado.mensagem_id,
        canal=str(comunicado.canal),
        assunto=comunicado.apresentacao.assunto,
        corpo=comunicado.apresentacao.corpo,
        rotulo=comunicado.apresentacao.rotulo,
        criado_em=comunicado.criado_em,
        visualizacao=_resposta_visualizacao(comunicado.visualizacao),
    )


def montar_servico_visualizacao_comunicado(
    configuracao: Configuracao,
) -> ServicoVisualizacaoComunicado:
    """Compõe o serviço de visualização sobre os repositórios reais do DuckDB local."""

    caminho = configuracao.caminho_banco
    return ServicoVisualizacaoComunicado(
        PortasVisualizacaoComunicado(
            mensagens=RepositorioMensagens(caminho),
            entregas=RepositorioEntregasSimuladas(caminho),
            elegibilidades=RepositorioElegibilidades(caminho),
            visualizacoes=RepositorioVisualizacoesComunicado(caminho),
        )
    )


def criar_roteador(configuracao: Configuracao) -> APIRouter:
    """Compõe o recurso do comunicado e da primeira visualização do segurado sintético."""

    roteador = APIRouter(tags=["Comunicado"])
    servico = montar_servico_visualizacao_comunicado(configuracao)

    @roteador.get(
        CAMINHO_COMUNICADO,
        response_model=RespostaComunicado,
        status_code=200,
        summary="Consultar o comunicado de uma entrega simulada",
        description=(
            "Devolve conteúdo, canal e natureza simulada do comunicado, e a primeira "
            "visualização já registrada, se houver. Consulta de leitura: não registra "
            "visualização nenhuma. Uma entrega inexistente e uma entrega que pertence a "
            "outro segurado devolvem exatamente a mesma resposta `404`."
        ),
        responses={
            200: {"description": "Comunicado encontrado para este segurado."},
            404: {
                "description": "Comunicado inexistente ou de outro segurado.",
                "model": ProblemaComunicado,
            },
            422: {
                "description": "Algum identificador não é um UUID válido.",
                "model": ProblemaComunicado,
            },
        },
    )
    async def consultar_comunicado(  # pyright: ignore[reportUnusedFunction]
        segurado_id: str, entrega_simulada_id: str
    ) -> RespostaComunicado | JSONResponse:
        """Traduz `ServicoVisualizacaoComunicado.obter_comunicado` para o contrato público."""

        try:
            segurado_uuid = UUID(segurado_id)
            entrega_uuid = UUID(entrega_simulada_id)
        except ValueError:
            return _problema_identificador_invalido()

        comunicado = servico.obter_comunicado(entrega_uuid, segurado_uuid)
        if comunicado is None:
            return _problema_nao_encontrado(entrega_simulada_id)
        return _resposta_comunicado(comunicado)

    @roteador.post(
        CAMINHO_VISUALIZACAO,
        response_model=RespostaVisualizacaoComunicado,
        status_code=200,
        summary="Registrar a primeira visualização de um comunicado",
        description=(
            "Registra, de forma idempotente, a primeira visualização do comunicado — "
            "chamado só depois do conteúdo já ter sido renderizado com sucesso, nunca no "
            "carregamento inicial da página. Reabrir um comunicado já visualizado devolve a "
            "mesma visualização, sem criar uma segunda. Uma mensagem de origem que ainda não "
            "foi simulada, foi rejeitada, excluída ou está em exceção é recusada com um erro "
            "de domínio explícito, sem registrar nenhum marco."
        ),
        responses={
            200: {"description": "Visualização registrada (ou já existente, no replay)."},
            404: {
                "description": "Comunicado inexistente ou de outro segurado.",
                "model": ProblemaComunicado,
            },
            409: {
                "description": "Mensagem de origem não elegível para virar comunicado.",
                "model": ProblemaComunicado,
            },
            422: {
                "description": "Algum identificador não é um UUID válido.",
                "model": ProblemaComunicado,
            },
        },
    )
    async def registrar_visualizacao(  # pyright: ignore[reportUnusedFunction]
        segurado_id: str, entrega_simulada_id: str
    ) -> RespostaVisualizacaoComunicado | JSONResponse:
        """Traduz `ServicoVisualizacaoComunicado.registrar_visualizacao` para o contrato
        público."""

        try:
            segurado_uuid = UUID(segurado_id)
            entrega_uuid = UUID(entrega_simulada_id)
        except ValueError:
            return _problema_identificador_invalido()

        try:
            visualizacao = servico.registrar_visualizacao(entrega_uuid, segurado_uuid)
        except MensagemNaoElegivelParaComunicado as recusa:
            return problema(
                409,
                "mensagem_nao_elegivel_para_comunicado",
                f"A mensagem de origem está em '{recusa.estado}', não elegível para virar "
                "comunicado.",
                "Nenhuma visualização foi registrada.",
                "Consulte o comunicado apenas depois que a mensagem chegar a "
                "'Enviada — simulação'.",
            )

        if visualizacao is None:
            return _problema_nao_encontrado(entrega_simulada_id)
        return RespostaVisualizacaoComunicado(
            id=visualizacao.id, visualizada_em=visualizacao.visualizada_em
        )

    return roteador
