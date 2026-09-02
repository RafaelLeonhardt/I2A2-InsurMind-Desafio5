"""Testes do recurso REST/JSON de consulta e explicação do público elegível (ELEG-08/09)."""

from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.composicao.api import criar_aplicacao
from central_preventiva.composicao.configuracao import Configuracao

TIPO_PROBLEMA = "application/problem+json"
AREA = "9990001"


def preparar_banco(tmp_path: Path) -> Path:
    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()
    return caminho


def inserir_segurado(caminho: Path, nome: str = "Pessoa Teste", canal: str = "whatsapp") -> str:
    id_segurado = str(uuid4())
    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO segurados (id, nome, codigo_ibge_area, canal_preferido, "
            "participa_de_alertas) VALUES (?, ?, ?, ?, true)",
            [id_segurado, nome, AREA, canal],
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


def inserir_regra(caminho: Path) -> str:
    id_regra = str(uuid4())
    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO regras (id, evento_tipo, limiar_meteorologico, area_aplicavel, "
            "apolice_tipo, cobertura_exigida, antecedencia_horas, canal, versao, estado) "
            "VALUES (?, 'chuva_intensa', 50.0, ?, 'residencial', 'alagamento', 24, "
            "'whatsapp', 3, 'ativa')",
            [id_regra, AREA],
        )
    return id_regra


def inserir_evento(caminho: Path) -> str:
    id_evento = str(uuid4())
    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO eventos_meteorologicos (id, tipo, area, periodo_inicio, "
            "periodo_fim, intensidade, proveniencia, instante_observado) VALUES "
            "(?, 'chuva_intensa', ?, '2026-03-10 06:00:00', '2026-03-10 18:00:00', "
            "72.5, 'sintetico', '2026-03-09 18:00:00')",
            [id_evento, AREA],
        )
    return id_evento


def inserir_resultado_elegibilidade(
    caminho: Path,
    execucao_id: str,
    evento_id: str,
    regra_id: str,
    segurado_id: str,
    apolice_id: str,
    elegivel: bool = True,
    canal: str = "whatsapp",
) -> str:
    id_registro = str(uuid4())
    criterios = (
        '[{"operando": "área afetada", "valor_observado": "9990001", "atende": true, '
        '"justificativa": "Área da apólice corresponde à área do evento (9990001)."}]'
    )
    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO elegibilidades_historicas "
            "(id, execucao_id, evento_id, regra_id, segurado_id, apolice_id, elegivel, "
            "criterios, canal, justificativa) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, "
            "'Segurado e apólice atendem integralmente aos critérios da regra ativa.')",
            [
                id_registro,
                execucao_id,
                evento_id,
                regra_id,
                segurado_id,
                apolice_id,
                elegivel,
                criterios,
                canal,
            ],
        )
    return id_registro


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


def test_get_elegibilidade_com_execucao_sem_nenhum_resultado_devolve_conjunto_vazio(
    tmp_path: Path,
) -> None:
    caminho = preparar_banco(tmp_path)
    execucao_id = str(uuid4())

    resposta = cliente_para(caminho).get(f"/api/v1/execucoes/{execucao_id}/elegibilidade")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["incluidos"] == 0
    assert corpo["excluidos"] == 0
    assert corpo["registros"] == []


def test_get_elegibilidade_retorna_quantidades_e_lista_completa(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    execucao_id = str(uuid4())
    id_segurado = inserir_segurado(caminho, nome="Maria Sintética")
    id_apolice = inserir_apolice(caminho, id_segurado)
    id_regra = inserir_regra(caminho)
    id_evento = inserir_evento(caminho)
    inserir_resultado_elegibilidade(
        caminho, execucao_id, id_evento, id_regra, id_segurado, id_apolice, elegivel=True
    )

    id_segurado_2 = inserir_segurado(caminho, nome="João Sintético", canal="sms")
    id_apolice_2 = inserir_apolice(caminho, id_segurado_2)
    inserir_resultado_elegibilidade(
        caminho,
        execucao_id,
        id_evento,
        id_regra,
        id_segurado_2,
        id_apolice_2,
        elegivel=False,
        canal="sms",
    )

    resposta = cliente_para(caminho).get(f"/api/v1/execucoes/{execucao_id}/elegibilidade")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["incluidos"] == 1
    assert corpo["excluidos"] == 1
    assert len(corpo["registros"]) == 2
    nomes = {registro["nome_segurado"] for registro in corpo["registros"]}
    assert nomes == {"Maria Sintética", "João Sintético"}
    canais = {registro["canal"] for registro in corpo["registros"]}
    assert canais == {"whatsapp", "sms"}


def test_get_elegibilidade_com_id_malformado_retorna_422(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)

    resposta = cliente_para(caminho).get("/api/v1/execucoes/nao-e-um-uuid/elegibilidade")

    assert resposta.status_code == 422
    assert resposta.headers["content-type"] == TIPO_PROBLEMA
    assert resposta.json()["codigo"] == "execucao_id_invalido"


def test_get_registro_elegibilidade_retorna_explicacao_completa(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    execucao_id = str(uuid4())
    id_segurado = inserir_segurado(caminho)
    id_apolice = inserir_apolice(caminho, id_segurado)
    id_regra = inserir_regra(caminho)
    id_evento = inserir_evento(caminho)
    id_registro = inserir_resultado_elegibilidade(
        caminho, execucao_id, id_evento, id_regra, id_segurado, id_apolice
    )

    resposta = cliente_para(caminho).get(
        f"/api/v1/execucoes/{execucao_id}/elegibilidade/{id_registro}"
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["id"] == id_registro
    assert corpo["regra_id"] == id_regra
    assert corpo["regra_versao"] == 3
    assert corpo["elegivel"] is True
    assert len(corpo["criterios"]) == 1
    assert corpo["criterios"][0]["operando"] == "área afetada"
    assert corpo["criterios"][0]["atende"] is True
    assert corpo["justificativa"].startswith("Segurado e apólice atendem integralmente")


def test_get_registro_elegibilidade_inexistente_retorna_404(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    execucao_id = str(uuid4())

    resposta = cliente_para(caminho).get(
        f"/api/v1/execucoes/{execucao_id}/elegibilidade/{uuid4()}"
    )

    assert resposta.status_code == 404
    assert resposta.json()["codigo"] == "resultado_elegibilidade_inexistente"


def test_get_registro_elegibilidade_de_outra_execucao_retorna_404(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    id_segurado = inserir_segurado(caminho)
    id_apolice = inserir_apolice(caminho, id_segurado)
    id_regra = inserir_regra(caminho)
    id_evento = inserir_evento(caminho)
    id_registro = inserir_resultado_elegibilidade(
        caminho, str(uuid4()), id_evento, id_regra, id_segurado, id_apolice
    )

    resposta = cliente_para(caminho).get(
        f"/api/v1/execucoes/{uuid4()}/elegibilidade/{id_registro}"
    )

    assert resposta.status_code == 404


def test_get_registro_elegibilidade_com_id_malformado_retorna_422(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)

    resposta = cliente_para(caminho).get(
        f"/api/v1/execucoes/{uuid4()}/elegibilidade/nao-e-um-uuid"
    )

    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "identificador_invalido"
