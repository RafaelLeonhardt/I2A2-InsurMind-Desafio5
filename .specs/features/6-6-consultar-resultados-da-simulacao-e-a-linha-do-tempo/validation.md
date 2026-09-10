# História 6.6 Validation

**Date**: 2026-09-10
**Spec**: `.specs/features/6-6-consultar-resultados-da-simulacao-e-a-linha-do-tempo/spec.md`
**Diff range**: `f22fb78^..87cf9ec` (7 commits: f22fb78, 77b5983, 17a5605, 9e478b3, c07c199, e506b7c, 87cf9ec)
**Verifier**: independent sub-agent (author ≠ verifier)
**Round 1 verdict** (superseded by Round 2 below): FAIL ❌ — 6/7 requirement IDs verified, 1 grounded gap (PAINELRES-05, no test evidence)

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

---
---

# Round 2

**Date**: 2026-09-10
**Diff range**: `87cf9ec..d32c831` (1 commit: `d32c831` — "test(resultados): cover PAINELRES-05 failure-reason rendering (Verifier Fix 1)")
**Verifier**: independent sub-agent (author ≠ verifier; fresh pass, no memory of round 1's authoring)
**Scope**: narrow re-verification of Fix 1 only (PAINELRES-05). Per round 1, PAINELRES-01/02/03/04/06/07 are not re-derived — nothing in this diff touches their code, and the full gate re-run below covers regression risk.
**Result**: PASS ✅ — PAINELRES-05 gap closed, no regressions.

---

## Fix 1 Review

**Change**: New test added to `SuperficieResultados.test.tsx`'s `describe('drill-down para SuperficieDetalheResultado (PAINELRES-04/05)', ...)` block: `it('exibe o motivo da falha exatamente como persistido quando o item selecionado está em exceção (PAINELRES-05)', ...)`.

- **Independent literal fixture**: `getDetalheResultado.mockResolvedValue({...})` (`SuperficieResultados.test.tsx:449-464`) is a hand-written literal — `excecao: { causa: 'ErroIntegracaoIA: contexto mínimo indisponível', tentativas: 3, impacto: 'Nenhuma mensagem foi gerada para este destinatário.', criadoEm: '2026-09-04T12:03:00Z' }` — not derived from or copied out of the component's own rendering logic. ✅
- **Assertion matches spec-defined outcome**: asserts `[data-secao="excecao"]` `toHaveTextContent` the exact `causa`, `tentativas` (`3`), and `impacto` strings from the fixture — i.e. "exhibits the reason exactly as persisted, without inferring" (PAINELRES-05's own wording). ✅
- **Reaches the real code path**: `SuperficieResultados.tsx:545-550` mounts `SuperficieDetalheResultado` with only `execucaoId`/`mensagemId` — the component fetches its own detail via `getDetalheResultado` internally (confirmed by reading `SuperficieResultados.tsx:536-550`, no `detalhe` prop threading). The test mocks that same module (`vi.mock('../../api/detalheResultado', ...)`, hoisted at `SuperficieResultados.test.tsx:11-23`), so the real, unmodified component logic runs against the fixture — this is a genuine composition test, not a shortcut. ✅
- **Assertion targets the right DOM node**: `SuperficieDetalheResultado.tsx:282-297` renders `detalhe.excecao && (<div className="detalhe-resultado-excecao" data-secao="excecao" role="alert">...)` with `Causa:`/`Tentativas:`/`Impacto:` `<p>` lines inside — exactly the node the test queries via `document.querySelector('[data-secao="excecao"]')` and asserts `role="alert"` on. ✅

**Verdict**: the new test genuinely exercises the previously-uncovered branch. Not tautological, not shallow.

---

## Spec-Anchored Acceptance Criteria (PAINELRES-05 only — re-check)

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| PAINELRES-05: IF o item selecionado estiver em estado de falha THEN o detalhe SHALL exibir o motivo da falha tal como persistido pela API, sem inferir ou completar informação ausente | Bloco `detalhe.excecao` (`causa`/`tentativas`/`impacto`) — `SuperficieDetalheResultado.tsx:282-297` | `SuperficieResultados.test.tsx:435-486` — `getDetalheResultado.mockResolvedValue({..., excecao: {causa: 'ErroIntegracaoIA: contexto mínimo indisponível', tentativas: 3, impacto: 'Nenhuma mensagem foi gerada para este destinatário.', ...}})`; `expect(secaoExcecao).toHaveTextContent('ErroIntegracaoIA: contexto mínimo indisponível')`, `.toHaveTextContent('3')`, `.toHaveTextContent('Nenhuma mensagem foi gerada para este destinatário.')` at `:481-483` — independent literal fixture, exact-value assertions, correct DOM node | ✅ PASS |

**Status**: ✅ Gap closed. All 7/7 PAINELRES ACs now covered with spec-anchored, non-tautological assertions (01-04/06/07 unchanged from round 1, re-affirmed by the clean full-suite gate re-run below).

---

## Discrimination Sensor (Fix 1 only)

Isolated in a temporary `git worktree` at `HEAD` (`d32c831`), `node_modules` symlinked for speed, never touching the real tree. Baseline `git status --porcelain` recorded before the sensor ran (`M docs/design/prototype/package-lock.json`, pre-existing/unrelated) and confirmed identical after cleanup.

| # | File:line | Description | Killed? |
| - | --- | --- | --- |
| 1 | `SuperficieDetalheResultado.tsx:282` | `{detalhe.excecao && (...)}` → `{false && (...)}` — the failure-reason block never renders | ✅ Killed (`SuperficieResultados.test.tsx` PAINELRES-05 test failed: `expected null not to be null`) |
| 2 | `SuperficieDetalheResultado.tsx:288` | `<strong>Causa:</strong> {detalhe.excecao.causa}` → `{detalhe.excecao.impacto}` (field swap — wrong value renders under the "Causa" label) | ✅ Killed (PAINELRES-05 test failed: expected text `ErroIntegracaoIA: contexto mínimo indisponível`, received `Exceção técnica registrada.Causa: Nenhuma mensagem foi gerada...`) |

**Sensor depth**: lightweight (2 targeted mutations, scoped to the Fix 1 diff — round 1's 5 mutations covering the rest of the story's logic are not re-run per the Verifier brief; nothing in this diff touches that code)
**Result**: 2/2 killed — the new test discriminates both a "block never renders" fault and a "wrong field under the right label" fault
**Isolation verified**: `git status --porcelain` before sensor setup and after `git worktree remove --force` match exactly.

---

## Gate Check

- **Gate command**: `npm run test --prefix src/frontend && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`
- **Result**: 520 passed, 0 failed, 0 skipped (49 test files)
- **Lint**: 0 errors (same pre-existing `react(set-state-in-effect)`/`react(only-export-components)` warnings as round 1, none introduced by Fix 1)
- **Build**: succeeds (`dist/` produced, 254ms)
- **Test count before this fix**: 519
- **Test count after this fix**: 520
- **Delta**: +1 new test (the PAINELRES-05 composition test)
- **Skipped tests**: none
- **Failures**: none
- **Regression check**: no other test's assertions were weakened or removed; diff to round-1 baseline is additive only (`git show --stat d32c831` — 1 file changed in `src/frontend`, 52 insertions, 0 deletions in the test file)

---

## Requirement Traceability Update

| Requirement | Round 1 Status | Round 2 Status |
| --- | --- | --- |
| PAINELRES-01 | ✅ Verified | ✅ Verified (unchanged) |
| PAINELRES-02 | ✅ Verified | ✅ Verified (unchanged) |
| PAINELRES-03 | ✅ Verified | ✅ Verified (unchanged) |
| PAINELRES-04 | ✅ Verified | ✅ Verified (unchanged) |
| PAINELRES-05 | ❌ Needs Fix | ✅ Verified |
| PAINELRES-06 | ✅ Verified | ✅ Verified (unchanged) |
| PAINELRES-07 | ✅ Verified | ✅ Verified (unchanged) |

`spec.md`'s traceability table and Coverage line updated to reflect PAINELRES-05 ✅ Verified and the round-2 PASS (matching the closing convention used by História 6.5's `spec.md`).

---

## Lessons

L-098 ("When a task reuses a pre-existing component's conditional branch (IF failure/error state) to satisfy an AC, add a test that actually drives that branch non-null...") was recorded as a `candidate` in round 1, grounded in this same PAINELRES-05 gap. Per `lessons.py`'s actual promotion mechanics (`references/lessons.md`, `scripts/lessons.py::cmd_add`), a candidate is promoted to `confirmed` only when the *same normalized lesson text* recurs across `promote_threshold` (2) **distinct features** — not when the originating feature's own gap is later fixed. Re-running `lessons.py add --feature 6-6-...` for this same feature would not increment `recurrence` (the feature is already in the lesson's `features` list) and would not promote it; fabricating a second feature name to force promotion would be dishonest bookkeeping. **L-098 is therefore correctly left as-is (`candidate`, recurrence 1, feature `6-6-...`)** — no `lessons.py` mutation was made. It will promote automatically, on its own evidence, if the same gap pattern is grounded in a second feature's validation. Round 2 itself is a clean PASS with no new surviving mutants, spec-precision gaps, or deviations, so per `lessons.md`'s "write nothing on clean PASS" rule, no new lesson was recorded for round 2.

---

## Summary (Round 2)

**Overall**: ✅ Ready

**Spec-anchored check**: 7/7 ACs matched spec outcome (6 unchanged from round 1 + PAINELRES-05 now closed)
**Sensor**: 2/2 Fix-1-scoped mutations killed (round 1's 5/5 for the rest of the story stand unchanged)
**Gate**: 520 passed, 0 failed, lint 0 errors, build succeeds

**What works**: The new composition test in `SuperficieResultados.test.tsx` opens the drawer for an item with a non-null `excecao` via the real `getDetalheResultado` fetch path (not a prop shortcut), and asserts the exact persisted `causa`/`tentativas`/`impacto` render inside the correct `[data-secao="excecao"][role="alert"]` node. Both a "block never renders" mutant and a "wrong field under the right label" mutant were killed by this single test, run in an isolated `git worktree` — the real tree's `git status --porcelain` was confirmed unchanged before and after.

**Issues found**: None. História 6.6 is fully verified — 7/7 PAINELRES requirements covered with spec-anchored, non-tautological, discrimination-tested evidence.

**Next steps**: None required. Feature is done. (Separately: L-098 remains a `candidate` lesson per the script's cross-feature promotion rule — see Lessons section above; no action needed unless/until a second feature grounds the same pattern.)
