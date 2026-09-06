"""Testes do recurso REST/JSON da apólice do segurado ativo e da explicação de critérios
(APOLICE-01..06, 5.3).
"""

from pathlib import Path
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.adaptadores.persistencia.repositorio_elegibilidade import (
    RepositorioElegibilidades,
)
from central_preventiva.composicao.api import criar_aplicacao
from central_preventiva.composicao.configuracao import Configuracao
from central_preventiva.dominio.avaliador_elegibilidade import ResultadoElegibilidade
from central_preventiva.dominio.avaliador_risco import Criterio

TIPO_PROBLEMA = "application/problem+json"
REGRA_ID = UUID("33333333-3333-3333-3333-333333333333")
EVENTO_ID = UUID("22222222-2222-2222-2222-222222222222")
CARLOS_ID = UUID("44444444-4444-4444-4444-444444444444")
AREA = "9990001"

CRITERIOS = (
    Criterio("área afetada", AREA, True, "Área da apólice corresponde à área do evento."),
    Criterio("tipo da apólice", "residencial", True, "Tipo corresponde ao exigido."),
    Criterio("situação da apólice", "ativa", True, "Apólice está ativa."),
    Criterio("cobertura exigida", "alagamento", True, "Apólice possui a cobertura exigida."),
    Criterio("participação em alertas", "True", True, "Segurado participa de alertas."),
)


def preparar_banco(tmp_path: Path) -> Path:
    """Aplica as migrações versionadas e semeia a regra em um banco temporário."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()
    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO regras (id, evento_tipo, limiar_meteorologico, area_aplicavel, "
            "apolice_tipo, cobertura_exigida, antecedencia_horas, canal, versao, estado) "
            "VALUES (?, 'chuva_intensa', 50.0, ?, 'residencial', 'alagamento', 24, "
            "'whatsapp', 1, 'ativa')",
            [REGRA_ID, AREA],
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


def criar_segurado(
    caminho: Path,
    segurado_id: UUID = CARLOS_ID,
    canal_preferido: str = "sms",
    participa_de_alertas: bool = True,
) -> None:
    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO segurados (id, nome, codigo_ibge_area, canal_preferido, "
            "participa_de_alertas) VALUES (?, 'Carlos Teste', ?, ?, ?)",
            [segurado_id, AREA, canal_preferido, participa_de_alertas],
        )


def criar_apolice(
    caminho: Path,
    segurado_id: UUID = CARLOS_ID,
    numero: str = "RES-0001",
    situacao: str = "ativa",
    vigencia_inicio: str = "2026-01-01",
    vigencia_fim: str = "2030-12-31",
    coberturas: tuple[str, ...] = ("alagamento", "vendaval"),
    endereco: str = "Rua Sintética, 123",
) -> UUID:
    id_apolice = uuid4()
    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO apolices (id, segurado_id, numero, tipo, situacao, "
            "vigencia_inicio, vigencia_fim, coberturas, endereco_risco_sintetico, "
            "codigo_ibge_area) VALUES (?, ?, ?, 'residencial', ?, ?, ?, ?, ?, ?)",
            [
                id_apolice, segurado_id, numero, situacao, vigencia_inicio, vigencia_fim,
                list(coberturas), endereco, AREA,
            ],
        )
    return id_apolice


def criar_elegibilidade(caminho: Path, segurado_id: UUID = CARLOS_ID) -> UUID:
    resultado = ResultadoElegibilidade(
        elegivel=True,
        criterios=CRITERIOS,
        canal="whatsapp",
        motivo="incluido",
        justificativa="Segurado e apólice atendem integralmente aos critérios da regra ativa.",
    )
    id_registro = RepositorioElegibilidades(caminho).salvar(
        uuid4(), EVENTO_ID, REGRA_ID, segurado_id, uuid4(), "Carlos Teste", resultado
    )
    assert id_registro is not None
    return id_registro


def test_consultar_apolice_devolve_200_com_todos_os_campos_do_contrato(
    tmp_path: Path,
) -> None:
    caminho = preparar_banco(tmp_path)
    criar_segurado(caminho)
    criar_apolice(caminho)

    resposta = cliente_para(caminho).get(f"/api/v1/segurados/{CARLOS_ID}/apolice")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["numero"] == "RES-0001"
    assert corpo["tipo"] == "residencial"
    assert corpo["situacao"] == "ativa"
    assert corpo["estado_objetivo"] == "ativa"
    assert corpo["vigencia_inicio"] == "2026-01-01"
    assert corpo["vigencia_fim"] == "2030-12-31"
    assert corpo["endereco_risco_sintetico"] == "Rua Sintética, 123"
    assert corpo["coberturas"] == ["alagamento", "vendaval"]
    assert corpo["canal_preferido"] == "sms"
    assert corpo["participa_de_alertas"] is True


def test_consultar_apolice_cancelada_devolve_estado_objetivo_textual(
    tmp_path: Path,
) -> None:
    caminho = preparar_banco(tmp_path)
    criar_segurado(caminho)
    criar_apolice(caminho, situacao="cancelada")

    resposta = cliente_para(caminho).get(f"/api/v1/segurados/{CARLOS_ID}/apolice")

    assert resposta.status_code == 200
    assert resposta.json()["estado_objetivo"] == "cancelada"


def test_consultar_apolice_suspensa_devolve_estado_objetivo_textual(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    criar_segurado(caminho)
    criar_apolice(caminho, situacao="suspensa")

    resposta = cliente_para(caminho).get(f"/api/v1/segurados/{CARLOS_ID}/apolice")

    assert resposta.status_code == 200
    assert resposta.json()["estado_objetivo"] == "suspensa"


def test_consultar_apolice_com_canal_e_participacao_nao_padrao(tmp_path: Path) -> None:
    """L-061: `participa_de_alertas`/`canal_preferido` só apareciam com um valor em toda
    a suíte — fixar qualquer um deles em `_resposta_apolice` não quebrava nada."""

    caminho = preparar_banco(tmp_path)
    criar_segurado(caminho, canal_preferido="whatsapp", participa_de_alertas=False)
    criar_apolice(caminho)

    resposta = cliente_para(caminho).get(f"/api/v1/segurados/{CARLOS_ID}/apolice")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["canal_preferido"] == "whatsapp"
    assert corpo["participa_de_alertas"] is False


def test_consultar_apolice_ativa_expirada_devolve_estado_expirada(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    criar_segurado(caminho)
    criar_apolice(caminho, situacao="ativa", vigencia_fim="2020-01-01")

    resposta = cliente_para(caminho).get(f"/api/v1/segurados/{CARLOS_ID}/apolice")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["situacao"] == "ativa"
    assert corpo["estado_objetivo"] == "expirada"


def test_consultar_apolice_inexistente_devolve_404(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    criar_segurado(caminho)

    resposta = cliente_para(caminho).get(f"/api/v1/segurados/{CARLOS_ID}/apolice")

    assert resposta.status_code == 404
    assert resposta.headers["content-type"] == TIPO_PROBLEMA
    assert resposta.json()["codigo"] == "apolice_nao_encontrada"


def test_consultar_apolice_de_outro_segurado_nao_vaza_para_o_segurado_consultado(
    tmp_path: Path,
) -> None:
    caminho = preparar_banco(tmp_path)
    criar_segurado(caminho)
    outro_segurado = uuid4()
    criar_segurado(caminho, segurado_id=outro_segurado)
    criar_apolice(caminho, segurado_id=outro_segurado)

    resposta_outro = cliente_para(caminho).get(f"/api/v1/segurados/{CARLOS_ID}/apolice")
    resposta_inexistente = cliente_para(caminho).get(
        f"/api/v1/segurados/{uuid4()}/apolice"
    )

    corpo_outro = resposta_outro.json()
    corpo_inexistente = resposta_inexistente.json()
    assert resposta_outro.status_code == 404
    assert resposta_inexistente.status_code == 404
    assert corpo_outro["codigo"] == corpo_inexistente["codigo"] == "apolice_nao_encontrada"
    assert corpo_outro["impacto"] == corpo_inexistente["impacto"]
    assert corpo_outro["proxima_acao"] == corpo_inexistente["proxima_acao"]


def test_consultar_apolice_com_identificador_invalido_devolve_422(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)

    resposta = cliente_para(caminho).get("/api/v1/segurados/nao-e-um-uuid/apolice")

    assert resposta.status_code == 422
    assert resposta.headers["content-type"] == TIPO_PROBLEMA
    assert resposta.json()["codigo"] == "identificador_invalido"


def test_consultar_explicacao_devolve_200_com_criterios_filtrados_e_completos(
    tmp_path: Path,
) -> None:
    caminho = preparar_banco(tmp_path)
    criar_segurado(caminho)
    # A apólice tem duas coberturas ("alagamento", "vendaval") - só "alagamento" participou
    # da regra avaliada (Edge Case da spec, ver asserção abaixo).
    criar_apolice(caminho)
    elegibilidade_id = criar_elegibilidade(caminho)

    resposta = cliente_para(caminho).get(
        f"/api/v1/segurados/{CARLOS_ID}/apolice/explicacao/{elegibilidade_id}"
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["elegibilidade_id"] == str(elegibilidade_id)
    operandos = {criterio["operando"] for criterio in corpo["criterios"]}
    assert operandos == {
        "área afetada", "tipo da apólice", "situação da apólice", "cobertura exigida",
    }
    criterio_area = next(c for c in corpo["criterios"] if c["operando"] == "área afetada")
    assert criterio_area["valor_observado"] == AREA
    assert criterio_area["atende"] is True
    assert criterio_area["justificativa"] == "Área da apólice corresponde à área do evento."
    # Edge Case da spec: a apólice tem duas coberturas ("alagamento", "vendaval"), mas só
    # "alagamento" participou da regra — a explicação nunca cita "vendaval" como se também
    # tivesse participado.
    valores_observados = {c["valor_observado"] for c in corpo["criterios"]}
    assert "vendaval" not in valores_observados
    criterio_cobertura = next(c for c in corpo["criterios"] if c["operando"] == "cobertura exigida")
    assert criterio_cobertura["valor_observado"] == "alagamento"


def test_consultar_explicacao_com_criterio_nao_atendido(tmp_path: Path) -> None:
    """L-061: `atende` só aparecia como `True` em toda a suíte HTTP — fixar
    `atende=True` em `_resposta_criterio` não quebrava nada."""

    caminho = preparar_banco(tmp_path)
    criar_segurado(caminho)
    criterios_com_reprovacao = (
        Criterio("área afetada", AREA, True, "Área da apólice corresponde à área do evento."),
        Criterio("tipo da apólice", "residencial", True, "Tipo corresponde ao exigido."),
        Criterio("situação da apólice", "ativa", True, "Apólice está ativa."),
        Criterio(
            "cobertura exigida", "nenhuma", False,
            "Apólice não possui a cobertura exigida pela regra (alagamento).",
        ),
    )
    resultado = ResultadoElegibilidade(
        elegivel=False,
        criterios=criterios_com_reprovacao,
        canal="whatsapp",
        motivo="cobertura_ausente",
        justificativa="Apólice não possui a cobertura exigida pela regra ativa.",
    )
    elegibilidade_id = RepositorioElegibilidades(caminho).salvar(
        uuid4(), EVENTO_ID, REGRA_ID, CARLOS_ID, uuid4(), "Carlos Teste", resultado
    )
    assert elegibilidade_id is not None

    resposta = cliente_para(caminho).get(
        f"/api/v1/segurados/{CARLOS_ID}/apolice/explicacao/{elegibilidade_id}"
    )

    assert resposta.status_code == 200
    criterio_cobertura = next(
        c for c in resposta.json()["criterios"] if c["operando"] == "cobertura exigida"
    )
    assert criterio_cobertura["atende"] is False


def test_consultar_explicacao_inexistente_devolve_404(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    criar_segurado(caminho)

    resposta = cliente_para(caminho).get(
        f"/api/v1/segurados/{CARLOS_ID}/apolice/explicacao/{uuid4()}"
    )

    assert resposta.status_code == 404
    assert resposta.json()["codigo"] == "explicacao_nao_encontrada"


def test_consultar_explicacao_de_outro_segurado_devolve_404_identico(
    tmp_path: Path,
) -> None:
    caminho = preparar_banco(tmp_path)
    criar_segurado(caminho)
    outro_segurado = uuid4()
    criar_segurado(caminho, segurado_id=outro_segurado)
    elegibilidade_de_outro = criar_elegibilidade(caminho, segurado_id=outro_segurado)

    resposta_outro = cliente_para(caminho).get(
        f"/api/v1/segurados/{CARLOS_ID}/apolice/explicacao/{elegibilidade_de_outro}"
    )
    resposta_inexistente = cliente_para(caminho).get(
        f"/api/v1/segurados/{CARLOS_ID}/apolice/explicacao/{uuid4()}"
    )

    corpo_outro = resposta_outro.json()
    corpo_inexistente = resposta_inexistente.json()
    assert resposta_outro.status_code == 404
    assert resposta_inexistente.status_code == 404
    assert corpo_outro["codigo"] == corpo_inexistente["codigo"] == "explicacao_nao_encontrada"
    assert corpo_outro["impacto"] == corpo_inexistente["impacto"]
    assert corpo_outro["proxima_acao"] == corpo_inexistente["proxima_acao"]


def test_consultar_explicacao_apos_apolice_atual_mudar_mantem_o_snapshot(
    tmp_path: Path,
) -> None:
    """APOLICE-05 na fronteira HTTP: a rota da explicação nunca lê a apólice atual."""

    caminho = preparar_banco(tmp_path)
    criar_segurado(caminho)
    criar_apolice(caminho, situacao="ativa")
    elegibilidade_id = criar_elegibilidade(caminho)

    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "UPDATE apolices SET situacao = 'cancelada' WHERE segurado_id = ?", [CARLOS_ID]
        )

    resposta = cliente_para(caminho).get(
        f"/api/v1/segurados/{CARLOS_ID}/apolice/explicacao/{elegibilidade_id}"
    )

    assert resposta.status_code == 200
    criterio_situacao = next(
        c for c in resposta.json()["criterios"] if c["operando"] == "situação da apólice"
    )
    assert criterio_situacao["valor_observado"] == "ativa"


def test_consultar_explicacao_com_identificador_invalido_devolve_422(
    tmp_path: Path,
) -> None:
    caminho = preparar_banco(tmp_path)

    resposta = cliente_para(caminho).get(
        f"/api/v1/segurados/{CARLOS_ID}/apolice/explicacao/nao-e-um-uuid"
    )

    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "identificador_invalido"
