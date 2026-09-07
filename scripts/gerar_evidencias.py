#!/usr/bin/env python3
"""Roda a suíte completa do projeto e organiza as evidências em docs/evidencias/.

Uso: python3 scripts/gerar_evidencias.py

Executa, nesta ordem, `uv run --directory src/backend pytest`,
`npm test --prefix src/frontend -- --run` e a suíte Playwright de `testes-e2e/`
(cenários, responsividade e acessibilidade), e escreve um relatório markdown por
arquivo de teste E2E em `docs/evidencias/`, cada um citando `file:line` dos testes
que comprovam o cenário. Termina com código de saída não-zero se qualquer suíte
falhar, mas sempre escreve os relatórios que conseguir montar a partir do que
rodou (evidência parcial, nunca silenciosa).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BACKEND = RAIZ / "src" / "backend"
FRONTEND = RAIZ / "src" / "frontend"
E2E = RAIZ / "testes-e2e"
EVIDENCIAS = RAIZ / "docs" / "evidencias"
RELATORIO_JSON = E2E / "relatorios" / "evidencias.json"

PADRAO_CABECALHO_REQUISITO = re.compile(r"E2E-\d{2}")


@dataclass
class ResultadoComando:
    nome: str
    comando: list[str]
    codigo_saida: int
    resumo: str


@dataclass
class CasoDeTeste:
    titulo: str
    arquivo: str
    linha: int
    passou: bool


@dataclass
class RelatorioCenario:
    arquivo_relativo: str
    titulo: str
    requisitos: list[str]
    contexto: str
    casos: list[CasoDeTeste] = field(default_factory=list)

    @property
    def passou(self) -> bool:
        return bool(self.casos) and all(caso.passou for caso in self.casos)


def rodar(nome: str, comando: list[str], cwd: Path) -> ResultadoComando:
    print(f"\n$ {' '.join(comando)}  (em {cwd})")
    processo = subprocess.run(comando, cwd=cwd, capture_output=True, text=True)
    saida = processo.stdout + processo.stderr
    sys.stdout.write(saida)
    ultimas_linhas = [linha for linha in saida.strip().splitlines() if linha.strip()][-5:]
    resumo = "\n".join(ultimas_linhas) or "(sem saída)"
    return ResultadoComando(nome=nome, comando=comando, codigo_saida=processo.returncode, resumo=resumo)


def rodar_backend() -> ResultadoComando:
    return rodar(
        "Backend (pytest)",
        ["uv", "run", "--directory", str(BACKEND), "pytest"],
        cwd=RAIZ,
    )


def rodar_frontend() -> ResultadoComando:
    return rodar(
        "Frontend (vitest)",
        ["npm", "test", "--prefix", str(FRONTEND), "--", "--run"],
        cwd=RAIZ,
    )


def rodar_e2e() -> ResultadoComando:
    RELATORIO_JSON.parent.mkdir(parents=True, exist_ok=True)
    env_extra = {"PLAYWRIGHT_JSON_OUTPUT_NAME": str(RELATORIO_JSON.relative_to(E2E))}
    import os

    ambiente = {**os.environ, **env_extra}
    print(f"\n$ npx playwright test --reporter=list,json  (em {E2E})")
    processo = subprocess.run(
        ["npx", "playwright", "test", "--reporter=list,json"],
        cwd=E2E,
        env=ambiente,
        capture_output=True,
        text=True,
    )
    saida = processo.stdout + processo.stderr
    sys.stdout.write(saida)
    ultimas_linhas = [linha for linha in saida.strip().splitlines() if linha.strip()][-5:]
    resumo = "\n".join(ultimas_linhas) or "(sem saída)"
    return ResultadoComando(
        nome="E2E (Playwright)",
        comando=["npx", "playwright", "test"],
        codigo_saida=processo.returncode,
        resumo=resumo,
    )


def extrair_cabecalho(caminho: Path) -> tuple[str, list[str], str]:
    """Lê o comentário `/** ... */` no topo do arquivo e devolve (título, requisitos, contexto).

    `requisitos` só considera a linha de título (ex.: "Cenário E2E-01 — ..."), nunca o corpo
    inteiro do comentário — o corpo costuma citar outros E2E-NN só para contexto (ex.:
    "mesmo caminho de E2E-06"), e isso não é um requisito que o arquivo comprove.
    """
    texto = caminho.read_text(encoding="utf-8")
    correspondencia = re.search(r"/\*\*(.*?)\*/", texto, re.S)
    if not correspondencia:
        return caminho.stem, [], ""
    corpo = correspondencia.group(1)
    linhas = [linha.strip().lstrip("*").strip() for linha in corpo.splitlines()]
    indices_com_conteudo = [indice for indice, linha in enumerate(linhas) if linha]
    if not indices_com_conteudo:
        return caminho.stem, [], ""
    indice_titulo = indices_com_conteudo[0]
    titulo = linhas[indice_titulo]
    requisitos = sorted(set(PADRAO_CABECALHO_REQUISITO.findall(titulo)))
    contexto = "\n".join(linhas[indice_titulo + 1 :]).strip("\n")
    return titulo, requisitos, contexto


def coletar_casos(suite: dict, casos_por_arquivo: dict[str, list[CasoDeTeste]]) -> None:
    for especificacao in suite.get("specs", []):
        arquivo = especificacao.get("file", suite.get("file", ""))
        caso = CasoDeTeste(
            titulo=especificacao.get("title", ""),
            arquivo=arquivo,
            linha=especificacao.get("line", 0),
            passou=bool(especificacao.get("ok", False)),
        )
        casos_por_arquivo.setdefault(arquivo, []).append(caso)
    for subsuite in suite.get("suites", []):
        coletar_casos(subsuite, casos_por_arquivo)


def montar_relatorios_e2e() -> list[RelatorioCenario]:
    casos_por_arquivo: dict[str, list[CasoDeTeste]] = {}
    if RELATORIO_JSON.exists():
        dados = json.loads(RELATORIO_JSON.read_text(encoding="utf-8"))
        for suite in dados.get("suites", []):
            coletar_casos(suite, casos_por_arquivo)

    arquivos_spec = sorted(E2E.glob("*/*.spec.ts"))
    relatorios = []
    for caminho in arquivos_spec:
        relativo = str(caminho.relative_to(E2E))
        titulo, requisitos, contexto = extrair_cabecalho(caminho)
        relatorios.append(
            RelatorioCenario(
                arquivo_relativo=relativo,
                titulo=titulo,
                requisitos=requisitos,
                contexto=contexto,
                casos=casos_por_arquivo.get(relativo, []),
            )
        )
    return relatorios


def slug(caminho_relativo: str) -> str:
    return caminho_relativo.replace("/", "-").removesuffix(".spec.ts")


def escrever_relatorio_cenario(relatorio: RelatorioCenario) -> Path:
    linhas = [
        f"# {relatorio.titulo}",
        "",
        f"**Arquivo de teste**: `testes-e2e/{relatorio.arquivo_relativo}`",
        f"**Requisitos**: {', '.join(relatorio.requisitos) if relatorio.requisitos else '(nenhum identificado no cabeçalho)'}",
        f"**Status**: {'PASSOU' if relatorio.passou else 'FALHOU ou não executado'}",
        "",
        "## Casos de teste (evidência `file:line`)",
        "",
        "| Caso | Local | Resultado |",
        "| --- | --- | --- |",
    ]
    if not relatorio.casos:
        linhas.append("| _(nenhum resultado — suíte não rodou ou não encontrou o arquivo)_ | — | — |")
    for caso in relatorio.casos:
        resultado = "✅ passou" if caso.passou else "❌ falhou"
        linhas.append(f"| {caso.titulo} | `testes-e2e/{caso.arquivo}:{caso.linha}` | {resultado} |")
    linhas.append("")

    if relatorio.contexto:
        linhas.append("## Contexto do cenário")
        linhas.append("")
        linhas.append(
            "Cópia do comentário de cabeçalho do arquivo de teste — inclui desvios conhecidos, "
            "tabelas de rastreabilidade e o que a IA não pode inventar sem editar o teste."
        )
        linhas.append("")
        linhas.append(relatorio.contexto)
        linhas.append("")

    destino = EVIDENCIAS / f"{slug(relatorio.arquivo_relativo)}.md"
    destino.write_text("\n".join(linhas), encoding="utf-8")
    return destino


def escrever_indice(
    relatorios: list[RelatorioCenario],
    resultado_backend: ResultadoComando,
    resultado_frontend: ResultadoComando,
    resultado_e2e: ResultadoComando,
) -> Path:
    agora = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    linhas = [
        "# Evidências da suíte completa — História 5.8",
        "",
        f"Gerado em {agora} por `python3 scripts/gerar_evidencias.py`.",
        "",
        "## Suítes de unidade e integração",
        "",
        "| Suíte | Comando | Resultado |",
        "| --- | --- | --- |",
        f"| Backend (pytest) | `uv run --directory src/backend pytest` | {'✅ passou' if resultado_backend.codigo_saida == 0 else '❌ falhou'} |",
        f"| Frontend (vitest) | `npm test --prefix src/frontend -- --run` | {'✅ passou' if resultado_frontend.codigo_saida == 0 else '❌ falhou'} |",
        f"| E2E (Playwright, todos os projetos) | `npx playwright test` (em `testes-e2e/`) | {'✅ passou' if resultado_e2e.codigo_saida == 0 else '❌ falhou'} |",
        "",
        "Resumo da última linha de cada suíte:",
        "",
        "```",
        f"[backend]\n{resultado_backend.resumo}",
        "",
        f"[frontend]\n{resultado_frontend.resumo}",
        "",
        f"[e2e]\n{resultado_e2e.resumo}",
        "```",
        "",
        "## Cenários ponta a ponta",
        "",
        "| Relatório | Requisitos | Status |",
        "| --- | --- | --- |",
    ]
    for relatorio in relatorios:
        caminho_relativo = f"{slug(relatorio.arquivo_relativo)}.md"
        requisitos = ", ".join(relatorio.requisitos) if relatorio.requisitos else "—"
        status = "✅ passou" if relatorio.passou else "❌ falhou ou não executado"
        linhas.append(f"| [{relatorio.titulo}]({caminho_relativo}) | {requisitos} | {status} |")
    linhas.append("")

    destino = EVIDENCIAS / "README.md"
    destino.write_text("\n".join(linhas), encoding="utf-8")
    return destino


def main() -> int:
    EVIDENCIAS.mkdir(parents=True, exist_ok=True)

    resultado_backend = rodar_backend()
    resultado_frontend = rodar_frontend()
    resultado_e2e = rodar_e2e()

    relatorios = montar_relatorios_e2e()
    for relatorio in relatorios:
        destino = escrever_relatorio_cenario(relatorio)
        print(f"Relatório escrito: {destino.relative_to(RAIZ)}")

    indice = escrever_indice(relatorios, resultado_backend, resultado_frontend, resultado_e2e)
    print(f"Índice escrito: {indice.relative_to(RAIZ)}")

    codigo_final = max(
        resultado_backend.codigo_saida,
        resultado_frontend.codigo_saida,
        resultado_e2e.codigo_saida,
    )
    if codigo_final != 0:
        print("\nUma ou mais suítes falharam — evidências parciais escritas acima.", file=sys.stderr)
    else:
        print("\nTodas as suítes passaram — evidências completas em docs/evidencias/.")
    return codigo_final


if __name__ == "__main__":
    raise SystemExit(main())
