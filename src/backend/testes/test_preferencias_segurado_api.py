"""Testes do recurso REST/JSON de atualização de preferências do segurado ativo
(PREFS-01..07, 5.6).
"""

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


def inserir_segurado(
    caminho: Path,
    canal_preferido: str = "whatsapp",
    participa_de_alertas: bool = True,
) -> str:
    id_segurado = str(uuid4())
    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO segurados (id, nome, codigo_ibge_area, canal_preferido, "
            "participa_de_alertas) VALUES (?, 'Pessoa Teste', '9990001', ?, ?)",
            [id_segurado, canal_preferido, participa_de_alertas],
        )
    return id_segurado


def configuracao_para(caminho: Path) -> Configuracao:
    return Configuracao(
        host_api="127.0.0.1",
        origem_frontend="http://127.0.0.1:5151",
        caminho_banco=caminho,
        url_base_inmet="https://inmet.exemplo.invalido",
        _env_file=None,
    )


def cliente_para(caminho: Path) -> TestClient:
    return TestClient(criar_aplicacao(configuracao_para(caminho)))


def test_get_preferencias_encontrado_retorna_200(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    id_segurado = inserir_segurado(caminho, canal_preferido="sms", participa_de_alertas=False)

    resposta = cliente_para(caminho).get(f"/api/v1/segurados/{id_segurado}/preferencias")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["segurado_id"] == id_segurado
    assert corpo["canal_preferido"] == "sms"
    assert corpo["participa_de_alertas"] is False
    assert corpo["versao"] == 1


def test_get_preferencias_segurado_inexistente_retorna_404(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)

    resposta = cliente_para(caminho).get(f"/api/v1/segurados/{uuid4()}/preferencias")

    assert resposta.status_code == 404
    assert resposta.headers["content-type"] == TIPO_PROBLEMA
    assert resposta.json()["codigo"] == "segurado_inexistente"


def test_get_preferencias_com_id_malformado_retorna_422(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)

    resposta = cliente_para(caminho).get("/api/v1/segurados/nao-e-um-uuid/preferencias")

    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "segurado_id_invalido"


def test_put_preferencias_alteracao_valida_retorna_200_e_persiste(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    id_segurado = inserir_segurado(caminho, canal_preferido="whatsapp")

    resposta = cliente_para(caminho).put(
        f"/api/v1/segurados/{id_segurado}/preferencias",
        json={"canal_preferido": "sms", "participa_de_alertas": False, "versao_esperada": 1},
        headers={"Idempotency-Key": "chave-1"},
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["segurado_id"] == id_segurado
    assert corpo["canal_preferido"] == "sms"
    assert corpo["participa_de_alertas"] is False
    assert corpo["versao"] == 2

    consulta = cliente_para(caminho).get(f"/api/v1/segurados/{id_segurado}/preferencias")
    assert consulta.json() == corpo


def test_put_preferencias_versao_esperada_desatualizada_retorna_409(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    id_segurado = inserir_segurado(caminho)

    resposta = cliente_para(caminho).put(
        f"/api/v1/segurados/{id_segurado}/preferencias",
        json={"canal_preferido": "sms", "participa_de_alertas": False, "versao_esperada": 99},
        headers={"Idempotency-Key": "chave-1"},
    )

    assert resposta.status_code == 409
    assert resposta.json()["codigo"] == "conflito_versao"


def test_put_preferencias_duas_edicoes_concorrentes_so_a_primeira_confirma(
    tmp_path: Path,
) -> None:
    """Edge case da spec: duas abas com a mesma `versao_esperada` — só a primeira
    confirma, a segunda recebe `409`, mesmo padrão de 2.4/3.2."""

    caminho = preparar_banco(tmp_path)
    id_segurado = inserir_segurado(caminho)
    cliente = cliente_para(caminho)
    corpo_requisicao = {
        "canal_preferido": "sms",
        "participa_de_alertas": False,
        "versao_esperada": 1,
    }

    primeira = cliente.put(
        f"/api/v1/segurados/{id_segurado}/preferencias",
        json=corpo_requisicao,
        headers={"Idempotency-Key": "chave-concorrente-1"},
    )
    segunda = cliente.put(
        f"/api/v1/segurados/{id_segurado}/preferencias",
        json=corpo_requisicao,
        headers={"Idempotency-Key": "chave-concorrente-2"},
    )

    assert primeira.status_code == 200
    assert primeira.json()["versao"] == 2
    assert segunda.status_code == 409
    assert segunda.json()["codigo"] == "conflito_versao"


def test_put_preferencias_repetido_com_mesma_chave_e_corpo_devolve_a_mesma_resposta(
    tmp_path: Path,
) -> None:
    caminho = preparar_banco(tmp_path)
    id_segurado = inserir_segurado(caminho)
    cliente = cliente_para(caminho)
    corpo_requisicao = {
        "canal_preferido": "sms",
        "participa_de_alertas": False,
        "versao_esperada": 1,
    }

    primeira = cliente.put(
        f"/api/v1/segurados/{id_segurado}/preferencias",
        json=corpo_requisicao,
        headers={"Idempotency-Key": "chave-repetida"},
    )
    segunda = cliente.put(
        f"/api/v1/segurados/{id_segurado}/preferencias",
        json=corpo_requisicao,
        headers={"Idempotency-Key": "chave-repetida"},
    )

    assert primeira.status_code == 200
    assert segunda.status_code == 200
    assert primeira.json() == segunda.json()

    consulta = cliente.get(f"/api/v1/segurados/{id_segurado}/preferencias")
    assert consulta.json()["versao"] == 2


def test_put_preferencias_mesma_chave_com_corpo_diferente_retorna_409(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    id_segurado = inserir_segurado(caminho)
    cliente = cliente_para(caminho)

    cliente.put(
        f"/api/v1/segurados/{id_segurado}/preferencias",
        json={"canal_preferido": "sms", "participa_de_alertas": False, "versao_esperada": 1},
        headers={"Idempotency-Key": "chave-conflito"},
    )
    resposta = cliente.put(
        f"/api/v1/segurados/{id_segurado}/preferencias",
        json={"canal_preferido": "email", "participa_de_alertas": False, "versao_esperada": 1},
        headers={"Idempotency-Key": "chave-conflito"},
    )

    assert resposta.status_code == 409
    assert resposta.json()["codigo"] == "conflito_idempotencia"


def test_put_preferencias_segurado_inexistente_retorna_404(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)

    resposta = cliente_para(caminho).put(
        f"/api/v1/segurados/{uuid4()}/preferencias",
        json={"canal_preferido": "sms", "participa_de_alertas": False, "versao_esperada": 1},
        headers={"Idempotency-Key": "chave-1"},
    )

    assert resposta.status_code == 404
    assert resposta.json()["codigo"] == "segurado_inexistente"


def test_put_preferencias_com_id_malformado_retorna_422(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)

    resposta = cliente_para(caminho).put(
        "/api/v1/segurados/nao-e-um-uuid/preferencias",
        json={"canal_preferido": "sms", "participa_de_alertas": False, "versao_esperada": 1},
        headers={"Idempotency-Key": "chave-1"},
    )

    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "segurado_id_invalido"


def test_put_preferencias_canal_invalido_retorna_422(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    id_segurado = inserir_segurado(caminho)

    resposta = cliente_para(caminho).put(
        f"/api/v1/segurados/{id_segurado}/preferencias",
        json={
            "canal_preferido": "pombo-correio",
            "participa_de_alertas": False,
            "versao_esperada": 1,
        },
        headers={"Idempotency-Key": "chave-1"},
    )

    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "canal_preferido_invalido"


def test_put_preferencias_sem_idempotency_key_retorna_422(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    id_segurado = inserir_segurado(caminho)

    resposta = cliente_para(caminho).put(
        f"/api/v1/segurados/{id_segurado}/preferencias",
        json={"canal_preferido": "sms", "participa_de_alertas": False, "versao_esperada": 1},
    )

    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "idempotency_key_ausente"


def test_put_preferencias_para_o_mesmo_canal_ja_vigente_e_alteracao_valida(
    tmp_path: Path,
) -> None:
    """Edge case da spec: mesmo valor já vigente é tratado como alteração válida
    idempotente normal, sem erro nem efeito colateral extra."""

    caminho = preparar_banco(tmp_path)
    id_segurado = inserir_segurado(caminho, canal_preferido="whatsapp", participa_de_alertas=True)

    resposta = cliente_para(caminho).put(
        f"/api/v1/segurados/{id_segurado}/preferencias",
        json={"canal_preferido": "whatsapp", "participa_de_alertas": True, "versao_esperada": 1},
        headers={"Idempotency-Key": "chave-1"},
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["canal_preferido"] == "whatsapp"
    assert corpo["participa_de_alertas"] is True
    assert corpo["versao"] == 2
