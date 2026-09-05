"""Recurso REST/JSON do detalhe individual de um resultado de simulação (DETALHE-01..05).

`GET /execucoes/{execucao_id}/mensagens/{mensagem_id}/detalhe` é uma leitura pura sobre
`ServicoDetalheResultado` (T1): uma mensagem que não existe e uma mensagem que existe mas
pertence a outra execução devolvem exatamente o mesmo `404` `application/problem+json`
genérico — nenhuma diferença de resposta que revele a existência cruzada de um registro
(DETALHE-05, AD-011).
"""

from datetime import datetime
from uuid import UUID, uuid4

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from central_preventiva.adaptadores.persistencia.repositorio_avaliacoes_criticas import (
    RepositorioAvaliacoesCriticas,
)
from central_preventiva.adaptadores.persistencia.repositorio_decisoes_humanas import (
    RepositorioDecisoesHumanas,
)
from central_preventiva.adaptadores.persistencia.repositorio_elegibilidade import (
    RepositorioElegibilidades,
)
from central_preventiva.adaptadores.persistencia.repositorio_entregas_simuladas import (
    RepositorioEntregasSimuladas,
)
from central_preventiva.adaptadores.persistencia.repositorio_execucao_preventiva import (
    RepositorioExcecoesOperacionais,
)
from central_preventiva.adaptadores.persistencia.repositorio_mensagens import (
    RepositorioMensagens,
    VersaoMensagem,
)
from central_preventiva.adaptadores.persistencia.repositorio_meteorologia import (
    RepositorioEventosMeteorologicos,
)
from central_preventiva.aplicacao.detalhe_resultado import (
    DetalheResultado,
    PortasDetalheResultado,
    ServicoDetalheResultado,
    VersaoDetalhada,
)
from central_preventiva.composicao.configuracao import Configuracao
from central_preventiva.dominio.validador_saida_canal import LimitesCanal, ValidadorSaidaCanal

TIPO_PROBLEMA = "application/problem+json"
CAMINHO_DETALHE = "/execucoes/{execucao_id}/mensagens/{mensagem_id}/detalhe"


class RespostaEventoDetalhe(BaseModel):
    """Evento meteorológico que originou a mensagem detalhada."""

    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(description="Identificador do evento meteorológico.")
    tipo: str = Field(description="Tipo do evento (`chuva_intensa` ou `granizo`).")
    area: str = Field(description="Código de área monitorada afetada pelo evento.")
    intensidade: float = Field(description="Intensidade observada do evento.")
    proveniencia: str = Field(description="Origem do evento (`real_inmet` ou `sintetico`).")
    periodo_inicio: datetime = Field(description="Início do período observado, em UTC.")
    periodo_fim: datetime = Field(description="Fim do período observado, em UTC.")


class RespostaApresentacaoSimulada(BaseModel):
    """Como o conteúdo aprovado apareceria no canal, sempre rotulado como simulado."""

    model_config = ConfigDict(extra="forbid")

    canal: str = Field(description="Canal em que a apresentação seria feita.")
    assunto: str | None = Field(description="Assunto apresentado, só no canal de e-mail.")
    corpo: str = Field(description="Corpo apresentado, cópia exata do conteúdo aprovado.")
    rotulo: str = Field(description="Rótulo fixo da natureza da entrega: sempre 'simulada'.")


class RespostaAvaliacaoCriticaDetalhe(BaseModel):
    """Avaliação crítica de uma versão da mensagem."""

    model_config = ConfigDict(extra="forbid")

    aprovada: bool = Field(description="Se o agente crítico aprovou esta versão.")
    motivos: list[str] = Field(description="Categorias dos motivos de reprovação, se houver.")
    agente: str = Field(description="Nome do agente que avaliou.")
    modelo: str = Field(description="Modelo da OpenAI usado na avaliação.")
    duracao_ms: float = Field(description="Duração da chamada de avaliação, em milissegundos.")
    criado_em: datetime = Field(description="Instante RFC 3339 em UTC do registro.")


class RespostaDecisaoHumanaDetalhe(BaseModel):
    """Decisão humana registrada sobre uma versão da mensagem."""

    model_config = ConfigDict(extra="forbid")

    perfil_responsavel: str = Field(description="Perfil de quem decidiu.")
    resultado: str = Field(
        description="Resultado da decisão (`aprovar`, `rejeitar`, `excluir` ou `regenerar`)."
    )
    justificativa: str | None = Field(
        description="Justificativa da decisão, obrigatória fora de 'aprovar'."
    )
    criado_em: datetime = Field(description="Instante RFC 3339 em UTC da decisão.")


class RespostaVersaoDetalhe(BaseModel):
    """Uma tentativa de geração relacionada à sua avaliação crítica e decisões humanas."""

    model_config = ConfigDict(extra="forbid")

    numero_tentativa: int = Field(description="Número da tentativa de geração.")
    valida: bool = Field(description="Se a validação determinística aprovou a saída.")
    motivo_invalidez: str | None = Field(description="Motivo estável da recusa, se houver.")
    assunto: str | None = Field(description="Assunto gerado nesta tentativa, só em e-mail.")
    corpo: str = Field(description="Corpo gerado nesta tentativa.")
    modelo: str = Field(description="Modelo da OpenAI usado na geração.")
    criado_em: datetime = Field(description="Instante RFC 3339 em UTC do registro da versão.")
    avaliacao_critica: RespostaAvaliacaoCriticaDetalhe | None = Field(
        description="Avaliação crítica desta versão, ou nula se ainda não avaliada."
    )
    decisoes_humanas: list[RespostaDecisaoHumanaDetalhe] = Field(
        description="Decisões humanas registradas sobre esta versão específica."
    )


class RespostaExcecaoDetalhe(BaseModel):
    """Exceção operacional associada à mensagem, quando ela falhou tecnicamente."""

    model_config = ConfigDict(extra="forbid")

    causa: str = Field(description="Código estável e sanitizado da causa da falha.")
    tentativas: int = Field(description="Tentativas realizadas antes de esgotar o limite.")
    impacto: str = Field(description="Efeito prático da falha, em português brasileiro.")
    criado_em: datetime = Field(description="Instante RFC 3339 em UTC do registro.")


class RespostaDetalheResultado(BaseModel):
    """Detalhe completo do resultado individual de uma mensagem simulada (DETALHE-01)."""

    model_config = ConfigDict(extra="forbid")

    mensagem_id: UUID = Field(description="Identificador da mensagem detalhada.")
    execucao_id: UUID = Field(description="Execução a que a mensagem pertence.")
    canal: str = Field(description="Canal da mensagem (`whatsapp`, `email` ou `sms`).")
    estado: str = Field(description="Estado de conteúdo atual da mensagem.")
    limite_canal_corpo: int = Field(description="Limite de caracteres do corpo do canal.")
    limite_canal_assunto: int | None = Field(
        description="Limite de caracteres do assunto, só no canal de e-mail."
    )
    criado_em: datetime = Field(description="Instante RFC 3339 em UTC de criação.")
    atualizado_em: datetime = Field(description="Instante RFC 3339 em UTC da última mudança.")
    nome_segurado: str = Field(description="Segurado sintético destinatário.")
    apolice_id: UUID = Field(description="Apólice sintética de referência.")
    codigo_ibge_area: str = Field(description="Área monitorada do segurado, no momento.")
    evento: RespostaEventoDetalhe | None = Field(description="Evento de origem da mensagem.")
    regra_id: UUID = Field(description="Regra preventiva aplicada ao público do lote.")
    regra_versao: int = Field(description="Versão da regra aplicada.")
    apresentacao_simulada: RespostaApresentacaoSimulada | None = Field(
        description="Apresentação simulada já registrada, ou nula se ainda não simulada."
    )
    versoes: list[RespostaVersaoDetalhe] = Field(
        description="Todas as tentativas de geração, da primeira à mais recente."
    )
    excecao: RespostaExcecaoDetalhe | None = Field(
        description="Exceção técnica associada, presente só quando a mensagem falhou."
    )


class ProblemaDetalheResultado(BaseModel):
    """Falha da consulta de detalhe, com ocorrência, impacto e próxima ação segura."""

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

    corpo = ProblemaDetalheResultado(
        codigo=codigo,
        correlacao_id=str(uuid4()),
        ocorrencia=ocorrencia,
        impacto=impacto,
        proxima_acao=proxima_acao,
    )
    return JSONResponse(status_code=status, media_type=TIPO_PROBLEMA, content=corpo.model_dump())


def _problema_nao_encontrado(execucao_id: str, mensagem_id: str) -> JSONResponse:
    """Resposta idêntica para mensagem inexistente e mensagem de outra execução (AD-011)."""

    return problema(
        404,
        "mensagem_nao_encontrada",
        f"A mensagem '{mensagem_id}' não existe na execução '{execucao_id}'.",
        "Nenhum detalhe pode ser exibido.",
        "Consulte a mensagem pelo identificador retornado pela API de resultados.",
    )


def _resposta_versao(versao_detalhada: VersaoDetalhada) -> RespostaVersaoDetalhe:
    """Traduz uma versão detalhada persistida para o contrato público."""

    versao: VersaoMensagem = versao_detalhada.versao
    avaliacao = versao_detalhada.avaliacao_critica
    return RespostaVersaoDetalhe(
        numero_tentativa=versao.numero_tentativa,
        valida=versao.valida,
        motivo_invalidez=versao.motivo_invalidez,
        assunto=versao.conteudo.assunto,
        corpo=versao.conteudo.corpo,
        modelo=versao.modelo,
        criado_em=versao.criado_em,
        avaliacao_critica=None
        if avaliacao is None
        else RespostaAvaliacaoCriticaDetalhe(
            aprovada=avaliacao.avaliacao.aprovada,
            motivos=[str(motivo.categoria) for motivo in avaliacao.avaliacao.motivos],
            agente=avaliacao.agente,
            modelo=avaliacao.modelo,
            duracao_ms=avaliacao.duracao_ms,
            criado_em=avaliacao.criado_em,
        ),
        decisoes_humanas=[
            RespostaDecisaoHumanaDetalhe(
                perfil_responsavel=decisao.perfil_responsavel,
                resultado=str(decisao.resultado),
                justificativa=decisao.justificativa,
                criado_em=decisao.criado_em,
            )
            for decisao in versao_detalhada.decisoes_humanas
        ],
    )


def _resposta_detalhe(detalhe: DetalheResultado) -> RespostaDetalheResultado:
    """Traduz o detalhe consolidado do caso de uso para o contrato público."""

    evento = detalhe.evento
    apresentacao = detalhe.apresentacao_simulada
    excecao = detalhe.excecao
    return RespostaDetalheResultado(
        mensagem_id=detalhe.mensagem_id,
        execucao_id=detalhe.execucao_id,
        canal=str(detalhe.canal),
        estado=str(detalhe.estado),
        limite_canal_corpo=detalhe.limite_canal_corpo,
        limite_canal_assunto=detalhe.limite_canal_assunto,
        criado_em=detalhe.criado_em,
        atualizado_em=detalhe.atualizado_em,
        nome_segurado=detalhe.nome_segurado,
        apolice_id=detalhe.apolice_id,
        codigo_ibge_area=detalhe.codigo_ibge_area,
        evento=None
        if evento is None
        else RespostaEventoDetalhe(
            id=evento.id,
            tipo=str(evento.tipo),
            area=evento.area,
            intensidade=evento.intensidade,
            proveniencia=str(evento.proveniencia),
            periodo_inicio=evento.periodo_inicio,
            periodo_fim=evento.periodo_fim,
        ),
        regra_id=detalhe.regra_id,
        regra_versao=detalhe.regra_versao,
        apresentacao_simulada=None
        if apresentacao is None
        else RespostaApresentacaoSimulada(
            canal=str(apresentacao.canal),
            assunto=apresentacao.assunto,
            corpo=apresentacao.corpo,
            rotulo=apresentacao.rotulo,
        ),
        versoes=[_resposta_versao(versao) for versao in detalhe.versoes],
        excecao=None
        if excecao is None
        else RespostaExcecaoDetalhe(
            causa=excecao.causa,
            tentativas=excecao.tentativas,
            impacto=excecao.impacto,
            criado_em=excecao.criado_em,
        ),
    )


def montar_servico_detalhe_resultado(configuracao: Configuracao) -> ServicoDetalheResultado:
    """Compõe o serviço de detalhe sobre os repositórios reais do DuckDB local."""

    caminho = configuracao.caminho_banco
    validador = ValidadorSaidaCanal(
        LimitesCanal(
            whatsapp=configuracao.limite_caracteres_whatsapp,
            sms=configuracao.limite_caracteres_sms,
            assunto_email=configuracao.limite_caracteres_assunto_email,
            corpo_email=configuracao.limite_caracteres_corpo_email,
        )
    )
    return ServicoDetalheResultado(
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


def criar_roteador(configuracao: Configuracao) -> APIRouter:
    """Compõe o recurso de consulta do detalhe individual de um resultado."""

    roteador = APIRouter(tags=["Resultados"])
    servico = montar_servico_detalhe_resultado(configuracao)

    @roteador.get(
        CAMINHO_DETALHE,
        response_model=RespostaDetalheResultado,
        status_code=200,
        summary="Consultar o detalhe individual de um resultado de simulação",
        description=(
            "Devolve segurado sintético, apólice, canal, conteúdo, horários, estado, "
            "evento, versão da regra e as aprovações agêntica e humana de origem de uma "
            "mensagem. Todas as tentativas de geração aparecem relacionadas à sua própria "
            "avaliação crítica e decisões humanas, na ordem cronológica. Uma mensagem "
            "inexistente e uma mensagem que existe mas pertence a outra execução devolvem "
            "exatamente a mesma resposta `404`, sem revelar a existência cruzada do registro."
        ),
        responses={
            200: {"description": "Mensagem encontrada na execução informada."},
            404: {
                "description": "Mensagem inexistente ou pertencente a outra execução.",
                "model": ProblemaDetalheResultado,
            },
            422: {
                "description": "Algum identificador informado não é um UUID válido.",
                "model": ProblemaDetalheResultado,
            },
        },
    )
    async def consultar_detalhe(  # pyright: ignore[reportUnusedFunction]
        execucao_id: str, mensagem_id: str
    ) -> RespostaDetalheResultado | JSONResponse:
        """Traduz `ServicoDetalheResultado.obter` para o contrato REST/JSON público."""

        try:
            execucao_uuid = UUID(execucao_id)
            mensagem_uuid = UUID(mensagem_id)
        except ValueError:
            return problema(
                422,
                "identificador_invalido",
                "O identificador da execução ou da mensagem não é um UUID válido.",
                "Nenhum detalhe pode ser exibido.",
                "Consulte a mensagem pelos identificadores retornados pela API de resultados.",
            )

        detalhe = servico.obter(execucao_uuid, mensagem_uuid)
        if detalhe is None:
            return _problema_nao_encontrado(execucao_id, mensagem_id)
        return _resposta_detalhe(detalhe)

    return roteador
