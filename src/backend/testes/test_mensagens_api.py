"""Testes do recurso REST/JSON de consulta das mensagens de uma execução (GERAR-11, 12)."""

from pathlib import Path
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.adaptadores.persistencia.repositorio_execucao_preventiva import (
    RepositorioExecucaoPreventiva,
)
from central_preventiva.adaptadores.persistencia.repositorio_mensagens import (
    RepositorioMensagens,
)
from central_preventiva.composicao.api import criar_aplicacao
from central_preventiva.composicao.configuracao import Configuracao
from central_preventiva.dominio.estados_execucao import EstadoExecucao
from central_preventiva.dominio.estados_mensagem import EstadoMensagem
from central_preventiva.dominio.validador_saida_canal import Canal, SaidaCanal

TIPO_PROBLEMA = "application/problem+json"


def preparar_banco(tmp_path: Path) -> Path:
    """Aplica as migrações versionadas em um banco temporário do teste."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()
    return caminho


def cliente_para(caminho: Path) -> TestClient:
    """Compõe a aplicação real apontada ao banco temporário do teste."""

    configuracao = Configuracao(
        host_api="127.0.0.1",
        origem_frontend="http://127.0.0.1:5151",
        caminho_banco=caminho,
    )
    return TestClient(criar_aplicacao(configuracao))


def criar_execucao(caminho: Path) -> UUID:
    """Cria uma execução em `processando_mensagens`, o estado em que a geração roda."""

    return RepositorioExecucaoPreventiva(caminho).criar(EstadoExecucao.PROCESSANDO_MENSAGENS)


def test_execucao_sem_mensagens_devolve_lista_vazia(tmp_path: Path) -> None:
    """GERAR-11: antes da geração, a consulta reflete só o que está persistido."""

    caminho = preparar_banco(tmp_path)
    execucao_id = criar_execucao(caminho)

    resposta = cliente_para(caminho).get(f"/api/v1/execucoes/{execucao_id}/mensagens")

    assert resposta.status_code == 200
    assert resposta.json() == {"execucao_id": str(execucao_id), "registros": []}


def test_mensagem_gerada_aparece_com_estado_canal_tentativa_e_versao_atual(
    tmp_path: Path,
) -> None:
    """GERAR-11: depois da geração, estado, canal, tentativa e versão vêm da persistência."""

    caminho = preparar_banco(tmp_path)
    execucao_id = criar_execucao(caminho)
    elegibilidade_id = uuid4()
    repo = RepositorioMensagens(caminho)
    mensagem_id = repo.criar(execucao_id, elegibilidade_id, Canal.SMS)
    repo.salvar_versao(
        mensagem_id=mensagem_id,
        numero_tentativa=1,
        conteudo=SaidaCanal(corpo="Chuva forte hoje. Evite áreas alagadas."),
        duracao_ms=742.5,
        modelo="gpt-4o-mini",
        versao_prompt="v1",
        tokens_entrada=210,
        tokens_saida=64,
        valida=True,
        motivo_invalidez=None,
    )
    repo.transicionar(mensagem_id, 1, EstadoMensagem.CRITICANDO)

    resposta = cliente_para(caminho).get(f"/api/v1/execucoes/{execucao_id}/mensagens")

    assert resposta.status_code == 200
    registros = resposta.json()["registros"]
    assert len(registros) == 1
    registro = registros[0]
    assert registro["id"] == str(mensagem_id)
    assert registro["elegibilidade_id"] == str(elegibilidade_id)
    assert registro["canal"] == "sms"
    assert registro["estado"] == "criticando"
    assert registro["tentativa_atual"] == 1
    assert registro["versao"] == 2
    assert registro["versao_atual"]["numero_tentativa"] == 1
    assert registro["versao_atual"]["valida"] is True
    assert registro["versao_atual"]["motivo_invalidez"] is None
    assert registro["versao_atual"]["modelo"] == "gpt-4o-mini"
    assert registro["versao_atual"]["versao_prompt"] == "v1"
    assert registro["versao_atual"]["duracao_ms"] == 742.5
    assert registro["versao_atual"]["tokens_entrada"] == 210
    assert registro["versao_atual"]["tokens_saida"] == 64


def test_mensagem_invalida_expoe_o_motivo_e_permanece_em_gerando(tmp_path: Path) -> None:
    """GERAR-09: a consulta mostra a recusa determinística, sem inventar estado."""

    caminho = preparar_banco(tmp_path)
    execucao_id = criar_execucao(caminho)
    repo = RepositorioMensagens(caminho)
    mensagem_id = repo.criar(execucao_id, uuid4(), Canal.SMS)
    repo.salvar_versao(
        mensagem_id=mensagem_id,
        numero_tentativa=1,
        conteudo=SaidaCanal(corpo="a" * 161),
        duracao_ms=100.0,
        modelo="gpt-4o-mini",
        versao_prompt="v1",
        tokens_entrada=None,
        tokens_saida=None,
        valida=False,
        motivo_invalidez="limite_excedido:corpo:161:160",
    )

    resposta = cliente_para(caminho).get(f"/api/v1/execucoes/{execucao_id}/mensagens")

    registro = resposta.json()["registros"][0]
    assert registro["estado"] == "gerando"
    assert registro["versao_atual"]["valida"] is False
    assert registro["versao_atual"]["motivo_invalidez"] == "limite_excedido:corpo:161:160"
    assert registro["versao_atual"]["tokens_entrada"] is None


def test_mensagem_ainda_sem_versao_devolve_versao_atual_nula(tmp_path: Path) -> None:
    """GERAR-11: uma mensagem em geração aparece sem versão, nunca com dado inventado."""

    caminho = preparar_banco(tmp_path)
    execucao_id = criar_execucao(caminho)
    RepositorioMensagens(caminho).criar(execucao_id, uuid4(), Canal.WHATSAPP)

    resposta = cliente_para(caminho).get(f"/api/v1/execucoes/{execucao_id}/mensagens")

    registro = resposta.json()["registros"][0]
    assert registro["estado"] == "gerando"
    assert registro["versao_atual"] is None


def test_consultas_repetidas_devolvem_o_mesmo_conteudo_sem_criar_mensagem(
    tmp_path: Path,
) -> None:
    """GERAR-12: reidratar consulta e não reenvia geração nem duplica mensagem."""

    caminho = preparar_banco(tmp_path)
    execucao_id = criar_execucao(caminho)
    repo = RepositorioMensagens(caminho)
    repo.criar(execucao_id, uuid4(), Canal.SMS)
    repo.criar(execucao_id, uuid4(), Canal.EMAIL)
    cliente = cliente_para(caminho)

    primeira = cliente.get(f"/api/v1/execucoes/{execucao_id}/mensagens")
    segunda = cliente.get(f"/api/v1/execucoes/{execucao_id}/mensagens")

    assert primeira.json() == segunda.json()
    assert len(segunda.json()["registros"]) == 2
    assert len(repo.listar_por_execucao(execucao_id)) == 2


def test_mensagens_de_outra_execucao_nao_aparecem(tmp_path: Path) -> None:
    """A consulta é escopada pela execução do caminho, nunca por todo o banco."""

    caminho = preparar_banco(tmp_path)
    execucao_id = criar_execucao(caminho)
    outra_execucao_id = criar_execucao(caminho)
    repo = RepositorioMensagens(caminho)
    propria = repo.criar(execucao_id, uuid4(), Canal.SMS)
    repo.criar(outra_execucao_id, uuid4(), Canal.SMS)

    resposta = cliente_para(caminho).get(f"/api/v1/execucoes/{execucao_id}/mensagens")

    assert [item["id"] for item in resposta.json()["registros"]] == [str(propria)]


def test_execucao_inexistente_devolve_404_correlacionado(tmp_path: Path) -> None:
    """Execução inexistente é 404 `problem+json`, com impacto e próxima ação."""

    caminho = preparar_banco(tmp_path)

    resposta = cliente_para(caminho).get(f"/api/v1/execucoes/{uuid4()}/mensagens")

    assert resposta.status_code == 404
    assert resposta.headers["content-type"].startswith(TIPO_PROBLEMA)
    corpo = resposta.json()
    assert corpo["codigo"] == "execucao_inexistente"
    assert corpo["correlacao_id"]
    assert corpo["impacto"] == "Nenhuma mensagem pode ser exibida."
    assert corpo["proxima_acao"]


def test_identificador_invalido_devolve_422_correlacionado(tmp_path: Path) -> None:
    """Identificador malformado é 422 `problem+json`, não 500."""

    caminho = preparar_banco(tmp_path)

    resposta = cliente_para(caminho).get("/api/v1/execucoes/nao-e-uuid/mensagens")

    assert resposta.status_code == 422
    assert resposta.headers["content-type"].startswith(TIPO_PROBLEMA)
    assert resposta.json()["codigo"] == "execucao_id_invalido"
