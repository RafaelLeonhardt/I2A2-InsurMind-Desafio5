"""Recurso REST/JSON da proveniência agêntica de uma mensagem (REGEN-07, REGEN-08).

Rota de leitura apenas: consultar a proveniência não gera, não reavalia e não chama a OpenAI.

A resposta é o histórico completo do ciclo, tentativa por tentativa: quem produziu (agente e
modelo), sob qual versão de prompt, que categorias de dado entraram no contexto, o que saiu,
como foi avaliado, quanto durou e quanto de uso a chamada consumiu. Nenhuma tentativa é
sobrescrita: a versão reprovada da tentativa 1 continua consultável depois da regeneração.

O que a resposta nunca contém (REGEN-08): chave de API, contato ou identificação direta do
segurado, e o texto do prompt. As categorias de entrada são nomes de categoria (o mesmo
contrato de minimização de 3.1), nunca o conteúdo do contexto; a saída exposta é o texto que
o próprio sistema produziu para o canal, exigido nominalmente pelo AC de proveniência.
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
from central_preventiva.adaptadores.persistencia.repositorio_contextos_agente import (
    RepositorioContextosAgente,
)
from central_preventiva.adaptadores.persistencia.repositorio_mensagens import (
    LIMITE_TENTATIVAS_MENSAGEM,
    RegistroMensagem,
    RepositorioMensagens,
    VersaoMensagem,
)
from central_preventiva.composicao.configuracao import Configuracao

TIPO_PROBLEMA = "application/problem+json"
CAMINHO_PROVENIENCIA = "/mensagens/{mensagem_id}/proveniencia"

AGENTE_REDATOR = "redator"
"""Agente que produz toda versão de mensagem.

`versoes_mensagem` (3.2) não tem coluna `agente` porque só existe um produtor de versão. O
nome entra aqui como constante do contrato, do mesmo jeito que `avaliacoes_criticas.agente`
já traz `'critico'` como padrão da própria tabela.
"""


class RespostaCategoriasEntrada(BaseModel):
    """Categorias de dado que entraram (e que ficaram de fora) do contexto do agente."""

    model_config = ConfigDict(extra="forbid")

    usadas: list[str] = Field(
        description="Categorias de dado que chegaram ao contexto mínimo do agente (3.1)."
    )
    nao_usadas: list[str] = Field(
        description="Categorias deliberadamente deixadas de fora do contexto."
    )


class RespostaSaidaGerada(BaseModel):
    """Conteúdo produzido em uma tentativa, nos campos do canal."""

    model_config = ConfigDict(extra="forbid")

    assunto: str | None = Field(
        description="Assunto gerado, presente só no canal e-mail; nulo nos demais."
    )
    corpo: str = Field(description="Corpo gerado nesta tentativa.")


class RespostaMotivoProveniencia(BaseModel):
    """Um motivo da avaliação: a categoria fechada e a justificativa dela."""

    model_config = ConfigDict(extra="forbid")

    categoria: str = Field(description="Critério avaliado, entre os sete critérios fechados.")
    justificativa: str = Field(description="Por que este critério sustenta a decisão.")


class RespostaAvaliacaoDaTentativa(BaseModel):
    """Avaliação crítica da versão produzida nesta tentativa, com sua proveniência."""

    model_config = ConfigDict(extra="forbid")

    agente: str = Field(description="Agente que avaliou o conteúdo desta tentativa.")
    modelo: str = Field(description="Modelo da OpenAI usado na avaliação.")
    aprovada: bool = Field(description="Decisão do crítico sobre o conteúdo desta tentativa.")
    motivos: list[RespostaMotivoProveniencia] = Field(
        description="Motivos categorizados da decisão; vazio quando o crítico aprovou."
    )
    duracao_ms: float = Field(description="Duração da chamada de avaliação, em milissegundos.")
    criado_em: datetime = Field(description="Instante RFC 3339 em UTC do registro da avaliação.")


class RespostaTentativaProveniencia(BaseModel):
    """Proveniência completa de uma tentativa: geração e, quando houve, avaliação."""

    model_config = ConfigDict(extra="forbid")

    numero_tentativa: int = Field(description="Número da tentativa, de 1 até o limite.")
    agente: str = Field(description="Agente que gerou o conteúdo desta tentativa.")
    modelo: str = Field(description="Modelo da OpenAI usado nesta tentativa de geração.")
    versao_prompt: str = Field(description="Versão do prompt usada nesta tentativa.")
    saida: RespostaSaidaGerada = Field(description="Conteúdo produzido nesta tentativa.")
    valida: bool = Field(
        description="Se a validação determinística aprovou a saída desta tentativa."
    )
    motivo_invalidez: str | None = Field(
        description="Código estável do motivo da recusa estrutural, ou nulo quando válida."
    )
    duracao_ms: float = Field(description="Duração da chamada de geração, em milissegundos.")
    tokens_entrada: int | None = Field(
        description="Tokens de entrada consumidos, ou nulo quando a chamada não os reportou."
    )
    tokens_saida: int | None = Field(
        description="Tokens de saída consumidos, ou nulo quando a chamada não os reportou."
    )
    criado_em: datetime = Field(description="Instante RFC 3339 em UTC do registro da versão.")
    avaliacao: RespostaAvaliacaoDaTentativa | None = Field(
        description="Avaliação crítica desta tentativa, ou nula se ela ainda não foi avaliada."
    )


class RespostaProvenienciaMensagem(BaseModel):
    """Proveniência agêntica completa de uma mensagem, tentativa por tentativa."""

    model_config = ConfigDict(extra="forbid")

    mensagem_id: UUID = Field(description="Identificador da mensagem consultada.")
    execucao_id: UUID = Field(description="Execução preventiva que originou a mensagem.")
    elegibilidade_id: UUID = Field(
        description="Item do público elegível que originou a mensagem."
    )
    canal: str = Field(description="Canal da mensagem (`whatsapp`, `email` ou `sms`).")
    estado: str = Field(description="Estado de conteúdo da mensagem, conforme o AD-4.")
    tentativa_atual: int = Field(description="Tentativa de geração em curso ou concluída.")
    limite_tentativas: int = Field(
        description="Máximo de tentativas de conteúdo permitidas por mensagem."
    )
    categorias_entrada: RespostaCategoriasEntrada = Field(
        description="Categorias de dado usadas e não usadas no contexto do agente."
    )
    tentativas: list[RespostaTentativaProveniencia] = Field(
        description="Histórico imutável das tentativas, da primeira à mais recente."
    )


class ProblemaProveniencia(BaseModel):
    """Falha da consulta de proveniência, com ocorrência, impacto e próxima ação segura."""

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

    corpo = ProblemaProveniencia(
        codigo=codigo,
        correlacao_id=str(uuid4()),
        ocorrencia=ocorrencia,
        impacto=impacto,
        proxima_acao=proxima_acao,
    )
    return JSONResponse(status_code=status, media_type=TIPO_PROBLEMA, content=corpo.model_dump())


def _resposta_avaliacao(
    registro: RegistroAvaliacaoCritica | None,
) -> RespostaAvaliacaoDaTentativa | None:
    """Traduz a avaliação persistida da tentativa, ou devolve nulo se não houver."""

    if registro is None:
        return None
    return RespostaAvaliacaoDaTentativa(
        agente=registro.agente,
        modelo=registro.modelo,
        aprovada=registro.avaliacao.aprovada,
        motivos=[
            RespostaMotivoProveniencia(
                categoria=motivo.categoria.value, justificativa=motivo.justificativa
            )
            for motivo in registro.avaliacao.motivos
        ],
        duracao_ms=registro.duracao_ms,
        criado_em=registro.criado_em,
    )


def _resposta_tentativa(
    versao: VersaoMensagem, avaliacao: RegistroAvaliacaoCritica | None
) -> RespostaTentativaProveniencia:
    """Traduz uma tentativa persistida para o contrato público."""

    return RespostaTentativaProveniencia(
        numero_tentativa=versao.numero_tentativa,
        agente=AGENTE_REDATOR,
        modelo=versao.modelo,
        versao_prompt=versao.versao_prompt,
        saida=RespostaSaidaGerada(
            assunto=versao.conteudo.assunto, corpo=versao.conteudo.corpo
        ),
        valida=versao.valida,
        motivo_invalidez=versao.motivo_invalidez,
        duracao_ms=versao.duracao_ms,
        tokens_entrada=versao.tokens_entrada,
        tokens_saida=versao.tokens_saida,
        criado_em=versao.criado_em,
        avaliacao=_resposta_avaliacao(avaliacao),
    )


def criar_roteador(configuracao: Configuracao) -> APIRouter:
    """Compõe o recurso de consulta da proveniência agêntica de uma mensagem."""

    roteador = APIRouter(tags=["Proveniência"])
    mensagens_repo = RepositorioMensagens(configuracao.caminho_banco)
    avaliacoes_repo = RepositorioAvaliacoesCriticas(configuracao.caminho_banco)
    contextos_repo = RepositorioContextosAgente(configuracao.caminho_banco)

    def _categorias(registro: RegistroMensagem) -> RespostaCategoriasEntrada:
        """Lê as categorias de entrada do contexto montado para o item (3.1)."""

        contexto = contextos_repo.obter_por_elegibilidade(registro.elegibilidade_id)
        if contexto is None:
            return RespostaCategoriasEntrada(usadas=[], nao_usadas=[])
        return RespostaCategoriasEntrada(
            usadas=list(contexto.categorias_usadas),
            nao_usadas=list(contexto.categorias_nao_usadas),
        )

    @roteador.get(
        CAMINHO_PROVENIENCIA,
        response_model=RespostaProvenienciaMensagem,
        status_code=200,
        summary="Consultar a proveniência agêntica de uma mensagem",
        description=(
            "Devolve o histórico completo do ciclo de uma mensagem, tentativa por tentativa: "
            "agente, modelo, versão do prompt, categorias de dado usadas e não usadas no "
            "contexto, conteúdo produzido, veredito da validação determinística, avaliação do "
            "agente crítico, duração e métricas de uso. Uma tentativa reprovada continua "
            "consultável depois da regeneração: nada é sobrescrito. É uma consulta de leitura: "
            "nada é gerado nem reavaliado e nenhuma chamada à OpenAI é feita. A resposta nunca "
            "expõe chave, contato, identificação direta do segurado ou texto de prompt."
        ),
        responses={
            200: {"description": "Proveniência encontrada (pode ter zero tentativas)."},
            404: {"description": "Mensagem inexistente.", "model": ProblemaProveniencia},
            422: {
                "description": "O identificador da mensagem não é um UUID válido.",
                "model": ProblemaProveniencia,
            },
        },
    )
    async def consultar_proveniencia(  # pyright: ignore[reportUnusedFunction]
        mensagem_id: str,
    ) -> RespostaProvenienciaMensagem | JSONResponse:
        """Reúne versões, avaliações e categorias de entrada no contrato público."""

        try:
            mensagem_uuid = UUID(mensagem_id)
        except ValueError:
            return problema(
                422,
                "mensagem_id_invalido",
                f"'{mensagem_id}' não é um identificador de mensagem válido.",
                "Nenhuma proveniência pode ser exibida.",
                "Consulte a mensagem pelo identificador UUID retornado pela API.",
            )

        registro = mensagens_repo.obter(mensagem_uuid)
        if registro is None:
            return problema(
                404,
                "mensagem_inexistente",
                f"A mensagem '{mensagem_id}' não existe.",
                "Nenhuma proveniência pode ser exibida.",
                "Consulte a mensagem pelo identificador UUID retornado pela API.",
            )

        return RespostaProvenienciaMensagem(
            mensagem_id=registro.id,
            execucao_id=registro.execucao_id,
            elegibilidade_id=registro.elegibilidade_id,
            canal=str(registro.canal),
            estado=str(registro.estado),
            tentativa_atual=registro.tentativa_atual,
            limite_tentativas=LIMITE_TENTATIVAS_MENSAGEM,
            categorias_entrada=_categorias(registro),
            tentativas=[
                _resposta_tentativa(versao, avaliacoes_repo.obter_por_versao(versao.id))
                for versao in mensagens_repo.listar_versoes(mensagem_uuid)
            ],
        )

    return roteador
