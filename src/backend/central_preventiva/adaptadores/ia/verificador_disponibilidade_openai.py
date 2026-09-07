"""Verificação de disponibilidade real da OpenAI no fluxo de produção (PREFL-03, PREFL-04).

Diferente da `SondaOpenAI` (Épico 1), que responde à superfície de Prontidão, esta
verificação faz parte do preflight de uma execução: o resultado decide se a execução
avança para `processando_mensagens` ou termina em `falhou_preparacao_ia`.

SPEC_DEVIATION: o design cita `langchain_openai.ChatOpenAI` como cliente da chamada de
disponibilidade, e admite no mesmo item "ou chamada HTTP equivalente de baixo custo".
Foi escolhida a chamada HTTP (`GET /v1/models`), por dois motivos que o `ChatOpenAI` não
atende: PREFL-03 proíbe iniciar qualquer chamada de geração antes do terminal, e uma
invocação de modelo seria exatamente isso; e o catálogo devolvido por `/v1/models` é o
que permite tratar "modelo configurado não existe mais" como falha de preparação (Edge
Cases da spec). `langchain-openai` continua sendo a integração da geração, a partir da
História 3.2.

A chave nunca aparece em `causa`, exceção ou log: só viaja no cabeçalho `Authorization`.
"""

from dataclasses import dataclass
from typing import cast

import httpx

URL_MODELOS_OPENAI = "https://api.openai.com/v1/models"

CAUSA_CREDENCIAL_AUSENTE = "A credencial da OpenAI não está configurada."
CAUSA_CREDENCIAL_INVALIDA = "A credencial da OpenAI foi recusada."
CAUSA_TIMEOUT = "Tempo limite excedido ao consultar a OpenAI."
CAUSA_CONEXAO = "Falha de conexão ao consultar a OpenAI."
CAUSA_CATALOGO_ILEGIVEL = "A OpenAI respondeu com um catálogo de modelos ilegível."


def _causa_status(status_code: int) -> str:
    """Descreve um status de erro da OpenAI sem citar corpo, cabeçalho ou credencial."""

    return f"A OpenAI respondeu com um status de erro ({status_code})."


def _causa_modelo_ausente(modelo: str) -> str:
    """Descreve um modelo bem formado que não está mais no catálogo da OpenAI."""

    return f"O modelo configurado ('{modelo}') não está no catálogo da OpenAI."


@dataclass(frozen=True, slots=True)
class ResultadoDisponibilidade:
    """Resultado do preflight de disponibilidade: disponível, ou a causa sanitizada."""

    disponivel: bool
    causa: str | None


def _catalogo_de(resposta: httpx.Response) -> frozenset[str] | None:
    """Extrai os identificadores de modelo do corpo, ou `None` se ele for ilegível."""

    try:
        corpo: object = resposta.json()
    except ValueError:
        return None
    if not isinstance(corpo, dict):
        return None
    dados = cast(dict[str, object], corpo).get("data")
    if not isinstance(dados, list):
        return None

    identificadores: set[str] = set()
    for item in cast(list[object], dados):
        if not isinstance(item, dict):
            continue
        identificador = cast(dict[str, object], item).get("id")
        if isinstance(identificador, str):
            identificadores.add(identificador)
    return frozenset(identificadores)


class VerificadorDisponibilidadeOpenAI:
    """Confirma que a credencial é aceita, o serviço responde e o modelo existe.

    Uma única tentativa por chamada, sem retry: a política de tentativas pertence ao
    `RetryComBackoff` do caso de uso (`aplicacao/_retry.py`), não a este adaptador.
    """

    # SPEC_DEVIATION: URL configurável via `Configuracao.url_base_openai` para permitir E2E
    # sem chamada real (história 5.8); o default preserva o comportamento de produção.
    def __init__(
        self,
        chave: str | None,
        modelo: str,
        timeout_segundos: float,
        transport: httpx.AsyncBaseTransport | None = None,
        url_modelos: str = URL_MODELOS_OPENAI,
    ) -> None:
        """Guarda a credencial já resolvida, o modelo alvo e o limite de tempo (AD-8)."""

        self._chave = chave
        self._modelo = modelo
        self._timeout_segundos = timeout_segundos
        self._transport = transport
        self._url_modelos = url_modelos

    async def verificar(self) -> ResultadoDisponibilidade:
        """Executa uma tentativa e classifica o resultado, sem nunca expor a credencial.

        Uma credencial ausente é classificada como indisponível sem nenhuma chamada de
        rede: não há o que verificar, e tentar mesmo assim só produziria um 401.
        """

        if self._chave is None or not self._chave.strip():
            return ResultadoDisponibilidade(disponivel=False, causa=CAUSA_CREDENCIAL_AUSENTE)

        try:
            async with httpx.AsyncClient(
                transport=self._transport, timeout=self._timeout_segundos
            ) as cliente:
                resposta = await cliente.get(
                    self._url_modelos,
                    headers={"Authorization": f"Bearer {self._chave}"},
                )
        except httpx.TimeoutException:
            return ResultadoDisponibilidade(disponivel=False, causa=CAUSA_TIMEOUT)
        except httpx.TransportError:
            return ResultadoDisponibilidade(disponivel=False, causa=CAUSA_CONEXAO)

        if resposta.status_code == 401:
            return ResultadoDisponibilidade(disponivel=False, causa=CAUSA_CREDENCIAL_INVALIDA)
        if resposta.status_code != 200:
            return ResultadoDisponibilidade(
                disponivel=False, causa=_causa_status(resposta.status_code)
            )

        catalogo = _catalogo_de(resposta)
        if catalogo is None:
            return ResultadoDisponibilidade(disponivel=False, causa=CAUSA_CATALOGO_ILEGIVEL)
        if self._modelo not in catalogo:
            return ResultadoDisponibilidade(
                disponivel=False, causa=_causa_modelo_ausente(self._modelo)
            )

        return ResultadoDisponibilidade(disponivel=True, causa=None)
