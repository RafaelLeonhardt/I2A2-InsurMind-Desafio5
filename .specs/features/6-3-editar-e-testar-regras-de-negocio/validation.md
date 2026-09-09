# História 6.3: Editar e testar regras de negócio — Validation

**Date**: 2026-09-09
**Spec**: `.specs/features/6-3-editar-e-testar-regras-de-negocio/spec.md`
**Diff range**: `aa5d18d` (parent `f9a00c6`)
**Verifier**: independent sub-agent (author ≠ verifier)
**Scope**: REGRASADM-01/02/03 (P1). REGRASADM-04 (P2) is out of scope for this verification — status `Deferred`, not touched.

---

## Task Completion

No formal `tasks.md` exists for this feature (Medium scope, Design done inline per spec.md Coverage note). Execute was a single atomic commit:

| Item | Status | Notes |
| ---- | ------ | ----- |
| `App.tsx` mounts `SuperficieRegras` in `case 'regras'` | ✅ Done | `src/frontend/src/App.tsx:60` |
| Integration test for "Regras de negócio" nav | ✅ Done | `src/frontend/src/App.test.tsx:439-462` |
| Placeholder test moved to "Segurados" (no coverage lost) | ✅ Done | `src/frontend/src/App.test.tsx:465-473` |
| New REGRASADM-03 conflict test (409) | ✅ Done | `src/frontend/src/funcionalidades/regras/SuperficieRegras.test.tsx:262-297` |
| spec.md updated (Assumption correction, Out of Scope, traceability) | ✅ Done | reviewed below |

---

## Spec-Anchored Acceptance Criteria

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| REGRASADM-01: WHEN administrador abre "Regras de negócio" THEN interface exibe a regra ativa "com suas seções de Evento, Público elegível e Comunicação preenchidas com os valores persistidos" | Literal outcome: three named sections (Evento / Público elegível / Comunicação) populated with persisted values | `src/frontend/src/App.test.tsx:439-462` mounts real `SuperficieRegras`, asserts `heading` "Regras" and cell text `Chuva intensa`; `src/frontend/src/funcionalidades/regras/SuperficieRegras.tsx:190-294` renders one versioned **table** (columns: Tipo de evento, Severidade, Limiar, Área, Apólice, Cobertura, Antecedência, Canal, Versão, Estado, Ação) — no section named "Evento", "Público elegível" or "Comunicação" exists anywhere in the component | ⚠️ Spec-precision gap — see Gap 1 below. The underlying capability (view active rule with persisted field values) is genuinely delivered and tested; the AC's literal wording was not corrected when the Assumptions table below it was |
| REGRASADM-02: WHEN administrador altera um campo e confirma "Salvar e testar regra" THEN sistema persiste nova versão e atualiza a versão exibida | Persist new version; UI reflects updated version | `src/frontend/src/funcionalidades/regras/SuperficieRegras.test.tsx:235-259` — clicks `Testar` then `Ativar nova versão` (no button named "Salvar e testar regra" exists — two-step flow), asserts `ativarRegra` called with `(REGRA_ATIVA.id, REGRA_ATIVA.versao, {...})` (`:255-259`) and `findByRole('status')` shows "Nova versão ativada" (`:254`), consistent with `ativarRegra.mockResolvedValue({...versao: 2})` (`:245`) | ✅ PASS on outcome (persist + version update reflected) — trigger-button name in the WHEN clause is stale (minor, see Gap 2), does not affect the THEN outcome being verified |
| REGRASADM-03: IF a versão mudou no backend (conflito otimista) THEN sistema rejeita a gravação com erro explícito, sem sobrescrever | Explicit error surfaced; no silent overwrite; latest version not clobbered | `src/frontend/src/funcionalidades/regras/SuperficieRegras.test.tsx:291-293` — `expect(await screen.findByRole('alert')).toHaveTextContent('A regra foi alterada por outra pessoa desde que esta tela foi carregada.')`; `:294` — `expect(screen.queryByRole('status')).toBeNull()` (no success message = no overwrite); backend contract confirmed at `src/backend/central_preventiva/adaptadores/http/regras.py:456-463` (`ConflitoVersao` → 409 `conflito_versao`) | ✅ PASS |

**Status**: ⚠️ 2/3 clean PASS, 1 spec-precision gap (REGRASADM-01 wording), 1 minor stale wording noted (REGRASADM-02) — no implementation gap found for any of the three in-scope ACs.

---

## Edge Cases (from spec.md)

| Edge case | Result |
| --- | --- |
| IF nenhuma regra preventiva ativa existir THEN mostrar esse estado explicitamente | ❌ Not covered by any test (evidence-or-zero). Code at `SuperficieRegras.tsx:224-225` handles only the fully-empty case (`regras.length === 0` → "Nenhuma regra configurada até o momento."), not the literal edge case as worded (existing rows, none `estado === 'ativa'`) — that state renders the table with only "Substituída" rows and no explicit "no active rule" message. Pre-existing 2.4 behavior, not touched by this diff, but now reachable through navigation for the first time — see Gap 3 |
| WHEN administrador tenta salvar condição inválida (ex.: limiar negativo) THEN rejeitar com mensagem de validação específica | ✅ Covered — `src/frontend/src/funcionalidades/regras/SuperficieRegras.test.tsx:199-233`, types `-1` into limiar (`:220`), asserts `findByText('Limiar meteorológico deve ser maior que zero.')` (`:227-229`) and `Ativar nova versão` stays disabled (`:232`) |

---

## Discrimination Sensor

Isolated `git worktree` at a scratch path (never `git stash`); `src/frontend/node_modules` symlinked in for speed; removed before `git worktree remove --force`.

| # | File:line | Description | Killed? |
| - | --- | --- | --- |
| 1 | `src/frontend/src/funcionalidades/regras/SuperficieRegras.tsx:443` | Flipped `Object.keys(errosCampo).length === 0` → `!== 0` (gate for the generic 409 failure alert) | ✅ Killed — REGRASADM-03 test fails: `findByRole('alert')` times out |
| 2 | `src/frontend/src/funcionalidades/regras/SuperficieRegras.tsx:178-179` | Removed `tratarFalha(causa)` call in `ativar()`'s catch block (dropped required side effect) | ✅ Killed — same REGRASADM-03 test fails identically |

**Sensor depth**: lightweight (2 mutations, targeted at the new REGRASADM-03 behavior)
**Result**: 2/2 killed — PASS
**Isolation check**: baseline `git status --porcelain` before sensor = `M docs/design/prototype/package-lock.json` (pre-existing, unrelated). After worktree removal, `git status --porcelain` on the real tree = identical single line. Confirmed intact.

---

## Code Quality

| Principle | Status |
| --- | --- |
| Minimum code | ✅ — 4 files touched, ~85 lines, matches "mount existing component" scope |
| Surgical changes | ✅ — `App.tsx` diff is a 1-line swap + 1 comment update |
| No scope creep | ✅ — `SuperficieRegras.tsx` and `api/regras.ts` (2.4 code) untouched |
| Matches existing patterns | ✅ — mocking pattern in `App.test.tsx` mirrors existing `getEventosMock` etc. |
| Spec-anchored outcome check | ⚠️ — see Gaps 1/2 (spec wording, not code, is stale) |
| Per-layer coverage (route+e2e happy/edge/error) | ✅ for REGRASADM-01/02/03; ❌ for "no active rule" edge case (pre-existing gap, see Gap 3) |
| Every test maps to a spec AC / edge case / Done-when | ✅ — no unclaimed tests found in the diff |
| Documented guidelines followed | none found beyond this skill's own conventions — strong defaults applied |

---

## Gate Check

- **Backend gate**: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright` → 1099 passed, ruff clean, pyright "0 errors, 0 warnings, 0 informations". Backend was not touched by this story; run to confirm no regression.
- **Frontend gate**: `npm run test --prefix src/frontend -- run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend` → **Test Files 47 passed (47)**, **Tests 469 passed (469)**; lint clean; build succeeded (`✓ built in 265ms`).
- **Test count before feature** (parent `f9a00c6`): 467 (469 − 2 net-new: +2 in `App.test.tsx` −1 renamed-away = net +1; +1 in `SuperficieRegras.test.tsx` = net +1; total +2, consistent with diff).
- **Test count after feature**: 469.
- **Delta**: +2 new tests (REGRASADM-01 integration test in `App.test.tsx`, REGRASADM-03 conflict test in `SuperficieRegras.test.tsx`); one placeholder test relabeled 'regras'→'segurados' rather than deleted — no coverage lost.
- **Skipped tests**: none.
- **Failures**: none.

---

## Fix Plans (gaps found — spec-documentation only, no code gap)

### Gap 1: REGRASADM-01 AC text not updated after Design-phase correction

- **Root cause**: The Assumptions table in spec.md correctly documents (with code evidence) that `SuperficieRegras` has no "Evento/Público elegível/Comunicação" sections — it's a versioned table + edit form. But the P1 Acceptance Criteria list (AC #1) still uses that stale wording ("com suas seções de Evento, Público elegível e Comunicação preenchidas"), which the actual UI cannot literally satisfy.
- **Fix task**: Reword REGRASADM-01's AC #1 in spec.md to describe the actual UI shape (versioned table row with the regra's persisted fields), consistent with the corrected Assumption.
- **Priority**: Minor (documentation only; the delivered capability is correct and tested, only the spec's phrasing is stale).

### Gap 2: REGRASADM-02 AC trigger wording ("Salvar e testar regra") doesn't match the UI

- **Root cause**: Same class of issue as Gap 1 — the actual flow is two separate buttons ("Testar" then "Ativar nova versão"), not one "Salvar e testar regra" action. The THEN outcome (persist + version update) is correctly delivered and tested; only the WHEN trigger description is stale.
- **Fix task**: Reword REGRASADM-02's AC #2 WHEN clause to name the actual two-step flow.
- **Priority**: Cosmetic (does not affect verifiability of the outcome).

### Gap 3: "No active rule" edge case has no explicit UI state or test

- **Root cause**: `SuperficieRegras.tsx:224-225` only distinguishes "zero regras total" from "has regras"; it does not detect "regras exist but none is `estado === 'ativa'`" and show that edge case's required explicit message. This is pre-existing 2.4 behavior (not part of this diff), but 6.3 is what first exposes it to real users via navigation, and spec.md's own Edge Cases section requires it.
- **Fix task**: Add a check for "no `estado === 'ativa'` row" distinct from "no rows at all," with an explicit message, plus a test. Out of this story's diff — recommend as a small follow-up task, not a blocker for REGRASADM-01/02/03.
- **Priority**: Minor (existing gap, now reachable; does not regress anything this story touched).

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
| --- | --- | --- |
| REGRASADM-01 | Implementing | ✅ Verified (spec-precision gap noted, Gap 1 — non-blocking) |
| REGRASADM-02 | Implementing | ✅ Verified (spec-precision gap noted, Gap 2 — non-blocking) |
| REGRASADM-03 | Implementing | ✅ Verified |
| REGRASADM-04 | Deferred | Deferred (unchanged — out of scope for this verification, decision well-documented in Out of Scope + traceability, no ambiguity found) |

---

## Summary

**Overall**: ⚠️ Ready, with 2 non-blocking spec-wording gaps and 1 pre-existing (untouched) edge-case gap flagged for follow-up

**Spec-anchored check**: 2/3 clean PASS, 1 spec-precision gap (REGRASADM-01)
**Sensor**: 2/2 mutations killed
**Gate**: 469 frontend + 1099 backend passed, 0 failed

**What works**: `SuperficieRegras` is correctly mounted at `case 'regras'`; the P1 edit/test/activate flow (REGRASADM-01/02) and the optimistic-concurrency conflict path (REGRASADM-03) are all genuinely exercised end-to-end with evidence, and the REGRASADM-03 test measurably discriminates real regressions (sensor confirmed). The REGRASADM-04 deferral is unambiguous: Out of Scope table cites the explicit user decision, the capability gap (no backend endpoint to count eligible insureds), and the traceability table correctly marks it `Deferred` (not `Pending`/`Implementing`) with rationale — no gap found there.

**Issues found**:
1. REGRASADM-01's AC text still describes a UI structure ("seções de Evento/Público elegível/Comunicação") that the Assumptions table itself says doesn't exist — spec.md wording, not code, needs a follow-up edit.
2. REGRASADM-02's AC trigger wording names a button that doesn't exist — same class of issue.
3. The "no active rule" edge case (spec.md Edge Cases) has no explicit handling or test distinct from "zero rules total" — pre-existing, not part of this diff, but now reachable.

**Next steps**: Reword REGRASADM-01/02 AC text in spec.md to match the corrected Assumption (Gaps 1-2, cosmetic, can be done same-session). File Gap 3 as a small standalone follow-up task against `SuperficieRegras.tsx` (2.4 code) if the product wants that edge case closed before more users rely on it.
