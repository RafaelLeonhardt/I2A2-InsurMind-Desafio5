"""Sonda de prontidão da OpenAI, sem nunca expor a credencial usada."""

import time
from collections.abc import Callable

import httpx

from central_preventiva.aplicacao.portas_prontidao import ResultadoSonda
from central_preventiva.dominio.estados_prontidao import EstadoProntidao

URL_MODELOS_OPENAI = "https://api.openai.com/v1/models"

TIMEOUT_SEGUNDOS = 5.0
"""Timeout da sonda (ping de prontidão), não o timeout do adaptador de produção."""

ORCAMENTO_LATENCIA_SEGUNDOS = 2.5
"""Acima deste tempo, uma resposta 2xx é classificada como `DEGRADADA`."""

CAUSA_TIMEOUT = "Tempo limite excedido ao consultar a OpenAI."
CAUSA_CONEXAO = "Falha de conexão ao consultar a OpenAI."
CAUSA_CREDENCIAL_INVALIDA = "A credencial da OpenAI foi recusada."
CAUSA_LATENCIA = "A OpenAI respondeu, mas acima do orçamento de latência da sonda."


def _causa_status_transitorio(status_code: int) -> str:
    return f"A OpenAI respondeu com um status transitório ({status_code})."


class SondaOpenAI:
    """Verifica a prontidão da OpenAI com uma chamada real de baixo custo.

    A sonda recebe a chave já resolvida pelo chamador; a decisão de reportar
    "sem credencial" sem chamada de rede pertence à camada de aplicação, não a
    esta sonda. A chave nunca é incluída em `causa`, exceção ou log.
    """

    # SPEC_DEVIATION: URL configurável via `Configuracao.url_base_openai` para permitir E2E
    # sem chamada real (história 5.8); o default preserva o comportamento de produção.
    def __init__(
        self,
        chave: str,
        transport: httpx.AsyncBaseTransport | None = None,
        medir_tempo: Callable[[], float] = time.monotonic,
        url_modelos: str = URL_MODELOS_OPENAI,
    ) -> None:
        """Guarda a credencial já resolvida e, opcionalmente, um transporte e relógio dublês."""

        self._chave = chave
        self._transport = transport
        self._medir_tempo = medir_tempo
        self._url_modelos = url_modelos

    async def verificar(self) -> ResultadoSonda:
        """Executa uma única tentativa HTTP e classifica o resultado, sem retries."""

        inicio = self._medir_tempo()
        try:
            async with httpx.AsyncClient(
                transport=self._transport, timeout=TIMEOUT_SEGUNDOS
            ) as cliente:
                resposta = await cliente.get(
                    self._url_modelos,
                    headers={"Authorization": f"Bearer {self._chave}"},
                )
        except httpx.TimeoutException:
            return ResultadoSonda(
                estado=EstadoProntidao.INDISPONIVEL, causa=CAUSA_TIMEOUT, latencia_ms=None
            )
        except httpx.TransportError:
            return ResultadoSonda(
                estado=EstadoProntidao.INDISPONIVEL, causa=CAUSA_CONEXAO, latencia_ms=None
            )

        fim = self._medir_tempo()
        latencia_ms = (fim - inicio) * 1000

        if resposta.status_code == 401:
            return ResultadoSonda(
                estado=EstadoProntidao.INDISPONIVEL,
                causa=CAUSA_CREDENCIAL_INVALIDA,
                latencia_ms=latencia_ms,
            )

        if resposta.status_code == 429 or resposta.status_code >= 500:
            return ResultadoSonda(
                estado=EstadoProntidao.DEGRADADA,
                causa=_causa_status_transitorio(resposta.status_code),
                latencia_ms=latencia_ms,
            )

        if (fim - inicio) > ORCAMENTO_LATENCIA_SEGUNDOS:
            return ResultadoSonda(
                estado=EstadoProntidao.DEGRADADA, causa=CAUSA_LATENCIA, latencia_ms=latencia_ms
            )

        return ResultadoSonda(
            estado=EstadoProntidao.DISPONIVEL, causa=None, latencia_ms=latencia_ms
        )
