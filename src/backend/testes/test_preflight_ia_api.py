"""Testes do recurso REST/JSON da preparação agêntica (PREFL-02, PREFL-09, PREFL-10)."""

from datetime import UTC, datetime
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
from central_preventiva.adaptadores.persistencia.repositorio_meteorologia import (
    RepositorioEventosMeteorologicos,
)
from central_preventiva.adaptadores.persistencia.serializacao_criterios import (
    serializar_criterios,
)
from central_preventiva.composicao.api import criar_aplicacao
from central_preventiva.composicao.configuracao import Configuracao
from central_preventiva.dominio.avaliador_elegibilidade import (
    OPERANDO_AREA_AFETADA,
    OPERANDO_COBERTURA_EXIGIDA,
)
from central_preventiva.dominio.avaliador_risco import Criterio
from central_preventiva.dominio.estados_execucao import EstadoExecucao
from central_preventiva.dominio.evento_meteorologico import (
    EventoMeteorologico,
    ProvenienciaEvento,
    TipoEventoMeteorologico,
)
from central_preventiva.dominio.montador_contexto_agente import (
    CATEGORIAS_NAO_UTILIZADAS,
    CATEGORIAS_UTILIZADAS,
)

TIPO_PROBLEMA = "application/problem+json"
AREA = "9990001"
MODELO = "gpt-4o-mini"
CHAVE_SINTETICA = "sk-teste-nao-deve-vazar-98765"

EVENTO = EventoMeteorologico(
    id=UUID("44444444-4444-4444-4444-444444444444"),
    tipo=TipoEventoMeteorologico.CHUVA_INTENSA,
    area=AREA,
    periodo_inicio=datetime(2026, 9, 3, 12, 0, tzinfo=UTC),
    periodo_fim=datetime(2026, 9, 3, 18, 0, tzinfo=UTC),
    intensidade=72.5,
    proveniencia=ProvenienciaEvento.REAL_INMET,
    instante_observado=datetime(2026, 9, 3, 18, 0, tzinfo=UTC),
)


@pytest.fixture(autouse=True)
def _bloquear_chamadas_de_rede_reais(monkeypatch: pytest.MonkeyPatch) -> None:
    """Impede qualquer chamada HTTP real: todo teste programa o que a OpenAI responde."""

    async def _send_bloqueado(
        self: httpx.AsyncClient, request: httpx.Request, **_: object
    ) -> httpx.Response:
        raise AssertionError(f"chamada de rede real bloqueada em teste: {request.url}")

    monkeypatch.setattr(httpx.AsyncClient, "send", _send_bloqueado)


def programar_openai(monkeypatch: pytest.MonkeyPatch, resposta: httpx.Response) -> None:
    """Programa a resposta que a OpenAI devolve à verificação de disponibilidade."""

    async def _send(
        self: httpx.AsyncClient, request: httpx.Request, **_: object
    ) -> httpx.Response:
        return httpx.Response(
            resposta.status_code,
            content=resposta.content,
            headers={"content-type": resposta.headers.get("content-type", "application/json")},
            request=request,
        )

    monkeypatch.setattr(httpx.AsyncClient, "send", _send)


def openai_disponivel() -> httpx.Response:
    """Resposta de catálogo contendo o modelo configurado."""

    return httpx.Response(200, json={"data": [{"id": MODELO}]})


def openai_indisponivel() -> httpx.Response:
    """Resposta de credencial recusada pela OpenAI."""

    return httpx.Response(401, json={"error": "invalid_api_key"})


def preparar_banco(tmp_path: Path) -> Path:
    """Aplica as migrações versionadas em um banco temporário do teste."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()
    return caminho


def configuracao_para(caminho: Path) -> Configuracao:
    """Configuração local apontada ao banco do teste, com credencial sintética."""

    return Configuracao(
        host_api="127.0.0.1",
        origem_frontend="http://127.0.0.1:5173",
        caminho_banco=caminho,
        chave_openai=CHAVE_SINTETICA,
        modelo_openai=MODELO,
        timeout_openai_segundos=1.0,
        _env_file=None,
    )


def inserir_regra(caminho: Path) -> UUID:
    """Insere a versão de regra ativa referenciada pelos snapshots de elegibilidade."""

    id_regra = uuid4()
    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO regras (id, evento_tipo, limiar_meteorologico, area_aplicavel, "
            "apolice_tipo, cobertura_exigida, antecedencia_horas, canal, versao, estado) "
            "VALUES (?, 'chuva_intensa', 50.0, ?, 'residencial', 'alagamento', 24, "
            "'sms', 1, 'ativa')",
            [id_regra, AREA],
        )
    return id_regra


def inserir_elegibilidade(
    caminho: Path, execucao_id: UUID, regra_id: UUID, elegivel: bool = True
) -> UUID:
    """Insere um resultado de elegibilidade da execução, no formato que 2.5 grava."""

    id_registro = uuid4()
    criterios = (
        Criterio(OPERANDO_AREA_AFETADA, AREA, True, "Área corresponde."),
        Criterio(OPERANDO_COBERTURA_EXIGIDA, "alagamento", True, "Possui cobertura."),
    )
    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO elegibilidades_historicas "
            "(id, execucao_id, evento_id, regra_id, segurado_id, apolice_id, elegivel, "
            "criterios, canal, nome_segurado, justificativa) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'sms', 'Pessoa Teste', 'justificativa')",
            [
                id_registro,
                execucao_id,
                EVENTO.id,
                regra_id,
                uuid4(),
                uuid4(),
                elegivel,
                serializar_criterios(criterios),
            ],
        )
    return id_registro


def montar_cenario(tmp_path: Path) -> tuple[TestClient, Path, UUID]:
    """Monta um cliente HTTP sobre uma execução parada em `aguardando_geracao`."""

    caminho = preparar_banco(tmp_path)
    RepositorioEventosMeteorologicos(caminho).salvar(EVENTO)
    regra_id = inserir_regra(caminho)
    execucoes = RepositorioExecucaoPreventiva(caminho)
    execucao_id = execucoes.criar(EstadoExecucao.AGUARDANDO_GERACAO)
    inserir_elegibilidade(caminho, execucao_id, regra_id, elegivel=True)
    inserir_elegibilidade(caminho, execucao_id, regra_id, elegivel=False)
    return TestClient(criar_aplicacao(configuracao_para(caminho))), caminho, execucao_id


def test_preflight_com_openai_disponivel_transiciona_para_processando_mensagens(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cliente, _, execucao_id = montar_cenario(tmp_path)
    programar_openai(monkeypatch, openai_disponivel())

    resposta = cliente.post(
        f"/api/v1/execucoes/{execucao_id}/preflight",
        headers={"Idempotency-Key": "chave-1"},
    )

    assert resposta.status_code == 202
    corpo = resposta.json()
    assert corpo["estado"] == "processando_mensagens"
    assert corpo["contextos_montados"] == 1
    assert corpo["itens_em_excecao"] == []
    assert corpo["causa"] is None
    assert cliente.get(f"/api/v1/execucoes/{execucao_id}").json()["estado"] == (
        "processando_mensagens"
    )


def test_preflight_com_openai_indisponivel_falha_a_preparacao_sem_expor_a_credencial(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """PREFL-03, PREFL-04, PREFL-16: bloqueio explícito, sem conteúdo substituto."""

    cliente, _, execucao_id = montar_cenario(tmp_path)
    programar_openai(monkeypatch, openai_indisponivel())

    resposta = cliente.post(
        f"/api/v1/execucoes/{execucao_id}/preflight",
        headers={"Idempotency-Key": "chave-1"},
    )

    assert resposta.status_code == 202
    corpo = resposta.json()
    assert corpo["estado"] == "falhou_preparacao_ia"
    assert corpo["causa"] == "A credencial da OpenAI foi recusada."
    assert corpo["contextos_montados"] == 0
    assert CHAVE_SINTETICA not in resposta.text
    assert cliente.get(f"/api/v1/execucoes/{execucao_id}/contextos").json()["registros"] == []


def test_preflight_sem_idempotency_key_devolve_problem_json(tmp_path: Path) -> None:
    cliente, _, execucao_id = montar_cenario(tmp_path)

    resposta = cliente.post(f"/api/v1/execucoes/{execucao_id}/preflight")

    assert resposta.status_code == 422
    assert resposta.headers["content-type"].startswith(TIPO_PROBLEMA)
    assert resposta.json()["codigo"] == "idempotency_key_ausente"


def test_repetir_a_chave_devolve_a_resposta_registrada_sem_novo_preflight(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AD-002: o replay não dispara uma segunda verificação de disponibilidade."""

    cliente, _, execucao_id = montar_cenario(tmp_path)
    programar_openai(monkeypatch, openai_disponivel())
    primeira = cliente.post(
        f"/api/v1/execucoes/{execucao_id}/preflight", headers={"Idempotency-Key": "chave-1"}
    )

    async def _send_proibido(
        self: httpx.AsyncClient, request: httpx.Request, **_: object
    ) -> httpx.Response:
        raise AssertionError("o replay não pode chamar a OpenAI de novo")

    monkeypatch.setattr(httpx.AsyncClient, "send", _send_proibido)
    segunda = cliente.post(
        f"/api/v1/execucoes/{execucao_id}/preflight", headers={"Idempotency-Key": "chave-1"}
    )

    assert segunda.status_code == 202
    assert segunda.json() == primeira.json()


def test_reusar_a_chave_em_outra_execucao_devolve_conflito_sem_reaproveitar_a_resposta(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AD-002: a mesma Idempotency-Key para uma execução diferente é conflito, não reuso.

    O corpo do POST é sempre vazio (o alvo vem do caminho), então o hash de idempotência
    precisa incluir o identificador da execução — sem isso, reaproveitar a chave em uma
    execução diferente devolveria silenciosamente a resposta da primeira em vez de rejeitar.
    """

    cliente, caminho, execucao_a = montar_cenario(tmp_path)
    programar_openai(monkeypatch, openai_disponivel())
    primeira = cliente.post(
        f"/api/v1/execucoes/{execucao_a}/preflight", headers={"Idempotency-Key": "chave-1"}
    )
    assert primeira.status_code == 202

    execucao_b = RepositorioExecucaoPreventiva(caminho).criar(EstadoExecucao.AGUARDANDO_GERACAO)

    resposta = cliente.post(
        f"/api/v1/execucoes/{execucao_b}/preflight", headers={"Idempotency-Key": "chave-1"}
    )

    assert resposta.status_code == 409
    assert resposta.json()["codigo"] == "conflito_idempotencia"
    assert (
        cliente.get(f"/api/v1/execucoes/{execucao_b}").json()["estado"] == "aguardando_geracao"
    )


def test_preflight_de_execucao_inexistente_devolve_404(tmp_path: Path) -> None:
    cliente, _, _ = montar_cenario(tmp_path)

    resposta = cliente.post(
        f"/api/v1/execucoes/{uuid4()}/preflight", headers={"Idempotency-Key": "chave-1"}
    )

    assert resposta.status_code == 404
    assert resposta.json()["codigo"] == "execucao_inexistente"


def test_preflight_de_execucao_fora_de_aguardando_geracao_devolve_409(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cliente, caminho, execucao_id = montar_cenario(tmp_path)
    RepositorioExecucaoPreventiva(caminho).transicionar(
        execucao_id, 1, EstadoExecucao.SEM_ELEGIVEIS
    )

    resposta = cliente.post(
        f"/api/v1/execucoes/{execucao_id}/preflight", headers={"Idempotency-Key": "chave-1"}
    )

    assert resposta.status_code == 409
    assert resposta.json()["codigo"] == "estado_nao_preparavel"


def test_proveniencia_expoe_as_categorias_usadas_e_nao_usadas(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """PREFL-13, PREFL-14: a consulta mostra as categorias, nunca o conteúdo."""

    cliente, _, execucao_id = montar_cenario(tmp_path)
    programar_openai(monkeypatch, openai_disponivel())
    cliente.post(
        f"/api/v1/execucoes/{execucao_id}/preflight", headers={"Idempotency-Key": "chave-1"}
    )

    resposta = cliente.get(f"/api/v1/execucoes/{execucao_id}/contextos")

    assert resposta.status_code == 200
    registros = resposta.json()["registros"]
    assert len(registros) == 1
    assert registros[0]["categorias_usadas"] == list(CATEGORIAS_UTILIZADAS)
    assert registros[0]["categorias_nao_usadas"] == list(CATEGORIAS_NAO_UTILIZADAS)
    assert "sms" not in resposta.text
    assert AREA not in resposta.text


def test_nova_tentativa_cria_execucao_correlacionada_navegavel_nos_dois_sentidos(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """PREFL-09, PREFL-10: origem e retentativa se referenciam sem mesclar históricos."""

    cliente, _, origem_id = montar_cenario(tmp_path)
    programar_openai(monkeypatch, openai_indisponivel())
    cliente.post(
        f"/api/v1/execucoes/{origem_id}/preflight", headers={"Idempotency-Key": "chave-1"}
    )

    resposta = cliente.post(
        f"/api/v1/execucoes/{origem_id}/nova-tentativa-ia",
        headers={"Idempotency-Key": "chave-2"},
    )

    assert resposta.status_code == 202
    nova_id = resposta.json()["execucao_id"]
    assert resposta.json()["execucao_origem_id"] == str(origem_id)
    assert nova_id != str(origem_id)

    nova = cliente.get(f"/api/v1/execucoes/{nova_id}").json()
    assert nova["estado"] == "aguardando_geracao"
    assert nova["execucao_origem_id"] == str(origem_id)
    assert nova["retentativas"] == []

    origem = cliente.get(f"/api/v1/execucoes/{origem_id}").json()
    assert origem["estado"] == "falhou_preparacao_ia"
    assert origem["execucao_origem_id"] is None
    assert origem["retentativas"] == [nova_id]
    # Históricos não se mesclam: o marco do bloqueio, com a causa que a interface explica,
    # pertence só à origem; a execução nova começa sem nenhum marco herdado.
    assert [marco["marco"] for marco in origem["marcos"]] == ["falhou_preparacao_ia"]
    assert origem["marcos"][0]["causa"] == "A credencial da OpenAI foi recusada."
    assert nova["marcos"] == []


def test_nova_tentativa_copia_o_publico_da_origem_e_permite_novo_preflight(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AD-012: a nova execução monta seus próprios contextos sobre as cópias."""

    cliente, caminho, origem_id = montar_cenario(tmp_path)
    programar_openai(monkeypatch, openai_disponivel())
    cliente.post(
        f"/api/v1/execucoes/{origem_id}/preflight", headers={"Idempotency-Key": "chave-1"}
    )
    RepositorioExecucaoPreventiva(caminho).transicionar(
        origem_id, 2, EstadoExecucao.FALHOU_PREPARACAO_IA
    )

    nova_id = cliente.post(
        f"/api/v1/execucoes/{origem_id}/nova-tentativa-ia",
        headers={"Idempotency-Key": "chave-2"},
    ).json()["execucao_id"]
    segundo = cliente.post(
        f"/api/v1/execucoes/{nova_id}/preflight", headers={"Idempotency-Key": "chave-3"}
    )

    assert segundo.status_code == 202
    assert segundo.json()["estado"] == "processando_mensagens"
    assert segundo.json()["contextos_montados"] == 1
    assert len(cliente.get(f"/api/v1/execucoes/{nova_id}/contextos").json()["registros"]) == 1
    assert len(cliente.get(f"/api/v1/execucoes/{origem_id}/contextos").json()["registros"]) == 1


def test_reusar_a_chave_de_nova_tentativa_em_outra_origem_devolve_conflito(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AD-002: a mesma Idempotency-Key para uma origem diferente é conflito, não reuso."""

    cliente, caminho, origem_a = montar_cenario(tmp_path)
    programar_openai(monkeypatch, openai_indisponivel())
    cliente.post(
        f"/api/v1/execucoes/{origem_a}/preflight", headers={"Idempotency-Key": "chave-1"}
    )
    cliente.post(
        f"/api/v1/execucoes/{origem_a}/nova-tentativa-ia",
        headers={"Idempotency-Key": "chave-2"},
    )

    regra_id = inserir_regra(caminho)
    origem_b = RepositorioExecucaoPreventiva(caminho).criar(EstadoExecucao.AGUARDANDO_GERACAO)
    inserir_elegibilidade(caminho, origem_b, regra_id, elegivel=True)
    cliente.post(
        f"/api/v1/execucoes/{origem_b}/preflight", headers={"Idempotency-Key": "chave-3"}
    )

    resposta = cliente.post(
        f"/api/v1/execucoes/{origem_b}/nova-tentativa-ia",
        headers={"Idempotency-Key": "chave-2"},
    )

    assert resposta.status_code == 409
    assert resposta.json()["codigo"] == "conflito_idempotencia"
    assert cliente.get(f"/api/v1/execucoes/{origem_b}").json()["retentativas"] == []


def test_nova_tentativa_a_partir_de_origem_nao_terminal_devolve_409(
    tmp_path: Path,
) -> None:
    cliente, _, execucao_id = montar_cenario(tmp_path)

    resposta = cliente.post(
        f"/api/v1/execucoes/{execucao_id}/nova-tentativa-ia",
        headers={"Idempotency-Key": "chave-1"},
    )

    assert resposta.status_code == 409
    assert resposta.json()["codigo"] == "origem_nao_retentavel"


def test_nova_tentativa_com_snapshot_incompleto_e_rejeitada_sem_criar_execucao(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """PREFL-08: validação falha, nenhuma execução nova é criada."""

    caminho = preparar_banco(tmp_path)
    RepositorioEventosMeteorologicos(caminho).salvar(EVENTO)
    execucoes = RepositorioExecucaoPreventiva(caminho)
    origem_id = execucoes.criar(EstadoExecucao.AGUARDANDO_GERACAO)
    execucoes.transicionar(origem_id, 1, EstadoExecucao.FALHOU_PREPARACAO_IA)
    cliente = TestClient(criar_aplicacao(configuracao_para(caminho)))

    resposta = cliente.post(
        f"/api/v1/execucoes/{origem_id}/nova-tentativa-ia",
        headers={"Idempotency-Key": "chave-1"},
    )

    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "snapshot_invalido"
    assert cliente.get(f"/api/v1/execucoes/{origem_id}").json()["retentativas"] == []


def test_nova_tentativa_sem_idempotency_key_devolve_problem_json(tmp_path: Path) -> None:
    cliente, _, execucao_id = montar_cenario(tmp_path)

    resposta = cliente.post(f"/api/v1/execucoes/{execucao_id}/nova-tentativa-ia")

    assert resposta.status_code == 422
    assert resposta.headers["content-type"].startswith(TIPO_PROBLEMA)
    assert resposta.json()["codigo"] == "idempotency_key_ausente"


def test_proveniencia_de_execucao_inexistente_devolve_404(tmp_path: Path) -> None:
    cliente, _, _ = montar_cenario(tmp_path)

    resposta = cliente.get(f"/api/v1/execucoes/{uuid4()}/contextos")

    assert resposta.status_code == 404
    assert resposta.json()["codigo"] == "execucao_inexistente"
