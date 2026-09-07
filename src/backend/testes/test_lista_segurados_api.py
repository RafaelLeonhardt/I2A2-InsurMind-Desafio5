"""Testes do recurso REST/JSON da lista de segurados sintéticos disponíveis (SELETOR-01)."""

from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.composicao.api import criar_aplicacao
from central_preventiva.composicao.configuracao import Configuracao

SEGURADO_B_ID = UUID("22222222-2222-2222-2222-222222222222")
SEGURADO_A_ID = UUID("11111111-1111-1111-1111-111111111111")


def preparar_banco(tmp_path: Path) -> Path:
    """Aplica as migrações versionadas em um banco temporário."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()
    return caminho


def inserir_segurado(caminho: Path, id: UUID, nome: str) -> None:
    """Insere um segurado sintético mínimo para os testes da rota."""

    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO segurados (id, nome, codigo_ibge_area, canal_preferido) "
            "VALUES (?, ?, '9990001', 'whatsapp')",
            [id, nome],
        )


def configuracao_para(caminho: Path) -> Configuracao:
    """Monta a configuração local apontada ao banco temporário do teste."""

    return Configuracao(
        host_api="127.0.0.1",
        origem_frontend="http://127.0.0.1:5151",
        caminho_banco=caminho,
    )


def test_listar_segurados_devolve_todos_ordenados_por_nome(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    inserir_segurado(caminho, SEGURADO_B_ID, "Pessoa Segurada Sintética DEMO-002")
    inserir_segurado(caminho, SEGURADO_A_ID, "Pessoa Segurada Sintética DEMO-001")
    cliente = TestClient(criar_aplicacao(configuracao_para(caminho)))

    resposta = cliente.get("/api/v1/segurados")

    assert resposta.status_code == 200
    assert resposta.json() == {
        "segurados": [
            {"id": str(SEGURADO_A_ID), "nome": "Pessoa Segurada Sintética DEMO-001"},
            {"id": str(SEGURADO_B_ID), "nome": "Pessoa Segurada Sintética DEMO-002"},
        ]
    }


def test_listar_segurados_devolve_lista_vazia_com_seed_ausente(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    cliente = TestClient(criar_aplicacao(configuracao_para(caminho)))

    resposta = cliente.get("/api/v1/segurados")

    assert resposta.status_code == 200
    assert resposta.json() == {"segurados": []}
