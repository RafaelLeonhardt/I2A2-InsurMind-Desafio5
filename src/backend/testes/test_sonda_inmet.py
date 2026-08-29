"""Testes da sonda de prontidão do INMET, sem nenhuma chamada de rede real."""

import asyncio
from collections.abc import Callable

import httpx
import pytest

from central_preventiva.adaptadores.prontidao.sonda_inmet import SondaInmet
from central_preventiva.dominio.estados_prontidao import EstadoProntidao

URL_BASE_TESTE = "https://inmet.exemplo.invalido/api"


def _sequencia_de_tempos(*valores: float) -> Callable[[], float]:
    """Devolve um relógio dublê que emite os valores informados, em ordem."""

    iterador = iter(valores)
    return lambda: next(iterador)


def test_resposta_2xx_rapida_resulta_em_disponivel() -> None:
    def manipulador(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "ok"})

    sonda = SondaInmet(
        URL_BASE_TESTE,
        transport=httpx.MockTransport(manipulador),
        medir_tempo=_sequencia_de_tempos(0.0, 0.1),
    )

    resultado = asyncio.run(sonda.verificar())

    assert resultado.estado == EstadoProntidao.DISPONIVEL
    assert resultado.causa is None


def test_resposta_2xx_lenta_acima_do_orcamento_resulta_em_degradada() -> None:
    def manipulador(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "ok"})

    sonda = SondaInmet(
        URL_BASE_TESTE,
        transport=httpx.MockTransport(manipulador),
        medir_tempo=_sequencia_de_tempos(0.0, 2.0),
    )

    resultado = asyncio.run(sonda.verificar())

    assert resultado.estado == EstadoProntidao.DEGRADADA
    assert resultado.causa is not None


def test_resposta_503_resulta_em_degradada() -> None:
    def manipulador(_: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    sonda = SondaInmet(
        URL_BASE_TESTE,
        transport=httpx.MockTransport(manipulador),
        medir_tempo=_sequencia_de_tempos(0.0, 0.1),
    )

    resultado = asyncio.run(sonda.verificar())

    assert resultado.estado == EstadoProntidao.DEGRADADA
    assert resultado.causa is not None


def test_resposta_429_resulta_em_degradada() -> None:
    def manipulador(_: httpx.Request) -> httpx.Response:
        return httpx.Response(429)

    sonda = SondaInmet(
        URL_BASE_TESTE,
        transport=httpx.MockTransport(manipulador),
        medir_tempo=_sequencia_de_tempos(0.0, 0.1),
    )

    resultado = asyncio.run(sonda.verificar())

    assert resultado.estado == EstadoProntidao.DEGRADADA


def test_timeout_resulta_em_indisponivel() -> None:
    def manipulador(_: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("tempo limite simulado")

    sonda = SondaInmet(
        URL_BASE_TESTE,
        transport=httpx.MockTransport(manipulador),
        medir_tempo=_sequencia_de_tempos(0.0),
    )

    resultado = asyncio.run(sonda.verificar())

    assert resultado.estado == EstadoProntidao.INDISPONIVEL
    assert resultado.latencia_ms is None


def test_falha_de_conexao_resulta_em_indisponivel() -> None:
    def manipulador(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("falha de conexão simulada")

    sonda = SondaInmet(
        URL_BASE_TESTE,
        transport=httpx.MockTransport(manipulador),
        medir_tempo=_sequencia_de_tempos(0.0),
    )

    resultado = asyncio.run(sonda.verificar())

    assert resultado.estado == EstadoProntidao.INDISPONIVEL
    assert resultado.latencia_ms is None


def test_nenhuma_chamada_usa_transporte_de_rede_real() -> None:
    def manipulador(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200)

    sonda = SondaInmet(URL_BASE_TESTE, transport=httpx.MockTransport(manipulador))

    resultado = asyncio.run(sonda.verificar())

    assert resultado.estado == EstadoProntidao.DISPONIVEL


@pytest.mark.parametrize("status_code", [500, 502, 503, 504])
def test_qualquer_5xx_resulta_em_degradada(status_code: int) -> None:
    def manipulador(_: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code)

    sonda = SondaInmet(
        URL_BASE_TESTE,
        transport=httpx.MockTransport(manipulador),
        medir_tempo=_sequencia_de_tempos(0.0, 0.1),
    )

    resultado = asyncio.run(sonda.verificar())

    assert resultado.estado == EstadoProntidao.DEGRADADA
