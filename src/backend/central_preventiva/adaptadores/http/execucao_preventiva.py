"""Recurso REST/JSON de início e acompanhamento da execução preventiva (RUNNER-01..09)."""

from datetime import datetime
from hashlib import sha256
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from central_preventiva.adaptadores.http.meteorologia import montar_portas_coleta
from central_preventiva.adaptadores.http.preflight_ia import montar_servico_geracao
from central_preventiva.adaptadores.persistencia.repositorio_avaliacoes_risco import (
    RepositorioAvaliacoesRisco,
)
from central_preventiva.adaptadores.persistencia.repositorio_elegibilidade import (
    RepositorioCandidatosElegibilidade,
    RepositorioElegibilidades,
)
from central_preventiva.adaptadores.persistencia.repositorio_execucao_preventiva import (
    RepositorioExecucaoPreventiva,
)
from central_preventiva.adaptadores.persistencia.repositorio_idempotencia import (
    RepositorioIdempotencia,
)
from central_preventiva.adaptadores.persistencia.repositorio_meteorologia import (
    RepositorioAreasMonitoradas,
    RepositorioEventosMeteorologicos,
)
from central_preventiva.adaptadores.persistencia.repositorio_regras import RepositorioRegras
from central_preventiva.aplicacao.avaliacao_elegibilidade import (
    PortasAvaliacaoElegibilidade,
    ServicoAvaliacaoElegibilidade,
)
from central_preventiva.aplicacao.avaliacao_risco import PortasAvaliacaoRisco, ServicoAvaliacaoRisco
from central_preventiva.aplicacao.coleta_meteorologica import (
    AreaMonitoradaInexistente,
    ServicoColetaMeteorologica,
)
from central_preventiva.aplicacao.gerenciador_execucoes import (
    GerenciadorExecucoes,
    PortasGerenciadorExecucoes,
)
from central_preventiva.aplicacao.portas_persistencia import ConflitoIdempotencia
from central_preventiva.composicao.configuracao import Configuracao
from central_preventiva.dominio.estados_execucao import EstadoExecucao

TIPO_PROBLEMA = "application/problem+json"
CAMINHO_EXECUCOES = "/execucoes"
CAMINHO_EXECUCAO = "/execucoes/{execucao_id}"
TAMANHO_PREVIA_PUBLICO = 5


class SolicitacaoExecucao(BaseModel):
    """Corpo da solicitação de início de execução: a área monitorada a avaliar."""

    model_config = ConfigDict(extra="forbid")

    area_id: UUID = Field(description="Identificador da área monitorada a avaliar.")


class RespostaExecucaoAceita(BaseModel):
    """Ack público de uma execução criada ou já em andamento com a mesma chave."""

    model_config = ConfigDict(extra="forbid")

    execucao_id: UUID = Field(description="Identificador da execução criada ou já em andamento.")


class RespostaMarco(BaseModel):
    """Um marco de transição já persistido da execução."""

    model_config = ConfigDict(extra="forbid")

    marco: str = Field(description="Nome do marco de transição.")
    causa: str | None = Field(description="Causa registrada, ou nula quando não houve falha.")
    criado_em: datetime = Field(
        description="Instante RFC 3339 em UTC em que o marco foi registrado."
    )


class RespostaPreviaPublico(BaseModel):
    """Um item da amostra do público elegível formado."""

    model_config = ConfigDict(extra="forbid")

    nome_segurado: str = Field(description="Nome do segurado sintético incluído.")
    canal: str = Field(description="Canal preferencial do segurado, no momento da avaliação.")


class RespostaExecucao(BaseModel):
    """Estado, marcos e, quando aplicável, prévia do público elegível de uma execução."""

    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(description="Identificador da execução.")
    estado: str = Field(description="Estado atual da execução.")
    marcos: list[RespostaMarco] = Field(
        description="Marcos de transição já persistidos, na ordem em que ocorreram."
    )
    publico_elegivel_total: int | None = Field(
        description=(
            "Quantidade total de incluídos no público elegível; nulo fora de "
            "'aguardando_geracao'."
        )
    )
    publico_elegivel_previa: list[RespostaPreviaPublico] = Field(
        description=(
            f"Amostra de até {TAMANHO_PREVIA_PUBLICO} incluídos no público elegível; "
            "vazia fora de 'aguardando_geracao'."
        )
    )
    execucao_origem_id: UUID | None = Field(
        description=(
            "Execução terminal que originou esta nova tentativa; nula quando esta execução "
            "não é correlacionada a nenhuma outra."
        )
    )
    retentativas: list[UUID] = Field(
        description=(
            "Execuções criadas como nova tentativa a partir desta; vazia quando não houve "
            "nenhuma. Cada execução mantém seu próprio histórico, sem mesclar marcos."
        )
    )


class ProblemaExecucao(BaseModel):
    """Falha da operação de execução, com ocorrência, impacto e próxima ação segura."""

    model_config = ConfigDict(extra="forbid")

    codigo: str = Field(description="Código estável que identifica o tipo da falha.")
    correlacao_id: str = Field(description="Identificador único desta ocorrência de falha.")
    ocorrencia: str = Field(description="O que aconteceu, em português brasileiro.")
    impacto: str = Field(description="Efeito prático da falha para quem consultou o recurso.")
    proxima_acao: str = Field(description="Próxima ação segura recomendada para contornar a falha.")


def problema(
    status: int, codigo: str, ocorrencia: str, impacto: str, proxima_acao: str
) -> JSONResponse:
    """Monta a resposta `problem+json` correlacionada de uma falha de execução."""

    corpo = ProblemaExecucao(
        codigo=codigo,
        correlacao_id=str(uuid4()),
        ocorrencia=ocorrencia,
        impacto=impacto,
        proxima_acao=proxima_acao,
    )
    return JSONResponse(status_code=status, media_type=TIPO_PROBLEMA, content=corpo.model_dump())


def montar_portas_execucao(configuracao: Configuracao) -> PortasGerenciadorExecucoes:
    """Compõe as portas reais do orquestrador, reusadas pelo roteador e pelo lifespan."""

    caminho = configuracao.caminho_banco
    return PortasGerenciadorExecucoes(
        execucoes=RepositorioExecucaoPreventiva(caminho),
        areas=RepositorioAreasMonitoradas(caminho),
        eventos=RepositorioEventosMeteorologicos(caminho),
        avaliacoes_risco=RepositorioAvaliacoesRisco(caminho),
        regras=RepositorioRegras(caminho),
        idempotencia=RepositorioIdempotencia(caminho),
        coleta=ServicoColetaMeteorologica(montar_portas_coleta(configuracao)),
        risco=ServicoAvaliacaoRisco(
            PortasAvaliacaoRisco(
                regras=RepositorioRegras(caminho),
                avaliacoes=RepositorioAvaliacoesRisco(caminho),
                execucoes=RepositorioExecucaoPreventiva(caminho),
            )
        ),
        elegibilidade=ServicoAvaliacaoElegibilidade(
            PortasAvaliacaoElegibilidade(
                candidatos=RepositorioCandidatosElegibilidade(caminho),
                elegibilidades=RepositorioElegibilidades(caminho),
            )
        ),
        geracao=montar_servico_geracao(configuracao),
    )


def criar_roteador(configuracao: Configuracao) -> APIRouter:
    """Compõe o recurso de início e acompanhamento da execução preventiva."""

    roteador = APIRouter(tags=["Execução"])
    execucoes_repo = RepositorioExecucaoPreventiva(configuracao.caminho_banco)
    elegibilidades_repo = RepositorioElegibilidades(configuracao.caminho_banco)
    gerenciador = GerenciadorExecucoes(montar_portas_execucao(configuracao))

    @roteador.post(
        CAMINHO_EXECUCOES,
        response_model=RespostaExecucaoAceita,
        status_code=202,
        summary="Iniciar uma execução preventiva",
        description=(
            "Inicia, de forma idempotente, a orquestração completa de coleta, avaliação "
            "de risco e avaliação de elegibilidade para a área informada, sem exigir "
            "nenhum clique manual intermediário (RUNNER-01). Exige o cabeçalho "
            "`Idempotency-Key` em toda requisição."
        ),
        responses={
            202: {"description": "Execução aceita e em andamento."},
            404: {"description": "Área monitorada desconhecida.", "model": ProblemaExecucao},
            409: {"description": "Conflito de idempotência.", "model": ProblemaExecucao},
            422: {
                "description": "Requisição sem o cabeçalho `Idempotency-Key`.",
                "model": ProblemaExecucao,
            },
        },
    )
    async def iniciar_execucao(  # pyright: ignore[reportUnusedFunction]
        corpo: SolicitacaoExecucao,
        requisicao: Request,
        idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    ) -> RespostaExecucaoAceita | JSONResponse:
        """Traduz `GerenciadorExecucoes.iniciar` para o contrato REST/JSON público."""

        if idempotency_key is None or not idempotency_key.strip():
            return problema(
                422,
                "idempotency_key_ausente",
                "A requisição de início de execução não informou o cabeçalho Idempotency-Key.",
                "Nenhuma execução foi iniciada.",
                "Repita a requisição incluindo um cabeçalho Idempotency-Key único.",
            )

        hash_requisicao = sha256(await requisicao.body()).hexdigest()

        try:
            execucao_id = await gerenciador.iniciar(corpo.area_id, idempotency_key, hash_requisicao)
        except AreaMonitoradaInexistente:
            return problema(
                404,
                "area_monitorada_desconhecida",
                f"A área monitorada '{corpo.area_id}' não existe.",
                "Nenhuma execução foi iniciada.",
                "Consulte as áreas monitoradas configuradas e repita com um area_id válido.",
            )
        except ConflitoIdempotencia:
            return problema(
                409,
                "conflito_idempotencia",
                "A chave de idempotência já foi usada com outro conteúdo de requisição.",
                "Nenhuma nova execução foi iniciada.",
                "Gere uma nova Idempotency-Key para iniciar outra execução.",
            )

        return RespostaExecucaoAceita(execucao_id=execucao_id)

    @roteador.get(
        CAMINHO_EXECUCAO,
        response_model=RespostaExecucao,
        status_code=200,
        summary="Consultar o acompanhamento de uma execução preventiva",
        description=(
            "Devolve o estado atual, os marcos de transição já persistidos e, quando o "
            "estado é 'aguardando_geracao', a quantidade total e uma prévia do público "
            "elegível formado (RUNNER-05). Traz também a navegação entre execuções "
            "correlacionadas: a origem desta execução e as novas tentativas criadas a "
            "partir dela, sem mesclar históricos."
        ),
        responses={
            200: {"description": "Execução encontrada."},
            404: {"description": "Execução inexistente.", "model": ProblemaExecucao},
            422: {
                "description": "O identificador da execução não é um UUID válido.",
                "model": ProblemaExecucao,
            },
        },
    )
    async def consultar_execucao(  # pyright: ignore[reportUnusedFunction]
        execucao_id: str,
    ) -> RespostaExecucao | JSONResponse:
        """Traduz o snapshot e os marcos persistidos para o contrato REST/JSON público."""

        try:
            execucao_uuid = UUID(execucao_id)
        except ValueError:
            return problema(
                422,
                "execucao_id_invalido",
                f"'{execucao_id}' não é um identificador de execução válido.",
                "Nenhum acompanhamento pode ser exibido.",
                "Consulte a execução pelo identificador UUID retornado pela API.",
            )

        snapshot = execucoes_repo.buscar(execucao_uuid)
        if snapshot is None:
            return problema(
                404,
                "execucao_inexistente",
                f"A execução '{execucao_id}' não existe.",
                "Nenhum acompanhamento pode ser exibido.",
                "Inicie uma nova execução em POST /execucoes.",
            )

        total: int | None = None
        previa: list[RespostaPreviaPublico] = []
        if snapshot.estado == EstadoExecucao.AGUARDANDO_GERACAO:
            contagem = elegibilidades_repo.contar_por_execucao(execucao_uuid)
            total = contagem.incluidos
            previa = [
                RespostaPreviaPublico(nome_segurado=registro.nome_segurado, canal=registro.canal)
                for registro in elegibilidades_repo.listar_por_execucao(execucao_uuid)
                if registro.elegivel
            ][:TAMANHO_PREVIA_PUBLICO]

        return RespostaExecucao(
            id=snapshot.id,
            estado=str(snapshot.estado),
            marcos=[
                RespostaMarco(marco=marco.marco, causa=marco.causa, criado_em=marco.criado_em)
                for marco in execucoes_repo.listar_marcos(execucao_uuid)
            ],
            publico_elegivel_total=total,
            publico_elegivel_previa=previa,
            execucao_origem_id=snapshot.execucao_origem_id,
            retentativas=[
                correlacionada.id
                for correlacionada in execucoes_repo.listar_correlacionadas(execucao_uuid)
            ],
        )

    return roteador
