"""Agente redator: gera o conteúdo estruturado de uma mensagem por canal (GERAR-07, 08).

O modelo recebe exatamente o contexto mínimo de 3.1 — os cinco campos de `ContextoAgente` —
e nada mais (AD-9). Ele apenas redige: campo obrigatório e tamanho são decididos depois, por
`ValidadorSaidaCanal`, fora do LLM (AD-5). O limite do canal entra no prompt como instrução
(o "antes" de GERAR-02), mas nunca como promessa: o mesmo limite é cobrado do texto devolvido.

SPEC_DEVIATION: o design declara `gerar(...) -> SaidaCanal`. A implementação devolve
`RespostaRedator`, que traz a saída e as métricas de uso da chamada. Dois motivos: GERAR-10
exige persistir as métricas de uso da geração, e um `SaidaCanal` puro não as carrega; e
GERAR-09 exige que saída ausente ou malformada seja marcada inválida, não que levante exceção,
então `saida` é anulável. A chamada usa `include_raw=True` justamente para ter as duas coisas
em uma só ida ao modelo.

SPEC_DEVIATION: o `design.md` da 3.4 diz que o redator é reusado "sem alteração de
assinatura", com os motivos da reprovação anterior chegando "pelo contexto". Motivo: as duas
coisas não podem ser verdadeiras ao mesmo tempo — o mesmo design (e o AD-9) exige que
`ContextoAgente` continue sendo exatamente os cinco campos minimizados de 3.1, então os
motivos não têm como entrar por ele. `gerar` ganhou um terceiro parâmetro opcional
(`motivos_anteriores`, vazio por padrão): toda chamada existente continua válida sem
alteração, e os motivos ficam sendo dado efêmero do ciclo, nunca dado do segurado (REGEN-01).
"""

from dataclasses import dataclass
from typing import Any, Protocol, cast

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from central_preventiva.dominio.avaliacao_critica import MotivoCritica
from central_preventiva.dominio.montador_contexto_agente import ContextoAgente
from central_preventiva.dominio.validador_saida_canal import (
    Canal,
    SaidaCanal,
    ValidadorSaidaCanal,
)


class SaidaWhatsApp(BaseModel):
    """Saída estruturada do canal WhatsApp: só corpo."""

    corpo: str = Field(description="Texto da mensagem preventiva enviada por WhatsApp.")


class SaidaSMS(BaseModel):
    """Saída estruturada do canal SMS: só corpo."""

    corpo: str = Field(description="Texto da mensagem preventiva enviada por SMS.")


class SaidaEmail(BaseModel):
    """Saída estruturada do canal e-mail: assunto e corpo."""

    assunto: str = Field(description="Linha de assunto do e-mail preventivo.")
    corpo: str = Field(description="Texto do e-mail preventivo.")


ESQUEMAS_POR_CANAL: dict[Canal, type[BaseModel]] = {
    Canal.WHATSAPP: SaidaWhatsApp,
    Canal.SMS: SaidaSMS,
    Canal.EMAIL: SaidaEmail,
}
"""Um schema Pydantic distinto por canal — o contrato que o modelo precisa preencher."""

INSTRUCAO_SISTEMA = (
    "Você redige comunicações preventivas de uma seguradora para clientes em área com "
    "evento meteorológico previsto. Escreva em português brasileiro, em tom direto e "
    "acolhedor. Use apenas as informações fornecidas. Não prometa cobertura, indenização, "
    "prazo ou valor. Não invente dado do cliente, endereço, telefone ou número de apólice. "
    "Deixe claro que é uma comunicação preventiva."
)
"""Instrução fixa do redator, versionada por `versao_prompt` na configuração."""


@dataclass(frozen=True, slots=True)
class RespostaRedator:
    """Saída estruturada do redator e as métricas de uso daquela chamada.

    `saida` é `None` quando o modelo respondeu mas não produziu conteúdo no schema do canal
    (saída ausente ou malformada) — o veredito de invalidez é do validador, não daqui. As
    métricas são anuláveis porque nem toda resposta traz metadados de uso.
    """

    saida: SaidaCanal | None
    tokens_entrada: int | None
    tokens_saida: int | None


class _Invocavel(Protocol):
    """Forma mínima do runnable devolvido por `with_structured_output`."""

    async def ainvoke(self, input: Any) -> Any: ...  # noqa: A002


class _ModeloDeChat(Protocol):
    """Forma mínima do modelo de chat de que o redator depende."""

    def with_structured_output(
        self, schema: type[BaseModel], *, include_raw: bool
    ) -> _Invocavel: ...


CABECALHO_CORRECAO = (
    "A versão anterior desta mensagem foi reprovada. Corrija exatamente os pontos abaixo e "
    "reescreva a mensagem inteira:"
)
"""Abertura do bloco de correção acrescentado ao pedido em uma regeneração (REGEN-01)."""


def montar_prompt(
    contexto: ContextoAgente,
    canal: Canal,
    limite_corpo: int,
    limite_assunto: int | None,
    motivos_anteriores: tuple[MotivoCritica, ...] = (),
) -> list[tuple[str, str]]:
    """Monta as mensagens do redator a partir dos cinco campos do contexto mínimo.

    Nada além do `ContextoAgente` alcança o prompt: não há caminho para documento, dado
    financeiro, dado de pagamento, credencial ou identificação direta do segurado (AD-9).

    Em uma regeneração (3.4), `motivos_anteriores` acrescenta ao pedido a categoria e a
    justificativa de cada motivo da reprovação anterior (REGEN-01). Esses motivos são dado
    efêmero do ciclo, produzidos pelo próprio sistema: eles nunca entram no `ContextoAgente`,
    que continua sendo exatamente os cinco campos minimizados de 3.1.
    """

    limites = f"O corpo deve ter no máximo {limite_corpo} caracteres."
    if limite_assunto is not None:
        limites += f" O assunto deve ter no máximo {limite_assunto} caracteres."

    coberturas = ", ".join(contexto.coberturas_relevantes)
    orientacoes = "\n".join(f"- {item}" for item in contexto.orientacoes_seguranca)
    pedido = (
        f"Evento previsto: {contexto.evento}\n"
        f"Localização aproximada: {contexto.localizacao_aproximada}\n"
        f"Coberturas relevantes da apólice: {coberturas}\n"
        f"Canal de envio: {canal.value}\n"
        f"Orientações de segurança a transmitir:\n{orientacoes}\n\n"
        f"Adapte o texto ao canal {canal.value}. {limites}"
    )
    if motivos_anteriores:
        correcoes = "\n".join(
            f"- {motivo.categoria.value}: {motivo.justificativa}"
            for motivo in motivos_anteriores
        )
        pedido += f"\n\n{CABECALHO_CORRECAO}\n{correcoes}"
    return [("system", INSTRUCAO_SISTEMA), ("human", pedido)]


def _saida_de(canal: Canal, estruturada: BaseModel) -> SaidaCanal:
    """Traduz o schema Pydantic do canal para o tipo de domínio validado depois."""

    dados = estruturada.model_dump()
    assunto = dados.get("assunto")
    return SaidaCanal(
        corpo=str(dados.get("corpo", "")),
        assunto=None if assunto is None else str(assunto),
    )


def _uso_de(bruta: object) -> tuple[int | None, int | None]:
    """Extrai tokens de entrada e saída dos metadados de uso, ou `(None, None)`."""

    uso = getattr(bruta, "usage_metadata", None)
    if not isinstance(uso, dict):
        return None, None
    dados = cast(dict[str, object], uso)
    entrada = dados.get("input_tokens")
    saida = dados.get("output_tokens")
    return (
        entrada if isinstance(entrada, int) else None,
        saida if isinstance(saida, int) else None,
    )


class AgenteRedator:
    """Chama o modelo com saída estruturada por canal e devolve o que ele produziu.

    Exceção de transporte não é tratada aqui: propaga ao chamador, que decide a política de
    tentativas (`RetryComBackoff`, `aplicacao/_retry.py`). Este adaptador não retenta nada.
    """

    def __init__(
        self,
        validador: ValidadorSaidaCanal,
        modelo: str,
        temperatura: float,
        timeout_segundos: float,
        chave: str | None,
        modelo_de_chat: _ModeloDeChat | None = None,
    ) -> None:
        """Guarda os parâmetros da geração e o modelo de chat (injetável nos testes).

        `validador` é a fonte única dos limites de canal: o mesmo número que instrui a
        geração é o que será cobrado do texto devolvido (GERAR-02).
        """

        self._validador = validador
        self._nome_modelo = modelo
        self._temperatura = temperatura
        self._timeout_segundos = timeout_segundos
        self._chave = chave
        self._modelo_de_chat = modelo_de_chat

    @property
    def modelo(self) -> str:
        """Identificador do modelo usado na geração, registrado em cada versão."""

        return self._nome_modelo

    def _obter_modelo_de_chat(self) -> _ModeloDeChat:
        """Constrói o `ChatOpenAI` na primeira geração, nunca na composição do app.

        Construir o cliente sem credencial levanta erro do SDK da OpenAI. A ausência de
        chave é estado de preflight (AD-9), não falha de inicialização do backend: adiar a
        construção até a primeira geração mantém o backend subindo com `OPENAI_API_KEY`
        vazia, exatamente como o `.env.example` documenta.
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

    async def gerar(
        self,
        contexto: ContextoAgente,
        canal: Canal,
        motivos_anteriores: tuple[MotivoCritica, ...] = (),
    ) -> RespostaRedator:
        """Pede ao modelo o conteúdo estruturado do canal e devolve o que voltou.

        Uma resposta que não preenche o schema do canal volta com `saida = None` — o
        validador determinístico é quem a marca inválida (GERAR-09).

        `motivos_anteriores` é vazio na primeira tentativa e carrega os motivos da
        reprovação anterior em uma regeneração (REGEN-01).
        """

        estruturado = self._obter_modelo_de_chat().with_structured_output(
            ESQUEMAS_POR_CANAL[canal], include_raw=True
        )
        resposta = await estruturado.ainvoke(
            montar_prompt(
                contexto,
                canal,
                self._validador.limite_corpo(canal),
                self._validador.limite_assunto(canal),
                motivos_anteriores,
            )
        )

        if not isinstance(resposta, dict):
            return RespostaRedator(saida=None, tokens_entrada=None, tokens_saida=None)
        conteudo = cast(dict[str, object], resposta)
        estruturada = conteudo.get("parsed")
        tokens_entrada, tokens_saida = _uso_de(conteudo.get("raw"))
        if not isinstance(estruturada, BaseModel):
            return RespostaRedator(
                saida=None, tokens_entrada=tokens_entrada, tokens_saida=tokens_saida
            )
        return RespostaRedator(
            saida=_saida_de(canal, estruturada),
            tokens_entrada=tokens_entrada,
            tokens_saida=tokens_saida,
        )
