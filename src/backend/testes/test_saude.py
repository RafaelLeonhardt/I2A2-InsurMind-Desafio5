"""Testes do único recurso HTTP previsto nesta história."""

import pytest
from fastapi.testclient import TestClient

from central_preventiva.composicao.api import criar_aplicacao
from central_preventiva.composicao.configuracao import Configuracao, obter_configuracao


def criar_configuracao_local() -> Configuracao:
    """Cria a configuração sintética compartilhada pelos testes HTTP."""

    return Configuracao(
        host_api="127.0.0.1",
        origem_frontend="http://127.0.0.1:5173",
    )


def test_saude_retorna_json_em_snake_case() -> None:
    cliente = TestClient(criar_aplicacao(criar_configuracao_local()))
    resposta = cliente.get("/api/v1/saude")
    assert resposta.status_code == 200
    assert resposta.json() == {"status": "disponivel", "ambiente": "educacional"}


def test_openapi_em_portugues_nao_antecipa_recursos_futuros() -> None:
    cliente = TestClient(criar_aplicacao(criar_configuracao_local()))
    documento = cliente.get("/openapi.json").json()
    assert documento["info"]["description"].startswith("Disponibiliza somente")
    assert set(documento["paths"]) == {
        "/api/v1/saude",
        "/api/v1/dados-sinteticos/restauracoes",
        "/api/v1/prontidao/dependencias",
        "/api/v1/prontidao/dependencias/{nome}/verificacoes",
        "/api/v1/segurados/padrao",
    }
    assert documento["paths"]["/api/v1/saude"]["get"]["description"].startswith("Confirma")
    assert documento["paths"]["/api/v1/saude"]["get"]["responses"]["200"]["description"] == (
        "Saúde do processo confirmada."
    )


def test_cors_aceita_somente_a_origem_local_configurada() -> None:
    cliente = TestClient(criar_aplicacao(criar_configuracao_local()))
    permitida = cliente.options(
        "/api/v1/saude",
        headers={"Origin": "http://127.0.0.1:5173", "Access-Control-Request-Method": "GET"},
    )
    recusada = cliente.options(
        "/api/v1/saude",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
    )
    assert permitida.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
    assert "access-control-allow-origin" not in recusada.headers


def test_composicao_real_carrega_ambiente_e_configura_saude_e_cors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CENTRAL_PREVENTIVA_HOST_API", "127.0.0.1")
    monkeypatch.setenv("CENTRAL_PREVENTIVA_ORIGEM_FRONTEND", "http://127.0.0.1:5173")
    obter_configuracao.cache_clear()

    try:
        cliente = TestClient(criar_aplicacao())
        saude = cliente.get("/api/v1/saude")
        cors = cliente.options(
            "/api/v1/saude",
            headers={
                "Origin": "http://127.0.0.1:5173",
                "Access-Control-Request-Method": "GET",
            },
        )

        assert saude.json() == {"status": "disponivel", "ambiente": "educacional"}
        assert cors.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
    finally:
        obter_configuracao.cache_clear()
