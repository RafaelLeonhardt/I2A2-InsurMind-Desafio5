"""Recurso REST/JSON da lista e do detalhe dos alertas do segurado ativo
(ALERTAS-01..06, 5.2).

`GET /segurados/{segurado_id}/alertas` lista todos os alertas `incluido` do segurado, cada
um com sua classificação. `GET /segurados/{segurado_id}/alertas/{elegibilidade_id}` abre o
detalhe de um alerta específico — uma elegibilidade inexistente e uma de outro segurado
devolvem exatamente o mesmo `404` genérico (ALERTAS-05, AD-011), mesmo padrão de 4.2/4.3.
"""

from uuid import UUID, uuid4

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from central_preventiva.adaptadores.http.alerta_segurado import RespostaAlerta
from central_preventiva.adaptadores.http.linha_do_tempo import (
    RespostaMarcoLinhaDoTempo,
    montar_servico_linha_do_tempo,
)
from central_preventiva.adaptadores.persistencia.repositorio_elegibilidade import (
    RepositorioElegibilidades,
)
from central_preventiva.adaptadores.persistencia.repositorio_execucao_preventiva import (
    RepositorioExecucaoPreventiva,
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
from central_preventiva.aplicacao.linha_do_tempo import MarcoLinhaDoTempo
from central_preventiva.aplicacao.lista_alertas_segurado import (
    DetalheAlertaSegurado,
    ItemAlertaListado,
    PortasListaAlertasSegurado,
    ServicoListaAlertasSegurado,
)
from central_preventiva.composicao.configuracao import Configuracao

TIPO_PROBLEMA = "application/problem+json"
CAMINHO_LISTA_ALERTAS = "/segurados/{segurado_id}/alertas"
CAMINHO_DETALHE_ALERTA = "/segurados/{segurado_id}/alertas/{elegibilidade_id}"


class RespostaItemAlerta(BaseModel):
    """Um item da lista de alertas: o alerta e sua classificação."""

    model_config = ConfigDict(extra="forbid")

    alerta: RespostaAlerta = Field(description="O alerta.")
    classificacao: str = Field(
        description="`ativo`, `anterior` ou `ainda_nao_simulado`."
    )


class RespostaListaAlertas(BaseModel):
    """A lista completa de alertas do segurado."""

    model_config = ConfigDict(extra="forbid")

    alertas: list[RespostaItemAlerta] = Field(
        description="Todos os alertas do segurado, mais recentes primeiro."
    )


class RespostaDetalheAlerta(BaseModel):
    """O detalhe completo de um alerta: alerta, classificação, contexto da apólice e
    linha do tempo da execução que o produziu."""

    model_config = ConfigDict(extra="forbid")

    alerta: RespostaAlerta = Field(description="O alerta.")
    classificacao: str = Field(
        description="`ativo`, `anterior` ou `ainda_nao_simulado`."
    )
    apolice_id: UUID = Field(description="Apólice que originou a elegibilidade.")
    justificativa: str = Field(description="Por que o segurado é elegível a este alerta.")
    linha_do_tempo: list[RespostaMarcoLinhaDoTempo] = Field(
        description="Marcos da execução que produziu este alerta; vazia se a "
        "elegibilidade não tiver execução associada (linha semeada de demonstração)."
    )


class ProblemaListaAlertas(BaseModel):
    """Falha da lista/detalhe de alertas, com ocorrência, impacto e próxima ação segura."""

    model_config = ConfigDict(extra="forbid")

    codigo: str = Field(description="Código estável que identifica o tipo da falha.")
    correlacao_id: str = Field(description="Identificador único desta ocorrência de falha.")
    ocorrencia: str = Field(description="O que aconteceu, em português brasileiro.")
    impacto: str = Field(description="Efeito prático da falha para quem consultou o recurso.")
    proxima_acao: str = Field(description="Próxima ação segura recomendada para contornar a falha.")


def _problema(
    status: int, codigo: str, ocorrencia: str, impacto: str, proxima_acao: str
) -> JSONResponse:
    """Monta a resposta `problem+json` correlacionada de uma falha."""

    corpo = ProblemaListaAlertas(
        codigo=codigo,
        correlacao_id=str(uuid4()),
        ocorrencia=ocorrencia,
        impacto=impacto,
        proxima_acao=proxima_acao,
    )
    return JSONResponse(status_code=status, media_type=TIPO_PROBLEMA, content=corpo.model_dump())


def _problema_identificador_invalido() -> JSONResponse:
    """Resposta de identificador que não é um UUID válido."""

    return _problema(
        422,
        "identificador_invalido",
        "O identificador do segurado ou do alerta não é um UUID válido.",
        "Nenhum alerta pode ser exibido.",
        "Consulte o alerta pelos identificadores UUID retornados pela API.",
    )


def _problema_nao_encontrado(elegibilidade_id: str) -> JSONResponse:
    """Resposta idêntica para alerta inexistente e alerta de outro segurado (AD-011)."""

    return _problema(
        404,
        "alerta_nao_encontrado",
        f"O alerta '{elegibilidade_id}' não existe para este segurado.",
        "Nenhum detalhe pode ser exibido.",
        "Consulte o alerta pelo identificador retornado pela lista de alertas.",
    )


def _resposta_marco(marco: MarcoLinhaDoTempo) -> RespostaMarcoLinhaDoTempo:
    """Traduz um marco agregado para o contrato público (mesma forma de linha_do_tempo.py)."""

    return RespostaMarcoLinhaDoTempo(
        timestamp=marco.timestamp.isoformat(),
        ator=marco.ator,
        acao=marco.acao,
        resultado=marco.resultado,
        correlacao=marco.correlacao,
        tipo=marco.tipo,
        mensagem_id=marco.mensagem_id,
    )


def _resposta_alerta(alerta: AlertaSegurado) -> RespostaAlerta:
    """Traduz o alerta para o contrato público (mesma forma de `alerta_segurado.py`)."""

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
    )


def _resposta_item(item: ItemAlertaListado) -> RespostaItemAlerta:
    """Traduz um item da lista para o contrato público."""

    return RespostaItemAlerta(
        alerta=_resposta_alerta(item.alerta), classificacao=str(item.classificacao)
    )


def _resposta_detalhe(detalhe: DetalheAlertaSegurado) -> RespostaDetalheAlerta:
    """Traduz o detalhe resolvido pelo caso de uso para o contrato público."""

    return RespostaDetalheAlerta(
        alerta=_resposta_alerta(detalhe.alerta),
        classificacao=str(detalhe.classificacao),
        apolice_id=detalhe.apolice_id,
        justificativa=detalhe.justificativa,
        linha_do_tempo=[_resposta_marco(marco) for marco in detalhe.linha_do_tempo],
    )


def montar_servico_lista_alertas_segurado(
    configuracao: Configuracao,
) -> ServicoListaAlertasSegurado:
    """Compõe o serviço de lista/detalhe sobre os repositórios reais do DuckDB local."""

    caminho = configuracao.caminho_banco
    alerta_segurado = ServicoAlertaSegurado(
        PortasAlertaSegurado(
            elegibilidades=RepositorioElegibilidades(caminho),
            eventos=RepositorioEventosMeteorologicos(caminho),
            regras=RepositorioRegras(caminho),
            areas_monitoradas=RepositorioAreasMonitoradas(caminho),
            sincronizacoes=RepositorioSincronizacoes(caminho),
            tentativas=RepositorioTentativasColeta(caminho),
        )
    )
    return ServicoListaAlertasSegurado(
        PortasListaAlertasSegurado(
            elegibilidades=RepositorioElegibilidades(caminho),
            execucoes=RepositorioExecucaoPreventiva(caminho),
            alerta_segurado=alerta_segurado,
            linha_do_tempo=montar_servico_linha_do_tempo(configuracao),
        )
    )


def criar_roteador(configuracao: Configuracao) -> APIRouter:
    """Compõe o recurso de lista e detalhe dos alertas do segurado ativo."""

    roteador = APIRouter(tags=["Alertas do segurado"])
    servico = montar_servico_lista_alertas_segurado(configuracao)

    @roteador.get(
        CAMINHO_LISTA_ALERTAS,
        response_model=RespostaListaAlertas,
        status_code=200,
        summary="Listar todos os alertas do segurado ativo",
        description=(
            "Devolve todos os alertas `incluido` do segurado, mais recentes primeiro, "
            "cada um classificado como `ativo`, `anterior` ou `ainda_nao_simulado`. "
            "Lista vazia quando o segurado não tiver nenhum alerta."
        ),
        responses={
            200: {"description": "Consulta realizada, com ou sem alertas."},
            422: {
                "description": "O identificador do segurado não é um UUID válido.",
                "model": ProblemaListaAlertas,
            },
        },
    )
    async def listar_alertas(segurado_id: str) -> RespostaListaAlertas | JSONResponse:  # pyright: ignore[reportUnusedFunction]
        """Traduz `ServicoListaAlertasSegurado.listar` para o contrato público."""

        try:
            segurado_uuid = UUID(segurado_id)
        except ValueError:
            return _problema_identificador_invalido()

        itens = servico.listar(segurado_uuid)
        return RespostaListaAlertas(alertas=[_resposta_item(item) for item in itens])

    @roteador.get(
        CAMINHO_DETALHE_ALERTA,
        response_model=RespostaDetalheAlerta,
        status_code=200,
        summary="Consultar o detalhe de um alerta do segurado ativo",
        description=(
            "Devolve o detalhe completo de um alerta — alerta, classificação, contexto "
            "da apólice e linha do tempo da execução. Um alerta inexistente e um alerta "
            "de outro segurado devolvem exatamente a mesma resposta `404`."
        ),
        responses={
            200: {"description": "Alerta encontrado para este segurado."},
            404: {
                "description": "Alerta inexistente ou de outro segurado.",
                "model": ProblemaListaAlertas,
            },
            422: {
                "description": "Algum identificador não é um UUID válido.",
                "model": ProblemaListaAlertas,
            },
        },
    )
    async def consultar_detalhe_alerta(  # pyright: ignore[reportUnusedFunction]
        segurado_id: str, elegibilidade_id: str
    ) -> RespostaDetalheAlerta | JSONResponse:
        """Traduz `ServicoListaAlertasSegurado.obter_detalhe` para o contrato público."""

        try:
            segurado_uuid = UUID(segurado_id)
            elegibilidade_uuid = UUID(elegibilidade_id)
        except ValueError:
            return _problema_identificador_invalido()

        detalhe = servico.obter_detalhe(segurado_uuid, elegibilidade_uuid)
        if detalhe is None:
            return _problema_nao_encontrado(elegibilidade_id)
        return _resposta_detalhe(detalhe)

    return roteador
