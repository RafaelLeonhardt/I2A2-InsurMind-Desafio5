"""Testes do `RepositorioExecucaoPreventiva`: criação, leitura e transição otimista (AD-008)."""

from pathlib import Path

import pytest

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.adaptadores.persistencia.repositorio_execucao_preventiva import (
    ConflitoVersao,
    RepositorioExcecoesOperacionais,
    RepositorioExecucaoPreventiva,
    TransicaoInvalida,
)
from central_preventiva.dominio.estados_execucao import EstadoExecucao


def preparar_banco(tmp_path: Path) -> Path:
    """Aplica as migrações versionadas em um arquivo temporário."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()
    return caminho


def test_criar_insere_com_versao_1_e_o_estado_inicial_informado(tmp_path: Path) -> None:
    repositorio = RepositorioExecucaoPreventiva(preparar_banco(tmp_path))

    execucao_id = repositorio.criar(EstadoExecucao.COLETANDO)
    snapshot = repositorio.obter(execucao_id)

    assert snapshot.id == execucao_id
    assert snapshot.estado == EstadoExecucao.COLETANDO
    assert snapshot.versao == 1


def test_transicionar_com_versao_esperada_correta_atualiza_estado_e_incrementa_versao(
    tmp_path: Path,
) -> None:
    repositorio = RepositorioExecucaoPreventiva(preparar_banco(tmp_path))
    execucao_id = repositorio.criar(EstadoExecucao.COLETANDO)

    repositorio.transicionar(execucao_id, versao_esperada=1, novo_estado=EstadoExecucao.SEM_RISCO)

    snapshot = repositorio.obter(execucao_id)
    assert snapshot.estado == EstadoExecucao.SEM_RISCO
    assert snapshot.versao == 2


def test_transicionar_com_versao_esperada_incorreta_levanta_conflito_sem_mutar(
    tmp_path: Path,
) -> None:
    repositorio = RepositorioExecucaoPreventiva(preparar_banco(tmp_path))
    execucao_id = repositorio.criar(EstadoExecucao.COLETANDO)

    with pytest.raises(ConflitoVersao):
        repositorio.transicionar(
            execucao_id, versao_esperada=99, novo_estado=EstadoExecucao.SEM_RISCO
        )

    snapshot = repositorio.obter(execucao_id)
    assert snapshot.estado == EstadoExecucao.COLETANDO
    assert snapshot.versao == 1


def test_transicionar_a_partir_de_estado_terminal_levanta_transicao_invalida(
    tmp_path: Path,
) -> None:
    repositorio = RepositorioExecucaoPreventiva(preparar_banco(tmp_path))
    execucao_id = repositorio.criar(EstadoExecucao.FALHOU_COLETA)

    with pytest.raises(TransicaoInvalida):
        repositorio.transicionar(
            execucao_id, versao_esperada=1, novo_estado=EstadoExecucao.SEM_RISCO
        )

    snapshot = repositorio.obter(execucao_id)
    assert snapshot.estado == EstadoExecucao.FALHOU_COLETA
    assert snapshot.versao == 1


def test_registrar_excecao_operacional_persiste_causa_tentativas_e_impacto(
    tmp_path: Path,
) -> None:
    caminho = preparar_banco(tmp_path)
    execucao_id = RepositorioExecucaoPreventiva(caminho).criar(EstadoExecucao.FALHOU_COLETA)

    RepositorioExcecoesOperacionais(caminho).registrar(
        execucao_id,
        causa="TimeoutException: timeout",
        tentativas=3,
        impacto="Coleta meteorológica indisponível.",
    )

    with abrir_conexao(caminho) as conexao:
        linha = conexao.execute(
            "SELECT execucao_id, causa, tentativas, impacto FROM excecoes_operacionais"
        ).fetchone()
    assert linha is not None
    assert str(linha[0]) == str(execucao_id)
    assert linha[1] == "TimeoutException: timeout"
    assert linha[2] == 3
    assert linha[3] == "Coleta meteorológica indisponível."


def test_listar_nao_terminais_exclui_estados_terminais(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    repositorio = RepositorioExecucaoPreventiva(caminho)

    id_coletando = repositorio.criar(EstadoExecucao.COLETANDO)
    id_avaliando = repositorio.criar(EstadoExecucao.AVALIANDO_ELEGIBILIDADE)
    id_aguardando = repositorio.criar(EstadoExecucao.AGUARDANDO_GERACAO)
    id_sem_risco = repositorio.criar(EstadoExecucao.SEM_RISCO)
    id_sem_elegiveis = repositorio.criar(EstadoExecucao.SEM_ELEGIVEIS)
    id_falhou = repositorio.criar(EstadoExecucao.FALHOU_COLETA)

    nao_terminais = set(repositorio.listar_nao_terminais())

    assert {id_coletando, id_avaliando, id_aguardando} <= nao_terminais
    assert id_sem_risco not in nao_terminais
    assert id_sem_elegiveis not in nao_terminais
    assert id_falhou not in nao_terminais


def test_registrar_marco_persiste_causa_opcional_e_correlaciona_por_execucao(
    tmp_path: Path,
) -> None:
    caminho = preparar_banco(tmp_path)
    repositorio = RepositorioExecucaoPreventiva(caminho)
    execucao_id = repositorio.criar(EstadoExecucao.COLETANDO)

    repositorio.registrar_marco(execucao_id, "coleta_concluida")
    repositorio.registrar_marco(
        execucao_id, "falhou_processamento", causa="ValueError: motivo sintético"
    )

    marcos = repositorio.listar_marcos(execucao_id)

    assert [m.marco for m in marcos] == ["coleta_concluida", "falhou_processamento"]
    assert marcos[0].causa is None
    assert marcos[1].causa == "ValueError: motivo sintético"


def test_listar_marcos_de_execucao_sem_nenhum_marco_devolve_lista_vazia(
    tmp_path: Path,
) -> None:
    caminho = preparar_banco(tmp_path)
    repositorio = RepositorioExecucaoPreventiva(caminho)
    execucao_id = repositorio.criar(EstadoExecucao.COLETANDO)

    assert repositorio.listar_marcos(execucao_id) == []
