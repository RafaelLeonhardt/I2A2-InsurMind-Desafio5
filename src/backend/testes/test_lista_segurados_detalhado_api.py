"""Testes do recurso REST/JSON da lista detalhada de segurados sintéticos para o admin
(LISTASEG-01..03)."""

from pathlib import Path
from uuid import UUID, uuid4

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


def inserir_segurado(
    caminho: Path, id: UUID, nome: str, canal_preferido: str = "whatsapp"
) -> None:
    """Insere um segurado sintético mínimo para os testes da rota."""

    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO segurados (id, nome, codigo_ibge_area, canal_preferido) "
            "VALUES (?, ?, '9990001', ?)",
            [id, nome, canal_preferido],
        )


def inserir_apolice(caminho: Path, segurado_id: UUID, numero: str) -> None:
    """Insere uma apólice sintética mínima ligada ao segurado."""

    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO apolices (id, segurado_id, numero, tipo, situacao, "
            "vigencia_inicio, vigencia_fim, coberturas, endereco_risco_sintetico, "
            "codigo_ibge_area) VALUES (?, ?, ?, 'residencial', 'ativa', '2026-01-01', "
            "'2026-12-31', ['alagamento'], 'Rua Teste, 123', '9990001')",
            [uuid4(), segurado_id, numero],
        )


def configuracao_para(caminho: Path) -> Configuracao:
    """Monta a configuração local apontada ao banco temporário do teste."""

    return Configuracao(
        host_api="127.0.0.1",
        origem_frontend="http://127.0.0.1:5151",
        caminho_banco=caminho,
    )


def test_listar_segurados_detalhado_devolve_area_apolice_e_canal_ordenados_por_nome(
    tmp_path: Path,
) -> None:
    caminho = preparar_banco(tmp_path)
    inserir_segurado(caminho, SEGURADO_B_ID, "Pessoa Segurada Sintética DEMO-002", "sms")
    inserir_apolice(caminho, SEGURADO_B_ID, "RES-0002")
    inserir_segurado(caminho, SEGURADO_A_ID, "Pessoa Segurada Sintética DEMO-001", "email")
    inserir_apolice(caminho, SEGURADO_A_ID, "RES-0001")
    cliente = TestClient(criar_aplicacao(configuracao_para(caminho)))

    resposta = cliente.get("/api/v1/segurados/detalhado")

    assert resposta.status_code == 200
    assert resposta.json() == {
        "segurados": [
            {
                "id": str(SEGURADO_A_ID),
                "nome": "Pessoa Segurada Sintética DEMO-001",
                "codigo_ibge_area": "9990001",
                "apolice_numero": "RES-0001",
                "canal_preferido": "email",
            },
            {
                "id": str(SEGURADO_B_ID),
                "nome": "Pessoa Segurada Sintética DEMO-002",
                "codigo_ibge_area": "9990001",
                "apolice_numero": "RES-0002",
                "canal_preferido": "sms",
            },
        ]
    }


def test_listar_segurados_detalhado_devolve_apolice_nula_sem_apolice_cadastrada(
    tmp_path: Path,
) -> None:
    caminho = preparar_banco(tmp_path)
    inserir_segurado(caminho, SEGURADO_A_ID, "Pessoa Sem Apólice")
    cliente = TestClient(criar_aplicacao(configuracao_para(caminho)))

    resposta = cliente.get("/api/v1/segurados/detalhado")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert len(corpo["segurados"]) == 1
    assert corpo["segurados"][0]["apolice_numero"] is None


def test_listar_segurados_detalhado_devolve_lista_vazia_com_seed_ausente(
    tmp_path: Path,
) -> None:
    caminho = preparar_banco(tmp_path)
    cliente = TestClient(criar_aplicacao(configuracao_para(caminho)))

    resposta = cliente.get("/api/v1/segurados/detalhado")

    assert resposta.status_code == 200
    assert resposta.json() == {"segurados": []}
