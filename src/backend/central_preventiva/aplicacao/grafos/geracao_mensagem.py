"""Grafo LangGraph de uma mensagem: os nós `gerar` (3.2) e `criticar` (3.3).

Um grafo por mensagem, não um grafo por lote: o AD-4 declara que cada mensagem tem seu
próprio estado de geração, crítica, revisão e simulação, então cada execução de grafo é
isolada e pequena. A revisão humana (3.5) chega depois, estendendo este mesmo grafo.

O nó `gerar` encadeia três decisões, nesta ordem: chamar o redator sob a política única de
tentativas (`RetryComBackoff`), classificar a saída pelo validador determinístico e devolver o
desfecho. O nó `criticar` só é alcançado quando esse desfecho é `valida`: a aresta condicional
depois de `gerar` é o que garante, por construção, que uma mensagem já reprovada
deterministicamente por 3.2 nunca chegue ao crítico e que o modelo não tenha como sobrepor a
validação objetiva (CRIT-04).

Nenhum dos dois nós transiciona estado nem escreve no banco — quem persiste é
`ServicoGeracaoMensagens`.
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
from central_preventiva.dominio.avaliacao_critica import AvaliacaoCritica, MotivoCritica
from central_preventiva.dominio.montador_contexto_agente import ContextoAgente
from central_preventiva.dominio.validador_saida_canal import (
    Canal,
    SaidaCanal,
    ValidadorSaidaCanal,
)

MENSAGEM_GERACAO_ESGOTADA = (
    f"Esgotadas {MAXIMO_TENTATIVAS} tentativas de chamada de geração à OpenAI."
)

MENSAGEM_CRITICA_ESGOTADA = (
    f"Esgotadas {MAXIMO_TENTATIVAS} tentativas de chamada de crítica à OpenAI."
)

CAUSA_TRANSPORTE_SEM_DETALHE = "A chamada de geração à OpenAI não foi concluída."
"""Causa registrada quando o esgotamento não carrega nenhum erro reconhecido."""

CAUSA_SAIDA_CRITICA_INVALIDA = "saida_critica_invalida"
"""Causa registrada quando o crítico responde algo não interpretável com segurança."""


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


class DesfechoCritica(StrEnum):
    """Os quatro desfechos possíveis do nó `criticar`, antes de qualquer persistência."""

    APROVADA = "aprovada"
    REPROVADA = "reprovada"
    SAIDA_INVALIDA = "saida_invalida"
    FALHOU_INTEGRACAO_IA = "falhou_integracao_ia"


@dataclass(frozen=True, slots=True)
class ResultadoCritica:
    """Desfecho de uma execução do nó `criticar`, com o que a avaliação precisa registrar.

    `SAIDA_INVALIDA` é falha da tentativa, não aprovação e não reprovação estruturada
    (CRIT-07): nada é persistido em `avaliacoes_criticas` e a mensagem segue disponível para
    a próxima tentativa (3.4).
    """

    desfecho: DesfechoCritica
    motivos: tuple[MotivoCritica, ...]
    causa: str | None
    duracao_ms: float
    modelo: str


class EstadoGrafoMensagem(TypedDict):
    """Cópia de trabalho tipada do grafo de uma mensagem (AD-4)."""

    contexto: ContextoAgente
    canal: Canal
    tentativa: int
    resultado: NotRequired[ResultadoGeracao]
    resultado_critica: NotRequired[ResultadoCritica]


class AtualizacaoGrafoMensagem(TypedDict):
    """Atualização parcial que o nó `gerar` devolve ao grafo."""

    resultado: ResultadoGeracao


class AtualizacaoCriticaMensagem(TypedDict):
    """Atualização parcial que o nó `criticar` devolve ao grafo."""

    resultado_critica: ResultadoCritica


class _Redator(Protocol):
    """Porta mínima do agente redator de que o nó `gerar` depende."""

    @property
    def modelo(self) -> str: ...

    async def gerar(self, contexto: ContextoAgente, canal: Canal) -> RespostaRedator: ...


class _Critico(Protocol):
    """Porta mínima do agente crítico de que o nó `criticar` depende."""

    @property
    def modelo(self) -> str: ...

    async def avaliar(
        self, conteudo: SaidaCanal, canal: Canal, contexto: ContextoAgente
    ) -> AvaliacaoCritica | None: ...


@dataclass(frozen=True, slots=True)
class DependenciasGrafo:
    """Dependências injetadas na construção do grafo de uma mensagem."""

    redator: _Redator
    validador: ValidadorSaidaCanal
    critico: _Critico
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
    """Compila o grafo de uma mensagem: `START → gerar → criticar? → END`.

    O nó `gerar` nunca levanta exceção de transporte: o esgotamento das tentativas vira o
    desfecho `falhou_integracao_ia`, e a saída recebida vira `valida` ou `invalida` conforme
    o veredito determinístico do validador. Só um desfecho `valida` segue para `criticar`:
    uma saída já reprovada por 3.2 encerra o grafo sem nenhuma chamada ao crítico (CRIT-04).
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

    async def criticar(state: EstadoGrafoMensagem) -> AtualizacaoCriticaMensagem:
        """Chama o crítico com retry e classifica a avaliação que voltou.

        Só é alcançado a partir de uma saída válida, então `resultado.saida` está presente:
        o crítico avalia exatamente o texto que a validação determinística já aprovou.
        """

        canal = state["canal"]
        gerado = state.get("resultado")
        assert gerado is not None, "o nó criticar só é alcançado depois do nó gerar"
        conteudo = gerado.saida
        assert conteudo is not None, "o nó criticar só é alcançado a partir de saída válida"
        inicio = perf_counter()

        def ignorar(_: Tentativa[AvaliacaoCritica | None]) -> None:
            """As tentativas de transporte não têm tabela própria nesta história."""

        retry: RetryComBackoff[AvaliacaoCritica | None] = RetryComBackoff(
            operacao=lambda: dependencias.critico.avaliar(conteudo, canal, state["contexto"]),
            aceitar=lambda _: True,
            registrar=ignorar,
            mensagem_esgotamento=MENSAGEM_CRITICA_ESGOTADA,
            erros_reconhecidos=(Exception,),
            esperar=dependencias.esperar,
        )

        def resultado(
            desfecho: DesfechoCritica,
            motivos: tuple[MotivoCritica, ...] = (),
            causa: str | None = None,
        ) -> AtualizacaoCriticaMensagem:
            """Fecha o desfecho da crítica com a duração medida e o modelo usado."""

            return {
                "resultado_critica": ResultadoCritica(
                    desfecho=desfecho,
                    motivos=motivos,
                    causa=causa,
                    duracao_ms=(perf_counter() - inicio) * 1000,
                    modelo=dependencias.critico.modelo,
                )
            }

        try:
            avaliacao = await retry.executar()
        except TentativasEsgotadas as falha:
            return resultado(DesfechoCritica.FALHOU_INTEGRACAO_IA, causa=_causa_de(falha))

        if avaliacao is None:
            return resultado(
                DesfechoCritica.SAIDA_INVALIDA, causa=CAUSA_SAIDA_CRITICA_INVALIDA
            )
        if avaliacao.aprovada:
            return resultado(DesfechoCritica.APROVADA, motivos=avaliacao.motivos)
        return resultado(DesfechoCritica.REPROVADA, motivos=avaliacao.motivos)

    def rota_apos_gerar(state: EstadoGrafoMensagem) -> str:
        """Encaminha ao crítico só a saída que a validação determinística aprovou."""

        gerado = state.get("resultado")
        assert gerado is not None, "a rota só é avaliada depois do nó gerar"
        return "criticar" if gerado.desfecho is DesfechoGeracao.VALIDA else END

    grafo = StateGraph(EstadoGrafoMensagem)
    grafo.add_node("gerar", gerar)  # pyright: ignore[reportUnknownMemberType]
    grafo.add_node("criticar", criticar)  # pyright: ignore[reportUnknownMemberType]
    grafo.add_edge(START, "gerar")
    grafo.add_conditional_edges(  # pyright: ignore[reportUnknownMemberType]
        "gerar", rota_apos_gerar, {"criticar": "criticar", END: END}
    )
    grafo.add_edge("criticar", END)
    return grafo.compile()  # pyright: ignore[reportUnknownMemberType]
