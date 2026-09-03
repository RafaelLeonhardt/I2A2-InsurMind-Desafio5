"""Agente crítico: avalia o conteúdo de uma versão de mensagem (CRIT-01, 02, 03).

O modelo recebe a mensagem já gerada e o mesmo contexto mínimo de 3.1 que o redator recebeu —
os cinco campos de `ContextoAgente` — e nada mais. Ele avalia conteúdo: tom, utilidade,
clareza, segurança, ausência de promessa, distinção de alerta oficial e adequação ao canal.

O crítico não decide risco, elegibilidade, cobertura nem limite de canal (CRIT-02, AD-5). Isso
é garantido por construção, não por instrução: ele não recebe `ValidadorSaidaCanal` nem nenhum
limite, o prompt não carrega número de limite algum, e o enum fechado `CategoriaCritica` não
tem categoria para nenhuma dessas quatro decisões. A validação determinística de 3.2 já rodou
antes — uma saída estruturalmente inválida nunca sai de `gerando` e nunca chega até aqui
(CRIT-04).

SPEC_DEVIATION: o design declara `avaliar(...) -> AvaliacaoCritica`. A implementação devolve
`AvaliacaoCritica | None`. Motivo: CRIT-07 exige que uma saída inválida ou não interpretável
seja falha da tentativa, nunca aprovação e nunca reprovação estruturada. Um retorno não
anulável só admitiria duas saídas erradas: levantar exceção (que o `RetryComBackoff` leria
como falha de transporte, levando a `falhou_integracao_ia` — o terminal que o Edge Case da
spec reserva para transporte) ou um sentinel `aprovada = False`, que é exatamente a reprovação
estruturada de que CRIT-07 distingue a falha. Diferente de 3.2, não há dataclass de
embrulho: `avaliacoes_criticas` não persiste métricas de uso, então não há o que carregar
junto e um embrulho de campo único seria indireção sem função.
"""

from typing import Any, Protocol, cast

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from central_preventiva.dominio.avaliacao_critica import (
    AvaliacaoCritica,
    CategoriaCritica,
    MotivoCritica,
)
from central_preventiva.dominio.montador_contexto_agente import ContextoAgente
from central_preventiva.dominio.validador_saida_canal import Canal, SaidaCanal


class MotivoEstruturado(BaseModel):
    """Um motivo da decisão, no schema que o modelo preenche."""

    categoria: CategoriaCritica = Field(
        description=(
            "Critério avaliado: tom preventivo e não alarmista, utilidade, clareza, "
            "segurança, promessa indevida, distinção de alerta oficial ou adequação ao canal."
        )
    )
    justificativa: str = Field(
        description="Por que este critério sustenta a decisão, em uma frase específica."
    )


class AvaliacaoEstruturada(BaseModel):
    """Saída estruturada do crítico: a decisão e os motivos específicos dela."""

    aprovada: bool = Field(
        description="Verdadeiro se a mensagem está adequada para seguir à revisão humana."
    )
    motivos: list[MotivoEstruturado] = Field(
        description=(
            "Motivos específicos da decisão. Vazio quando aprovada; ao menos um, com "
            "justificativa, quando reprovada."
        )
    )


INSTRUCAO_SISTEMA = (
    "Você avalia a qualidade e a segurança de uma comunicação preventiva de seguradora já "
    "redigida, em português brasileiro. Avalie somente o conteúdo, contra estes sete "
    "critérios: tom preventivo e não alarmista; utilidade da orientação; clareza; segurança "
    "da instrução; ausência de promessa de cobertura, indenização, prazo ou valor; distinção "
    "clara de um alerta oficial de defesa civil; adequação ao canal. Você não decide risco, "
    "elegibilidade, cobertura nem limite de canal: essas decisões são determinísticas e já "
    "foram tomadas fora de você. Você também não reescreve a mensagem: apenas aprova ou "
    "reprova, com motivos específicos."
)
"""Instrução fixa do crítico, versionada por `versao_prompt` na configuração."""


class _Invocavel(Protocol):
    """Forma mínima do runnable devolvido por `with_structured_output`."""

    async def ainvoke(self, input: Any) -> Any: ...  # noqa: A002


class _ModeloDeChat(Protocol):
    """Forma mínima do modelo de chat de que o crítico depende."""

    def with_structured_output(
        self, schema: type[BaseModel], *, include_raw: bool
    ) -> _Invocavel: ...


def montar_prompt(
    conteudo: SaidaCanal, canal: Canal, contexto: ContextoAgente
) -> list[tuple[str, str]]:
    """Monta as mensagens do crítico: a mensagem avaliada e o contexto mínimo dela.

    Nenhum limite de canal, nenhum critério de risco e nenhum critério de elegibilidade
    entram no prompt — o crítico julga o texto, não a decisão determinística (CRIT-02).
    """

    coberturas = ", ".join(contexto.coberturas_relevantes)
    orientacoes = "\n".join(f"- {item}" for item in contexto.orientacoes_seguranca)
    assunto = "" if conteudo.assunto is None else f"Assunto da mensagem: {conteudo.assunto}\n"
    pedido = (
        f"Canal de envio: {canal.value}\n"
        f"{assunto}"
        f"Corpo da mensagem:\n{conteudo.corpo}\n\n"
        f"Contexto usado na redação:\n"
        f"Evento previsto: {contexto.evento}\n"
        f"Localização aproximada: {contexto.localizacao_aproximada}\n"
        f"Coberturas relevantes da apólice: {coberturas}\n"
        f"Orientações de segurança a transmitir:\n{orientacoes}\n\n"
        f"Avalie a mensagem contra os sete critérios e devolva a decisão com os motivos."
    )
    return [("system", INSTRUCAO_SISTEMA), ("human", pedido)]


def _avaliacao_de(estruturada: AvaliacaoEstruturada) -> AvaliacaoCritica | None:
    """Traduz a saída do modelo para o domínio, ou `None` se ela não for interpretável.

    Duas formas de saída não são interpretáveis com segurança (CRIT-07): uma reprovação sem
    nenhum motivo, que CRIT-03/CRIT-06 exigem específico e associável à versão, e um motivo
    sem justificativa, que não teria o que exibir no detalhe da avaliação (CRIT-08). Nenhuma
    das duas vira aprovação.
    """

    motivos = tuple(
        MotivoCritica(categoria=motivo.categoria, justificativa=motivo.justificativa.strip())
        for motivo in estruturada.motivos
    )
    if any(not motivo.justificativa for motivo in motivos):
        return None
    if not estruturada.aprovada and not motivos:
        return None
    return AvaliacaoCritica(aprovada=estruturada.aprovada, motivos=motivos)


class AgenteCritico:
    """Chama o modelo com saída estruturada e devolve a avaliação que ele produziu.

    Exceção de transporte não é tratada aqui: propaga ao chamador, que decide a política de
    tentativas (`RetryComBackoff`, `aplicacao/_retry.py`). Este adaptador não retenta nada.
    """

    def __init__(
        self,
        modelo: str,
        temperatura: float,
        timeout_segundos: float,
        chave: str | None,
        modelo_de_chat: _ModeloDeChat | None = None,
    ) -> None:
        """Guarda os parâmetros da avaliação e o modelo de chat (injetável nos testes).

        Não há parâmetro de limite nem de validador: o crítico não tem como conhecer o
        limite de canal e, portanto, não tem como sobrepor a validação determinística de
        3.2 (CRIT-02, CRIT-04).
        """

        self._nome_modelo = modelo
        self._temperatura = temperatura
        self._timeout_segundos = timeout_segundos
        self._chave = chave
        self._modelo_de_chat = modelo_de_chat

    @property
    def modelo(self) -> str:
        """Identificador do modelo usado na avaliação, registrado em cada avaliação."""

        return self._nome_modelo

    def _obter_modelo_de_chat(self) -> _ModeloDeChat:
        """Constrói o `ChatOpenAI` na primeira avaliação, nunca na composição do app.

        Mesma razão do redator (3.2): construir o cliente sem credencial levanta erro do SDK
        da OpenAI, e a ausência de chave é estado de preflight (AD-9), não falha de
        inicialização do backend.
        """

        if self._modelo_de_chat is None:
            self._modelo_de_chat = cast(
                _ModeloDeChat,
                ChatOpenAI(
                    model=self._nome_modelo,
                    temperature=self._temperatura,
                    timeout=self._timeout_segundos,
                    api_key=self._chave,  # pyright: ignore[reportArgumentType]
                ),
            )
        return self._modelo_de_chat

    async def avaliar(
        self, conteudo: SaidaCanal, canal: Canal, contexto: ContextoAgente
    ) -> AvaliacaoCritica | None:
        """Pede ao modelo a avaliação estruturada da mensagem e devolve o que voltou.

        Devolve `None` quando o modelo respondeu mas a saída não é interpretável com
        segurança — o chamador trata isso como falha da tentativa, nunca aprovação (CRIT-07).
        """

        estruturado = self._obter_modelo_de_chat().with_structured_output(
            AvaliacaoEstruturada, include_raw=True
        )
        resposta = await estruturado.ainvoke(montar_prompt(conteudo, canal, contexto))

        if not isinstance(resposta, dict):
            return None
        estruturada = cast(dict[str, object], resposta).get("parsed")
        if not isinstance(estruturada, AvaliacaoEstruturada):
            return None
        return _avaliacao_de(estruturada)
