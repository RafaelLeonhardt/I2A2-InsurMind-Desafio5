"""Recurso REST/JSON do detalhe de uma avaliação crítica (CRIT-08, CRIT-09).

Rota de leitura apenas: consultar o detalhe não reavalia nada nem chama a OpenAI.

A resposta separa explicitamente as duas origens da decisão sobre a mesma versão (CRIT-09):
a decisão agêntica do crítico (`origem = 'agente_ia'`, com os motivos categorizados, o agente,
o modelo e a duração) e a validação determinística de 3.2 (`origem = 'regras_deterministicas'`,
com o veredito estrutural e o motivo da recusa). A separação é um campo do contrato, não uma
convenção de exibição: a interface não tem como colapsar as duas em uma só.
"""

from datetime import datetime
from uuid import UUID, uuid4

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from central_preventiva.adaptadores.persistencia.repositorio_avaliacoes_criticas import (
    RegistroAvaliacaoCritica,
    RepositorioAvaliacoesCriticas,
)
from central_preventiva.adaptadores.persistencia.repositorio_mensagens import (
    RepositorioMensagens,
    VersaoMensagem,
)
from central_preventiva.composicao.configuracao import Configuracao
from central_preventiva.dominio.avaliacao_critica import CategoriaCritica

TIPO_PROBLEMA = "application/problem+json"
CAMINHO_AVALIACAO = "/mensagens/{mensagem_id}/versoes/{versao_id}/avaliacao-critica"

ORIGEM_AGENTICA = "agente_ia"
"""Marca a decisão tomada pelo agente crítico sobre o conteúdo (3.3)."""

ORIGEM_DETERMINISTICA = "regras_deterministicas"
"""Marca o veredito estrutural decidido por regra, fora do modelo (3.2)."""

CRITERIOS_AVALIADOS = tuple(categoria.value for categoria in CategoriaCritica)
"""Os sete critérios contra os quais toda avaliação é feita (CRIT-03, CRIT-08)."""


class RespostaMotivoCritica(BaseModel):
    """Um motivo da decisão do crítico: a categoria avaliada e a justificativa."""

    model_config = ConfigDict(extra="forbid")

    categoria: str = Field(description="Critério avaliado, entre os sete critérios fechados.")
    justificativa: str = Field(description="Por que este critério sustenta a decisão.")


class RespostaValidacaoDeterministica(BaseModel):
    """Veredito estrutural de 3.2 sobre a mesma versão, decidido fora do modelo."""

    model_config = ConfigDict(extra="forbid")

    origem: str = Field(
        description="Sempre 'regras_deterministicas': decidido por regra, nunca pelo modelo."
    )
    valida: bool = Field(
        description="Se campos obrigatórios e limite de canal foram atendidos (3.2)."
    )
    motivo_invalidez: str | None = Field(
        description="Código estável do motivo da recusa estrutural, ou nulo quando válida."
    )


class RespostaAvaliacaoCritica(BaseModel):
    """Detalhe de uma avaliação: versão, critérios, decisão, motivos e proveniência."""

    model_config = ConfigDict(extra="forbid")

    mensagem_id: UUID = Field(description="Mensagem a que a versão avaliada pertence.")
    versao_mensagem_id: UUID = Field(description="Versão de mensagem avaliada.")
    numero_tentativa: int = Field(description="Número da tentativa de geração avaliada.")
    origem: str = Field(
        description="Sempre 'agente_ia': esta decisão é do agente crítico, não de uma regra."
    )
    criterios: list[str] = Field(
        description="Os sete critérios contra os quais a mensagem foi avaliada."
    )
    aprovada: bool = Field(
        description="Decisão do crítico sobre o conteúdo; não substitui a validação de regra."
    )
    motivos: list[RespostaMotivoCritica] = Field(
        description="Motivos específicos da decisão; vazio quando o crítico aprovou."
    )
    agente: str = Field(description="Agente que produziu a avaliação.")
    modelo: str = Field(description="Modelo da OpenAI usado na avaliação.")
    duracao_ms: float = Field(description="Duração da chamada de avaliação, em milissegundos.")
    criado_em: datetime = Field(description="Instante RFC 3339 em UTC do registro da avaliação.")
    validacao_deterministica: RespostaValidacaoDeterministica = Field(
        description="Veredito estrutural de 3.2 sobre a mesma versão, mantido separado."
    )


class ProblemaAvaliacaoCritica(BaseModel):
    """Falha da consulta do detalhe, com ocorrência, impacto e próxima ação segura."""

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

    corpo = ProblemaAvaliacaoCritica(
        codigo=codigo,
        correlacao_id=str(uuid4()),
        ocorrencia=ocorrencia,
        impacto=impacto,
        proxima_acao=proxima_acao,
    )
    return JSONResponse(status_code=status, media_type=TIPO_PROBLEMA, content=corpo.model_dump())


def _resposta(
    mensagem_id: UUID, versao: VersaoMensagem, registro: RegistroAvaliacaoCritica
) -> RespostaAvaliacaoCritica:
    """Traduz a avaliação e a versão avaliada para o contrato público."""

    return RespostaAvaliacaoCritica(
        mensagem_id=mensagem_id,
        versao_mensagem_id=registro.versao_mensagem_id,
        numero_tentativa=versao.numero_tentativa,
        origem=ORIGEM_AGENTICA,
        criterios=list(CRITERIOS_AVALIADOS),
        aprovada=registro.avaliacao.aprovada,
        motivos=[
            RespostaMotivoCritica(
                categoria=motivo.categoria.value, justificativa=motivo.justificativa
            )
            for motivo in registro.avaliacao.motivos
        ],
        agente=registro.agente,
        modelo=registro.modelo,
        duracao_ms=registro.duracao_ms,
        criado_em=registro.criado_em,
        validacao_deterministica=RespostaValidacaoDeterministica(
            origem=ORIGEM_DETERMINISTICA,
            valida=versao.valida,
            motivo_invalidez=versao.motivo_invalidez,
        ),
    )


def criar_roteador(configuracao: Configuracao) -> APIRouter:
    """Compõe o recurso de consulta do detalhe de uma avaliação crítica."""

    roteador = APIRouter(tags=["Avaliação crítica"])
    mensagens_repo = RepositorioMensagens(configuracao.caminho_banco)
    avaliacoes_repo = RepositorioAvaliacoesCriticas(configuracao.caminho_banco)

    @roteador.get(
        CAMINHO_AVALIACAO,
        response_model=RespostaAvaliacaoCritica,
        status_code=200,
        summary="Consultar o detalhe da avaliação crítica de uma versão de mensagem",
        description=(
            "Devolve a versão avaliada, os sete critérios considerados, a decisão do agente "
            "crítico, os motivos categorizados, o agente, o modelo e a duração da avaliação. "
            "A decisão do agente ('agente_ia') vem separada da validação determinística de "
            "campos e limite de canal ('regras_deterministicas'), que é decidida por regra e "
            "nunca pelo modelo. É uma consulta de leitura: nada é reavaliado e nenhuma "
            "chamada à OpenAI é feita."
        ),
        responses={
            200: {"description": "Avaliação encontrada."},
            404: {
                "description": (
                    "Mensagem inexistente, versão inexistente ou versão ainda não avaliada."
                ),
                "model": ProblemaAvaliacaoCritica,
            },
            422: {
                "description": "Identificador de mensagem ou de versão inválido.",
                "model": ProblemaAvaliacaoCritica,
            },
        },
    )
    async def consultar_avaliacao(  # pyright: ignore[reportUnusedFunction]
        mensagem_id: str, versao_id: str
    ) -> RespostaAvaliacaoCritica | JSONResponse:
        """Traduz `RepositorioAvaliacoesCriticas.obter_por_versao` para o contrato público."""

        try:
            mensagem_uuid = UUID(mensagem_id)
            versao_uuid = UUID(versao_id)
        except ValueError:
            return problema(
                422,
                "identificador_invalido",
                "O identificador de mensagem ou de versão não é um UUID válido.",
                "Nenhum detalhe de avaliação pode ser exibido.",
                "Consulte a mensagem e a versão pelos identificadores UUID retornados pela API.",
            )

        if mensagens_repo.obter(mensagem_uuid) is None:
            return problema(
                404,
                "mensagem_inexistente",
                f"A mensagem '{mensagem_id}' não existe.",
                "Nenhum detalhe de avaliação pode ser exibido.",
                "Consulte a mensagem pelo identificador UUID retornado pela API.",
            )

        versao = mensagens_repo.obter_versao(mensagem_uuid, versao_uuid)
        if versao is None:
            return problema(
                404,
                "versao_inexistente",
                f"A versão '{versao_id}' não existe nesta mensagem.",
                "Nenhum detalhe de avaliação pode ser exibido.",
                "Consulte a versão pelo identificador UUID retornado pela API.",
            )

        registro = avaliacoes_repo.obter_por_versao(versao_uuid)
        if registro is None:
            return problema(
                404,
                "avaliacao_inexistente",
                f"A versão '{versao_id}' ainda não foi avaliada pelo agente crítico.",
                "Nenhum detalhe de avaliação pode ser exibido; a versão segue em avaliação.",
                "Acompanhe o progresso da execução e consulte de novo quando a versão "
                "tiver sido avaliada.",
            )

        return _resposta(mensagem_uuid, versao, registro)

    return roteador
