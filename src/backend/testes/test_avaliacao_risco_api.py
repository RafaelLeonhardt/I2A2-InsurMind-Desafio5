"""Testes do recurso REST/JSON de detalhe da decisão de risco (RISCO-11, RISCO-12)."""

import json
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.composicao.api import criar_aplicacao
from central_preventiva.composicao.configuracao import Configuracao

TIPO_PROBLEMA = "application/problem+json"


def preparar_banco(tmp_path: Path) -> Path:
    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()
    return caminho


def inserir_avaliacao(caminho: Path, execucao_id: str) -> None:
    criterios = json.dumps(
        [
            {
                "operando": "área aplicável",
                "valor_observado": "9990001",
                "atende": True,
                "justificativa": "Área do evento corresponde à área aplicável da regra (9990001).",
            },
            {
                "operando": "intensidade (mm acumulados no período)",
                "valor_observado": "72.5 mm",
                "atende": True,
                "justificativa": "Intensidade observada atinge o limiar de 50.0 mm.",
            },
        ]
    )
    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO avaliacoes_risco "
            "(id, execucao_id, evento_id, regra_id, regra_versao, relevante, criterios, motivo) "
            "VALUES (?, ?, ?, ?, 1, true, ?, 'relevante')",
            [uuid4(), execucao_id, uuid4(), uuid4(), criterios],
        )


def configuracao_para(caminho: Path) -> Configuracao:
    return Configuracao(
        host_api="127.0.0.1",
        origem_frontend="http://127.0.0.1:5173",
        caminho_banco=caminho,
        url_base_inmet="https://inmet.exemplo.invalido",
        _env_file=None,
    )


def cliente_para(caminho: Path) -> TestClient:
    return TestClient(criar_aplicacao(configuracao_para(caminho)))


def test_get_avaliacao_risco_retorna_200_com_criterios_detalhados(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    execucao_id = str(uuid4())
    inserir_avaliacao(caminho, execucao_id)

    resposta = cliente_para(caminho).get(f"/api/v1/execucoes/{execucao_id}/avaliacao-risco")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["execucao_id"] == execucao_id
    assert corpo["relevante"] is True
    assert corpo["motivo"] == "relevante"
    assert len(corpo["criterios"]) == 2
    assert corpo["criterios"][0]["operando"] == "área aplicável"
    assert corpo["criterios"][0]["atende"] is True
    assert corpo["criterios"][1]["valor_observado"] == "72.5 mm"


def test_get_avaliacao_risco_sem_avaliacao_retorna_404_problem_json(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)

    resposta = cliente_para(caminho).get(f"/api/v1/execucoes/{uuid4()}/avaliacao-risco")

    assert resposta.status_code == 404
    assert resposta.headers["content-type"].startswith(TIPO_PROBLEMA)
    assert resposta.json()["codigo"] == "avaliacao_risco_inexistente"


def test_get_avaliacao_risco_com_id_malformado_retorna_422_problem_json(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)

    resposta = cliente_para(caminho).get("/api/v1/execucoes/nao-e-um-uuid/avaliacao-risco")

    assert resposta.status_code == 422
    assert resposta.headers["content-type"].startswith(TIPO_PROBLEMA)
    assert resposta.json()["codigo"] == "execucao_id_invalido"
