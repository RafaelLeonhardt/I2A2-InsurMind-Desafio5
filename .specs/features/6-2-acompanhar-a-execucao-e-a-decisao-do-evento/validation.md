# História 6.2 — Acompanhar a execução e a decisão do evento — Validation

**Date**: 2026-09-09
**Spec**: `.specs/features/6-2-acompanhar-a-execucao-e-a-decisao-do-evento/spec.md`
**Diff range**: `54c2c16..b9eb12f` (code diff itself lives entirely in `bf148e9`, staged together with unrelated 6.3–6.9 specs by accident; `b9eb12f` only adds this feature's own `spec.md`)
**Verifier**: independent sub-agent (author ≠ verifier)

**Result**: PASS ✅

---

## Task Completion

No formal `tasks.md` — Design and Tasks were done inline (Medium scope, reuses AD-016, no new architecture decision). Three atomic changes to `SuperficieExecucao.tsx` per the author's own commit message (`b9eb12f`):

| Change | Status | Notes |
| --- | --- | --- |
| `construirEtapas()` treats any `falhou_*` state as exception (not just `falhou_coleta`) | ✅ Done | `src/frontend/src/funcionalidades/execucao/SuperficieExecucao.tsx:78` |
| New "Execuções correlacionadas" section (`execucaoOrigemId` + `retentativas`, navigable via AD-016) | ✅ Done | `SuperficieExecucao.tsx:243-278` |
| `mostrarDecisaoDeRisco` widened from "only `aguardando_geracao`" to every post-coleta stage | ✅ Done | `SuperficieExecucao.tsx:190-191` |

---

## Spec-Anchored Acceptance Criteria

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| **PAINELEXEC-01** — WHEN admin selects an event with an associated execution THEN interface opens `SuperficieExecucao`, showing current stage + persisted milestone history | List action navigates to the execution surface; that surface derives stage/milestones only from what the API persisted | `src/frontend/src/funcionalidades/eventos/SuperficieEventos.tsx:83-85,162-168` — `onClick={() => abrirExecucao(evento.execucaoId as string)}` calling `selecionarSuperficie({ tipo: 'evento-execucao', ... })`; `src/frontend/src/App.tsx:54-55` — `case 'evento-execucao': return <SuperficieExecucao execucaoId={superficieAtiva.execucaoId} />`; `src/frontend/src/funcionalidades/eventos/SuperficieEventos.test.tsx:61-87` — click "Ver execução" then `expect(screen.getByTestId('superficie-ativa')).toHaveTextContent(JSON.stringify({ tipo: 'evento-execucao', execucaoId: '2222...', perfilPai: 'administrador' }))`; `SuperficieExecucao.tsx:66-103` (`construirEtapas`) tested at `SuperficieExecucao.test.tsx:74-93` (`findByText('Coletando dados meteorológicos…')` / `findByText('Coleta meteorológica concluída')`) | ✅ PASS |
| **PAINELEXEC-02** — WHILE execution is in a risk/rule decision stage THEN interface shows `SuperficieEventoDecisao` with weather evidence and the rule's evaluated conditions | `SuperficieEventoDecisao` embedded for every post-coleta stage (not just `aguardando_geracao`), never for `coletando`/`falhou_coleta` | `SuperficieExecucao.tsx:190-191` — `mostrarDecisaoDeRisco = execucao !== null && execucao.estado !== 'coletando' && execucao.estado !== 'falhou_coleta'`; `:280` — `{mostrarDecisaoDeRisco && <SuperficieEventoDecisao embutido execucaoId={execucaoId} />}`; `SuperficieExecucao.test.tsx:302-313` — `sem_risco` embeds (`container.querySelector('.secao-evento-decisao-embutida')).toBeInTheDocument()`); `:315-321` — `coletando` does NOT embed (`.not.toBeInTheDocument()`); `:164-192` — `aguardando_geracao` still embeds. Evidence/conditions table itself: `SuperficieEventoDecisao.tsx:223-243` (`tabela-criterios-decisao`, columns Operando/Valor observado/Resultado/Justificativa) tested at `SuperficieEventoDecisao.test.tsx:139-151` (`getByText('área aplicável')`, `getByText('9990001')`, `getAllByText('Atende')).toHaveLength(2)`) | ✅ PASS |
| **PAINELEXEC-03** — IF execution terminated in a failure state (e.g. `falhou_coleta`, `falhou_preparacao_ia`) THEN interface shows the terminal state and, when it exists, the correlated retry execution (`execucao_origem_id`, AD-009) | Any `falhou_*` state renders as exception with the persisted cause; origin/retry links navigate via `selecionarSuperficie` (AD-016) | `SuperficieExecucao.tsx:78-84` — `if (execucao.estado.startsWith('falhou_'))` pushes `{ categoria: 'excecao', causa: ultimoMarco?.causa ?? null }`; `:243-278` — "Execuções correlacionadas" section rendered `{execucao.execucaoOrigemId !== null \|\| execucao.retentativas.length > 0}`, buttons call `abrirExecucao(...)` (`:174-183`, uses `selecionarSuperficie`). Tests: `SuperficieExecucao.test.tsx:279-300` — `falhou_preparacao_ia` → `findByText('Falha técnica não recuperável')` + `getByText('ErroIntegracaoIA: contexto mínimo indisponível')`; `:323-343` — origin link `findByRole('button', { name: ORIGEM_ID })`, click, then `toHaveTextContent(JSON.stringify({ tipo: 'evento-execucao', execucaoId: ORIGEM_ID, perfilPai: 'administrador' }))`; `:345-367` — same for a retry id; `:369-377` — no "Execuções correlacionadas" heading when neither origin nor retries exist | ✅ PASS |
| **PAINELEXEC-04** — WHEN the event's decision has identified an eligible audience THEN interface shows a table with name, neighborhood, policy and channel for each eligible insured | Fixed table columns Segurado/Apólice/Localização/Canal, populated from the API's eligibility records | `src/frontend/src/funcionalidades/evento-decisao/SuperficieEventoDecisao.tsx:281-323` (`tabela-publico-elegivel`, headers at `:287-291`, rows at `:296-321`); `SuperficieEventoDecisao.test.tsx:274-287` — `findByRole('table', { name: /Público elegível/ })` then `within(tabela).getByText('Maria Sintética')`, `getByText('João Sintético')`, `getByText('whatsapp')`, `getByText('sms')`, `getByText('Incluído')`, `getByText('Excluído')` | ✅ PASS |
| **PAINELEXEC-05** — WHERE the eligibility backend exposes the eligibility reason THEN interface shows that column; otherwise it stays absent (never invented) | A per-insured reason mechanism grounded only in backend-provided data | `SuperficieEventoDecisao.tsx:311-318` — "Ver critérios"/"Ocultar critérios" button per row; `:326-358` — expanded region renders `criterios`/`justificativa` from `DetalheElegibilidade` (`src/frontend/src/api/elegibilidade.ts:29-42`), never a client-computed value; `SuperficieEventoDecisao.test.tsx:307-351` — keyboard-opens the region, asserts `within(explicacao).getByText('área afetada')`, `getByText('9990001')`, `getByText('Atende')`, and the literal justification text | ⚠️ Spec-precision gap (see note) |

**Status**: ✅ All ACs covered, 1 spec-precision gap flagged (PAINELEXEC-05)

**Note on PAINELEXEC-05**: the spec literally describes a *conditional table column* ("a coluna" shown only `WHERE o backend... expuser o motivo"). The implementation instead exposes the same underlying information (criteria + justification, i.e. the "motivo") through an always-present, expandable "Ver critérios" affordance per row — not a column, and not conditional, because `ResumoElegibilidade`/`DetalheElegibilidade` (`src/frontend/src/api/elegibilidade.ts:5-11,29-42`) never carry a raw `motivo` field at all; there is no code path where the "backend exposes it" branch could ever be exercised, so the WHERE-conditionality itself is never tested. Functionally this satisfies the AC's *intent* (never invents data; shows the real reason when the backend has one to give), but it is not the literal mechanism described, and no test asserts the "column absent when the field is missing" behavior directly (it's absent by construction, not by a runtime check). Not treated as a code gap — nothing needs to change — but flagged so the spec's traceability reflects the actual mechanism rather than the literal wording. This AC predates this session's diff (inherited from História 2.5); it is verified here with fresh evidence, per the evidence-or-zero rule, not by trusting the author's prior annotation.

---

## Edge Cases

- [x] "Evento `dado_invalido`/`sem_risco` (RISCO-12/13) mostra por que nenhuma execução foi criada, sem tela de decisão vazia como erro" — handled at two levels, both pre-existing and already verified: (1) an event with no execution at all shows "Sem execução iniciada" and no "Ver execução" action (`SuperficieEventos.tsx:158`, tested `SuperficieEventos.test.tsx:89-96`); (2) within an execution that did run, `SuperficieEventoDecisao`'s `dado_invalido`/`sem_risco` categories render distinct text+icon+color, never an empty/error-shaped screen (verified previously under RISCO-12/13, `.specs/features/2-3-.../validation.md:59-60`). Nothing in this session's diff touches this path; re-confirmed by reading, not re-tested.
- [x] "Execução bloqueada por exceção: causa exibida vem do marco persistido, nunca de texto inventado" — `SuperficieExecucao.tsx:83` (`causa: ultimoMarco?.causa ?? null`) — tested with two distinct persisted causes: `SuperficieExecucao.test.tsx:144-162` (`'RuntimeError: erro inesperado no risco'`) and `:279-300` (`'ErroIntegracaoIA: contexto mínimo indisponível'`), both asserting the literal persisted string, not a hardcoded label.

---

## Discrimination Sensor

Ran in an isolated `git worktree` (`git worktree add <scratch> HEAD`), `node_modules` symlinked from the real tree to avoid a full reinstall. Real working tree never touched; `git status --porcelain` captured before sensor work and re-checked identical after cleanup (`git worktree remove --force`).

| Mutation | File:line | Description | Killed? |
| --- | --- | --- | --- |
| 1 | `SuperficieExecucao.tsx:78` | `execucao.estado.startsWith('falhou_')` → `!execucao.estado.startsWith('falhou_')` | ✅ Killed — 9/16 tests failed in `SuperficieExecucao.test.tsx` |
| 2 | `SuperficieExecucao.tsx:191` | `mostrarDecisaoDeRisco` condition `execucao.estado !== 'coletando'` → `execucao.estado === 'coletando'` | ✅ Killed — 3/16 tests failed, including the `sem_risco`-embeds and `coletando`-does-not-embed discrimination tests |
| 3 | `SuperficieExecucao.tsx:251` | Removed `abrirExecucao(execucao.execucaoOrigemId as string)` from the origin link's `onClick` (replaced with a no-op) | ✅ Killed — 1/16 tests failed (`mostra a execução de origem como link e navega para ela ao clicar`) |

**Sensor depth**: lightweight (3 targeted mutations, default tier)
**Result**: 3/3 killed — PASS ✅
**Isolation check**: `git status --porcelain` before and after sensor run are byte-identical (only the pre-existing, unrelated `docs/design/prototype/package-lock.json` modification present in both).

---

## Code Quality

| Principle | Status |
| --- | --- |
| No features beyond what was asked | ✅ — 3 changes match the author's own commit description exactly, nothing extra |
| No abstractions for single-use code | ✅ |
| No unnecessary "flexibility" added | ✅ |
| Only touched files required for task | ✅ — diff is exactly `SuperficieExecucao.tsx` + `SuperficieExecucao.test.tsx` |
| Didn't "improve" unrelated code | ✅ |
| Matches existing patterns/style | ✅ — reuses `usePerfilContexto`/`selecionarSuperficie` exactly as `SuperficieEventos.tsx` already does (AD-016) |
| Would senior engineer approve? | ✅ |
| Tests map to acceptance criteria and are non-shallow (spot-check one story) | ✅ — spot-checked P1 story 1 (PAINELEXEC-01..03): every new test asserts a specific rendered string or a specific `superficie-ativa` payload, never just "no crash" |
| Spec-anchored outcome check | ✅ 4/5 direct match, 1 spec-precision gap (PAINELEXEC-05, see above) |
| Per-layer Coverage Expectation met | ✅ — domain logic (`construirEtapas`, `mostrarDecisaoDeRisco`) has 1:1 coverage per branch (`coletando`, `falhou_coleta`, other `falhou_*`, `sem_risco`, `aguardando_geracao`) |
| Every test in scope maps to a spec AC, listed edge case, or Done-when criterion | ✅ — all 6 new tests map to PAINELEXEC-02/03 |
| Documented project quality/testing guidelines followed | `.specs/LESSONS.md` (confirmed lessons on fixture variation, per-layer testing) — followed; no violation found |

---

## Gate Check

- **Gate commands**: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright` ; `npm run test --prefix src/frontend -- run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`
- **Backend result**: 1099 passed, 0 failed, 0 skipped; ruff — all checks passed; pyright — 0 errors, 0 warnings
- **Frontend result**: 467 passed (47 files), 0 failed, 0 skipped; lint (`oxlint`) — exit 0, only pre-existing warnings (none in the two changed files' new code, one pre-existing `set-state-in-effect` warning at `SuperficieExecucao.tsx:149` predates this diff — same line before and after); build — succeeded
- **Test count before this story** (commit `54c2c16`, immediately before `bf148e9`): backend 1099, frontend 461 (47 files)
- **Test count after this story** (current `HEAD` = `b9eb12f`): backend 1099, frontend 467 (47 files)
- **Delta**: backend +0 (expected — no backend files in this story's diff), frontend +6 new tests, matching the 6 new `it(...)` blocks added in `SuperficieExecucao.test.tsx` (`falhou_preparacao_ia` as exception; embeds decisão in `sem_risco`; does not embed in `coletando`/`falhou_coleta`; origin link navigation; retry link navigation; no correlated-executions section when neither exists)
- **Skipped tests**: none
- **Failures**: none

---

## Fix Plans

None — no code gap found. PAINELEXEC-05 is a spec-precision note (documentation/traceability nuance), not a fix task.

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
| --- | --- | --- |
| PAINELEXEC-01 | Implementing | ✅ Verified |
| PAINELEXEC-02 | Implementing | ✅ Verified |
| PAINELEXEC-03 | Implementing | ✅ Verified |
| PAINELEXEC-04 | Implementing | ✅ Verified |
| PAINELEXEC-05 | Implementing | ✅ Verified (spec-precision note recorded above) |

---

## Summary

**Overall**: ✅ Ready

**Spec-anchored check**: 5/5 ACs covered, 1 spec-precision gap flagged (PAINELEXEC-05 — mechanism differs from literal wording, intent fully met)
**Sensor**: 3/3 mutations killed
**Gate**: backend 1099 passed / frontend 467 passed, 0 failed, lint/build/ruff/pyright all clean

**What works**: Every ACs' spec-defined outcome is backed by a `file:line` test assertion targeting the exact rendered text or navigation payload, not a vague "renders something" check. The 6 new tests discriminate real behavior — confirmed empirically by 3/3 sensor mutations being killed, covering the three riskiest new branches (`falhou_*` generalization, widened `mostrarDecisaoDeRisco`, origin-link navigation). PAINELEXEC-01 and PAINELEXEC-04/05's pre-existing dependencies (6.1's navigation, `SuperficieEventoDecisao` from 2.5) were re-verified with fresh `file:line` evidence rather than trusting the author's traceability annotations, per evidence-or-zero. Test count delta (+6 frontend, +0 backend) exactly matches the diff's scope — no backend touched, no test deleted or weakened.

**Issues found**: PAINELEXEC-05 — spec wording describes a conditional column that can architecturally never appear (no `motivo` field exists anywhere in the eligibility API types); actual behavior is an always-present "Ver critérios" expansion showing the same grounded information. No functional defect; recommend the spec's wording be reconciled with the real mechanism next time `spec.md` for a 2.5-derived AC is touched, so future verifiers don't need to re-derive this each time.

**Next steps**: None required to close this story. Optional (non-blocking): if a future backend adds a distinct per-segurado `motivo` field, decide then whether it becomes a table column (per spec's literal text) or folds into the existing "Ver critérios" explanation.
