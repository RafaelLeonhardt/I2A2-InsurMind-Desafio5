"""Testes do recurso REST/JSON de consulta dos resultados consolidados (RESULT-02,09)."""

from pathlib import Path
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.adaptadores.persistencia.repositorio_entregas_simuladas import (
    MensagemAprovada,
    RepositorioEntregasSimuladas,
)
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
CONTEUDO = SaidaCanal(corpo="Chuva forte hoje. Evite áreas alagadas.")


def preparar_banco(tmp_path: Path) -> Path:
    """Aplica as migrações versionadas em um banco temporário do teste."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()
    return caminho


def cliente_para(caminho: Path) -> TestClient:
    """Compõe a aplicação real apontada ao banco temporário do teste."""

    configuracao = Configuracao(
        host_api="127.0.0.1",
        origem_frontend="http://127.0.0.1:5173",
        caminho_banco=caminho,
    )
    return TestClient(criar_aplicacao(configuracao))


def criar_execucao(caminho: Path, estado: EstadoExecucao) -> UUID:
    """Cria uma execução no estado informado."""

    return RepositorioExecucaoPreventiva(caminho).criar(estado)


def test_execucao_concluida_devolve_200_com_totais_reconciliaveis(tmp_path: Path) -> None:
    """RESULT-02: totais por canal/estado, com as não-simuláveis fora das entregas."""

    caminho = preparar_banco(tmp_path)
    execucao_id = criar_execucao(caminho, EstadoExecucao.CONCLUIDA)
    mensagens = RepositorioMensagens(caminho)
    entregas = RepositorioEntregasSimuladas(caminho)
    simulada_id = mensagens.criar(execucao_id, uuid4(), Canal.SMS)
    mensagens.transicionar(simulada_id, 1, EstadoMensagem.SIMULADA_ENTREGUE)
    entregas.criar_lote(execucao_id, [MensagemAprovada(simulada_id, Canal.SMS, CONTEUDO)])
    rejeitada_id = mensagens.criar(execucao_id, uuid4(), Canal.EMAIL)
    mensagens.transicionar(rejeitada_id, 1, EstadoMensagem.REJEITADA)

    resposta = cliente_para(caminho).get(f"/api/v1/execucoes/{execucao_id}/resultados")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["execucao_id"] == str(execucao_id)
    assert corpo["concluido"] is True
    totais_estado = {item["chave"]: item["total"] for item in corpo["totais_por_estado"]}
    assert totais_estado["simulada_entregue"] == 1
    assert totais_estado["rejeitada"] == 1
    assert [item["mensagem_id"] for item in corpo["nao_simulaveis"]] == [str(rejeitada_id)]
    assert corpo["nao_simulaveis"][0]["motivo"] == "rejeitada pela revisão humana"
    assert corpo["divergencia"] is None


def test_execucao_em_simulando_devolve_progresso_sem_totais_finais(tmp_path: Path) -> None:
    """Edge Case da spec: consulta durante `simulando` nunca mostra total parcial como final."""

    caminho = preparar_banco(tmp_path)
    execucao_id = criar_execucao(caminho, EstadoExecucao.SIMULANDO)
    RepositorioMensagens(caminho).criar(execucao_id, uuid4(), Canal.SMS)

    resposta = cliente_para(caminho).get(f"/api/v1/execucoes/{execucao_id}/resultados")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["concluido"] is False
    assert corpo["estado"] == "simulando"
    assert corpo["totais_por_canal"] == []
    assert corpo["totais_por_estado"] == []
    assert corpo["nao_simulaveis"] == []


def test_falhou_simulacao_expoe_mensagens_ainda_aprovadas(tmp_path: Path) -> None:
    """RESULT-04/05: falha local mostra mensagens `aprovada`, nunca falha de canal."""

    caminho = preparar_banco(tmp_path)
    execucao_id = criar_execucao(caminho, EstadoExecucao.FALHOU_SIMULACAO)
    mensagens = RepositorioMensagens(caminho)
    aprovada_id = mensagens.criar(execucao_id, uuid4(), Canal.WHATSAPP)
    mensagens.transicionar(aprovada_id, 1, EstadoMensagem.APROVADA)

    resposta = cliente_para(caminho).get(f"/api/v1/execucoes/{execucao_id}/resultados")

    corpo = resposta.json()
    assert corpo["concluido"] is True
    totais_estado = {item["chave"]: item["total"] for item in corpo["totais_por_estado"]}
    assert totais_estado == {"aprovada": 1}
    assert corpo["nao_simulaveis"] == []


def test_divergencia_aparece_no_corpo_com_correlacao(tmp_path: Path) -> None:
    """RESULT-09: divergência exposta via API com a execução como correlação."""

    caminho = preparar_banco(tmp_path)
    execucao_id = criar_execucao(caminho, EstadoExecucao.CONCLUIDA)
    mensagens = RepositorioMensagens(caminho)
    simulada_id = mensagens.criar(execucao_id, uuid4(), Canal.SMS)
    mensagens.transicionar(simulada_id, 1, EstadoMensagem.SIMULADA_ENTREGUE)

    resposta = cliente_para(caminho).get(f"/api/v1/execucoes/{execucao_id}/resultados")

    corpo = resposta.json()
    assert corpo["divergencia"] is not None
    assert corpo["divergencia"]["execucao_id"] == str(execucao_id)
    assert corpo["divergencia"]["mensagens_simulada_entregue"] == 1
    assert corpo["divergencia"]["entregas_persistidas"] == 0


def test_consultas_repetidas_devolvem_o_mesmo_conteudo(tmp_path: Path) -> None:
    """RESULT-06/07: reidratação pura — repetir a consulta não muda o resultado."""

    caminho = preparar_banco(tmp_path)
    execucao_id = criar_execucao(caminho, EstadoExecucao.CONCLUIDA)
    mensagens = RepositorioMensagens(caminho)
    mensagem_id = mensagens.criar(execucao_id, uuid4(), Canal.SMS)
    mensagens.transicionar(mensagem_id, 1, EstadoMensagem.SIMULADA_ENTREGUE)
    RepositorioEntregasSimuladas(caminho).criar_lote(
        execucao_id, [MensagemAprovada(mensagem_id, Canal.SMS, CONTEUDO)]
    )
    cliente = cliente_para(caminho)

    primeira = cliente.get(f"/api/v1/execucoes/{execucao_id}/resultados")
    segunda = cliente.get(f"/api/v1/execucoes/{execucao_id}/resultados")

    assert primeira.json() == segunda.json()


def test_execucao_inexistente_devolve_404_correlacionado(tmp_path: Path) -> None:
    """Execução inexistente é 404 `problem+json`, com impacto e próxima ação."""

    caminho = preparar_banco(tmp_path)

    resposta = cliente_para(caminho).get(f"/api/v1/execucoes/{uuid4()}/resultados")

    assert resposta.status_code == 404
    assert resposta.headers["content-type"].startswith(TIPO_PROBLEMA)
    corpo = resposta.json()
    assert corpo["codigo"] == "execucao_inexistente"
    assert corpo["correlacao_id"]
    assert corpo["impacto"] == "Nenhum resultado pode ser exibido."


def test_identificador_invalido_devolve_422_correlacionado(tmp_path: Path) -> None:
    """Identificador malformado é 422 `problem+json`, não 500."""

    caminho = preparar_banco(tmp_path)

    resposta = cliente_para(caminho).get("/api/v1/execucoes/nao-e-uuid/resultados")

    assert resposta.status_code == 422
    assert resposta.headers["content-type"].startswith(TIPO_PROBLEMA)
    assert resposta.json()["codigo"] == "execucao_id_invalido"
