# História 5.9: Preparar e empacotar a entrega final — Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

**Pré-condição de Execute:** esta história depende de `docs/evidencias/` (produzido pela História 5.8) já existir. A publicação (T5) é uma ação manual e separada — nunca automatizada por nenhuma task desta história — e só ocorre mediante autorização explícita do usuário no momento em que for solicitada, conforme o blast radius do processo (nunca antecipada nem presumida aqui).

---

**Design**: `.specs/features/5-9-preparar-e-empacotar-a-entrega-final/design.md`
**Status**: Approved

---

## Test Coverage Matrix

> Guidelines: `AGENTS.md`, `README.md`. Esta história produz scripts de orquestração de arquivos, não código de aplicação — a verificação é funcional (o script produz o artefato correto), não uma suíte de asserção de domínio.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| `gerar_relatorio_tecnico.py` | integration | PDF gerado contém as seções do AC; falha explícita se evidência ausente | `testes/test_gerar_relatorio_tecnico.py` | `uv run --directory . pytest testes/test_gerar_relatorio_tecnico.py` |
| `empacotar_entrega.py` | integration | ZIP não contém nenhum padrão da lista de exclusão | `testes/test_empacotar_entrega.py` | `uv run --directory . pytest testes/test_empacotar_entrega.py` |
| `gerar_inventario.py` | integration | Checksums batem com o conteúdo real dos arquivos | `testes/test_gerar_inventario.py` | `uv run --directory . pytest testes/test_gerar_inventario.py` |
| Validação de checkout limpo + ZIP | integration | Instalação/execução só com comandos do README, sem etapa oculta | roteiro manual documentado em `docs/entrega/validacao-checkout.md` | comandos do `README.md`, executados em diretório limpo |

## Gate Check Commands

| Gate Level | When to Use | Command |
| --- | --- | --- |
| Quick | Após cada script isolado | `uv run --directory . pytest testes/test_<script>.py` |
| Build (fim de fase) | Fim de fase / pacote completo | `python3 scripts/gerar_relatorio_tecnico.py && python3 scripts/empacotar_entrega.py && python3 scripts/gerar_inventario.py` |

---

## Execution Plan

### Phase 1: Relatório técnico e pacote

T1 e T2 são independentes entre si; execução em ordem T1, T2.

```
T1
T2
```

### Phase 2: Inventário e validação

```
T3 → T4
```

### Phase 3: Publicação (ação manual, mediante autorização)

```
T5
```

---

## Task Breakdown

### T1: `gerar_relatorio_tecnico.py`

**What**: Monta o relatório técnico em Markdown a partir de `docs/evidencias/` (5.8)+ADRs+design, converte a PDF; falha explícita se alguma evidência referenciada estiver ausente.
**Where**: `scripts/gerar_relatorio_tecnico.py`
**Depends on**: None
**Reuses**: `docs/evidencias/` (5.8), `docs/adr/`, `docs/design/`
**Requirement**: ENTREGA-01

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] PDF gerado contém arquitetura, agentes, tecnologias, fluxo, decisões, limitações, evidências, exemplos sanitizados
- [x] Evidência ausente (dado de teste) faz o script falhar explicitamente, sem gerar PDF com lacuna
- [x] Ferramenta de conversão Markdown→PDF escolhida e documentada (verificada no ambiente real)
- [x] Gate check passa: `uv run --directory . pytest testes/test_gerar_relatorio_tecnico.py`

**Tests**: integration
**Gate**: quick

---

### T2: `empacotar_entrega.py`

**What**: Monta o ZIP completo, excluindo `.env`, `var/`, `node_modules/`, `.venv/`, caches e demais artefatos operacionais (mesma lista do `.gitignore`).
**Where**: `scripts/empacotar_entrega.py`
**Depends on**: None
**Reuses**: `.gitignore` já existente como lista de exclusão
**Requirement**: ENTREGA-02

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] ZIP extraído não contém nenhum arquivo/padrão da lista de exclusão (testado por busca automatizada no conteúdo extraído)
- [ ] ZIP contém `src/`, `docs/` (incluindo `docs/evidencias/`), `README.md`, `LICENSE`
- [ ] Gate check passa: `uv run --directory . pytest testes/test_empacotar_entrega.py`

**Tests**: integration
**Gate**: quick

---

### T3: `gerar_inventario.py`

**What**: Registra nomes, tamanhos e checksums SHA-256 de PDF, ZIP e demais artefatos finais em `docs/entrega/inventario.json`.
**Where**: `scripts/gerar_inventario.py`
**Depends on**: T1, T2
**Reuses**: PDF de T1, ZIP de T2
**Requirement**: ENTREGA-03

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Inventário lista nome, tamanho e checksum SHA-256 de cada artefato final
- [ ] Recalcular o checksum de um arquivo alterado (dado de teste) diverge do valor registrado até `gerar_inventario.py` rodar de novo
- [ ] Gate check passa: `uv run --directory . pytest testes/test_gerar_inventario.py`

**Tests**: integration
**Gate**: quick

---

### T4: Validação de checkout limpo e ZIP

**What**: Roteiro documentado (e, quando possível, automatizado) que valida instalação/execução a partir de um `git clone` limpo e separadamente do ZIP extraído, usando só comandos do README.
**Where**: `docs/entrega/validacao-checkout.md`
**Depends on**: T3
**Reuses**: comandos já documentados no `README.md`
**Requirement**: ENTREGA-04, ENTREGA-05

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Checkout limpo instala e executa usando só os comandos do README, sem etapa manual oculta
- [ ] ZIP extraído instala e executa da mesma forma, independentemente do checkout via Git
- [ ] Nenhuma dependência de artefato operacional local (`var/central_preventiva.duckdb` preexistente, por exemplo) em nenhum dos dois caminhos
- [ ] Gate check passa: execução manual documentada do roteiro, com resultado registrado em `docs/entrega/validacao-checkout.md`

**Tests**: integration
**Gate**: build

---

### T5: Publicação autorizada (ação manual, separada)

**What**: Após autorização explícita do usuário no momento em que for solicitada, publicar o repositório preparado (comando `git`/`gh` manual, nunca script automatizado); em caso de falha, registrar erro sanitizado sem alterar `docs/entrega/`.
**Where**: nenhum arquivo de código — ação operacional documentada em `docs/entrega/publicacao.md`
**Depends on**: T4
**Reuses**: nenhum
**Requirement**: ENTREGA-06, ENTREGA-07

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Sem autorização explícita: história permanece pendente, nenhuma tentativa de publicação ocorre
- [ ] Com autorização explícita e sucesso: publicação confirmada, história pode ser marcada concluída
- [ ] Com autorização explícita e falha: artefatos locais intactos, erro sanitizado registrado em `docs/entrega/publicacao.md`, história permanece pendente

**Tests**: none — ação manual gated por aprovação humana, fora do escopo de teste automatizado
**Gate**: build

**Commit**: `docs(entrega): adicionar scripts de geracao do relatorio tecnico, pacote e inventario da entrega final`

---

## Phase Execution Map

```
Phase 1:  T1   T2
Phase 2:  T3 → T4
Phase 3:  T5
```

Grafo completo de dependências:

```
T1 → T3
T2 → T3
T3 → T4
T4 → T5
```

(T1 e T2 são independentes entre si na Fase 1.)

---

## Task Granularity Check

| Task | Scope | Status |
| --- | --- | --- |
| T1: `gerar_relatorio_tecnico.py` | 1 script | ✅ Granular |
| T2: `empacotar_entrega.py` | 1 script | ✅ Granular |
| T3: `gerar_inventario.py` | 1 script | ✅ Granular |
| T4: Validação de checkout/ZIP | 1 roteiro documentado | ✅ Granular |
| T5: Publicação autorizada | 1 ação manual documentada, sem código | ✅ Granular |

---

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| --- | --- | --- | --- |
| T1 | None | — | ✅ Match |
| T2 | None | — | ✅ Match |
| T3 | T1, T2 | T1 → T3, T2 → T3 (grafo completo) | ✅ Match |
| T4 | T3 | T3 → T4 | ✅ Match |
| T5 | T4 | T4 → T5 | ✅ Match |

**Rules confirmed**: toda dependência aponta para trás ou dentro da mesma fase.

---

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| --- | --- | --- | --- | --- |
| T1: `gerar_relatorio_tecnico.py` | Script de orquestração | integration | integration | ✅ OK |
| T2: `empacotar_entrega.py` | Script de orquestração | integration | integration | ✅ OK |
| T3: `gerar_inventario.py` | Script de orquestração | integration | integration | ✅ OK |
| T4: Validação de checkout/ZIP | Roteiro operacional | integration | integration | ✅ OK |
| T5: Publicação autorizada | Ação manual, sem código | none | none | ✅ OK — ação gated por aprovação humana explícita, nunca automatizável, consistente com a matriz |

**Rules confirmed**: `Tests: none` só em T5 (ação manual fora do escopo de automação, por design de segurança), conforme documentado no `Done when`.
