"""Recurso REST/JSON da simulação local do lote confirmado (SIMUL-01, 07, 10, 11).

`GET /execucoes/{id}/simulacao` devolve o que a confirmação precisa mostrar — evento, regra,
período, quantidade de destinatários e distribuição pelos três canais — e, depois de simular,
as entregas com a apresentação por canal, sempre rotuladas como simuladas. Traz também a
navegação entre a origem e as retentativas, sem mesclar históricos.

`POST /execucoes/{id}/confirmar-simulacao` exige o campo de reconhecimento marcado e a
`Idempotency-Key`. `POST /execucoes/{origem_id}/nova-tentativa-simulacao` cria a execução
correlacionada a partir de `falhou_simulacao`.

Nenhum conector real de canal é montado, importado ou chamado aqui: a composição liga apenas
repositórios locais do DuckDB. O parâmetro `injecao_falha_teste` de `ServicoSimulacao.confirmar`
também **nunca** é passado por este módulo — ele existe só para o teste determinístico de
rollback, e um teste verifica que ele não aparece nesta composição.

SPEC_DEVIATION (História 3.6): a `tasks.md` (T4) escreve "`GET /api/v1/execucoes/{id}` estendido
com o resumo da simulação". A rota `GET /execucoes/{id}` é de outro recurso (2.6,
`adaptadores/http/execucao_preventiva.py`) e já expõe estado, marcos, `execucao_origem_id` e
retentativas — a metade de SIMUL-11 que ela cobre continua onde está. O resumo da simulação
entrou como `GET /execucoes/{id}/simulacao` neste roteador, o arquivo que a própria T4 nomeia
em "Where", em vez de inchar o recurso de acompanhamento da execução com dados de outra etapa.
"""

from datetime import datetime
from hashlib import sha256
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from central_preventiva.adaptadores.persistencia.repositorio_avaliacoes_criticas import (
    RepositorioAvaliacoesCriticas,
)
from central_preventiva.adaptadores.persistencia.repositorio_elegibilidade import (
    RepositorioElegibilidades,
)
from central_preventiva.adaptadores.persistencia.repositorio_entregas_simuladas import (
    RepositorioEntregasSimuladas,
)
from central_preventiva.adaptadores.persistencia.repositorio_execucao_preventiva import (
    ConflitoVersao,
    RepositorioExcecoesOperacionais,
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
from central_preventiva.aplicacao.simulacao import (
    EstadoNaoConfirmavel,
    ExecucaoInexistente,
    FalhaLocalSimulacao,
    NenhumaMensagemAprovada,
    OrigemNaoRetentavel,
    PortasSimulacao,
    ReconhecimentoObrigatorio,
    ResultadoSimulacao,
    ResumoSimulacao,
    ServicoSimulacao,
    SnapshotInvalido,
)
from central_preventiva.composicao.configuracao import Configuracao

TIPO_PROBLEMA = "application/problem+json"
CAMINHO_RESUMO = "/execucoes/{execucao_id}/simulacao"
CAMINHO_CONFIRMACAO = "/execucoes/{execucao_id}/confirmar-simulacao"
CAMINHO_NOVA_TENTATIVA_SIMULACAO = "/execucoes/{execucao_origem_id}/nova-tentativa-simulacao"


class RespostaEventoSimulacao(BaseModel):
    """Evento meteorológico que originou a execução a simular."""

    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(description="Identificador do evento meteorológico.")
    tipo: str = Field(description="Tipo do evento (`chuva_intensa` ou `granizo`).")
    area: str = Field(description="Código de área monitorada afetada pelo evento.")
    intensidade: float = Field(description="Intensidade observada do evento.")
    proveniencia: str = Field(description="Origem do evento (`real_inmet` ou `sintetico`).")
    periodo_inicio: datetime = Field(description="Início do período observado, em UTC.")
    periodo_fim: datetime = Field(description="Fim do período observado, em UTC.")


class RespostaCanalSimulacao(BaseModel):
    """Quantidade de destinatários do lote simulável em um canal."""

    model_config = ConfigDict(extra="forbid")

    canal: str = Field(description="Canal da comunicação (`whatsapp`, `email` ou `sms`).")
    total: int = Field(description="Destinatários do lote simulável neste canal.")


class RespostaEntregaSimulada(BaseModel):
    """Uma entrega simulada: como o conteúdo aprovado apareceria no canal (SIMUL-06)."""

    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(description="Identificador da entrega simulada.")
    mensagem_id: UUID = Field(description="Mensagem aprovada que originou a entrega.")
    canal: str = Field(description="Canal em que a apresentação seria feita.")
    rotulo: str = Field(
        description=(
            "Rótulo fixo da natureza da entrega: sempre 'simulada'. Nenhuma confirmação nem "
            "falha de provedor externo é registrada, porque nenhum conector real é usado."
        )
    )
    assunto: str | None = Field(
        description="Assunto apresentado, presente somente no canal de e-mail."
    )
    corpo: str = Field(description="Corpo apresentado, cópia exata do conteúdo aprovado.")
    criado_em: datetime = Field(description="Instante RFC 3339 em UTC do registro da entrega.")


class RespostaResumoSimulacao(BaseModel):
    """Resumo da simulação de uma execução, antes e depois de confirmá-la (SIMUL-01)."""

    model_config = ConfigDict(extra="forbid")

    execucao_id: UUID = Field(description="Identificador da execução.")
    estado: str = Field(description="Estado agregado atual da execução.")
    versao: int = Field(
        description="Versão de concorrência otimista a reenviar como `versao_esperada`."
    )
    evento: RespostaEventoSimulacao | None = Field(
        description="Evento de origem, ou nulo quando a execução não tem público preservado."
    )
    regra_id: UUID | None = Field(description="Regra preventiva aplicada ao público do lote.")
    regra_versao: int | None = Field(description="Versão da regra aplicada ao público.")
    total_destinatarios: int = Field(
        description="Destinatários do lote simulável: aprovados e já simulados."
    )
    distribuicao_por_canal: list[RespostaCanalSimulacao] = Field(
        description="Distribuição do lote simulável entre WhatsApp, e-mail e SMS."
    )
    entregas: list[RespostaEntregaSimulada] = Field(
        description="Entregas simuladas já registradas, vazias antes da confirmação."
    )
    execucao_origem_id: UUID | None = Field(
        description=(
            "Execução terminal que originou esta nova tentativa; nula quando esta execução "
            "não é correlacionada a nenhuma outra."
        )
    )
    retentativas: list[UUID] = Field(
        description=(
            "Execuções criadas como nova tentativa a partir desta; cada uma mantém seu "
            "próprio histórico, sem mesclar marcos."
        )
    )


class PedidoConfirmacaoSimulacao(BaseModel):
    """Confirmação consciente da simulação, com o reconhecimento explícito (SIMUL-03)."""

    model_config = ConfigDict(extra="forbid")

    versao_esperada: int = Field(
        description="Versão de concorrência otimista lida no resumo (AD-008)."
    )
    reconhecimento_simulacao: bool = Field(
        default=False,
        description=(
            "Reconhecimento explícito de que a operação é uma simulação e nenhuma "
            "comunicação real será enviada. Sem ele o comando é recusado."
        ),
    )


class RespostaSimulacaoConfirmada(BaseModel):
    """Desfecho da confirmação: onde o agregado parou e o que a simulação registrou."""

    model_config = ConfigDict(extra="forbid")

    execucao_id: UUID = Field(description="Execução cuja simulação foi executada.")
    estado: str = Field(description="Estado agregado da execução após a simulação.")
    entregas_criadas: list[UUID] = Field(
        description="Entregas simuladas criadas nesta confirmação."
    )
    mensagens_simuladas: list[UUID] = Field(
        description="Mensagens que passaram a `simulada_entregue` nesta confirmação."
    )


class RespostaNovaTentativaSimulacao(BaseModel):
    """Ack da execução correlacionada criada a partir de uma falha local de simulação."""

    model_config = ConfigDict(extra="forbid")

    execucao_id: UUID = Field(description="Identificador da execução correlacionada criada.")
    execucao_origem_id: UUID = Field(
        description="Execução terminal de origem, que permanece terminal."
    )


class ProblemaSimulacao(BaseModel):
    """Falha da simulação, com ocorrência, impacto e próxima ação segura."""

    model_config = ConfigDict(extra="forbid")

    codigo: str = Field(description="Código estável que identifica o tipo da falha.")
    correlacao_id: str = Field(description="Identificador único desta ocorrência de falha.")
    ocorrencia: str = Field(description="O que aconteceu, em português brasileiro.")
    impacto: str = Field(description="Efeito prático da falha para quem solicitou a operação.")
    proxima_acao: str = Field(description="Próxima ação segura recomendada para contornar a falha.")


def problema(
    status: int, codigo: str, ocorrencia: str, impacto: str, proxima_acao: str
) -> JSONResponse:
    """Monta a resposta `problem+json` correlacionada de uma falha da simulação."""

    corpo = ProblemaSimulacao(
        codigo=codigo,
        correlacao_id=str(uuid4()),
        ocorrencia=ocorrencia,
        impacto=impacto,
        proxima_acao=proxima_acao,
    )
    return JSONResponse(status_code=status, media_type=TIPO_PROBLEMA, content=corpo.model_dump())


def _hash_requisicao_escopado(identificador_alvo: str, corpo: bytes) -> str:
    """Hash de conteúdo da requisição, escopado pelo identificador do recurso alvo.

    O corpo da confirmação varia de fato (versão esperada e reconhecimento), mas o escopo
    pelo alvo é mantido de propósito: sem ele, dois comandos idênticos para execuções
    diferentes produziriam o mesmo hash, e a mesma `Idempotency-Key` devolveria a simulação
    da primeira execução em vez de ser rejeitada como conflito. Mesma correção aplicada em
    `preflight_ia.py` e `revisao_lote.py` (AD-002).
    """

    return sha256(identificador_alvo.encode() + b":" + corpo).hexdigest()


def _problema_execucao_inexistente(execucao_id: str) -> JSONResponse:
    """Resposta idêntica para execução inexistente, em qualquer motivo (AD-011)."""

    return problema(
        404,
        "execucao_inexistente",
        f"A execução '{execucao_id}' não existe.",
        "Nenhuma simulação pode ser consultada nem confirmada.",
        "Consulte a execução pelo identificador UUID retornado pela API.",
    )


def _problema_execucao_id_invalido(execucao_id: str) -> JSONResponse:
    """Resposta de identificador que não é um UUID válido."""

    return problema(
        422,
        "execucao_id_invalido",
        f"'{execucao_id}' não é um identificador de execução válido.",
        "Nenhuma simulação foi consultada nem confirmada.",
        "Repita a requisição com o identificador UUID retornado pela API.",
    )


def _problema_idempotency_key_ausente() -> JSONResponse:
    """Resposta de requisição mutável sem `Idempotency-Key` (AD-002)."""

    return problema(
        422,
        "idempotency_key_ausente",
        "A requisição não informou o cabeçalho Idempotency-Key.",
        "Nenhuma simulação foi executada.",
        "Repita a requisição incluindo um cabeçalho Idempotency-Key único.",
    )


def _problema_conflito_idempotencia() -> JSONResponse:
    """Resposta de reuso da mesma chave com outro conteúdo de requisição (AD-002)."""

    return problema(
        409,
        "conflito_idempotencia",
        "A chave de idempotência já foi usada com outro conteúdo de requisição.",
        "Nenhuma simulação nova foi executada.",
        "Gere uma nova Idempotency-Key para executar outra simulação.",
    )


def _resposta_resumo(resumo: ResumoSimulacao) -> RespostaResumoSimulacao:
    """Traduz o resumo da simulação para o contrato público."""

    evento = resumo.evento
    return RespostaResumoSimulacao(
        execucao_id=resumo.execucao_id,
        estado=str(resumo.estado),
        versao=resumo.versao,
        evento=None
        if evento is None
        else RespostaEventoSimulacao(
            id=evento.id,
            tipo=str(evento.tipo),
            area=evento.area,
            intensidade=evento.intensidade,
            proveniencia=str(evento.proveniencia),
            periodo_inicio=evento.periodo_inicio,
            periodo_fim=evento.periodo_fim,
        ),
        regra_id=resumo.regra_id,
        regra_versao=resumo.regra_versao,
        total_destinatarios=resumo.total_destinatarios,
        distribuicao_por_canal=[
            RespostaCanalSimulacao(canal=str(canal), total=total)
            for canal, total in resumo.distribuicao_por_canal
        ],
        entregas=[
            RespostaEntregaSimulada(
                id=entrega.id,
                mensagem_id=entrega.mensagem_id,
                canal=str(entrega.canal),
                rotulo=entrega.apresentacao.rotulo,
                assunto=entrega.apresentacao.assunto,
                corpo=entrega.apresentacao.corpo,
                criado_em=entrega.criado_em,
            )
            for entrega in resumo.entregas
        ],
        execucao_origem_id=resumo.execucao_origem_id,
        retentativas=list(resumo.retentativas),
    )


def _resposta_confirmacao(resultado: ResultadoSimulacao) -> RespostaSimulacaoConfirmada:
    """Traduz o desfecho da confirmação para o contrato público."""

    return RespostaSimulacaoConfirmada(
        execucao_id=resultado.execucao_id,
        estado=str(resultado.estado),
        entregas_criadas=list(resultado.entregas_criadas),
        mensagens_simuladas=list(resultado.mensagens_simuladas),
    )


def montar_portas_simulacao(configuracao: Configuracao) -> PortasSimulacao:
    """Compõe as portas reais da simulação a partir da configuração local.

    Todas as portas são repositórios do DuckDB local. Nenhum cliente de canal existe aqui,
    porque nenhuma entrega real é feita em lugar nenhum do MVP (ADR-0009/0013).
    """

    caminho = configuracao.caminho_banco
    return PortasSimulacao(
        execucoes=RepositorioExecucaoPreventiva(caminho),
        mensagens=RepositorioMensagens(caminho),
        avaliacoes=RepositorioAvaliacoesCriticas(caminho),
        entregas=RepositorioEntregasSimuladas(caminho),
        excecoes=RepositorioExcecoesOperacionais(caminho),
        elegibilidades=RepositorioElegibilidades(caminho),
        eventos=RepositorioEventosMeteorologicos(caminho),
        idempotencia=RepositorioIdempotencia(caminho),
        transacao=TransacaoDuckDB(caminho),
    )


def criar_roteador(configuracao: Configuracao) -> APIRouter:
    """Compõe o recurso da simulação local do lote confirmado."""

    roteador = APIRouter(tags=["Simulação"])
    servico = ServicoSimulacao(montar_portas_simulacao(configuracao))
    execucoes_repo = RepositorioExecucaoPreventiva(configuracao.caminho_banco)

    @roteador.get(
        CAMINHO_RESUMO,
        response_model=RespostaResumoSimulacao,
        status_code=200,
        summary="Consultar o resumo da simulação de uma execução",
        description=(
            "Devolve o que a confirmação da simulação precisa mostrar: evento, regra, "
            "período observado, quantidade de destinatários e distribuição entre WhatsApp, "
            "e-mail e SMS. Depois da simulação, devolve também cada entrega simulada com a "
            "apresentação que o canal teria, sempre rotulada como simulada e sem nenhuma "
            "confirmação ou falha de provedor externo. Traz ainda a navegação entre esta "
            "execução, sua origem e suas retentativas, sem mesclar históricos."
        ),
        responses={
            200: {"description": "Execução encontrada."},
            404: {"description": "Execução inexistente.", "model": ProblemaSimulacao},
            422: {
                "description": "O identificador da execução não é um UUID válido.",
                "model": ProblemaSimulacao,
            },
        },
    )
    async def consultar_resumo(  # pyright: ignore[reportUnusedFunction]
        execucao_id: str,
    ) -> RespostaResumoSimulacao | JSONResponse:
        """Traduz `ServicoSimulacao.obter_resumo` para o contrato REST/JSON público."""

        try:
            execucao_uuid = UUID(execucao_id)
        except ValueError:
            return _problema_execucao_id_invalido(execucao_id)

        resumo = servico.obter_resumo(execucao_uuid)
        if resumo is None:
            return _problema_execucao_inexistente(execucao_id)
        return _resposta_resumo(resumo)

    @roteador.post(
        CAMINHO_CONFIRMACAO,
        response_model=RespostaSimulacaoConfirmada,
        status_code=200,
        summary="Confirmar e executar a simulação de uma execução",
        description=(
            "Executa a simulação local do lote aprovado. Exige o campo "
            "`reconhecimento_simulacao` marcado: sem ele o comando é recusado, mesmo por "
            "chamada direta à API. A elegibilidade das mensagens é reverificada do estado "
            "real no momento da confirmação, e só as aprovadas pelo agente crítico e por "
            "Marina são reclamadas: rejeitada, excluída, em exceção ou de volta ao ciclo de "
            "geração fica de fora. Cada mensagem reclamada ganha uma entrega simulada e passa "
            "a 'simulada_entregue' na mesma transação; nenhum conector real de WhatsApp, "
            "e-mail ou SMS é usado. Uma falha local desfaz a transação inteira, preserva as "
            "mensagens como 'aprovada' e move a execução a 'falhou_simulacao'. Exige o "
            "cabeçalho `Idempotency-Key`; repeti-lo devolve a simulação já registrada."
        ),
        responses={
            200: {"description": "Simulação executada (ou já registrada, no replay)."},
            404: {"description": "Execução inexistente.", "model": ProblemaSimulacao},
            409: {
                "description": (
                    "Execução fora de 'aguardando_confirmacao', `versao_esperada` "
                    "desatualizada ou chave de idempotência reusada com outro conteúdo."
                ),
                "model": ProblemaSimulacao,
            },
            422: {
                "description": (
                    "Requisição sem `Idempotency-Key`, identificador inválido, "
                    "reconhecimento não marcado ou lote sem nenhuma mensagem aprovada."
                ),
                "model": ProblemaSimulacao,
            },
            500: {
                "description": "Falha local durante a simulação, já revertida.",
                "model": ProblemaSimulacao,
            },
        },
    )
    async def confirmar_simulacao(  # pyright: ignore[reportUnusedFunction]
        execucao_id: str,
        pedido: PedidoConfirmacaoSimulacao,
        requisicao: Request,
        idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    ) -> RespostaSimulacaoConfirmada | JSONResponse:
        """Traduz `ServicoSimulacao.confirmar` para o contrato REST/JSON público.

        `injecao_falha_teste` não é passado aqui, nem em nenhum outro ponto de composição:
        ele é um gancho exclusivo de teste (ver o docstring de `ServicoSimulacao.confirmar`).
        """

        if idempotency_key is None or not idempotency_key.strip():
            return _problema_idempotency_key_ausente()
        try:
            execucao_uuid = UUID(execucao_id)
        except ValueError:
            return _problema_execucao_id_invalido(execucao_id)

        hash_requisicao = _hash_requisicao_escopado(execucao_id, await requisicao.body())
        try:
            resultado = servico.confirmar(
                execucao_uuid,
                pedido.versao_esperada,
                pedido.reconhecimento_simulacao,
                idempotency_key,
                hash_requisicao,
            )
        except ReconhecimentoObrigatorio:
            return problema(
                422,
                "reconhecimento_obrigatorio",
                "A confirmação não reconheceu explicitamente a natureza simulada da operação.",
                "Nenhuma simulação foi executada.",
                "Marque o reconhecimento de que nenhuma comunicação real será enviada e "
                "reenvie a confirmação.",
            )
        except ExecucaoInexistente:
            return _problema_execucao_inexistente(execucao_id)
        except EstadoNaoConfirmavel as recusa:
            return problema(
                409,
                "estado_nao_confirmavel",
                f"A execução '{execucao_id}' está em '{recusa.estado}'.",
                "Nenhuma simulação foi executada.",
                "A confirmação só parte de uma execução em 'aguardando_confirmacao'.",
            )
        except NenhumaMensagemAprovada:
            return problema(
                422,
                "nenhuma_mensagem_aprovada",
                f"A execução '{execucao_id}' não tem nenhuma mensagem aprovada pelo agente "
                "crítico e por Marina no momento da confirmação.",
                "Nenhuma simulação foi criada; uma simulação vazia nunca é registrada.",
                "Recarregue o lote de revisão e confira as decisões antes de confirmar.",
            )
        except ConflitoVersao:
            return problema(
                409,
                "conflito_versao",
                f"A versão esperada não corresponde à versão atual da execução "
                f"'{execucao_id}'.",
                "Nenhuma mensagem foi reclamada e nenhuma entrega simulada foi criada.",
                "Recarregue o resumo da simulação e reenvie a confirmação com a versão atual.",
            )
        except ConflitoIdempotencia:
            return _problema_conflito_idempotencia()
        except FalhaLocalSimulacao as falha:
            return problema(
                500,
                "falha_local_simulacao",
                f"A simulação da execução '{execucao_id}' falhou localmente "
                f"({falha.causa}).",
                "Nenhuma entrega simulada foi registrada e as mensagens aprovadas "
                "continuam aprovadas.",
                "Solicite uma nova tentativa de simulação a partir desta execução.",
            )

        return _resposta_confirmacao(resultado)

    @roteador.post(
        CAMINHO_NOVA_TENTATIVA_SIMULACAO,
        response_model=RespostaNovaTentativaSimulacao,
        status_code=202,
        summary="Solicitar nova tentativa de simulação",
        description=(
            "Valida a integridade dos snapshots versionados da execução de origem e, "
            "passando, cria uma execução correlacionada nova em 'aguardando_geracao', com "
            "`execucao_origem_id` próprio e uma cópia integral do público elegível da origem "
            "(incluídos e excluídos). A execução de origem permanece em 'falhou_simulacao' e "
            "nunca é reaberta. Exige o cabeçalho `Idempotency-Key`."
        ),
        responses={
            202: {"description": "Execução correlacionada criada."},
            404: {"description": "Execução de origem inexistente.", "model": ProblemaSimulacao},
            409: {
                "description": "Origem fora de 'falhou_simulacao' ou conflito de chave.",
                "model": ProblemaSimulacao,
            },
            422: {
                "description": (
                    "Requisição sem `Idempotency-Key`, identificador inválido ou snapshot "
                    "da origem incompleto."
                ),
                "model": ProblemaSimulacao,
            },
        },
    )
    async def solicitar_nova_tentativa_simulacao(  # pyright: ignore[reportUnusedFunction]
        execucao_origem_id: str,
        requisicao: Request,
        idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    ) -> RespostaNovaTentativaSimulacao | JSONResponse:
        """Traduz `ServicoSimulacao.solicitar_nova_tentativa` para o contrato público."""

        if idempotency_key is None or not idempotency_key.strip():
            return _problema_idempotency_key_ausente()
        try:
            origem_uuid = UUID(execucao_origem_id)
        except ValueError:
            return _problema_execucao_id_invalido(execucao_origem_id)

        if execucoes_repo.buscar(origem_uuid) is None:
            return _problema_execucao_inexistente(execucao_origem_id)

        hash_requisicao = _hash_requisicao_escopado(
            execucao_origem_id, await requisicao.body()
        )
        try:
            nova_execucao_id = servico.solicitar_nova_tentativa(
                origem_uuid, idempotency_key, hash_requisicao
            )
        except OrigemNaoRetentavel as recusa:
            return problema(
                409,
                "origem_nao_retentavel",
                f"A execução '{execucao_origem_id}' está em '{recusa.estado}'.",
                "Nenhuma execução nova foi criada.",
                "A nova tentativa de simulação só parte de uma execução em "
                "'falhou_simulacao'.",
            )
        except SnapshotInvalido as recusa:
            return problema(
                422,
                "snapshot_invalido",
                f"Os snapshots da execução '{execucao_origem_id}' não passaram na "
                f"validação: {recusa.motivo}.",
                "Nenhuma execução nova foi criada.",
                "Reinicie uma execução preventiva a partir da área monitorada.",
            )
        except ConflitoIdempotencia:
            return _problema_conflito_idempotencia()

        return RespostaNovaTentativaSimulacao(
            execucao_id=nova_execucao_id, execucao_origem_id=origem_uuid
        )

    return roteador
