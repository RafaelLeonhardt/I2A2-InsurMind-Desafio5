"""Grafo LangGraph de uma mensagem: `gerar` (3.2), `criticar` (3.3) e o ciclo de 3.4.

Um grafo por mensagem, não um grafo por lote: o AD-4 declara que cada mensagem tem seu
próprio estado de geração, crítica, revisão e simulação, então cada execução de grafo é
isolada e pequena. A revisão humana (3.5) chega depois, estendendo este mesmo grafo.

O nó `gerar` encadeia três decisões, nesta ordem: chamar o redator sob a política única de
tentativas (`RetryComBackoff`), classificar a saída pelo validador determinístico e devolver o
desfecho. O nó `criticar` só é alcançado quando esse desfecho é `valida`: a aresta condicional
depois de `gerar` é o que garante, por construção, que uma mensagem já reprovada
deterministicamente por 3.2 nunca chegue ao crítico e que o modelo não tenha como sobrepor a
validação objetiva (CRIT-04).

A História 3.4 fecha o ciclo automático do AD-4 dentro deste mesmo grafo, sem que o caso de
uso relance o grafo por fora: uma reprovação (do crítico ou da validação determinística) com
tentativa disponível passa por `regenerar`, que reserva a próxima tentativa e volta a `gerar`
levando os motivos da reprovação anterior; a terceira reprovação passa por `esgotar`, que leva
a mensagem a `falhou_conteudo` com uma `Exceção` (REGEN-01..04). Uma falha de transporte
esgotada, em qualquer nó e em qualquer tentativa, encerra o grafo em `falhou_integracao_ia` e
nunca consome uma regeneração: os dois terminais permanecem distintos por causa (REGEN-05).

Os nós não conhecem DuckDB. Cada marco durável é delegado à porta `CicloMensagem`, que o
`ServicoGeracaoMensagens` implementa: o grafo decide *quando* persistir, o caso de uso decide
*como*. Persistir marco a marco (e não só no fim) é o que torna a retomada de 3.4 possível —
uma tentativa concluída fica durável antes de a próxima começar (REGEN-08).

SPEC_DEVIATION: o `design.md` da 3.4 declara `RepositorioMensagens.incrementar_tentativa`
como dependência direta do grafo e uma única função de aresta
`decidir_apos_critica(estado) -> Literal["gerar", "falhou_conteudo"]`.
Motivo: (a) uma dependência direta de repositório colocaria DuckDB dentro do grafo e criaria
um ciclo de composição (o serviço precisa do grafo, e o grafo precisaria dos repositórios do
serviço); a porta `CicloMensagem`, entregue pelo estado do grafo, guarda a mesma decisão do
design sem esse acoplamento. (b) `falhou_conteudo` é um estado de mensagem, não um nó: o
destino virou o nó `esgotar`, e a decisão precisa existir também depois de `gerar`, porque a
reprovação determinística nunca chega a `criticar` mas consome a tentativa do mesmo jeito
(REGEN-01) — daí duas funções de aresta em vez de uma.

SPEC_DEVIATION: o `design.md` tipa `motivos_reprovacao_anterior` como
`list[MotivoCritica] | None`. A implementação usa `tuple[MotivoCritica, ...]`, ausente na
primeira tentativa. Motivo: todo valor de domínio deste projeto é imutável (`AvaliacaoCritica`
já expõe `motivos` como tupla), e uma lista mutável dentro do estado do grafo poderia ser
alterada por um nó sem que a alteração fosse visível como atualização de estado.
"""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import StrEnum
from time import perf_counter
from typing import NotRequired, Protocol, TypedDict
from uuid import UUID

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
from central_preventiva.dominio.avaliacao_critica import (
    AvaliacaoCritica,
    CategoriaCritica,
    MotivoCritica,
)
from central_preventiva.dominio.montador_contexto_agente import ContextoAgente
from central_preventiva.dominio.validador_saida_canal import (
    Canal,
    SaidaCanal,
    ValidadorSaidaCanal,
)

MAXIMO_TENTATIVAS_MENSAGEM = 3
"""Máximo de tentativas de conteúdo por mensagem (REGEN-02) — não confundir com
`MAXIMO_TENTATIVAS`, que é a política de retentativa de *transporte* de uma única chamada."""

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

MOTIVO_DETERMINISTICO_SEM_DETALHE = "saida_recusada_pela_validacao_deterministica"
"""Justificativa usada quando a recusa determinística não trouxe um código de motivo."""

NO_GERAR = "gerar"
NO_CRITICAR = "criticar"
NO_REGENERAR = "regenerar"
NO_ESGOTAR = "esgotar"


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
    (CRIT-07): nada é persistido em `avaliacoes_criticas` e a tentativa é consumida como
    qualquer outra reprovação (AD-4: "saída inválida do redator ou do crítico nunca é
    aprovação e consome a tentativa de geração correspondente").
    """

    desfecho: DesfechoCritica
    motivos: tuple[MotivoCritica, ...]
    causa: str | None
    duracao_ms: float
    modelo: str


class CicloMensagem(Protocol):
    """Porta dos marcos duráveis do ciclo de uma mensagem, chamada pelos nós do grafo.

    Cada método corresponde a um marco do segundo diagrama do AD-4. A implementação real é
    do `ServicoGeracaoMensagens`; o grafo nunca conhece repositório nem banco.
    """

    def registrar_geracao(
        self, mensagem_id: UUID, tentativa: int, resultado: ResultadoGeracao
    ) -> None:
        """Persiste a versão gerada nesta tentativa e o estado que ela implica."""
        ...

    def registrar_critica(
        self, mensagem_id: UUID, tentativa: int, critica: ResultadoCritica
    ) -> None:
        """Persiste a avaliação desta tentativa e o estado que ela implica."""
        ...

    def preparar_regeneracao(self, mensagem_id: UUID) -> int:
        """Reserva a próxima tentativa e devolve o número reservado (REGEN-01)."""
        ...

    def esgotar_tentativas(
        self, mensagem_id: UUID, tentativa: int, motivos: tuple[MotivoCritica, ...]
    ) -> None:
        """Leva a mensagem a `falhou_conteudo` com uma `Exceção` própria (REGEN-04)."""
        ...


class EstadoGrafoMensagem(TypedDict):
    """Cópia de trabalho tipada do grafo de uma mensagem (AD-4)."""

    contexto: ContextoAgente
    canal: Canal
    tentativa: int
    mensagem_id: UUID
    ciclo: CicloMensagem
    motivos_reprovacao_anterior: NotRequired[tuple[MotivoCritica, ...]]
    resultado: NotRequired[ResultadoGeracao]
    resultado_critica: NotRequired[ResultadoCritica]
    retomar_de: NotRequired[str]


class AtualizacaoGrafoMensagem(TypedDict):
    """Atualização parcial que o nó `gerar` devolve ao grafo."""

    resultado: ResultadoGeracao


class AtualizacaoCriticaMensagem(TypedDict):
    """Atualização parcial que o nó `criticar` devolve ao grafo."""

    resultado_critica: ResultadoCritica


class AtualizacaoRegeneracao(TypedDict):
    """Atualização parcial que o nó `regenerar` devolve ao grafo (REGEN-01)."""

    tentativa: int
    motivos_reprovacao_anterior: tuple[MotivoCritica, ...]


class _Redator(Protocol):
    """Porta mínima do agente redator de que o nó `gerar` depende."""

    @property
    def modelo(self) -> str: ...

    async def gerar(
        self,
        contexto: ContextoAgente,
        canal: Canal,
        motivos_anteriores: tuple[MotivoCritica, ...] = (),
    ) -> RespostaRedator: ...


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


def motivos_da_reprovacao(state: EstadoGrafoMensagem) -> tuple[MotivoCritica, ...]:
    """Devolve os motivos da reprovação que acabou de acontecer nesta tentativa.

    A fonte é decidida pelo desfecho da geração da própria tentativa, não pela ordem em que
    os campos foram escritos: uma saída `invalida` só pode ter vindo do validador
    determinístico (o crítico nunca é alcançado a partir dela), e uma saída `valida` só pode
    ter sido reprovada pelo crítico. Assim uma avaliação da tentativa anterior nunca é lida
    como se fosse desta.
    """

    gerado = state.get("resultado")
    assert gerado is not None, "os motivos só existem depois do nó gerar"
    if gerado.desfecho is DesfechoGeracao.INVALIDA:
        return (
            MotivoCritica(
                CategoriaCritica.ADEQUACAO_CANAL,
                gerado.motivo or MOTIVO_DETERMINISTICO_SEM_DETALHE,
            ),
        )
    critica = state.get("resultado_critica")
    return () if critica is None else critica.motivos


type GrafoMensagemCompilado = CompiledStateGraph[
    EstadoGrafoMensagem, None, EstadoGrafoMensagem, EstadoGrafoMensagem
]
"""Grafo já compilado de uma mensagem, pronto para `ainvoke`."""


def construir_grafo(dependencias: DependenciasGrafo) -> GrafoMensagemCompilado:
    """Compila o grafo de uma mensagem, com o ciclo automático de regeneração do AD-4.

    O nó `gerar` nunca levanta exceção de transporte: o esgotamento das tentativas vira o
    desfecho `falhou_integracao_ia`, e a saída recebida vira `valida` ou `invalida` conforme
    o veredito determinístico do validador. Só um desfecho `valida` segue para `criticar`:
    uma saída já reprovada por 3.2 encerra a tentativa sem nenhuma chamada ao crítico
    (CRIT-04) — mas ainda consome a tentativa, então segue para `regenerar` ou `esgotar`
    como qualquer outra reprovação (REGEN-01).
    """

    async def gerar(state: EstadoGrafoMensagem) -> AtualizacaoGrafoMensagem:
        """Chama o redator com retry, classifica a saída e persiste a versão da tentativa."""

        canal = state["canal"]
        motivos_anteriores = state.get("motivos_reprovacao_anterior", ())
        inicio = perf_counter()

        def ignorar(_: Tentativa[RespostaRedator]) -> None:
            """As tentativas de transporte não têm tabela própria nesta história."""

        retry: RetryComBackoff[RespostaRedator] = RetryComBackoff(
            operacao=lambda: dependencias.redator.gerar(
                state["contexto"], canal, motivos_anteriores
            ),
            aceitar=lambda _: True,
            registrar=ignorar,
            mensagem_esgotamento=MENSAGEM_GERACAO_ESGOTADA,
            erros_reconhecidos=(Exception,),
            esperar=dependencias.esperar,
        )

        def concluir(resultado: ResultadoGeracao) -> AtualizacaoGrafoMensagem:
            """Persiste o marco durável da tentativa antes de devolver o desfecho."""

            state["ciclo"].registrar_geracao(
                state["mensagem_id"], state["tentativa"], resultado
            )
            return {"resultado": resultado}

        try:
            resposta = await retry.executar()
        except TentativasEsgotadas as falha:
            return concluir(
                ResultadoGeracao(
                    desfecho=DesfechoGeracao.FALHOU_INTEGRACAO_IA,
                    saida=None,
                    motivo=_causa_de(falha),
                    duracao_ms=(perf_counter() - inicio) * 1000,
                    modelo=dependencias.redator.modelo,
                    tokens_entrada=None,
                    tokens_saida=None,
                )
            )

        veredito = dependencias.validador.validar(canal, resposta.saida)
        return concluir(
            ResultadoGeracao(
                desfecho=DesfechoGeracao.VALIDA if veredito.valida else DesfechoGeracao.INVALIDA,
                saida=resposta.saida,
                motivo=veredito.motivo,
                duracao_ms=(perf_counter() - inicio) * 1000,
                modelo=dependencias.redator.modelo,
                tokens_entrada=resposta.tokens_entrada,
                tokens_saida=resposta.tokens_saida,
            )
        )

    async def criticar(state: EstadoGrafoMensagem) -> AtualizacaoCriticaMensagem:
        """Chama o crítico com retry, classifica a avaliação e persiste o marco.

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
            """Fecha o desfecho da crítica e persiste o marco durável da tentativa."""

            critica = ResultadoCritica(
                desfecho=desfecho,
                motivos=motivos,
                causa=causa,
                duracao_ms=(perf_counter() - inicio) * 1000,
                modelo=dependencias.critico.modelo,
            )
            state["ciclo"].registrar_critica(
                state["mensagem_id"], state["tentativa"], critica
            )
            return {"resultado_critica": critica}

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

    async def regenerar(state: EstadoGrafoMensagem) -> AtualizacaoRegeneracao:
        """Reserva a próxima tentativa e devolve ao redator os motivos da reprovação."""

        motivos = motivos_da_reprovacao(state)
        proxima = state["ciclo"].preparar_regeneracao(state["mensagem_id"])
        return {"tentativa": proxima, "motivos_reprovacao_anterior": motivos}

    async def esgotar(state: EstadoGrafoMensagem) -> dict[str, object]:
        """Fecha a mensagem em `falhou_conteudo` depois da terceira reprovação."""

        state["ciclo"].esgotar_tentativas(
            state["mensagem_id"], state["tentativa"], motivos_da_reprovacao(state)
        )
        return {}

    def _apos_reprovacao(state: EstadoGrafoMensagem) -> str:
        """Regenera enquanto houver tentativa disponível; senão esgota (REGEN-02/04)."""

        return (
            NO_REGENERAR
            if state["tentativa"] < MAXIMO_TENTATIVAS_MENSAGEM
            else NO_ESGOTAR
        )

    def rota_apos_gerar(state: EstadoGrafoMensagem) -> str:
        """Encaminha ao crítico só a saída que a validação determinística aprovou."""

        gerado = state.get("resultado")
        assert gerado is not None, "a rota só é avaliada depois do nó gerar"
        if gerado.desfecho is DesfechoGeracao.VALIDA:
            return NO_CRITICAR
        if gerado.desfecho is DesfechoGeracao.FALHOU_INTEGRACAO_IA:
            return END
        return _apos_reprovacao(state)

    def rota_apos_criticar(state: EstadoGrafoMensagem) -> str:
        """Encerra na aprovação e na falha de transporte; reprovação consome a tentativa."""

        critica = state.get("resultado_critica")
        assert critica is not None, "a rota só é avaliada depois do nó criticar"
        if critica.desfecho in (
            DesfechoCritica.APROVADA,
            DesfechoCritica.FALHOU_INTEGRACAO_IA,
        ):
            return END
        return _apos_reprovacao(state)

    def rota_inicial(state: EstadoGrafoMensagem) -> str:
        """Escolhe o nó de entrada: `gerar` no fluxo normal, o marco seguinte na retomada.

        Uma execução nova sempre começa em `gerar`. Uma retomada no boot (REGEN-08) informa
        `retomar_de` a partir do que está persistido, para continuar do último marco durável
        em vez de repetir uma tentativa já concluída.
        """

        return state.get("retomar_de", NO_GERAR)

    grafo = StateGraph(EstadoGrafoMensagem)
    grafo.add_node(NO_GERAR, gerar)  # pyright: ignore[reportUnknownMemberType]
    grafo.add_node(NO_CRITICAR, criticar)  # pyright: ignore[reportUnknownMemberType]
    grafo.add_node(NO_REGENERAR, regenerar)  # pyright: ignore[reportUnknownMemberType]
    grafo.add_node(NO_ESGOTAR, esgotar)  # pyright: ignore[reportUnknownMemberType]
    grafo.add_conditional_edges(  # pyright: ignore[reportUnknownMemberType]
        START,
        rota_inicial,
        {
            NO_GERAR: NO_GERAR,
            NO_CRITICAR: NO_CRITICAR,
            NO_REGENERAR: NO_REGENERAR,
            NO_ESGOTAR: NO_ESGOTAR,
        },
    )
    grafo.add_conditional_edges(  # pyright: ignore[reportUnknownMemberType]
        NO_GERAR,
        rota_apos_gerar,
        {
            NO_CRITICAR: NO_CRITICAR,
            NO_REGENERAR: NO_REGENERAR,
            NO_ESGOTAR: NO_ESGOTAR,
            END: END,
        },
    )
    grafo.add_conditional_edges(  # pyright: ignore[reportUnknownMemberType]
        NO_CRITICAR,
        rota_apos_criticar,
        {NO_REGENERAR: NO_REGENERAR, NO_ESGOTAR: NO_ESGOTAR, END: END},
    )
    grafo.add_edge(NO_REGENERAR, NO_GERAR)
    grafo.add_edge(NO_ESGOTAR, END)
    return grafo.compile()  # pyright: ignore[reportUnknownMemberType]
