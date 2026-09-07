"""Testes de integração de `scripts/empacotar_entrega.py` (História 5.9, T2).

Cobre a AC "ZIP completo e sanitizado" de `spec.md` (ENTREGA-02): o ZIP extraído
nunca contém `.env`, chave, cache ou artefato operacional, e contém `src/`,
`docs/` (incluindo `docs/evidencias/`), `README.md` e `LICENSE`.
"""

from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))

import empacotar_entrega as modulo  # noqa: E402

PADROES_PROIBIDOS = (
    ".venv",
    "__pycache__",
    "node_modules",
    "/var/",
    ".pytest_cache",
    ".ruff_cache",
)
SUFIXOS_PROIBIDOS = (".duckdb", ".duckdb.wal", ".pyc")


@pytest.fixture(scope="module")
def zip_gerado(tmp_path_factory: pytest.TempPathFactory) -> zipfile.ZipFile:
    destino = tmp_path_factory.mktemp("pacote") / "entrega.zip"
    modulo.empacotar(raiz=RAIZ, destino=destino)
    return zipfile.ZipFile(destino)


def test_zip_nao_contem_env_real(zip_gerado: zipfile.ZipFile) -> None:
    nomes = zip_gerado.namelist()
    assert not [n for n in nomes if n.rsplit("/", 1)[-1] == ".env"]


@pytest.mark.parametrize("padrao", PADROES_PROIBIDOS)
def test_zip_nao_contem_padrao_operacional(zip_gerado: zipfile.ZipFile, padrao: str) -> None:
    nomes = zip_gerado.namelist()
    assert not [n for n in nomes if padrao in n]


@pytest.mark.parametrize("sufixo", SUFIXOS_PROIBIDOS)
def test_zip_nao_contem_sufixo_operacional(zip_gerado: zipfile.ZipFile, sufixo: str) -> None:
    nomes = zip_gerado.namelist()
    assert not [n for n in nomes if n.endswith(sufixo)]


def test_zip_nao_se_contem_a_si_mesmo(zip_gerado: zipfile.ZipFile) -> None:
    nomes = zip_gerado.namelist()
    assert not [n for n in nomes if n.endswith("entrega.zip")]


@pytest.mark.parametrize(
    "caminho_esperado",
    [
        "README.md",
        "LICENSE",
        "docs/evidencias/README.md",
        "src/backend/pyproject.toml",
        "src/frontend/package.json",
    ],
)
def test_zip_contem_arquivo_essencial(zip_gerado: zipfile.ZipFile, caminho_esperado: str) -> None:
    nomes = zip_gerado.namelist()
    alvo = f"{modulo.NOME_PASTA_RAIZ_NO_ZIP}/{caminho_esperado}"
    assert alvo in nomes


def test_falha_explicita_quando_raiz_nao_e_repositorio_git(tmp_path: Path) -> None:
    (tmp_path / "arquivo.txt").write_text("conteudo", encoding="utf-8")
    with pytest.raises((modulo.ArquivoNaoRastreado, subprocess.CalledProcessError)):
        modulo.listar_arquivos_no_pacote(raiz=tmp_path)


def test_lista_exclui_arquivo_gitignorado(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t.com", "-c", "user.name=t"],
        cwd=tmp_path,
        check=False,
    )
    (tmp_path / ".gitignore").write_text("var/\n*.duckdb\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("readme", encoding="utf-8")
    (tmp_path / "var").mkdir()
    (tmp_path / "var" / "banco.duckdb").write_text("dados", encoding="utf-8")
    subprocess.run(["git", "add", "README.md", ".gitignore"], cwd=tmp_path, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.email=t@t.com",
            "-c",
            "user.name=t",
            "commit",
            "-q",
            "-m",
            "inicial",
        ],
        cwd=tmp_path,
        check=True,
    )

    arquivos = modulo.listar_arquivos_no_pacote(raiz=tmp_path)

    assert "README.md" in arquivos
    assert not [a for a in arquivos if a.startswith("var/")]


def test_regenerar_sobrescreve_de_forma_limpa(tmp_path: Path) -> None:
    destino = tmp_path / "entrega.zip"
    destino.write_bytes(b"zip antigo invalido")

    modulo.empacotar(raiz=RAIZ, destino=destino)

    with zipfile.ZipFile(destino) as pacote:
        assert pacote.testzip() is None
        assert len(pacote.namelist()) > 1
