"""Testes de integração de `scripts/gerar_relatorio_tecnico.py` (História 5.9, T1).

Cobre a AC "relatório técnico verificável" de `spec.md` (ENTREGA-01): o PDF gerado
contém as seções exigidas com conteúdo real (não só o cabeçalho), o exemplo de
mensagem citado é o texto canônico literal (não inventado pelo extrator), e uma
evidência ausente faz o script falhar explicitamente — sem escrever nenhuma
saída — em vez de gerar um PDF com lacuna silenciosa.

Cada marcador de conteúdo abaixo é lido diretamente do arquivo-fonte (ou
hardcoded como literal independente), nunca através das funções `montar_*` do
próprio módulo — comparar contra a mesma função que produz o conteúdo não
provaria nada (ver História 5.9, achado do Verifier: M3/M4/M5).
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

# Literal canônico do dublê de E2E (`testes-e2e/suporte/servidor-dubles.ts`),
# copiado aqui como valor independente — nunca obtido via
# `modulo._extrair_conteudo_duble()` — para que o teste continue discriminando
# se o extrator um dia devolver texto inventado.
WHATSAPP_CANONICO = (
    "Chuva forte prevista na sua regiao nas proximas horas. Evite areas alagadas, "
    "recolha objetos soltos e mantenha documentos em local alto. Comunicacao preventiva."
)
SMS_CANONICO = "Chuva forte prevista hoje. Evite areas alagadas. Comunicacao preventiva."


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
    texto = "\n".join(pagina.extract_text() for pagina in leitor.pages)
    return _normalizar_espacos(texto)


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


def _ler_bruto(caminho: Path) -> str:
    """Leitura direta do arquivo-fonte, sem passar por nenhuma função `montar_*`
    do módulo sob teste — a fonte da verdade do marcador de conteúdo."""
    return caminho.read_text(encoding="utf-8")


def test_secao_arquitetura_contem_titulo_de_adr_real(relatorio_pdf: str) -> None:
    indice_adr = _ler_bruto(modulo.ADR_README)
    assert "Uso de DuckDB como banco de dados" in indice_adr  # sanidade da fonte
    assert "Uso de DuckDB como banco de dados" in relatorio_pdf


def test_secao_arquitetura_contem_prosa_real_do_readme_e_do_design(relatorio_pdf: str) -> None:
    # Fecha o spec-precision gap do Verifier (M10, rodada 2): a seção não pode
    # se sustentar só nas linhas de ADR — a prosa introdutória do README.md e
    # do docs/design/README.md também precisa chegar ao corpo do relatório.
    marcador_readme = "transformar a comunicação entre seguradoras e segurados"
    marcador_design = "prova de conceito para comunicação proativa com segurados"
    texto_readme = _ler_bruto(modulo.README_MD)
    texto_design = _ler_bruto(modulo.DESIGN_README)
    assert marcador_readme in texto_readme  # sanidade da fonte
    assert marcador_design in texto_design  # sanidade da fonte
    assert marcador_readme in relatorio_pdf
    assert marcador_design in relatorio_pdf


def test_secao_agentes_contem_titulo_real_do_adr_0012(relatorio_pdf: str) -> None:
    adr_0012 = modulo.DOCS / "adr" / "0012-adocao-de-langchain-e-langgraph-para-agentes.md"
    titulo = _ler_bruto(adr_0012).splitlines()[0].lstrip("# ").strip()
    assert titulo  # sanidade: o título não é vazio
    assert titulo in relatorio_pdf


def test_secao_tecnologias_contem_dependencia_real_do_backend(relatorio_pdf: str) -> None:
    texto_pyproject = _ler_bruto(modulo.BACKEND_PYPROJECT)
    assert '"duckdb>=1.4.4,<2"' in texto_pyproject  # sanidade da fonte
    assert "duckdb>=1.4.4,<2" in relatorio_pdf


def test_secao_fluxo_contem_primeiro_passo_real_do_readme(relatorio_pdf: str) -> None:
    marcador = "Coleta de dados em uma fonte pública de informações meteorológicas"
    texto_readme = _ler_bruto(modulo.README_MD)
    assert marcador in texto_readme  # sanidade da fonte
    assert marcador in relatorio_pdf


def test_secao_decisoes_contem_texto_real_da_ad_001(relatorio_pdf: str) -> None:
    marcador = "DuckDB schema evolves through numbered"
    texto_state = _ler_bruto(modulo.STATE_MD)
    assert marcador in texto_state  # sanidade da fonte
    assert marcador in relatorio_pdf


def test_secao_limitacoes_contem_item_real_do_handoff(relatorio_pdf: str) -> None:
    marcador = "Superfícies órfãs do perfil"
    texto_state = _ler_bruto(modulo.STATE_MD)
    assert marcador in texto_state  # sanidade da fonte
    assert marcador in relatorio_pdf


def test_secao_evidencias_contem_cenario_real_de_5_8(relatorio_pdf: str) -> None:
    marcador = "chuva intensa residencial"
    texto_indice = _ler_bruto(modulo.EVIDENCIAS_DIR / "README.md")
    assert marcador in texto_indice  # sanidade da fonte
    assert marcador in relatorio_pdf


def test_secao_mensagens_contem_o_texto_canonico_literal_do_duble(relatorio_pdf: str) -> None:
    # Comparação contra literais independentes copiados do dublê de E2E, nunca
    # contra `modulo._extrair_conteudo_duble()` — do contrário o teste passaria
    # mesmo que o extrator devolvesse conteúdo inventado.
    assert WHATSAPP_CANONICO in relatorio_pdf
    assert SMS_CANONICO in relatorio_pdf


def test_extrator_de_mensagem_bate_com_o_literal_canonico() -> None:
    # Trava adicional: se o dublê de E2E mudar o texto canônico, este teste
    # aponta exatamente onde atualizar os literais acima.
    conteudo, _ = modulo._extrair_conteudo_duble()
    assert conteudo["whatsapp"] == WHATSAPP_CANONICO
    assert conteudo["sms"] == SMS_CANONICO


def test_ler_falha_explicita_com_mensagem_precisa_quando_arquivo_ausente(
    tmp_path: Path,
) -> None:
    caminho_inexistente = tmp_path / "arquivo-que-nao-existe.md"
    with pytest.raises(
        modulo.EvidenciaAusente,
        match=r"evidência ausente: .*arquivo-que-nao-existe\.md não encontrado",
    ):
        modulo._ler(caminho_inexistente)


@pytest.mark.parametrize(
    "atributo",
    [
        "README_MD",
        "ADR_README",
        "DESIGN_README",
        "STATE_MD",
        "DUBLES_TS",
        "BACKEND_PYPROJECT",
        "FRONTEND_PACKAGE_JSON",
        "E2E_PACKAGE_JSON",
    ],
)
def test_gerar_nao_escreve_saida_quando_artefato_citado_esta_ausente(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, atributo: str
) -> None:
    caminho_inexistente = tmp_path / f"{atributo}-nao-existe.md"
    monkeypatch.setattr(modulo, atributo, caminho_inexistente)
    saida_md = tmp_path / f"saida-{atributo}.md"
    saida_pdf = tmp_path / f"saida-{atributo}.pdf"

    with pytest.raises(modulo.EvidenciaAusente):
        modulo.gerar(saida_md=saida_md, saida_pdf=saida_pdf)

    assert not saida_md.exists()
    assert not saida_pdf.exists()


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
