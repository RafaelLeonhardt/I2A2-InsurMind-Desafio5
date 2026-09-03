"""Caso de uso da geração automática de mensagens do lote (GERAR-04..06, 10..12).

Para cada item incluído do público elegível, cria a mensagem, roda o grafo de geração e
persiste o desfecho. Nenhuma ação humana por mensagem: `gerar_lote` recebe a execução inteira
e percorre o público (GERAR-04).

Três desfechos por item, todos persistidos:

- válida: versão registrada com `valida = true`, mensagem avança `gerando` → `criticando`;
- inválida: versão registrada com `valida = false` e o motivo, mensagem **permanece** em
  `gerando` — a política de nova tentativa é da História 3.4, não desta (GERAR-09);
- transporte esgotado: mensagem vai a `falhou_integracao_ia` com `Exceção` operacional
  registrada, e o restante do lote continua (AD-8).

Reinvocar `gerar_lote` para uma execução já processada é no-op: a `UNIQUE
(elegibilidade_id, canal)` recusa a segunda criação, o item é pulado antes de qualquer
chamada à OpenAI e nenhuma mensagem é duplicada (GERAR-11, GERAR-12, AD-010).
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
    DesfechoGeracao,
    EstadoGrafoMensagem,
    ResultadoGeracao,
)
from central_preventiva.dominio.estados_mensagem import EstadoMensagem
from central_preventiva.dominio.montador_contexto_agente import ContextoAgente
from central_preventiva.dominio.validador_saida_canal import Canal, SaidaCanal

TENTATIVA_INICIAL = 1
"""Toda entrada em `gerando` nesta história é a primeira tentativa (AD-4; 3.4 incrementa)."""

VERSAO_INICIAL_MENSAGEM = 1
"""Versão de concorrência otimista de uma mensagem recém-criada (AD-008)."""

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

        resultado = await self._executar_grafo(contexto.contexto, canal)

        if resultado.desfecho is DesfechoGeracao.FALHOU_INTEGRACAO_IA:
            self._registrar_excecao(
                execucao_id, _causa_integracao(registro.id, resultado.motivo)
            )
            self._portas.mensagens.transicionar(
                mensagem_id, VERSAO_INICIAL_MENSAGEM, EstadoMensagem.FALHOU_INTEGRACAO_IA
            )
            return

        self._portas.mensagens.salvar_versao(
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

        if resultado.desfecho is DesfechoGeracao.VALIDA:
            self._portas.mensagens.transicionar(
                mensagem_id, VERSAO_INICIAL_MENSAGEM, EstadoMensagem.CRITICANDO
            )

    async def _executar_grafo(self, contexto: ContextoAgente, canal: Canal) -> ResultadoGeracao:
        """Roda o grafo de uma mensagem e devolve o resultado tipado do nó `gerar`."""

        estado: EstadoGrafoMensagem = {
            "contexto": contexto,
            "canal": canal,
            "tentativa": TENTATIVA_INICIAL,
        }
        final: Any = await self._portas.grafo.ainvoke(estado)
        resultado = final["resultado"]
        assert isinstance(resultado, ResultadoGeracao)
        return resultado

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
