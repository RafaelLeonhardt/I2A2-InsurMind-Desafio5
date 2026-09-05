"""Recurso REST/JSON da apólice do segurado ativo e da explicação de critérios
(APOLICE-01..06, 5.3).

`GET /segurados/{segurado_id}/apolice` devolve os dados cadastrais e o estado objetivo da
apólice. `GET /segurados/{segurado_id}/apolice/explicacao/{elegibilidade_id}` devolve a
explicação de critérios de uma execução específica — uma apólice/elegibilidade inexistente
e uma de outro segurado devolvem exatamente o mesmo `404` genérico (APOLICE-04, AD-011),
mesmo padrão de 4.2/4.3/5.2.
"""

from uuid import UUID, uuid4

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from central_preventiva.adaptadores.persistencia.repositorio_apolices import (
    RepositorioApolices,
)
from central_preventiva.adaptadores.persistencia.repositorio_elegibilidade import (
    RepositorioElegibilidades,
)
from central_preventiva.adaptadores.persistencia.repositorio_segurados import (
    RepositorioSegurados,
)
from central_preventiva.aplicacao.apolice_segurado import (
    ApoliceSegurado,
    ExplicacaoApolice,
    PortasApoliceSegurado,
    ServicoApoliceSegurado,
)
from central_preventiva.composicao.configuracao import Configuracao
from central_preventiva.dominio.avaliador_risco import Criterio

TIPO_PROBLEMA = "application/problem+json"
CAMINHO_APOLICE = "/segurados/{segurado_id}/apolice"
CAMINHO_EXPLICACAO = "/segurados/{segurado_id}/apolice/explicacao/{elegibilidade_id}"


class RespostaApolice(BaseModel):
    """Os dados da apólice exibíveis ao segurado ativo."""

    model_config = ConfigDict(extra="forbid")

    numero: str = Field(description="Número da apólice.")
    tipo: str = Field(description="Tipo da apólice (`residencial`/`automovel`).")
    situacao: str = Field(description="Situação cadastral (`ativa`/`cancelada`/`suspensa`).")
    estado_objetivo: str = Field(
        description="Estado objetivo textual — inclui `expirada` quando a vigência já "
        "passou, mesmo com `situacao='ativa'`. Nunca uma falha técnica."
    )
    vigencia_inicio: str = Field(description="Data de início de vigência (ISO 8601).")
    vigencia_fim: str = Field(description="Data de fim de vigência (ISO 8601).")
    endereco_risco_sintetico: str = Field(description="Endereço sintético do risco.")
    coberturas: list[str] = Field(description="Coberturas contratadas.")
    canal_preferido: str = Field(description="Canal de comunicação preferencial.")
    participa_de_alertas: bool = Field(description="Se o segurado participa de alertas.")


class RespostaCriterioApolice(BaseModel):
    """Um critério comparado pela regra determinística, relevante à apólice."""

    model_config = ConfigDict(extra="forbid")

    operando: str = Field(description="O que foi comparado.")
    valor_observado: str = Field(description="O valor observado no momento da avaliação.")
    atende: bool = Field(description="Se o critério foi atendido.")
    justificativa: str = Field(description="Explicação da comparação, sem promessa de cobertura.")


class RespostaExplicacaoApolice(BaseModel):
    """A explicação de critérios relevantes à apólice, do snapshot de uma execução."""

    model_config = ConfigDict(extra="forbid")

    elegibilidade_id: UUID = Field(description="Identificador da elegibilidade de origem.")
    criterios: list[RespostaCriterioApolice] = Field(
        description="Critérios relevantes à apólice (área, tipo, situação, cobertura)."
    )


class ProblemaApoliceSegurado(BaseModel):
    """Falha da apólice/explicação, com ocorrência, impacto e próxima ação segura."""

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

    corpo = ProblemaApoliceSegurado(
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
        "O identificador do segurado ou da elegibilidade não é um UUID válido.",
        "Nenhum dado pode ser exibido.",
        "Consulte pelos identificadores UUID retornados pela API.",
    )


def _problema_apolice_nao_encontrada() -> JSONResponse:
    """Resposta idêntica para apólice inexistente e apólice de outro segurado (AD-011)."""

    return _problema(
        404,
        "apolice_nao_encontrada",
        "Não existe apólice para este segurado.",
        "Nenhum dado de apólice pode ser exibido.",
        "Consulte a apólice pelo identificador do segurado ativo.",
    )


def _problema_explicacao_nao_encontrada(elegibilidade_id: str) -> JSONResponse:
    """Resposta idêntica para explicação inexistente e de outro segurado (AD-011)."""

    return _problema(
        404,
        "explicacao_nao_encontrada",
        f"A explicação '{elegibilidade_id}' não existe para este segurado.",
        "Nenhuma explicação pode ser exibida.",
        "Consulte a explicação pelo identificador de elegibilidade retornado pela API.",
    )


def _resposta_apolice(apolice: ApoliceSegurado) -> RespostaApolice:
    """Traduz a apólice resolvida pelo caso de uso para o contrato público."""

    return RespostaApolice(
        numero=apolice.numero,
        tipo=apolice.tipo,
        situacao=apolice.situacao,
        estado_objetivo=apolice.estado_objetivo,
        vigencia_inicio=apolice.vigencia_inicio.isoformat(),
        vigencia_fim=apolice.vigencia_fim.isoformat(),
        endereco_risco_sintetico=apolice.endereco_risco_sintetico,
        coberturas=list(apolice.coberturas),
        canal_preferido=apolice.canal_preferido,
        participa_de_alertas=apolice.participa_de_alertas,
    )


def _resposta_criterio(criterio: Criterio) -> RespostaCriterioApolice:
    """Traduz um critério para o contrato público."""

    return RespostaCriterioApolice(
        operando=criterio.operando,
        valor_observado=criterio.valor_observado,
        atende=criterio.atende,
        justificativa=criterio.justificativa,
    )


def _resposta_explicacao(explicacao: ExplicacaoApolice) -> RespostaExplicacaoApolice:
    """Traduz a explicação resolvida pelo caso de uso para o contrato público."""

    return RespostaExplicacaoApolice(
        elegibilidade_id=explicacao.elegibilidade_id,
        criterios=[_resposta_criterio(criterio) for criterio in explicacao.criterios],
    )


def montar_servico_apolice_segurado(configuracao: Configuracao) -> ServicoApoliceSegurado:
    """Compõe o serviço da apólice sobre os repositórios reais do DuckDB local."""

    caminho = configuracao.caminho_banco
    return ServicoApoliceSegurado(
        PortasApoliceSegurado(
            apolices=RepositorioApolices(caminho),
            segurados=RepositorioSegurados(caminho),
            elegibilidades=RepositorioElegibilidades(caminho),
        )
    )


def criar_roteador(configuracao: Configuracao) -> APIRouter:
    """Compõe o recurso da apólice e da explicação de critérios do segurado ativo."""

    roteador = APIRouter(tags=["Apólice do segurado"])
    servico = montar_servico_apolice_segurado(configuracao)

    @roteador.get(
        CAMINHO_APOLICE,
        response_model=RespostaApolice,
        status_code=200,
        summary="Consultar a apólice do segurado ativo",
        description=(
            "Devolve número, situação, vigência, endereço sintético do risco, "
            "coberturas, canal preferencial e participação em alertas. O estado "
            "objetivo distingue `expirada` de `cancelada`/`suspensa`, nunca como falha."
        ),
        responses={
            200: {"description": "Apólice encontrada para este segurado."},
            404: {
                "description": "Segurado sem apólice, ou apólice de outro segurado.",
                "model": ProblemaApoliceSegurado,
            },
            422: {
                "description": "O identificador do segurado não é um UUID válido.",
                "model": ProblemaApoliceSegurado,
            },
        },
    )
    async def consultar_apolice(segurado_id: str) -> RespostaApolice | JSONResponse:  # pyright: ignore[reportUnusedFunction]
        """Traduz `ServicoApoliceSegurado.obter` para o contrato público."""

        try:
            segurado_uuid = UUID(segurado_id)
        except ValueError:
            return _problema_identificador_invalido()

        apolice = servico.obter(segurado_uuid)
        if apolice is None:
            return _problema_apolice_nao_encontrada()
        return _resposta_apolice(apolice)

    @roteador.get(
        CAMINHO_EXPLICACAO,
        response_model=RespostaExplicacaoApolice,
        status_code=200,
        summary="Consultar a explicação de critérios de uma execução",
        description=(
            "Devolve os critérios relevantes à apólice (área, tipo, situação, "
            "cobertura) comparados pela regra determinística numa execução específica — "
            "sempre o snapshot da execução, nunca a apólice atual. Uma elegibilidade "
            "inexistente e uma de outro segurado devolvem exatamente a mesma resposta "
            "`404`."
        ),
        responses={
            200: {"description": "Explicação encontrada para este segurado."},
            404: {
                "description": "Elegibilidade inexistente ou de outro segurado.",
                "model": ProblemaApoliceSegurado,
            },
            422: {
                "description": "Algum identificador não é um UUID válido.",
                "model": ProblemaApoliceSegurado,
            },
        },
    )
    async def consultar_explicacao(  # pyright: ignore[reportUnusedFunction]
        segurado_id: str, elegibilidade_id: str
    ) -> RespostaExplicacaoApolice | JSONResponse:
        """Traduz `ServicoApoliceSegurado.obter_explicacao` para o contrato público."""

        try:
            segurado_uuid = UUID(segurado_id)
            elegibilidade_uuid = UUID(elegibilidade_id)
        except ValueError:
            return _problema_identificador_invalido()

        explicacao = servico.obter_explicacao(segurado_uuid, elegibilidade_uuid)
        if explicacao is None:
            return _problema_explicacao_nao_encontrada(elegibilidade_id)
        return _resposta_explicacao(explicacao)

    return roteador
