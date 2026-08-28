"""Testes do helper de conexão explícita ao DuckDB."""

from pathlib import Path

import duckdb
import pytest

from central_preventiva.adaptadores.persistencia import conexao as modulo_conexao
from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao


def test_alteracao_persiste_apos_fechar_e_reabrir(tmp_path: Path) -> None:
    caminho = tmp_path / "central_preventiva.duckdb"

    with abrir_conexao(caminho) as conexao:
        conexao.execute("CREATE TABLE exemplo (valor INTEGER)")
        conexao.execute("INSERT INTO exemplo VALUES (7)")

    with abrir_conexao(caminho) as reaberta:
        assert reaberta.execute("SELECT valor FROM exemplo").fetchall() == [(7,)]


def test_cria_o_diretorio_do_arquivo_quando_ausente(tmp_path: Path) -> None:
    caminho = tmp_path / "var" / "central_preventiva.duckdb"

    with abrir_conexao(caminho) as conexao:
        conexao.execute("CREATE TABLE exemplo (valor INTEGER)")

    assert caminho.exists()


def test_fecha_a_conexao_mesmo_quando_o_bloco_falha(tmp_path: Path) -> None:
    caminho = tmp_path / "central_preventiva.duckdb"
    capturada: list[duckdb.DuckDBPyConnection] = []

    with pytest.raises(ValueError, match="falha simulada"), abrir_conexao(caminho) as conexao:
        capturada.append(conexao)
        raise ValueError("falha simulada")

    with pytest.raises(duckdb.ConnectionException):
        capturada[0].execute("SELECT 1")


def test_cada_chamada_abre_uma_conexao_propria(tmp_path: Path) -> None:
    caminho = tmp_path / "central_preventiva.duckdb"

    with abrir_conexao(caminho) as primeira:
        pass
    with abrir_conexao(caminho) as segunda:
        assert segunda is not primeira

    assert not [
        nome
        for nome, valor in vars(modulo_conexao).items()
        if isinstance(valor, duckdb.DuckDBPyConnection)
    ]
