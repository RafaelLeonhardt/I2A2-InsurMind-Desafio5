"""Testes do recurso REST/JSON de prontidão das dependências (caminho GET)."""

from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.composicao.api import criar_aplicacao
from central_preventiva.composicao.configuracao import Configuracao

CAMINHO = "/api/v1/prontidao/dependencias"
CAMPOS_ESPERADOS = {"nome", "estado", "verificado_em", "causa", "impacto", "acao_disponivel"}


@pytest.fixture(autouse=True)
def _bloquear_chamadas_de_rede_reais(monkeypatch: pytest.MonkeyPatch) -> None:
    """Impede qualquer chamada HTTP real das sondas compostas neste módulo de teste."""

    async def _send_bloqueado(
        self: httpx.AsyncClient, request: httpx.Request, **_: object
    ) -> httpx.Response:
        raise AssertionError(f"chamada de rede real bloqueada em teste: {request.url}")

    monkeypatch.setattr(httpx.AsyncClient, "send", _send_bloqueado)


def configuracao_para(caminho: Path, chave_openai: str | None = None) -> Configuracao:
    """Monta a configuração local determinística, sem depender do `.env` real."""

    return Configuracao(
        host_api="127.0.0.1",
        origem_frontend="http://127.0.0.1:5173",
        caminho_banco=caminho,
        chave_openai=chave_openai,
        url_base_inmet="",
        _env_file=None,
    )


def preparar_banco(tmp_path: Path) -> Path:
    """Aplica as migrações em um banco temporário, sem semear dados sintéticos."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()
    return caminho


def cliente_para(caminho: Path, chave_openai: str | None = None) -> TestClient:
    """Cria o cliente HTTP da aplicação composta sobre o banco indicado."""

    return TestClient(criar_aplicacao(configuracao_para(caminho, chave_openai)))


def test_get_retorna_as_4_linhas_com_os_campos_esperados(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)

    resposta = cliente_para(caminho).get(CAMINHO)

    assert resposta.status_code == 200
    corpo = resposta.json()
    nomes = {dependencia["nome"] for dependencia in corpo["dependencias"]}
    assert nomes == {"backend", "banco_dados", "inmet", "openai"}
    for dependencia in corpo["dependencias"]:
        assert set(dependencia) == CAMPOS_ESPERADOS


def test_backend_e_banco_dados_respondem_terminal_na_primeira_chamada(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)

    corpo = cliente_para(caminho).get(CAMINHO).json()
    por_nome = {dependencia["nome"]: dependencia for dependencia in corpo["dependencias"]}

    assert por_nome["backend"]["estado"] == "disponivel"
    assert por_nome["backend"]["verificado_em"] is not None
    assert por_nome["banco_dados"]["estado"] == "disponivel"
    assert por_nome["banco_dados"]["verificado_em"] is not None


def test_sem_chave_openai_a_linha_openai_fica_indisponivel_sem_chamada_de_rede(
    tmp_path: Path,
) -> None:
    caminho = preparar_banco(tmp_path)

    corpo = cliente_para(caminho, chave_openai=None).get(CAMINHO).json()
    por_nome = {dependencia["nome"]: dependencia for dependencia in corpo["dependencias"]}

    assert por_nome["openai"]["estado"] == "indisponivel"
    assert por_nome["openai"]["causa"] == "Credencial ausente."
    assert por_nome["openai"]["verificado_em"] is not None


def test_resposta_nao_contem_a_chave_openai_sintetica_configurada(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    chave_sintetica = "sk-teste-e2e-nao-deve-vazar-98765"

    resposta = cliente_para(caminho, chave_openai=chave_sintetica).get(CAMINHO)

    assert resposta.status_code == 200
    assert chave_sintetica not in resposta.text
    for valor in resposta.headers.values():
        assert chave_sintetica not in valor


def test_contrato_openapi_descreve_a_prontidao_em_portugues(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)

    documento = cliente_para(caminho).get("/openapi.json").json()

    operacao = documento["paths"][CAMINHO]["get"]
    assert operacao["summary"] == "Consultar a prontidão das dependências"
    propriedades = documento["components"]["schemas"]["RespostaDependencia"]["properties"]
    assert set(propriedades) == CAMPOS_ESPERADOS


def test_cors_libera_o_get_de_prontidao_para_a_origem_local(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)

    permitida = cliente_para(caminho).options(
        CAMINHO,
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert permitida.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
