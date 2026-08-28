"""Abertura explícita e de curta duração de conexões ao DuckDB."""

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

import duckdb


@contextmanager
def abrir_conexao(caminho: Path) -> Generator[duckdb.DuckDBPyConnection]:
    """Abre uma conexão exclusiva ao arquivo indicado e a fecha ao sair do bloco."""

    caminho.parent.mkdir(parents=True, exist_ok=True)
    conexao = duckdb.connect(str(caminho))
    try:
        yield conexao
    finally:
        conexao.close()
