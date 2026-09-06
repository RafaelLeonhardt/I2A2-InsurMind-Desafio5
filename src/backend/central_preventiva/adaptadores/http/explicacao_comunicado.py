"""Recurso REST/JSON da explicação acessível de um comunicado (EXPLICACAO-01..05).

`GET /segurados/{segurado_id}/comunicados/{entrega_simulada_id}/explicacao` é uma leitura
pura sobre `ServicoExplicacaoComunicado` (T1): uma entrega inexistente e uma entrega cuja
mensagem pertence a outro segurado devolvem exatamente o mesmo `404` genérico, mesmo padrão
de não-enumeração de 4.2/4.3/5.2/5.3 (AD-011).
"""

from uuid import UUID, uuid4

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from central_preventiva.adaptadores.persistencia.repositorio_avaliacoes_criticas import (
    RepositorioAvaliacoesCriticas,
)
from central_preventiva.adaptadores.persistencia.repositorio_contextos_agente import (
    RepositorioContextosAgente,
)
from central_preventiva.adaptadores.persistencia.repositorio_decisoes_humanas import (
    DecisaoHumana,
    RepositorioDecisoesHumanas,
)
from central_preventiva.adaptadores.persistencia.repositorio_elegibilidade import (
    RepositorioElegibilidades,
)
from central_preventiva.adaptadores.persistencia.repositorio_entregas_simuladas import (
    ApresentacaoSimulada,
    RepositorioEntregasSimuladas,
)
from central_preventiva.adaptadores.persistencia.repositorio_execucao_preventiva import (
    RepositorioExcecoesOperacionais,
    RepositorioExecucaoPreventiva,
)
from central_preventiva.adaptadores.persistencia.repositorio_mensagens import (
    RepositorioMensagens,
)
from central_preventiva.adaptadores.persistencia.repositorio_meteorologia import (
    RepositorioEventosMeteorologicos,
)
from central_preventiva.aplicacao.detalhe_resultado import (
    PortasDetalheResultado,
    ServicoDetalheResultado,
)
from central_preventiva.aplicacao.explicacao_comunicado import (
    ExplicacaoComunicado,
    PortasExplicacaoComunicado,
    SecaoAgente,
    SecaoContexto,
    SecaoEvento,
    ServicoExplicacaoComunicado,
    TentativaExplicada,
)
from central_preventiva.composicao.configuracao import Configuracao
from central_preventiva.dominio.validador_saida_canal import LimitesCanal, ValidadorSaidaCanal

TIPO_PROBLEMA = "application/problem+json"
CAMINHO_EXPLICACAO = "/segurados/{segurado_id}/comunicados/{entrega_simulada_id}/explicacao"


class RespostaEventoDeterministico(BaseModel):
    """Evento meteorológico de origem, sempre rotulado como determinístico."""

    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(description="Identificador do evento meteorológico.")
    tipo: str = Field(description="Tipo do evento (`chuva_intensa` ou `granizo`).")
    area: str = Field(description="Código de área monitorada afetada pelo evento.")
    proveniencia: str = Field(description="Origem do evento (`real_inmet` ou `sintetico`).")


class RespostaSecaoEvento(BaseModel):
    """Evento e regra que originaram a mensagem — sempre `deterministica` (EXPLICACAO-01)."""

    model_config = ConfigDict(extra="forbid")

    origem: str = Field(description="Sempre `deterministica`: nunca produzido por IA.")
    evento: RespostaEventoDeterministico | None = Field(
        description="Evento de origem, ou nulo se não houver evento associado."
    )
    regra_id: UUID = Field(description="Regra preventiva aplicada ao público do lote.")
    regra_versao: int = Field(description="Versão da regra aplicada.")


class RespostaSecaoContexto(BaseModel):
    """Categorias de dado usadas e não usadas pelo agente redator (EXPLICACAO-03)."""

    model_config = ConfigDict(extra="forbid")

    categorias_usadas: list[str] = Field(description="Categorias de dado que chegaram à IA.")
    categorias_nao_usadas: list[str] = Field(
        description="Categorias deliberadamente deixadas de fora."
    )


class RespostaAvaliacaoCriticaExplicacao(BaseModel):
    """Avaliação crítica de uma tentativa de geração."""

    model_config = ConfigDict(extra="forbid")

    aprovada: bool = Field(description="Se o agente crítico aprovou esta tentativa.")
    motivos: list[str] = Field(description="Categorias dos motivos de reprovação, se houver.")
    agente: str = Field(description="Nome do agente que avaliou.")
    modelo: str = Field(description="Modelo da OpenAI usado na avaliação.")
    duracao_ms: float = Field(description="Duração da chamada de avaliação, em milissegundos.")


class RespostaDecisaoHumana(BaseModel):
    """Decisão humana registrada sobre uma tentativa."""

    model_config = ConfigDict(extra="forbid")

    resultado: str = Field(
        description="Resultado da decisão (`aprovar`, `rejeitar`, `excluir` ou `regenerar`)."
    )
    justificativa: str | None = Field(description="Justificativa da decisão, se houver.")


class RespostaTentativaExplicacao(BaseModel):
    """Uma tentativa de geração: redator, crítico e decisões humanas — sempre `agente`."""

    model_config = ConfigDict(extra="forbid")

    numero_tentativa: int = Field(description="Número da tentativa de geração.")
    origem_regeneracao: str = Field(
        description="Por que esta tentativa existe: `primeira_tentativa`, `automatica` "
        "(ciclo automático de crítica) ou `humana` (decisão humana de regenerar)."
    )
    corpo: str = Field(description="Corpo gerado nesta tentativa.")
    assunto: str | None = Field(description="Assunto gerado nesta tentativa, só em e-mail.")
    modelo_redator: str = Field(description="Modelo da OpenAI usado pelo agente redator.")
    avaliacao_critica: RespostaAvaliacaoCriticaExplicacao | None = Field(
        description="Avaliação do agente crítico, ou nula se ainda não avaliada."
    )
    decisoes_humanas: list[RespostaDecisaoHumana] = Field(
        description="Decisões humanas registradas sobre esta tentativa."
    )


class RespostaSecaoAgente(BaseModel):
    """Os papéis do agente redator e do agente crítico — sempre `agente` (EXPLICACAO-02)."""

    model_config = ConfigDict(extra="forbid")

    origem: str = Field(description="Sempre `agente`: nunca uma decisão determinística.")
    status: str = Field(
        description="`completa`, `parcial` (lacuna de dado) ou `excecao` (falha técnica)."
    )
    causa_excecao: str | None = Field(
        description="Causa sanitizada da exceção, presente só quando `status='excecao'`."
    )
    tentativas: list[RespostaTentativaExplicacao] = Field(
        description="Todas as tentativas de geração, da primeira à mais recente."
    )


class RespostaApresentacaoSimuladaExplicacao(BaseModel):
    """Prévia da mensagem final — cópia exata da versão aprovada e simulada."""

    model_config = ConfigDict(extra="forbid")

    canal: str = Field(description="Canal em que a apresentação seria feita.")
    assunto: str | None = Field(description="Assunto apresentado, só no canal de e-mail.")
    corpo: str = Field(description="Corpo apresentado, cópia exata do conteúdo aprovado.")
    rotulo: str = Field(description="Rótulo fixo da natureza da entrega: sempre 'simulada'.")


class RespostaExplicacaoComunicado(BaseModel):
    """Explicação completa de "Como esta mensagem foi criada" (EXPLICACAO-01..05)."""

    model_config = ConfigDict(extra="forbid")

    entrega_simulada_id: UUID = Field(description="Identificador do comunicado explicado.")
    mensagem_id: UUID = Field(description="Mensagem de origem do comunicado.")
    execucao_id: UUID = Field(description="Execução a que a mensagem pertence.")
    execucao_origem_id: UUID | None = Field(
        description="Presente só quando a execução é uma retentativa correlacionada."
    )
    evento_e_regra: RespostaSecaoEvento = Field(description="Seção determinística.")
    contexto: RespostaSecaoContexto | None = Field(
        description="Contexto minimizado, ou nulo se ainda não montado."
    )
    agente: RespostaSecaoAgente = Field(description="Seção agêntica.")
    apresentacao_simulada: RespostaApresentacaoSimuladaExplicacao | None = Field(
        description="Prévia da mensagem final simulada, ou nula se ainda não simulada."
    )


class ProblemaExplicacaoComunicado(BaseModel):
    """Falha da consulta de explicação, com ocorrência, impacto e próxima ação segura."""

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

    corpo = ProblemaExplicacaoComunicado(
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
        "O identificador do segurado ou da entrega simulada não é um UUID válido.",
        "Nenhuma explicação pode ser exibida.",
        "Consulte a explicação pelos identificadores UUID retornados pela API.",
    )


def _problema_nao_encontrada() -> JSONResponse:
    """Resposta idêntica para explicação inexistente e de outro segurado (AD-011)."""

    return _problema(
        404,
        "explicacao_nao_encontrada",
        "Este comunicado não existe ou não pertence a este segurado.",
        "Nenhuma explicação pode ser exibida.",
        "Consulte a explicação pelo identificador do comunicado retornado pela API.",
    )


def _resposta_decisao(decisao: DecisaoHumana) -> RespostaDecisaoHumana:
    """Traduz uma decisão humana persistida para o contrato público."""

    return RespostaDecisaoHumana(
        resultado=str(decisao.resultado), justificativa=decisao.justificativa
    )


def _resposta_tentativa(tentativa: TentativaExplicada) -> RespostaTentativaExplicacao:
    """Traduz uma tentativa explicada para o contrato público."""

    avaliacao = tentativa.avaliacao_critica
    return RespostaTentativaExplicacao(
        numero_tentativa=tentativa.numero_tentativa,
        origem_regeneracao=str(tentativa.origem_regeneracao),
        corpo=tentativa.corpo,
        assunto=tentativa.assunto,
        modelo_redator=tentativa.modelo_redator,
        avaliacao_critica=None
        if avaliacao is None
        else RespostaAvaliacaoCriticaExplicacao(
            aprovada=avaliacao.avaliacao.aprovada,
            motivos=[str(motivo.categoria) for motivo in avaliacao.avaliacao.motivos],
            agente=avaliacao.agente,
            modelo=avaliacao.modelo,
            duracao_ms=avaliacao.duracao_ms,
        ),
        decisoes_humanas=[_resposta_decisao(decisao) for decisao in tentativa.decisoes_humanas],
    )


def _resposta_secao_agente(secao: SecaoAgente) -> RespostaSecaoAgente:
    """Traduz a seção agêntica para o contrato público."""

    return RespostaSecaoAgente(
        origem=str(secao.origem),
        status=str(secao.status),
        causa_excecao=secao.causa_excecao,
        tentativas=[_resposta_tentativa(tentativa) for tentativa in secao.tentativas],
    )


def _resposta_secao_evento(secao: SecaoEvento) -> RespostaSecaoEvento:
    """Traduz a seção determinística para o contrato público."""

    evento = secao.evento
    return RespostaSecaoEvento(
        origem=str(secao.origem),
        evento=None
        if evento is None
        else RespostaEventoDeterministico(
            id=evento.id,
            tipo=str(evento.tipo),
            area=evento.area,
            proveniencia=str(evento.proveniencia),
        ),
        regra_id=secao.regra_id,
        regra_versao=secao.regra_versao,
    )


def _resposta_secao_contexto(secao: SecaoContexto | None) -> RespostaSecaoContexto | None:
    """Traduz o contexto minimizado para o contrato público."""

    if secao is None:
        return None
    return RespostaSecaoContexto(
        categorias_usadas=list(secao.categorias_usadas),
        categorias_nao_usadas=list(secao.categorias_nao_usadas),
    )


def _resposta_apresentacao(
    apresentacao: ApresentacaoSimulada | None,
) -> RespostaApresentacaoSimuladaExplicacao | None:
    """Traduz a prévia simulada para o contrato público."""

    if apresentacao is None:
        return None
    return RespostaApresentacaoSimuladaExplicacao(
        canal=str(apresentacao.canal),
        assunto=apresentacao.assunto,
        corpo=apresentacao.corpo,
        rotulo=apresentacao.rotulo,
    )


def _resposta_explicacao(explicacao: ExplicacaoComunicado) -> RespostaExplicacaoComunicado:
    """Traduz a explicação consolidada do caso de uso para o contrato público."""

    return RespostaExplicacaoComunicado(
        entrega_simulada_id=explicacao.entrega_simulada_id,
        mensagem_id=explicacao.mensagem_id,
        execucao_id=explicacao.execucao_id,
        execucao_origem_id=explicacao.execucao_origem_id,
        evento_e_regra=_resposta_secao_evento(explicacao.evento_e_regra),
        contexto=_resposta_secao_contexto(explicacao.contexto),
        agente=_resposta_secao_agente(explicacao.agente),
        apresentacao_simulada=_resposta_apresentacao(explicacao.apresentacao_simulada),
    )


def montar_servico_explicacao_comunicado(
    configuracao: Configuracao,
) -> ServicoExplicacaoComunicado:
    """Compõe o serviço de explicação sobre os repositórios reais do DuckDB local."""

    caminho = configuracao.caminho_banco
    validador = ValidadorSaidaCanal(
        LimitesCanal(
            whatsapp=configuracao.limite_caracteres_whatsapp,
            sms=configuracao.limite_caracteres_sms,
            assunto_email=configuracao.limite_caracteres_assunto_email,
            corpo_email=configuracao.limite_caracteres_corpo_email,
        )
    )
    detalhe = ServicoDetalheResultado(
        PortasDetalheResultado(
            mensagens=RepositorioMensagens(caminho),
            avaliacoes=RepositorioAvaliacoesCriticas(caminho),
            decisoes=RepositorioDecisoesHumanas(caminho),
            entregas=RepositorioEntregasSimuladas(caminho),
            elegibilidades=RepositorioElegibilidades(caminho),
            eventos=RepositorioEventosMeteorologicos(caminho),
            excecoes=RepositorioExcecoesOperacionais(caminho),
            validador=validador,
        )
    )
    return ServicoExplicacaoComunicado(
        PortasExplicacaoComunicado(
            entregas=RepositorioEntregasSimuladas(caminho),
            mensagens=RepositorioMensagens(caminho),
            elegibilidades=RepositorioElegibilidades(caminho),
            detalhe=detalhe,
            contextos=RepositorioContextosAgente(caminho),
            execucoes=RepositorioExecucaoPreventiva(caminho),
        )
    )


def criar_roteador(configuracao: Configuracao) -> APIRouter:
    """Compõe o recurso de explicação do comunicado do segurado ativo."""

    roteador = APIRouter(tags=["Explicação do comunicado"])
    servico = montar_servico_explicacao_comunicado(configuracao)

    @roteador.get(
        CAMINHO_EXPLICACAO,
        response_model=RespostaExplicacaoComunicado,
        status_code=200,
        summary="Consultar como um comunicado foi criado",
        description=(
            "Devolve evento/regra (determinístico), redator/crítico/decisões humanas "
            "(agente), categorias de contexto usadas/não usadas e a prévia da mensagem "
            "final, exatamente como simulada. Um comunicado inexistente e um de outro "
            "segurado devolvem exatamente a mesma resposta `404`."
        ),
        responses={
            200: {"description": "Explicação encontrada para este segurado."},
            404: {
                "description": "Comunicado inexistente ou de outro segurado.",
                "model": ProblemaExplicacaoComunicado,
            },
            422: {
                "description": "Algum identificador informado não é um UUID válido.",
                "model": ProblemaExplicacaoComunicado,
            },
        },
    )
    async def consultar_explicacao(  # pyright: ignore[reportUnusedFunction]
        segurado_id: str, entrega_simulada_id: str
    ) -> RespostaExplicacaoComunicado | JSONResponse:
        """Traduz `ServicoExplicacaoComunicado.obter` para o contrato REST/JSON público."""

        try:
            segurado_uuid = UUID(segurado_id)
            entrega_uuid = UUID(entrega_simulada_id)
        except ValueError:
            return _problema_identificador_invalido()

        explicacao = servico.obter(segurado_uuid, entrega_uuid)
        if explicacao is None:
            return _problema_nao_encontrada()
        return _resposta_explicacao(explicacao)

    return roteador
