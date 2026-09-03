"""Testes do preflight de disponibilidade da OpenAI, sem nenhuma chamada de rede real."""

import asyncio

import httpx
import pytest

from central_preventiva.adaptadores.ia.verificador_disponibilidade_openai import (
    CAUSA_CATALOGO_ILEGIVEL,
    CAUSA_CONEXAO,
    CAUSA_CREDENCIAL_AUSENTE,
    CAUSA_CREDENCIAL_INVALIDA,
    CAUSA_TIMEOUT,
    URL_MODELOS_OPENAI,
    ResultadoDisponibilidade,
    VerificadorDisponibilidadeOpenAI,
)

CHAVE_SINTETICA = "sk-teste-nao-deve-vazar-98765"
MODELO = "gpt-4o-mini"
TIMEOUT = 5.0


class TransporteEspiao:
    """Transporte dublê: conta as requisições e devolve a resposta programada."""

    def __init__(self, resposta: httpx.Response | BaseException) -> None:
        self.requisicoes: list[httpx.Request] = []
        self._resposta = resposta

    def como_transporte(self) -> httpx.MockTransport:
        def manipulador(requisicao: httpx.Request) -> httpx.Response:
            self.requisicoes.append(requisicao)
            if isinstance(self._resposta, BaseException):
                raise self._resposta
            return self._resposta

        return httpx.MockTransport(manipulador)


def catalogo(*modelos: str) -> httpx.Response:
    """Monta a resposta 200 de `GET /v1/models` com os modelos informados."""

    return httpx.Response(200, json={"data": [{"id": modelo} for modelo in modelos]})


def verificar(
    resposta: httpx.Response | BaseException,
    chave: str | None = CHAVE_SINTETICA,
    modelo: str = MODELO,
) -> tuple[ResultadoDisponibilidade, TransporteEspiao]:
    """Executa uma verificação contra o transporte dublê e devolve resultado e espião."""

    espiao = TransporteEspiao(resposta)
    verificador = VerificadorDisponibilidadeOpenAI(
        chave, modelo, TIMEOUT, transport=espiao.como_transporte()
    )
    return asyncio.run(verificador.verificar()), espiao


def test_modelo_presente_no_catalogo_resulta_em_disponivel() -> None:
    resultado, espiao = verificar(catalogo("gpt-4o", MODELO))

    assert resultado == ResultadoDisponibilidade(disponivel=True, causa=None)
    assert len(espiao.requisicoes) == 1
    assert str(espiao.requisicoes[0].url) == URL_MODELOS_OPENAI


@pytest.mark.parametrize("chave", [None, "", "   "])
def test_credencial_ausente_resulta_em_indisponivel_sem_nenhuma_chamada_de_rede(
    chave: str | None,
) -> None:
    resultado, espiao = verificar(catalogo(MODELO), chave=chave)

    assert resultado.disponivel is False
    assert resultado.causa == CAUSA_CREDENCIAL_AUSENTE
    assert espiao.requisicoes == []


def test_credencial_recusada_resulta_em_indisponivel_com_causa_sanitizada() -> None:
    resultado, _ = verificar(httpx.Response(401))

    assert resultado.disponivel is False
    assert resultado.causa == CAUSA_CREDENCIAL_INVALIDA


@pytest.mark.parametrize("status_code", [429, 500, 503])
def test_status_de_erro_resulta_em_indisponivel_citando_apenas_o_status(
    status_code: int,
) -> None:
    resultado, _ = verificar(httpx.Response(status_code))

    assert resultado.disponivel is False
    assert resultado.causa == f"A OpenAI respondeu com um status de erro ({status_code})."


def test_timeout_resulta_em_indisponivel() -> None:
    resultado, _ = verificar(httpx.TimeoutException("tempo esgotado"))

    assert resultado.disponivel is False
    assert resultado.causa == CAUSA_TIMEOUT


def test_falha_de_transporte_resulta_em_indisponivel() -> None:
    resultado, _ = verificar(httpx.ConnectError("sem rota"))

    assert resultado.disponivel is False
    assert resultado.causa == CAUSA_CONEXAO


def test_modelo_ausente_do_catalogo_resulta_em_falha_de_preparacao_nao_em_sucesso() -> None:
    """Edge case da spec: chave válida, serviço no ar, mas o modelo configurado sumiu."""

    resultado, _ = verificar(catalogo("gpt-4o", "o3-mini"))

    assert resultado.disponivel is False
    assert resultado.causa == f"O modelo configurado ('{MODELO}') não está no catálogo da OpenAI."


@pytest.mark.parametrize(
    "corpo",
    [
        httpx.Response(200, text="não é json"),
        httpx.Response(200, json=["lista", "no", "lugar", "do", "objeto"]),
        httpx.Response(200, json={"models": [{"id": MODELO}]}),
    ],
)
def test_catalogo_ilegivel_resulta_em_indisponivel_em_vez_de_disponivel(
    corpo: httpx.Response,
) -> None:
    resultado, _ = verificar(corpo)

    assert resultado.disponivel is False
    assert resultado.causa == CAUSA_CATALOGO_ILEGIVEL


@pytest.mark.parametrize(
    "resposta",
    [
        httpx.Response(401),
        httpx.Response(429),
        httpx.Response(500),
        httpx.Response(200, json={"data": [{"id": "outro-modelo"}]}),
        httpx.Response(200, text="não é json"),
        httpx.TimeoutException("tempo esgotado"),
        httpx.ConnectError("sem rota"),
    ],
)
def test_a_credencial_nunca_aparece_em_nenhum_campo_do_resultado(
    resposta: httpx.Response | BaseException,
) -> None:
    """PREFL-04: nenhuma causa revela valor, fragmento ou cabeçalho da credencial."""

    resultado, _ = verificar(resposta)

    assert resultado.disponivel is False
    assert resultado.causa is not None
    assert CHAVE_SINTETICA not in resultado.causa
    assert CHAVE_SINTETICA not in repr(resultado)
    assert "Bearer" not in resultado.causa
    assert "Authorization" not in resultado.causa


def test_a_credencial_viaja_apenas_no_cabecalho_authorization() -> None:
    _, espiao = verificar(catalogo(MODELO))

    requisicao = espiao.requisicoes[0]
    assert requisicao.headers["Authorization"] == f"Bearer {CHAVE_SINTETICA}"
    assert CHAVE_SINTETICA not in str(requisicao.url)
