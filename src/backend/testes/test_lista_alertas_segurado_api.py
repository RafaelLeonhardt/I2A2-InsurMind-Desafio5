"""Testes do recurso REST/JSON da lista e do detalhe dos alertas do segurado
(ALERTAS-01..06, 5.2)."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.adaptadores.persistencia.repositorio_elegibilidade import (
    RepositorioElegibilidades,
)
from central_preventiva.adaptadores.persistencia.repositorio_execucao_preventiva import (
    RepositorioExecucaoPreventiva,
)
from central_preventiva.adaptadores.persistencia.repositorio_meteorologia import (
    RepositorioEventosMeteorologicos,
    RepositorioSincronizacoes,
)
from central_preventiva.aplicacao.portas_meteorologia import (
    EstadoSincronizacao,
    OrigemSincronizacao,
)
from central_preventiva.composicao.api import criar_aplicacao
from central_preventiva.composicao.configuracao import Configuracao
from central_preventiva.dominio.avaliador_elegibilidade import ResultadoElegibilidade
from central_preventiva.dominio.avaliador_risco import Criterio
from central_preventiva.dominio.estados_execucao import EstadoExecucao
from central_preventiva.dominio.evento_meteorologico import (
    EventoMeteorologico,
    ProvenienciaEvento,
    TipoEventoMeteorologico,
)

TIPO_PROBLEMA = "application/problem+json"
REGRA_ID = UUID("33333333-3333-3333-3333-333333333333")
CARLOS_ID = UUID("44444444-4444-4444-4444-444444444444")
APOLICE_ID = UUID("55555555-5555-5555-5555-555555555555")
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
        origem_frontend="http://127.0.0.1:5151",
        caminho_banco=caminho,
    )
    return TestClient(criar_aplicacao(configuracao))


def criar_evento(
    caminho: Path,
    periodo_inicio: datetime,
    periodo_fim: datetime,
    proveniencia: ProvenienciaEvento = ProvenienciaEvento.REAL_INMET,
) -> EventoMeteorologico:
    """Persiste um evento real com o período informado.

    `instante_observado` é distinto de `periodo_inicio`/`periodo_fim` de propósito — os
    três campos precisam de valores diferentes entre si para que uma troca entre
    quaisquer dois deles na resposta HTTP seja detectável por asserção.
    """

    evento = EventoMeteorologico(
        id=uuid4(),
        tipo=TipoEventoMeteorologico.CHUVA_INTENSA,
        area=AREA,
        periodo_inicio=periodo_inicio,
        periodo_fim=periodo_fim,
        intensidade=62.5,
        proveniencia=proveniencia,
        instante_observado=periodo_inicio - timedelta(hours=1),
    )
    RepositorioEventosMeteorologicos(caminho).salvar(evento)
    return evento


def criar_elegibilidade(
    caminho: Path, evento_id: UUID, execucao_id: UUID, segurado_id: UUID = CARLOS_ID
) -> UUID:
    """Persiste uma elegibilidade `incluido` correlacionada à execução informada."""

    id_registro = RepositorioElegibilidades(caminho).salvar(
        execucao_id, evento_id, REGRA_ID, segurado_id, APOLICE_ID, "Carlos Teste",
        RESULTADO_INCLUIDO,
    )
    assert id_registro is not None
    return id_registro


def _periodo_futuro() -> tuple[datetime, datetime]:
    inicio = datetime.now(UTC).replace(tzinfo=None) + timedelta(days=7)
    return inicio, inicio + timedelta(hours=6)


def test_listar_devolve_200_com_lista_vazia_sem_alertas(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)

    resposta = cliente_para(caminho).get(f"/api/v1/segurados/{CARLOS_ID}/alertas")

    assert resposta.status_code == 200
    assert resposta.json() == {"alertas": []}


def test_listar_devolve_alertas_com_classificacoes_distintas(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    execucoes = RepositorioExecucaoPreventiva(caminho)

    inicio_futuro, fim_futuro = _periodo_futuro()
    evento_ativo = criar_evento(caminho, inicio_futuro, fim_futuro)
    execucao_ativa = execucoes.criar(EstadoExecucao.CONCLUIDA)
    criar_elegibilidade(caminho, evento_ativo.id, execucao_ativa)

    evento_pendente = criar_evento(
        caminho, inicio_futuro + timedelta(days=1), fim_futuro + timedelta(days=1)
    )
    execucao_pendente = execucoes.criar(EstadoExecucao.SIMULANDO)
    criar_elegibilidade(caminho, evento_pendente.id, execucao_pendente)

    resposta = cliente_para(caminho).get(f"/api/v1/segurados/{CARLOS_ID}/alertas")

    assert resposta.status_code == 200
    classificacoes = {item["classificacao"] for item in resposta.json()["alertas"]}
    assert classificacoes == {"ativo", "ainda_nao_simulado"}
    assert len(resposta.json()["alertas"]) == 2


def test_listar_nao_devolve_alertas_de_outro_segurado(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    execucoes = RepositorioExecucaoPreventiva(caminho)
    inicio, fim = _periodo_futuro()
    evento = criar_evento(caminho, inicio, fim)
    execucao_id = execucoes.criar(EstadoExecucao.CONCLUIDA)
    criar_elegibilidade(caminho, evento.id, execucao_id, segurado_id=uuid4())

    resposta = cliente_para(caminho).get(f"/api/v1/segurados/{CARLOS_ID}/alertas")

    assert resposta.status_code == 200
    assert resposta.json() == {"alertas": []}


def test_consultar_detalhe_devolve_200_com_todos_os_campos_do_contrato(
    tmp_path: Path,
) -> None:
    """Contrato completo: prova que a rota não inverte/mistura nenhum dos campos ao
    traduzir `AlertaSegurado` e o detalhe para o corpo público."""

    caminho = preparar_banco(tmp_path)
    execucoes = RepositorioExecucaoPreventiva(caminho)
    inicio, fim = _periodo_futuro()
    evento = criar_evento(caminho, inicio, fim)
    execucao_id = execucoes.criar(EstadoExecucao.CONCLUIDA)
    elegibilidade_id = criar_elegibilidade(caminho, evento.id, execucao_id)

    resposta = cliente_para(caminho).get(
        f"/api/v1/segurados/{CARLOS_ID}/alertas/{elegibilidade_id}"
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["classificacao"] == "ativo"
    assert corpo["apolice_id"] == str(APOLICE_ID)
    assert corpo["justificativa"] == "Segurado e apólice atendem à regra ativa."
    alerta = corpo["alerta"]
    assert alerta["evento_tipo"] == "chuva_intensa"
    assert alerta["origem"] == "real_inmet"
    assert alerta["localizacao"] == AREA
    assert alerta["fonte_degradada"] is False
    assert alerta["periodo_inicio"] == evento.periodo_inicio.isoformat()
    assert alerta["periodo_fim"] == evento.periodo_fim.isoformat()
    assert alerta["instante_observado"] == evento.instante_observado.isoformat()
    assert "62.5" in alerta["severidade"]
    assert alerta["impactos_esperados"] == ["alagamento"]
    assert len(alerta["recomendacoes"]) > 0
    assert len(corpo["linha_do_tempo"]) > 0


def test_consultar_detalhe_de_evento_sintetico_com_fonte_degradada(tmp_path: Path) -> None:
    """A fronteira HTTP do detalhe nunca hardcoda `origem`/`fonte_degradada` — os demais
    testes desta rota só usam evento real com fonte operacional, o que deixaria a rota
    livre para fixar os dois campos sem que nenhum teste percebesse."""

    caminho = preparar_banco(tmp_path)
    execucoes = RepositorioExecucaoPreventiva(caminho)
    inicio, fim = _periodo_futuro()
    evento = criar_evento(caminho, inicio, fim, proveniencia=ProvenienciaEvento.SINTETICO)
    execucao_id = execucoes.criar(EstadoExecucao.CONCLUIDA)
    elegibilidade_id = criar_elegibilidade(caminho, evento.id, execucao_id)

    resposta = cliente_para(caminho).get(
        f"/api/v1/segurados/{CARLOS_ID}/alertas/{elegibilidade_id}"
    )

    assert resposta.status_code == 200
    assert resposta.json()["alerta"]["origem"] == "sintetico"


def test_consultar_lista_com_fonte_degradada_devolve_fonte_degradada_true(
    tmp_path: Path,
) -> None:
    caminho = preparar_banco(tmp_path)
    execucoes = RepositorioExecucaoPreventiva(caminho)
    inicio, fim = _periodo_futuro()
    evento = criar_evento(caminho, inicio, fim)
    execucao_id = execucoes.criar(EstadoExecucao.CONCLUIDA)
    criar_elegibilidade(caminho, evento.id, execucao_id)
    id_area = uuid4()
    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO areas_monitoradas_inmet "
            "(id, codigo_estacao_inmet, nome_estacao, codigo_ibge_area, ativa) "
            "VALUES (?, 'A701', 'Estação de Teste', ?, true)",
            [id_area, AREA],
        )
    sincronizacoes = RepositorioSincronizacoes(caminho)
    sincronizacao = sincronizacoes.criar(
        uuid4(), id_area, OrigemSincronizacao.AUTOMATICA, EstadoSincronizacao.COLETANDO
    )
    sincronizacoes.atualizar_estado(sincronizacao.id, EstadoSincronizacao.FALHA)

    resposta = cliente_para(caminho).get(f"/api/v1/segurados/{CARLOS_ID}/alertas")

    assert resposta.status_code == 200
    [item] = resposta.json()["alertas"]
    assert item["alerta"]["fonte_degradada"] is True


def test_consultar_detalhe_de_execucao_nao_terminal_devolve_ainda_nao_simulado(
    tmp_path: Path,
) -> None:
    caminho = preparar_banco(tmp_path)
    execucoes = RepositorioExecucaoPreventiva(caminho)
    inicio, fim = _periodo_futuro()
    evento = criar_evento(caminho, inicio, fim)
    execucao_id = execucoes.criar(EstadoExecucao.PROCESSANDO_MENSAGENS)
    elegibilidade_id = criar_elegibilidade(caminho, evento.id, execucao_id)

    resposta = cliente_para(caminho).get(
        f"/api/v1/segurados/{CARLOS_ID}/alertas/{elegibilidade_id}"
    )

    assert resposta.status_code == 200
    assert resposta.json()["classificacao"] == "ainda_nao_simulado"


def test_consultar_detalhe_de_execucao_terminal_sem_simulacao_devolve_ainda_nao_simulado(
    tmp_path: Path,
) -> None:
    """A generalização da classificação (5.2, aplicacao/lista_alertas_segurado.py) cobre
    também um terminal técnico anterior à simulação, não só os 4 estados do diagrama."""

    caminho = preparar_banco(tmp_path)
    execucoes = RepositorioExecucaoPreventiva(caminho)
    inicio, fim = _periodo_futuro()
    evento = criar_evento(caminho, inicio, fim)
    execucao_id = execucoes.criar(EstadoExecucao.FALHOU_PREPARACAO_IA)
    elegibilidade_id = criar_elegibilidade(caminho, evento.id, execucao_id)

    resposta = cliente_para(caminho).get(
        f"/api/v1/segurados/{CARLOS_ID}/alertas/{elegibilidade_id}"
    )

    assert resposta.status_code == 200
    assert resposta.json()["classificacao"] == "ainda_nao_simulado"


def test_consultar_detalhe_inexistente_devolve_404(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)

    resposta = cliente_para(caminho).get(f"/api/v1/segurados/{CARLOS_ID}/alertas/{uuid4()}")

    assert resposta.status_code == 404
    assert resposta.headers["content-type"] == TIPO_PROBLEMA
    assert resposta.json()["codigo"] == "alerta_nao_encontrado"


def test_consultar_detalhe_de_outro_segurado_devolve_404_identico(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    execucoes = RepositorioExecucaoPreventiva(caminho)
    inicio, fim = _periodo_futuro()
    evento = criar_evento(caminho, inicio, fim)
    execucao_id = execucoes.criar(EstadoExecucao.CONCLUIDA)
    elegibilidade_de_outro = criar_elegibilidade(
        caminho, evento.id, execucao_id, segurado_id=uuid4()
    )

    resposta_outro = cliente_para(caminho).get(
        f"/api/v1/segurados/{CARLOS_ID}/alertas/{elegibilidade_de_outro}"
    )
    resposta_inexistente = cliente_para(caminho).get(
        f"/api/v1/segurados/{CARLOS_ID}/alertas/{uuid4()}"
    )

    corpo_outro = resposta_outro.json()
    corpo_inexistente = resposta_inexistente.json()
    assert resposta_outro.status_code == 404
    assert corpo_outro["codigo"] == corpo_inexistente["codigo"] == "alerta_nao_encontrado"
    assert corpo_outro["impacto"] == corpo_inexistente["impacto"]
    assert corpo_outro["proxima_acao"] == corpo_inexistente["proxima_acao"]


def test_listar_com_identificador_invalido_devolve_422(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)

    resposta = cliente_para(caminho).get("/api/v1/segurados/nao-e-um-uuid/alertas")

    assert resposta.status_code == 422
    assert resposta.headers["content-type"] == TIPO_PROBLEMA
    assert resposta.json()["codigo"] == "identificador_invalido"


def test_consultar_detalhe_com_identificador_invalido_devolve_422(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)

    resposta = cliente_para(caminho).get(
        f"/api/v1/segurados/{CARLOS_ID}/alertas/nao-e-um-uuid"
    )

    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "identificador_invalido"
