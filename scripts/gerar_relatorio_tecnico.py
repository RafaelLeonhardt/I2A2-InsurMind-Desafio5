#!/usr/bin/env python3
"""Monta o relatório técnico da entrega final (História 5.9) e converte-o em PDF.

Uso: python3 scripts/gerar_relatorio_tecnico.py

O conteúdo é montado só a partir de artefatos já versionados: `README.md`,
`docs/adr/`, `docs/design/`, `.specs/STATE.md`, `docs/evidencias/` (História 5.8),
os manifestos de dependência do backend/frontend e a constante de mensagens
sanitizadas do dublê de E2E (`testes-e2e/suporte/servidor-dubles.ts`). Nenhum
conteúdo é inventado — se um artefato citado estiver ausente, o script falha
explicitamente (saída não-zero, nenhum PDF é escrito), nunca gera um relatório
com lacuna silenciosa.

Ferramenta de conversão Markdown→PDF: `fpdf2` (dependência declarada em
`pyproject.toml`, raiz do repositório). Escolhida por ser pura em Python, sem
binário externo (pandoc, wkhtmltopdf) nem biblioteca de sistema (weasyprint
exige Cairo/Pango) — nenhum dos dois está disponível neste ambiente de build,
verificado no momento da implementação da História 5.9.

Saída: `docs/entrega/relatorio-tecnico.md` e `docs/entrega/relatorio-tecnico.pdf`.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from fpdf import FPDF

RAIZ = Path(__file__).resolve().parent.parent
DOCS = RAIZ / "docs"
EVIDENCIAS_DIR = DOCS / "evidencias"
ADR_README = DOCS / "adr" / "README.md"
DESIGN_README = DOCS / "design" / "README.md"
STATE_MD = RAIZ / ".specs" / "STATE.md"
README_MD = RAIZ / "README.md"
DUBLES_TS = RAIZ / "testes-e2e" / "suporte" / "servidor-dubles.ts"
BACKEND_PYPROJECT = RAIZ / "src" / "backend" / "pyproject.toml"
FRONTEND_PACKAGE_JSON = RAIZ / "src" / "frontend" / "package.json"
E2E_PACKAGE_JSON = RAIZ / "testes-e2e" / "package.json"

SAIDA_DIR = DOCS / "entrega"
SAIDA_MD = SAIDA_DIR / "relatorio-tecnico.md"
SAIDA_PDF = SAIDA_DIR / "relatorio-tecnico.pdf"

ADRS_ARQUITETURA = ("0004", "0005", "0006", "0008", "0009", "0010", "0013")

_MAPEAMENTO_CARACTERES = {
    "–": "-",
    "—": "-",
    "→": "->",
    "─": "-",
    "└": "+",
    "├": "+",
    "✅": "[OK]",
    "❌": "[FALHOU]",
    "⚠": "[ATENCAO]",
    "‘": "'",
    "’": "'",
    "“": '"',
    "”": '"',
    "…": "...",
    "•": "-",
}


class EvidenciaAusente(RuntimeError):
    """Uma evidência ou artefato canônico citado pelo relatório não foi encontrado."""


def _rel(caminho: Path) -> str:
    try:
        return str(caminho.relative_to(RAIZ))
    except ValueError:
        return str(caminho)


def _ler(caminho: Path) -> str:
    if not caminho.is_file():
        raise EvidenciaAusente(f"evidência ausente: {_rel(caminho)} não encontrado")
    return caminho.read_text(encoding="utf-8")


def _intro(texto: str) -> str:
    """Parágrafos entre o título (H1) e o primeiro cabeçalho H2."""
    linhas = texto.splitlines()
    fim = next((i for i, linha in enumerate(linhas) if linha.startswith("## ")), len(linhas))
    return "\n".join(linhas[1:fim]).strip()


def _secao(texto: str, origem: Path, cabecalho: str) -> str:
    """Corpo de uma seção markdown identificada por `cabecalho`, até o próximo
    cabeçalho de mesmo nível ou superior."""
    linhas = texto.splitlines()
    nivel = len(cabecalho) - len(cabecalho.lstrip("#"))
    try:
        inicio = next(i for i, linha in enumerate(linhas) if linha.strip() == cabecalho)
    except StopIteration as exc:
        raise EvidenciaAusente(
            f"seção ausente: '{cabecalho}' não encontrada em {_rel(origem)}"
        ) from exc
    fim = len(linhas)
    for i in range(inicio + 1, len(linhas)):
        linha = linhas[i]
        if linha.startswith("#"):
            nivel_linha = len(linha) - len(linha.lstrip("#"))
            if nivel_linha <= nivel:
                fim = i
                break
    return "\n".join(linhas[inicio + 1 : fim]).strip()


def montar_arquitetura() -> str:
    readme = _intro(_ler(README_MD))
    design = _intro(_ler(DESIGN_README))
    indice_adr = _ler(ADR_README)
    linhas_relevantes = [
        linha
        for linha in indice_adr.splitlines()
        if linha.startswith("|") and any(f"[{adr}]" in linha for adr in ADRS_ARQUITETURA)
    ]
    if not linhas_relevantes:
        raise EvidenciaAusente(f"nenhum ADR de arquitetura encontrado em {_rel(ADR_README)}")
    return (
        readme
        + "\n\n"
        + design
        + "\n\n**Decisões arquiteturais relevantes** (ver `docs/adr/`):\n\n"
        + "\n".join(linhas_relevantes)
    )


def montar_agentes() -> str:
    adr_0012 = DOCS / "adr" / "0012-adocao-de-langchain-e-langgraph-para-agentes.md"
    conteudo = _ler(adr_0012)
    modulos = [
        RAIZ / "src" / "backend" / "central_preventiva" / "adaptadores" / "ia" / "agente_redator.py",
        RAIZ / "src" / "backend" / "central_preventiva" / "adaptadores" / "ia" / "agente_critico.py",
        RAIZ / "src" / "backend" / "central_preventiva" / "aplicacao" / "grafos" / "geracao_mensagem.py",
    ]
    linhas_modulos = []
    for modulo in modulos:
        if not modulo.is_file():
            raise EvidenciaAusente(f"módulo de agente ausente: {_rel(modulo)}")
        total_linhas = len(modulo.read_text(encoding="utf-8").splitlines())
        linhas_modulos.append(f"- `{_rel(modulo)}` ({total_linhas} linhas)")
    return conteudo + "\n\n**Implementação verificada** (módulos existentes no momento da geração):\n\n" + "\n".join(
        linhas_modulos
    )


def _dependencias_pyproject(caminho: Path) -> list[str]:
    texto = _ler(caminho)
    match = re.search(r"dependencies\s*=\s*\[(.*?)\]", texto, re.DOTALL)
    if not match:
        raise EvidenciaAusente(f"lista de dependencies ausente em {_rel(caminho)}")
    return re.findall(r'"([^"]+)"', match.group(1))


def _dependencias_package_json(caminho: Path, chaves: set[str] | None = None) -> dict[str, str]:
    dados = json.loads(_ler(caminho))
    deps = dict(dados.get("dependencies", {}))
    dev = dados.get("devDependencies", {})
    if chaves is None:
        deps.update(dev)
    else:
        deps.update({chave: dev[chave] for chave in chaves if chave in dev})
    return deps


def montar_tecnologias() -> str:
    backend = _dependencias_pyproject(BACKEND_PYPROJECT)
    frontend = _dependencias_package_json(
        FRONTEND_PACKAGE_JSON, chaves={"typescript", "vite", "vitest"}
    )
    e2e = _dependencias_package_json(E2E_PACKAGE_JSON)
    linhas = ["**Backend** (`src/backend/pyproject.toml`):", ""]
    linhas += [f"- {dep}" for dep in backend]
    linhas += ["", "**Frontend** (`src/frontend/package.json`):", ""]
    linhas += [f"- {nome} {versao}" for nome, versao in frontend.items()]
    linhas += ["", "**Testes ponta a ponta** (`testes-e2e/package.json`):", ""]
    linhas += [f"- {nome} {versao}" for nome, versao in e2e.items()]
    return "\n".join(linhas)


def montar_fluxo() -> str:
    return _secao(_ler(README_MD), README_MD, "## Fluxo da solução")


def montar_decisoes() -> str:
    texto = _secao(_ler(STATE_MD), STATE_MD, "## Decisions")
    blocos = re.split(r"(?m)^### (?=AD-\d+)", texto)[1:]
    if not blocos:
        raise EvidenciaAusente(f"nenhuma decisão (AD-NNN) encontrada em {_rel(STATE_MD)}")
    linhas = []
    for bloco in blocos:
        titulo, _, resto = bloco.partition("\n")
        decisao = re.search(r"- \*\*Decision\*\*: (.+)", resto)
        trade_off = re.search(r"- \*\*Trade-off\*\*: (.+)", resto)
        data = re.search(r"- \*\*Date\*\*: (.+)", resto)
        if not decisao:
            raise EvidenciaAusente(f"AD-{titulo.strip()} sem campo Decision em {_rel(STATE_MD)}")
        linhas.append(f"### {titulo.strip()}")
        linhas.append(f"- **Decisão**: {decisao.group(1).strip()}")
        if trade_off:
            linhas.append(f"- **Trade-off**: {trade_off.group(1).strip()}")
        if data:
            linhas.append(f"- **Data**: {data.group(1).strip()}")
        linhas.append("")
    return "\n".join(linhas).strip()


def montar_limitacoes() -> str:
    handoff = _secao(_ler(STATE_MD), STATE_MD, "## Handoff")
    linhas = handoff.splitlines()
    inicio = next(
        (i for i, linha in enumerate(linhas) if "Known open items" in linha),
        None,
    )
    if inicio is None:
        raise EvidenciaAusente(
            f"bloco 'Known open items' ausente no Handoff de {_rel(STATE_MD)}"
        )
    itens = []
    for linha in linhas[inicio + 1 :]:
        if linha.startswith("  - "):
            itens.append("- " + linha.strip()[2:])
        elif linha.strip() == "" or linha.startswith("  "):
            continue
        else:
            break
    if not itens:
        raise EvidenciaAusente(
            f"nenhum item aberto listado sob 'Known open items' em {_rel(STATE_MD)}"
        )
    return "\n".join(itens)


def montar_evidencias() -> str:
    if not EVIDENCIAS_DIR.is_dir():
        raise EvidenciaAusente(f"diretório de evidências ausente: {_rel(EVIDENCIAS_DIR)}")
    indice = _ler(EVIDENCIAS_DIR / "README.md")
    arquivos = sorted(p for p in EVIDENCIAS_DIR.glob("*.md") if p.name != "README.md")
    if not arquivos:
        raise EvidenciaAusente(f"nenhum arquivo de evidência em {_rel(EVIDENCIAS_DIR)}")
    return indice


def _extrair_conteudo_duble() -> tuple[dict[str, str], int]:
    texto = _ler(DUBLES_TS)
    match = re.search(r"export const CONTEUDO_PADRAO_DUBLE = \{(.*?)\n\} as const", texto, re.DOTALL)
    if not match:
        raise EvidenciaAusente(
            f"CONTEUDO_PADRAO_DUBLE não encontrado em {_rel(DUBLES_TS)}"
        )
    linha_inicio = texto[: match.start()].count("\n") + 1
    corpo = match.group(1)
    resultado: dict[str, str] = {}
    for chave in ("whatsapp", "sms", "assuntoEmail", "corpoEmail"):
        campo = re.search(rf"{chave}:\s*((?:'(?:[^'\\]|\\.)*'\s*\+?\s*)+)", corpo)
        if not campo:
            raise EvidenciaAusente(
                f"campo '{chave}' ausente em CONTEUDO_PADRAO_DUBLE ({_rel(DUBLES_TS)})"
            )
        partes = re.findall(r"'((?:[^'\\]|\\.)*)'", campo.group(1))
        resultado[chave] = "".join(partes)
    return resultado, linha_inicio


def montar_exemplos_mensagens() -> str:
    conteudo, linha = _extrair_conteudo_duble()
    citacao = f"`{_rel(DUBLES_TS)}:{linha}`"
    linhas = [
        f"Conteúdo canônico usado pelos cenários ponta a ponta ({citacao}) para provar que a "
        "saída do agente redator atravessa crítica, revisão e simulação sem ser substituída "
        "por conteúdo fixo em nenhum ponto do caminho. Dados fictícios, sem identificação real.",
        "",
        f"- **WhatsApp**: {conteudo['whatsapp']}",
        f"- **SMS**: {conteudo['sms']}",
        f"- **E-mail (assunto)**: {conteudo['assuntoEmail']}",
        f"- **E-mail (corpo)**: {conteudo['corpoEmail']}",
    ]
    return "\n".join(linhas)


def montar_markdown() -> str:
    from datetime import UTC, datetime

    gerado_em = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    secoes = [
        ("# Central Preventiva — Relatório Técnico de Entrega", ""),
        ("", f"Gerado em {gerado_em} por `scripts/gerar_relatorio_tecnico.py`."),
        ("## Arquitetura implementada", montar_arquitetura()),
        ("## Agentes", montar_agentes()),
        ("## Tecnologias", montar_tecnologias()),
        ("## Fluxo da solução", montar_fluxo()),
        ("## Decisões", montar_decisoes()),
        ("## Limitações", montar_limitacoes()),
        ("## Evidências", montar_evidencias()),
        ("## Exemplos sanitizados de mensagens", montar_exemplos_mensagens()),
    ]
    partes = []
    for cabecalho, corpo in secoes:
        if cabecalho:
            partes.append(cabecalho)
        if corpo:
            partes.append(corpo)
        partes.append("")
    return "\n".join(partes).strip() + "\n"


def _quebrar_tokens_longos(texto: str, limite: int = 40) -> str:
    """Insere espaços após separadores (-, _, /, .) em tokens sem espaço mais longos
    que `limite`, para que o renderizador de PDF sempre tenha onde quebrar a linha
    (evita a exceção do fpdf2 para um token maior que a largura da página)."""

    def _quebrar(match: re.Match[str]) -> str:
        token = match.group(0)
        if len(token) <= limite:
            return token
        return re.sub(r"(?<=[-_/.])", " ", token)

    return re.sub(r"\S+", _quebrar, texto)


def _sanitizar(texto: str) -> str:
    for origem, destino in _MAPEAMENTO_CARACTERES.items():
        texto = texto.replace(origem, destino)
    texto = _quebrar_tokens_longos(texto)
    try:
        texto.encode("latin-1")
    except UnicodeEncodeError as exc:
        raise EvidenciaAusente(
            "caractere não suportado pelo gerador de PDF "
            f"(adicione um mapeamento em _MAPEAMENTO_CARACTERES): {exc}"
        ) from exc
    return texto


def _preprocessar(texto: str) -> str:
    texto = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"[Imagem: \1]", texto)
    texto = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", texto)
    return texto


def renderizar_pdf(markdown_texto: str, destino: Path) -> None:
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(18, 18, 18)
    pdf.add_page()
    dentro_bloco_codigo = False
    for linha_bruta in _preprocessar(markdown_texto).splitlines():
        linha = _sanitizar(linha_bruta)
        despojada = linha.strip()
        if despojada.startswith("```"):
            dentro_bloco_codigo = not dentro_bloco_codigo
            continue
        if dentro_bloco_codigo:
            pdf.set_font("courier", size=9)
            pdf.multi_cell(0, 5, linha or " ", new_x="LMARGIN", new_y="NEXT")
            continue
        if linha.startswith("# "):
            pdf.set_font("helvetica", style="B", size=18)
            pdf.ln(4)
            pdf.multi_cell(0, 10, linha[2:].strip(), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)
            continue
        if linha.startswith("## "):
            pdf.set_font("helvetica", style="B", size=14)
            pdf.ln(3)
            pdf.multi_cell(0, 8, linha[3:].strip(), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)
            continue
        if linha.startswith("### "):
            pdf.set_font("helvetica", style="B", size=12)
            pdf.ln(2)
            pdf.multi_cell(0, 7, linha[4:].strip(), new_x="LMARGIN", new_y="NEXT")
            continue
        if despojada.startswith("|"):
            celulas = [c.strip() for c in despojada.strip("|").split("|")]
            if all(re.fullmatch(r"-{3,}", c) for c in celulas):
                continue
            pdf.set_font("courier", size=8)
            pdf.multi_cell(0, 5, " | ".join(celulas), new_x="LMARGIN", new_y="NEXT")
            continue
        if despojada.startswith(("- ", "* ")):
            pdf.set_font("helvetica", size=10)
            pdf.multi_cell(0, 6, "  - " + despojada[2:], new_x="LMARGIN", new_y="NEXT")
            continue
        if not despojada:
            pdf.ln(2)
            continue
        pdf.set_font("helvetica", size=10)
        pdf.multi_cell(0, 6, linha, new_x="LMARGIN", new_y="NEXT")
    pdf.output(str(destino))


def gerar(saida_md: Path = SAIDA_MD, saida_pdf: Path = SAIDA_PDF) -> None:
    saida_md.parent.mkdir(parents=True, exist_ok=True)
    markdown_texto = montar_markdown()
    saida_md.write_text(markdown_texto, encoding="utf-8")
    renderizar_pdf(markdown_texto, saida_pdf)


def main() -> int:
    try:
        gerar()
    except EvidenciaAusente as erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 1
    print(f"relatório técnico gerado em {_rel(SAIDA_MD)} e {_rel(SAIDA_PDF)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
