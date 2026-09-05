"""Testes do recurso REST/JSON do alerta mais relevante do segurado ativo (VISAO-01, 06, 5.1)."""

from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.adaptadores.persistencia.repositorio_elegibilidade import (
    RepositorioElegibilidades,
)
from central_preventiva.adaptadores.persistencia.repositorio_meteorologia import (
    RepositorioEventosMeteorologicos,
)
from central_preventiva.composicao.api import criar_aplicacao
from central_preventiva.composicao.configuracao import Configuracao
from central_preventiva.dominio.avaliador_elegibilidade import ResultadoElegibilidade
from central_preventiva.dominio.avaliador_risco import Criterio
from central_preventiva.dominio.evento_meteorologico import (
    EventoMeteorologico,
    ProvenienciaEvento,
    TipoEventoMeteorologico,
)

TIPO_PROBLEMA = "application/problem+json"
REGRA_ID = UUID("33333333-3333-3333-3333-333333333333")
CARLOS_ID = UUID("44444444-4444-4444-4444-444444444444")
AREA = "9990001"

RESULTADO_INCLUIDO = ResultadoElegibilidade(
    elegivel=True,
    criterios=(Criterio("área afetada", AREA, True, "Área corresponde."),),
    canal="whatsapp",
    motivo="incluido",
    justificativa="Segurado e apólice atendem à regra ativa.",
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


def criar_elegibilidade_incluida(caminho: Path, segurado_id: UUID) -> None:
    """Persiste um evento real e uma elegibilidade `incluido` para o segurado informado."""

    evento = EventoMeteorologico(
        id=uuid4(),
        tipo=TipoEventoMeteorologico.CHUVA_INTENSA,
        area=AREA,
        periodo_inicio=datetime(2026, 9, 4, 12, 0),
        periodo_fim=datetime(2026, 9, 4, 18, 0),
        intensidade=62.5,
        proveniencia=ProvenienciaEvento.REAL_INMET,
        instante_observado=datetime(2026, 9, 4, 18, 0),
    )
    RepositorioEventosMeteorologicos(caminho).salvar(evento)
    RepositorioElegibilidades(caminho).salvar(
        uuid4(), evento.id, REGRA_ID, segurado_id, uuid4(), "Carlos Teste", RESULTADO_INCLUIDO
    )


def test_consultar_alerta_devolve_200_com_alerta_quando_existir(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    criar_elegibilidade_incluida(caminho, CARLOS_ID)

    resposta = cliente_para(caminho).get(f"/api/v1/segurados/{CARLOS_ID}/alerta-mais-relevante")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["alerta"] is not None
    assert corpo["alerta"]["evento_tipo"] == "chuva_intensa"
    assert corpo["alerta"]["origem"] == "real_inmet"
    assert corpo["alerta"]["localizacao"] == AREA
    assert corpo["alerta"]["fonte_degradada"] is False


def test_consultar_alerta_devolve_200_com_alerta_nulo_quando_nao_existir(
    tmp_path: Path,
) -> None:
    caminho = preparar_banco(tmp_path)

    resposta = cliente_para(caminho).get(f"/api/v1/segurados/{CARLOS_ID}/alerta-mais-relevante")

    assert resposta.status_code == 200
    assert resposta.json() == {"alerta": None}


def test_consultar_alerta_de_outro_segurado_nao_vaza_para_o_segurado_consultado(
    tmp_path: Path,
) -> None:
    caminho = preparar_banco(tmp_path)
    criar_elegibilidade_incluida(caminho, uuid4())

    resposta = cliente_para(caminho).get(f"/api/v1/segurados/{CARLOS_ID}/alerta-mais-relevante")

    assert resposta.status_code == 200
    assert resposta.json() == {"alerta": None}


def test_consultar_alerta_com_identificador_invalido_devolve_422(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)

    resposta = cliente_para(caminho).get("/api/v1/segurados/nao-e-um-uuid/alerta-mais-relevante")

    assert resposta.status_code == 422
    assert resposta.headers["content-type"] == TIPO_PROBLEMA
    assert resposta.json()["codigo"] == "identificador_invalido"
