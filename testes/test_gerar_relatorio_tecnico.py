"""Testes de integração de `scripts/gerar_relatorio_tecnico.py` (História 5.9, T1).

Cobre a AC "relatório técnico verificável" de `spec.md` (ENTREGA-01): o PDF gerado
contém as seções exigidas com conteúdo real, e uma evidência ausente faz o script
falhar explicitamente em vez de gerar um PDF com lacuna silenciosa.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest
from pypdf import PdfReader

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))

import gerar_relatorio_tecnico as modulo  # noqa: E402


def _normalizar_espacos(texto: str) -> str:
    """Colapsa quebras de linha do texto extraído do PDF, que variam conforme onde
    o `multi_cell` decidiu quebrar o parágrafo, sem alterar o conteúdo comparado."""
    return re.sub(r"\s+", " ", texto)


@pytest.fixture(scope="module")
def relatorio_pdf(tmp_path_factory: pytest.TempPathFactory) -> str:
    diretorio = tmp_path_factory.mktemp("relatorio")
    saida_md = diretorio / "relatorio-tecnico.md"
    saida_pdf = diretorio / "relatorio-tecnico.pdf"
    modulo.gerar(saida_md=saida_md, saida_pdf=saida_pdf)
    leitor = PdfReader(str(saida_pdf))
    return "\n".join(pagina.extract_text() for pagina in leitor.pages)


SECOES_OBRIGATORIAS = [
    "Arquitetura implementada",
    "Agentes",
    "Tecnologias",
    "Fluxo da solução",
    "Decisões",
    "Limitações",
    "Evidências",
    "Exemplos sanitizados de mensagens",
]


@pytest.mark.parametrize("cabecalho", SECOES_OBRIGATORIAS)
def test_pdf_contem_cada_secao_obrigatoria(relatorio_pdf: str, cabecalho: str) -> None:
    assert cabecalho in relatorio_pdf


def test_pdf_contem_arquitetura_e_tecnologia_verificaveis(relatorio_pdf: str) -> None:
    # Conteúdo verificável contra artefatos canônicos reais: um ADR citado e uma
    # dependência real do backend, não texto inventado pelo script.
    assert "DuckDB" in relatorio_pdf
    assert "fastapi" in relatorio_pdf


def test_pdf_contem_decisao_real_do_state(relatorio_pdf: str) -> None:
    assert "AD-001" in relatorio_pdf


def test_pdf_contem_exemplo_sanitizado_de_mensagem_canonico(relatorio_pdf: str) -> None:
    conteudo, _ = modulo._extrair_conteudo_duble()
    texto_normalizado = _normalizar_espacos(relatorio_pdf)
    assert conteudo["whatsapp"] in texto_normalizado
    assert conteudo["sms"] in texto_normalizado


def test_falha_explicita_quando_evidencia_esta_ausente(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    caminho_inexistente = tmp_path / "nao-existe.md"
    monkeypatch.setattr(modulo, "README_MD", caminho_inexistente)
    with pytest.raises(modulo.EvidenciaAusente):
        modulo.montar_fluxo()
    assert not caminho_inexistente.exists()


def test_falha_explicita_quando_diretorio_de_evidencias_esta_vazio(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    vazio = tmp_path / "evidencias-vazias"
    vazio.mkdir()
    monkeypatch.setattr(modulo, "EVIDENCIAS_DIR", vazio)
    with pytest.raises(modulo.EvidenciaAusente):
        modulo.montar_evidencias()


def test_regenerar_sobrescreve_de_forma_limpa(tmp_path: Path) -> None:
    saida_md = tmp_path / "relatorio-tecnico.md"
    saida_pdf = tmp_path / "relatorio-tecnico.pdf"
    saida_md.write_text("conteudo antigo que nao deve sobreviver", encoding="utf-8")
    saida_pdf.write_bytes(b"pdf antigo")

    modulo.gerar(saida_md=saida_md, saida_pdf=saida_pdf)

    texto_novo = saida_md.read_text(encoding="utf-8")
    assert "conteudo antigo que nao deve sobreviver" not in texto_novo
    assert "Central Preventiva" in texto_novo
    assert saida_pdf.read_bytes() != b"pdf antigo"
