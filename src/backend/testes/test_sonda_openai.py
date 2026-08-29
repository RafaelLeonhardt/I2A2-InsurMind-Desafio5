"""Testes da sonda de prontidão da OpenAI, sem nenhuma chamada de rede real."""

import asyncio
from collections.abc import Callable

import httpx
import pytest

from central_preventiva.adaptadores.prontidao.sonda_openai import SondaOpenAI
from central_preventiva.dominio.estados_prontidao import EstadoProntidao

CHAVE_SINTETICA = "sk-teste-xyz"


def _sequencia_de_tempos(*valores: float) -> Callable[[], float]:
    """Devolve um relógio dublê que emite os valores informados, em ordem."""

    iterador = iter(valores)
    return lambda: next(iterador)


def test_resposta_200_resulta_em_disponivel() -> None:
    def manipulador(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": []})

    sonda = SondaOpenAI(
        CHAVE_SINTETICA,
        transport=httpx.MockTransport(manipulador),
        medir_tempo=_sequencia_de_tempos(0.0, 0.1),
    )

    resultado = asyncio.run(sonda.verificar())

    assert resultado.estado == EstadoProntidao.DISPONIVEL
    assert resultado.causa is None


@pytest.mark.parametrize("status_code", [429, 500, 503])
def test_status_transitorio_resulta_em_degradada(status_code: int) -> None:
    def manipulador(_: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code)

    sonda = SondaOpenAI(
        CHAVE_SINTETICA,
        transport=httpx.MockTransport(manipulador),
        medir_tempo=_sequencia_de_tempos(0.0, 0.1),
    )

    resultado = asyncio.run(sonda.verificar())

    assert resultado.estado == EstadoProntidao.DEGRADADA


def test_resposta_401_resulta_em_indisponivel_sem_expor_a_chave_usada_no_teste() -> None:
    def manipulador(_: httpx.Request) -> httpx.Response:
        return httpx.Response(401)

    sonda = SondaOpenAI(
        CHAVE_SINTETICA,
        transport=httpx.MockTransport(manipulador),
        medir_tempo=_sequencia_de_tempos(0.0, 0.1),
    )

    resultado = asyncio.run(sonda.verificar())

    assert resultado.estado == EstadoProntidao.INDISPONIVEL
    assert resultado.causa is not None
    assert CHAVE_SINTETICA not in resultado.causa


def test_timeout_resulta_em_indisponivel() -> None:
    def manipulador(_: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("tempo limite simulado")

    sonda = SondaOpenAI(
        CHAVE_SINTETICA,
        transport=httpx.MockTransport(manipulador),
        medir_tempo=_sequencia_de_tempos(0.0),
    )

    resultado = asyncio.run(sonda.verificar())

    assert resultado.estado == EstadoProntidao.INDISPONIVEL


def test_falha_de_conexao_resulta_em_indisponivel() -> None:
    def manipulador(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("falha de conexão simulada")

    sonda = SondaOpenAI(
        CHAVE_SINTETICA,
        transport=httpx.MockTransport(manipulador),
        medir_tempo=_sequencia_de_tempos(0.0),
    )

    resultado = asyncio.run(sonda.verificar())

    assert resultado.estado == EstadoProntidao.INDISPONIVEL


def test_2xx_lento_acima_do_orcamento_resulta_em_degradada() -> None:
    def manipulador(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": []})

    sonda = SondaOpenAI(
        CHAVE_SINTETICA,
        transport=httpx.MockTransport(manipulador),
        medir_tempo=_sequencia_de_tempos(0.0, 3.0),
    )

    resultado = asyncio.run(sonda.verificar())

    assert resultado.estado == EstadoProntidao.DEGRADADA


def test_chave_sintetica_nunca_aparece_em_nenhum_estado_do_resultado() -> None:
    """Cobre todos os estados terminais (200/401/429/5xx/timeout/conexão) sem vazar a chave."""

    cenarios: list[Callable[[httpx.Request], httpx.Response]] = [
        lambda _: httpx.Response(200, json={"data": []}),
        lambda _: httpx.Response(401),
        lambda _: httpx.Response(429),
        lambda _: httpx.Response(503),
    ]

    for manipulador in cenarios:
        sonda = SondaOpenAI(
            CHAVE_SINTETICA,
            transport=httpx.MockTransport(manipulador),
            medir_tempo=_sequencia_de_tempos(0.0, 0.1),
        )
        resultado = asyncio.run(sonda.verificar())
        assert CHAVE_SINTETICA not in str(resultado)

    def levanta_timeout(_: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("tempo limite simulado")

    try:
        sonda_timeout = SondaOpenAI(
            CHAVE_SINTETICA,
            transport=httpx.MockTransport(levanta_timeout),
            medir_tempo=_sequencia_de_tempos(0.0),
        )
        resultado_timeout = asyncio.run(sonda_timeout.verificar())
        assert CHAVE_SINTETICA not in str(resultado_timeout)
    except httpx.HTTPError as excecao_nao_tratada:
        assert CHAVE_SINTETICA not in str(excecao_nao_tratada)
