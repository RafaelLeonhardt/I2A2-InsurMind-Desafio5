# História 6.6 Validation

**Date**: 2026-09-10
**Spec**: `.specs/features/6-6-consultar-resultados-da-simulacao-e-a-linha-do-tempo/spec.md`
**Diff range**: `f22fb78^..87cf9ec` (7 commits: f22fb78, 77b5983, 17a5605, 9e478b3, c07c199, e506b7c, 87cf9ec)
**Verifier**: independent sub-agent (author ≠ verifier)
**Result**: FAIL ❌ — 6/7 requirement IDs verified, 1 grounded gap (PAINELRES-05, no test evidence)

---

## Task Completion

| Task | Status  | Notes |
| ---- | ------- | ----- |
| T1   | ✅ Done | `SuperficieDetalhe` union extended — `PerfilContexto.tsx:26-28` |
| T2   | ✅ Done | Label + button gated on `concluida` — `SuperficieExecucao.tsx:63,220,323-327` |
| T3   | ✅ Done | `App.tsx` mounts both surfaces; `EmConstrucao` fully removed |
| T4   | ✅ Done | `totalProcessado`/`totalEntregue`/`totalComFalha` — `SuperficieResultados.tsx:98-114` |
| T5   | ✅ Done | `filtrarNaoSimulaveis` + selects — `SuperficieResultados.tsx:255-265,299-356` |
| T6   | ⚠️ Partial | Drawer wiring done and tested, but the failure-reason branch (`excecao`) is never exercised by any test (see PAINELRES-05 below) |
| T7   | ✅ Done | `paraCsv`/`exportarCsv` — `SuperficieResultados.tsx:276-297` |

---

## Spec-Anchored Acceptance Criteria

| Criterion (WHEN X THEN Y) | Spec-defined outcome (per corrected Assumptions table) | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| PAINELRES-01: exibir estatísticas agregadas (gerada/processada/entregue/falha) | "processado" = soma de `totaisPorEstado`; "entregue" = `simulada_entregue`; "com falha" = `falhou_conteudo`+`falhou_integracao_ia` | `SuperficieResultados.test.tsx:251-275` — `expect(...getByText('Total processado')...).toHaveTextContent('10')` (5+1+2+1+1), `'Total entregue'→'5'`, `'Total com falha'→'2'` (independent literals, not derived-vs-derived); zero-case at `:277-298`. Reachability: `SuperficieExecucao.test.tsx:582-606` (label "Concluída — resultado disponível" + button navigates to `{tipo:'resultado-execucao',...}`), `App.test.tsx:566-589` (mounts `SuperficieResultados` with correct `execucaoId`) | ✅ PASS |
| PAINELRES-02: filtrar tabela de itens por status/canal | Filtro aplica-se só a `TabelaNaoSimulaveis` (única tabela por item) — não ao "lote inteiro" | `SuperficieResultados.test.tsx:321-331` (canal), `:333-343` (estado) — cada assertion usa `queryByText(...).not.toBeInTheDocument()` sobre o item excluído, não uma comparação tautológica | ✅ PASS |
| PAINELRES-03: soma dos itens exibidos nunca excede o total | Propriedade do filtro client-side sobre `naoSimulaveis` | `SuperficieResultados.test.tsx:345-355` — `within(tabela).getAllByRole('row')` tem comprimento exato (cabeçalho+1), literal independente; `:371-383` — interseção vazia mostra "Nenhuma mensagem corresponde ao filtro selecionado" | ✅ PASS |
| PAINELRES-04: selecionar item abre `SuperficieDetalheResultado` com dados completos | Só alcançável a partir de `TabelaNaoSimulaveis` (única tabela por item) | `SuperficieResultados.test.tsx:387-408` — clique em "Ver detalhe" abre `role="dialog"` e `expect(getDetalheResultado).toHaveBeenCalledWith(EXECUCAO_ID, 'msg-alvo')`; fechamento em `:410-432` | ✅ PASS |
| PAINELRES-05: IF falha THEN exibir motivo exatamente como persistido, sem inferir | Bloco `detalhe.excecao` (`causa`/`tentativas`/`impacto`) em `SuperficieDetalheResultado.tsx:282-294` | **Nenhuma citação encontrada.** Busca em todo `src/frontend/src/**/*.test.tsx` por `excecao:` com valor não-nulo não retornou nenhum resultado — o fixture padrão de `SuperficieDetalheResultado.test.tsx:78` usa `excecao: null` e nunca é sobrescrito; o teste de drill-down novo em `SuperficieResultados.test.tsx:387-408` também usa o mesmo mock com `excecao: null` e só confirma que o dialog abre, não que o motivo de falha é renderizado. O `Done when` do próprio T6 ("mostra o motivo exatamente como persistido... confirmado por teste de composição") promete essa evidência e ela não existe | ❌ GAP |
| PAINELRES-06: linha do tempo em ordem cronológica | Marcos do evento até a simulação, ordem cronológica geral preservada | `App.test.tsx:594-604` — clique em "Comunicações" monta `SuperficieLinhaDoTempo` (reachability, novo nesta história); comportamento de ordenação em si já coberto por teste pré-existente e não tocado por esta história, `SuperficieLinhaDoTempo.test.tsx:90-100` ("agrupa os marcos... mantendo a ordem cronológica geral entre grupos") | ✅ PASS |
| PAINELRES-07: exportar gera arquivo só com itens filtrados exibidos | CSV client-side, `Blob`+`URL.createObjectURL`, conteúdo = itens pós-filtro | `SuperficieResultados.test.tsx:476-487` (sem filtro, exporta tudo), `:489-501` (com filtro por estado, `csv` não contém o item excluído) — inspeciona `Blob.text()` real, não o clique do botão isoladamente | ✅ PASS |

**Status**: ❌ 1 gap present (PAINELRES-05) — 6/7 ACs fully covered with spec-anchored, non-tautological assertions.

---

## Discrimination Sensor

Isolated in a temporary `git worktree` at `HEAD` (87cf9ec), `node_modules` symlinked for speed, never touching the real tree. Baseline `git status --porcelain` recorded before the sensor ran and confirmed identical after cleanup.

| # | File:line | Description | Killed? |
| - | --- | --- | --- |
| 1 | `SuperficieResultados.tsx:260-264` | `filtrarNaoSimulaveis`: AND (`&&`) between canal/estado clauses flipped to OR (`\|\|`) | ✅ Killed (6 tests failed) |
| 2 | `SuperficieExecucao.tsx:220` | `mostrarResultado` guard `execucao.estado === 'concluida'` removed (always true when execução loaded) | ✅ Killed (1 test failed — "não mostra o botão... fora de concluida") |
| 3 | `SuperficieResultados.tsx:103-107` | `totalEntregue`'s filter predicate swapped to `ESTADOS_FALHA.has(item.chave)` (the falha predicate) | ✅ Killed (1 test failed — resumo estatístico) |
| 4 | `SuperficieResultados.tsx:388` | "Ver detalhe" `onClick={() => aoSelecionar(item.mensagemId)}` replaced with a no-op `() => {}` | ✅ Killed (2 tests failed — drill-down open/close) |
| 5 | `SuperficieResultados.tsx:359` | `exportarCsv(itens)` (filtered) replaced with `exportarCsv(todosItens)` (unfiltered) | ✅ Killed (1 test failed — "com um filtro por estado ativo, exporta só os itens daquele estado") |

**Sensor depth**: lightweight (5 targeted mutations, default tier)
**Result**: 5/5 killed — sensor discriminates the new logic correctly
**Isolation verified**: `git status --porcelain` before and after the sensor run match exactly (`M docs/design/prototype/package-lock.json`, pre-existing and unrelated); worktree removed with `git worktree remove --force`.

---

## CSV Export Test Methodology (explicit check)

- `URL.createObjectURL`/`URL.revokeObjectURL` are mocked with `vi.spyOn` inside a scoped `beforeEach` (`SuperficieResultados.test.tsx:461-470`), and unwound with `afterEach(() => vi.restoreAllMocks())` at `:472-474` — no leakage into other `describe` blocks.
- The assertion helper `csvExportado()` (`:455-459`) reads the actual `Blob` passed to `URL.createObjectURL` and calls `blob.text()` — the two export tests (`:476-487`, `:489-501`) assert on real CSV string content (`toContain`/`not.toContain` on the motivo text), not merely that the button was clicked or that `createObjectURL` was called.
- Verdict: methodology is sound.

---

## Code Quality

| Principle | Status |
| --- | --- |
| Minimum code | ✅ — each task touches exactly the files design.md named |
| Surgical changes | ✅ |
| No scope creep | ✅ |
| Matches patterns | ✅ — `mensagemAberta` mirrors `SuperficieRevisaoLote` (6.5); `resultado-execucao` mirrors `evento-execucao` (AD-016) |
| Spec-anchored outcome check | ⚠️ — 6/7 ACs match; PAINELRES-05 has no assertion at all (see gap) |
| Per-layer Coverage Expectation met | ⚠️ — domain logic (derived stats, filter, CSV) has 1:1 AC mapping; the one reused-component branch (`excecao`) is uncovered |
| Every test maps to a spec AC/edge case — no unclaimed tests | ✅ |
| Documented guidelines followed | `.specs/LESSONS.md` L-024 (text+icon+color distinction) — pre-existing, unmodified by this story, still holds |

---

## Edge Cases

- [x] Edge case 1 (execução ainda não concluída): `SuperficieResultados.tsx:491-496`, tested at `SuperficieResultados.test.tsx:212-226` (pre-existing test, unmodified by this story, still valid — component logic untouched)
- [x] Edge case 2 (ordenação estável): `SuperficieResultados.tsx:143-150` (`ordenarTotais`) relies on `Array.prototype.sort`, stable by ECMA-262 spec since 2019 — design.md's Risks & Concerns table explicitly registers this as evidence of the AC rather than a gap requiring a dedicated test; accepted as documented design decision, not silently passed

---

## Gate Check

- **Gate command**: `npm run test --prefix src/frontend && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`
- **Result**: 519 passed, 0 failed, 0 skipped (49 test files)
- **Lint**: 0 errors (pre-existing `react(set-state-in-effect)`/`react(only-export-components)` warnings only, none introduced by this story's new logic)
- **Build**: succeeds (`dist/` produced, 288ms)
- **Test count before feature**: 502 (519 − 17 new tests added across `PerfilContexto.test.tsx`, `SuperficieExecucao.test.tsx`, `App.test.tsx`, `SuperficieResultados.test.tsx`)
- **Test count after feature**: 519
- **Delta**: +17 new tests
- **Skipped tests**: none
- **Failures**: none

---

## Fix Plans

### Fix 1: PAINELRES-05 has no test evidence for the failure-reason rendering path

- **Root cause**: `SuperficieDetalheResultado.tsx:282-294` renders `detalhe.excecao` (causa/tentativas/impacto) only when `excecao !== null`, but every fixture across the frontend test suite (`SuperficieDetalheResultado.test.tsx:78` and the new `SuperficieResultados.test.tsx` composition mock) sets `excecao: null` and is never overridden. The component code is almost certainly correct (it is pre-existing, from before this story), but the specific behavior PAINELRES-05 requires — "motivo da falha tal como persistido, sem inferir" — has zero automated coverage, so a regression here (e.g., swapped/dropped fields, wrong wording) would not be caught.
- **Fix task**: Add one test — either in `SuperficieDetalheResultado.test.tsx` (mock `excecao: {causa: '...', tentativas: N, impacto: '...', criadoEm: '...'}` and assert the rendered text matches those exact values) or, to satisfy T6's original intent of a *composition* test, in `SuperficieResultados.test.tsx`'s drill-down `describe` block (mock `getDetalheResultado` to resolve with a non-null `excecao` and assert the drawer shows the exact `causa`/`impacto` text after opening it from `TabelaNaoSimulaveis`).
- **Priority**: Major (P1/MVP acceptance criterion with no evidence; underlying code is plausibly correct but unverified).

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
| --- | --- | --- |
| PAINELRES-01 | Implementing | ✅ Verified |
| PAINELRES-02 | Implementing | ✅ Verified |
| PAINELRES-03 | Implementing | ✅ Verified |
| PAINELRES-04 | Implementing | ✅ Verified |
| PAINELRES-05 | Implementing | ❌ Needs Fix |
| PAINELRES-06 | Implementing | ✅ Verified |
| PAINELRES-07 | Implementing | ✅ Verified |

---

## Summary

**Overall**: ⚠️ Issues

**Spec-anchored check**: 6/7 ACs matched spec outcome, 1 gap (PAINELRES-05, no evidence anywhere in the codebase)
**Sensor**: 5/5 mutations killed
**Gate**: 519 passed, 0 failed, lint 0 errors, build succeeds

**What works**: Navigation wiring (T1-T3) is fully tested and correct, including confirmed removal of `EmConstrucao` (no dangling references, no orphaned CSS/imports). Derived stats (T4), the canal/estado filter (T5), the CSV export (T7), and the drawer's open/close wiring (T6, minus the failure branch) all have precise, non-tautological, spec-anchored tests, and all 5 injected mutants covering this new logic were killed — the test suite genuinely discriminates regressions in this story's own code.

**Issues found**: PAINELRES-05 (IF item failed THEN show the exact persisted failure reason) has no test anywhere in the frontend suite exercising a non-null `excecao`. See Fix 1.

**Next steps**: Route Fix 1 to an implementer (add the missing test per Fix Plans above), then re-verify. This is a single, narrow gap — everything else in the story is solid.
