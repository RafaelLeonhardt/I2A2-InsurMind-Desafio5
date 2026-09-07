"""Testes do recurso REST/JSON de início e acompanhamento da execução preventiva
(RUNNER-01..09)."""

import time
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.adaptadores.persistencia.repositorio_execucao_preventiva import (
    RepositorioExecucaoPreventiva,
)
from central_preventiva.composicao.api import criar_aplicacao
from central_preventiva.composicao.configuracao import Configuracao
from central_preventiva.dominio.estados_execucao import EstadoExecucao

CAMINHO_EXECUCOES = "/api/v1/execucoes"
TIPO_PROBLEMA = "application/problem+json"
AREA = "9990001"


@pytest.fixture(autouse=True)
def _bloquear_chamadas_de_rede_reais(monkeypatch: pytest.MonkeyPatch) -> None:
    """Impede qualquer chamada HTTP real do `ClienteInmet` composto neste módulo de teste."""

    async def _send_bloqueado(
        self: httpx.AsyncClient, request: httpx.Request, **_: object
    ) -> httpx.Response:
        raise AssertionError(f"chamada de rede real bloqueada em teste: {request.url}")

    monkeypatch.setattr(httpx.AsyncClient, "send", _send_bloqueado)


def permitir_resposta_valida(monkeypatch: pytest.MonkeyPatch, chuva: str = "72.5") -> None:
    """Libera uma resposta INMET válida programada, com chuva acima do limiar de teste."""

    async def _send_valido(
        self: httpx.AsyncClient, request: httpx.Request, **_: object
    ) -> httpx.Response:
        return httpx.Response(
            200,
            json={"CHUVA": chuva, "DT_MEDICAO": "2026-08-30", "HR_MEDICAO": "1200"},
            request=request,
        )

    monkeypatch.setattr(httpx.AsyncClient, "send", _send_valido)


def preparar_banco(tmp_path: Path) -> Path:
    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()
    return caminho


def inserir_area_monitorada(caminho: Path) -> str:
    id_area = str(uuid4())
    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO areas_monitoradas_inmet "
            "(id, codigo_estacao_inmet, nome_estacao, codigo_ibge_area, ativa) "
            "VALUES (?, 'A001', 'Estação de Teste', ?, true)",
            [id_area, AREA],
        )
    return id_area


def inserir_regra(caminho: Path, limiar: float = 50.0) -> str:
    id_regra = str(uuid4())
    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO regras (id, evento_tipo, limiar_meteorologico, area_aplicavel, "
            "apolice_tipo, cobertura_exigida, antecedencia_horas, canal, versao, estado) "
            "VALUES (?, 'chuva_intensa', ?, ?, 'residencial', 'alagamento', 24, "
            "'whatsapp', 1, 'ativa')",
            [id_regra, limiar, AREA],
        )
    return id_regra


def inserir_segurado(caminho: Path, nome: str = "Pessoa Teste") -> str:
    id_segurado = str(uuid4())
    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO segurados (id, nome, codigo_ibge_area, canal_preferido, "
            "participa_de_alertas) VALUES (?, ?, ?, 'whatsapp', true)",
            [id_segurado, nome, AREA],
        )
    return id_segurado


def inserir_apolice(caminho: Path, segurado_id: str) -> str:
    id_apolice = str(uuid4())
    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO apolices (id, segurado_id, numero, tipo, situacao, "
            "vigencia_inicio, vigencia_fim, coberturas, endereco_risco_sintetico, "
            "codigo_ibge_area) VALUES (?, ?, 'NUM-TESTE', 'residencial', 'ativa', "
            "'2026-01-01', '2026-12-31', ['alagamento'], 'Rua Teste', ?)",
            [id_apolice, segurado_id, AREA],
        )
    return id_apolice


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


def aguardar_conclusao(cliente: TestClient, execucao_id: str, timeout: float = 2.0) -> dict:
    """Espera a orquestração em segundo plano sair de `coletando`/`avaliando_elegibilidade`."""

    limite = time.monotonic() + timeout
    corpo = {}
    while time.monotonic() < limite:
        corpo = cliente.get(f"{CAMINHO_EXECUCOES}/{execucao_id}").json()
        if corpo["estado"] not in {"coletando", "avaliando_elegibilidade"}:
            return corpo
        time.sleep(0.01)
    raise AssertionError(f"execução '{execucao_id}' não concluiu a tempo: {corpo}")


def test_post_sem_idempotency_key_e_recusado(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)

    resposta = cliente_para(caminho).post(CAMINHO_EXECUCOES, json={"area_id": str(uuid4())})

    assert resposta.status_code == 422
    assert resposta.headers["content-type"].startswith(TIPO_PROBLEMA)
    assert resposta.json()["codigo"] == "idempotency_key_ausente"


def test_post_com_area_desconhecida_e_recusado(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)

    resposta = cliente_para(caminho).post(
        CAMINHO_EXECUCOES,
        json={"area_id": str(uuid4())},
        headers={"Idempotency-Key": "chave-1"},
    )

    assert resposta.status_code == 404
    assert resposta.headers["content-type"].startswith(TIPO_PROBLEMA)
    assert resposta.json()["codigo"] == "area_monitorada_desconhecida"


def test_post_com_chave_nova_retorna_202_com_execucao_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    caminho = preparar_banco(tmp_path)
    area_id = inserir_area_monitorada(caminho)
    permitir_resposta_valida(monkeypatch)

    resposta = cliente_para(caminho).post(
        CAMINHO_EXECUCOES,
        json={"area_id": area_id},
        headers={"Idempotency-Key": "chave-1"},
    )

    assert resposta.status_code == 202
    execucao_id = resposta.json()["execucao_id"]
    snapshot = RepositorioExecucaoPreventiva(caminho).buscar(UUID(execucao_id))
    assert snapshot is not None


def test_repetir_a_mesma_idempotency_key_devolve_o_mesmo_execucao_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    caminho = preparar_banco(tmp_path)
    area_id = inserir_area_monitorada(caminho)
    permitir_resposta_valida(monkeypatch)
    cliente = cliente_para(caminho)
    corpo = {"area_id": area_id}

    primeira = cliente.post(CAMINHO_EXECUCOES, json=corpo, headers={"Idempotency-Key": "chave-x"})
    segunda = cliente.post(CAMINHO_EXECUCOES, json=corpo, headers={"Idempotency-Key": "chave-x"})

    assert primeira.status_code == 202
    assert segunda.status_code == 202
    assert primeira.json()["execucao_id"] == segunda.json()["execucao_id"]


def test_repetir_a_chave_com_corpo_diferente_retorna_409(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    caminho = preparar_banco(tmp_path)
    area_1 = inserir_area_monitorada(caminho)
    area_2 = inserir_area_monitorada(caminho)
    permitir_resposta_valida(monkeypatch)
    cliente = cliente_para(caminho)

    cliente.post(
        CAMINHO_EXECUCOES, json={"area_id": area_1}, headers={"Idempotency-Key": "chave-y"}
    )
    resposta = cliente.post(
        CAMINHO_EXECUCOES, json={"area_id": area_2}, headers={"Idempotency-Key": "chave-y"}
    )

    assert resposta.status_code == 409
    assert resposta.headers["content-type"].startswith(TIPO_PROBLEMA)
    assert resposta.json()["codigo"] == "conflito_idempotencia"


def test_get_execucao_inexistente_retorna_404(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)

    resposta = cliente_para(caminho).get(f"{CAMINHO_EXECUCOES}/{uuid4()}")

    assert resposta.status_code == 404
    assert resposta.headers["content-type"].startswith(TIPO_PROBLEMA)
    assert resposta.json()["codigo"] == "execucao_inexistente"


def test_get_execucao_com_id_malformado_retorna_422(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)

    resposta = cliente_para(caminho).get(f"{CAMINHO_EXECUCOES}/nao-e-um-uuid")

    assert resposta.status_code == 422
    assert resposta.headers["content-type"].startswith(TIPO_PROBLEMA)
    assert resposta.json()["codigo"] == "execucao_id_invalido"


def test_get_execucao_sem_risco_nao_traz_previa_de_publico(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    execucao_id = RepositorioExecucaoPreventiva(caminho).criar(EstadoExecucao.SEM_RISCO)

    resposta = cliente_para(caminho).get(f"{CAMINHO_EXECUCOES}/{execucao_id}")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["estado"] == "sem_risco"
    assert corpo["publico_elegivel_total"] is None
    assert corpo["publico_elegivel_previa"] == []


def test_get_execucao_sem_elegiveis_nao_traz_previa_de_publico(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    execucao_id = RepositorioExecucaoPreventiva(caminho).criar(EstadoExecucao.SEM_ELEGIVEIS)

    resposta = cliente_para(caminho).get(f"{CAMINHO_EXECUCOES}/{execucao_id}")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["estado"] == "sem_elegiveis"
    assert corpo["publico_elegivel_total"] is None
    assert corpo["publico_elegivel_previa"] == []


def test_get_execucao_reflete_marcos_persistidos_na_ordem(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    repositorio = RepositorioExecucaoPreventiva(caminho)
    execucao_id = repositorio.criar(EstadoExecucao.COLETANDO)
    repositorio.registrar_marco(execucao_id, "coleta_concluida")
    repositorio.transicionar(execucao_id, 1, EstadoExecucao.SEM_RISCO)
    repositorio.registrar_marco(execucao_id, "sem_risco")

    resposta = cliente_para(caminho).get(f"{CAMINHO_EXECUCOES}/{execucao_id}")

    corpo = resposta.json()
    assert [m["marco"] for m in corpo["marcos"]] == ["coleta_concluida", "sem_risco"]


def test_fluxo_completo_via_post_chega_em_aguardando_geracao_com_previa_do_publico(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Prova de ponta a ponta: `POST` real dispara a cadeia completa (coleta com resposta
    INMET válida acima do limiar, risco relevante, um segurado elegível) até o checkpoint
    de geração, sem nenhum clique manual intermediário (RUNNER-01, RUNNER-04, RUNNER-05)."""

    caminho = preparar_banco(tmp_path)
    area_id = inserir_area_monitorada(caminho)
    inserir_regra(caminho, limiar=50.0)
    segurado_id = inserir_segurado(caminho, nome="Pessoa Elegível de Teste")
    inserir_apolice(caminho, segurado_id)
    permitir_resposta_valida(monkeypatch, chuva="72.5")
    cliente = cliente_para(caminho)

    resposta = cliente.post(
        CAMINHO_EXECUCOES,
        json={"area_id": area_id},
        headers={"Idempotency-Key": "chave-fluxo-completo"},
    )
    assert resposta.status_code == 202
    execucao_id = resposta.json()["execucao_id"]

    corpo = aguardar_conclusao(cliente, execucao_id)

    assert corpo["estado"] == "aguardando_geracao"
    assert corpo["publico_elegivel_total"] == 1
    assert len(corpo["publico_elegivel_previa"]) == 1
    assert corpo["publico_elegivel_previa"][0]["nome_segurado"] == "Pessoa Elegível de Teste"
    marcos = [m["marco"] for m in corpo["marcos"]]
    assert marcos == [
        "coleta_concluida",
        "avaliacao_risco_concluida",
        "avaliacao_elegibilidade_concluida",
        "publico_elegivel_formado",
        "aguardando_geracao",
    ]
