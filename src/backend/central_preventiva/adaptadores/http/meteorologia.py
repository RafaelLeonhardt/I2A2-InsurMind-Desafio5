"""Recurso REST/JSON de coleta e consulta meteorológica do INMET."""

from datetime import datetime, timedelta
from hashlib import sha256
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from central_preventiva.adaptadores.meteorologia.cliente_inmet import ClienteInmet
from central_preventiva.adaptadores.meteorologia.normalizador_inmet import NormalizadorInmet
from central_preventiva.adaptadores.persistencia.repositorio_idempotencia import (
    RepositorioIdempotencia,
)
from central_preventiva.adaptadores.persistencia.repositorio_meteorologia import (
    RepositorioAreasMonitoradas,
    RepositorioEventosMeteorologicos,
    RepositorioSincronizacoes,
)
from central_preventiva.aplicacao.coleta_meteorologica import (
    AreaMonitoradaInexistente,
    PortasColetaMeteorologica,
    ServicoColetaMeteorologica,
)
from central_preventiva.aplicacao.portas_meteorologia import INTERVALO_SEGUNDOS_COLETA
from central_preventiva.aplicacao.portas_persistencia import ConflitoIdempotencia
from central_preventiva.composicao.configuracao import Configuracao

TIPO_PROBLEMA = "application/problem+json"
CAMINHO_COLETAS = "/meteorologia/coletas"
CAMINHO_EVENTOS = "/meteorologia/eventos"
CAMINHO_SINCRONIZACOES = "/meteorologia/sincronizacoes"


class SolicitacaoColeta(BaseModel):
    """Corpo da solicitação de coleta manual: a área monitorada a consultar."""

    model_config = ConfigDict(extra="forbid")

    area_id: UUID = Field(description="Identificador da área monitorada a coletar.")


class RespostaColetaAceita(BaseModel):
    """Ack público de uma solicitação de coleta manual aceita ou já registrada."""

    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(description="Identificador da sincronização criada ou já registrada.")
    requisicao_id: UUID = Field(description="Identificador de correlação da tentativa.")
    estado: str = Field(description="Estado da sincronização no momento da resposta.")
    registros_validos: int = Field(description="Quantidade de eventos válidos produzidos.")
    motivo_falha: str | None = Field(description="Motivo tipado da falha, ou nulo se não houve.")
    aceito_em: datetime = Field(
        description="Instante RFC 3339 em UTC em que a solicitação foi aceita."
    )


class RespostaEvento(BaseModel):
    """Evento meteorológico normalizado, pronto para exibição."""

    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(description="Identificador do evento meteorológico.")
    tipo: str = Field(description="Tipo do evento (`chuva_intensa` ou `granizo`).")
    area: str = Field(description="Código IBGE da área onde o evento foi observado.")
    periodo_inicio: datetime = Field(description="Início RFC 3339 em UTC do período do evento.")
    periodo_fim: datetime = Field(description="Término RFC 3339 em UTC do período do evento.")
    intensidade: float = Field(description="Intensidade normalizada da medida observada.")
    proveniencia: str = Field(description="Origem do evento (`real_inmet` ou `sintetico`).")
    instante_observado: datetime = Field(
        description="Instante RFC 3339 em UTC em que a medida foi observada."
    )


class RespostaEventos(BaseModel):
    """Lista pública de eventos meteorológicos normalizados."""

    model_config = ConfigDict(extra="forbid")

    eventos: list[RespostaEvento] = Field(description="Eventos meteorológicos, do mais recente.")


class RespostaSincronizacao(BaseModel):
    """Registro público de uma tentativa de sincronização meteorológica."""

    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(description="Identificador da sincronização.")
    requisicao_id: UUID = Field(description="Identificador de correlação da tentativa.")
    origem: str = Field(description="Origem da tentativa (`automatica` ou `manual`).")
    estado: str = Field(description="Estado atual da sincronização.")
    registros_validos: int = Field(description="Quantidade de eventos válidos produzidos.")
    motivo_falha: str | None = Field(description="Motivo tipado da falha, ou nulo se não houve.")
    iniciado_em: datetime = Field(description="Instante RFC 3339 em UTC de início da tentativa.")
    finalizado_em: datetime | None = Field(
        description="Instante RFC 3339 em UTC de término, ou nulo se em andamento."
    )


class RespostaHistoricoSincronizacoes(BaseModel):
    """Histórico de sincronização, com os marcos exigidos pela consulta de Marina."""

    model_config = ConfigDict(extra="forbid")

    ultima_tentativa: RespostaSincronizacao | None = Field(
        description="Tentativa mais recente registrada, ou nula se nunca houve nenhuma."
    )
    ultima_valida: RespostaSincronizacao | None = Field(
        description="Última tentativa concluída com sucesso, ou nula se nenhuma concluiu."
    )
    proxima_consulta: datetime | None = Field(
        description="Instante RFC 3339 em UTC estimado da próxima coleta automática."
    )
    resultados_anteriores: list[RespostaSincronizacao] = Field(
        description="Histórico completo, da tentativa mais recente para a mais antiga."
    )


class ProblemaMeteorologia(BaseModel):
    """Falha de uma operação meteorológica, com ocorrência, impacto e próxima ação segura."""

    model_config = ConfigDict(extra="forbid")

    codigo: str = Field(description="Código estável que identifica o tipo da falha.")
    correlacao_id: str = Field(description="Identificador único desta ocorrência de falha.")
    ocorrencia: str = Field(description="O que aconteceu, em português brasileiro.")
    impacto: str = Field(description="Efeito prático da falha para quem consultou o recurso.")
    proxima_acao: str = Field(description="Próxima ação segura recomendada para contornar a falha.")


def problema(
    status: int,
    codigo: str,
    ocorrencia: str,
    impacto: str,
    proxima_acao: str,
) -> JSONResponse:
    """Monta a resposta `problem+json` correlacionada de uma falha meteorológica."""

    corpo = ProblemaMeteorologia(
        codigo=codigo,
        correlacao_id=str(uuid4()),
        ocorrencia=ocorrencia,
        impacto=impacto,
        proxima_acao=proxima_acao,
    )
    return JSONResponse(
        status_code=status,
        media_type=TIPO_PROBLEMA,
        content=corpo.model_dump(),
    )


def _resposta_evento(evento: object) -> RespostaEvento:
    """Traduz um `EventoMeteorologico` interno para o contrato REST/JSON público."""

    return RespostaEvento(
        id=evento.id,  # type: ignore[attr-defined]
        tipo=str(evento.tipo),  # type: ignore[attr-defined]
        area=evento.area,  # type: ignore[attr-defined]
        periodo_inicio=evento.periodo_inicio,  # type: ignore[attr-defined]
        periodo_fim=evento.periodo_fim,  # type: ignore[attr-defined]
        intensidade=evento.intensidade,  # type: ignore[attr-defined]
        proveniencia=str(evento.proveniencia),  # type: ignore[attr-defined]
        instante_observado=evento.instante_observado,  # type: ignore[attr-defined]
    )


def _resposta_sincronizacao(sincronizacao: object) -> RespostaSincronizacao:
    """Traduz uma `Sincronizacao` interna para o contrato REST/JSON público."""

    return RespostaSincronizacao(
        id=sincronizacao.id,  # type: ignore[attr-defined]
        requisicao_id=sincronizacao.requisicao_id,  # type: ignore[attr-defined]
        origem=str(sincronizacao.origem),  # type: ignore[attr-defined]
        estado=str(sincronizacao.estado),  # type: ignore[attr-defined]
        registros_validos=sincronizacao.registros_validos,  # type: ignore[attr-defined]
        motivo_falha=sincronizacao.motivo_falha,  # type: ignore[attr-defined]
        iniciado_em=sincronizacao.iniciado_em,  # type: ignore[attr-defined]
        finalizado_em=sincronizacao.finalizado_em,  # type: ignore[attr-defined]
    )


def montar_portas_coleta(configuracao: Configuracao) -> PortasColetaMeteorologica:
    """Compõe as portas reais da coleta meteorológica, reusadas pelo roteador e pelo agendador."""

    return PortasColetaMeteorologica(
        idempotencia=RepositorioIdempotencia(configuracao.caminho_banco),
        areas=RepositorioAreasMonitoradas(configuracao.caminho_banco),
        coletor=ClienteInmet(configuracao.url_base_inmet),
        normalizador=NormalizadorInmet(),
        eventos=RepositorioEventosMeteorologicos(configuracao.caminho_banco),
        sincronizacoes=RepositorioSincronizacoes(configuracao.caminho_banco),
    )


def criar_roteador(configuracao: Configuracao) -> APIRouter:
    """Compõe o recurso de meteorologia sobre os adaptadores reais do INMET."""

    roteador = APIRouter(tags=["Meteorologia"])
    portas = montar_portas_coleta(configuracao)
    eventos_repo = portas.eventos
    sincronizacoes_repo = portas.sincronizacoes
    servico = ServicoColetaMeteorologica(portas)

    @roteador.post(
        CAMINHO_COLETAS,
        response_model=RespostaColetaAceita,
        status_code=202,
        summary="Solicitar uma coleta meteorológica manual",
        description=(
            "Solicita, de forma idempotente, uma coleta meteorológica manual para a área "
            "informada. Exige o cabeçalho `Idempotency-Key` em toda requisição."
        ),
        responses={
            202: {"description": "Coleta manual aceita e concluída."},
            404: {"description": "Área monitorada desconhecida.", "model": ProblemaMeteorologia},
            409: {
                "description": "Conflito de idempotência.",
                "model": ProblemaMeteorologia,
            },
            422: {
                "description": "Requisição sem o cabeçalho `Idempotency-Key`.",
                "model": ProblemaMeteorologia,
            },
        },
    )
    async def solicitar_coleta(  # pyright: ignore[reportUnusedFunction]
        corpo: SolicitacaoColeta,
        requisicao: Request,
        idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    ) -> RespostaColetaAceita | JSONResponse:
        """Traduz `solicitar_coleta_manual` para o contrato REST/JSON público."""

        if idempotency_key is None or not idempotency_key.strip():
            return problema(
                422,
                "idempotency_key_ausente",
                "A requisição de coleta manual não informou o cabeçalho Idempotency-Key.",
                "Nenhuma coleta foi solicitada.",
                "Repita a requisição incluindo um cabeçalho Idempotency-Key único.",
            )

        hash_requisicao = sha256(await requisicao.body()).hexdigest()

        try:
            aceita = await servico.solicitar_coleta_manual(
                corpo.area_id, idempotency_key, hash_requisicao
            )
        except AreaMonitoradaInexistente:
            return problema(
                404,
                "area_monitorada_desconhecida",
                f"A área monitorada '{corpo.area_id}' não existe.",
                "Nenhuma coleta foi solicitada.",
                "Consulte as áreas monitoradas configuradas e repita com um area_id válido.",
            )
        except ConflitoIdempotencia:
            return problema(
                409,
                "conflito_idempotencia",
                "A chave de idempotência já foi usada com outro conteúdo de requisição.",
                "Nenhuma nova coleta foi solicitada.",
                "Gere uma nova Idempotency-Key para solicitar outra coleta.",
            )

        sincronizacao = aceita.sincronizacao
        return RespostaColetaAceita(
            id=sincronizacao.id,
            requisicao_id=sincronizacao.requisicao_id,
            estado=str(sincronizacao.estado),
            registros_validos=sincronizacao.registros_validos,
            motivo_falha=sincronizacao.motivo_falha,
            aceito_em=aceita.aceito_em,
        )

    @roteador.get(
        CAMINHO_EVENTOS,
        response_model=RespostaEventos,
        status_code=200,
        summary="Consultar os eventos meteorológicos normalizados",
        description="Devolve os eventos meteorológicos já normalizados, do mais recente.",
        responses={200: {"description": "Eventos meteorológicos normalizados."}},
    )
    async def consultar_eventos() -> RespostaEventos:  # pyright: ignore[reportUnusedFunction]
        """Traduz a listagem de eventos para o contrato REST/JSON público."""

        return RespostaEventos(
            eventos=[_resposta_evento(evento) for evento in eventos_repo.listar()]
        )

    @roteador.get(
        CAMINHO_SINCRONIZACOES,
        response_model=RespostaHistoricoSincronizacoes,
        status_code=200,
        summary="Consultar o histórico de sincronizações meteorológicas",
        description=(
            "Devolve a última tentativa, a última coleta válida, a próxima consulta "
            "estimada e o histórico completo de sincronizações, só com dados persistidos."
        ),
        responses={200: {"description": "Histórico de sincronizações meteorológicas."}},
    )
    async def consultar_sincronizacoes() -> RespostaHistoricoSincronizacoes:  # pyright: ignore[reportUnusedFunction]
        """Traduz o histórico de sincronizações para o contrato REST/JSON público."""

        recentes = sincronizacoes_repo.listar_recentes()
        ultima_tentativa = recentes[0] if recentes else None
        ultima_valida = next((s for s in recentes if str(s.estado) == "concluido"), None)
        proxima_consulta = (
            ultima_tentativa.iniciado_em + timedelta(seconds=INTERVALO_SEGUNDOS_COLETA)
            if ultima_tentativa is not None
            else None
        )
        return RespostaHistoricoSincronizacoes(
            ultima_tentativa=(
                _resposta_sincronizacao(ultima_tentativa) if ultima_tentativa is not None else None
            ),
            ultima_valida=(
                _resposta_sincronizacao(ultima_valida) if ultima_valida is not None else None
            ),
            proxima_consulta=proxima_consulta,
            resultados_anteriores=[_resposta_sincronizacao(s) for s in recentes],
        )

    return roteador
