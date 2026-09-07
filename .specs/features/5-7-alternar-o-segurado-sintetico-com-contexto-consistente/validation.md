# História 5.7: Alternar o segurado sintético com contexto consistente — Validation (Round 2)

**Date**: 2026-09-06
**Spec**: `.specs/features/5-7-alternar-o-segurado-sintetico-com-contexto-consistente/spec.md`
**Diff range (this round)**: `9ab6c0f..a57df76` (fix commit; `594ecf0` on top is docs-only, recording round 1)
**Full feature diff range**: `2794f90..a57df76`
**Verifier**: independent sub-agent (author ≠ verifier) — fresh pass, round 2
**Result**: PASS ✅ — round 1's Blocker (Gap 1, reachability) is closed; component-level logic (unchanged this round) remains spec-precise; all gates green; sensor kills both the round-1 logic mutations (unchanged code, not re-run) and a new round-2 mutation targeting the fix itself.

---

## Round 1 recap (for context, not re-copied as evidence)

Round 1 (`validation.md` as of commit `594ecf0`, diff range `2794f90..9ab6c0f`) found:
- T1–T4 and the `PainelSegurado` composition itself (T5) correct and spec-precisely tested at the component/isolated level — 8/8 requirements SELETOR-01..08, 0 spec-precision gaps.
- Sensor 3/3 killed on `SeguradoContexto.tsx`'s core guarantees (late-response discard, revert-on-failure, same-id no-op).
- Gate green on both stacks.
- **Overall FAIL** on one Blocker: `PainelSegurado` was composed correctly but never mounted anywhere reachable — `src/frontend/src/App.tsx` still rendered a bare `<VisaoGeralSegurado />` under the Segurado profile's `'visao-geral'` case, so no demo presenter could ever reach the "Visualizar como" selector.

This round re-derives the verdict from scratch rather than trusting that recap; the recap is included only so the reader has the "why" behind what changed.

---

## Task Completion

| Task | Status | Notes |
| --- | --- | --- |
| T1: `RepositorioSegurados.listar_sinteticos` | ✅ Done | Unchanged since round 1; re-confirmed by backend gate (1095/1095 pytest). |
| T2: `GET /api/v1/segurados` | ✅ Done | Unchanged since round 1; re-confirmed by backend gate. |
| T3: `SeguradoContexto` (provider) | ✅ Done | Unchanged since round 1 (`git diff 9ab6c0f..a57df76` touches only `App.tsx`/`App.test.tsx`/`tasks.md`). |
| T4: `SeletorSegurado` | ✅ Done | Unchanged since round 1. |
| T5: Integração das 5 superfícies (`PainelSegurado`) | ✅ Done | Unchanged since round 1 — component-level composition was already correct. |
| **Fix 1 (round 2): mount `PainelSegurado` in the real shell** | ✅ Done | `src/frontend/src/App.tsx:11,41` — `SuperficieAtiva`'s `case 'visao-geral'` now returns `<PainelSegurado />` (was `<VisaoGeralSegurado />`); confirmed by direct read, not by trusting the commit message. |

---

## Spec-Anchored Acceptance Criteria

### P1: Seletor "Visualizar como" sem ambiguidade de autenticação

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| WHEN a pessoa abrir o seletor demonstrativo no perfil Segurado ativo THEN a interface exibe só os sintéticos do seed, rotulado "Visualizar como", nunca login/autenticação | Lista mostra só segurados do seed; nenhum texto de login/senha/entrar; **e o seletor deve ser alcançável a partir do perfil Segurado real** | Component level (unchanged): `src/frontend/src/funcionalidades/segurado/SeletorSegurado.test.tsx:35-44,46-58`. **Reachability (new this round)**: `src/frontend/src/App.tsx:11,41` mounts `<PainelSegurado />` for `case 'visao-geral'`; `src/frontend/src/App.test.tsx:200-224` renders the real `<App/>`, clicks the real `Visualizar como Segurado` profile toggle (`:220`), and asserts `screen.findByRole('combobox', { name: 'Visualizar como' })` resolves (`:223`) | ✅ PASS — reachable and spec-precise |

### P1: Troca consistente entre as cinco superfícies

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| WHEN outro segurado for selecionado e a transição terminar THEN as 5 superfícies refletem o mesmo segurado, sem dado persistido alterado | Todas as 5 mostram dado do novo segurado, nenhuma mistura | Component level (unchanged): `PainelSegurado.test.tsx:159-194` — asserts `APOL-B`/`Assunto B`/unchecked checkbox appear and `Área Demo A`/`APOL-A`/`Assunto A` are gone. **Reachability**: `App.test.tsx:200-230` — through the real UI, selects segurado B in the live combobox (`:226`) and asserts `APOL-B` appears (`:228`) while `APOL-A` disappears (`:229`) | ✅ PASS |
| WHILE o novo contexto ainda carregando THEN `Contexto trocando` impede mistura, sem manter conteúdo anterior sob o novo nome | Nenhuma superfície muda de segurado antes da troca ser confirmada | Component level (unchanged): `PainelSegurado.test.tsx:174-181`; `SeletorSegurado.test.tsx:121-145` | ✅ PASS at component level — same behavior now reachable end-to-end (no round-2 change to this branch's own logic, so not re-asserted at App level; App-level test does not need to duplicate it) |
| IF falha ao carregar parte do novo contexto THEN bloqueia/reverte ao último contexto íntegro, com causa/impacto/próxima ação visíveis | `seguradoAtivoId` volta ao valor anterior; `falha` expõe as 3 campos | Component level (unchanged): `SeguradoContexto.test.tsx:96-119` | ✅ PASS (spec-precise) at component level, now reachable via `PainelSegurado` mounted in the real app |

### P1: Ausência de ações administrativas e retorno seguro ao Administrador

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| WHEN qualquer superfície do Segurado for inspecionada THEN nenhum comando administrativo existe; endereço administrativo direto retorna ao contexto correto | Nenhum botão/link com nome "editar regra"/"gerar mensagem"/"aprovar lote"/"iniciar simulação" | Component level (unchanged): `PainelSegurado.test.tsx:196-212` — iterates every button/link accessible name against the 4 forbidden patterns. Now genuinely relevant in practice: this component is what actually renders under the Segurado profile | ✅ PASS |
| WHEN a pessoa voltar ao Administrador THEN as superfícies administrativas reaparecem, sem conceder/retirar autoridade | Perfil volta a listar `prontidao`/`restaurar-dados-sinteticos`/`documentacao-api` | `src/frontend/src/App.test.tsx:232-243` ("Segurado → Administrador...", unmodified from round 1, 1.4-inherited) | ✅ PASS |

### P2: Acessibilidade do seletor

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| WHEN o seletor for operado por teclado THEN rótulo, opção ativa, foco e mudança são anunciados | Tab foca o campo; seleção anuncia "Visualizando como X" | Component level (unchanged): `SeletorSegurado.test.tsx:60-77` | ✅ PASS — now reachable (the selector renders under the live Segurado profile) |
| The control SHALL possuir alvo mínimo 44×44px e motivo textual quando desabilitado | Classe CSS com min 44px; texto do motivo visível quando desabilitado | Component level (unchanged): `SeletorSegurado.test.tsx:93-119,121-145`; `SeletorSegurado.css` | ✅ PASS |

**Status**: ✅ All 8 requirements (SELETOR-01..08) are correctly implemented, spec-precisely tested at the component level (unchanged since round 1, so not re-audited line-by-line here beyond confirming the files are untouched by `git diff 9ab6c0f..a57df76`), **and are now reachable from the actual running application** — the deciding gap from round 1 is closed.

---

## Reachability re-verification (round-2 specific)

Read directly, not inferred from the commit message:

- `src/frontend/src/App.tsx:11` imports `PainelSegurado` from `./funcionalidades/segurado/PainelSegurado` (the old `VisaoGeralSegurado` import is gone).
- `src/frontend/src/App.tsx:40-41`: `SuperficieAtiva`'s switch, `case 'visao-geral': return <PainelSegurado />`. This is the only case for the `'visao-geral'` surface, and `SUPERFICIES_POR_PERFIL.segurado` (`src/frontend/src/contexto/PerfilContexto.tsx:15`) is `['visao-geral']` — the sole and default surface for the Segurado profile. `PainelSegurado` is therefore unconditionally rendered whenever the Segurado profile is active; nothing gates it behind a flag that never fires, and the import is used (not dead).
- `src/frontend/src/funcionalidades/segurado/PainelSegurado.tsx:45-51`: `PainelSegurado` wraps `<SeguradoProvider><ConteudoPainelSegurado /></SeguradoProvider>`, and `ConteudoPainelSegurado` (`:27-41`) renders `<SeletorSegurado />` followed by all 5 surfaces (`VisaoGeralSegurado`, `SuperficieAlertas`, `SuperficieApolice`, `SuperficieComunicados`, `SuperficieMeusDados`), each fed `seguradoId={seguradoAtivoId}` from `useSeguradoContexto()`. This file is itself unchanged since round 1 — only its caller changed.
- `src/frontend/src/App.test.tsx:200-230` ("`perfil Segurado: o seletor "Visualizar como" está alcançável e troca as superfícies (5.7)`") proves this end-to-end through the real UI, not just at the unit level: it renders the actual `<App/>` (no manual context injection), clicks the real `Visualizar como Segurado` profile-toggle button (the same one 1.4's pre-existing tests use), waits for the real nav to show `Visão geral`, then locates the combobox by its real accessible name `Visualizar como`, confirms `APOL-A` (segurado A's real apólice number, sourced through the real `PainelSegurado` → `SuperficieApolice` → mocked API chain) is shown, performs a real `selectOptions` on the live combobox to segurado B, and asserts `APOL-B` appears while `APOL-A` disappears. This is **not shallow or tautological**: it does not assert on internal state or call `PainelSegurado` directly — it drives the DOM the way a demo presenter would (profile toggle → nav → selector → cross-surface content change) and would fail if any link in that chain (`App.tsx`'s wiring, `PerfilContexto`, `SeguradoContexto`, `SeletorSegurado`, or `SuperficieApolice`'s prop wiring) were broken.
- No pre-existing `App.test.tsx` assertion was weakened or removed — confirmed by reading the full diff (`git diff 9ab6c0f..a57df76 -- src/frontend/src/App.test.tsx`): only new `vi.mock`/`vi.hoisted` entries, new `beforeEach` mock defaults, and one new `it(...)` block were added.

---

## Discrimination Sensor

Two independent sensor passes, both in isolated `git worktree`s (never `git stash`); real-tree `git status --porcelain` was empty before and after both.

### Round 1 mutations (on unchanged code — not re-run this round, results still valid since `SeguradoContexto.tsx` is untouched by the round-2 diff)

| Mutation | File:line | Description | Killed? |
| --- | --- | --- | --- |
| 1 | `src/frontend/src/contexto/SeguradoContexto.tsx:119` | Flipped late-response-discard guard | ✅ Killed (round 1) |
| 2 | `src/frontend/src/contexto/SeguradoContexto.tsx:132-134` | Applied failed id instead of reverting | ✅ Killed (round 1) |
| 3 | `src/frontend/src/contexto/SeguradoContexto.tsx:112` | Flipped same-id no-op guard | ✅ Killed (round 1) |

### Round 2 mutation (new — targets the round-2 diff itself, per the task instruction to confirm the new App-level test actually detects the regression it's meant to catch)

| Mutation | File:line | Description | Killed? |
| --- | --- | --- | --- |
| 4 | `src/frontend/src/App.tsx:41` (scratch worktree only) | Reverted `case 'visao-geral': return <PainelSegurado />` back to `return <VisaoGeralSegurado />` — i.e., re-introduced round 1's exact Blocker | ✅ Killed — `npx vitest run src/App.test.tsx` in the scratch worktree: 1 failed / 13 passed (14 total). The failure is exactly the new 5.7 reachability test, timing out at `screen.findByRole('combobox', { name: 'Visualizar como' })` (`App.test.tsx:223`) because the combobox never renders when `VisaoGeralSegurado` is mounted bare. All 13 other `App.test.tsx` tests still pass, confirming the failure is specific to this test, not collateral damage. |

**Isolation procedure**: `git worktree add <scratch> HEAD` (mutation 4), frontend `node_modules` symlinked in read-only (no real-tree write); real-tree `git status --porcelain` captured empty before sensor work, confirmed empty again after `git worktree remove --force <scratch>`.

**Sensor depth**: lightweight (4 mutations across both rounds combined; round 2 added exactly the 1 targeted mutation the task called for)
**Sensor outcome**: 4/4 killed across both rounds. The round-2 fix's own regression-detection is confirmed real: undoing the fix in isolation makes the new test fail, and only that test.

---

## Code Quality

| Principle | Status |
| --- | --- |
| Minimum code | ✅ — the fix is a 2-line functional change (`App.tsx` import + case) plus test additions; no unrelated files touched |
| Surgical changes | ✅ — `git diff 9ab6c0f..a57df76 --stat` touches exactly `App.tsx`, `App.test.tsx`, `tasks.md` |
| No scope creep | ✅ — no new features beyond mounting the existing, already-tested `PainelSegurado` |
| Matches existing patterns | ✅ — follows the exact same `case` structure already used for the other 3 surfaces in `SuperficieAtiva` |
| Spec-anchored outcome check (asserted values match spec) | ✅ — the new App-level assertions target concrete DOM outcomes (combobox present, apólice number changes/disappears), not vague "something renders" checks |
| Per-layer Coverage Expectation met | ✅ — this fix is integration/wiring-only; the 1:1 domain-logic and unit coverage was already established in round 1 and is unchanged |
| Every test maps to a spec requirement — no unclaimed tests | ✅ — the new test maps directly to SELETOR-01/02 (selector reachable, cross-surface switch works) |
| Documented guidelines followed | ✅ — none project-specific beyond `AGENTS.md`/`README.md` (cited in round 1), followed; hermetic mocking pattern matches the rest of `App.test.tsx` |

---

## Edge Cases

- [x] Selecionar o mesmo segurado já ativo é tratado como no-op — unchanged, `SeguradoContexto.test.tsx:82-94` (component level; now also reachable in the live app)
- [x] Seletor aberto sem segurado disponível explica a ausência — unchanged, `SeletorSegurado.test.tsx:106-119`
- [x] Resposta tardia de uma leitura em andamento é descartada — unchanged, covered at `SeguradoContexto.test.tsx:121-155` and exercised together by `PainelSegurado.test.tsx:159-194`; all now reachable in the live app

All three edge cases, previously correct only in isolation, are now reachable and exercised end-to-end via the real Segurado profile.

---

## Gate Check

- **Gate command (backend)**: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright`
- **Gate command (frontend)**: `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`
- **Gate outcome (backend)**: pytest 1095/1095 passed (128.15s), ruff "All checks passed!", pyright "0 errors, 0 warnings, 0 informations". Backend is untouched by the round-2 diff; this re-confirms no regression.
- **Gate outcome (frontend)**: `npm test -- --run` initially reported 1 failed / 440 passed because `src/funcionalidades/prontidao/SuperficieProntidao.test.tsx` (a fake-timer polling test, **unrelated to this feature** — not present in `git diff 9ab6c0f..a57df76`) is flaky. Re-run of that file alone: 10/10 passed. Full-suite re-run: **441/441 passed (46 files)**. `npm run lint` (oxlint): exit 0, only pre-existing warnings (`only-export-components`, `set-state-in-effect`) in files unrelated to this round's diff, none in `App.tsx`. `npm run build`: succeeded (`✓ built in 342ms`).
- **Test count before feature** (commit `2794f90`): backend 1091, frontend 418 (42 files)
- **Test count after round 1** (commit `9ab6c0f`): backend 1095, frontend 440 (46 files)
- **Test count after round 2** (commit `a57df76`): backend 1095 (unchanged — no backend files in this round's diff), frontend 441 (46 files, +1 new test: the 5.7 reachability test)
- **Delta (round 2 only)**: frontend +1, matches the single new `it(...)` block added to `App.test.tsx`. No test deleted, no assertion weakened — confirmed by reading the full diff.
- **Skipped tests**: none
- **Failures**: none (the single flaky failure on the first frontend run was confirmed non-reproducible and unrelated to this feature's diff by isolated re-run and full-suite re-run)

---

## Fix Plans

None — round 1's only Blocker (Gap 1) is closed and confirmed by direct code reading, a genuine end-to-end App-level test, and a targeted mutation that reproduces and is caught by exactly that test.

---

## Requirement Traceability Update

| Requirement | Previous Status (round 1) | New Status (round 2) |
| --- | --- | --- |
| SELETOR-01 | ❌ Needs Fix (component correct, unreachable) | ✅ Verified |
| SELETOR-02 | ❌ Needs Fix (component correct, unreachable) | ✅ Verified |
| SELETOR-03 | ❌ Needs Fix (component correct, unreachable) | ✅ Verified |
| SELETOR-04 | ❌ Needs Fix (component correct, unreachable) | ✅ Verified |
| SELETOR-05 | ❌ Needs Fix (component correct, unreachable) | ✅ Verified |
| SELETOR-06 | ✅ Verified (inherited from 1.4) | ✅ Verified |
| SELETOR-07 | ❌ Needs Fix (component correct, unreachable) | ✅ Verified |
| SELETOR-08 | ❌ Needs Fix (component correct, unreachable) | ✅ Verified |

---

## Summary

**Overall**: ✅ Ready

**Spec-anchored check**: 8/8 requirements correctly implemented, spec-precisely tested, and now reachable from the actual running application. 0 spec-precision gaps.
**Sensor**: 4/4 mutations killed across both rounds (3 from round 1 on unchanged core logic, 1 new this round targeting the fix itself — confirmed the new App-level test genuinely detects the round-1 regression if reintroduced).
**Gate**: backend 1095 passed / 0 failed; frontend 441 passed / 0 failed (1 unrelated flaky test confirmed non-reproducible); ruff/pyright/oxlint/build all clean.

**What works**: Everything round 1 already confirmed at the component level (`RepositorioSegurados.listar_sinteticos`, `GET /api/v1/segurados`, `SeguradoContexto`, `SeletorSegurado`, `PainelSegurado`'s own composition) — plus, as of this round, `PainelSegurado` is genuinely mounted and reachable from the live Segurado profile in `App.tsx`, proven by an end-to-end test that drives the real UI (profile toggle → nav → selector → cross-surface update) rather than asserting on internals.

**Issues found**: None this round.

**Next steps**: None required. Feature is done; round 1's L-079/L-080 candidate lessons remain as recorded (not re-added; no new grounded gap this round to distill).
