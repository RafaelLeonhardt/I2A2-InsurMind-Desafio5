# História 4.1: Consolidar resultados e estados da simulação — Validation

**Date**: 2026-09-04 (round 2)
**Spec**: `.specs/features/4-1-consolidar-resultados-e-estados-da-simulacao/spec.md`
**Diff range**: `69d4097..27f9968` — T1 `dc19fd3`, T2 `4f109c4`, T3 `a59cee1`, T4 `2b63f5a`, Fix 1 `27f9968`
**Verifier**: independent sub-agent (author ≠ verifier)

---

## Round 1 → Round 2

Round 1 (diff `69d4097..2b63f5a`) found 9/10 ACs directly evidenced, all edge cases handled, and a full green Build gate (904 backend / 296 frontend), but the discrimination sensor found **1 of 3 mutants survived**: flipping the sort-direction sign in `ordenarTotais` (`SuperficieResultados.tsx:122`) passed all 11 existing frontend tests, because `SuperficieResultados.test.tsx`'s sort test asserted only the `aria-sort` attribute, never the actual rendered row order. Verdict: FAIL (sensor 2/3).

**Fix 1** (`27f9968`, test-only): rewrote the sort test to assert the real row order (`within(tabelaEstado).getAllByRole('row')` text content) before/after each header click, in both directions — scoped to the `totais_por_estado` table via `within(...)`, not a global query. No production code changed; the diff `2b63f5a..27f9968` touches exactly one file, `SuperficieResultados.test.tsx` (+14/-5).

This round re-runs the sensor against that exact mutation and re-confirms the rest of round 1 still holds against the new `HEAD`.

---

## Task Completion

| Task | Status | Notes |
| ---- | ------ | ----- |
| T1: `RepositorioMensagens.listar_por_execucao` | ✅ Done | Unchanged since round 1. |
| T2: `ServicoConsolidacaoResultados` | ✅ Done | Unchanged since round 1. |
| T3: Endpoint HTTP de resultados | ✅ Done | Unchanged since round 1. |
| T4: Superfície de Resultados | ✅ Done | Unchanged production code; test strengthened by Fix 1. |
| Fix 1: sort-order assertion | ✅ Done | `SuperficieResultados.test.tsx` now asserts real row order, not just `aria-sort`. |

---

## Spec-Anchored Acceptance Criteria

Unchanged from round 1 — no production code changed between rounds, so round 1's evidence for RESULT-01..07, 09, 10 stands as re-verified (re-run in this round's Gate Check below). RESULT-08 evidence is upgraded by Fix 1:

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| RESULT-01: confirmação atômica Preparada/Processada/Enviada-simulação | Pre-verified in 3.6; `ServicoConsolidacaoResultados` has no write ports | `src/backend/central_preventiva/aplicacao/consolidacao_resultados.py:101-118` | ✅ PASS |
| RESULT-02: totais reconciliáveis | Soma == quantidade real do lote | `src/backend/testes/test_consolidacao_resultados.py:97`; `test_resultados_api.py:69-78` | ✅ PASS |
| RESULT-03: não-simuláveis contabilizadas à parte | `nao_simulaveis` nunca somado às entregas | `test_consolidacao_resultados.py:98-99,112-115` | ✅ PASS |
| RESULT-04: `falhou_simulacao` sem entrega parcial | Zero `simulada_entregue`, mensagens `aprovada` | `test_consolidacao_resultados.py:130-133`; `test_resultados_api.py:111-114` | ✅ PASS |
| RESULT-05: nunca falha fictícia de canal | Nenhum motivo menciona canal | `test_consolidacao_resultados.py:135-140` | ✅ PASS |
| RESULT-06: reidratação sem repetir transição | Duas consultas idênticas, sem nova linha | `test_consolidacao_resultados.py:154-156`; `test_resultados_api.py:151` | ✅ PASS |
| RESULT-07: nunca regride/reabre estado terminal | Nenhuma escrita alcançável de `consolidar` | `consolidacao_resultados.py:101-118` (Protocols só leem) | ✅ PASS |
| RESULT-08: cabeçalhos/ordenação/contagens/ações com nomes acessíveis | Nomes acessíveis via roles ARIA; ordenação afeta de fato a ordem exibida | `SuperficieResultados.test.tsx:104-113` (nomes acessíveis); **`:115-133` (Fix 1)** — `expect(linhas[0]).toHaveTextContent('Rejeitada')` / `expect(linhas[1]).toHaveTextContent('Enviada — simulação')` após clique ascendente, invertido após o segundo clique; `:135-142` (ativação só por teclado) | ✅ PASS (upgraded — round 1's shallow attribute-only assertion is now a real content-order assertion) |
| RESULT-09: divergência com correlação/impacto, nunca corrigida | `divergencia` preenchido, total exibido inalterado | `test_consolidacao_resultados.py:170-174`; `SuperficieResultados.test.tsx:146-164` | ✅ PASS |
| RESULT-10: "Enviada — simulação" por extenso, texto+ícone+cor | Rótulo exato + ícone/cor distintos | `SuperficieResultados.tsx:48-53`; test `:62-83` | ✅ PASS |

**Status**: ✅ All 10 ACs covered with direct file:line evidence (RESULT-01 additionally pre-verified in 3.6). Round 1's RESULT-08 spec-precision note (no per-row action buttons exist yet — deferred to História 4.2 per spec.md Out of Scope) still applies and remains non-blocking; the sort/accessibility portion of RESULT-08 is now fully evidenced, not just attribute-shallow.

---

## Discrimination Sensor (round 2)

Isolated `git worktree add <scratch> HEAD` off `27f9968`; baseline `git status --porcelain` captured before and confirmed identical after (`diff` of both captures was empty).

| Mutation | File:line | Description | Killed? |
| --- | --- | --- | --- |
| 3 (re-run) | `src/frontend/src/funcionalidades/resultados/SuperficieResultados.tsx:122` | `const sinal = ordenacao.direcao === 'asc' ? 1 : -1` → flipped to `? -1 : 1` (identical mutation to round 1) | ✅ **Killed** — `SuperficieResultados.test.tsx` failed 1/11: `expect(linhas[0]).toHaveTextContent('Rejeitada')` received `'Enviada — simulação2'` instead |

Mutations 1 and 2 from round 1 (divergence-detection flip, `concluido` always-true) target backend code untouched since round 1; both already confirmed killed in round 1 and the underlying code is unchanged, so they are not re-injected this round — re-running an unrelated mutant against unmodified code would produce no new information (round 1's report already permanently records `file:line`, description, and kill evidence for them).

**Sensor depth**: lightweight (1 targeted re-run of the round-1 survivor)
**Result**: 3/3 killed across both rounds (2 confirmed round 1 + 1 confirmed round 2) — **PASS** ✅

---

## Code Quality

| Principle | Status |
| --- | --- |
| Minimum code | ✅ — Fix 1 is test-only, 14/-5 lines, one file |
| Surgical changes | ✅ |
| No scope creep | ✅ |
| Matches patterns | ✅ — uses existing `within(...)`/`getAllByRole('row')` Testing Library idioms already used elsewhere in the suite |
| Spec-anchored outcome check | ✅ |
| Per-layer Coverage Expectation met | ✅ |
| Every test maps to a spec requirement — no unclaimed tests | ✅ |
| Documented guidelines followed | ✅ — `AGENTS.md`, `README.md`, Test Coverage Matrix floor tests |
| Discrimination sensor confirms tests are non-shallow | ✅ — round 1's shallow attribute-only sort assertion is now a real row-order assertion |

---

## Edge Cases

- [x] Sem nenhuma mensagem aprovada → zero entregas simuladas, sem erro: `test_consolidacao_resultados.py:194-206`
- [x] Duas execuções distintas nunca misturam contagens: `test_consolidacao_resultados.py:209-227`
- [x] Consulta durante `simulando` mostra progresso real, não total parcial: `test_consolidacao_resultados.py:177-191`, `test_resultados_api.py:81-96`, `SuperficieResultados.test.tsx:174-190`

---

## Gate Check

- **Gate command**: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright` **and** `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`
- **Result**: backend — 904 passed, 0 failed; `ruff check .` → All checks passed; `pyright` → 0 errors, 0 warnings, 0 informations. frontend — 296 tests / 31 files passed, 0 failed; `oxlint` → 0 errors (20 pre-existing warnings across the codebase, none new, none in `resultados/`); `vite build` → succeeded.
- **Test count before feature (round 0 baseline)**: 888 backend / 285 frontend
- **Test count after round 1 (`2b63f5a`)**: 904 backend / 296 frontend
- **Test count after round 2 / Fix 1 (`27f9968`)**: 904 backend / **296 frontend** (unchanged from round 1 — Fix 1 strengthened the assertions of an *existing* `it()` block rather than adding a new one; verified directly: `grep -c "  it(" SuperficieResultados.test.tsx` returns `11` both before and after `27f9968`). The round-1→2 handoff's expectation of 297 does not match the actual diff and is corrected here per the "confirm the actual total yourself" instruction.
- **Skipped tests**: none
- **Failures**: none

---

## Requirement Traceability Update

| Requirement | Previous Status (round 1) | New Status (round 2) |
| --- | --- | --- |
| RESULT-01 | Verified (pre-existing, 3.6) | Verified |
| RESULT-02 | Implementing | ✅ Verified |
| RESULT-03 | Implementing | ✅ Verified |
| RESULT-04 | Implementing | ✅ Verified |
| RESULT-05 | Implementing | ✅ Verified |
| RESULT-06 | Implementing | ✅ Verified |
| RESULT-07 | Implementing | ✅ Verified |
| RESULT-08 | Implementing | ✅ Verified |
| RESULT-09 | Implementing | ✅ Verified |
| RESULT-10 | Implementing | ✅ Verified |

Applied to `spec.md`'s Requirement Traceability table and Coverage summary line in this same change.

---

## Lessons

**L-050** (candidate, recurrence 1, scope `frontend-tables`): *"When testing a sortable table, assert the actual rendered row order after activating sort, not only the aria-sort attribute value."* Recorded in round 1 against the surviving mutant. Decision this round: **left as-is, unchanged.** The specific instance is fixed in this feature, but `lessons.py` candidates are promoted by corroboration across ≥2 *distinct* features (not by an in-feature fix), and the lesson's value is forward-looking guidance for future sortable-table work elsewhere in the codebase. `penalize` does not apply — that action is for a *confirmed* lesson that was loaded as guidance and then failed again, which is not this case (L-050 was created, not loaded, this session). No new lesson is warranted for the fix itself (fixing a gap is not a new grounded failure signal).

---

## Summary

**Overall**: ✅ Ready

**Spec-anchored check**: 10/10 ACs matched spec outcome, 0 gaps, 1 non-blocking spec-precision note (RESULT-08 row actions out of scope, deferred to 4.2)
**Sensor**: 3/3 mutations killed (2 confirmed round 1, 1 re-confirmed round 2 after Fix 1)
**Gate**: backend 904 passed / frontend 296 passed, ruff/pyright/lint/build all green

**What works**: Everything reported in round 1 (pure read-only consolidation with no reachable write path; reconciled totals; non-simulable accounting; `falhou_simulacao` honesty; divergence reporting with correlation/impact, never silently corrected; "Enviada — simulação" text+icon+color; all 3 spec edge cases) plus the previously-shallow sort test now genuinely proves row reordering in both directions, closing the only gap from round 1.

**Issues found**: none remaining.

**Next steps**: None — feature verified. `spec.md` Requirement Traceability updated to Verified for RESULT-01..10; this report, the traceability update, and the lessons bookkeeping are committed together in one atomic commit.
