"""Testes do recurso REST/JSON de consulta do segurado sintético padrão."""

from pathlib import Path

from fastapi.testclient import TestClient

from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.adaptadores.persistencia.semeador import SemeadorDadosSinteticos
from central_preventiva.composicao.api import criar_aplicacao
from central_preventiva.composicao.configuracao import Configuracao
from central_preventiva.dominio.identificadores_demonstracao import SEGURADO_PADRAO

CAMINHO = "/api/v1/segurados/padrao"
TIPO_PROBLEMA = "application/problem+json"


def configuracao_para(caminho: Path) -> Configuracao:
    """Monta a configuração local apontada ao banco temporário do teste."""

    return Configuracao(
        host_api="127.0.0.1",
        origem_frontend="http://127.0.0.1:5173",
        caminho_banco=caminho,
    )


def preparar_banco_semeado(tmp_path: Path) -> Path:
    """Aplica as migrações e semeia o conjunto sintético em um banco temporário."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()
    SemeadorDadosSinteticos(caminho).semear()
    return caminho


def cliente_para(caminho: Path) -> TestClient:
    """Cria o cliente HTTP da aplicação composta sobre o banco indicado."""

    return TestClient(criar_aplicacao(configuracao_para(caminho)))


def test_consulta_devolve_o_segurado_padrao_quando_semeado(tmp_path: Path) -> None:
    caminho = preparar_banco_semeado(tmp_path)

    resposta = cliente_para(caminho).get(CAMINHO)

    assert resposta.status_code == 200
    assert resposta.json() == {
        "id": str(SEGURADO_PADRAO),
        "nome": "Pessoa Segurada Sintética DEMO-001",
    }


def test_consulta_devolve_503_quando_os_dados_sinteticos_nao_foram_semeados(
    tmp_path: Path,
) -> None:
    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()

    resposta = cliente_para(caminho).get(CAMINHO)

    assert resposta.status_code == 503
    assert resposta.headers["content-type"].startswith(TIPO_PROBLEMA)
    corpo = resposta.json()
    assert corpo["codigo"] == "segurado_padrao_ausente"
    assert corpo["correlacao_id"]
    assert corpo["ocorrencia"] and corpo["impacto"] and corpo["proxima_acao"]


def test_roteador_registrado_com_prefixo_api_v1(tmp_path: Path) -> None:
    caminho = preparar_banco_semeado(tmp_path)

    documento = cliente_para(caminho).get("/openapi.json").json()

    assert CAMINHO in documento["paths"]
    assert "get" in documento["paths"][CAMINHO]
