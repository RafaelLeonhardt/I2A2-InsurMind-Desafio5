# História 6.7: Monitorar a fonte meteorológica INMET — Validation

**Date**: 2026-09-09
**Spec**: `.specs/features/6-7-monitorar-a-fonte-meteorologica-inmet/spec.md`
**Diff range**: `7d299b2` (single commit: `feat(fontes): montar SuperficieFonteMeteorologica na navegação do admin`)
**Verifier**: independent sub-agent (author ≠ verifier)

---

## Task Completion

No formal `tasks.md` was produced for this feature (Medium scope, design done inline per spec.md's own Coverage note). Scope of the single commit, confirmed via `git show 7d299b2 --stat`:

| File | Status | Notes |
| ---- | ------ | ----- |
| `src/frontend/src/App.tsx` | ✅ Done | `case 'fontes-de-dados'` now returns `<SuperficieFonteMeteorologica />` instead of `<EmConstrucao />` |
| `src/frontend/src/App.test.tsx` | ✅ Done | New integration test asserts real navigation mounts the real component |
| `.specs/features/6-7-monitorar-a-fonte-meteorologica-inmet/spec.md` | ✅ Done | Traceability rows added (pre-Verifier state) |

`SuperficieFonteMeteorologica.tsx` and its test file were **not** touched by this commit (pre-existing code) but all 5 ACs depend on them, so evidence for those ACs is cited below regardless of authorship (evidence-or-zero applies to proof, not authorship).

---

## Spec-Anchored Acceptance Criteria

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| MONITORFONTE-01: WHEN o administrador abrir "Fontes de dados" THEN a interface SHALL exibir o estado atual da fonte (um dos 6) com rótulo acessível | Real navigation mounts the real component; each of the 6 states (`operacional`, `em_tentativa`, `indisponivel`, `sintetica`, `recuperada`, `degradada`) renders its Portuguese label | `src/frontend/src/App.test.tsx:484-494` — click `getByRole('button', {name:'Fontes de dados'})`, `expect(await screen.findByRole('heading', {name:'Fonte meteorológica'})).toBeInTheDocument()`; `src/frontend/src/funcionalidades/fonte-meteorologica/SuperficieFonteMeteorologica.test.tsx:225-234` (`findByText('Operacional')`), `:236-245` (`findByText('Indisponível')`), `:247-256` (`findByText('Sintética')`), `:258-277` (`findByText('Degradada')`), `:279-293` (`findByText('Recuperada')`), `:295-315` (`findByText('Em tentativa')`) | ✅ PASS |
| MONITORFONTE-02: WHILE `indisponivel`/`degradada` THEN destacar visualmente distinto de `operacional` | Distinct color + icon per state | `src/frontend/src/funcionalidades/fonte-meteorologica/SuperficieFonteMeteorologica.tsx:218-223` (badge class `estado-fonte-badge--${estadoFonte}`), `:84-91` (`IconeEstadoFonte`: `XCircleIcon` for `indisponivel`, `WarningIcon` for `degradada`, `CheckCircleIcon` for `operacional`); `SuperficieFonteMeteorologica.css:22-25` (operacional `#15803d`/`#dcfce7`), `:32-35` (degradada `#b45309`/`#fef3c7`), `:37-40` (indisponivel `#b91c1c`/`#fee2e2`); mechanism proven at `SuperficieFonteMeteorologica.test.tsx:516-527` — `container.querySelector('[data-icone="indisponivel"]')` has class `estado-fonte-badge--indisponivel` and an `svg` icon; `indisponivel` additionally gets a `role="alert"` block (`tsx:196-212`, tested `test.tsx:204-213`) and a "Dados desatualizados" note (`tsx:270-276`, tested `test.tsx:487-494`) | ✅ PASS (see note 1) |
| MONITORFONTE-03: IF evento mais recente `sintetica` THEN informar explicitamente que o dado não veio de coleta real | State badge literally reads "Sintética" when the latest event's `proveniencia` is `sintetico` | `SuperficieFonteMeteorologica.test.tsx:247-256` — `getEventos.mockResolvedValue([evento({ proveniencia: 'sintetico' })])`, `expect(await screen.findByText('Sintética')).toBeInTheDocument()` | ✅ PASS (see note 2) |
| MONITORFONTE-04: WHEN consultar histórico THEN listar cada tentativa com resultado e instante | Each sync entry shows origin, result (`Concluído`/`Falha`), and `iniciadoEm` timestamp | `SuperficieFonteMeteorologica.test.tsx:178-189` — `expect(screen.getByText(/Manual — Concluído — 2026-08-30T12:00:00\+00:00/)).toBeInTheDocument()`; `:191-202` — `expect(screen.getByText(/Automática — Falha — iniciado em 2026-08-30T13:00:00\+00:00 — motivo: campo_ausente/)).toBeInTheDocument()` | ✅ PASS |
| MONITORFONTE-05: WHEN acionar "Tentar novamente" com `indisponivel` THEN disparar nova tentativa e atualizar o estado exibido conforme resultado | Clicking the button calls the retry API with the correct sync id and triggers a re-fetch of the history (matches spec's own Independent Test: "confirmar que o histórico registra a nova tentativa") | `SuperficieFonteMeteorologica.test.tsx:317-335` — click `Solicitar nova tentativa`, `await waitFor(() => expect(solicitarNovaTentativa).toHaveBeenCalledWith('s2'))`, `await waitFor(() => expect(getSincronizacoes).toHaveBeenCalledTimes(2))` | ✅ PASS (see note 3) |

**Status**: ✅ All ACs covered (3 minor precision notes below — not blocking)

**Notes (spec-precision, non-blocking):**
1. No test directly asserts `degradada`'s specific badge CSS class/icon (only `indisponivel` gets that direct assertion at `test.tsx:516-527`); `degradada` is exercised only for its text label (`test.tsx:258-277`). Same generic templated code path (`tsx:218-223`), so functionally covered by code inspection, but not by a dedicated assertion.
2. No test asserts the per-row "Sintético" origin label in the events table for a synthetic event (only `real_inmet` → "INMET (real)" is asserted, `test.tsx:151`); the primary AC signal (state badge "Sintética") is directly tested.
3. No test asserts the visible badge/text actually changes on screen after the retry completes — only the API call and refetch count. This matches the spec's own Independent Test wording, which grades success by histórico registration, not by a specific post-retry badge value.

---

## Discrimination Sensor

Isolated in a temporary git worktree (`git worktree add`), never `git stash`. Real tree porcelain baseline (`M docs/design/prototype/package-lock.json`, pre-existing and unrelated) captured before sensor work and confirmed identical after `git worktree remove --force`.

| Mutation | File:line | Description | Killed? |
| --- | --- | --- | --- |
| 1 | `src/frontend/src/App.tsx:66-67` (scratch) | Reverted `case 'fontes-de-dados'` to `<EmConstrucao titulo="Fontes de dados" />` (the pre-story placeholder) | ✅ Killed — `App.test.tsx` new integration test failed: `findByRole('heading', {name:'Fonte meteorológica'})` timed out (1 failed / 18 passed) |
| 2 | `src/frontend/src/App.tsx:66-67` (scratch) | Changed `case 'fontes-de-dados'` to `return null` | ✅ Killed — same test failed identically (1 failed / 18 passed) |

**Sensor depth**: lightweight (2 mutations; this feature's only new production code is the one-line case wiring in `App.tsx`)
**Result**: 2/2 killed — PASS ✅
**Isolation check**: `git status --porcelain` before and after sensor work both show only `M docs/design/prototype/package-lock.json` (pre-existing, unrelated) — real tree untouched.

---

## Code Quality

| Principle | Status |
| --- | --- |
| Minimum code | ✅ — one-line case body change + one import + one integration test |
| Surgical changes | ✅ — only `App.tsx`/`App.test.tsx`/`spec.md` touched, matches the story's own scope statement |
| No scope creep | ✅ — no changes to `SuperficieFonteMeteorologica.tsx` itself |
| Matches patterns | ✅ — follows the same `case` → component pattern as `eventos`, `regras`, etc. |
| Spec-anchored outcome check (asserted values match spec) | ✅ — see table above (3 minor notes, non-blocking) |
| Per-layer Coverage Expectation met | ✅ — UI component has direct per-state assertions; navigation integration has a dedicated test |
| Every test maps to a spec requirement — no unclaimed tests | ✅ — the one new test (`App.test.tsx:484-494`) maps directly to MONITORFONTE-01 |
| Documented guidelines followed | none found (no frontend testing-guidelines doc) — strong defaults applied (Testing Library, role-based queries) |

---

## Edge Cases

- [x] "Nenhuma sincronização ainda → operacional, não erro": handled in code (`SuperficieFonteMeteorologica.tsx:61` `if (ultima === null) return 'operacional'`; empty-state text `Nenhuma sincronização registrada até o momento.` at `tsx:354`). Test evidence is partial: `test.tsx:225-234` confirms the `Operacional` badge and no action buttons render for `historicoVazio()`, but does not itself assert the "Nenhuma sincronização registrada" text in the same run. No `❌ erro` state is ever reachable for this input (code path returns `operacional` unconditionally), so functionally correct; test coverage of the literal empty-state message for this exact scenario is not directly cited.
- [x] Precedência de estados quando mais de uma condição vale: directly tested — `SuperficieFonteMeteorologica.test.tsx:413-429` (`recuperada` vence `degradada`), `:431-442` (`indisponivel` vence `sintetica`)

---

## Gate Check

- **Backend gate**: `uv run --directory src/backend pytest` → 1107 passed, 0 failed (exit 0); `uv run --directory src/backend ruff check .` → "All checks passed!"; `uv run --directory src/backend pyright` → 0 errors, 0 warnings, 0 informations. Backend was not touched by this story; run to confirm no regression.
- **Frontend gate**: `npm run test --prefix src/frontend -- run` → 47 test files, 470 tests passed, 0 failed; `npm run lint --prefix src/frontend` → clean (exit 0); `npm run build --prefix src/frontend` → succeeded (exit 0).
- **Test count before feature**: commit message states "470 testes" post-implementation with 1 new test added (`App.test.tsx`); pre-existing `SuperficieFonteMeteorologica.test.tsx` (30 tests) untouched.
- **Test count after feature**: 470 frontend tests (matches commit message), 1107 backend tests.
- **Delta**: +1 new frontend test (the App.tsx navigation-integration test)
- **Skipped tests**: none observed
- **Failures**: none

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
| --- | --- | --- |
| MONITORFONTE-01 | Implementing | ✅ Verified |
| MONITORFONTE-02 | Implementing | ✅ Verified |
| MONITORFONTE-03 | Implementing | ✅ Verified |
| MONITORFONTE-04 | Implementing | ✅ Verified |
| MONITORFONTE-05 | Implementing | ✅ Verified |

---

## Summary

**Overall**: ✅ Ready

**Spec-anchored check**: 5/5 ACs matched spec outcome (3 minor spec-precision notes, non-blocking — see Notes above)
**Sensor**: 2/2 mutations killed
**Gate**: backend 1107 passed / frontend 470 passed, lint clean, build clean, ruff/pyright clean

**What works**: The admin "Fontes de dados" navigation entry now mounts the real, pre-existing, well-tested `SuperficieFonteMeteorologica` component (previously a placeholder). All 6 fonte states render with accessible Portuguese labels, `indisponivel`/`degradada` are visually distinguished from `operacional` via color+icon (and `indisponivel` additionally gets an `alert` role and a "dados desatualizados" note), synthetic events are flagged via the "Sintética" badge, sync history lists each attempt with result and timestamp, and "Solicitar nova tentativa" triggers the retry API and a re-fetch.

**Issues found**: None blocking. Three minor test-coverage precision notes recorded above (degradada badge class not directly asserted; synthetic per-row origin label not directly asserted; post-retry displayed-state change not directly asserted) — all are pre-existing test-file gaps, not introduced by this story, and each AC's core spec-defined outcome still has direct positive test evidence.

**Next steps**: None required to close this story. Optional future hardening (not required for this story's scope): add direct assertions for the 3 notes above to `SuperficieFonteMeteorologica.test.tsx` if that file is touched again.
