"""Grafo LangGraph de geração de uma mensagem: o nó `gerar` (GERAR-05, GERAR-09).

Um grafo por mensagem, não um grafo por lote: o AD-4 declara que cada mensagem tem seu
próprio estado de geração, crítica, revisão e simulação, então cada execução de grafo é
isolada e pequena. Esta história implementa só o nó `gerar`; `criticar` e revisão chegam em
3.3+ estendendo este mesmo grafo.

O nó encadeia três decisões, nesta ordem: chamar o redator sob a política única de tentativas
(`RetryComBackoff`), classificar a saída pelo validador determinístico e devolver o desfecho.
Ele nunca transiciona estado nem escreve no banco — quem persiste é `ServicoGeracaoMensagens`.
"""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import StrEnum
from time import perf_counter
from typing import NotRequired, Protocol, TypedDict

from langgraph.graph import END, START, StateGraph  # pyright: ignore[reportMissingTypeStubs]
from langgraph.graph.state import (  # pyright: ignore[reportMissingTypeStubs]
    CompiledStateGraph,
)

from central_preventiva.adaptadores.ia.agente_redator import RespostaRedator
from central_preventiva.aplicacao._retry import (
    MAXIMO_TENTATIVAS,
    RetryComBackoff,
    Tentativa,
    TentativasEsgotadas,
)
from central_preventiva.dominio.montador_contexto_agente import ContextoAgente
from central_preventiva.dominio.validador_saida_canal import (
    Canal,
    SaidaCanal,
    ValidadorSaidaCanal,
)

MENSAGEM_GERACAO_ESGOTADA = (
    f"Esgotadas {MAXIMO_TENTATIVAS} tentativas de chamada de geração à OpenAI."
)

CAUSA_TRANSPORTE_SEM_DETALHE = "A chamada de geração à OpenAI não foi concluída."
"""Causa registrada quando o esgotamento não carrega nenhum erro reconhecido."""


class DesfechoGeracao(StrEnum):
    """Os três desfechos possíveis do nó `gerar`, antes de qualquer persistência."""

    VALIDA = "valida"
    INVALIDA = "invalida"
    FALHOU_INTEGRACAO_IA = "falhou_integracao_ia"


@dataclass(frozen=True, slots=True)
class ResultadoGeracao:
    """Desfecho de uma execução do nó `gerar`, com tudo que a versão precisa registrar."""

    desfecho: DesfechoGeracao
    saida: SaidaCanal | None
    motivo: str | None
    duracao_ms: float
    modelo: str
    tokens_entrada: int | None
    tokens_saida: int | None


class EstadoGrafoMensagem(TypedDict):
    """Cópia de trabalho tipada do grafo de uma mensagem (AD-4)."""

    contexto: ContextoAgente
    canal: Canal
    tentativa: int
    resultado: NotRequired[ResultadoGeracao]


class AtualizacaoGrafoMensagem(TypedDict):
    """Atualização parcial que o nó `gerar` devolve ao grafo."""

    resultado: ResultadoGeracao


class _Redator(Protocol):
    """Porta mínima do agente redator de que o nó `gerar` depende."""

    @property
    def modelo(self) -> str: ...

    async def gerar(self, contexto: ContextoAgente, canal: Canal) -> RespostaRedator: ...


@dataclass(frozen=True, slots=True)
class DependenciasGrafo:
    """Dependências injetadas na construção do grafo de geração."""

    redator: _Redator
    validador: ValidadorSaidaCanal
    esperar: Callable[[float], Awaitable[None]] = asyncio.sleep


def _causa_de(falha: TentativasEsgotadas) -> str:
    """Descreve o esgotamento citando o tipo do erro, nunca conteúdo nem credencial (AD-10)."""

    erro = falha.ultimo_erro
    if erro is None:
        return CAUSA_TRANSPORTE_SEM_DETALHE
    return f"{type(erro).__name__}: {erro}"


type GrafoMensagemCompilado = CompiledStateGraph[
    EstadoGrafoMensagem, None, EstadoGrafoMensagem, EstadoGrafoMensagem
]
"""Grafo já compilado de uma mensagem, pronto para `ainvoke`."""


def construir_grafo(dependencias: DependenciasGrafo) -> GrafoMensagemCompilado:
    """Compila o grafo de uma mensagem: `START → gerar → END`.

    O nó `gerar` nunca levanta exceção de transporte: o esgotamento das tentativas vira o
    desfecho `falhou_integracao_ia`, e a saída recebida vira `valida` ou `invalida` conforme
    o veredito determinístico do validador.
    """

    async def gerar(state: EstadoGrafoMensagem) -> AtualizacaoGrafoMensagem:
        """Chama o redator com retry e classifica a saída pelo validador."""

        canal = state["canal"]
        inicio = perf_counter()

        def ignorar(_: Tentativa[RespostaRedator]) -> None:
            """As tentativas de transporte não têm tabela própria nesta história."""

        retry: RetryComBackoff[RespostaRedator] = RetryComBackoff(
            operacao=lambda: dependencias.redator.gerar(state["contexto"], canal),
            aceitar=lambda _: True,
            registrar=ignorar,
            mensagem_esgotamento=MENSAGEM_GERACAO_ESGOTADA,
            erros_reconhecidos=(Exception,),
            esperar=dependencias.esperar,
        )

        try:
            resposta = await retry.executar()
        except TentativasEsgotadas as falha:
            return {
                "resultado": ResultadoGeracao(
                    desfecho=DesfechoGeracao.FALHOU_INTEGRACAO_IA,
                    saida=None,
                    motivo=_causa_de(falha),
                    duracao_ms=(perf_counter() - inicio) * 1000,
                    modelo=dependencias.redator.modelo,
                    tokens_entrada=None,
                    tokens_saida=None,
                )
            }

        veredito = dependencias.validador.validar(canal, resposta.saida)
        return {
            "resultado": ResultadoGeracao(
                desfecho=DesfechoGeracao.VALIDA if veredito.valida else DesfechoGeracao.INVALIDA,
                saida=resposta.saida,
                motivo=veredito.motivo,
                duracao_ms=(perf_counter() - inicio) * 1000,
                modelo=dependencias.redator.modelo,
                tokens_entrada=resposta.tokens_entrada,
                tokens_saida=resposta.tokens_saida,
            )
        }

    grafo = StateGraph(EstadoGrafoMensagem)
    grafo.add_node("gerar", gerar)  # pyright: ignore[reportUnknownMemberType]
    grafo.add_edge(START, "gerar")
    grafo.add_edge("gerar", END)
    return grafo.compile()  # pyright: ignore[reportUnknownMemberType]
