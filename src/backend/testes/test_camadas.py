"""Testes das fronteiras arquiteturais mínimas do backend."""

import ast
from pathlib import Path


def test_dominio_nao_importa_frameworks_ou_adaptadores() -> None:
    raiz_dominio = Path("central_preventiva/dominio")
    arquivos = list(raiz_dominio.rglob("*.py"))
    assert arquivos, "O pacote de domínio deve conter ao menos um arquivo Python."

    importacoes_absolutas_proibidas = (
        "fastapi",
        "pydantic",
        "duckdb",
        "central_preventiva.aplicacao",
        "central_preventiva.adaptadores",
        "central_preventiva.composicao",
    )
    camadas_relativas_proibidas = {"aplicacao", "adaptadores", "composicao"}

    for arquivo in arquivos:
        arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
        for no in ast.walk(arvore):
            if isinstance(no, ast.Import):
                for nome in no.names:
                    assert not nome.name.startswith(importacoes_absolutas_proibidas)

            if isinstance(no, ast.ImportFrom):
                modulo = no.module or ""
                assert not modulo.startswith(importacoes_absolutas_proibidas)

                if no.level > 0:
                    raiz_relativa = modulo.split(".", maxsplit=1)[0] if modulo else ""
                    nomes_relativos = {raiz_relativa} | {nome.name for nome in no.names}
                    assert camadas_relativas_proibidas.isdisjoint(nomes_relativos)
