"""Testes do recurso REST/JSON de coleta e consulta meteorológica do INMET."""

import time
from datetime import datetime, timedelta
from math import ceil
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.composicao.api import criar_aplicacao
from central_preventiva.composicao.configuracao import Configuracao

CAMINHO_COLETAS = "/api/v1/meteorologia/coletas"
CAMINHO_EVENTOS = "/api/v1/meteorologia/eventos"
CAMINHO_SINCRONIZACOES = "/api/v1/meteorologia/sincronizacoes"
TIPO_PROBLEMA = "application/problem+json"
ORIGEM_CONFIGURADA = "http://127.0.0.1:5151"
IDENTIFICADOR_CENARIO_GRANIZO = "granizo-demonstrativo"


def caminho_nova_tentativa(sincronizacao_id: str) -> str:
    return f"/api/v1/meteorologia/{sincronizacao_id}/nova-tentativa"


def caminho_ativar_cenario_sintetico(identificador: str) -> str:
    return f"/api/v1/meteorologia/cenarios-sinteticos/{identificador}/ativar"


@pytest.fixture(autouse=True)
def _bloquear_chamadas_de_rede_reais(monkeypatch: pytest.MonkeyPatch) -> None:
    """Impede qualquer chamada HTTP real do `ClienteInmet` composto neste módulo de teste."""

    async def _send_bloqueado(
        self: httpx.AsyncClient, request: httpx.Request, **_: object
    ) -> httpx.Response:
        raise AssertionError(f"chamada de rede real bloqueada em teste: {request.url}")

    monkeypatch.setattr(httpx.AsyncClient, "send", _send_bloqueado)


def configuracao_para(caminho: Path) -> Configuracao:
    """Monta a configuração local determinística, sem depender do `.env` real."""

    return Configuracao(
        host_api="127.0.0.1",
        origem_frontend=ORIGEM_CONFIGURADA,
        caminho_banco=caminho,
        url_base_inmet="https://inmet.exemplo.invalido",
        _env_file=None,
    )


def preparar_banco(tmp_path: Path) -> Path:
    """Aplica as migrações em um banco temporário, sem semear dados sintéticos."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()
    return caminho


def inserir_area_monitorada(caminho: Path, codigo_estacao: str, codigo_ibge_area: str) -> str:
    """Insere uma área monitorada de teste e devolve o seu id."""

    id_area = str(uuid4())
    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO areas_monitoradas_inmet "
            "(id, codigo_estacao_inmet, nome_estacao, codigo_ibge_area, ativa) "
            "VALUES (?, ?, 'Estação de Teste', ?, true)",
            [id_area, codigo_estacao, codigo_ibge_area],
        )
    return id_area


def cliente_para(caminho: Path) -> TestClient:
    """Cria o cliente HTTP da aplicação composta sobre o banco indicado."""

    return TestClient(criar_aplicacao(configuracao_para(caminho)))


def permitir_resposta_valida(monkeypatch: pytest.MonkeyPatch) -> list[httpx.Request]:
    """Libera uma resposta INMET válida programada, registrando as requisições recebidas."""

    chamadas: list[httpx.Request] = []

    async def _send_valido(
        self: httpx.AsyncClient, request: httpx.Request, **_: object
    ) -> httpx.Response:
        chamadas.append(request)
        return httpx.Response(
            200,
            json={"CHUVA": "42.0", "DT_MEDICAO": "2026-08-30", "HR_MEDICAO": "1200"},
            request=request,
        )

    monkeypatch.setattr(httpx.AsyncClient, "send", _send_valido)
    return chamadas


def test_post_sem_idempotency_key_e_recusado(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    area_id = inserir_area_monitorada(caminho, "A701", "9990001")

    resposta = cliente_para(caminho).post(CAMINHO_COLETAS, json={"area_id": area_id})

    assert resposta.status_code == 422
    assert resposta.headers["content-type"].startswith(TIPO_PROBLEMA)
    assert resposta.json()["codigo"] == "idempotency_key_ausente"


def test_post_com_idempotency_key_nova_retorna_202(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    caminho = preparar_banco(tmp_path)
    area_id = inserir_area_monitorada(caminho, "A701", "9990001")
    permitir_resposta_valida(monkeypatch)

    resposta = cliente_para(caminho).post(
        CAMINHO_COLETAS,
        json={"area_id": area_id},
        headers={"Idempotency-Key": str(uuid4())},
    )

    assert resposta.status_code == 202
    corpo = resposta.json()
    assert corpo["estado"] == "concluido"
    assert corpo["registros_validos"] == 1


def test_repetir_a_mesma_idempotency_key_devolve_a_resposta_ja_registrada_sem_nova_chamada(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    caminho = preparar_banco(tmp_path)
    area_id = inserir_area_monitorada(caminho, "A701", "9990001")
    chamadas = permitir_resposta_valida(monkeypatch)
    cliente = cliente_para(caminho)
    chave = str(uuid4())

    primeira = cliente.post(
        CAMINHO_COLETAS, json={"area_id": area_id}, headers={"Idempotency-Key": chave}
    )
    segunda = cliente.post(
        CAMINHO_COLETAS, json={"area_id": area_id}, headers={"Idempotency-Key": chave}
    )

    assert primeira.status_code == 202
    assert segunda.status_code == 202
    assert primeira.json() == segunda.json()
    assert len(chamadas) == 1


def test_post_manual_e_aceito_independentemente_do_agendamento_automatico_em_curso(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """INMET-04: com o `lifespan` real ativo (agendador automático rodando), o `POST`

    manual ainda é aceito e produz uma tentativa correlacionada distinta da automática —
    cobre também o edge case de duas coletas quase simultâneas persistidas separadamente.
    """

    caminho = preparar_banco(tmp_path)
    area_id = inserir_area_monitorada(caminho, "A701", "9990001")
    permitir_resposta_valida(monkeypatch)

    with TestClient(criar_aplicacao(configuracao_para(caminho))) as cliente:
        resposta_manual = cliente.post(
            CAMINHO_COLETAS,
            json={"area_id": area_id},
            headers={"Idempotency-Key": str(uuid4())},
        )
        assert resposta_manual.status_code == 202

        origens: set[str] = set()
        resultados: list[dict[str, object]] = []
        for _ in range(40):
            resultados = cliente.get(CAMINHO_SINCRONIZACOES).json()["resultados_anteriores"]
            origens = {str(item["origem"]) for item in resultados}
            if {"automatica", "manual"} <= origens:
                break
            time.sleep(0.05)

        assert {"automatica", "manual"} <= origens
        ids_requisicao = {item["requisicao_id"] for item in resultados}
        assert len(ids_requisicao) == len(resultados)


def test_post_com_area_desconhecida_e_recusado(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)

    resposta = cliente_para(caminho).post(
        CAMINHO_COLETAS,
        json={"area_id": str(uuid4())},
        headers={"Idempotency-Key": str(uuid4())},
    )

    assert resposta.status_code == 404
    assert resposta.headers["content-type"].startswith(TIPO_PROBLEMA)
    assert resposta.json()["codigo"] == "area_monitorada_desconhecida"


def test_get_eventos_retorna_200_com_os_campos_esperados_apos_coleta(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    caminho = preparar_banco(tmp_path)
    area_id = inserir_area_monitorada(caminho, "A701", "9990001")
    permitir_resposta_valida(monkeypatch)
    cliente = cliente_para(caminho)
    cliente.post(
        CAMINHO_COLETAS, json={"area_id": area_id}, headers={"Idempotency-Key": str(uuid4())}
    )

    resposta = cliente.get(CAMINHO_EVENTOS)

    assert resposta.status_code == 200
    eventos = resposta.json()["eventos"]
    assert len(eventos) == 1
    campos_esperados = {
        "id",
        "tipo",
        "area",
        "periodo_inicio",
        "periodo_fim",
        "intensidade",
        "proveniencia",
        "instante_observado",
    }
    assert set(eventos[0]) == campos_esperados
    assert eventos[0]["tipo"] == "chuva_intensa"
    assert eventos[0]["proveniencia"] == "real_inmet"


def test_get_eventos_sem_nenhuma_coleta_devolve_lista_vazia(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)

    resposta = cliente_para(caminho).get(CAMINHO_EVENTOS)

    assert resposta.status_code == 200
    assert resposta.json() == {"eventos": []}


def test_get_sincronizacoes_retorna_200_com_os_campos_esperados_apos_coleta(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    caminho = preparar_banco(tmp_path)
    area_id = inserir_area_monitorada(caminho, "A701", "9990001")
    permitir_resposta_valida(monkeypatch)
    cliente = cliente_para(caminho)
    cliente.post(
        CAMINHO_COLETAS, json={"area_id": area_id}, headers={"Idempotency-Key": str(uuid4())}
    )

    resposta = cliente.get(CAMINHO_SINCRONIZACOES)

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert set(corpo) == {
        "ultima_tentativa",
        "ultima_valida",
        "proxima_consulta",
        "resultados_anteriores",
    }
    assert corpo["ultima_tentativa"]["estado"] == "concluido"
    assert corpo["ultima_valida"]["estado"] == "concluido"
    assert corpo["ultima_tentativa"]["limite_tentativas"] == 3
    assert len(corpo["ultima_tentativa"]["tentativas"]) == 1
    assert corpo["ultima_tentativa"]["tentativas"][0]["numero_tentativa"] == 1
    assert corpo["ultima_tentativa"]["tentativas"][0]["codigo_resultado"] == "sucesso"
    iniciado_em = datetime.fromisoformat(corpo["ultima_tentativa"]["iniciado_em"])
    proxima_consulta = datetime.fromisoformat(corpo["proxima_consulta"])
    # 900s hardcoded (não importado de INTERVALO_SEGUNDOS_COLETA): referenciar a própria
    # constante de produção faria este teste acompanhar qualquer mutação no intervalo,
    # sem nunca discriminar uma regressão real (15 minutos, INMET-03/INMET-15).
    assert proxima_consulta == iniciado_em + timedelta(seconds=900)
    assert len(corpo["resultados_anteriores"]) == 1


def test_get_sincronizacoes_sem_nenhuma_coleta_devolve_marcos_nulos(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)

    resposta = cliente_para(caminho).get(CAMINHO_SINCRONIZACOES)

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["ultima_tentativa"] is None
    assert corpo["ultima_valida"] is None
    assert corpo["proxima_consulta"] is None
    assert corpo["resultados_anteriores"] == []


def test_consultas_de_eventos_e_sincronizacoes_respondem_em_ate_1s_no_percentil_95(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """INMET-15: a consulta usando só dados persistidos responde em até 1s no p95."""

    caminho = preparar_banco(tmp_path)
    area_id = inserir_area_monitorada(caminho, "A701", "9990001")
    permitir_resposta_valida(monkeypatch)
    cliente = cliente_para(caminho)
    cliente.post(
        CAMINHO_COLETAS, json={"area_id": area_id}, headers={"Idempotency-Key": str(uuid4())}
    )

    def p95_segundos(caminho_recurso: str, repeticoes: int = 20) -> float:
        duracoes: list[float] = []
        for _ in range(repeticoes):
            inicio = time.perf_counter()
            resposta = cliente.get(caminho_recurso)
            duracoes.append(time.perf_counter() - inicio)
            assert resposta.status_code == 200
        duracoes.sort()
        indice_p95 = max(0, ceil(0.95 * len(duracoes)) - 1)
        return duracoes[indice_p95]

    assert p95_segundos(CAMINHO_EVENTOS) < 1.0
    assert p95_segundos(CAMINHO_SINCRONIZACOES) < 1.0


def test_cors_libera_o_post_de_coletas_para_a_origem_configurada(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)

    resposta = cliente_para(caminho).options(
        CAMINHO_COLETAS,
        headers={
            "Origin": ORIGEM_CONFIGURADA,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type, Idempotency-Key",
        },
    )

    assert resposta.headers.get("access-control-allow-origin") == ORIGEM_CONFIGURADA


def test_cors_recusa_uma_origem_nao_configurada_para_coletas(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)

    resposta = cliente_para(caminho).options(
        CAMINHO_COLETAS,
        headers={
            "Origin": "http://evil.example",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type, Idempotency-Key",
        },
    )

    assert "access-control-allow-origin" not in resposta.headers


def forcar_timeout_persistente(monkeypatch: pytest.MonkeyPatch) -> None:
    """Faz toda chamada HTTP real falhar por timeout, esgotando as 3 tentativas."""

    async def _send_timeout(
        self: httpx.AsyncClient, request: httpx.Request, **_: object
    ) -> httpx.Response:
        raise httpx.TimeoutException(f"timeout simulado: {request.url}")

    monkeypatch.setattr(httpx.AsyncClient, "send", _send_timeout)


def criar_sincronizacao_falha(caminho: Path, area_id: str, monkeypatch: pytest.MonkeyPatch) -> str:
    """Esgota as 3 tentativas de uma coleta manual e devolve o id da sincronização falha."""

    forcar_timeout_persistente(monkeypatch)
    resposta = cliente_para(caminho).post(
        CAMINHO_COLETAS, json={"area_id": area_id}, headers={"Idempotency-Key": str(uuid4())}
    )
    assert resposta.json()["estado"] == "falha"
    return str(resposta.json()["id"])


def test_nova_tentativa_sem_idempotency_key_e_recusada(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    caminho = preparar_banco(tmp_path)
    area_id = inserir_area_monitorada(caminho, "A701", "9990001")
    sincronizacao_id = criar_sincronizacao_falha(caminho, area_id, monkeypatch)

    resposta = cliente_para(caminho).post(caminho_nova_tentativa(sincronizacao_id))

    assert resposta.status_code == 422
    assert resposta.headers["content-type"].startswith(TIPO_PROBLEMA)
    assert resposta.json()["codigo"] == "idempotency_key_ausente"


def test_nova_tentativa_com_idempotency_key_nova_retorna_202(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    caminho = preparar_banco(tmp_path)
    area_id = inserir_area_monitorada(caminho, "A701", "9990001")
    sincronizacao_id = criar_sincronizacao_falha(caminho, area_id, monkeypatch)

    permitir_resposta_valida(monkeypatch)
    resposta = cliente_para(caminho).post(
        caminho_nova_tentativa(sincronizacao_id),
        headers={"Idempotency-Key": str(uuid4())},
    )

    assert resposta.status_code == 202
    corpo = resposta.json()
    assert corpo["id"] != sincronizacao_id
    assert corpo["estado"] == "concluido"


def test_repetir_a_mesma_idempotency_key_da_nova_tentativa_nao_duplica(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    caminho = preparar_banco(tmp_path)
    area_id = inserir_area_monitorada(caminho, "A701", "9990001")
    sincronizacao_id = criar_sincronizacao_falha(caminho, area_id, monkeypatch)
    permitir_resposta_valida(monkeypatch)
    cliente = cliente_para(caminho)
    chave = str(uuid4())

    primeira = cliente.post(
        caminho_nova_tentativa(sincronizacao_id), headers={"Idempotency-Key": chave}
    )
    segunda = cliente.post(
        caminho_nova_tentativa(sincronizacao_id), headers={"Idempotency-Key": chave}
    )

    assert primeira.status_code == 202
    assert segunda.status_code == 202
    assert primeira.json() == segunda.json()


def test_nova_tentativa_com_sincronizacao_inexistente_e_recusada(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)

    resposta = cliente_para(caminho).post(
        caminho_nova_tentativa(str(uuid4())),
        headers={"Idempotency-Key": str(uuid4())},
    )

    assert resposta.status_code == 404
    assert resposta.headers["content-type"].startswith(TIPO_PROBLEMA)
    assert resposta.json()["codigo"] == "sincronizacao_desconhecida"


def test_ativar_cenario_sintetico_sem_idempotency_key_e_recusado(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    area_id = inserir_area_monitorada(caminho, "A701", "9990001")

    resposta = cliente_para(caminho).post(
        caminho_ativar_cenario_sintetico(IDENTIFICADOR_CENARIO_GRANIZO),
        json={"area_id": area_id},
    )

    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "idempotency_key_ausente"


def test_ativar_cenario_sintetico_com_idempotency_key_nova_cria_evento_sintetico(
    tmp_path: Path,
) -> None:
    caminho = preparar_banco(tmp_path)
    area_id = inserir_area_monitorada(caminho, "A701", "9990001")
    cliente = cliente_para(caminho)

    resposta = cliente.post(
        caminho_ativar_cenario_sintetico(IDENTIFICADOR_CENARIO_GRANIZO),
        json={"area_id": area_id},
        headers={"Idempotency-Key": str(uuid4())},
    )

    assert resposta.status_code == 202
    assert resposta.json()["estado"] == "concluido"
    eventos = cliente.get(CAMINHO_EVENTOS).json()["eventos"]
    assert len(eventos) == 1
    assert eventos[0]["tipo"] == "granizo"
    assert eventos[0]["proveniencia"] == "sintetico"


def test_repetir_a_mesma_idempotency_key_do_cenario_sintetico_nao_duplica(
    tmp_path: Path,
) -> None:
    caminho = preparar_banco(tmp_path)
    area_id = inserir_area_monitorada(caminho, "A701", "9990001")
    cliente = cliente_para(caminho)
    chave = str(uuid4())

    primeira = cliente.post(
        caminho_ativar_cenario_sintetico(IDENTIFICADOR_CENARIO_GRANIZO),
        json={"area_id": area_id},
        headers={"Idempotency-Key": chave},
    )
    segunda = cliente.post(
        caminho_ativar_cenario_sintetico(IDENTIFICADOR_CENARIO_GRANIZO),
        json={"area_id": area_id},
        headers={"Idempotency-Key": chave},
    )

    assert primeira.status_code == 202
    assert segunda.status_code == 202
    assert primeira.json() == segunda.json()
    assert len(cliente.get(CAMINHO_EVENTOS).json()["eventos"]) == 1
