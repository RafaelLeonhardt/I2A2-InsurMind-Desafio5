"""Testes de fronteira de CORS e de disponibilidade da documentação via loopback."""

from pathlib import Path

from fastapi.testclient import TestClient

from central_preventiva.composicao.api import criar_aplicacao
from central_preventiva.composicao.configuracao import Configuracao

ORIGEM_CONFIGURADA = "http://127.0.0.1:5151"
ORIGEM_NAO_CONFIGURADA = "http://evil.example"


def configuracao_para(caminho: Path) -> Configuracao:
    """Monta a configuração local apontada ao banco temporário do teste."""

    return Configuracao(
        host_api="127.0.0.1",
        origem_frontend=ORIGEM_CONFIGURADA,
        caminho_banco=caminho,
    )


def cliente_para(caminho: Path) -> TestClient:
    """Cria o cliente HTTP da aplicação composta sobre o banco indicado."""

    return TestClient(criar_aplicacao(configuracao_para(caminho)))


def test_cors_libera_a_origem_configurada_do_frontend(tmp_path: Path) -> None:
    cliente = cliente_para(tmp_path / "banco.duckdb")

    resposta = cliente.get("/api/v1/saude", headers={"Origin": ORIGEM_CONFIGURADA})

    assert resposta.headers.get("access-control-allow-origin") == ORIGEM_CONFIGURADA


def test_cors_recusa_uma_origem_nao_configurada(tmp_path: Path) -> None:
    cliente = cliente_para(tmp_path / "banco.duckdb")

    resposta = cliente.get("/api/v1/saude", headers={"Origin": ORIGEM_NAO_CONFIGURADA})

    assert "access-control-allow-origin" not in resposta.headers


def test_preflight_libera_metodos_e_cabecalhos_esperados_para_a_origem_configurada(
    tmp_path: Path,
) -> None:
    cliente = cliente_para(tmp_path / "banco.duckdb")

    resposta = cliente.options(
        "/api/v1/dados-sinteticos/restauracoes",
        headers={
            "Origin": ORIGEM_CONFIGURADA,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type, Idempotency-Key",
        },
    )

    assert resposta.headers.get("access-control-allow-origin") == ORIGEM_CONFIGURADA
    metodos_liberados = resposta.headers.get("access-control-allow-methods", "")
    assert "GET" in metodos_liberados
    assert "POST" in metodos_liberados
    cabecalhos_liberados = resposta.headers.get("access-control-allow-headers", "")
    assert "content-type" in cabecalhos_liberados.lower()
    assert "idempotency-key" in cabecalhos_liberados.lower()
    assert "accept" in cabecalhos_liberados.lower()


def test_preflight_recusa_uma_origem_nao_configurada(tmp_path: Path) -> None:
    cliente = cliente_para(tmp_path / "banco.duckdb")

    resposta = cliente.options(
        "/api/v1/dados-sinteticos/restauracoes",
        headers={
            "Origin": ORIGEM_NAO_CONFIGURADA,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type, Idempotency-Key",
        },
    )

    assert "access-control-allow-origin" not in resposta.headers


def test_swagger_ui_responde_200_via_loopback(tmp_path: Path) -> None:
    cliente = cliente_para(tmp_path / "banco.duckdb")

    resposta = cliente.get("/docs")

    assert resposta.status_code == 200


def test_openapi_json_responde_200_com_content_type_json_via_loopback(
    tmp_path: Path,
) -> None:
    cliente = cliente_para(tmp_path / "banco.duckdb")

    resposta = cliente.get("/openapi.json")

    assert resposta.status_code == 200
    assert resposta.headers["content-type"].startswith("application/json")
