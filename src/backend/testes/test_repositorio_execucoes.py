"""Testes da guarda de execuções preventivas ativas."""

from pathlib import Path
from uuid import UUID

import pytest

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.adaptadores.persistencia.repositorio_execucoes import RepositorioExecucoes
from central_preventiva.dominio.estados_execucao import ESTADOS_TERMINAIS, EstadoExecucao

ESTADOS_NAO_TERMINAIS = [estado for estado in EstadoExecucao if estado not in ESTADOS_TERMINAIS]


def preparar_banco(tmp_path: Path) -> Path:
    """Cria o schema versionado em um arquivo temporário e devolve seu caminho."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()
    return caminho


def inserir_execucao(caminho: Path, identificador: str, estado: EstadoExecucao) -> None:
    """Insere uma execução preventiva sintética com o estado informado."""

    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO execucao_preventiva (id, estado) VALUES (?, ?)",
            [UUID(identificador), estado.value],
        )


def test_retorna_falso_com_tabela_vazia(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)

    assert RepositorioExecucoes(caminho).existe_execucao_nao_terminal() is False


@pytest.mark.parametrize("estado", ESTADOS_NAO_TERMINAIS)
def test_retorna_verdadeiro_com_execucao_em_estado_nao_terminal(
    tmp_path: Path, estado: EstadoExecucao
) -> None:
    caminho = preparar_banco(tmp_path)
    inserir_execucao(caminho, "00000000-0000-4000-8000-000000000001", estado)

    assert RepositorioExecucoes(caminho).existe_execucao_nao_terminal() is True


def test_retorna_falso_quando_todas_as_execucoes_estao_em_estado_terminal(
    tmp_path: Path,
) -> None:
    caminho = preparar_banco(tmp_path)
    for indice, estado in enumerate(sorted(ESTADOS_TERMINAIS), start=1):
        inserir_execucao(caminho, f"00000000-0000-4000-8000-00000000{indice:04d}", estado)

    assert RepositorioExecucoes(caminho).existe_execucao_nao_terminal() is False


def test_retorna_verdadeiro_com_execucao_ativa_entre_execucoes_terminais(
    tmp_path: Path,
) -> None:
    caminho = preparar_banco(tmp_path)
    inserir_execucao(
        caminho, "00000000-0000-4000-8000-000000000001", EstadoExecucao.CONCLUIDA
    )
    inserir_execucao(
        caminho, "00000000-0000-4000-8000-000000000002", EstadoExecucao.SIMULANDO
    )

    assert RepositorioExecucoes(caminho).existe_execucao_nao_terminal() is True
