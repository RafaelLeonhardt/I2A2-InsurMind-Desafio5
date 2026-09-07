"""Testes de integração de `scripts/gerar_inventario.py` (História 5.9, T3).

Cobre a AC "inventário verificável" de `spec.md` (ENTREGA-03): checksums batem
com o conteúdo real de cada artefato, e um arquivo alterado diverge do valor
registrado até o inventário rodar de novo.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))

import gerar_inventario as modulo  # noqa: E402


@pytest.fixture
def diretorio_artefatos(tmp_path: Path) -> Path:
    diretorio = tmp_path / "entrega"
    diretorio.mkdir()
    (diretorio / "relatorio-tecnico.pdf").write_bytes(b"conteudo pdf de teste")
    (diretorio / "entrega.zip").write_bytes(b"conteudo zip de teste")
    return diretorio


def test_inventario_lista_nome_tamanho_e_checksum_de_cada_artefato(
    diretorio_artefatos: Path,
) -> None:
    inventario = modulo.montar_inventario(diretorio_artefatos, diretorio_artefatos / "inventario.json")

    nomes = {registro["nome"] for registro in inventario["artefatos"]}
    assert nomes == {"relatorio-tecnico.pdf", "entrega.zip"}
    for registro in inventario["artefatos"]:
        caminho = diretorio_artefatos / registro["nome"]
        assert registro["tamanho_bytes"] == caminho.stat().st_size
        assert registro["sha256"] == hashlib.sha256(caminho.read_bytes()).hexdigest()


def test_checksum_diverge_apos_alteracao_ate_regenerar(diretorio_artefatos: Path) -> None:
    saida = diretorio_artefatos / "inventario.json"
    modulo.gerar(diretorio_artefatos, saida)
    inventario_original = json.loads(saida.read_text(encoding="utf-8"))
    checksum_original = next(
        r["sha256"] for r in inventario_original["artefatos"] if r["nome"] == "entrega.zip"
    )

    (diretorio_artefatos / "entrega.zip").write_bytes(b"conteudo zip MODIFICADO")
    checksum_real_do_arquivo = hashlib.sha256(
        (diretorio_artefatos / "entrega.zip").read_bytes()
    ).hexdigest()

    assert checksum_real_do_arquivo != checksum_original

    modulo.gerar(diretorio_artefatos, saida)
    inventario_atualizado = json.loads(saida.read_text(encoding="utf-8"))
    checksum_atualizado = next(
        r["sha256"] for r in inventario_atualizado["artefatos"] if r["nome"] == "entrega.zip"
    )
    assert checksum_atualizado == checksum_real_do_arquivo


def test_falha_explicita_quando_diretorio_de_artefatos_esta_vazio(tmp_path: Path) -> None:
    vazio = tmp_path / "vazio"
    vazio.mkdir()
    with pytest.raises(modulo.ArtefatoAusente):
        modulo.listar_artefatos(vazio)


def test_falha_explicita_quando_diretorio_de_artefatos_nao_existe(tmp_path: Path) -> None:
    ausente = tmp_path / "nao-existe"
    with pytest.raises(modulo.ArtefatoAusente):
        modulo.listar_artefatos(ausente)


def test_inventario_nao_inclui_a_si_mesmo(diretorio_artefatos: Path) -> None:
    saida = diretorio_artefatos / "inventario.json"
    modulo.gerar(diretorio_artefatos, saida)

    inventario = json.loads(saida.read_text(encoding="utf-8"))

    assert "inventario.json" not in {r["nome"] for r in inventario["artefatos"]}
