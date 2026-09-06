"""Recurso REST/JSON da lista de comunicados do segurado ativo (COMUNICADOS-01, COMUNICADOS-02).

`GET /segurados/{segurado_id}/comunicados` lista todos os comunicados do segurado, mais
antigos primeiro, cada um com o estado de visualização já registrado, se houver. O detalhe e o
registro da própria visualização continuam em `visualizacao_comunicado.py` (4.3), sem
duplicação — esta rota só agrega a lista.
"""

from datetime import datetime
from uuid import UUID
from uuid import uuid4 as gerar_uuid

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from central_preventiva.adaptadores.http.visualizacao_comunicado import (
    RespostaVisualizacaoComunicado,
)
from central_preventiva.adaptadores.persistencia.repositorio_entregas_simuladas import (
    RepositorioEntregasSimuladas,
)
from central_preventiva.adaptadores.persistencia.repositorio_visualizacoes_comunicado import (
    RepositorioVisualizacoesComunicado,
)
from central_preventiva.aplicacao.lista_comunicados import (
    ItemComunicadoListado,
    PortasListaComunicados,
    ServicoListaComunicados,
)
from central_preventiva.composicao.configuracao import Configuracao

TIPO_PROBLEMA = "application/problem+json"
CAMINHO_LISTA_COMUNICADOS = "/segurados/{segurado_id}/comunicados"


class RespostaItemComunicado(BaseModel):
    """Um item da lista de comunicados: canal, assunto/resumo, data e visualização."""

    model_config = ConfigDict(extra="forbid")

    entrega_simulada_id: UUID = Field(description="Identificador da entrega simulada.")
    mensagem_id: UUID = Field(description="Mensagem que originou o comunicado.")
    canal: str = Field(description="Canal do comunicado (`whatsapp`, `email` ou `sms`).")
    assunto_ou_resumo: str = Field(
        description="Assunto real (e-mail) ou resumo truncado do corpo (WhatsApp/SMS)."
    )
    criado_em: datetime = Field(description="Instante RFC 3339 em UTC de criação da entrega.")
    visualizacao: RespostaVisualizacaoComunicado | None = Field(
        description="Primeira visualização já registrada, ou nula se ainda não visualizado."
    )


class RespostaListaComunicados(BaseModel):
    """A lista completa de comunicados do segurado."""

    model_config = ConfigDict(extra="forbid")

    comunicados: list[RespostaItemComunicado] = Field(
        description="Todos os comunicados do segurado, mais antigos primeiro."
    )


class ProblemaListaComunicados(BaseModel):
    """Falha da lista de comunicados, com ocorrência, impacto e próxima ação segura."""

    model_config = ConfigDict(extra="forbid")

    codigo: str = Field(description="Código estável que identifica o tipo da falha.")
    correlacao_id: str = Field(description="Identificador único desta ocorrência de falha.")
    ocorrencia: str = Field(description="O que aconteceu, em português brasileiro.")
    impacto: str = Field(description="Efeito prático da falha para quem consultou o recurso.")
    proxima_acao: str = Field(description="Próxima ação segura recomendada para contornar a falha.")


def _problema_identificador_invalido() -> JSONResponse:
    """Resposta de identificador que não é um UUID válido."""

    corpo = ProblemaListaComunicados(
        codigo="identificador_invalido",
        correlacao_id=str(gerar_uuid()),
        ocorrencia="O identificador do segurado não é um UUID válido.",
        impacto="Nenhum comunicado pode ser exibido.",
        proxima_acao="Consulte a lista pelo identificador do segurado retornado pela API.",
    )
    return JSONResponse(status_code=422, media_type=TIPO_PROBLEMA, content=corpo.model_dump())


def _resposta_visualizacao(
    visualizacao: ItemComunicadoListado,
) -> RespostaVisualizacaoComunicado | None:
    """Traduz a visualização do item para o contrato público, ou devolve nula."""

    if visualizacao.visualizacao is None:
        return None
    return RespostaVisualizacaoComunicado(
        id=visualizacao.visualizacao.id, visualizada_em=visualizacao.visualizacao.visualizada_em
    )


def _resposta_item(item: ItemComunicadoListado) -> RespostaItemComunicado:
    """Traduz um item da lista para o contrato público."""

    return RespostaItemComunicado(
        entrega_simulada_id=item.entrega_simulada_id,
        mensagem_id=item.mensagem_id,
        canal=str(item.canal),
        assunto_ou_resumo=item.assunto_ou_resumo,
        criado_em=item.criado_em,
        visualizacao=_resposta_visualizacao(item),
    )


def montar_servico_lista_comunicados(configuracao: Configuracao) -> ServicoListaComunicados:
    """Compõe o serviço de lista sobre os repositórios reais do DuckDB local."""

    caminho = configuracao.caminho_banco
    return ServicoListaComunicados(
        PortasListaComunicados(
            entregas=RepositorioEntregasSimuladas(caminho),
            visualizacoes=RepositorioVisualizacoesComunicado(caminho),
        )
    )


def criar_roteador(configuracao: Configuracao) -> APIRouter:
    """Compõe o recurso da lista de comunicados do segurado ativo."""

    roteador = APIRouter(tags=["Comunicado"])
    servico = montar_servico_lista_comunicados(configuracao)

    @roteador.get(
        CAMINHO_LISTA_COMUNICADOS,
        response_model=RespostaListaComunicados,
        status_code=200,
        summary="Listar todos os comunicados do segurado ativo",
        description=(
            "Devolve todos os comunicados do segurado, mais antigos primeiro, com canal, "
            "assunto/resumo, data e a visualização já registrada, se houver. Lista vazia "
            "quando o segurado não tiver nenhum comunicado."
        ),
        responses={
            200: {"description": "Consulta realizada, com ou sem comunicados."},
            422: {
                "description": "O identificador do segurado não é um UUID válido.",
                "model": ProblemaListaComunicados,
            },
        },
    )
    async def listar_comunicados(segurado_id: str) -> RespostaListaComunicados | JSONResponse:  # pyright: ignore[reportUnusedFunction]
        """Traduz `ServicoListaComunicados.listar` para o contrato público."""

        try:
            segurado_uuid = UUID(segurado_id)
        except ValueError:
            return _problema_identificador_invalido()

        itens = servico.listar(segurado_uuid)
        return RespostaListaComunicados(comunicados=[_resposta_item(item) for item in itens])

    return roteador
