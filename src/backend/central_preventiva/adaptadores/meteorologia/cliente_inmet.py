"""Cliente HTTP real do INMET e dublê de teste para a mesma porta `ColetorMeteorologico`."""

from datetime import date

import httpx

from central_preventiva.aplicacao.portas_meteorologia import AreaMonitorada, RespostaColetaInmet

TIMEOUT_SEGUNDOS = 5.0
"""Timeout da coleta de produção (distinto dos 3s da sonda de prontidão, que só faz ping)."""


class ClienteInmet:
    """Executa uma única chamada HTTP real ao INMET, sem normalizar nem tratar falhas."""

    def __init__(self, url_base: str, transport: httpx.AsyncBaseTransport | None = None) -> None:
        """Guarda o endpoint a consultar e, opcionalmente, um transporte dublê de teste."""

        self._url_base = url_base
        self._transport = transport

    async def coletar(self, area: AreaMonitorada) -> RespostaColetaInmet:
        """Faz uma única tentativa de `GET` na leitura horária da estação, sem retries.

        Propaga `httpx.TimeoutException`/`httpx.TransportError` sem tratá-los: a História 2.2
        decide o que fazer com eles. Não loga cabeçalhos, credenciais nem o corpo íntegro da
        resposta.
        """

        data_hoje = date.today().isoformat()
        caminho = f"/estacao/dados/{data_hoje}/{area.codigo_estacao_inmet}"
        async with httpx.AsyncClient(
            transport=self._transport, timeout=TIMEOUT_SEGUNDOS
        ) as cliente:
            resposta = await cliente.get(f"{self._url_base}{caminho}")

        try:
            corpo: object = resposta.json()
        except ValueError:
            corpo = None

        return RespostaColetaInmet(status_code=resposta.status_code, corpo=corpo)


class AdaptadorInmetFalso:
    """Dublê de `ColetorMeteorologico` com resposta programável, sem nenhuma chamada de rede."""

    def __init__(
        self,
        resposta: RespostaColetaInmet | None = None,
        excecao: Exception | None = None,
    ) -> None:
        """Guarda a resposta (ou exceção) a devolver e o diário de áreas coletadas."""

        self._resposta = resposta
        self._excecao = excecao
        self.chamadas: list[AreaMonitorada] = []

    async def coletar(self, area: AreaMonitorada) -> RespostaColetaInmet:
        """Registra a chamada e devolve a resposta programada, ou lança a exceção programada."""

        self.chamadas.append(area)
        if self._excecao is not None:
            raise self._excecao
        if self._resposta is None:
            raise ValueError("AdaptadorInmetFalso sem resposta nem exceção programada.")
        return self._resposta
