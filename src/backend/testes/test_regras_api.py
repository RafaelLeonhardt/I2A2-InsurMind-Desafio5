"""Testes do recurso REST/JSON de gestão versionada de regras preventivas (REGRA-11..13)."""

from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.composicao.api import criar_aplicacao
from central_preventiva.composicao.configuracao import Configuracao

TIPO_PROBLEMA = "application/problem+json"

DADOS_CHUVA_VALIDOS = {
    "evento_tipo": "chuva_intensa",
    "limiar_meteorologico": 60.0,
    "area_aplicavel": "9990001",
    "apolice_tipo": "residencial",
    "cobertura_exigida": "alagamento",
    "antecedencia_horas": 48,
    "canal": "email",
}


def preparar_banco(tmp_path: Path) -> Path:
    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()
    return caminho


def inserir_regra(
    caminho: Path,
    evento_tipo: str = "chuva_intensa",
    limiar: float = 50.0,
    area_aplicavel: str = "9990001",
    apolice_tipo: str = "residencial",
    versao: int = 1,
    estado: str = "ativa",
) -> str:
    id_regra = str(uuid4())
    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO regras (id, evento_tipo, limiar_meteorologico, area_aplicavel, "
            "apolice_tipo, cobertura_exigida, antecedencia_horas, canal, versao, estado) "
            "VALUES (?, ?, ?, ?, ?, 'alagamento', 24, 'whatsapp', ?, ?)",
            [id_regra, evento_tipo, limiar, area_aplicavel, apolice_tipo, versao, estado],
        )
    return id_regra


def inserir_evento_sintetico(
    caminho: Path, tipo: str = "chuva_intensa", area: str = "9990001", intensidade: float = 72.5
) -> str:
    id_evento = str(uuid4())
    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO eventos_meteorologicos (id, tipo, area, periodo_inicio, periodo_fim, "
            "intensidade, proveniencia, instante_observado) VALUES "
            "(?, ?, ?, '2026-03-10 06:00:00', '2026-03-10 18:00:00', ?, 'sintetico', "
            "'2026-03-09 18:00:00')",
            [id_evento, tipo, area, intensidade],
        )
    return id_evento


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


def test_get_regras_lista_todas_as_versoes(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    inserir_regra(caminho, versao=1, estado="substituida")
    inserir_regra(caminho, versao=2, estado="ativa")

    resposta = cliente_para(caminho).get("/api/v1/regras")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert len(corpo["regras"]) == 2
    estados = {regra["estado"] for regra in corpo["regras"]}
    versoes = {regra["versao"] for regra in corpo["regras"]}
    assert estados == {"ativa", "substituida"}
    assert versoes == {1, 2}


def test_get_regra_por_id_encontrada_retorna_200(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    id_regra = inserir_regra(caminho)

    resposta = cliente_para(caminho).get(f"/api/v1/regras/{id_regra}")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["id"] == id_regra
    assert corpo["limiar_meteorologico"] == 50.0
    assert corpo["estado"] == "ativa"


def test_get_regra_inexistente_retorna_404(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)

    resposta = cliente_para(caminho).get(f"/api/v1/regras/{uuid4()}")

    assert resposta.status_code == 404
    assert resposta.headers["content-type"] == TIPO_PROBLEMA
    assert resposta.json()["codigo"] == "regra_inexistente"


def test_get_regra_com_id_malformado_retorna_422_nao_o_generico_do_fastapi(
    tmp_path: Path,
) -> None:
    caminho = preparar_banco(tmp_path)

    resposta = cliente_para(caminho).get("/api/v1/regras/nao-e-um-uuid")

    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "regra_id_invalido"


def test_post_testar_configuracao_valida_devolve_um_caso_por_cenario(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    id_regra = inserir_regra(caminho)
    inserir_evento_sintetico(caminho, intensidade=72.5)

    resposta = cliente_para(caminho).post(
        f"/api/v1/regras/{id_regra}/testar", json=DADOS_CHUVA_VALIDOS
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert len(corpo["casos"]) == 1
    caso = corpo["casos"][0]
    assert caso["relevante"] is True
    assert caso["motivo"] == "relevante"
    criterio_intensidade = next(
        c for c in caso["criterios"] if c["operando"].startswith("intensidade")
    )
    assert criterio_intensidade["valor_observado"] == "72.5 mm"
    assert criterio_intensidade["atende"] is True
    assert "60.0 mm" in criterio_intensidade["justificativa"]


def test_post_testar_configuracao_invalida_retorna_422_com_erros_por_campo(
    tmp_path: Path,
) -> None:
    caminho = preparar_banco(tmp_path)
    id_regra = inserir_regra(caminho)
    dados_invalidos = {**DADOS_CHUVA_VALIDOS, "limiar_meteorologico": -1.0}

    resposta = cliente_para(caminho).post(
        f"/api/v1/regras/{id_regra}/testar", json=dados_invalidos
    )

    assert resposta.status_code == 422
    corpo = resposta.json()
    assert corpo["codigo"] == "configuracao_invalida"
    assert any(erro["campo"] == "limiar_meteorologico" for erro in corpo["erros"])


def test_post_testar_sem_cenario_aplicavel_devolve_200_com_lista_vazia(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    id_regra = inserir_regra(caminho, evento_tipo="granizo", apolice_tipo="automovel")
    dados_granizo = {
        **DADOS_CHUVA_VALIDOS,
        "evento_tipo": "granizo",
        "apolice_tipo": "automovel",
    }

    resposta = cliente_para(caminho).post(
        f"/api/v1/regras/{id_regra}/testar", json=dados_granizo
    )

    assert resposta.status_code == 200
    assert resposta.json()["casos"] == []


def test_post_ativar_sem_idempotency_key_retorna_422(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    id_regra = inserir_regra(caminho)

    resposta = cliente_para(caminho).post(
        f"/api/v1/regras/{id_regra}/ativar",
        json={**DADOS_CHUVA_VALIDOS, "versao_esperada": 1},
    )

    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "idempotency_key_ausente"


def test_post_ativar_configuracao_valida_cria_nova_versao_e_preserva_a_anterior(
    tmp_path: Path,
) -> None:
    caminho = preparar_banco(tmp_path)
    id_regra = inserir_regra(caminho)
    inserir_evento_sintetico(caminho)

    resposta = cliente_para(caminho).post(
        f"/api/v1/regras/{id_regra}/ativar",
        json={**DADOS_CHUVA_VALIDOS, "versao_esperada": 1},
        headers={"Idempotency-Key": "chave-ativacao-1"},
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["versao"] == 2
    assert corpo["estado"] == "ativa"
    assert corpo["limiar_meteorologico"] == 60.0

    anterior = cliente_para(caminho).get(f"/api/v1/regras/{id_regra}")
    assert anterior.json()["estado"] == "substituida"


def test_post_ativar_versao_esperada_desatualizada_retorna_409(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    id_regra = inserir_regra(caminho)
    inserir_evento_sintetico(caminho)

    resposta = cliente_para(caminho).post(
        f"/api/v1/regras/{id_regra}/ativar",
        json={**DADOS_CHUVA_VALIDOS, "versao_esperada": 99},
        headers={"Idempotency-Key": "chave-ativacao-2"},
    )

    assert resposta.status_code == 409
    assert resposta.json()["codigo"] == "conflito_versao"


def test_post_ativar_duas_edicoes_concorrentes_com_a_mesma_versao_esperada_so_a_primeira_confirma(
    tmp_path: Path,
) -> None:
    """REGRA-11 literal: duas tentativas concorrentes informam a mesma versao_esperada (1);
    só a primeira transação válida é confirmada, a segunda recebe 409 sem mutar nada."""

    caminho = preparar_banco(tmp_path)
    id_regra = inserir_regra(caminho)
    inserir_evento_sintetico(caminho)
    cliente = cliente_para(caminho)
    corpo_requisicao = {**DADOS_CHUVA_VALIDOS, "versao_esperada": 1}

    primeira = cliente.post(
        f"/api/v1/regras/{id_regra}/ativar",
        json=corpo_requisicao,
        headers={"Idempotency-Key": "chave-concorrente-1"},
    )
    segunda = cliente.post(
        f"/api/v1/regras/{id_regra}/ativar",
        json=corpo_requisicao,
        headers={"Idempotency-Key": "chave-concorrente-2"},
    )

    assert primeira.status_code == 200
    assert primeira.json()["versao"] == 2
    assert segunda.status_code == 409
    assert segunda.json()["codigo"] == "conflito_versao"

    regras = cliente.get("/api/v1/regras").json()["regras"]
    assert len(regras) == 2
    assert {r["versao"] for r in regras} == {1, 2}


def test_post_ativar_repetido_com_mesma_chave_e_corpo_devolve_a_mesma_resposta(
    tmp_path: Path,
) -> None:
    caminho = preparar_banco(tmp_path)
    id_regra = inserir_regra(caminho)
    inserir_evento_sintetico(caminho)
    cliente = cliente_para(caminho)
    corpo_requisicao = {**DADOS_CHUVA_VALIDOS, "versao_esperada": 1}

    primeira = cliente.post(
        f"/api/v1/regras/{id_regra}/ativar",
        json=corpo_requisicao,
        headers={"Idempotency-Key": "chave-repetida"},
    )
    segunda = cliente.post(
        f"/api/v1/regras/{id_regra}/ativar",
        json=corpo_requisicao,
        headers={"Idempotency-Key": "chave-repetida"},
    )

    assert primeira.status_code == 200
    assert segunda.status_code == 200
    assert primeira.json() == segunda.json()

    regras = cliente.get("/api/v1/regras").json()["regras"]
    assert len(regras) == 2


def test_post_ativar_mesma_chave_com_corpo_diferente_retorna_409(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    id_regra = inserir_regra(caminho)
    inserir_evento_sintetico(caminho)
    cliente = cliente_para(caminho)

    cliente.post(
        f"/api/v1/regras/{id_regra}/ativar",
        json={**DADOS_CHUVA_VALIDOS, "versao_esperada": 1},
        headers={"Idempotency-Key": "chave-conflito"},
    )
    resposta = cliente.post(
        f"/api/v1/regras/{id_regra}/ativar",
        json={**DADOS_CHUVA_VALIDOS, "versao_esperada": 1, "limiar_meteorologico": 65.0},
        headers={"Idempotency-Key": "chave-conflito"},
    )

    assert resposta.status_code == 409
    assert resposta.json()["codigo"] == "conflito_idempotencia"


def test_post_ativar_regra_inexistente_retorna_404(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)

    resposta = cliente_para(caminho).post(
        f"/api/v1/regras/{uuid4()}/ativar",
        json={**DADOS_CHUVA_VALIDOS, "versao_esperada": 1},
        headers={"Idempotency-Key": "chave-inexistente"},
    )

    assert resposta.status_code == 404
    assert resposta.json()["codigo"] == "regra_inexistente"


def test_post_ativar_sem_cenario_aplicavel_retorna_422(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    id_regra = inserir_regra(caminho, evento_tipo="granizo", apolice_tipo="automovel")
    dados_granizo = {
        **DADOS_CHUVA_VALIDOS,
        "evento_tipo": "granizo",
        "apolice_tipo": "automovel",
        "versao_esperada": 1,
    }

    resposta = cliente_para(caminho).post(
        f"/api/v1/regras/{id_regra}/ativar",
        json=dados_granizo,
        headers={"Idempotency-Key": "chave-sem-cenario"},
    )

    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "nenhum_cenario_aplicavel"
