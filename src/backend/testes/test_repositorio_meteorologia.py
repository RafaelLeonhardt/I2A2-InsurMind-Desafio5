"""Testes dos repositórios DuckDB de coleta meteorológica do INMET."""

from pathlib import Path
from uuid import uuid4

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.adaptadores.persistencia.repositorio_meteorologia import (
    RepositorioAreasMonitoradas,
    RepositorioEventosMeteorologicos,
    RepositorioSincronizacoes,
)
from central_preventiva.aplicacao.portas_meteorologia import (
    EstadoSincronizacao,
    OrigemSincronizacao,
)
from central_preventiva.dominio.evento_meteorologico import (
    EventoMeteorologico,
    ProvenienciaEvento,
    TipoEventoMeteorologico,
)

from datetime import datetime


def preparar_banco(tmp_path: Path) -> Path:
    """Cria o schema versionado em um arquivo temporário e devolve seu caminho."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()
    return caminho


def inserir_area_monitorada(caminho: Path, codigo_estacao: str, codigo_ibge_area: str) -> None:
    """Insere uma área monitorada de teste, fora do fluxo do semeador canônico."""

    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO areas_monitoradas_inmet "
            "(id, codigo_estacao_inmet, nome_estacao, codigo_ibge_area, ativa) "
            "VALUES (?, ?, 'Estação de Teste', ?, true)",
            [uuid4(), codigo_estacao, codigo_ibge_area],
        )


def test_buscar_area_por_codigo_estacao_resolve_area_sintetica(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    inserir_area_monitorada(caminho, "A701", "9990001")

    area = RepositorioAreasMonitoradas(caminho).buscar_por_codigo_estacao("A701")

    assert area is not None
    assert area.codigo_estacao_inmet == "A701"
    assert area.codigo_ibge_area == "9990001"


def test_buscar_area_por_codigo_estacao_inexistente_devolve_none_sem_lancar(
    tmp_path: Path,
) -> None:
    caminho = preparar_banco(tmp_path)

    assert RepositorioAreasMonitoradas(caminho).buscar_por_codigo_estacao("INEXISTENTE") is None


def test_salvar_evento_meteorologico_persiste_o_evento(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    evento = EventoMeteorologico(
        id=uuid4(),
        tipo=TipoEventoMeteorologico.CHUVA_INTENSA,
        area="9990001",
        periodo_inicio=datetime(2026, 8, 30, 17, 0, 0),
        periodo_fim=datetime(2026, 8, 30, 18, 0, 0),
        intensidade=55.4,
        proveniencia=ProvenienciaEvento.REAL_INMET,
        instante_observado=datetime(2026, 8, 30, 18, 0, 0),
    )

    RepositorioEventosMeteorologicos(caminho).salvar(evento)

    lido = RepositorioEventosMeteorologicos(caminho).buscar_por_id(evento.id)
    assert lido == evento


def test_buscar_evento_inexistente_devolve_none_sem_lancar(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)

    assert RepositorioEventosMeteorologicos(caminho).buscar_por_id(uuid4()) is None


def test_criar_sincronizacao_persiste_em_estado_coletando(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    inserir_area_monitorada(caminho, "A701", "9990001")
    area = RepositorioAreasMonitoradas(caminho).buscar_por_codigo_estacao("A701")
    assert area is not None
    requisicao_id = uuid4()

    sincronizacao = RepositorioSincronizacoes(caminho).criar(
        requisicao_id=requisicao_id,
        area_monitorada_id=area.id,
        origem=OrigemSincronizacao.MANUAL,
        estado=EstadoSincronizacao.COLETANDO,
    )

    assert sincronizacao.requisicao_id == requisicao_id
    assert sincronizacao.estado == EstadoSincronizacao.COLETANDO
    assert sincronizacao.registros_validos == 0
    assert sincronizacao.finalizado_em is None


def test_atualizar_estado_para_concluido_fecha_finalizado_em_e_registros_validos(
    tmp_path: Path,
) -> None:
    caminho = preparar_banco(tmp_path)
    inserir_area_monitorada(caminho, "A701", "9990001")
    area = RepositorioAreasMonitoradas(caminho).buscar_por_codigo_estacao("A701")
    assert area is not None
    repositorio = RepositorioSincronizacoes(caminho)
    sincronizacao = repositorio.criar(
        requisicao_id=uuid4(),
        area_monitorada_id=area.id,
        origem=OrigemSincronizacao.AUTOMATICA,
        estado=EstadoSincronizacao.COLETANDO,
    )

    repositorio.atualizar_estado(
        sincronizacao.id, EstadoSincronizacao.CONCLUIDO, registros_validos=1
    )

    (atualizada,) = repositorio.listar_recentes()
    assert atualizada.estado == EstadoSincronizacao.CONCLUIDO
    assert atualizada.registros_validos == 1
    assert atualizada.finalizado_em is not None


def test_atualizar_estado_para_falha_registra_motivo_falha(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    inserir_area_monitorada(caminho, "A701", "9990001")
    area = RepositorioAreasMonitoradas(caminho).buscar_por_codigo_estacao("A701")
    assert area is not None
    repositorio = RepositorioSincronizacoes(caminho)
    sincronizacao = repositorio.criar(
        requisicao_id=uuid4(),
        area_monitorada_id=area.id,
        origem=OrigemSincronizacao.MANUAL,
        estado=EstadoSincronizacao.COLETANDO,
    )

    repositorio.atualizar_estado(
        sincronizacao.id, EstadoSincronizacao.FALHA, motivo_falha="campo_ausente"
    )

    (atualizada,) = repositorio.listar_recentes()
    assert atualizada.estado == EstadoSincronizacao.FALHA
    assert atualizada.motivo_falha == "campo_ausente"


def test_listar_recentes_ordena_da_mais_recente_para_a_mais_antiga(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    inserir_area_monitorada(caminho, "A701", "9990001")
    area = RepositorioAreasMonitoradas(caminho).buscar_por_codigo_estacao("A701")
    assert area is not None
    repositorio = RepositorioSincronizacoes(caminho)

    with abrir_conexao(caminho) as conexao:
        primeira_id = uuid4()
        segunda_id = uuid4()
        conexao.execute(
            "INSERT INTO sincronizacoes_meteorologicas "
            "(id, requisicao_id, area_monitorada_id, origem, estado, registros_validos, "
            "iniciado_em) VALUES (?, ?, ?, 'manual', 'concluido', 0, TIMESTAMP '2026-08-30 10:00:00')",
            [primeira_id, uuid4(), area.id],
        )
        conexao.execute(
            "INSERT INTO sincronizacoes_meteorologicas "
            "(id, requisicao_id, area_monitorada_id, origem, estado, registros_validos, "
            "iniciado_em) VALUES (?, ?, ?, 'manual', 'concluido', 0, TIMESTAMP '2026-08-30 12:00:00')",
            [segunda_id, uuid4(), area.id],
        )

    historico = repositorio.listar_recentes()

    assert [linha.id for linha in historico] == [segunda_id, primeira_id]


def test_listar_recentes_com_historico_vazio_nao_lanca(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)

    assert RepositorioSincronizacoes(caminho).listar_recentes() == ()
