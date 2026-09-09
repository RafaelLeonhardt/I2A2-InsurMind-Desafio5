"""Testes dos repositórios DuckDB de coleta meteorológica do INMET."""

from datetime import datetime
from pathlib import Path
from uuid import uuid4

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.adaptadores.persistencia.repositorio_meteorologia import (
    RepositorioAreasMonitoradas,
    RepositorioCenariosSinteticosAtivados,
    RepositorioEventosMeteorologicos,
    RepositorioSincronizacoes,
    RepositorioTentativasColeta,
)
from central_preventiva.aplicacao.portas_meteorologia import (
    CodigoResultadoTentativa,
    EstadoSincronizacao,
    OrigemSincronizacao,
)
from central_preventiva.dominio.evento_meteorologico import (
    EventoMeteorologico,
    ProvenienciaEvento,
    TipoEventoMeteorologico,
)


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


def inserir_execucao(caminho: Path, execucao_id, estado: str) -> None:
    """Insere uma execução preventiva de teste, fora do fluxo real de orquestração."""

    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO execucao_preventiva (id, estado) VALUES (?, ?)",
            [execucao_id, estado],
        )


def inserir_avaliacao_risco(
    caminho: Path, execucao_id, evento_id, criado_em: datetime
) -> None:
    """Insere uma avaliação de risco de teste, ligando evento e execução (migração 0004)."""

    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO avaliacoes_risco "
            "(id, execucao_id, evento_id, regra_id, regra_versao, relevante, criterios, "
            "motivo, criado_em) VALUES (?, ?, ?, NULL, NULL, true, '[]', 'evento_relevante', ?)",
            [uuid4(), execucao_id, evento_id, criado_em],
        )


def test_mapear_execucoes_por_evento_devolve_vazio_sem_nenhuma_avaliacao(
    tmp_path: Path,
) -> None:
    caminho = preparar_banco(tmp_path)

    assert RepositorioEventosMeteorologicos(caminho).mapear_execucoes_por_evento() == {}


def test_mapear_execucoes_por_evento_liga_evento_a_sua_execucao(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    evento_id = uuid4()
    execucao_id = uuid4()
    inserir_execucao(caminho, execucao_id, "aguardando_geracao")
    inserir_avaliacao_risco(caminho, execucao_id, evento_id, datetime(2026, 8, 30, 18, 0, 0))

    mapa = RepositorioEventosMeteorologicos(caminho).mapear_execucoes_por_evento()

    assert mapa == {evento_id: (execucao_id, "aguardando_geracao")}


def test_mapear_execucoes_por_evento_mantem_so_a_avaliacao_mais_recente_por_evento(
    tmp_path: Path,
) -> None:
    caminho = preparar_banco(tmp_path)
    evento_id = uuid4()
    execucao_antiga_id = uuid4()
    execucao_recente_id = uuid4()
    inserir_execucao(caminho, execucao_antiga_id, "concluido")
    inserir_execucao(caminho, execucao_recente_id, "aguardando_geracao")
    inserir_avaliacao_risco(
        caminho, execucao_antiga_id, evento_id, datetime(2026, 8, 30, 10, 0, 0)
    )
    inserir_avaliacao_risco(
        caminho, execucao_recente_id, evento_id, datetime(2026, 8, 30, 20, 0, 0)
    )

    mapa = RepositorioEventosMeteorologicos(caminho).mapear_execucoes_por_evento()

    assert mapa == {evento_id: (execucao_recente_id, "aguardando_geracao")}


def test_listar_sinteticos_por_tipo_exclui_eventos_reais_do_mesmo_tipo(tmp_path: Path) -> None:
    """2.4 T3: o teste determinístico de uma regra só pode usar cenários sintéticos — um
    evento real do mesmo tipo (ex.: coletado do INMET) nunca deve ser incluído."""

    caminho = preparar_banco(tmp_path)
    repo = RepositorioEventosMeteorologicos(caminho)
    sintetico = EventoMeteorologico(
        id=uuid4(),
        tipo=TipoEventoMeteorologico.CHUVA_INTENSA,
        area="9990001",
        periodo_inicio=datetime(2026, 3, 10, 6, 0, 0),
        periodo_fim=datetime(2026, 3, 10, 18, 0, 0),
        intensidade=72.5,
        proveniencia=ProvenienciaEvento.SINTETICO,
        instante_observado=datetime(2026, 3, 9, 18, 0, 0),
    )
    real = EventoMeteorologico(
        id=uuid4(),
        tipo=TipoEventoMeteorologico.CHUVA_INTENSA,
        area="9990001",
        periodo_inicio=datetime(2026, 8, 30, 17, 0, 0),
        periodo_fim=datetime(2026, 8, 30, 18, 0, 0),
        intensidade=55.4,
        proveniencia=ProvenienciaEvento.REAL_INMET,
        instante_observado=datetime(2026, 8, 30, 18, 0, 0),
    )
    repo.salvar(sintetico)
    repo.salvar(real)

    resultado = repo.listar_sinteticos_por_tipo(TipoEventoMeteorologico.CHUVA_INTENSA)

    assert [evento.id for evento in resultado] == [sintetico.id]


def test_listar_sinteticos_por_tipo_filtra_por_tipo_de_evento(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    repo = RepositorioEventosMeteorologicos(caminho)
    chuva = EventoMeteorologico(
        id=uuid4(),
        tipo=TipoEventoMeteorologico.CHUVA_INTENSA,
        area="9990001",
        periodo_inicio=datetime(2026, 3, 10, 6, 0, 0),
        periodo_fim=datetime(2026, 3, 10, 18, 0, 0),
        intensidade=72.5,
        proveniencia=ProvenienciaEvento.SINTETICO,
        instante_observado=datetime(2026, 3, 9, 18, 0, 0),
    )
    granizo = EventoMeteorologico(
        id=uuid4(),
        tipo=TipoEventoMeteorologico.GRANIZO,
        area="9990002",
        periodo_inicio=datetime(2026, 3, 12, 14, 0, 0),
        periodo_fim=datetime(2026, 3, 12, 20, 0, 0),
        intensidade=31.0,
        proveniencia=ProvenienciaEvento.SINTETICO,
        instante_observado=datetime(2026, 3, 12, 8, 0, 0),
    )
    repo.salvar(chuva)
    repo.salvar(granizo)

    resultado = repo.listar_sinteticos_por_tipo(TipoEventoMeteorologico.GRANIZO)

    assert [evento.id for evento in resultado] == [granizo.id]


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
            "iniciado_em) "
            "VALUES (?, ?, ?, 'manual', 'concluido', 0, TIMESTAMP '2026-08-30 10:00:00')",
            [primeira_id, uuid4(), area.id],
        )
        conexao.execute(
            "INSERT INTO sincronizacoes_meteorologicas "
            "(id, requisicao_id, area_monitorada_id, origem, estado, registros_validos, "
            "iniciado_em) "
            "VALUES (?, ?, ?, 'manual', 'concluido', 0, TIMESTAMP '2026-08-30 12:00:00')",
            [segunda_id, uuid4(), area.id],
        )

    historico = repositorio.listar_recentes()

    assert [linha.id for linha in historico] == [segunda_id, primeira_id]


def test_listar_recentes_com_historico_vazio_nao_lanca(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)

    assert RepositorioSincronizacoes(caminho).listar_recentes() == ()


def _criar_sincronizacao(caminho: Path) -> object:
    inserir_area_monitorada(caminho, "A701", "9990001")
    area = RepositorioAreasMonitoradas(caminho).buscar_por_codigo_estacao("A701")
    assert area is not None
    return RepositorioSincronizacoes(caminho).criar(
        requisicao_id=uuid4(),
        area_monitorada_id=area.id,
        origem=OrigemSincronizacao.MANUAL,
        estado=EstadoSincronizacao.COLETANDO,
    )


def test_registrar_tentativa_persiste_numero_codigo_e_instantes(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    sincronizacao = _criar_sincronizacao(caminho)
    inicio = datetime(2026, 8, 30, 12, 0, 0)
    fim = datetime(2026, 8, 30, 12, 0, 5)

    RepositorioTentativasColeta(caminho).registrar_tentativa(
        sincronizacao.id, 1, CodigoResultadoTentativa.TIMEOUT, inicio, fim  # type: ignore[attr-defined]
    )
    tentativas = RepositorioTentativasColeta(caminho).listar_tentativas(sincronizacao.id)  # type: ignore[attr-defined]

    assert len(tentativas) == 1
    assert tentativas[0].numero_tentativa == 1
    assert tentativas[0].codigo_resultado == CodigoResultadoTentativa.TIMEOUT
    assert tentativas[0].iniciado_em == inicio
    assert tentativas[0].finalizado_em == fim


def test_listar_tentativas_ordena_por_numero_crescente(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    sincronizacao = _criar_sincronizacao(caminho)
    repositorio = RepositorioTentativasColeta(caminho)
    repositorio.registrar_tentativa(
        sincronizacao.id,  # type: ignore[attr-defined]
        2,
        CodigoResultadoTentativa.SUCESSO,
        datetime(2026, 8, 30, 12, 0, 3),
        datetime(2026, 8, 30, 12, 0, 4),
    )
    repositorio.registrar_tentativa(
        sincronizacao.id,  # type: ignore[attr-defined]
        1,
        CodigoResultadoTentativa.TIMEOUT,
        datetime(2026, 8, 30, 12, 0, 0),
        datetime(2026, 8, 30, 12, 0, 1),
    )

    tentativas = repositorio.listar_tentativas(sincronizacao.id)  # type: ignore[attr-defined]

    assert [tentativa.numero_tentativa for tentativa in tentativas] == [1, 2]


def test_listar_tentativas_sem_nenhuma_registrada_devolve_tupla_vazia(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    sincronizacao = _criar_sincronizacao(caminho)

    assert RepositorioTentativasColeta(caminho).listar_tentativas(sincronizacao.id) == ()  # type: ignore[attr-defined]


def test_registrar_cenario_sintetico_ativado_persiste_a_ativacao(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    sincronizacao = _criar_sincronizacao(caminho)

    RepositorioCenariosSinteticosAtivados(caminho).registrar(
        sincronizacao.id, "granizo-demonstrativo"  # type: ignore[attr-defined]
    )

    with abrir_conexao(caminho) as conexao:
        linha = conexao.execute(
            "SELECT sincronizacao_id, identificador_cenario FROM cenarios_sinteticos_ativados"
        ).fetchone()
    assert linha is not None
    assert str(linha[0]) == str(sincronizacao.id)  # type: ignore[attr-defined]
    assert linha[1] == "granizo-demonstrativo"
