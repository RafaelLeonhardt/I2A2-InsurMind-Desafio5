"""Testes de sincronia do contrato OpenAPI e de completude em português brasileiro."""

import json
from pathlib import Path

from central_preventiva.composicao.configuracao import Configuracao
from central_preventiva.composicao.openapi_export import (
    CAMINHO_SNAPSHOT_PADRAO,
    gerar_documento_openapi,
)

def configuracao_para(caminho: Path) -> Configuracao:
    """Monta a configuração local apontada ao banco temporário do teste."""

    return Configuracao(
        host_api="127.0.0.1",
        origem_frontend="http://127.0.0.1:5173",
        caminho_banco=caminho,
    )


def carregar_snapshot_versionado() -> dict:
    """Lê o snapshot versionado do documento OpenAPI."""

    return json.loads(CAMINHO_SNAPSHOT_PADRAO.read_text(encoding="utf-8"))


def test_documento_openapi_ao_vivo_corresponde_exatamente_ao_snapshot_versionado(
    tmp_path: Path,
) -> None:
    documento_ao_vivo = gerar_documento_openapi(configuracao_para(tmp_path / "banco.duckdb"))
    snapshot = carregar_snapshot_versionado()

    assert documento_ao_vivo == snapshot


def test_toda_operacao_sob_api_v1_tem_summary_e_description_em_portugues(
    tmp_path: Path,
) -> None:
    documento = gerar_documento_openapi(configuracao_para(tmp_path / "banco.duckdb"))

    operacoes_api_v1 = [
        (caminho, metodo, operacao)
        for caminho, operacoes in documento["paths"].items()
        if caminho.startswith("/api/v1")
        for metodo, operacao in operacoes.items()
    ]

    assert operacoes_api_v1, "esperava ao menos uma operação sob /api/v1"

    for caminho, metodo, operacao in operacoes_api_v1:
        summary = operacao.get("summary", "")
        description = operacao.get("description", "")
        assert summary.strip(), f"{metodo.upper()} {caminho} sem summary"
        assert description.strip(), f"{metodo.upper()} {caminho} sem description"


def test_todo_schema_de_erro_referenciado_sob_api_v1_tem_description_em_portugues(
    tmp_path: Path,
) -> None:
    documento = gerar_documento_openapi(configuracao_para(tmp_path / "banco.duckdb"))

    schemas_de_erro = {
        nome: schema
        for nome, schema in documento["components"]["schemas"].items()
        if nome.startswith("Problema")
    }

    assert schemas_de_erro, "esperava ao menos um schema de erro Problema*"

    for nome, schema in schemas_de_erro.items():
        assert schema.get("description", "").strip(), f"{nome} sem description"
