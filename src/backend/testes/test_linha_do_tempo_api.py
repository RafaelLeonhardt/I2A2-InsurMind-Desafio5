"""Testes do recurso REST/JSON da linha do tempo e da busca de execuções (TIMELINE-01, 08, 09)."""

from pathlib import Path
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.adaptadores.persistencia.repositorio_execucao_preventiva import (
    RepositorioExecucaoPreventiva,
)
from central_preventiva.adaptadores.persistencia.repositorio_mensagens import (
    RepositorioMensagens,
)
from central_preventiva.adaptadores.persistencia.serializacao_criterios import (
    serializar_criterios,
)
from central_preventiva.composicao.api import criar_aplicacao
from central_preventiva.composicao.configuracao import Configuracao
from central_preventiva.dominio.estados_execucao import EstadoExecucao
from central_preventiva.dominio.validador_saida_canal import Canal

TIPO_PROBLEMA = "application/problem+json"
REGRA_ID = UUID("33333333-3333-3333-3333-333333333333")


def preparar_banco(tmp_path: Path) -> Path:
    """Aplica as migrações versionadas e semeia a regra em um banco temporário."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()
    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO regras (id, evento_tipo, limiar_meteorologico, area_aplicavel, "
            "apolice_tipo, cobertura_exigida, antecedencia_horas, canal, versao, estado) "
            "VALUES (?, 'chuva_intensa', 50.0, '9990001', 'residencial', 'alagamento', "
            "6, 'sms', 1, 'ativa')",
            [REGRA_ID],
        )
    return caminho


def cliente_para(caminho: Path) -> TestClient:
    """Compõe a aplicação real apontada ao banco temporário do teste."""

    configuracao = Configuracao(
        host_api="127.0.0.1",
        origem_frontend="http://127.0.0.1:5173",
        caminho_banco=caminho,
    )
    return TestClient(criar_aplicacao(configuracao))


def elegibilidade_para(caminho: Path, execucao_id: UUID, canal: str, nome: str) -> UUID:
    """Insere um item do público elegível, no formato que 2.5 grava."""

    id_registro = uuid4()
    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO elegibilidades_historicas "
            "(id, execucao_id, evento_id, regra_id, segurado_id, "
            "apolice_id, elegivel, criterios, canal, nome_segurado, justificativa) "
            "VALUES (?, ?, ?, ?, ?, ?, true, ?, ?, ?, "
            "'Atende integralmente aos critérios da regra ativa.')",
            [
                id_registro,
                execucao_id,
                uuid4(),
                REGRA_ID,
                uuid4(),
                uuid4(),
                serializar_criterios(()),
                canal,
                nome,
            ],
        )
    return id_registro


def test_consultar_linha_do_tempo_devolve_200_com_os_marcos(tmp_path: Path) -> None:
    """TIMELINE-01: caminho feliz devolve os marcos já persistidos, em ordem."""

    caminho = preparar_banco(tmp_path)
    execucoes = RepositorioExecucaoPreventiva(caminho)
    execucao_id = execucoes.criar(EstadoExecucao.CONCLUIDA)
    execucoes.registrar_marco(execucao_id, "coleta_concluida")

    resposta = cliente_para(caminho).get(f"/api/v1/execucoes/{execucao_id}/linha-do-tempo")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["execucao_id"] == str(execucao_id)
    assert corpo["estado"] == "concluida"
    assert len(corpo["marcos"]) == 1
    assert corpo["marcos"][0]["acao"] == "coleta_concluida"
    assert corpo["marcos"][0]["tipo"] == "execucao"
    assert corpo["retentativas"] == []
    assert corpo["execucao_origem_id"] is None


def test_consultar_linha_do_tempo_de_execucao_inexistente_devolve_404(tmp_path: Path) -> None:
    """`404` `problem+json` correlacionado para execução inexistente."""

    caminho = preparar_banco(tmp_path)

    resposta = cliente_para(caminho).get(f"/api/v1/execucoes/{uuid4()}/linha-do-tempo")

    assert resposta.status_code == 404
    assert resposta.headers["content-type"].startswith(TIPO_PROBLEMA)
    corpo = resposta.json()
    assert corpo["codigo"] == "execucao_inexistente"
    assert corpo["correlacao_id"]


def test_consultar_linha_do_tempo_com_identificador_invalido_devolve_422(
    tmp_path: Path,
) -> None:
    """Identificador malformado é 422 `problem+json`, não 500."""

    caminho = preparar_banco(tmp_path)

    resposta = cliente_para(caminho).get("/api/v1/execucoes/nao-e-uuid/linha-do-tempo")

    assert resposta.status_code == 422
    assert resposta.headers["content-type"].startswith(TIPO_PROBLEMA)
    assert resposta.json()["codigo"] == "execucao_id_invalido"


def test_buscar_execucoes_com_filtro_de_canal_traz_so_as_correspondentes(
    tmp_path: Path,
) -> None:
    """TIMELINE-08: busca filtrada retorna só os resultados correspondentes."""

    caminho = preparar_banco(tmp_path)
    execucoes = RepositorioExecucaoPreventiva(caminho)
    execucao_email = execucoes.criar(EstadoExecucao.CONCLUIDA)
    execucao_sms = execucoes.criar(EstadoExecucao.CONCLUIDA)
    mensagens = RepositorioMensagens(caminho)
    mensagens.criar(
        execucao_email,
        elegibilidade_para(caminho, execucao_email, "email", "Marina Teste"),
        Canal.EMAIL,
    )
    mensagens.criar(
        execucao_sms, elegibilidade_para(caminho, execucao_sms, "sms", "Carlos Teste"), Canal.SMS
    )

    resposta = cliente_para(caminho).get("/api/v1/execucoes", params={"canal": "email"})

    assert resposta.status_code == 200
    resultados = resposta.json()["resultados"]
    assert [item["execucao_id"] for item in resultados] == [str(execucao_email)]


def test_buscar_execucoes_sem_filtro_devolve_todas(tmp_path: Path) -> None:
    """Sem filtro nenhum, a busca devolve todas as execuções."""

    caminho = preparar_banco(tmp_path)
    execucoes = RepositorioExecucaoPreventiva(caminho)
    primeira = execucoes.criar(EstadoExecucao.CONCLUIDA)
    segunda = execucoes.criar(EstadoExecucao.SEM_RISCO)

    resposta = cliente_para(caminho).get("/api/v1/execucoes")

    assert resposta.status_code == 200
    ids = {item["execucao_id"] for item in resposta.json()["resultados"]}
    assert ids == {str(primeira), str(segunda)}


def test_buscar_execucoes_com_canal_invalido_devolve_422(tmp_path: Path) -> None:
    """TIMELINE-09: um canal fora do conjunto fechado é recusado, não um erro técnico."""

    caminho = preparar_banco(tmp_path)

    resposta = cliente_para(caminho).get(
        "/api/v1/execucoes", params={"canal": "pombo-correio"}
    )

    assert resposta.status_code == 422
    assert resposta.headers["content-type"].startswith(TIPO_PROBLEMA)
    assert resposta.json()["codigo"] == "canal_invalido"


def test_buscar_execucoes_sem_correspondencia_devolve_lista_vazia(tmp_path: Path) -> None:
    """TIMELINE-09: filtro sem nenhuma correspondência devolve lista vazia, não erro."""

    caminho = preparar_banco(tmp_path)
    RepositorioExecucaoPreventiva(caminho).criar(EstadoExecucao.CONCLUIDA)

    resposta = cliente_para(caminho).get("/api/v1/execucoes", params={"canal": "whatsapp"})

    assert resposta.status_code == 200
    assert resposta.json()["resultados"] == []
