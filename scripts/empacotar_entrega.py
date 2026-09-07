#!/usr/bin/env python3
"""Monta o ZIP completo e sanitizado da entrega final (História 5.9).

Uso: python3 scripts/empacotar_entrega.py

O conteúdo do ZIP é exatamente o conjunto de arquivos rastreados pelo Git
(`git ls-files`), a mesma lista que já respeita o `.gitignore` do projeto —
por isso `.env`, `.venv/`, `node_modules/`, `__pycache__/`, `*.duckdb`,
`var/` e `docs/entrega/` (o próprio destino deste script) nunca são
rastreados e, portanto, nunca entram no pacote. Como defesa em profundidade,
um filtro adicional exclui qualquer caminho que corresponda a esses mesmos
padrões operacionais, mesmo que estivesse (por engano) rastreado pelo Git.

Saída: `docs/entrega/entrega.zip`.
"""

from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SAIDA_DIR = RAIZ / "docs" / "entrega"
SAIDA_ZIP = SAIDA_DIR / "entrega.zip"
NOME_PASTA_RAIZ_NO_ZIP = "central-preventiva"

PADROES_EXCLUIDOS = (
    ".env",
    ".venv/",
    "__pycache__/",
    "node_modules/",
    "var/",
    "docs/entrega/",
    ".pytest_cache/",
    ".ruff_cache/",
    ".mypy_cache/",
    ".pyright/",
    ".uv-cache/",
)
SUFIXOS_EXCLUIDOS = (".duckdb", ".duckdb.wal", ".pyc", ".pyo")


class ArquivoNaoRastreado(RuntimeError):
    """`git ls-files` não retornou nenhum arquivo — raiz não é um repositório Git."""


def _esta_excluido(caminho_relativo: str) -> bool:
    if Path(caminho_relativo).name == ".env" or caminho_relativo == ".env":
        return True
    for padrao in PADROES_EXCLUIDOS:
        prefixo = padrao.rstrip("/")
        if caminho_relativo == prefixo or caminho_relativo.startswith(prefixo + "/"):
            return True
    return any(caminho_relativo.endswith(sufixo) for sufixo in SUFIXOS_EXCLUIDOS)


def listar_arquivos_no_pacote(raiz: Path = RAIZ) -> list[str]:
    resultado = subprocess.run(
        ["git", "-C", str(raiz), "ls-files", "-z"],
        capture_output=True,
        check=True,
    )
    todos = [item for item in resultado.stdout.decode("utf-8").split("\0") if item]
    if not todos:
        raise ArquivoNaoRastreado(f"'git ls-files' não retornou arquivos em {raiz}")
    return [caminho for caminho in todos if not _esta_excluido(caminho)]


def empacotar(raiz: Path = RAIZ, destino: Path = SAIDA_ZIP) -> Path:
    arquivos = listar_arquivos_no_pacote(raiz)
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists():
        destino.unlink()
    with zipfile.ZipFile(destino, mode="w", compression=zipfile.ZIP_DEFLATED) as pacote:
        for caminho_relativo in sorted(arquivos):
            origem = raiz / caminho_relativo
            if not origem.is_file():
                continue
            pacote.write(origem, arcname=f"{NOME_PASTA_RAIZ_NO_ZIP}/{caminho_relativo}")
    return destino


def main() -> int:
    try:
        destino = empacotar()
    except ArquivoNaoRastreado as erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 1
    print(f"pacote gerado em {destino.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
