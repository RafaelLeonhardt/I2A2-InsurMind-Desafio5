"""Testes do `ClienteInmet` (adaptador HTTP real) e do `AdaptadorInmetFalso`, sem rede real."""

import asyncio
from uuid import uuid4

import httpx
import pytest

from central_preventiva.adaptadores.meteorologia.cliente_inmet import (
    AdaptadorInmetFalso,
    ClienteInmet,
)
from central_preventiva.aplicacao.portas_meteorologia import AreaMonitorada, RespostaColetaInmet

URL_BASE_TESTE = "https://inmet.exemplo.invalido/api"

AREA = AreaMonitorada(
    id=uuid4(),
    codigo_estacao_inmet="A701",
    nome_estacao="Estação Sintética Demo",
    codigo_ibge_area="9990001",
    ativa=True,
)


def test_coleta_bem_sucedida_devolve_status_e_corpo_json() -> None:
    def manipulador(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"CHUVA": "10.0"})

    cliente = ClienteInmet(URL_BASE_TESTE, transport=httpx.MockTransport(manipulador))

    resposta = asyncio.run(cliente.coletar(AREA))

    assert resposta.status_code == 200
    assert resposta.corpo == {"CHUVA": "10.0"}


def test_timeout_e_propagado_sem_tratamento() -> None:
    def manipulador(_: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("tempo limite simulado")

    cliente = ClienteInmet(URL_BASE_TESTE, transport=httpx.MockTransport(manipulador))

    with pytest.raises(httpx.TimeoutException):
        asyncio.run(cliente.coletar(AREA))


def test_erro_de_transporte_e_propagado_sem_tratamento() -> None:
    def manipulador(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("falha de conexão simulada")

    cliente = ClienteInmet(URL_BASE_TESTE, transport=httpx.MockTransport(manipulador))

    with pytest.raises(httpx.TransportError):
        asyncio.run(cliente.coletar(AREA))


def test_status_de_erro_e_devolvido_sem_lancar_excecao() -> None:
    def manipulador(_: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"erro": "indisponível"})

    cliente = ClienteInmet(URL_BASE_TESTE, transport=httpx.MockTransport(manipulador))

    resposta = asyncio.run(cliente.coletar(AREA))

    assert resposta.status_code == 500
    assert resposta.corpo == {"erro": "indisponível"}


def test_adaptador_falso_devolve_resposta_programada_e_registra_a_chamada() -> None:
    resposta_programada = RespostaColetaInmet(status_code=200, corpo={"CHUVA": "5.0"})
    dublê = AdaptadorInmetFalso(resposta=resposta_programada)

    resposta = asyncio.run(dublê.coletar(AREA))

    assert resposta == resposta_programada
    assert dublê.chamadas == [AREA]


def test_adaptador_falso_lanca_excecao_programada() -> None:
    dublê = AdaptadorInmetFalso(excecao=httpx.TimeoutException("simulado"))

    with pytest.raises(httpx.TimeoutException):
        asyncio.run(dublê.coletar(AREA))

    assert dublê.chamadas == [AREA]
