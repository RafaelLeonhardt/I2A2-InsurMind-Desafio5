"""Recurso REST/JSON de prontidão das dependências."""

from datetime import UTC, datetime
from hashlib import sha256
from typing import Annotated, get_args
from uuid import uuid4

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from central_preventiva.adaptadores.persistencia.repositorio_idempotencia import (
    RepositorioIdempotencia,
)
from central_preventiva.adaptadores.prontidao.sonda_backend import SondaBackend
from central_preventiva.adaptadores.prontidao.sonda_banco_dados import SondaBancoDados
from central_preventiva.adaptadores.prontidao.sonda_inmet import SondaInmet
from central_preventiva.adaptadores.prontidao.sonda_openai import SondaOpenAI
from central_preventiva.aplicacao.portas_persistencia import ConflitoIdempotencia
from central_preventiva.aplicacao.portas_prontidao import NomeDependencia, VerificacaoEmAndamento
from central_preventiva.aplicacao.prontidao import (
    DependenciaLocalNaoReverifica,
    PortasProntidao,
    RegistroProntidao,
    aceito_em_de,
    consultar_prontidao,
    operacao_verificacao,
    solicitar_nova_verificacao,
)
from central_preventiva.composicao.configuracao import Configuracao

TIPO_PROBLEMA = "application/problem+json"
CAMINHO_DEPENDENCIAS = "/prontidao/dependencias"
CAMINHO_VERIFICACOES = "/prontidao/dependencias/{nome}/verificacoes"

NOMES_CONHECIDOS: frozenset[str] = frozenset(get_args(NomeDependencia))


class RespostaDependencia(BaseModel):
    """Estado de prontidão de uma única dependência, pronto para exibição."""

    model_config = ConfigDict(extra="forbid")

    nome: str = Field(description="Nome canônico da dependência verificada.")
    estado: str = Field(description="Estado atual de prontidão da dependência.")
    verificado_em: datetime | None = Field(
        description="Instante RFC 3339 em UTC da última verificação, ou nulo se ainda não houve."
    )
    causa: str | None = Field(
        description="Causa da indisponibilidade ou degradação, ou nula quando disponível."
    )
    impacto: str = Field(description="Efeito prático do estado atual para quem consulta.")
    acao_disponivel: str = Field(description="Ação segura disponível dado o estado atual.")


class RespostaDependencias(BaseModel):
    """Resposta pública consolidada das 4 dependências."""

    model_config = ConfigDict(extra="forbid")

    dependencias: list[RespostaDependencia] = Field(
        description="Estado de prontidão de cada uma das 4 dependências monitoradas."
    )


class RespostaVerificacaoAceita(BaseModel):
    """Ack de uma nova verificação aceita para processamento em segundo plano."""

    model_config = ConfigDict(extra="forbid")

    nome: str = Field(description="Nome canônico da dependência cuja verificação foi aceita.")
    estado: str = Field(
        description="Estado da dependência no momento em que a verificação foi aceita."
    )
    aceito_em: datetime = Field(
        description="Instante RFC 3339 em UTC em que a nova verificação foi aceita."
    )


class ProblemaProntidao(BaseModel):
    """Falha da operação de prontidão, com ocorrência, impacto e próxima ação segura."""

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
    """Monta a resposta `problem+json` correlacionada de uma falha de prontidão."""

    corpo = ProblemaProntidao(
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


def criar_roteador(configuracao: Configuracao) -> APIRouter:
    """Compõe o recurso de prontidão sobre as sondas reais e um registro por processo."""

    roteador = APIRouter(tags=["Prontidão"])
    registro = RegistroProntidao()
    idempotencia = RepositorioIdempotencia(configuracao.caminho_banco)

    chave_openai = configuracao.chave_openai
    portas = PortasProntidao(
        backend=SondaBackend(),
        banco_dados=SondaBancoDados(configuracao.caminho_banco),
        inmet=SondaInmet(configuracao.url_base_inmet),
        openai=SondaOpenAI(chave_openai.get_secret_value()) if chave_openai else None,
    )

    @roteador.get(
        CAMINHO_DEPENDENCIAS,
        response_model=RespostaDependencias,
        status_code=200,
        summary="Consultar a prontidão das dependências",
        description=(
            "Devolve o estado mais recente de backend, banco de dados, INMET e OpenAI. "
            "Backend e banco de dados são recomputados a cada chamada; INMET e OpenAI, na "
            "primeira consulta, disparam a verificação em segundo plano e retornam "
            "'verificando'."
        ),
        responses={200: {"description": "Estado de prontidão das 4 dependências."}},
    )
    async def consultar() -> RespostaDependencias:  # pyright: ignore[reportUnusedFunction]
        """Traduz `consultar_prontidao` para o contrato REST/JSON público."""

        estados = await consultar_prontidao(portas, registro)
        return RespostaDependencias(
            dependencias=[
                RespostaDependencia(
                    nome=estado.nome,
                    estado=str(estado.estado),
                    verificado_em=estado.verificado_em,
                    causa=estado.causa,
                    impacto=estado.impacto,
                    acao_disponivel=estado.acao_disponivel,
                )
                for estado in estados
            ]
        )

    @roteador.post(
        CAMINHO_VERIFICACOES,
        response_model=RespostaVerificacaoAceita,
        status_code=202,
        summary="Solicitar uma nova verificação de prontidão",
        description=(
            "Solicita, de forma assíncrona e idempotente, uma nova verificação de INMET ou "
            "OpenAI. Exige o cabeçalho `Idempotency-Key` em toda requisição. Backend e banco "
            "de dados não aceitam este recurso: já são recomputados a cada `GET`."
        ),
        responses={
            202: {"description": "Nova verificação aceita e em andamento."},
            404: {"description": "Dependência desconhecida.", "model": ProblemaProntidao},
            409: {
                "description": "Conflito de idempotência ou verificação já em andamento.",
                "model": ProblemaProntidao,
            },
            422: {
                "description": "Cabeçalho ausente ou dependência local sem re-verificação.",
                "model": ProblemaProntidao,
            },
        },
    )
    async def verificar_novamente(  # pyright: ignore[reportUnusedFunction]
        nome: str,
        requisicao: Request,
        idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    ) -> RespostaVerificacaoAceita | JSONResponse:
        """Traduz `solicitar_nova_verificacao` para o contrato REST/JSON público."""

        if nome not in NOMES_CONHECIDOS:
            return problema(
                404,
                "dependencia_desconhecida",
                f"A dependência '{nome}' é desconhecida.",
                "Nenhuma verificação foi solicitada.",
                "Use um dos nomes válidos: backend, banco_dados, inmet, openai.",
            )

        if idempotency_key is None or not idempotency_key.strip():
            return problema(
                422,
                "idempotency_key_ausente",
                "A requisição de verificação não informou o cabeçalho Idempotency-Key.",
                "Nenhuma verificação foi solicitada.",
                "Repita a requisição incluindo um cabeçalho Idempotency-Key único.",
            )

        hash_requisicao = sha256(await requisicao.body()).hexdigest()
        nome_valido: NomeDependencia = nome  # pyright: ignore[reportAssignmentType]

        try:
            estado = await solicitar_nova_verificacao(
                portas, idempotencia, registro, nome_valido, idempotency_key, hash_requisicao
            )
        except DependenciaLocalNaoReverifica:
            return problema(
                422,
                "dependencia_local_nao_reverifica",
                f"A dependência '{nome}' é recomputada a cada consulta de prontidão.",
                "Nenhuma verificação foi solicitada.",
                "Consulte o estado mais recente em GET /prontidao/dependencias.",
            )
        except ConflitoIdempotencia:
            return problema(
                409,
                "conflito_idempotencia",
                "A chave de idempotência já foi usada com outro conteúdo de requisição.",
                "Nenhuma nova verificação foi solicitada.",
                "Gere uma nova Idempotency-Key para solicitar outra verificação.",
            )
        except VerificacaoEmAndamento:
            return problema(
                409,
                "verificacao_em_andamento",
                f"Já existe uma verificação em andamento para a dependência '{nome}'.",
                "Nenhuma nova verificação foi solicitada; a verificação em curso continua.",
                "Aguarde a conclusão e consulte o progresso em GET /prontidao/dependencias.",
            )

        registrada = idempotencia.buscar(idempotency_key, operacao_verificacao(nome_valido))
        aceito_em = aceito_em_de(registrada.corpo) if registrada is not None else datetime.now(UTC)

        return RespostaVerificacaoAceita(
            nome=estado.nome,
            estado=str(estado.estado),
            aceito_em=aceito_em,
        )

    return roteador
