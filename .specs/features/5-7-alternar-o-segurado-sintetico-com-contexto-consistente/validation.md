# História 5.7: Alternar o segurado sintético com contexto consistente — Validation

**Date**: 2026-09-06
**Spec**: `.specs/features/5-7-alternar-o-segurado-sintetico-com-contexto-consistente/spec.md`
**Diff range**: `2794f90..9ab6c0f` (b790553, a9edc13, 68adba3, 5a0269b, 9ab6c0f)
**Verifier**: independent sub-agent (author ≠ verifier)
**Result**: FAIL ❌ — see Gap 1 (integration/reachability); component-level logic and gate are clean, see Summary

---

## Task Completion

| Task | Status | Notes |
| --- | --- | --- |
| T1: `RepositorioSegurados.listar_sinteticos` | ✅ Done | `repositorio_segurados.py:56-62`; tested `test_repositorio_segurados.py:121-144` |
| T2: `GET /api/v1/segurados` | ✅ Done | `lista_segurados.py:41-72`; wired in `composicao/api.py`; `openapi.json` regenerated; `test_saude.py` path list updated |
| T3: `SeguradoContexto` (provider) | ✅ Done | `SeguradoContexto.tsx:84-146`; all branches unit-tested |
| T4: `SeletorSegurado` | ✅ Done | `SeletorSegurado.tsx:16-69`; keyboard/44px/disabled-reason tested |
| T5: Integração das 5 superfícies | ⚠️ Done per task checklist, but **not reachable in the running app** | `PainelSegurado.tsx` correctly composes context + 5 surfaces and is well component-tested (`PainelSegurado.test.tsx`), but is never mounted by `App.tsx`/`NavegacaoLateral`/`PerfilContexto` — see Gap 1 below. All items literally listed in T5's "Done when" are satisfied at the component level; the checklist itself never asked for app-level wiring, which is why this slipped past self-check. |

---

## Spec-Anchored Acceptance Criteria

### P1: Seletor "Visualizar como" sem ambiguidade de autenticação

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| WHEN a pessoa abrir o seletor demonstrativo no perfil Segurado ativo THEN a interface exibe só os sintéticos do seed, rotulado "Visualizar como", nunca login/autenticação | Lista mostra só segurados do seed; nenhum texto de login/senha/entrar | `src/frontend/src/funcionalidades/segurado/SeletorSegurado.test.tsx:35-44` — `expect(textoRenderizado).not.toMatch(/login\|senha\|entrar/i)`; `:46-58` — options list equals seed names | ✅ PASS at component level, but ❌ **unreachable in the live app** — see Gap 1. The precondition "no perfil Segurado ativo" never actually exposes this selector (`SUPERFICIES_POR_PERFIL.segurado` in `src/frontend/src/contexto/PerfilContexto.tsx:15` still lists only `['visao-geral']`; `src/frontend/src/App.tsx:41` renders bare `<VisaoGeralSegurado />`, not `<PainelSegurado />`). |

### P1: Troca consistente entre as cinco superfícies

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| WHEN outro segurado for selecionado e a transição terminar THEN as 5 superfícies refletem o mesmo segurado, sem dado persistido alterado | Todas as 5 mostram dado do novo segurado, nenhuma mistura | `PainelSegurado.test.tsx:159-194` — asserts `APOL-B`/`Assunto B`/unchecked checkbox appear and `Área Demo A`/`APOL-A`/`Assunto A` are all gone after the switch | ✅ PASS at component level / ❌ same reachability gap (Gap 1) |
| WHILE o novo contexto ainda carregando THEN `Contexto trocando` impede mistura, sem manter conteúdo anterior sob o novo nome | Nenhuma superfície muda de segurado antes da troca ser confirmada | `PainelSegurado.test.tsx:174-181` — while revalidation promise is unresolved, `queryByText('APOL-B')` is absent and `APOL-A` still shown; `SeletorSegurado.test.tsx:121-145` — select disabled with textual reason while `trocando` | ✅ PASS at component level / ❌ same reachability gap |
| IF falha ao carregar parte do novo contexto THEN bloqueia/reverte ao último contexto íntegro, com causa/impacto/próxima ação visíveis | `seguradoAtivoId` volta ao valor anterior; `falha` expõe as 3 campos | `SeguradoContexto.test.tsx:96-119` — `expect(result.current.seguradoAtivoId).toBe(SEGURADO_A.id)` after a rejected revalidation, `expect(result.current.falha).toEqual({ ocorrencia, impacto, proximaAcao })` | ✅ PASS (spec-precise) at component level / ❌ same reachability gap |

### P1: Ausência de ações administrativas e retorno seguro ao Administrador

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| WHEN qualquer superfície do Segurado for inspecionada THEN nenhum comando administrativo existe; endereço administrativo direto retorna ao contexto correto | Nenhum botão/link com nome "editar regra"/"gerar mensagem"/"aprovar lote"/"iniciar simulação" | `PainelSegurado.test.tsx:196-212` — iterates every button/link accessible name against the 4 forbidden patterns | ✅ PASS at component level / ❌ same reachability gap (irrelevant in practice today since the Segurado profile shows none of these 5 surfaces at all in the live app) |
| WHEN a pessoa voltar ao Administrador THEN as superfícies administrativas reaparecem, sem conceder/retirar autoridade | Perfil volta a listar `prontidao`/`restaurar-dados-sinteticos`/`documentacao-api` | `src/frontend/src/App.test.tsx:137-148` (1.4, unmodified) — reused guarantee, explicitly accepted by design.md/T5 as "sem teste dedicado nesta história" | ✅ PASS (inherited from 1.4, reasonable reuse) |

### P2: Acessibilidade do seletor

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| WHEN o seletor for operado por teclado THEN rótulo, opção ativa, foco e mudança são anunciados | Tab foca o campo; seleção anuncia "Visualizando como X" | `SeletorSegurado.test.tsx:60-77` | ✅ PASS at component level / ❌ same reachability gap |
| The control SHALL possuir alvo mínimo 44×44px e motivo textual quando desabilitado | Classe CSS com min 44px; texto do motivo visível quando desabilitado | `SeletorSegurado.test.tsx:93-119`, `:121-145`; CSS `SeletorSegurado.css` | ✅ PASS at component level / ❌ same reachability gap |

**Status**: ⚠️ All 8 requirements (SELETOR-01..08) are correctly implemented and spec-precisely tested **at the component/isolated level**, but **none are reachable from the actual running application** (Gap 1). This is the deciding factor for the overall verdict below.

---

## Discrimination Sensor

Sensor ran in an isolated `git worktree` (`git worktree add <scratch> HEAD`), frontend `node_modules` symlinked in (read-only reuse of the real tree's install, not a real-tree mutation). Real-tree `git status --porcelain` was empty before sensor work and empty again after `git worktree remove --force` — isolation confirmed.

| Mutation | File:line | Description | Killed? |
| --- | --- | --- | --- |
| 1 | `src/frontend/src/contexto/SeguradoContexto.tsx:119` | Flipped late-response-discard guard `if (token !== tokenAtualRef.current) return` → `if (token === tokenAtualRef.current) return` in `selecionar`'s success handler | ✅ Killed — 3 tests failed (`SeguradoContexto.test.tsx`, `PainelSegurado.test.tsx`) |
| 2 | `src/frontend/src/contexto/SeguradoContexto.tsx:132-134` | Added `definirSeguradoAtivoId(novoId)` inside the `.catch` handler, i.e. applying the failed id instead of reverting | ✅ Killed — 1 test failed (`SeguradoContexto.test.tsx:96-119`, "falha simulada ... reverte ao seguradoAtivoId anterior") |
| 3 | `src/frontend/src/contexto/SeguradoContexto.tsx:112` | Flipped the same-id no-op guard `if (novoId === seguradoAtivoId) return` → `if (novoId !== seguradoAtivoId) return` | ✅ Killed — 4 tests failed (`SeguradoContexto.test.tsx`) |

**Sensor depth**: lightweight (3 mutations, default tier)
**Sensor outcome**: 3/3 killed. The tests for `SeguradoContexto`'s core "no data mixing" guarantees (late-response discard, revert-on-failure, same-id no-op) are discriminating.

---

## Code Quality

| Principle | Status |
| --- | --- |
| Minimum code | ✅ |
| Surgical changes | ✅ — diff touches exactly the files needed; the 5 pre-existing surfaces were deliberately left untouched, reusing their existing `seguradoId` seam |
| No scope creep | ✅ |
| Matches existing patterns | ✅ — `SeguradoContexto` faithfully mirrors `PerfilContexto`'s provider/hook/`localStorage` shape |
| Spec-anchored outcome check (asserted values match spec) | ✅ — every assertion checked above targets the spec's precise expected value (exact id, exact falha fields, exact disabled reason text), not just "an assertion exists" |
| Per-layer Coverage Expectation met (domain 1:1 ACs; routes happy+edge+error) | ✅ — repository has 1:1 tests for `listar_sinteticos` (populated + empty seed); route has happy path + empty-seed path; `SeguradoContexto` covers every state branch |
| Every test maps to a spec requirement — no unclaimed tests | ✅ |
| Documented guidelines followed: [file(s) or "none - strong defaults applied"] | ✅ — `AGENTS.md`, `README.md`, and the 1.4 `PerfilContexto.test.tsx` floor cited in tasks.md's Test Coverage Matrix, followed |

**SPEC_DEVIATION judgment** (per tasks.md T5 / design.md "Implementado como"): The decision to introduce `PainelSegurado.tsx` as the single composition root instead of making each of the 5 pre-existing surfaces call `useSeguradoContexto()` directly is **sound and well-justified** — it avoids rewriting 5 already-passing test suites for a dependency seam that was deliberately built in 5.1–5.6 (`seguradoId?: string`), and the resulting component is itself correctly and thoroughly tested (`PainelSegurado.test.tsx`). **However, the deviation's own justification never addresses (and the implementation never delivers) the one thing that actually matters for the spec's User Stories: making the selector and the five-surfaces-together experience reachable by "a pessoa demonstradora."** `PainelSegurado` is composed correctly but composed *nowhere* — see Gap 1. The deviation is reasonable engineering; it does not, on its own, deliver the spec's ACs to an actual user of the running app.

---

## Edge Cases

- [x] Selecionar o mesmo segurado já ativo é tratado como no-op — `SeguradoContexto.test.tsx:82-94` (asserts `getListaSeguradosMock` called exactly once, state stays `ocioso`)
- [x] Seletor aberto sem segurado disponível explica a ausência — `SeletorSegurado.test.tsx:106-119`
- [x] Resposta tardia de uma leitura em andamento (ex.: Alertas) é descartada, nunca aplicada ao novo contexto — covered at two levels: `SeguradoContexto.test.tsx:121-155` (context's own list-revalidation race) and each of the 5 surfaces' own pre-existing `requisicaoAtualRef`/token guard (confirmed by reading `VisaoGeralSegurado.tsx:68-90`, unchanged from 5.1–5.6), exercised together by `PainelSegurado.test.tsx:159-194`

All three edge cases are correctly handled in isolation; all three share Gap 1's reachability caveat.

---

## Gate Check

- **Gate command (backend)**: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright`
- **Gate command (frontend)**: `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`
- **Gate outcome**: all green — pytest 1095/1095 passed, ruff "All checks passed!", pyright "0 errors, 0 warnings, 0 informations"; vitest 440/440 passed (46 files), oxlint exit 0 (pre-existing warnings only, none introduced by files new to this feature beyond the same `react(only-export-components)` pattern `PerfilContexto.tsx` already carries), `npm run build` succeeded.
- **Test count before feature** (commit `2794f90`): backend 1091, frontend 418 (42 files)
- **Test count after feature** (commit `9ab6c0f`): backend 1095, frontend 440 (46 files)
- **Delta**: backend +4 (2 in `test_lista_segurados_api.py`, 2 in `test_repositorio_segurados.py`) — matches new test files exactly; frontend +22 (4 in `listaSegurados.test.ts`, 8 in `SeguradoContexto.test.tsx`, 3 in `PainelSegurado.test.tsx`, 7 in `SeletorSegurado.test.tsx`) — matches new test files exactly. No reduction, no weakened assertions detected.
- **Skipped tests**: none
- **Failures**: none

---

## Fix Plans

### Fix 1: Wire `PainelSegurado` (and therefore `SeletorSegurado`/`SeguradoContexto`) into the actual running application

- **Root cause**: `src/frontend/src/App.tsx` and `src/frontend/src/contexto/PerfilContexto.tsx` were never touched by this feature. `PerfilContexto.tsx:15` still defines `SUPERFICIES_POR_PERFIL.segurado = ['visao-geral']` (the single surface from before Épico 1 Story 1.4/5.1), and `App.tsx`'s `SuperficieAtiva()` switch (`case 'visao-geral': return <VisaoGeralSegurado />`, line 41) renders `VisaoGeralSegurado` bare — no `SeguradoProvider`, no `seguradoId` prop, so it silently falls back to `getSeguradoPadrao()`, exactly the pre-5.7 behavior the spec's Problem Statement says this story must replace. There is no router and no alternate entry point (`main.tsx` mounts `<App/>` directly) — `PainelSegurado` is imported nowhere outside its own file and its own test. `src/frontend/src/App.test.tsx:122-135` still explicitly asserts "Segurado profile shows only Visão geral," confirming this is the actual, currently-tested behavior of the shipped app, not an oversight in a stale test.
- **Fix task**: Replace (or extend) the Segurado-profile render path to mount `<PainelSegurado />` instead of (or alongside) the bare `<VisaoGeralSegurado />`, and update `SUPERFICIES_POR_PERFIL`/`NavegacaoLateral`/`App.test.tsx` accordingly so a demo presenter can actually reach the "Visualizar como" selector and see all 5 surfaces follow it.
  - **Where**: `src/frontend/src/App.tsx` (`SuperficieAtiva`), `src/frontend/src/contexto/PerfilContexto.tsx` (`Superficie` type / `SUPERFICIES_POR_PERFIL`), `src/frontend/src/componentes/NavegacaoLateral.tsx` (`ROTULOS`/icons, if new nav entries are introduced), `src/frontend/src/App.test.tsx` (update the now-stale "somente Visão geral" assertions)
  - **Verify**: an `App.test.tsx` (or new) test renders `<App/>`, switches to the Segurado profile, and asserts the "Visualizar como" combobox is present and that switching it updates visible content from more than one surface
  - **Done when**: A demo presenter navigating the live app to the Segurado profile can open "Visualizar como," switch segurado, and observe the change reflected without a full page reload
- **Priority**: Blocker

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
| --- | --- | --- |
| SELETOR-01 | Implementing | ❌ Needs Fix (component correct, unreachable) |
| SELETOR-02 | Implementing | ❌ Needs Fix (component correct, unreachable) |
| SELETOR-03 | Implementing | ❌ Needs Fix (component correct, unreachable) |
| SELETOR-04 | Implementing | ❌ Needs Fix (component correct, unreachable) |
| SELETOR-05 | Implementing | ❌ Needs Fix (component correct, unreachable) |
| SELETOR-06 | Implementing | ✅ Verified (inherited from 1.4, genuinely reachable via the Administrador↔Segurado toggle) |
| SELETOR-07 | Implementing | ❌ Needs Fix (component correct, unreachable) |
| SELETOR-08 | Implementing | ❌ Needs Fix (component correct, unreachable) |

---

## Summary

**Overall**: ❌ Not Ready

**Spec-anchored check**: 8/8 requirements correctly implemented and spec-precisely tested at the component/isolated level; 0 spec-precision gaps. But 7/8 (all except the inherited SELETOR-06) are unreachable in the actual running application.
**Sensor**: 3/3 mutations killed — the isolated logic is genuinely well-tested, not just superficially covered.
**Gate**: backend 1095 passed / 0 failed; frontend 440 passed / 0 failed; ruff/pyright/oxlint/build all clean.

**What works**: `RepositorioSegurados.listar_sinteticos` + `GET /api/v1/segurados` (backend, fully correct and tested); `SeguradoContexto` (React provider — `localStorage` persistence, `trocando`/`erro` states, revert-on-failure, late-response-discard by token, same-id no-op) — all correct and discriminated by the sensor; `SeletorSegurado` (accessible, correctly labeled, 44px target, textual disabled reasons); `PainelSegurado` (correctly composes context + the 5 pre-existing surfaces, proven not to mix data across a switch, in isolation).

**Issues found**:
- **Gap 1 (Blocker)**: None of the above is reachable from the actual running application. `App.tsx`/`PerfilContexto.tsx`/`NavegacaoLateral.tsx` were never updated to mount `PainelSegurado`; the Segurado profile in the live app still renders the same single, hardcoded-default `VisaoGeralSegurado` it rendered before this feature started. The SPEC_DEVIATION note in `tasks.md`/`design.md` correctly justifies *why* a new composition root (`PainelSegurado`) was chosen over touching the 5 existing files, but never addresses (and the implementation never delivers) wiring that root into the app a demo presenter actually uses. How to fix: see Fix Plan 1 above.

**Next steps**: Route Fix 1 back to an implementer (fix→re-verify loop, iteration 1 of the 3-round bound). Re-run this Verifier once `App.tsx`/`PerfilContexto.tsx`/`NavegacaoLateral.tsx`/`App.test.tsx` are updated to actually mount and reach `PainelSegurado` from the Segurado profile.
