"""Testes do `RepositorioExecucaoPreventiva`: criação, leitura e transição otimista (AD-008)."""

from pathlib import Path

import pytest

from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.adaptadores.persistencia.repositorio_execucao_preventiva import (
    ConflitoVersao,
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
