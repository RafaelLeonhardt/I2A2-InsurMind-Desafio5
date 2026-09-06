"""Recurso REST/JSON de atualização de preferências do segurado ativo (PREFS-01..07, 5.6).

`PUT /segurados/{segurado_id}/preferencias` é a única mutação legítima do perfil Segurado
no MVP: canal preferencial e participação em alertas, sob concorrência otimista
(`versao_esperada`) e idempotência (`Idempotency-Key`, AD-002) — mesmo padrão de
`POST /regras/{regra_id}/ativar` (2.4).

SPEC_DEVIATION (T4): `design.md`/`tasks.md` só descrevem o `PUT`. `GET` foi acrescentado
neste mesmo roteador porque a superfície de Meus Dados (T5) precisa do `versao` corrente
para compor `versao_esperada` antes da primeira edição — nenhum outro endpoint expõe isso.
Reusa `RepositorioSegurados.buscar_preferencias_por_id` (5.3) sem alterar o endpoint de
apólice já verificado.
"""

from hashlib import sha256
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from central_preventiva.adaptadores.persistencia.repositorio_idempotencia import (
    RepositorioIdempotencia,
)
from central_preventiva.adaptadores.persistencia.repositorio_segurados import (
    ConflitoVersao,
    RepositorioSegurados,
)
from central_preventiva.aplicacao.portas_persistencia import ConflitoIdempotencia
from central_preventiva.aplicacao.preferencias_segurado import (
    PortasPreferenciasSegurado,
    PreferenciasAtualizadas,
    ServicoPreferenciasSegurado,
)
from central_preventiva.composicao.configuracao import Configuracao
from central_preventiva.dominio.validador_saida_canal import Canal

TIPO_PROBLEMA = "application/problem+json"
CAMINHO_PREFERENCIAS = "/segurados/{segurado_id}/preferencias"


class SolicitacaoPreferencias(BaseModel):
    """Canal preferencial, participação em alertas e versão esperada para concorrência
    otimista."""

    model_config = ConfigDict(extra="forbid")

    canal_preferido: str = Field(description="Canal de comunicação (`whatsapp`, `email` ou `sms`).")
    participa_de_alertas: bool = Field(description="Se o segurado participa de alertas.")
    versao_esperada: int = Field(
        description="Versão atual esperada do segurado (concorrência otimista, PREFS-02)."
    )


class RespostaPreferencias(BaseModel):
    """As preferências do segurado após a atualização (fresca ou repetida por
    idempotência)."""

    model_config = ConfigDict(extra="forbid")

    segurado_id: UUID = Field(description="Identificador do segurado.")
    canal_preferido: str = Field(description="Canal de comunicação preferencial.")
    participa_de_alertas: bool = Field(description="Se o segurado participa de alertas.")
    versao: int = Field(description="Nova versão do segurado após a atualização.")


class ErroPreferenciasSegurado(BaseModel):
    """Falha de uma atualização de preferências, com ocorrência, impacto e próxima ação
    segura."""

    model_config = ConfigDict(extra="forbid")

    codigo: str = Field(description="Código estável que identifica o tipo da falha.")
    correlacao_id: str = Field(description="Identificador único desta ocorrência de falha.")
    ocorrencia: str = Field(description="O que aconteceu, em português brasileiro.")
    impacto: str = Field(description="Efeito prático da falha para quem chamou o recurso.")
    proxima_acao: str = Field(description="Próxima ação segura recomendada para contornar a falha.")


def _problema(
    status: int, codigo: str, ocorrencia: str, impacto: str, proxima_acao: str
) -> JSONResponse:
    """Monta a resposta `problem+json` correlacionada de uma falha de preferências."""

    corpo = ErroPreferenciasSegurado(
        codigo=codigo,
        correlacao_id=str(uuid4()),
        ocorrencia=ocorrencia,
        impacto=impacto,
        proxima_acao=proxima_acao,
    )
    return JSONResponse(status_code=status, media_type=TIPO_PROBLEMA, content=corpo.model_dump())


def _resposta_atualizadas(atualizadas: PreferenciasAtualizadas) -> RespostaPreferencias:
    """Traduz `PreferenciasAtualizadas` (fresca ou repetida por idempotência) para o
    contrato público."""

    return RespostaPreferencias(
        segurado_id=atualizadas.segurado_id,
        canal_preferido=atualizadas.canal_preferido,
        participa_de_alertas=atualizadas.participa_de_alertas,
        versao=atualizadas.versao,
    )


def montar_portas_preferencias_segurado(
    configuracao: Configuracao,
) -> PortasPreferenciasSegurado:
    """Compõe as portas reais das preferências do segurado, reusadas pelo roteador."""

    return PortasPreferenciasSegurado(
        segurados=RepositorioSegurados(configuracao.caminho_banco),
        idempotencia=RepositorioIdempotencia(configuracao.caminho_banco),
    )


def criar_roteador(configuracao: Configuracao) -> APIRouter:
    """Compõe o recurso de atualização de preferências do segurado ativo."""

    roteador = APIRouter(tags=["Preferências do segurado"])
    segurados_repo = RepositorioSegurados(configuracao.caminho_banco)
    servico = ServicoPreferenciasSegurado(montar_portas_preferencias_segurado(configuracao))

    @roteador.get(
        CAMINHO_PREFERENCIAS,
        response_model=RespostaPreferencias,
        status_code=200,
        summary="Consultar canal preferencial e participação em alertas",
        description=(
            "Devolve o canal preferencial, a participação em alertas e a versão "
            "corrente do segurado ativo, para exibição e para compor `versao_esperada` "
            "de uma atualização subsequente (PREFS-01)."
        ),
        responses={
            200: {"description": "Preferências do segurado encontradas."},
            404: {"description": "Segurado não encontrado.", "model": ErroPreferenciasSegurado},
            422: {
                "description": "O identificador do segurado não é um UUID válido.",
                "model": ErroPreferenciasSegurado,
            },
        },
    )
    async def consultar_preferencias(  # pyright: ignore[reportUnusedFunction]
        segurado_id: str,
    ) -> RespostaPreferencias | JSONResponse:
        """Traduz `RepositorioSegurados.buscar_preferencias_por_id` para o contrato público."""

        try:
            segurado_uuid = UUID(segurado_id)
        except ValueError:
            return _problema(
                422,
                "segurado_id_invalido",
                f"'{segurado_id}' não é um identificador de segurado válido.",
                "Nenhuma preferência pode ser exibida.",
                "Consulte o segurado pelo identificador UUID retornado pela API.",
            )

        preferencias = segurados_repo.buscar_preferencias_por_id(segurado_uuid)
        if preferencias is None:
            return _problema(
                404,
                "segurado_inexistente",
                f"O segurado '{segurado_id}' não existe.",
                "Nenhuma preferência pode ser exibida.",
                "Consulte o segurado ativo pelo identificador válido.",
            )

        return RespostaPreferencias(
            segurado_id=segurado_uuid,
            canal_preferido=preferencias.canal_preferido,
            participa_de_alertas=preferencias.participa_de_alertas,
            versao=preferencias.versao,
        )

    @roteador.put(
        CAMINHO_PREFERENCIAS,
        response_model=RespostaPreferencias,
        status_code=200,
        summary="Atualizar canal preferencial e participação em alertas",
        description=(
            "Atualiza o canal preferencial e a participação em alertas do segurado "
            "ativo, de forma idempotente e sob concorrência otimista. Exige o cabeçalho "
            "`Idempotency-Key` em toda requisição."
        ),
        responses={
            200: {"description": "Preferências atualizadas, ou resposta idempotente repetida."},
            404: {"description": "Segurado não encontrado.", "model": ErroPreferenciasSegurado},
            409: {
                "description": "Conflito de versão ou de idempotência.",
                "model": ErroPreferenciasSegurado,
            },
            422: {
                "description": (
                    "Identificador inválido, canal inválido ou cabeçalho `Idempotency-Key` ausente."
                ),
                "model": ErroPreferenciasSegurado,
            },
        },
    )
    async def atualizar_preferencias(  # pyright: ignore[reportUnusedFunction]
        segurado_id: str,
        corpo: SolicitacaoPreferencias,
        requisicao: Request,
        idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    ) -> RespostaPreferencias | JSONResponse:
        """Traduz `ServicoPreferenciasSegurado.atualizar` para o contrato público."""

        try:
            segurado_uuid = UUID(segurado_id)
        except ValueError:
            return _problema(
                422,
                "segurado_id_invalido",
                f"'{segurado_id}' não é um identificador de segurado válido.",
                "Nenhuma preferência foi atualizada.",
                "Consulte o segurado pelo identificador UUID retornado pela API.",
            )

        try:
            canal = Canal(corpo.canal_preferido)
        except ValueError:
            return _problema(
                422,
                "canal_preferido_invalido",
                f"'{corpo.canal_preferido}' não é um canal preferencial válido.",
                "Nenhuma preferência foi atualizada.",
                "Escolha um canal entre whatsapp, email ou sms.",
            )

        if idempotency_key is None or not idempotency_key.strip():
            return _problema(
                422,
                "idempotency_key_ausente",
                "A requisição de atualização não informou o cabeçalho Idempotency-Key.",
                "Nenhuma preferência foi atualizada.",
                "Repita a requisição incluindo um cabeçalho Idempotency-Key único.",
            )

        if segurados_repo.buscar_por_id(segurado_uuid) is None:
            return _problema(
                404,
                "segurado_inexistente",
                f"O segurado '{segurado_id}' não existe.",
                "Nenhuma preferência foi atualizada.",
                "Consulte o segurado ativo pelo identificador válido.",
            )

        hash_requisicao = sha256(await requisicao.body()).hexdigest()

        try:
            atualizadas = servico.atualizar(
                segurado_uuid,
                corpo.versao_esperada,
                canal,
                corpo.participa_de_alertas,
                idempotency_key,
                hash_requisicao,
            )
        except ConflitoVersao:
            return _problema(
                409,
                "conflito_versao",
                "A versão esperada não corresponde à versão corrente do segurado.",
                "Nenhuma preferência foi atualizada.",
                "Recarregue as preferências atuais e tente salvar de novo com a versão correta.",
            )
        except ConflitoIdempotencia:
            return _problema(
                409,
                "conflito_idempotencia",
                "A chave de idempotência já foi usada com outro conteúdo de requisição.",
                "Nenhuma nova preferência foi aplicada.",
                "Gere uma nova Idempotency-Key para salvar outra alteração.",
            )

        return _resposta_atualizadas(atualizadas)

    return roteador
