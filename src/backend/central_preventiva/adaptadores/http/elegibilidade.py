"""Recurso REST/JSON de consulta e explicação do público elegível (ELEG-08, ELEG-09)."""

from datetime import datetime
from uuid import UUID, uuid4

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from central_preventiva.adaptadores.persistencia.repositorio_elegibilidade import (
    RegistroElegibilidade,
    RepositorioElegibilidades,
)
from central_preventiva.composicao.configuracao import Configuracao

TIPO_PROBLEMA = "application/problem+json"
CAMINHO_ELEGIBILIDADE = "/execucoes/{execucao_id}/elegibilidade"
CAMINHO_REGISTRO_ELEGIBILIDADE = "/execucoes/{execucao_id}/elegibilidade/{registro_id}"


class RespostaResumoElegibilidade(BaseModel):
    """Um resultado de elegibilidade na listagem: segurado, apólice, localização, canal."""

    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(description="Identificador do resultado de elegibilidade.")
    nome_segurado: str = Field(description="Nome do segurado sintético avaliado.")
    apolice_id: UUID = Field(description="Identificador da apólice avaliada.")
    codigo_ibge_area: str = Field(description="Código IBGE da área da apólice avaliada.")
    canal: str = Field(description="Canal preferencial do segurado, no momento da avaliação.")
    elegivel: bool = Field(description="Se a combinação foi incluída no público elegível.")


class RespostaElegibilidade(BaseModel):
    """Quantidades e lista do público avaliado de uma execução (ELEG-08)."""

    model_config = ConfigDict(extra="forbid")

    incluidos: int = Field(description="Quantidade de resultados incluídos.")
    excluidos: int = Field(description="Quantidade de resultados excluídos.")
    registros: list[RespostaResumoElegibilidade] = Field(
        description="Resultados de elegibilidade, mais recentes primeiro."
    )


class RespostaCriterioElegibilidade(BaseModel):
    """Um critério avaliado: operando, valor observado, resultado e justificativa."""

    model_config = ConfigDict(extra="forbid")

    operando: str = Field(description="O que foi comparado (ex.: área afetada, cobertura).")
    valor_observado: str = Field(description="Valor observado para este critério.")
    atende: bool = Field(description="Se o valor observado atende ao critério.")
    justificativa: str = Field(description="Explicação em português brasileiro do resultado.")


class RespostaDetalheElegibilidade(BaseModel):
    """Explicação completa de um resultado de elegibilidade (ELEG-09)."""

    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(description="Identificador do resultado de elegibilidade.")
    execucao_id: UUID = Field(description="Identificador da execução avaliada.")
    evento_id: UUID = Field(description="Identificador do evento meteorológico avaliado.")
    regra_id: UUID = Field(description="Identificador da versão de regra usada na avaliação.")
    regra_versao: int = Field(description="Versão da regra usada na avaliação.")
    segurado_id: UUID = Field(description="Identificador do segurado avaliado.")
    nome_segurado: str = Field(description="Nome do segurado sintético avaliado.")
    apolice_id: UUID = Field(description="Identificador da apólice avaliada.")
    codigo_ibge_area: str = Field(description="Código IBGE da área da apólice avaliada.")
    elegivel: bool = Field(description="Se a combinação foi incluída no público elegível.")
    criterios: list[RespostaCriterioElegibilidade] = Field(
        description="Critérios avaliados, na ordem aplicada."
    )
    canal: str = Field(description="Canal preferencial do segurado, no momento da avaliação.")
    justificativa: str = Field(description="Explicação objetiva do resultado, em português.")
    criado_em: datetime = Field(description="Instante RFC 3339 em UTC da avaliação.")


class ProblemaElegibilidade(BaseModel):
    """Falha da consulta de elegibilidade, com ocorrência, impacto e próxima ação segura."""

    model_config = ConfigDict(extra="forbid")

    codigo: str = Field(description="Código estável que identifica o tipo da falha.")
    correlacao_id: str = Field(description="Identificador único desta ocorrência de falha.")
    ocorrencia: str = Field(description="O que aconteceu, em português brasileiro.")
    impacto: str = Field(description="Efeito prático da falha para quem consultou o recurso.")
    proxima_acao: str = Field(description="Próxima ação segura recomendada para contornar a falha.")


def problema(
    status: int, codigo: str, ocorrencia: str, impacto: str, proxima_acao: str
) -> JSONResponse:
    """Monta a resposta `problem+json` correlacionada de uma falha de elegibilidade."""

    corpo = ProblemaElegibilidade(
        codigo=codigo,
        correlacao_id=str(uuid4()),
        ocorrencia=ocorrencia,
        impacto=impacto,
        proxima_acao=proxima_acao,
    )
    return JSONResponse(status_code=status, media_type=TIPO_PROBLEMA, content=corpo.model_dump())


def _resposta_resumo(registro: RegistroElegibilidade) -> RespostaResumoElegibilidade:
    """Traduz um `RegistroElegibilidade` para o resumo público da listagem."""

    return RespostaResumoElegibilidade(
        id=registro.id,
        nome_segurado=registro.nome_segurado,
        apolice_id=registro.apolice_id,
        codigo_ibge_area=registro.codigo_ibge_area,
        canal=registro.canal,
        elegivel=registro.elegivel,
    )


def _resposta_detalhe(registro: RegistroElegibilidade) -> RespostaDetalheElegibilidade:
    """Traduz um `RegistroElegibilidade` para a explicação completa pública."""

    assert registro.execucao_id is not None
    return RespostaDetalheElegibilidade(
        id=registro.id,
        execucao_id=registro.execucao_id,
        evento_id=registro.evento_id,
        regra_id=registro.regra_id,
        regra_versao=registro.regra_versao,
        segurado_id=registro.segurado_id,
        nome_segurado=registro.nome_segurado,
        apolice_id=registro.apolice_id,
        codigo_ibge_area=registro.codigo_ibge_area,
        elegivel=registro.elegivel,
        criterios=[
            RespostaCriterioElegibilidade(
                operando=criterio.operando,
                valor_observado=criterio.valor_observado,
                atende=criterio.atende,
                justificativa=criterio.justificativa,
            )
            for criterio in registro.criterios
        ],
        canal=registro.canal,
        justificativa=registro.justificativa,
        criado_em=registro.criado_em,
    )


def criar_roteador(configuracao: Configuracao) -> APIRouter:
    """Compõe o recurso de consulta e explicação do público elegível."""

    roteador = APIRouter(tags=["Elegibilidade"])
    elegibilidades_repo = RepositorioElegibilidades(configuracao.caminho_banco)

    @roteador.get(
        CAMINHO_ELEGIBILIDADE,
        response_model=RespostaElegibilidade,
        status_code=200,
        summary="Consultar o público elegível de uma execução",
        description=(
            "Devolve as quantidades de incluídos e excluídos e a lista do público "
            "avaliado, com segurado sintético, apólice, localização, canal e resultado. "
            "Uma execução sem nenhum resultado devolve quantidades zeradas e lista vazia."
        ),
        responses={
            200: {"description": "Público elegível encontrado (pode ser vazio)."},
            422: {
                "description": "O identificador da execução não é um UUID válido.",
                "model": ProblemaElegibilidade,
            },
        },
    )
    async def consultar_elegibilidade(  # pyright: ignore[reportUnusedFunction]
        execucao_id: str,
    ) -> RespostaElegibilidade | JSONResponse:
        """Traduz `RepositorioElegibilidades.listar_por_execucao`/`contar_por_execucao`."""

        try:
            execucao_uuid = UUID(execucao_id)
        except ValueError:
            return problema(
                422,
                "execucao_id_invalido",
                f"'{execucao_id}' não é um identificador de execução válido.",
                "Nenhum público elegível pode ser exibido.",
                "Consulte a execução pelo identificador UUID retornado pela API.",
            )

        contagem = elegibilidades_repo.contar_por_execucao(execucao_uuid)
        registros = elegibilidades_repo.listar_por_execucao(execucao_uuid)
        return RespostaElegibilidade(
            incluidos=contagem.incluidos,
            excluidos=contagem.excluidos,
            registros=[_resposta_resumo(registro) for registro in registros],
        )

    @roteador.get(
        CAMINHO_REGISTRO_ELEGIBILIDADE,
        response_model=RespostaDetalheElegibilidade,
        status_code=200,
        summary="Consultar a explicação completa de um resultado de elegibilidade",
        description=(
            "Devolve regra e versão, operando, valor observado, resultado e justificativa "
            "de cada critério da decisão de elegibilidade já tomada, sem recalcular nada."
        ),
        responses={
            200: {"description": "Resultado de elegibilidade encontrado."},
            404: {
                "description": "Resultado inexistente ou de outra execução.",
                "model": ProblemaElegibilidade,
            },
            422: {
                "description": "Algum identificador informado não é um UUID válido.",
                "model": ProblemaElegibilidade,
            },
        },
    )
    async def consultar_registro_elegibilidade(  # pyright: ignore[reportUnusedFunction]
        execucao_id: str, registro_id: str
    ) -> RespostaDetalheElegibilidade | JSONResponse:
        """Traduz `RepositorioElegibilidades.obter_por_id` para o contrato público."""

        try:
            execucao_uuid = UUID(execucao_id)
            registro_uuid = UUID(registro_id)
        except ValueError:
            return problema(
                422,
                "identificador_invalido",
                "O identificador da execução ou do resultado não é um UUID válido.",
                "Nenhuma explicação pode ser exibida.",
                "Consulte o resultado pelos identificadores UUID retornados pela API.",
            )

        registro = elegibilidades_repo.obter_por_id(registro_uuid)
        if registro is None or registro.execucao_id != execucao_uuid:
            return problema(
                404,
                "resultado_elegibilidade_inexistente",
                f"O resultado '{registro_id}' não existe para a execução '{execucao_id}'.",
                "Nenhuma explicação pode ser exibida.",
                "Consulte a lista de elegibilidade da execução e repita com um id válido.",
            )

        return _resposta_detalhe(registro)

    return roteador
