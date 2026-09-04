"""Recurso REST/JSON da revisão humana do lote de comunicação (REVISAO-01..14).

`GET /execucoes/{id}/revisao` devolve o lote já ordenado com os itens que exigem atenção
primeiro, e é a primeira rota do projeto que expõe o texto gerado: a consulta de 3.2
deliberadamente não o expõe, porque decidir sobre ele é escopo desta história.

`POST /execucoes/{id}/revisao/decisoes` aplica uma ou várias decisões numa transação única.
Um conflito de `versao_esperada` em qualquer item devolve `409` sem efeito parcial; um item
já decidido é recusado no corpo da resposta, com motivo, sem impedir os demais.
"""

import asyncio
from datetime import datetime
from hashlib import sha256
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from central_preventiva.adaptadores.http.preflight_ia import montar_servico_geracao
from central_preventiva.adaptadores.persistencia.repositorio_avaliacoes_criticas import (
    RepositorioAvaliacoesCriticas,
)
from central_preventiva.adaptadores.persistencia.repositorio_contextos_agente import (
    RepositorioContextosAgente,
)
from central_preventiva.adaptadores.persistencia.repositorio_decisoes_humanas import (
    RepositorioDecisoesHumanas,
)
from central_preventiva.adaptadores.persistencia.repositorio_elegibilidade import (
    RepositorioElegibilidades,
)
from central_preventiva.adaptadores.persistencia.repositorio_execucao_preventiva import (
    ConflitoVersao,
    RepositorioExecucaoPreventiva,
)
from central_preventiva.adaptadores.persistencia.repositorio_idempotencia import (
    RepositorioIdempotencia,
)
from central_preventiva.adaptadores.persistencia.repositorio_mensagens import (
    RepositorioMensagens,
)
from central_preventiva.adaptadores.persistencia.repositorio_meteorologia import (
    RepositorioEventosMeteorologicos,
)
from central_preventiva.adaptadores.persistencia.transacao import TransacaoDuckDB
from central_preventiva.aplicacao.portas_persistencia import ConflitoIdempotencia
from central_preventiva.aplicacao.revisao_lote import (
    ConflitoVersaoDecisao,
    DecisaoRequisitada,
    EstadoNaoRevisavel,
    ExecucaoInexistente,
    ItemLoteRevisao,
    JustificativaObrigatoria,
    LoteRevisao,
    PortasRevisaoLote,
    ResultadoDecisaoLote,
    ServicoRevisaoLote,
    VersaoRevisada,
)
from central_preventiva.composicao.configuracao import Configuracao
from central_preventiva.dominio.decisao_humana import ResultadoDecisaoHumana

_tarefas_de_regeneracao: set[asyncio.Task[None]] = set()
"""Referências fortes às retomadas em andamento, para não serem coletadas."""

TIPO_PROBLEMA = "application/problem+json"
CAMINHO_LOTE = "/execucoes/{execucao_id}/revisao"
CAMINHO_DECISOES = "/execucoes/{execucao_id}/revisao/decisoes"

PERFIL_REVISOR_PADRAO = "administrador"
"""Perfil demonstrativo assumido quando o cliente não informa outro (ADR-0009)."""


class RespostaEventoLote(BaseModel):
    """Evento meteorológico que originou a execução em revisão."""

    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(description="Identificador do evento meteorológico.")
    tipo: str = Field(description="Tipo do evento (`chuva_intensa` ou `granizo`).")
    area: str = Field(description="Código de área monitorada afetada pelo evento.")
    intensidade: float = Field(description="Intensidade observada do evento.")
    proveniencia: str = Field(description="Origem do evento (`real_inmet` ou `sintetico`).")
    periodo_inicio: datetime = Field(description="Início do período observado, em UTC.")
    periodo_fim: datetime = Field(description="Fim do período observado, em UTC.")


class RespostaDestinatario(BaseModel):
    """Destinatário sintético da mensagem, como o snapshot da elegibilidade registrou."""

    model_config = ConfigDict(extra="forbid")

    elegibilidade_id: UUID = Field(description="Item do público elegível que originou a mensagem.")
    segurado_id: UUID = Field(description="Segurado sintético destinatário.")
    nome_segurado: str = Field(description="Nome sintético registrado no momento da avaliação.")
    apolice_id: UUID = Field(description="Apólice sintética que sustentou a elegibilidade.")
    codigo_ibge_area: str = Field(description="Área do destinatário no momento da avaliação.")
    canal: str = Field(description="Canal preferido registrado no snapshot da elegibilidade.")


class RespostaCriterioLote(BaseModel):
    """Um critério avaliado da elegibilidade, com o valor observado e o veredito."""

    model_config = ConfigDict(extra="forbid")

    operando: str = Field(description="O que foi comparado (ex.: área afetada, cobertura).")
    valor_observado: str = Field(description="Valor observado no momento da avaliação.")
    atende: bool = Field(description="Se o valor observado atende ao critério.")
    justificativa: str = Field(description="Explicação em português brasileiro do resultado.")


class RespostaOrigem(BaseModel):
    """Dados de origem da mensagem: evento, regra versionada e critérios avaliados."""

    model_config = ConfigDict(extra="forbid")

    evento_id: UUID = Field(description="Evento meteorológico de origem.")
    regra_id: UUID = Field(description="Regra preventiva aplicada.")
    regra_versao: int = Field(description="Versão da regra aplicada no momento da avaliação.")
    justificativa: str = Field(description="Justificativa da inclusão no público elegível.")
    criterios: list[RespostaCriterioLote] = Field(
        description="Critérios avaliados, com o valor observado e o veredito de cada um."
    )


class RespostaProveniencia(BaseModel):
    """Proveniência do contexto do agente: o que foi e o que não foi usado (3.1)."""

    model_config = ConfigDict(extra="forbid")

    categorias_usadas: list[str] = Field(
        description="Categorias de dado que chegaram ao contexto do agente redator."
    )
    categorias_nao_usadas: list[str] = Field(
        description="Categorias deliberadamente deixadas de fora do contexto."
    )


class RespostaMotivoCritico(BaseModel):
    """Um motivo categorizado da reprovação do agente crítico."""

    model_config = ConfigDict(extra="forbid")

    categoria: str = Field(description="Categoria fechada do motivo avaliado.")
    justificativa: str = Field(description="Justificativa do crítico para esta categoria.")


class RespostaAvaliacaoCriticaLote(BaseModel):
    """Avaliação do agente crítico sobre uma versão da mensagem (3.3)."""

    model_config = ConfigDict(extra="forbid")

    aprovada: bool = Field(description="Decisão textual do agente crítico sobre esta versão.")
    motivos: list[RespostaMotivoCritico] = Field(
        description="Motivos categorizados da reprovação; vazio quando a versão foi aprovada."
    )
    agente: str = Field(description="Agente responsável pela avaliação.")
    modelo: str = Field(description="Modelo da OpenAI usado na avaliação.")
    duracao_ms: float = Field(description="Duração da chamada de crítica, em milissegundos.")


class RespostaVersaoRevisada(BaseModel):
    """Uma tentativa de geração: conteúdo, verificação determinística e crítica."""

    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(description="Identificador da versão da mensagem.")
    numero_tentativa: int = Field(description="Número da tentativa de geração registrada.")
    assunto: str | None = Field(
        description="Assunto gerado, presente somente no canal de e-mail."
    )
    corpo: str = Field(description="Texto gerado desta tentativa, exibido sem edição possível.")
    valida: bool = Field(
        description="Veredito da verificação determinística de canal sobre esta tentativa."
    )
    motivo_invalidez: str | None = Field(
        description="Motivo da recusa determinística, ou nulo quando a saída é válida."
    )
    modelo: str = Field(description="Modelo da OpenAI usado nesta tentativa.")
    versao_prompt: str = Field(description="Versão do prompt usada nesta tentativa.")
    duracao_ms: float = Field(description="Duração da chamada de geração, em milissegundos.")
    tokens_entrada: int | None = Field(
        description="Tokens de entrada consumidos, ou nulo quando não reportados."
    )
    tokens_saida: int | None = Field(
        description="Tokens de saída consumidos, ou nulo quando não reportados."
    )
    criado_em: datetime = Field(description="Instante RFC 3339 em UTC do registro da versão.")
    avaliacao_critica: RespostaAvaliacaoCriticaLote | None = Field(
        description="Avaliação do crítico sobre esta versão, ou nula se ela não foi avaliada."
    )


class RespostaDecisaoRegistrada(BaseModel):
    """Uma decisão humana já registrada sobre a mensagem (REVISAO-07)."""

    model_config = ConfigDict(extra="forbid")

    versao_mensagem_id: UUID = Field(description="Versão da mensagem sobre a qual se decidiu.")
    perfil_responsavel: str = Field(description="Perfil sintético que tomou a decisão.")
    resultado: str = Field(description="Resultado da decisão humana.")
    justificativa: str | None = Field(
        description="Justificativa registrada, obrigatória fora da aprovação."
    )
    criado_em: datetime = Field(description="Instante RFC 3339 em UTC da decisão.")


class RespostaItemLote(BaseModel):
    """Uma mensagem do lote, com tudo que a decisão humana precisa (REVISAO-03)."""

    model_config = ConfigDict(extra="forbid")

    mensagem_id: UUID = Field(description="Identificador da mensagem.")
    canal: str = Field(description="Canal da mensagem (`whatsapp`, `email` ou `sms`).")
    estado: str = Field(description="Estado de conteúdo da mensagem, conforme o AD-4.")
    tentativa_atual: int = Field(description="Tentativa de geração em curso ou concluída.")
    limite_tentativas: int = Field(
        description="Máximo de tentativas de conteúdo permitidas por mensagem."
    )
    versao: int = Field(
        description="Versão de concorrência otimista a reenviar como `versao_esperada`."
    )
    destinatario: RespostaDestinatario = Field(description="Destinatário sintético da mensagem.")
    origem: RespostaOrigem = Field(description="Dados de origem que produziram a mensagem.")
    proveniencia: RespostaProveniencia | None = Field(
        description="Proveniência do contexto do agente, ou nula se ele não foi montado."
    )
    versoes: list[RespostaVersaoRevisada] = Field(
        description="Tentativas registradas, da primeira à última."
    )
    decisoes: list[RespostaDecisaoRegistrada] = Field(
        description="Decisões humanas já registradas sobre esta mensagem."
    )
    aprovada_pelo_critico: bool = Field(
        description="Se a última tentativa foi aprovada pelo agente crítico."
    )
    reprovacao_historica: bool = Field(
        description="Se alguma tentativa foi reprovada, ainda que a final tenha sido aprovada."
    )
    em_excecao: bool = Field(
        description="Se a mensagem terminou em exceção de conteúdo ou de integração."
    )
    decidivel: bool = Field(description="Se a mensagem aguarda decisão humana agora.")
    pode_regenerar: bool = Field(
        description="Se ainda há tentativa disponível para solicitar nova geração."
    )
    prioridade: int = Field(
        description="Ordem de atenção do item: menor valor exige atenção antes."
    )


class RespostaDistribuicaoCanal(BaseModel):
    """Quantidade de mensagens do lote em um canal."""

    model_config = ConfigDict(extra="forbid")

    canal: str = Field(description="Canal da comunicação.")
    total: int = Field(description="Quantidade de mensagens do lote neste canal.")


class RespostaLoteRevisao(BaseModel):
    """O lote de revisão de uma execução, com os itens de atenção primeiro (REVISAO-01)."""

    model_config = ConfigDict(extra="forbid")

    execucao_id: UUID = Field(description="Identificador da execução em revisão.")
    estado: str = Field(description="Estado agregado atual da execução.")
    evento: RespostaEventoLote | None = Field(
        description="Evento meteorológico de origem, ou nulo se o lote ainda está vazio."
    )
    regra_id: UUID | None = Field(description="Regra preventiva aplicada ao público do lote.")
    regra_versao: int | None = Field(description="Versão da regra aplicada ao público do lote.")
    total_publico_incluido: int = Field(
        description="Itens incluídos do público elegível desta execução."
    )
    distribuicao_por_canal: list[RespostaDistribuicaoCanal] = Field(
        description="Quantidade de mensagens do lote por canal."
    )
    aprovacoes_agenticas: int = Field(
        description="Mensagens cuja última tentativa foi aprovada pelo agente crítico."
    )
    itens_em_excecao: int = Field(
        description="Mensagens que terminaram em exceção de conteúdo ou de integração."
    )
    itens: list[RespostaItemLote] = Field(
        description="Mensagens do lote, com os itens que exigem atenção primeiro."
    )


class PedidoDecisao(BaseModel):
    """Uma decisão que Marina envia sobre uma mensagem específica."""

    model_config = ConfigDict(extra="forbid")

    mensagem_id: UUID = Field(description="Mensagem sobre a qual se decide.")
    versao_esperada: int = Field(
        description="Versão de concorrência otimista lida no lote (AD-008)."
    )
    resultado: ResultadoDecisaoHumana = Field(
        description="Decisão: aprovar, rejeitar, excluir do lote ou solicitar nova geração."
    )
    justificativa: str | None = Field(
        default=None,
        description="Justificativa da decisão, obrigatória fora da aprovação.",
    )


class PedidoDecisaoLote(BaseModel):
    """Envio de decisões sobre uma ou várias mensagens do lote."""

    model_config = ConfigDict(extra="forbid")

    decisoes: list[PedidoDecisao] = Field(
        default_factory=list[PedidoDecisao],
        description=(
            "Decisões a aplicar na mesma transação; lista vazia apenas reconhece o lote."
        ),
    )
    perfil: str = Field(
        default=PERFIL_REVISOR_PADRAO,
        description="Perfil sintético responsável pela decisão, registrado no histórico.",
    )


class RespostaDecisaoRecusada(BaseModel):
    """Um item excluído do envio, com o motivo estável da recusa."""

    model_config = ConfigDict(extra="forbid")

    mensagem_id: UUID = Field(description="Mensagem recusada do envio.")
    motivo: str = Field(description="Código estável do motivo da recusa deste item.")


class RespostaDecisaoLote(BaseModel):
    """Desfecho do envio: o que foi aplicado, o que foi recusado e onde o agregado parou."""

    model_config = ConfigDict(extra="forbid")

    execucao_id: UUID = Field(description="Execução cujo lote foi decidido.")
    estado: str = Field(description="Estado agregado da execução após o envio.")
    aplicadas: list[UUID] = Field(description="Mensagens cujas decisões foram aplicadas.")
    recusadas: list[RespostaDecisaoRecusada] = Field(
        description="Itens recusados do envio, cada um com o seu motivo."
    )
    mensagens_aprovadas: list[UUID] = Field(
        description="Mensagens aprovadas pelo agente crítico e por Marina."
    )
    regeneracoes_ativas: list[UUID] = Field(
        description="Mensagens devolvidas ao ciclo de geração por decisão humana."
    )


class ProblemaRevisao(BaseModel):
    """Falha da revisão do lote, com ocorrência, impacto e próxima ação segura."""

    model_config = ConfigDict(extra="forbid")

    codigo: str = Field(description="Código estável que identifica o tipo da falha.")
    correlacao_id: str = Field(description="Identificador único desta ocorrência de falha.")
    ocorrencia: str = Field(description="O que aconteceu, em português brasileiro.")
    impacto: str = Field(description="Efeito prático da falha para quem solicitou a operação.")
    proxima_acao: str = Field(description="Próxima ação segura recomendada para contornar a falha.")


def problema(
    status: int, codigo: str, ocorrencia: str, impacto: str, proxima_acao: str
) -> JSONResponse:
    """Monta a resposta `problem+json` correlacionada de uma falha da revisão."""

    corpo = ProblemaRevisao(
        codigo=codigo,
        correlacao_id=str(uuid4()),
        ocorrencia=ocorrencia,
        impacto=impacto,
        proxima_acao=proxima_acao,
    )
    return JSONResponse(status_code=status, media_type=TIPO_PROBLEMA, content=corpo.model_dump())


def _hash_requisicao_escopado(identificador_alvo: str, corpo: bytes) -> str:
    """Hash de conteúdo da requisição, escopado pelo identificador do recurso alvo.

    O corpo desta rota varia de fato (a lista de decisões), mas o escopo pelo alvo é mantido
    de propósito: sem ele, dois envios idênticos para execuções diferentes produziriam o mesmo
    hash e a mesma `Idempotency-Key` devolveria a resposta da primeira execução em vez de ser
    rejeitada como conflito. Mesma correção aplicada em `preflight_ia.py` (AD-002).
    """

    return sha256(identificador_alvo.encode() + b":" + corpo).hexdigest()


def _problema_execucao_inexistente(execucao_id: str) -> JSONResponse:
    """Resposta idêntica para execução inexistente, em qualquer motivo (AD-011)."""

    return problema(
        404,
        "execucao_inexistente",
        f"A execução '{execucao_id}' não existe.",
        "Nenhum lote de revisão pode ser exibido.",
        "Consulte a execução pelo identificador UUID retornado pela API.",
    )


def _problema_execucao_id_invalido(execucao_id: str) -> JSONResponse:
    """Resposta de identificador que não é um UUID válido."""

    return problema(
        422,
        "execucao_id_invalido",
        f"'{execucao_id}' não é um identificador de execução válido.",
        "Nenhum lote de revisão pode ser exibido.",
        "Repita a requisição com o identificador UUID retornado pela API.",
    )


def _resposta_criterios(item: ItemLoteRevisao) -> list[RespostaCriterioLote]:
    """Traduz os critérios do snapshot de elegibilidade para o contrato público."""

    return [
        RespostaCriterioLote(
            operando=criterio.operando,
            valor_observado=criterio.valor_observado,
            atende=criterio.atende,
            justificativa=criterio.justificativa,
        )
        for criterio in item.origem.criterios
    ]


def _resposta_versao(versao: VersaoRevisada) -> RespostaVersaoRevisada:
    """Traduz uma tentativa persistida, com a crítica dela, para o contrato público."""

    avaliacao = versao.avaliacao
    return RespostaVersaoRevisada(
        id=versao.id,
        numero_tentativa=versao.numero_tentativa,
        assunto=versao.conteudo.assunto,
        corpo=versao.conteudo.corpo,
        valida=versao.valida,
        motivo_invalidez=versao.motivo_invalidez,
        modelo=versao.modelo,
        versao_prompt=versao.versao_prompt,
        duracao_ms=versao.duracao_ms,
        tokens_entrada=versao.tokens_entrada,
        tokens_saida=versao.tokens_saida,
        criado_em=versao.criado_em,
        avaliacao_critica=None
        if avaliacao is None
        else RespostaAvaliacaoCriticaLote(
            aprovada=avaliacao.avaliacao.aprovada,
            motivos=[
                RespostaMotivoCritico(
                    categoria=str(motivo.categoria), justificativa=motivo.justificativa
                )
                for motivo in avaliacao.avaliacao.motivos
            ],
            agente=avaliacao.agente,
            modelo=avaliacao.modelo,
            duracao_ms=avaliacao.duracao_ms,
        ),
    )


def _resposta_item(item: ItemLoteRevisao) -> RespostaItemLote:
    """Traduz um item do lote para o contrato público, já agrupado por categoria."""

    return RespostaItemLote(
        mensagem_id=item.mensagem_id,
        canal=item.canal,
        estado=str(item.estado),
        tentativa_atual=item.tentativa_atual,
        limite_tentativas=item.limite_tentativas,
        versao=item.versao,
        destinatario=RespostaDestinatario(
            elegibilidade_id=item.destinatario.elegibilidade_id,
            segurado_id=item.destinatario.segurado_id,
            nome_segurado=item.destinatario.nome_segurado,
            apolice_id=item.destinatario.apolice_id,
            codigo_ibge_area=item.destinatario.codigo_ibge_area,
            canal=item.destinatario.canal,
        ),
        origem=RespostaOrigem(
            evento_id=item.origem.evento_id,
            regra_id=item.origem.regra_id,
            regra_versao=item.origem.regra_versao,
            justificativa=item.origem.justificativa,
            criterios=_resposta_criterios(item),
        ),
        proveniencia=None
        if item.proveniencia is None
        else RespostaProveniencia(
            categorias_usadas=list(item.proveniencia.categorias_usadas),
            categorias_nao_usadas=list(item.proveniencia.categorias_nao_usadas),
        ),
        versoes=[_resposta_versao(versao) for versao in item.versoes],
        decisoes=[
            RespostaDecisaoRegistrada(
                versao_mensagem_id=decisao.versao_mensagem_id,
                perfil_responsavel=decisao.perfil_responsavel,
                resultado=str(decisao.resultado),
                justificativa=decisao.justificativa,
                criado_em=decisao.criado_em,
            )
            for decisao in item.decisoes
        ],
        aprovada_pelo_critico=item.aprovada_pelo_critico,
        reprovacao_historica=item.reprovacao_historica,
        em_excecao=item.em_excecao,
        decidivel=item.decidivel,
        pode_regenerar=item.pode_regenerar,
        prioridade=item.prioridade,
    )


def _resposta_lote(lote: LoteRevisao) -> RespostaLoteRevisao:
    """Traduz o lote inteiro para o contrato público, preservando a ordem de atenção."""

    evento = lote.evento
    return RespostaLoteRevisao(
        execucao_id=lote.execucao_id,
        estado=str(lote.estado),
        evento=None
        if evento is None
        else RespostaEventoLote(
            id=evento.id,
            tipo=str(evento.tipo),
            area=evento.area,
            intensidade=evento.intensidade,
            proveniencia=str(evento.proveniencia),
            periodo_inicio=evento.periodo_inicio,
            periodo_fim=evento.periodo_fim,
        ),
        regra_id=lote.regra_id,
        regra_versao=lote.regra_versao,
        total_publico_incluido=lote.total_publico_incluido,
        distribuicao_por_canal=[
            RespostaDistribuicaoCanal(canal=canal, total=total)
            for canal, total in lote.distribuicao_por_canal
        ],
        aprovacoes_agenticas=lote.aprovacoes_agenticas,
        itens_em_excecao=lote.itens_em_excecao,
        itens=[_resposta_item(item) for item in lote.itens],
    )


def _resposta_decisao(resultado: ResultadoDecisaoLote) -> RespostaDecisaoLote:
    """Traduz o desfecho do envio de decisões para o contrato público."""

    return RespostaDecisaoLote(
        execucao_id=resultado.execucao_id,
        estado=str(resultado.estado),
        aplicadas=list(resultado.aplicadas),
        recusadas=[
            RespostaDecisaoRecusada(mensagem_id=item.mensagem_id, motivo=item.motivo)
            for item in resultado.recusadas
        ],
        mensagens_aprovadas=list(resultado.mensagens_aprovadas),
        regeneracoes_ativas=list(resultado.regeneracoes_ativas),
    )


def montar_portas_revisao(configuracao: Configuracao) -> PortasRevisaoLote:
    """Compõe as portas reais da revisão do lote a partir da configuração local.

    `acionar_regeneracao` reusa a retomada de 3.4 (`retomar_mensagens_pendentes`), disparada
    como task desacoplada — mesmo padrão do gatilho de geração do preflight — para que a
    resposta da decisão não espere o ciclo inteiro da mensagem regenerada.
    """

    caminho = configuracao.caminho_banco
    geracao = montar_servico_geracao(configuracao)

    async def acionar_regeneracao(execucao_id: UUID) -> None:
        """Agenda a retomada das mensagens devolvidas ao ciclo pela decisão humana."""

        tarefa = asyncio.create_task(geracao.retomar_mensagens_pendentes(execucao_id))
        _tarefas_de_regeneracao.add(tarefa)
        tarefa.add_done_callback(_tarefas_de_regeneracao.discard)

    return PortasRevisaoLote(
        execucoes=RepositorioExecucaoPreventiva(caminho),
        mensagens=RepositorioMensagens(caminho),
        elegibilidades=RepositorioElegibilidades(caminho),
        avaliacoes=RepositorioAvaliacoesCriticas(caminho),
        decisoes=RepositorioDecisoesHumanas(caminho),
        contextos=RepositorioContextosAgente(caminho),
        eventos=RepositorioEventosMeteorologicos(caminho),
        idempotencia=RepositorioIdempotencia(caminho),
        transacao=TransacaoDuckDB(caminho),
        acionar_regeneracao=acionar_regeneracao,
    )


def criar_roteador(configuracao: Configuracao) -> APIRouter:
    """Compõe o recurso de revisão humana do lote de comunicação."""

    roteador = APIRouter(tags=["Revisão do lote"])
    servico = ServicoRevisaoLote(montar_portas_revisao(configuracao))

    @roteador.get(
        CAMINHO_LOTE,
        response_model=RespostaLoteRevisao,
        status_code=200,
        summary="Consultar o lote de revisão de uma execução",
        description=(
            "Devolve o lote inteiro de comunicação da execução: evento, regra, público, "
            "distribuição por canal, aprovações agênticas e exceções no cabeçalho, e um item "
            "por mensagem com destinatário sintético, conteúdo de cada versão, verificação "
            "determinística, avaliação crítica, dados de origem e proveniência. Os itens que "
            "exigem atenção vêm primeiro: exceções, depois reprovações em alguma tentativa "
            "anterior, depois as aprovações limpas."
        ),
        responses={
            200: {"description": "Lote encontrado (pode estar vazio)."},
            404: {"description": "Execução inexistente.", "model": ProblemaRevisao},
            422: {
                "description": "O identificador da execução não é um UUID válido.",
                "model": ProblemaRevisao,
            },
        },
    )
    async def consultar_lote(  # pyright: ignore[reportUnusedFunction]
        execucao_id: str,
    ) -> RespostaLoteRevisao | JSONResponse:
        """Traduz `ServicoRevisaoLote.obter_lote` para o contrato REST/JSON público."""

        try:
            execucao_uuid = UUID(execucao_id)
        except ValueError:
            return _problema_execucao_id_invalido(execucao_id)

        lote = servico.obter_lote(execucao_uuid)
        if lote is None:
            return _problema_execucao_inexistente(execucao_id)
        return _resposta_lote(lote)

    @roteador.post(
        CAMINHO_DECISOES,
        response_model=RespostaDecisaoLote,
        status_code=200,
        summary="Decidir uma ou várias mensagens do lote de revisão",
        description=(
            "Aplica as decisões humanas (aprovar, rejeitar, excluir do lote ou solicitar nova "
            "geração) numa única transação: ou todas as decisões válidas do envio são "
            "aplicadas, ou nenhuma. Um conflito de `versao_esperada` em qualquer item devolve "
            "409 sem efeito parcial; um item já decidido antes é recusado no corpo da "
            "resposta, com motivo, sem impedir os demais. Rejeitar, excluir e regenerar "
            "exigem justificativa. Aplicadas as decisões, a execução avança para "
            "'aguardando_confirmacao' quando houver ao menos uma mensagem aprovada pelo "
            "crítico e por Marina, conclui sem simulação quando não houver nenhuma, e volta a "
            "'processando_mensagens' enquanto houver regeneração ativa. Exige o cabeçalho "
            "`Idempotency-Key`."
        ),
        responses={
            200: {"description": "Envio processado; o corpo informa aplicadas e recusadas."},
            404: {"description": "Execução inexistente.", "model": ProblemaRevisao},
            409: {
                "description": (
                    "Conflito de `versao_esperada`, execução fora de revisão ou chave de "
                    "idempotência reusada com outro conteúdo."
                ),
                "model": ProblemaRevisao,
            },
            422: {
                "description": (
                    "Requisição sem `Idempotency-Key`, identificador inválido ou decisão sem "
                    "justificativa."
                ),
                "model": ProblemaRevisao,
            },
        },
    )
    async def decidir_lote(  # pyright: ignore[reportUnusedFunction]
        execucao_id: str,
        pedido: PedidoDecisaoLote,
        requisicao: Request,
        idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    ) -> RespostaDecisaoLote | JSONResponse:
        """Traduz `ServicoRevisaoLote.decidir_lote` para o contrato REST/JSON público."""

        if idempotency_key is None or not idempotency_key.strip():
            return problema(
                422,
                "idempotency_key_ausente",
                "A requisição não informou o cabeçalho Idempotency-Key.",
                "Nenhuma decisão foi aplicada.",
                "Repita a requisição incluindo um cabeçalho Idempotency-Key único.",
            )
        try:
            execucao_uuid = UUID(execucao_id)
        except ValueError:
            return _problema_execucao_id_invalido(execucao_id)

        decisoes = tuple(
            DecisaoRequisitada(
                mensagem_id=item.mensagem_id,
                versao_esperada=item.versao_esperada,
                resultado=item.resultado,
                justificativa=item.justificativa,
            )
            for item in pedido.decisoes
        )
        hash_requisicao = _hash_requisicao_escopado(execucao_id, await requisicao.body())
        try:
            resultado = await servico.decidir_lote(
                execucao_uuid,
                decisoes,
                pedido.perfil,
                idempotency_key,
                hash_requisicao,
            )
        except ExecucaoInexistente:
            return _problema_execucao_inexistente(execucao_id)
        except EstadoNaoRevisavel as recusa:
            return problema(
                409,
                "estado_nao_revisavel",
                f"A execução '{execucao_id}' está em '{recusa.estado}'.",
                "Nenhuma decisão foi aplicada.",
                "A decisão do lote só parte de uma execução em 'aguardando_revisao'.",
            )
        except JustificativaObrigatoria as recusa:
            return problema(
                422,
                "justificativa_obrigatoria",
                f"A decisão '{recusa.resultado}' sobre a mensagem '{recusa.mensagem_id}' "
                "exige justificativa.",
                "Nenhuma decisão do envio foi aplicada.",
                "Preencha a justificativa da decisão e reenvie o lote.",
            )
        except (ConflitoVersaoDecisao, ConflitoVersao) as conflito:
            return _problema_conflito_versao(conflito)
        except ConflitoIdempotencia:
            return problema(
                409,
                "conflito_idempotencia",
                "A chave de idempotência já foi usada com outro conteúdo de requisição.",
                "Nenhuma decisão nova foi aplicada.",
                "Gere uma nova Idempotency-Key para enviar outra decisão.",
            )

        return _resposta_decisao(resultado)

    return roteador


def _problema_conflito_versao(
    conflito: ConflitoVersaoDecisao | ConflitoVersao,
) -> JSONResponse:
    """Resposta de conflito de concorrência otimista, sem nenhum efeito parcial (REVISAO-12)."""

    identificados = (
        ", ".join(str(item) for item in conflito.mensagens)
        if isinstance(conflito, ConflitoVersaoDecisao)
        else str(conflito.execucao_id)
    )
    return problema(
        409,
        "conflito_versao",
        f"A versão esperada não corresponde à persistida em: {identificados}.",
        "Nenhuma decisão do envio foi aplicada.",
        "Recarregue o lote de revisão e reenvie as decisões com a versão atual.",
    )
