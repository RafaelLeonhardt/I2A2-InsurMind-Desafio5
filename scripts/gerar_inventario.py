#!/usr/bin/env python3
"""Registra nomes, tamanhos e checksums SHA-256 dos artefatos finais da entrega.

Uso: python3 scripts/gerar_inventario.py

Lê todo arquivo já presente em `docs/entrega/` (produzidos por
`gerar_relatorio_tecnico.py` e `empacotar_entrega.py`), exceto o próprio
inventário, e grava `docs/entrega/inventario.json` com nome, tamanho em bytes
e checksum SHA-256 de cada um — permitindo a qualquer avaliador conferir a
integridade do PDF, do ZIP e dos demais arquivos submetidos.

Falha explicitamente se `docs/entrega/` estiver vazio ou ausente: rodar
`gerar_relatorio_tecnico.py` e `empacotar_entrega.py` antes é pré-condição
desta etapa (Fase 2 depende da Fase 1, `tasks.md`).
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SAIDA_DIR = RAIZ / "docs" / "entrega"
SAIDA_INVENTARIO = SAIDA_DIR / "inventario.json"


class ArtefatoAusente(RuntimeError):
    """Nenhum artefato final foi encontrado para inventariar."""


def _sha256(caminho: Path) -> str:
    hasher = hashlib.sha256()
    with caminho.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(65536), b""):
            hasher.update(bloco)
    return hasher.hexdigest()


def listar_artefatos(diretorio: Path, excluir: Path | None = None) -> list[Path]:
    if not diretorio.is_dir():
        raise ArtefatoAusente(f"diretório de artefatos ausente: {diretorio}")
    arquivos = sorted(p for p in diretorio.rglob("*") if p.is_file() and p != excluir)
    if not arquivos:
        raise ArtefatoAusente(f"nenhum artefato encontrado em {diretorio}")
    return arquivos


def montar_inventario(diretorio: Path = SAIDA_DIR, saida: Path = SAIDA_INVENTARIO) -> dict:
    arquivos = listar_artefatos(diretorio, excluir=saida)
    registros = [
        {
            "nome": str(caminho.relative_to(diretorio)),
            "tamanho_bytes": caminho.stat().st_size,
            "sha256": _sha256(caminho),
        }
        for caminho in arquivos
    ]
    return {
        "gerado_em": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "artefatos": registros,
    }


def gerar(diretorio: Path = SAIDA_DIR, saida: Path = SAIDA_INVENTARIO) -> Path:
    inventario = montar_inventario(diretorio, saida)
    saida.write_text(json.dumps(inventario, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return saida


def main() -> int:
    try:
        destino = gerar()
    except ArtefatoAusente as erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 1
    print(f"inventário gerado em {destino.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
