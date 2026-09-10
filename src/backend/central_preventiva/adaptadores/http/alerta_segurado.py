"""Recurso REST/JSON do alerta mais relevante do segurado ativo (VISAO-01, 06, 5.1).

`GET /segurados/{segurado_id}/alerta-mais-relevante` sempre devolve `200`: a ausência de
alerta é um resultado válido, não um erro, então o corpo traz `alerta: null` em vez de um
`404` — a Visão geral do segurado precisa distinguir "sem alerta" de "falha ao consultar"
(VISAO-04), e um `404` genérico misturaria as duas.
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
from central_preventiva.adaptadores.persistencia.repositorio_meteorologia import (
    RepositorioAreasMonitoradas,
    RepositorioEventosMeteorologicos,
    RepositorioSincronizacoes,
    RepositorioTentativasColeta,
)
from central_preventiva.adaptadores.persistencia.repositorio_regras import RepositorioRegras
from central_preventiva.aplicacao.alerta_segurado import (
    AlertaSegurado,
    PortasAlertaSegurado,
    ServicoAlertaSegurado,
)
from central_preventiva.composicao.configuracao import Configuracao

TIPO_PROBLEMA = "application/problem+json"
CAMINHO_ALERTA = "/segurados/{segurado_id}/alerta-mais-relevante"


class RespostaAlerta(BaseModel):
    """O alerta mais relevante exibível ao segurado ativo."""

    model_config = ConfigDict(extra="forbid")

    elegibilidade_id: UUID = Field(description="Identificador da elegibilidade de origem.")
    evento_tipo: str = Field(
        description="Tipo do evento meteorológico (`chuva_intensa`/`granizo`)."
    )
    severidade: str = Field(
        description="Critério de risco observado que tornou o evento relevante."
    )
    periodo_inicio: datetime = Field(description="Instante RFC 3339 em UTC de início do evento.")
    periodo_fim: datetime = Field(description="Instante RFC 3339 em UTC de fim do evento.")
    localizacao: str = Field(description="Área afetada, no mesmo código usado pela apólice.")
    impactos_esperados: list[str] = Field(
        description="Coberturas da apólice relevantes ao evento."
    )
    recomendacoes: list[str] = Field(description="Recomendações preventivas curtas e práticas.")
    origem: str = Field(description="Procedência do evento: `real_inmet` ou `sintetico`.")
    instante_observado: datetime = Field(
        description="Instante RFC 3339 em UTC em que o dado do evento foi observado."
    )
    fonte_degradada: bool = Field(
        description=(
            "Se a fonte meteorológica real está degradada no momento da consulta — o "
            "alerta é o último snapshot disponível, de caráter apenas informativo."
        )
    )
    entrega_simulada_id: UUID | None = Field(
        description=(
            "Entrega simulada mais recente associada a este alerta, ou nulo se nenhuma "
            "mensagem dele chegou a `simulada_entregue` ainda."
        )
    )


class RespostaAlertaSegurado(BaseModel):
    """O alerta mais relevante do segurado, ou nulo se não houver nenhum."""

    model_config = ConfigDict(extra="forbid")

    alerta: RespostaAlerta | None = Field(
        description="O alerta mais relevante, ou nulo se o segurado não tiver nenhum."
    )


class ProblemaAlertaSegurado(BaseModel):
    """Falha da consulta do alerta, com ocorrência, impacto e próxima ação segura."""

    model_config = ConfigDict(extra="forbid")

    codigo: str = Field(description="Código estável que identifica o tipo da falha.")
    correlacao_id: str = Field(description="Identificador único desta ocorrência de falha.")
    ocorrencia: str = Field(description="O que aconteceu, em português brasileiro.")
    impacto: str = Field(description="Efeito prático da falha para quem consultou o recurso.")
    proxima_acao: str = Field(description="Próxima ação segura recomendada para contornar a falha.")


def _problema_identificador_invalido(segurado_id: str) -> JSONResponse:
    """Resposta de identificador de segurado que não é um UUID válido."""

    corpo = ProblemaAlertaSegurado(
        codigo="identificador_invalido",
        correlacao_id=str(uuid4()),
        ocorrencia=f"'{segurado_id}' não é um identificador de segurado válido.",
        impacto="Nenhum alerta pode ser exibido.",
        proxima_acao="Consulte o alerta pelo identificador UUID do segurado ativo.",
    )
    return JSONResponse(status_code=422, media_type=TIPO_PROBLEMA, content=corpo.model_dump())


def _resposta_alerta(alerta: AlertaSegurado) -> RespostaAlerta:
    """Traduz o alerta resolvido pelo caso de uso para o contrato público."""

    return RespostaAlerta(
        elegibilidade_id=alerta.elegibilidade_id,
        evento_tipo=str(alerta.evento_tipo),
        severidade=alerta.severidade,
        periodo_inicio=alerta.periodo_inicio,
        periodo_fim=alerta.periodo_fim,
        localizacao=alerta.localizacao,
        impactos_esperados=list(alerta.impactos_esperados),
        recomendacoes=list(alerta.recomendacoes),
        origem=str(alerta.origem),
        instante_observado=alerta.instante_observado,
        fonte_degradada=alerta.fonte_degradada,
        entrega_simulada_id=alerta.entrega_simulada_id,
    )


def montar_servico_alerta_segurado(configuracao: Configuracao) -> ServicoAlertaSegurado:
    """Compõe o serviço do alerta sobre os repositórios reais do DuckDB local."""

    caminho = configuracao.caminho_banco
    return ServicoAlertaSegurado(
        PortasAlertaSegurado(
            elegibilidades=RepositorioElegibilidades(caminho),
            eventos=RepositorioEventosMeteorologicos(caminho),
            regras=RepositorioRegras(caminho),
            areas_monitoradas=RepositorioAreasMonitoradas(caminho),
            sincronizacoes=RepositorioSincronizacoes(caminho),
            tentativas=RepositorioTentativasColeta(caminho),
            entregas=RepositorioEntregasSimuladas(caminho),
        )
    )


def criar_roteador(configuracao: Configuracao) -> APIRouter:
    """Compõe o recurso do alerta mais relevante do segurado ativo."""

    roteador = APIRouter(tags=["Alerta do segurado"])
    servico = montar_servico_alerta_segurado(configuracao)

    @roteador.get(
        CAMINHO_ALERTA,
        response_model=RespostaAlertaSegurado,
        status_code=200,
        summary="Consultar o alerta mais relevante do segurado ativo",
        description=(
            "Devolve o alerta mais relevante do segurado — tipo, severidade, período, "
            "localização, impactos e recomendações — ou `alerta: null` se não houver "
            "nenhum. Ausência de alerta é um resultado válido, nunca um erro `404`."
        ),
        responses={
            200: {"description": "Consulta realizada, com ou sem alerta."},
            422: {
                "description": "O identificador do segurado não é um UUID válido.",
                "model": ProblemaAlertaSegurado,
            },
        },
    )
    async def consultar_alerta(  # pyright: ignore[reportUnusedFunction]
        segurado_id: str,
    ) -> RespostaAlertaSegurado | JSONResponse:
        """Traduz `ServicoAlertaSegurado.obter_mais_relevante` para o contrato público."""

        try:
            segurado_uuid = UUID(segurado_id)
        except ValueError:
            return _problema_identificador_invalido(segurado_id)

        alerta = servico.obter_mais_relevante(segurado_uuid)
        return RespostaAlertaSegurado(alerta=None if alerta is None else _resposta_alerta(alerta))

    return roteador
