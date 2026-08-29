"""Exporta o documento OpenAPI gerado pela aplicação real, como fonte única."""

import json
from pathlib import Path
from typing import Any

from central_preventiva.composicao.api import criar_aplicacao
from central_preventiva.composicao.configuracao import Configuracao, obter_configuracao

CAMINHO_SNAPSHOT_PADRAO = Path(__file__).resolve().parent / "openapi.json"


def gerar_documento_openapi(configuracao: Configuracao) -> dict[str, Any]:
    """Compõe a aplicação real e devolve seu documento OpenAPI sem alterações."""

    return criar_aplicacao(configuracao).openapi()


def escrever_documento_openapi(caminho: Path, documento: dict[str, Any]) -> None:
    """Grava o documento em JSON estável (chaves ordenadas) para diffs previsíveis."""

    caminho.write_text(
        json.dumps(documento, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    escrever_documento_openapi(
        CAMINHO_SNAPSHOT_PADRAO, gerar_documento_openapi(obter_configuracao())
    )
