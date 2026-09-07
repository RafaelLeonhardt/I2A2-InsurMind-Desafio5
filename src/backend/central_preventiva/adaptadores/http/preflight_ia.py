"""Recurso REST/JSON da preparação agêntica: preflight, nova tentativa e proveniência."""

import asyncio
from hashlib import sha256
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from central_preventiva.adaptadores.ia.agente_critico import AgenteCritico
from central_preventiva.adaptadores.ia.agente_redator import AgenteRedator
from central_preventiva.adaptadores.ia.verificador_disponibilidade_openai import (
    VerificadorDisponibilidadeOpenAI,
)
from central_preventiva.adaptadores.persistencia.repositorio_avaliacoes_criticas import (
    RepositorioAvaliacoesCriticas,
)
from central_preventiva.adaptadores.persistencia.repositorio_contextos_agente import (
    RepositorioContextosAgente,
)
from central_preventiva.adaptadores.persistencia.repositorio_elegibilidade import (
    RepositorioElegibilidades,
)
from central_preventiva.adaptadores.persistencia.repositorio_execucao_preventiva import (
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
from central_preventiva.aplicacao.geracao_mensagens import (
    PortasGeracaoMensagens,
    ServicoGeracaoMensagens,
)
from central_preventiva.aplicacao.grafos.geracao_mensagem import (
    DependenciasGrafo,
    construir_grafo,
)
from central_preventiva.aplicacao.portas_persistencia import ConflitoIdempotencia
from central_preventiva.aplicacao.preflight_ia import (
    EstadoNaoPreparavel,
    OrigemNaoRetentavel,
    PortasPreflightIA,
    ServicoPreflightIA,
    SnapshotInvalido,
)
from central_preventiva.composicao.configuracao import Configuracao
from central_preventiva.dominio.montador_contexto_agente import MontadorContextoAgente
from central_preventiva.dominio.validador_saida_canal import (
    LimitesCanal,
    ValidadorSaidaCanal,
)

_tarefas_de_geracao: set[asyncio.Task[None]] = set()
"""Referências fortes às tasks de geração em andamento, para não serem coletadas."""

TIPO_PROBLEMA = "application/problem+json"
CAMINHO_PREFLIGHT = "/execucoes/{execucao_id}/preflight"
CAMINHO_NOVA_TENTATIVA = "/execucoes/{execucao_origem_id}/nova-tentativa-ia"
CAMINHO_PROVENIENCIA = "/execucoes/{execucao_id}/contextos"


class RespostaPreflight(BaseModel):
    """Desfecho do preflight de uma execução: estado alcançado e o que foi preparado."""

    model_config = ConfigDict(extra="forbid")

    execucao_id: UUID = Field(description="Identificador da execução preparada.")
    estado: str = Field(description="Estado alcançado pela execução após o preflight.")
    contextos_montados: int = Field(
        description="Quantidade de itens do público elegível com contexto mínimo montado."
    )
    itens_em_excecao: list[UUID] = Field(
        description="Itens cujo contexto não pôde ser montado; os demais seguem normalmente."
    )
    causa: str | None = Field(
        description="Causa sanitizada do bloqueio, ou nula quando o preflight foi bem-sucedido."
    )


class RespostaNovaTentativaIA(BaseModel):
    """Ack da execução correlacionada criada a partir de uma falha de preparação."""

    model_config = ConfigDict(extra="forbid")

    execucao_id: UUID = Field(description="Identificador da execução correlacionada criada.")
    execucao_origem_id: UUID = Field(
        description="Identificador da execução terminal que originou a nova tentativa."
    )


class RespostaProvenienciaContexto(BaseModel):
    """Proveniência do contexto minimizado de um item: o que foi e o que não foi usado."""

    model_config = ConfigDict(extra="forbid")

    elegibilidade_id: UUID = Field(description="Item do público elegível preparado.")
    categorias_usadas: list[str] = Field(
        description="Categorias de dado que chegaram ao contexto do agente redator."
    )
    categorias_nao_usadas: list[str] = Field(
        description="Categorias deliberadamente deixadas de fora do contexto."
    )


class RespostaProveniencias(BaseModel):
    """Proveniência dos contextos já montados de uma execução (PREFL-14)."""

    model_config = ConfigDict(extra="forbid")

    registros: list[RespostaProvenienciaContexto] = Field(
        description="Proveniência de cada item preparado, na ordem em que foi montado."
    )


class ProblemaPreflight(BaseModel):
    """Falha da preparação agêntica, com ocorrência, impacto e próxima ação segura."""

    model_config = ConfigDict(extra="forbid")

    codigo: str = Field(description="Código estável que identifica o tipo da falha.")
    correlacao_id: str = Field(description="Identificador único desta ocorrência de falha.")
    ocorrencia: str = Field(description="O que aconteceu, em português brasileiro.")
    impacto: str = Field(description="Efeito prático da falha para quem solicitou a operação.")
    proxima_acao: str = Field(description="Próxima ação segura recomendada para contornar a falha.")


def problema(
    status: int, codigo: str, ocorrencia: str, impacto: str, proxima_acao: str
) -> JSONResponse:
    """Monta a resposta `problem+json` correlacionada de uma falha de preparação."""

    corpo = ProblemaPreflight(
        codigo=codigo,
        correlacao_id=str(uuid4()),
        ocorrencia=ocorrencia,
        impacto=impacto,
        proxima_acao=proxima_acao,
    )
    return JSONResponse(status_code=status, media_type=TIPO_PROBLEMA, content=corpo.model_dump())


def _hash_requisicao_escopado(identificador_alvo: str, corpo: bytes) -> str:
    """Hash de conteúdo da requisição, escopado pelo identificador do recurso alvo.

    Os dois corpos POST desta rota são vazios (o alvo vem só do caminho), então hashear
    apenas `corpo` produziria o mesmo valor para qualquer execução — a mesma
    `Idempotency-Key` reaproveitada para uma execução diferente devolveria, sem detectar
    nada, a resposta registrada da primeira execução em vez de rejeitar como conflito
    (AD-002). Incluir o identificador do alvo no hash faz o par (chave, alvo diferente)
    divergir do hash já registrado, disparando `ConflitoIdempotencia` (409).
    """

    return sha256(identificador_alvo.encode() + b":" + corpo).hexdigest()


def _problema_execucao_inexistente(execucao_id: str) -> JSONResponse:
    """Resposta idêntica para execução inexistente, em qualquer motivo (AD-011)."""

    return problema(
        404,
        "execucao_inexistente",
        f"A execução '{execucao_id}' não existe.",
        "Nenhuma preparação agêntica foi iniciada.",
        "Consulte a execução pelo identificador UUID retornado pela API.",
    )


def _problema_idempotency_key_ausente() -> JSONResponse:
    """Resposta de requisição mutável sem `Idempotency-Key` (AD-002)."""

    return problema(
        422,
        "idempotency_key_ausente",
        "A requisição não informou o cabeçalho Idempotency-Key.",
        "Nenhuma preparação agêntica foi iniciada.",
        "Repita a requisição incluindo um cabeçalho Idempotency-Key único.",
    )


def _problema_conflito_idempotencia() -> JSONResponse:
    """Resposta de reuso da mesma chave com outro conteúdo de requisição (AD-002)."""

    return problema(
        409,
        "conflito_idempotencia",
        "A chave de idempotência já foi usada com outro conteúdo de requisição.",
        "Nenhuma operação nova foi executada.",
        "Gere uma nova Idempotency-Key para executar outra operação.",
    )


def montar_servico_geracao(configuracao: Configuracao) -> ServicoGeracaoMensagens:
    """Compõe a geração automática do lote a partir da configuração local (GERAR-04)."""

    caminho = configuracao.caminho_banco
    chave = configuracao.chave_openai
    validador = ValidadorSaidaCanal(
        LimitesCanal(
            whatsapp=configuracao.limite_caracteres_whatsapp,
            sms=configuracao.limite_caracteres_sms,
            assunto_email=configuracao.limite_caracteres_assunto_email,
            corpo_email=configuracao.limite_caracteres_corpo_email,
        )
    )
    redator = AgenteRedator(
        validador=validador,
        modelo=configuracao.modelo_openai,
        temperatura=configuracao.temperatura_openai,
        timeout_segundos=configuracao.timeout_openai_segundos,
        chave=chave.get_secret_value() if chave is not None else None,
    )
    critico = AgenteCritico(
        modelo=configuracao.modelo_openai,
        temperatura=configuracao.temperatura_openai,
        timeout_segundos=configuracao.timeout_openai_segundos,
        chave=chave.get_secret_value() if chave is not None else None,
    )
    return ServicoGeracaoMensagens(
        PortasGeracaoMensagens(
            elegibilidades=RepositorioElegibilidades(caminho),
            contextos=RepositorioContextosAgente(caminho),
            mensagens=RepositorioMensagens(caminho),
            avaliacoes=RepositorioAvaliacoesCriticas(caminho),
            excecoes=RepositorioExcecoesOperacionais(caminho),
            execucoes=RepositorioExecucaoPreventiva(caminho),
            grafo=construir_grafo(
                DependenciasGrafo(redator=redator, validador=validador, critico=critico)
            ),
            versao_prompt=configuracao.versao_prompt,
        )
    )


def montar_portas_preflight(configuracao: Configuracao) -> PortasPreflightIA:
    """Compõe as portas reais da preparação agêntica a partir da configuração local.

    `acionar_geracao` liga a geração do lote (3.2) ao único ponto do código que entra em
    `processando_mensagens`, e a dispara como task desacoplada (mesmo padrão de
    `GerenciadorExecucoes`) para que a resposta `202` não espere pelo lote inteiro.
    """

    caminho = configuracao.caminho_banco
    chave = configuracao.chave_openai
    geracao = montar_servico_geracao(configuracao)

    async def acionar_geracao(execucao_id: UUID) -> None:
        """Agenda a geração do lote sem bloquear o ack do preflight."""

        tarefa = asyncio.create_task(geracao.gerar_lote(execucao_id))
        _tarefas_de_geracao.add(tarefa)
        tarefa.add_done_callback(_tarefas_de_geracao.discard)

    return PortasPreflightIA(
        verificador=VerificadorDisponibilidadeOpenAI(
            chave.get_secret_value() if chave is not None else None,
            configuracao.modelo_openai,
            configuracao.timeout_openai_segundos,
            url_modelos=f"{configuracao.url_base_openai}/v1/models",
        ),
        montador=MontadorContextoAgente(),
        execucoes=RepositorioExecucaoPreventiva(caminho),
        excecoes=RepositorioExcecoesOperacionais(caminho),
        elegibilidades=RepositorioElegibilidades(caminho),
        contextos=RepositorioContextosAgente(caminho),
        eventos=RepositorioEventosMeteorologicos(caminho),
        idempotencia=RepositorioIdempotencia(caminho),
        acionar_geracao=acionar_geracao,
    )


def criar_roteador(configuracao: Configuracao) -> APIRouter:
    """Compõe o recurso de preparação agêntica da execução preventiva."""

    roteador = APIRouter(tags=["Preparação da IA"])
    execucoes_repo = RepositorioExecucaoPreventiva(configuracao.caminho_banco)
    contextos_repo = RepositorioContextosAgente(configuracao.caminho_banco)
    servico = ServicoPreflightIA(montar_portas_preflight(configuracao))

    @roteador.post(
        CAMINHO_PREFLIGHT,
        response_model=RespostaPreflight,
        status_code=202,
        summary="Preparar a etapa agêntica de uma execução preventiva",
        description=(
            "Verifica a configuração e a disponibilidade real da OpenAI antes de gerar "
            "qualquer mensagem e, confirmada a disponibilidade, monta o contexto mínimo de "
            "cada item do público elegível e transiciona a execução para "
            "'processando_mensagens'. Indisponibilidade que esgota as tentativas leva a "
            "'falhou_preparacao_ia' com causa sanitizada, sem nenhuma chamada de geração e "
            "sem nenhum conteúdo substituto. Exige o cabeçalho `Idempotency-Key`."
        ),
        responses={
            202: {"description": "Preflight concluído; o corpo informa o estado alcançado."},
            404: {"description": "Execução inexistente.", "model": ProblemaPreflight},
            409: {
                "description": "Execução fora de 'aguardando_geracao' ou conflito de chave.",
                "model": ProblemaPreflight,
            },
            422: {
                "description": "Requisição sem `Idempotency-Key` ou identificador inválido.",
                "model": ProblemaPreflight,
            },
        },
    )
    async def preparar_execucao(  # pyright: ignore[reportUnusedFunction]
        execucao_id: str,
        requisicao: Request,
        idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    ) -> RespostaPreflight | JSONResponse:
        """Traduz `ServicoPreflightIA.preparar` para o contrato REST/JSON público."""

        if idempotency_key is None or not idempotency_key.strip():
            return _problema_idempotency_key_ausente()
        try:
            execucao_uuid = UUID(execucao_id)
        except ValueError:
            return problema(
                422,
                "execucao_id_invalido",
                f"'{execucao_id}' não é um identificador de execução válido.",
                "Nenhuma preparação agêntica foi iniciada.",
                "Repita a requisição com o identificador UUID retornado pela API.",
            )

        snapshot = execucoes_repo.buscar(execucao_uuid)
        if snapshot is None:
            return _problema_execucao_inexistente(execucao_id)

        hash_requisicao = _hash_requisicao_escopado(execucao_id, await requisicao.body())
        try:
            resultado = await servico.preparar(
                execucao_uuid, snapshot.versao, idempotency_key, hash_requisicao
            )
        except EstadoNaoPreparavel as recusa:
            return problema(
                409,
                "estado_nao_preparavel",
                f"A execução '{execucao_id}' está em '{recusa.estado}'.",
                "Nenhuma preparação agêntica foi iniciada.",
                "A preparação agêntica só parte de uma execução em 'aguardando_geracao'.",
            )
        except ConflitoIdempotencia:
            return _problema_conflito_idempotencia()

        return RespostaPreflight(
            execucao_id=resultado.execucao_id,
            estado=str(resultado.estado),
            contextos_montados=resultado.contextos_montados,
            itens_em_excecao=list(resultado.itens_em_excecao),
            causa=resultado.causa,
        )

    @roteador.post(
        CAMINHO_NOVA_TENTATIVA,
        response_model=RespostaNovaTentativaIA,
        status_code=202,
        summary="Solicitar nova tentativa de preparação agêntica",
        description=(
            "Valida a integridade dos snapshots versionados da execução de origem e, "
            "passando, cria uma execução correlacionada nova em 'aguardando_geracao', com "
            "`execucao_origem_id` próprio e uma cópia integral do público elegível da "
            "origem. A execução de origem permanece terminal e nunca é reaberta. Exige o "
            "cabeçalho `Idempotency-Key`."
        ),
        responses={
            202: {"description": "Execução correlacionada criada."},
            404: {"description": "Execução de origem inexistente.", "model": ProblemaPreflight},
            409: {
                "description": "Origem fora de 'falhou_preparacao_ia' ou conflito de chave.",
                "model": ProblemaPreflight,
            },
            422: {
                "description": (
                    "Requisição sem `Idempotency-Key`, identificador inválido ou snapshot "
                    "da origem incompleto."
                ),
                "model": ProblemaPreflight,
            },
        },
    )
    async def solicitar_nova_tentativa_ia(  # pyright: ignore[reportUnusedFunction]
        execucao_origem_id: str,
        requisicao: Request,
        idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    ) -> RespostaNovaTentativaIA | JSONResponse:
        """Traduz `ServicoPreflightIA.solicitar_nova_tentativa` para o contrato público."""

        if idempotency_key is None or not idempotency_key.strip():
            return _problema_idempotency_key_ausente()
        try:
            origem_uuid = UUID(execucao_origem_id)
        except ValueError:
            return problema(
                422,
                "execucao_id_invalido",
                f"'{execucao_origem_id}' não é um identificador de execução válido.",
                "Nenhuma execução nova foi criada.",
                "Repita a requisição com o identificador UUID retornado pela API.",
            )

        if execucoes_repo.buscar(origem_uuid) is None:
            return _problema_execucao_inexistente(execucao_origem_id)

        hash_requisicao = _hash_requisicao_escopado(execucao_origem_id, await requisicao.body())
        try:
            nova_execucao_id = await servico.solicitar_nova_tentativa(
                origem_uuid, idempotency_key, hash_requisicao
            )
        except OrigemNaoRetentavel as recusa:
            return problema(
                409,
                "origem_nao_retentavel",
                f"A execução '{execucao_origem_id}' está em '{recusa.estado}'.",
                "Nenhuma execução nova foi criada.",
                "A nova tentativa só parte de uma execução em 'falhou_preparacao_ia'.",
            )
        except SnapshotInvalido as recusa:
            return problema(
                422,
                "snapshot_invalido",
                f"Os snapshots da execução '{execucao_origem_id}' não passaram na validação: "
                f"{recusa.motivo}.",
                "Nenhuma execução nova foi criada.",
                "Reinicie uma execução preventiva a partir da área monitorada.",
            )
        except ConflitoIdempotencia:
            return _problema_conflito_idempotencia()

        return RespostaNovaTentativaIA(
            execucao_id=nova_execucao_id, execucao_origem_id=origem_uuid
        )

    @roteador.get(
        CAMINHO_PROVENIENCIA,
        response_model=RespostaProveniencias,
        status_code=200,
        summary="Consultar a proveniência dos contextos preparados",
        description=(
            "Devolve, para cada item do público elegível já preparado, quais categorias de "
            "dado foram usadas no contexto do agente redator e quais foram deliberadamente "
            "deixadas de fora. São nomes de categoria, nunca conteúdo: a consulta nunca "
            "expõe documento, dado financeiro, dado de pagamento ou credencial."
        ),
        responses={
            200: {"description": "Proveniência encontrada (pode ser vazia)."},
            404: {"description": "Execução inexistente.", "model": ProblemaPreflight},
            422: {
                "description": "O identificador da execução não é um UUID válido.",
                "model": ProblemaPreflight,
            },
        },
    )
    async def consultar_proveniencia(  # pyright: ignore[reportUnusedFunction]
        execucao_id: str,
    ) -> RespostaProveniencias | JSONResponse:
        """Traduz `RepositorioContextosAgente.listar_por_execucao` para o contrato público."""

        try:
            execucao_uuid = UUID(execucao_id)
        except ValueError:
            return problema(
                422,
                "execucao_id_invalido",
                f"'{execucao_id}' não é um identificador de execução válido.",
                "Nenhuma proveniência pode ser exibida.",
                "Consulte a execução pelo identificador UUID retornado pela API.",
            )

        if execucoes_repo.buscar(execucao_uuid) is None:
            return _problema_execucao_inexistente(execucao_id)

        return RespostaProveniencias(
            registros=[
                RespostaProvenienciaContexto(
                    elegibilidade_id=registro.elegibilidade_id,
                    categorias_usadas=list(registro.categorias_usadas),
                    categorias_nao_usadas=list(registro.categorias_nao_usadas),
                )
                for registro in contextos_repo.listar_por_execucao(execucao_uuid)
            ]
        )

    return roteador
