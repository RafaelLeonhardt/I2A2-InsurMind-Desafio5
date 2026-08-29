"""Testes do recurso REST/JSON de restauração dos dados sintéticos."""

from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from central_preventiva.adaptadores.persistencia import semeador as modulo_semeador
from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.adaptadores.persistencia.semeador import SemeadorDadosSinteticos
from central_preventiva.composicao.api import criar_aplicacao
from central_preventiva.composicao.configuracao import Configuracao

CAMINHO = "/api/v1/dados-sinteticos/restauracoes"
TIPO_PROBLEMA = "application/problem+json"
NOME_ALTERADO = "Nome alterado localmente"


def configuracao_para(caminho: Path) -> Configuracao:
    """Monta a configuração local apontada ao banco temporário do teste."""

    return Configuracao(
        host_api="127.0.0.1",
        origem_frontend="http://127.0.0.1:5173",
        caminho_banco=caminho,
    )


def preparar_banco(tmp_path: Path) -> Path:
    """Aplica as migrações e semeia o conjunto sintético em um banco temporário."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()
    SemeadorDadosSinteticos(caminho).semear()
    return caminho


def cliente_para(caminho: Path) -> TestClient:
    """Cria o cliente HTTP da aplicação composta sobre o banco indicado."""

    return TestClient(criar_aplicacao(configuracao_para(caminho)))


def alterar_um_segurado(caminho: Path) -> None:
    """Simula uma alteração local em um registro de referência semeado."""

    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "UPDATE segurados SET nome = ? WHERE nome = (SELECT min(nome) FROM segurados)",
            [NOME_ALTERADO],
        )


def nomes_alterados(caminho: Path) -> int:
    """Conta quantos registros de referência ainda carregam a alteração local."""

    with abrir_conexao(caminho) as conexao:
        linha = conexao.execute(
            "SELECT count(*) FROM segurados WHERE nome = ?", [NOME_ALTERADO]
        ).fetchone()
    assert linha is not None
    return int(linha[0])


def test_restauracao_confirmada_repoe_o_conjunto_versionado(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    alterar_um_segurado(caminho)
    assert nomes_alterados(caminho) == 1

    resposta = cliente_para(caminho).post(CAMINHO, headers={"Idempotency-Key": str(uuid4())})

    assert resposta.status_code == 201
    assert set(resposta.json()) == {"status", "restaurado_em"}
    assert resposta.json()["status"] == "restaurado"
    assert nomes_alterados(caminho) == 0


def test_requisicao_sem_idempotency_key_e_recusada(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    alterar_um_segurado(caminho)

    resposta = cliente_para(caminho).post(CAMINHO)

    assert resposta.status_code == 422
    assert resposta.headers["content-type"].startswith(TIPO_PROBLEMA)
    assert resposta.json()["codigo"] == "idempotency_key_ausente"
    assert resposta.json()["correlacao_id"]
    assert nomes_alterados(caminho) == 1


def test_mesma_chave_e_mesmo_conteudo_devolve_a_resposta_registrada(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    cliente = cliente_para(caminho)
    chave = str(uuid4())

    primeira = cliente.post(CAMINHO, headers={"Idempotency-Key": chave})
    alterar_um_segurado(caminho)
    segunda = cliente.post(CAMINHO, headers={"Idempotency-Key": chave})

    assert primeira.status_code == 201
    assert segunda.status_code == 201
    assert segunda.json() == primeira.json()
    assert nomes_alterados(caminho) == 1


def test_mesma_chave_com_conteudo_diferente_conflita_sem_mutacao(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    cliente = cliente_para(caminho)
    chave = str(uuid4())
    cliente.post(CAMINHO, headers={"Idempotency-Key": chave})
    alterar_um_segurado(caminho)

    resposta = cliente.post(
        CAMINHO,
        headers={"Idempotency-Key": chave, "Content-Type": "application/json"},
        content=b'{"forcar": true}',
    )

    assert resposta.status_code == 409
    assert resposta.headers["content-type"].startswith(TIPO_PROBLEMA)
    assert resposta.json()["codigo"] == "conflito_idempotencia"
    assert nomes_alterados(caminho) == 1


def test_execucao_ativa_impede_a_restauracao_sem_mutacao(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    alterar_um_segurado(caminho)
    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO execucao_preventiva (id, estado) VALUES (?, 'coletando')", [uuid4()]
        )

    resposta = cliente_para(caminho).post(CAMINHO, headers={"Idempotency-Key": str(uuid4())})

    assert resposta.status_code == 409
    assert resposta.headers["content-type"].startswith(TIPO_PROBLEMA)
    assert resposta.json()["codigo"] == "execucao_ativa_impede_restauracao"
    assert "execução preventiva ativa" in resposta.json()["ocorrencia"]
    assert nomes_alterados(caminho) == 1


def test_restauracao_antes_da_inicializacao_orienta_a_inicializar(tmp_path: Path) -> None:
    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()

    resposta = cliente_para(caminho).post(CAMINHO, headers={"Idempotency-Key": str(uuid4())})

    assert resposta.status_code == 409
    assert resposta.headers["content-type"].startswith(TIPO_PROBLEMA)
    assert resposta.json()["codigo"] == "nao_inicializado"
    assert "inicialização" in resposta.json()["proxima_acao"]


def test_restauracao_em_banco_sem_nenhuma_migracao_orienta_a_inicializar(tmp_path: Path) -> None:
    caminho = tmp_path / "central_preventiva.duckdb"

    resposta = cliente_para(caminho).post(CAMINHO, headers={"Idempotency-Key": str(uuid4())})

    assert resposta.status_code == 409
    assert resposta.headers["content-type"].startswith(TIPO_PROBLEMA)
    assert resposta.json()["codigo"] == "nao_inicializado"
    assert "inicialização" in resposta.json()["proxima_acao"]


def test_falha_na_transacao_preserva_o_conjunto_anterior_e_relata_a_falha(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    caminho = preparar_banco(tmp_path)
    alterar_um_segurado(caminho)

    def falhar(self: SemeadorDadosSinteticos) -> None:
        raise RuntimeError("falha simulada na transação")

    monkeypatch.setattr(modulo_semeador.SemeadorDadosSinteticos, "restaurar", falhar)

    resposta = cliente_para(caminho).post(CAMINHO, headers={"Idempotency-Key": str(uuid4())})

    assert resposta.status_code == 500
    assert resposta.headers["content-type"].startswith(TIPO_PROBLEMA)
    corpo = resposta.json()
    assert corpo["codigo"] == "falha_restauracao"
    assert corpo["ocorrencia"] and corpo["impacto"] and corpo["proxima_acao"]
    assert "falha simulada" not in str(corpo)
    assert nomes_alterados(caminho) == 1


def test_contrato_openapi_descreve_a_restauracao_em_portugues(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)

    documento = cliente_para(caminho).get("/openapi.json").json()

    operacao = documento["paths"][CAMINHO]["post"]
    assert operacao["summary"] == "Restaurar os dados sintéticos da demonstração"
    assert operacao["description"].startswith("Repõe o conjunto sintético versionado")
    assert operacao["responses"]["201"]["description"] == "Dados sintéticos restaurados."
    assert operacao["responses"]["409"]["description"] == (
        "Restauração recusada sem qualquer mutação."
    )
    propriedades = documento["components"]["schemas"]["RespostaRestauracao"]["properties"]
    assert set(propriedades) == {"status", "restaurado_em"}


def test_cors_libera_o_post_de_restauracao_para_a_origem_local(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)

    permitida = cliente_para(caminho).options(
        CAMINHO,
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Idempotency-Key",
        },
    )

    assert permitida.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
    assert "idempotency-key" in permitida.headers["access-control-allow-headers"].lower()
