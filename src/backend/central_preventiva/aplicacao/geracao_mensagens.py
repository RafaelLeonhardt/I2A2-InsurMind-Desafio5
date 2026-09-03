"""Caso de uso da geração e da crítica automáticas do lote (GERAR-04..06, 10..12; CRIT-05..07).

Para cada item incluído do público elegível, cria a mensagem, roda o grafo (geração e, quando
a saída é válida, crítica) e persiste o desfecho. Nenhuma ação humana por mensagem:
`gerar_lote` recebe a execução inteira e percorre o público (GERAR-04).

Três desfechos de geração por item, todos persistidos:

- válida: versão registrada com `valida = true`, mensagem avança `gerando` → `criticando`;
- inválida: versão registrada com `valida = false` e o motivo, mensagem **permanece** em
  `gerando` — a política de nova tentativa é da História 3.4, não desta (GERAR-09);
- transporte esgotado: mensagem vai a `falhou_integracao_ia` com `Exceção` operacional
  registrada, e o restante do lote continua (AD-8).

Uma versão válida segue para a crítica, com quatro desfechos:

- aprovada: avaliação persistida com `aprovada = true`, mensagem avança para
  `aguardando_revisao` (CRIT-05);
- reprovada: avaliação persistida com os motivos categorizados, mensagem **permanece** em
  `criticando`, disponível para a próxima tentativa da História 3.4 (CRIT-06);
- saída do crítico não interpretável: falha da tentativa — nenhuma avaliação persistida,
  nenhuma transição, nunca aprovação (CRIT-07);
- transporte esgotado: mesmo tratamento do redator, `falhou_integracao_ia` com `Exceção`
  operacional registrada, sem terminal novo.

Reinvocar `gerar_lote` para uma execução já processada é no-op: a `UNIQUE
(elegibilidade_id, canal)` recusa a segunda criação, o item é pulado antes de qualquer
chamada à OpenAI e nenhuma mensagem é duplicada nem reavaliada (GERAR-11, GERAR-12, AD-010).
"""

from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

from central_preventiva.adaptadores.persistencia.repositorio_contextos_agente import (
    RegistroContextoAgente,
)
from central_preventiva.adaptadores.persistencia.repositorio_elegibilidade import (
    RegistroElegibilidade,
)
from central_preventiva.adaptadores.persistencia.repositorio_mensagens import (
    MensagemJaExiste,
)
from central_preventiva.aplicacao.grafos.geracao_mensagem import (
    DesfechoCritica,
    DesfechoGeracao,
    EstadoGrafoMensagem,
    ResultadoCritica,
    ResultadoGeracao,
)
from central_preventiva.dominio.avaliacao_critica import MotivoCritica
from central_preventiva.dominio.estados_mensagem import EstadoMensagem
from central_preventiva.dominio.montador_contexto_agente import ContextoAgente
from central_preventiva.dominio.validador_saida_canal import Canal, SaidaCanal

TENTATIVA_INICIAL = 1
"""Toda entrada em `gerando` nesta história é a primeira tentativa (AD-4; 3.4 incrementa)."""

VERSAO_INICIAL_MENSAGEM = 1
"""Versão de concorrência otimista de uma mensagem recém-criada (AD-008)."""

VERSAO_APOS_CRITICANDO = 2
"""Versão da mensagem depois da transição `gerando` → `criticando` (AD-008)."""

IMPACTO_ITEM_SEM_MENSAGEM = (
    "Este item do público elegível não recebe mensagem nesta execução; os demais seguem "
    "normalmente."
)
"""Impacto operacional de um item que não pôde ser gerado (AD-8, exceção isolada)."""


def _causa_contexto_ausente(elegibilidade_id: UUID) -> str:
    """Descreve um item sem contexto mínimo montado (3.1), citando só o identificador."""

    return f"contexto_ausente:{elegibilidade_id}"


def _causa_canal_desconhecido(elegibilidade_id: UUID, canal: str) -> str:
    """Descreve um item cujo canal persistido não é um canal suportado."""

    return f"canal_desconhecido:{elegibilidade_id}:{canal}"


def _causa_integracao(elegibilidade_id: UUID, motivo: str | None) -> str:
    """Descreve a falha de integração de um item, com a causa já sanitizada pelo grafo."""

    return f"falha_integracao_ia:{elegibilidade_id}:{motivo}"


def _causa_integracao_critica(elegibilidade_id: UUID, motivo: str | None) -> str:
    """Descreve a falha de transporte da crítica, distinta da falha da geração."""

    return f"falha_integracao_ia_critica:{elegibilidade_id}:{motivo}"


class _RepositorioElegibilidades(Protocol):
    """Porta mínima do público elegível preservado pela execução (2.5)."""

    def listar_por_execucao(self, execucao_id: UUID) -> list[RegistroElegibilidade]: ...


class _RepositorioContextosAgente(Protocol):
    """Porta mínima do contexto mínimo montado por item (3.1)."""

    def obter_por_elegibilidade(
        self, elegibilidade_id: UUID
    ) -> RegistroContextoAgente | None: ...


class _RepositorioMensagens(Protocol):
    """Porta mínima de `mensagens`/`versoes_mensagem` de que este caso de uso depende."""

    def criar(self, execucao_id: UUID, elegibilidade_id: UUID, canal: Canal) -> UUID: ...

    def salvar_versao(
        self,
        mensagem_id: UUID,
        numero_tentativa: int,
        conteudo: SaidaCanal,
        duracao_ms: float,
        modelo: str,
        versao_prompt: str,
        tokens_entrada: int | None,
        tokens_saida: int | None,
        valida: bool,
        motivo_invalidez: str | None,
    ) -> UUID: ...

    def transicionar(
        self, mensagem_id: UUID, versao_esperada: int, novo_estado: EstadoMensagem
    ) -> None: ...


class _RepositorioAvaliacoesCriticas(Protocol):
    """Porta mínima de `avaliacoes_criticas` de que este caso de uso depende."""

    def salvar(
        self,
        versao_mensagem_id: UUID,
        aprovada: bool,
        motivos: tuple[MotivoCritica, ...],
        modelo: str,
        duracao_ms: float,
    ) -> UUID: ...


class _RepositorioExcecoesOperacionais(Protocol):
    """Porta mínima de registro de `Exceção` operacional sanitizada."""

    def registrar(self, execucao_id: UUID, causa: str, tentativas: int, impacto: str) -> None: ...


class _GrafoGeracao(Protocol):
    """Porta mínima do grafo compilado de geração de uma mensagem."""

    async def ainvoke(self, input: EstadoGrafoMensagem) -> Any: ...  # noqa: A002


@dataclass(frozen=True, slots=True)
class PortasGeracaoMensagens:
    """Agrupa as portas de que a geração do lote depende."""

    elegibilidades: _RepositorioElegibilidades
    contextos: _RepositorioContextosAgente
    mensagens: _RepositorioMensagens
    avaliacoes: _RepositorioAvaliacoesCriticas
    excecoes: _RepositorioExcecoesOperacionais
    grafo: _GrafoGeracao
    versao_prompt: str


class ServicoGeracaoMensagens:
    """Gera automaticamente uma mensagem por item elegível da execução."""

    def __init__(self, portas: PortasGeracaoMensagens) -> None:
        """Guarda as portas de que este caso de uso depende."""

        self._portas = portas

    async def gerar_lote(self, execucao_id: UUID) -> None:
        """Percorre o público elegível da execução e gera a mensagem de cada item.

        Sequencial por decisão de escopo (uma chamada à OpenAI por vez): o conjunto
        sintético da demonstração é pequeno e paralelizar não é exigido por nenhum AC.
        Uma falha isolada de um item nunca interrompe os demais.
        """

        for registro in self._portas.elegibilidades.listar_por_execucao(execucao_id):
            if not registro.elegivel:
                continue
            await self._gerar_item(execucao_id, registro)

    async def _gerar_item(self, execucao_id: UUID, registro: RegistroElegibilidade) -> None:
        """Gera a mensagem de um item, isolando qualquer motivo de exceção só nele."""

        canal = self._canal_de(execucao_id, registro)
        if canal is None:
            return

        contexto = self._portas.contextos.obter_por_elegibilidade(registro.id)
        if contexto is None:
            self._registrar_excecao(execucao_id, _causa_contexto_ausente(registro.id))
            return

        try:
            mensagem_id = self._portas.mensagens.criar(execucao_id, registro.id, canal)
        except MensagemJaExiste:
            return

        resultado, critica = await self._executar_grafo(contexto.contexto, canal)

        if resultado.desfecho is DesfechoGeracao.FALHOU_INTEGRACAO_IA:
            self._registrar_excecao(
                execucao_id, _causa_integracao(registro.id, resultado.motivo)
            )
            self._portas.mensagens.transicionar(
                mensagem_id, VERSAO_INICIAL_MENSAGEM, EstadoMensagem.FALHOU_INTEGRACAO_IA
            )
            return

        versao_id = self._portas.mensagens.salvar_versao(
            mensagem_id=mensagem_id,
            numero_tentativa=TENTATIVA_INICIAL,
            conteudo=resultado.saida if resultado.saida is not None else SaidaCanal(corpo=""),
            duracao_ms=resultado.duracao_ms,
            modelo=resultado.modelo,
            versao_prompt=self._portas.versao_prompt,
            tokens_entrada=resultado.tokens_entrada,
            tokens_saida=resultado.tokens_saida,
            valida=resultado.desfecho is DesfechoGeracao.VALIDA,
            motivo_invalidez=resultado.motivo,
        )

        if resultado.desfecho is not DesfechoGeracao.VALIDA:
            return

        self._portas.mensagens.transicionar(
            mensagem_id, VERSAO_INICIAL_MENSAGEM, EstadoMensagem.CRITICANDO
        )
        if critica is not None:
            self._concluir_critica(execucao_id, registro.id, mensagem_id, versao_id, critica)

    def _concluir_critica(
        self,
        execucao_id: UUID,
        elegibilidade_id: UUID,
        mensagem_id: UUID,
        versao_id: UUID,
        critica: ResultadoCritica,
    ) -> None:
        """Persiste a avaliação e transiciona a mensagem conforme a decisão do crítico.

        Uma saída do crítico não interpretável não persiste avaliação nem transiciona nada
        (CRIT-07): a mensagem fica em `criticando`, disponível para a próxima tentativa da
        História 3.4. Uma reprovação persiste os motivos e também não transiciona: só a
        aprovação avança para `aguardando_revisao` (CRIT-05, CRIT-06).
        """

        if critica.desfecho is DesfechoCritica.FALHOU_INTEGRACAO_IA:
            self._registrar_excecao(
                execucao_id, _causa_integracao_critica(elegibilidade_id, critica.causa)
            )
            self._portas.mensagens.transicionar(
                mensagem_id, VERSAO_APOS_CRITICANDO, EstadoMensagem.FALHOU_INTEGRACAO_IA
            )
            return

        if critica.desfecho is DesfechoCritica.SAIDA_INVALIDA:
            return

        self._portas.avaliacoes.salvar(
            versao_mensagem_id=versao_id,
            aprovada=critica.desfecho is DesfechoCritica.APROVADA,
            motivos=critica.motivos,
            modelo=critica.modelo,
            duracao_ms=critica.duracao_ms,
        )

        if critica.desfecho is DesfechoCritica.APROVADA:
            self._portas.mensagens.transicionar(
                mensagem_id, VERSAO_APOS_CRITICANDO, EstadoMensagem.AGUARDANDO_REVISAO
            )

    async def _executar_grafo(
        self, contexto: ContextoAgente, canal: Canal
    ) -> tuple[ResultadoGeracao, ResultadoCritica | None]:
        """Roda o grafo de uma mensagem e devolve os resultados tipados dos seus nós.

        O resultado da crítica é `None` quando o grafo encerrou em `gerar` — saída inválida
        ou falha de transporte da geração nunca alcançam o nó `criticar` (CRIT-04).
        """

        estado: EstadoGrafoMensagem = {
            "contexto": contexto,
            "canal": canal,
            "tentativa": TENTATIVA_INICIAL,
        }
        final: Any = await self._portas.grafo.ainvoke(estado)
        resultado = final["resultado"]
        assert isinstance(resultado, ResultadoGeracao)
        critica = final.get("resultado_critica")
        assert critica is None or isinstance(critica, ResultadoCritica)
        return resultado, critica

    def _canal_de(self, execucao_id: UUID, registro: RegistroElegibilidade) -> Canal | None:
        """Resolve o canal do snapshot, isolando um canal não suportado como exceção."""

        try:
            return Canal(registro.canal)
        except ValueError:
            self._registrar_excecao(
                execucao_id, _causa_canal_desconhecido(registro.id, registro.canal)
            )
            return None

    def _registrar_excecao(self, execucao_id: UUID, causa: str) -> None:
        """Registra a exceção operacional do item, sempre com o mesmo impacto isolado."""

        self._portas.excecoes.registrar(execucao_id, causa, 1, IMPACTO_ITEM_SEM_MENSAGEM)
