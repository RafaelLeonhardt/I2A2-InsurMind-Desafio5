"""Sonda de prontidão do endpoint público do INMET."""

import time
from collections.abc import Callable

import httpx

from central_preventiva.aplicacao.portas_prontidao import ResultadoSonda
from central_preventiva.dominio.estados_prontidao import EstadoProntidao

TIMEOUT_SEGUNDOS = 3.0
"""Timeout da sonda (ping de prontidão), não o timeout do adaptador de produção."""

ORCAMENTO_LATENCIA_SEGUNDOS = 1.5
"""Acima deste tempo, uma resposta 2xx é classificada como `DEGRADADA`."""

CAUSA_TIMEOUT = "Tempo limite excedido ao consultar o INMET."
CAUSA_CONEXAO = "Falha de conexão ao consultar o INMET."
CAUSA_LATENCIA = "O INMET respondeu, mas acima do orçamento de latência da sonda."


def _causa_status_transitorio(status_code: int) -> str:
    return f"O INMET respondeu com um status transitório ({status_code})."


class SondaInmet:
    """Verifica a prontidão do INMET por uma chamada HTTP real, sem retries."""

    def __init__(
        self,
        url_base: str,
        transport: httpx.AsyncBaseTransport | None = None,
        medir_tempo: Callable[[], float] = time.monotonic,
    ) -> None:
        """Guarda o endpoint a sondar e, opcionalmente, um transporte e relógio dublês."""

        self._url_base = url_base
        self._transport = transport
        self._medir_tempo = medir_tempo

    async def verificar(self) -> ResultadoSonda:
        """Executa uma única tentativa HTTP e classifica o resultado, sem retries."""

        inicio = self._medir_tempo()
        try:
            async with httpx.AsyncClient(
                transport=self._transport, timeout=TIMEOUT_SEGUNDOS
            ) as cliente:
                resposta = await cliente.get(self._url_base)
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
