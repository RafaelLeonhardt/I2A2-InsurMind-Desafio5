"""Caso de uso da preparação agêntica: preflight de disponibilidade e nova tentativa.

Orquestra, para uma execução parada em `aguardando_geracao` (2.6): verificação real de
disponibilidade da OpenAI com a política única de retry (AD-8), montagem do contexto mínimo
por item elegível e transição de estado. Nenhuma chamada de geração acontece aqui — esta
história só prepara e valida o terreno (PREFL-03).

SPEC_DEVIATION: o design escreve `preparar(execucao_id, versao_esperada)`. A assinatura
implementada acrescenta `chave_idempotencia` e `hash_requisicao`, porque o AD-002 exige
`Idempotency-Key` em todo `POST` mutável e o T8 exige que repetir a chave devolva a resposta
registrada sem novo preflight. Isso precisa ser decidido onde o efeito acontece, no mesmo
padrão já usado por `ServicoColetaMeteorologica` (2.2).
"""

import asyncio
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Protocol, cast
from uuid import UUID

from central_preventiva.adaptadores.ia.verificador_disponibilidade_openai import (
    ResultadoDisponibilidade,
)
from central_preventiva.adaptadores.persistencia.repositorio_contextos_agente import (
    RegistroContextoAgente,
)
from central_preventiva.adaptadores.persistencia.repositorio_elegibilidade import (
    ContagemElegibilidade,
    RegistroElegibilidade,
)
from central_preventiva.adaptadores.persistencia.repositorio_execucao_preventiva import (
    SnapshotExecucao,
)
from central_preventiva.aplicacao._retry import (
    MAXIMO_TENTATIVAS,
    RetryComBackoff,
    Tentativa,
    TentativasEsgotadas,
)
from central_preventiva.aplicacao.portas_persistencia import (
    ConflitoIdempotencia,
    PortaIdempotencia,
)
from central_preventiva.dominio.avaliador_elegibilidade import (
    MOTIVO_INCLUIDO,
    ResultadoElegibilidade,
)
from central_preventiva.dominio.estados_execucao import EstadoExecucao
from central_preventiva.dominio.evento_meteorologico import EventoMeteorologico
from central_preventiva.dominio.montador_contexto_agente import (
    CATEGORIAS_NAO_UTILIZADAS,
    CATEGORIAS_UTILIZADAS,
    ContextoAgente,
    ErroContexto,
    MontadorContextoAgente,
)

OPERACAO_PREFLIGHT = "preparar_producao_agentica"
"""Escopo do preflight no armazenamento genérico de chaves de idempotência (AD-002)."""

OPERACAO_NOVA_TENTATIVA_IA = "solicitar_nova_tentativa_ia"
"""Escopo da nova tentativa após `falhou_preparacao_ia` (PREFL-09, AD-002)."""

STATUS_PREFLIGHT_ACEITO = 202
"""Status registrado para o ack de um preflight aceito."""

MENSAGEM_PREFLIGHT_ESGOTADO = (
    f"Esgotadas {MAXIMO_TENTATIVAS} tentativas de preflight de disponibilidade da OpenAI."
)

IMPACTO_PREPARACAO_IA = (
    "Nenhuma mensagem preventiva é gerada nesta execução; a coleta, a avaliação de risco e "
    "o público elegível já produzidos permanecem consultáveis."
)
"""Impacto operacional de toda execução que termina em `falhou_preparacao_ia` (PREFL-04)."""

IMPACTO_ITEM_SEM_CONTEXTO = (
    "Este item do público elegível não recebe mensagem nesta execução; os demais seguem "
    "normalmente."
)
"""Impacto operacional de um item cujo contexto não pôde ser montado (PREFL-15)."""

CAUSA_INDISPONIVEL_SEM_DETALHE = "A OpenAI permaneceu indisponível durante o preflight."
"""Causa registrada quando o verificador não devolveu nenhuma causa própria."""

MARCO_PREPARACAO_CONCLUIDA = "preparacao_ia_concluida"
"""Marco de sucesso do preflight, correlacionado à execução (RUNNER-02)."""

MARCO_FALHOU_PREPARACAO_IA = "falhou_preparacao_ia"
"""Marco do bloqueio de preparação: carrega a causa sanitizada que a interface explica
a Marina (PREFL-17). É o que torna a causa consultável depois, sem que nenhuma tela
precise inventar um texto substituto (PREFL-16)."""


def _causa_item(erro: ErroContexto) -> str:
    """Descreve a inconsistência de um item citando o campo, nunca o valor recusado."""

    return f"contexto_invalido:{erro.elegibilidade_id}:{erro.campo}"


def _causa_evento_ausente(registro: RegistroElegibilidade) -> str:
    """Descreve um item cujo evento de referência não existe mais."""

    return f"evento_inexistente:{registro.id}:{registro.evento_id}"


class ExecucaoInexistente(RuntimeError):
    """Indica que o `execucao_id` informado não corresponde a nenhuma execução."""

    def __init__(self, execucao_id: UUID) -> None:
        """Identifica a execução ausente e monta a mensagem em português."""

        super().__init__(f"A execução '{execucao_id}' não existe.")
        self.execucao_id = execucao_id


class EstadoNaoPreparavel(RuntimeError):
    """Indica preflight solicitado para uma execução fora de `aguardando_geracao`."""

    def __init__(self, execucao_id: UUID, estado: EstadoExecucao) -> None:
        """Identifica a execução e o estado que impede o preflight."""

        super().__init__(
            f"A execução '{execucao_id}' está em '{estado}' e não pode ter a etapa "
            "agêntica preparada."
        )
        self.execucao_id = execucao_id
        self.estado = estado


class OrigemNaoRetentavel(RuntimeError):
    """Indica nova tentativa pedida a partir de uma execução que não falhou na preparação."""

    def __init__(self, execucao_id: UUID, estado: EstadoExecucao) -> None:
        """Identifica a execução de origem e seu estado atual."""

        super().__init__(
            f"A execução '{execucao_id}' está em '{estado}'; a nova tentativa de preparação "
            "só parte de 'falhou_preparacao_ia'."
        )
        self.execucao_id = execucao_id
        self.estado = estado


class SnapshotInvalido(RuntimeError):
    """Indica snapshot incompleto, corrompido ou em versão não suportada (PREFL-07/08)."""

    def __init__(self, execucao_origem_id: UUID, motivo: str) -> None:
        """Identifica a origem e o motivo da recusa, sem citar conteúdo do snapshot."""

        super().__init__(
            f"Os snapshots da execução '{execucao_origem_id}' não passaram na validação: "
            f"{motivo}. Nenhuma execução nova foi criada."
        )
        self.execucao_origem_id = execucao_origem_id
        self.motivo = motivo


@dataclass(frozen=True, slots=True)
class ResultadoPreflight:
    """Desfecho do preflight de uma execução: estado alcançado e o que foi preparado."""

    execucao_id: UUID
    estado: EstadoExecucao
    contextos_montados: int
    itens_em_excecao: tuple[UUID, ...]
    causa: str | None


class _RepositorioExecucaoPreventiva(Protocol):
    """Porta mínima de `execucao_preventiva` de que este caso de uso depende."""

    def buscar(self, execucao_id: UUID) -> SnapshotExecucao | None:
        """Lê o estado, a versão e a origem correlacionada da execução, ou `None`."""
        ...

    def transicionar(
        self, execucao_id: UUID, versao_esperada: int, novo_estado: EstadoExecucao
    ) -> None:
        """Transiciona a execução sob checagem otimista de versão (AD-008)."""
        ...

    def registrar_marco(self, execucao_id: UUID, marco: str, causa: str | None = None) -> None:
        """Persiste um marco de transição correlacionado à execução (RUNNER-02)."""
        ...

    def criar_correlacionada(
        self,
        estado_inicial: EstadoExecucao,
        execucao_origem_id: UUID,
        apos_criar: Callable[[Any, UUID], None] | None = None,
    ) -> UUID:
        """Cria a execução correlacionada, executando `apos_criar` na mesma transação."""
        ...


class _RepositorioExcecoesOperacionais(Protocol):
    """Porta mínima de registro de `Exceção` operacional sanitizada."""

    def registrar(self, execucao_id: UUID, causa: str, tentativas: int, impacto: str) -> None:
        """Persiste a exceção operacional correlacionada à execução."""
        ...


class _RepositorioElegibilidades(Protocol):
    """Porta mínima do público elegível preservado pela execução (2.5)."""

    def listar_por_execucao(self, execucao_id: UUID) -> list[RegistroElegibilidade]:
        """Lista os resultados de elegibilidade já persistidos da execução."""
        ...

    def contar_por_execucao(self, execucao_id: UUID) -> ContagemElegibilidade:
        """Conta incluídos e excluídos já persistidos da execução."""
        ...

    def copiar_para_execucao(
        self,
        execucao_origem_id: UUID,
        nova_execucao_id: UUID,
        conexao: Any = None,
    ) -> int:
        """Copia as elegibilidades da origem para a nova execução (AD-012)."""
        ...


class _RepositorioContextosAgente(Protocol):
    """Porta mínima de persistência do contexto mínimo e da sua proveniência."""

    def salvar(
        self,
        execucao_id: UUID,
        elegibilidade_id: UUID,
        contexto: ContextoAgente,
        categorias_usadas: tuple[str, ...],
        categorias_nao_usadas: tuple[str, ...],
    ) -> UUID:
        """Persiste o contexto do item e a proveniência do que foi e não foi usado."""
        ...

    def listar_por_execucao(self, execucao_id: UUID) -> list[RegistroContextoAgente]:
        """Lista os contextos já montados da execução."""
        ...


class _RepositorioEventos(Protocol):
    """Porta mínima de resolução do evento meteorológico referenciado pelo snapshot."""

    def buscar_por_id(self, id: UUID) -> EventoMeteorologico | None:
        """Resolve o evento pelo identificador, ou `None` se ele não existir."""
        ...


class _VerificadorDisponibilidade(Protocol):
    """Porta da verificação real de disponibilidade da OpenAI."""

    async def verificar(self) -> ResultadoDisponibilidade:
        """Executa uma tentativa de verificação e classifica o resultado."""
        ...


@dataclass(frozen=True, slots=True)
class PortasPreflightIA:
    """Agrupa as portas de que o caso de uso da preparação agêntica depende."""

    verificador: _VerificadorDisponibilidade
    montador: MontadorContextoAgente
    execucoes: _RepositorioExecucaoPreventiva
    excecoes: _RepositorioExcecoesOperacionais
    elegibilidades: _RepositorioElegibilidades
    contextos: _RepositorioContextosAgente
    eventos: _RepositorioEventos
    idempotencia: PortaIdempotencia
    esperar: Callable[[float], Awaitable[None]] = asyncio.sleep


def _serializar_preflight(resultado: ResultadoPreflight) -> str:
    """Serializa o desfecho do preflight para o corpo guardado na chave idempotente."""

    return json.dumps(
        {
            "execucao_id": str(resultado.execucao_id),
            "estado": str(resultado.estado),
            "contextos_montados": resultado.contextos_montados,
            "itens_em_excecao": [str(item) for item in resultado.itens_em_excecao],
            "causa": resultado.causa,
        }
    )


def _desserializar_preflight(corpo: str) -> ResultadoPreflight:
    """Reconstrói o desfecho do preflight previamente registrado, sem refazer nada."""

    dados = cast(dict[str, Any], json.loads(corpo))
    return ResultadoPreflight(
        execucao_id=UUID(str(dados["execucao_id"])),
        estado=EstadoExecucao(str(dados["estado"])),
        contextos_montados=int(dados["contextos_montados"]),
        itens_em_excecao=tuple(UUID(str(item)) for item in dados["itens_em_excecao"]),
        causa=None if dados["causa"] is None else str(dados["causa"]),
    )


def _resultado_de(registro: RegistroElegibilidade) -> ResultadoElegibilidade:
    """Reconstrói o resultado de elegibilidade a partir da linha já persistida (2.5).

    `motivo` não é uma coluna de `elegibilidades_historicas`: só itens incluídos chegam
    aqui, e o motivo de um incluído é sempre `incluido`. O montador lê apenas `criterios`
    e `canal`, os dois campos que o snapshot preserva integralmente.
    """

    return ResultadoElegibilidade(
        elegivel=registro.elegivel,
        criterios=registro.criterios,
        canal=registro.canal,
        motivo=MOTIVO_INCLUIDO,
        justificativa=registro.justificativa,
    )


class ServicoPreflightIA:
    """Prepara a produção agêntica de uma execução e trata a nova tentativa correlacionada."""

    def __init__(self, portas: PortasPreflightIA) -> None:
        """Guarda as portas de que este caso de uso depende."""

        self._portas = portas

    async def preparar(
        self,
        execucao_id: UUID,
        versao_esperada: int,
        chave_idempotencia: str,
        hash_requisicao: str,
    ) -> ResultadoPreflight:
        """Verifica a disponibilidade da OpenAI e monta o contexto mínimo do público.

        Só uma execução em `aguardando_geracao` é preparável (PREFL-01). Disponibilidade
        confirmada transiciona para `processando_mensagens` (PREFL-02); indisponibilidade
        que esgota as tentativas transiciona para `falhou_preparacao_ia` com exceção
        sanitizada, sem nenhuma chamada de geração (PREFL-03, PREFL-04). Repetir a mesma
        chave idempotente devolve a resposta registrada, sem refazer o preflight (AD-002).
        """

        registrada = self._portas.idempotencia.buscar(chave_idempotencia, OPERACAO_PREFLIGHT)
        if registrada is not None:
            if registrada.hash_requisicao != hash_requisicao:
                raise ConflitoIdempotencia(chave=chave_idempotencia, operacao=OPERACAO_PREFLIGHT)
            return _desserializar_preflight(registrada.corpo)

        resultado = await self._preparar_agora(execucao_id, versao_esperada)
        self._portas.idempotencia.registrar(
            chave_idempotencia,
            OPERACAO_PREFLIGHT,
            hash_requisicao,
            STATUS_PREFLIGHT_ACEITO,
            _serializar_preflight(resultado),
        )
        return resultado

    async def solicitar_nova_tentativa(
        self, execucao_origem_id: UUID, chave_idempotencia: str, hash_requisicao: str
    ) -> UUID:
        """Cria uma execução correlacionada nova a partir de `falhou_preparacao_ia`.

        Valida antes a integridade dos snapshots da origem e rejeita sem criar nada se a
        validação falhar (PREFL-07, PREFL-08). Passando, cria a execução em
        `aguardando_geracao` com `execucao_origem_id` próprio e copia, na mesma transação,
        todas as elegibilidades da origem — incluídas e excluídas (AD-012). A origem
        permanece terminal, nunca é reaberta (AD-009), e repetir a chave idempotente
        devolve o mesmo `execucao_id` sem criar uma segunda execução (PREFL-09).
        """

        registrada = self._portas.idempotencia.buscar(
            chave_idempotencia, OPERACAO_NOVA_TENTATIVA_IA
        )
        if registrada is not None:
            if registrada.hash_requisicao != hash_requisicao:
                raise ConflitoIdempotencia(
                    chave=chave_idempotencia, operacao=OPERACAO_NOVA_TENTATIVA_IA
                )
            return UUID(str(cast(dict[str, Any], json.loads(registrada.corpo))["execucao_id"]))

        origem = self._portas.execucoes.buscar(execucao_origem_id)
        if origem is None:
            raise ExecucaoInexistente(execucao_origem_id)
        if origem.estado != EstadoExecucao.FALHOU_PREPARACAO_IA:
            raise OrigemNaoRetentavel(execucao_origem_id, origem.estado)

        self._validar_snapshots(execucao_origem_id)

        def copiar_elegibilidades(conexao: Any, nova_execucao_id: UUID) -> None:
            self._portas.elegibilidades.copiar_para_execucao(
                execucao_origem_id, nova_execucao_id, conexao
            )

        nova_execucao_id = self._portas.execucoes.criar_correlacionada(
            EstadoExecucao.AGUARDANDO_GERACAO, execucao_origem_id, copiar_elegibilidades
        )
        self._portas.idempotencia.registrar(
            chave_idempotencia,
            OPERACAO_NOVA_TENTATIVA_IA,
            hash_requisicao,
            STATUS_PREFLIGHT_ACEITO,
            json.dumps({"execucao_id": str(nova_execucao_id)}),
        )
        return nova_execucao_id

    async def _preparar_agora(
        self, execucao_id: UUID, versao_esperada: int
    ) -> ResultadoPreflight:
        """Executa o preflight de fato, já resolvida a idempotência do comando."""

        snapshot = self._portas.execucoes.buscar(execucao_id)
        if snapshot is None:
            raise ExecucaoInexistente(execucao_id)
        if snapshot.estado == EstadoExecucao.PROCESSANDO_MENSAGENS:
            return ResultadoPreflight(
                execucao_id=execucao_id,
                estado=snapshot.estado,
                contextos_montados=len(self._portas.contextos.listar_por_execucao(execucao_id)),
                itens_em_excecao=(),
                causa=None,
            )
        if snapshot.estado != EstadoExecucao.AGUARDANDO_GERACAO:
            raise EstadoNaoPreparavel(execucao_id, snapshot.estado)

        causa_indisponibilidade = await self._verificar_disponibilidade()
        if causa_indisponibilidade is not None:
            self._portas.execucoes.transicionar(
                execucao_id, versao_esperada, EstadoExecucao.FALHOU_PREPARACAO_IA
            )
            self._portas.excecoes.registrar(
                execucao_id, causa_indisponibilidade, MAXIMO_TENTATIVAS, IMPACTO_PREPARACAO_IA
            )
            self._portas.execucoes.registrar_marco(
                execucao_id, MARCO_FALHOU_PREPARACAO_IA, causa_indisponibilidade
            )
            return ResultadoPreflight(
                execucao_id=execucao_id,
                estado=EstadoExecucao.FALHOU_PREPARACAO_IA,
                contextos_montados=0,
                itens_em_excecao=(),
                causa=causa_indisponibilidade,
            )

        montados, em_excecao = self._montar_contextos(execucao_id)
        self._portas.execucoes.transicionar(
            execucao_id, versao_esperada, EstadoExecucao.PROCESSANDO_MENSAGENS
        )
        self._portas.execucoes.registrar_marco(execucao_id, MARCO_PREPARACAO_CONCLUIDA)
        return ResultadoPreflight(
            execucao_id=execucao_id,
            estado=EstadoExecucao.PROCESSANDO_MENSAGENS,
            contextos_montados=montados,
            itens_em_excecao=em_excecao,
            causa=None,
        )

    async def _verificar_disponibilidade(self) -> str | None:
        """Devolve `None` se a OpenAI respondeu disponível, ou a causa sanitizada da falha.

        Aplica a política única de tentativas de `aplicacao/_retry.py`: uma indisponibilidade
        momentânea não condena a execução, e uma persistente termina em causa explícita.
        """

        def ignorar(_: Tentativa[ResultadoDisponibilidade]) -> None:
            """O preflight não tem tabela de tentativas própria; o registro é a `Exceção`."""

        retry: RetryComBackoff[ResultadoDisponibilidade] = RetryComBackoff(
            operacao=self._portas.verificador.verificar,
            aceitar=lambda resultado: resultado.disponivel,
            registrar=ignorar,
            mensagem_esgotamento=MENSAGEM_PREFLIGHT_ESGOTADO,
            esperar=self._portas.esperar,
        )
        try:
            await retry.executar()
        except TentativasEsgotadas as falha:
            ultimo = cast(ResultadoDisponibilidade | None, falha.ultimo_valor)
            if ultimo is not None and ultimo.causa is not None:
                return ultimo.causa
            return CAUSA_INDISPONIVEL_SEM_DETALHE
        return None

    def _montar_contextos(self, execucao_id: UUID) -> tuple[int, tuple[UUID, ...]]:
        """Monta e persiste o contexto mínimo de cada item incluído do público elegível.

        Um item inconsistente registra sua própria `Exceção` e é reportado em
        `itens_em_excecao`, sem interromper os demais (PREFL-15). Nenhuma solicitação parcial
        chega à OpenAI: nada é enviado nesta etapa, a disponibilidade já foi confirmada antes.
        """

        eventos: dict[UUID, EventoMeteorologico | None] = {}
        montados = 0
        em_excecao: list[UUID] = []

        for registro in self._portas.elegibilidades.listar_por_execucao(execucao_id):
            if not registro.elegivel:
                continue
            if registro.evento_id not in eventos:
                eventos[registro.evento_id] = self._portas.eventos.buscar_por_id(
                    registro.evento_id
                )
            evento = eventos[registro.evento_id]
            if evento is None:
                self._portas.excecoes.registrar(
                    execucao_id, _causa_evento_ausente(registro), 1, IMPACTO_ITEM_SEM_CONTEXTO
                )
                em_excecao.append(registro.id)
                continue

            resultado = self._portas.montador.montar(
                registro.id, _resultado_de(registro), evento
            )
            if isinstance(resultado, ErroContexto):
                self._portas.excecoes.registrar(
                    execucao_id, _causa_item(resultado), 1, IMPACTO_ITEM_SEM_CONTEXTO
                )
                em_excecao.append(registro.id)
                continue

            self._portas.contextos.salvar(
                execucao_id,
                registro.id,
                resultado,
                CATEGORIAS_UTILIZADAS,
                CATEGORIAS_NAO_UTILIZADAS,
            )
            montados += 1

        return montados, tuple(em_excecao)

    def _validar_snapshots(self, execucao_origem_id: UUID) -> None:
        """Recusa a nova tentativa se algum snapshot da origem estiver incompleto (PREFL-07).

        Verifica, antes de criar qualquer registro: que a origem preservou público, que toda
        linha resolve sua regra versionada, que a versão de regra é suportada, que os
        critérios e o canal do snapshot estão preenchidos, e que o evento referenciado ainda
        existe.
        """

        contagem = self._portas.elegibilidades.contar_por_execucao(execucao_origem_id)
        total = contagem.incluidos + contagem.excluidos
        if total == 0:
            raise SnapshotInvalido(
                execucao_origem_id, "a execução de origem não preservou nenhuma elegibilidade"
            )

        registros = self._portas.elegibilidades.listar_por_execucao(execucao_origem_id)
        if len(registros) != total:
            raise SnapshotInvalido(
                execucao_origem_id, "há elegibilidade sem a regra versionada de referência"
            )

        for registro in registros:
            if registro.regra_versao < 1:
                raise SnapshotInvalido(
                    execucao_origem_id, "há elegibilidade com versão de regra não suportada"
                )
            if not registro.criterios:
                raise SnapshotInvalido(
                    execucao_origem_id, "há elegibilidade sem snapshot de critérios"
                )
            if not registro.canal.strip() or not registro.nome_segurado.strip():
                raise SnapshotInvalido(
                    execucao_origem_id, "há elegibilidade com snapshot incompleto"
                )
            if self._portas.eventos.buscar_por_id(registro.evento_id) is None:
                raise SnapshotInvalido(
                    execucao_origem_id, "há elegibilidade cujo evento de referência não existe"
                )
