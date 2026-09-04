"""Recurso REST/JSON de consulta das mensagens de uma execução (GERAR-11, GERAR-12).

Rota de leitura apenas: reidratar a página consulta este `GET` e reconstrói etapa e
progresso do que está persistido, sem reenviar geração nenhuma.

A resposta traz o estado de conteúdo, o canal, a tentativa, o limite de tentativas (3.4) e os
metadados da versão atual (veredito, motivo, modelo, prompt), não o texto gerado: exibir a
mensagem para decisão humana é a superfície de revisão da História 3.5, fora do escopo desta.
O limite vem do backend, e não de uma constante da interface, para que "tentativa 2 de 3"
nunca divirja da regra que o repositório realmente cobra (REGEN-11).
"""

from datetime import datetime
from uuid import UUID, uuid4

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from central_preventiva.adaptadores.persistencia.repositorio_execucao_preventiva import (
    RepositorioExecucaoPreventiva,
)
from central_preventiva.adaptadores.persistencia.repositorio_mensagens import (
    LIMITE_TENTATIVAS_MENSAGEM,
    RegistroMensagem,
    RepositorioMensagens,
    VersaoMensagem,
)
from central_preventiva.composicao.configuracao import Configuracao

TIPO_PROBLEMA = "application/problem+json"
CAMINHO_MENSAGENS = "/execucoes/{execucao_id}/mensagens"


class RespostaVersaoMensagem(BaseModel):
    """Metadados da versão atual de uma mensagem: veredito, motivo e proveniência."""

    model_config = ConfigDict(extra="forbid")

    numero_tentativa: int = Field(description="Número da tentativa de geração registrada.")
    valida: bool = Field(
        description="Se a validação determinística aprovou a saída desta tentativa."
    )
    motivo_invalidez: str | None = Field(
        description="Código estável do motivo da recusa, ou nulo quando a saída é válida."
    )
    modelo: str = Field(description="Modelo da OpenAI usado nesta tentativa de geração.")
    versao_prompt: str = Field(description="Versão do prompt usada nesta tentativa.")
    duracao_ms: float = Field(description="Duração da chamada de geração, em milissegundos.")
    tokens_entrada: int | None = Field(
        description="Tokens de entrada consumidos, ou nulo quando a chamada não os reportou."
    )
    tokens_saida: int | None = Field(
        description="Tokens de saída consumidos, ou nulo quando a chamada não os reportou."
    )
    criado_em: datetime = Field(description="Instante RFC 3339 em UTC do registro da versão.")


class RespostaMensagem(BaseModel):
    """Uma mensagem da execução: origem, canal, estado de conteúdo e versão atual."""

    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(description="Identificador da mensagem.")
    elegibilidade_id: UUID = Field(
        description="Item do público elegível que originou esta mensagem."
    )
    canal: str = Field(description="Canal da mensagem (`whatsapp`, `email` ou `sms`).")
    estado: str = Field(description="Estado de conteúdo da mensagem, conforme o AD-4.")
    tentativa_atual: int = Field(description="Tentativa de geração em curso ou concluída.")
    limite_tentativas: int = Field(
        description="Máximo de tentativas de conteúdo permitidas por mensagem."
    )
    versao: int = Field(description="Versão de concorrência otimista da mensagem.")
    versao_atual: RespostaVersaoMensagem | None = Field(
        description="Versão mais recente registrada, ou nula se nenhuma foi persistida ainda."
    )


class RespostaMensagens(BaseModel):
    """Mensagens já persistidas de uma execução, na ordem em que foram criadas."""

    model_config = ConfigDict(extra="forbid")

    execucao_id: UUID = Field(description="Identificador da execução consultada.")
    registros: list[RespostaMensagem] = Field(
        description="Mensagens da execução; lista vazia quando nenhuma foi criada ainda."
    )


class ProblemaMensagens(BaseModel):
    """Falha da consulta de mensagens, com ocorrência, impacto e próxima ação segura."""

    model_config = ConfigDict(extra="forbid")

    codigo: str = Field(description="Código estável que identifica o tipo da falha.")
    correlacao_id: str = Field(description="Identificador único desta ocorrência de falha.")
    ocorrencia: str = Field(description="O que aconteceu, em português brasileiro.")
    impacto: str = Field(description="Efeito prático da falha para quem consultou o recurso.")
    proxima_acao: str = Field(description="Próxima ação segura recomendada para contornar a falha.")


def problema(
    status: int, codigo: str, ocorrencia: str, impacto: str, proxima_acao: str
) -> JSONResponse:
    """Monta a resposta `problem+json` correlacionada de uma falha da consulta."""

    corpo = ProblemaMensagens(
        codigo=codigo,
        correlacao_id=str(uuid4()),
        ocorrencia=ocorrencia,
        impacto=impacto,
        proxima_acao=proxima_acao,
    )
    return JSONResponse(status_code=status, media_type=TIPO_PROBLEMA, content=corpo.model_dump())


def _resposta_versao(versao: VersaoMensagem | None) -> RespostaVersaoMensagem | None:
    """Traduz a versão atual persistida para o contrato público, ou devolve nulo."""

    if versao is None:
        return None
    return RespostaVersaoMensagem(
        numero_tentativa=versao.numero_tentativa,
        valida=versao.valida,
        motivo_invalidez=versao.motivo_invalidez,
        modelo=versao.modelo,
        versao_prompt=versao.versao_prompt,
        duracao_ms=versao.duracao_ms,
        tokens_entrada=versao.tokens_entrada,
        tokens_saida=versao.tokens_saida,
        criado_em=versao.criado_em,
    )


def _resposta_mensagem(
    registro: RegistroMensagem, versao: VersaoMensagem | None
) -> RespostaMensagem:
    """Traduz uma mensagem persistida e sua versão atual para o contrato público."""

    return RespostaMensagem(
        id=registro.id,
        elegibilidade_id=registro.elegibilidade_id,
        canal=str(registro.canal),
        estado=str(registro.estado),
        tentativa_atual=registro.tentativa_atual,
        limite_tentativas=LIMITE_TENTATIVAS_MENSAGEM,
        versao=registro.versao,
        versao_atual=_resposta_versao(versao),
    )


def criar_roteador(configuracao: Configuracao) -> APIRouter:
    """Compõe o recurso de consulta das mensagens geradas de uma execução."""

    roteador = APIRouter(tags=["Mensagens"])
    execucoes_repo = RepositorioExecucaoPreventiva(configuracao.caminho_banco)
    mensagens_repo = RepositorioMensagens(configuracao.caminho_banco)

    @roteador.get(
        CAMINHO_MENSAGENS,
        response_model=RespostaMensagens,
        status_code=200,
        summary="Consultar as mensagens geradas de uma execução",
        description=(
            "Devolve, para cada mensagem já criada na execução, o item do público elegível "
            "de origem, o canal, o estado de conteúdo, a tentativa e os metadados da versão "
            "atual. É uma consulta de leitura: reidratar a página reconstrói o progresso "
            "somente do que está persistido, sem reenviar nenhuma geração e sem duplicar "
            "mensagem. Uma execução sem mensagens devolve lista vazia."
        ),
        responses={
            200: {"description": "Mensagens encontradas (pode ser lista vazia)."},
            404: {"description": "Execução inexistente.", "model": ProblemaMensagens},
            422: {
                "description": "O identificador da execução não é um UUID válido.",
                "model": ProblemaMensagens,
            },
        },
    )
    async def consultar_mensagens(  # pyright: ignore[reportUnusedFunction]
        execucao_id: str,
    ) -> RespostaMensagens | JSONResponse:
        """Traduz `RepositorioMensagens.listar_por_execucao` para o contrato público."""

        try:
            execucao_uuid = UUID(execucao_id)
        except ValueError:
            return problema(
                422,
                "execucao_id_invalido",
                f"'{execucao_id}' não é um identificador de execução válido.",
                "Nenhuma mensagem pode ser exibida.",
                "Consulte a execução pelo identificador UUID retornado pela API.",
            )

        if execucoes_repo.buscar(execucao_uuid) is None:
            return problema(
                404,
                "execucao_inexistente",
                f"A execução '{execucao_id}' não existe.",
                "Nenhuma mensagem pode ser exibida.",
                "Consulte a execução pelo identificador UUID retornado pela API.",
            )

        return RespostaMensagens(
            execucao_id=execucao_uuid,
            registros=[
                _resposta_mensagem(
                    registro, mensagens_repo.obter_versao_atual(registro.id)
                )
                for registro in mensagens_repo.listar_por_execucao(execucao_uuid)
            ],
        )

    return roteador
