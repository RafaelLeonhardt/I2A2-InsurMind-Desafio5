"""Testes de integração de `scripts/empacotar_entrega.py` (História 5.9, T2).

Cobre a AC "ZIP completo e sanitizado" de `spec.md` (ENTREGA-02): o ZIP extraído
nunca contém `.env`, chave, cache ou artefato operacional, e contém `src/`,
`docs/` (incluindo `docs/evidencias/`), `README.md` e `LICENSE`. Também cobre
ENTREGA-03 (repositório com licença MIT e livre de segredos conhecidos), cujo
Independent Test em `spec.md` é literalmente uma busca automatizada no
conteúdo extraído — não só nos nomes de caminho.
"""

from __future__ import annotations

import re
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

PADROES_DE_CHAVE_CONHECIDA = (
    re.compile(rb"sk-[A-Za-z0-9]{20,}"),
    re.compile(rb"AKIA[0-9A-Z]{16}"),
    re.compile(rb"gh[pousr]_[A-Za-z0-9]{36,}"),
    re.compile(rb"xox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(rb"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)


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


def test_zip_licenca_e_mit(zip_gerado: zipfile.ZipFile) -> None:
    conteudo = zip_gerado.read(f"{modulo.NOME_PASTA_RAIZ_NO_ZIP}/LICENSE").decode("utf-8")
    assert conteudo.startswith("MIT License")


def test_zip_nao_contem_nenhum_padrao_de_chave_conhecida(zip_gerado: zipfile.ZipFile) -> None:
    for nome in zip_gerado.namelist():
        dados = zip_gerado.read(nome)
        for padrao in PADROES_DE_CHAVE_CONHECIDA:
            assert not padrao.search(dados), f"padrão de chave encontrado em {nome}"


@pytest.mark.parametrize(
    ("caminho", "esperado"),
    [
        (".env", True),
        ("sub/.env", True),
        (".venv/lib/x.py", True),
        ("sub/.venv/lib/x.py", True),
        ("__pycache__/x.pyc", True),
        ("node_modules/pkg/index.js", True),
        ("var/central_preventiva.duckdb", True),
        ("docs/entrega/relatorio-tecnico.pdf", True),
        (".pytest_cache/v/x", True),
        ("banco.duckdb", True),
        ("banco.duckdb.wal", True),
        ("modulo.pyc", True),
        ("src/backend/central_preventiva/main.py", False),
        (".env.example", False),
        ("README.md", False),
    ],
)
def test_esta_excluido_reconhece_cada_padrao_da_lista(caminho: str, esperado: bool) -> None:
    assert modulo._esta_excluido(caminho) is esperado


def test_filtro_defensivo_remove_env_mesmo_se_rastreado_pelo_git(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / "README.md").write_text("readme", encoding="utf-8")
    (tmp_path / ".env").write_text("SEGREDO=1", encoding="utf-8")
    # `-f` força o rastreamento mesmo que um `.gitignore` existisse: prova que
    # é o filtro defensivo de `_esta_excluido`, não o `.gitignore`, que remove
    # o arquivo da lista final.
    subprocess.run(["git", "add", "-f", "README.md", ".env"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t.com", "-c", "user.name=t", "commit", "-q", "-m", "inicial"],
        cwd=tmp_path,
        check=True,
    )

    arquivos = modulo.listar_arquivos_no_pacote(raiz=tmp_path)

    assert "README.md" in arquivos
    assert ".env" not in arquivos


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
