# História 1.5: Consumir e inspecionar a API real — Validation

**Date**: 2026-08-29
**Spec**: `.specs/features/1-5-consumir-e-inspecionar-a-api-real/spec.md`
**Diff range**: `8cb7b3a..18470aa` (16 story commits `8f6759b`..`9fc278f`, plus fix commit `18470aa`)
**Verifier**: independent sub-agent (author ≠ verifier) — **re-verification pass (iteration 2)**, fresh independent re-derivation, not a spot-check of the prior report

---

## Task Completion

| Task | Status | Notes |
| --- | --- | --- |
| T1 | ✅ Done | `openapi_export.py` matches spec |
| T2 | ✅ Done | `openapi.json` snapshot committed |
| T3 | ✅ Done (post-fix) | Now also asserts per-*field* `description` (`test_todo_campo_dos_schemas_sob_api_v1_tem_description_em_portugues`), closing the prior gap |
| T4 | ✅ Done | Commit correctly skipped; the fix closed the field-level dimension T3 previously missed, so "zero gaps" now holds against the full API15-02 requirement |
| T5 | ✅ Done (post-fix) | CORS/loopback tests now also assert `Accept` in `access-control-allow-headers` and cover an `OPTIONS` preflight from a non-configured origin |
| T6 | ✅ Done | deps + scripts in `package.json` |
| T7 | ✅ Done | `tipos-gerados.ts` committed, includes `/api/v1/saude` |
| T8 | ✅ Done | `clienteHttp.ts` thin typed wrapper |
| T9 | ✅ Done | `documentacaoApi.ts` + co-located test, 3 branches |
| T10 | ✅ Done | `SuperficieDocumentacaoApi.tsx` + co-located test, 3 states |
| T11 | ✅ Done | `PerfilContexto.tsx` extended + tested |
| T12 | ✅ Done | `NavegacaoLateral.tsx` extended + tested |
| T13 | ✅ Done | `App.tsx` wired + tested |
| T14 | ✅ Done (per tasks.md; not re-run live by this pass) | Manual E2E evidence recorded in tasks.md; automated gates below independently re-confirm the same code paths |
| T15 | ✅ Done | README documents snapshot regen, `gerar-tipos-api`/`verificar-tipos-api`, Swagger UI address |
| T16 | ✅ Done | Full gate re-run independently below; backend count moved from 185→187 (the 2 fix-commit tests), frontend unchanged at 96 |

---

## Spec-Anchored Acceptance Criteria

### P1: Contrato OpenAPI fiel e documentado em PT-BR

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| API15-01: API SHALL expose `GET /openapi.json` from `criar_aplicacao`'s real routers | HTTP 200, JSON content-type | `src/backend/central_preventiva/composicao/openapi_export.py:13-16` (`gerar_documento_openapi` = `criar_aplicacao(configuracao).openapi()`) + `src/backend/testes/test_cors.py:93-101` — `assert resposta.status_code == 200; assert resposta.headers["content-type"].startswith("application/json")` | ✅ PASS |
| API15-02: doc SHALL contain `title`, `description`, per-operation `summary`, and PT-BR descriptions for **every field** and error response, for all of `/api/v1` | Non-empty PT-BR text for summary/description (operation-level), error-schema description, and **per-field property description** | `src/backend/testes/test_openapi_sincronizado.py:38-56` (operation summary/description), `:59-73` (schema-level `Problema*` description), **`:76-100`** (`test_todo_campo_dos_schemas_sob_api_v1_tem_description_em_portugues` — walks every `$ref`'d schema under `/api/v1` and every one of its `properties`, asserting non-empty `description`) | ✅ PASS — gap closed |
| API15-03: WHEN OpenAPI compared to `test_contexto_api.py`/`test_prontidao_api.py`/`test_dados_sinteticos_api.py`'s actually-executed contracts THEN `status_code`/`response_model`/error schemas SHALL match exactly | Exact match between documented and actually-served contracts | `src/backend/testes/test_openapi_sincronizado.py:29-35` (`assert documento_ao_vivo == snapshot`) proves the doc is generated live from `criar_aplicacao().openapi()` — the same route declarations (`response_model`, `status_code`, error schemas) that `test_contexto_api.py`/`test_prontidao_api.py`/`test_dados_sinteticos_api.py` exercise via `TestClient`. No test file directly cross-references those three test files' assertions against the OpenAPI doc | ⚠️ Spec-precision gap (satisfied by construction — same FastAPI source of truth — not by an explicit cross-file test). Re-independently judged: informational, non-blocking, consistent with the prior pass's call |
| API15-04: IF a test detects an endpoint/status/schema present in the running app but absent/divergent in `openapi.json` THEN suite SHALL fail, naming the divergent field | Non-zero exit / failing assertion on divergence | `src/backend/testes/test_openapi_sincronizado.py:35` — `assert documento_ao_vivo == snapshot` (pytest dict-diff names the divergent path/field). Empirically re-confirmed this pass by discrimination sensor Mutation 1 (killed) | ✅ PASS |

### P1: Swagger UI e OpenAPI acessíveis somente via loopback

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| API15-05: `GET /docs` SHALL return 200 | status 200 | `src/backend/testes/test_cors.py:85-90` — `assert resposta.status_code == 200` | ✅ PASS |
| API15-06: `GET /openapi.json` SHALL return 200 + JSON content-type | status 200, content-type JSON | `src/backend/testes/test_cors.py:93-101` | ✅ PASS |
| API15-07: server SHALL refuse bind outside `127.0.0.1`; story adds test proving `/docs`/`/openapi.json` respond on the configured host | `ValueError` on non-loopback host (pre-existing) + 200 on `127.0.0.1` for both routes | `src/backend/central_preventiva/composicao/configuracao.py:43-49` (`validar_host_api` raises `ValueError` unless `valor == "127.0.0.1"`) + `test_cors.py:14-21,85-101` (`configuracao_para` fixes `host_api="127.0.0.1"`, both routes exercised on it) | ✅ PASS |
| API15-08: README SHALL document command + address for Swagger UI | Command + `http://127.0.0.1:8000/docs` | `README.md:66` (`uv run --directory src/backend python -m central_preventiva.composicao.servidor`) + `README.md:70` ("Swagger UI interativa fica disponível em `http://127.0.0.1:8000/docs`") | ✅ PASS |

### P1: Cliente HTTP central tipado por `openapi-typescript`

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| API15-09: `openapi-typescript` devDep + `gerar-tipos-api` script reading `/openapi.json`, writing `tipos-gerados.ts` | Script defined exactly as described | `src/frontend/package.json:16` (`"gerar-tipos-api": "openapi-typescript http://127.0.0.1:8000/openapi.json -o src/api/tipos-gerados.ts"`), `:36` (`"openapi-typescript": "^7.13.0"` devDependency) | ✅ PASS |
| API15-10: `clienteHttp.ts` builds requests from generated types via `openapi-fetch`, no manual field redeclaration | Module exports a `createClient<paths>` instance | `src/frontend/src/api/clienteHttp.ts:1-7` (`createClient<paths>({ baseUrl: ENDERECO_BASE_API })`) | ✅ PASS |
| API15-11: IF `openapi.json` changes a field/type/status used by the surface and types aren't regenerated THEN `tsc -b` SHALL fail | Non-zero `tsc -b` exit | Structural guarantee: `documentacaoApi.ts:61` calls `clienteApi.GET('/api/v1/saude', { fetch })`, type-checked against `paths` imported from `tipos-gerados.ts` (`clienteHttp.ts:3`); a changed/removed path or field breaks this call at compile time. Not independently re-run via mutation this pass (frontend `tsc -b`/mutation of `tipos-gerados.ts` was covered in the prior pass and the mechanism is unchanged); `npm run build --prefix src/frontend` (`tsc -b`) passes cleanly against the current generated types | ✅ PASS (structural, consistent with prior pass) |
| API15-12: verification script/`npm test` SHALL include a check that committed `tipos-gerados.ts` is identical to a fresh regeneration | Non-zero exit on mismatch | `src/frontend/scripts/verificar-tipos-api.mjs:17-33` (regenerates to a temp dir, `readFileSync` + string compare, `process.exit(1)` on mismatch), wired as `npm run verificar-tipos-api` (`package.json:17`), documented in `README.md:83-84` | ✅ PASS |

### P1: Superfície "Documentação da API" sem dado fixo

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| API15-13: `'documentacao-api'` added to `Superficie` + `SUPERFICIES_POR_PERFIL.administrador`, own nav item | Present in Administrador's array, absent from Segurado's | `src/frontend/src/contexto/PerfilContexto.tsx:8,14` + test `PerfilContexto.test.tsx:133-136`; nav item `NavegacaoLateral.tsx:13,24` + test `NavegacaoLateral.test.tsx:20-27,39-43`; wired in `App.tsx:38-39` + test `App.test.tsx:86-95` | ✅ PASS |
| API15-14: WHEN surface opens THEN loading state shown until first `GET /api/v1/saude` response via the central client | `role="status"` visible pre-response, absent after | `SuperficieDocumentacaoApi.tsx:19,48` + test `SuperficieDocumentacaoApi.test.tsx:30-39` (`getByRole('status')` with pending promise, no "Disponível"/"Indisponível" text yet); typed call at `documentacaoApi.ts:61` | ✅ PASS |
| API15-15: WHEN success THEN "Disponível" + Swagger UI address + working new-tab link | Text "Disponível", `href="http://127.0.0.1:8000/docs"`, `target="_blank"`, `rel="noopener noreferrer"` | `SuperficieDocumentacaoApi.tsx:50-63` + test `SuperficieDocumentacaoApi.test.tsx:41-58` | ✅ PASS |
| API15-16: IF request fails THEN "Indisponível" + typed causa + expected address, no fixture data | Text "Indisponível" + non-empty causa/impacto/proximaAcao/enderecoEsperado | `SuperficieDocumentacaoApi.tsx:65-83` + test `SuperficieDocumentacaoApi.test.tsx:60-85` | ✅ PASS |
| API15-17: component SHALL use no fixed sample response value as default/placeholder | No literal example data before first real response | `SuperficieDocumentacaoApi.tsx:12-14` (`resultado`/`falha` initialized to `null`) + test `SuperficieDocumentacaoApi.test.tsx:36-38` | ✅ PASS |

### P2: Testes de contrato consolidados (CORS, erro, sincronia)

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| API15-18: WHEN OPTIONS/fetch from a non-configured origin THEN API SHALL refuse CORS (no matching `Access-Control-Allow-Origin`) | Header absent | `src/backend/testes/test_cors.py:38-43` (`GET` from wrong origin) **and** `:70-82` (`test_preflight_recusa_uma_origem_nao_configurada` — `OPTIONS` preflight from wrong origin, new) — both assert `"access-control-allow-origin" not in resposta.headers` | ✅ PASS — gap closed |
| API15-19: WHEN request from configured origin THEN API SHALL respond releasing `GET`, `POST`, `Accept`, `Content-Type`, `Idempotency-Key` | All five present in the applicable CORS response headers | `src/backend/testes/test_cors.py:46-67` — asserts `GET`/`POST` in `access-control-allow-methods`, and `content-type`/`idempotency-key`/**`accept`** (new, line 67) in `access-control-allow-headers` | ✅ PASS — gap closed |
| API15-20: test suite SHALL include a backend-side test that generates `openapi.json` live and fails on divergence from the versioned file | Failing assertion on divergence | `src/backend/testes/test_openapi_sincronizado.py:29-35`; empirically re-confirmed this pass via discrimination sensor Mutation 1 (killed) | ✅ PASS |

**Status**: ✅ All 20 ACs covered — 19/20 clean PASS, 1 spec-precision gap flagged (API15-03, informational, non-blocking, unchanged from the prior pass's independent judgment)

---

## Discrimination Sensor

Isolation: one temporary `git worktree` (scratch path under this session's scratchpad dir), created from `HEAD` (`18470aa`), never `git stash`. `.venv`/`node_modules` were symlinked into the worktree (read-only reuse of already-installed deps, not a write to the real tree) to avoid a slow reinstall; each mutation was applied, tested, then reverted with `git checkout --` inside the worktree before the next. Baseline `git status --porcelain` on the real tree captured before any sensor work and re-confirmed identical after `git worktree remove --force`.

| # | File:line | Description | Test run | Killed? |
| --- | --- | --- | --- | --- |
| 1 | `src/backend/central_preventiva/adaptadores/http/contexto.py:28` | `RespostaSeguradoPadrao.id` field `description` emptied (`Field(description="")`) | `uv run pytest testes/test_openapi_sincronizado.py` | ✅ Killed — both the drift test (dict mismatch) and the new `test_todo_campo_dos_schemas_sob_api_v1_tem_description_em_portugues` fail, pinpointing `RespostaSeguradoPadrao.id` |
| 2 | `src/backend/central_preventiva/composicao/api.py:34` | `allow_origins=[configuracao_ativa.origem_frontend]` → `allow_origins=["*"]` | `uv run pytest testes/test_cors.py` | ✅ Killed — 4 of 6 CORS tests fail, including the new `test_preflight_recusa_uma_origem_nao_configurada` (fix-commit test) |
| 3 | `src/frontend/src/api/documentacaoApi.ts:71` | `if (resultado.error \|\| !resultado.response.ok)` → `if (false)` (disabled the error branch) | `npx vitest run src/api/documentacaoApi.test.ts` | ✅ Killed — "rejeita com ErroDocumentacaoApi quando /api/v1/saude responde status não-2xx" fails (resolves instead of throwing) |
| 4 | `src/frontend/src/funcionalidades/documentacao-api/SuperficieDocumentacaoApi.tsx:57` | Removed `rel="noopener noreferrer" target="_blank"` from the Swagger UI link | `npx vitest run src/funcionalidades/documentacao-api/SuperficieDocumentacaoApi.test.tsx` | ✅ Killed — link-attribute assertions fail (`target` receives `null`) |
| 5 | `src/frontend/src/contexto/PerfilContexto.tsx:15` | `segurado: ['visao-geral']` → `segurado: ['visao-geral', 'documentacao-api']` (removed Administrador-only gating) | `npx vitest run src/contexto/PerfilContexto.test.tsx src/componentes/NavegacaoLateral.test.tsx` | ✅ Killed — both the `PerfilContexto` gating assertion and `NavegacaoLateral`'s "somente Visão geral" assertion fail |

**Sensor depth**: lightweight (default tier), 5 mutations — 2 targeting the fix commit's new coverage (API15-02 field descriptions, API15-18/19 CORS precision), 3 fresh mutations on previously-uncovered lines (frontend link attributes, Administrador-only gating)
**Result**: 5/5 killed — ✅ PASS

Note on mutation 2: Starlette's `CORSMiddleware` always safelists `Accept`/`Content-Type`/`Accept-Language`/`Content-Language` into the preflight `Access-Control-Allow-Headers` response regardless of the configured `allow_headers` list, so an app-level mutation that merely drops `"Accept"` from `allow_headers=[...]` cannot discriminate the new `Accept` assertion (verified: removing it from the list left the response header — and all tests — unchanged). The `allow_origins=["*"]` mutation above was used instead, which does discriminate the new `test_preflight_recusa_uma_origem_nao_configurada` test meaningfully. The `Accept` assertion itself is correct and matches the spec's required outcome; it is just not independently mutation-killable at the application-code level given the framework's built-in safelisting — this is a property of the dependency, not a weakness in the test.

Post-sensor isolation check: `git status --porcelain` on the real working tree after worktree removal matches the pre-sensor baseline exactly (5 untracked `.specs`/`.claude` files unrelated to this session's mutations, present before and after; confirmed via `diff`).

---

## Payload/Conjunction Rule Check

| Payload | Fields required together | Evidence | Result |
| --- | --- | --- | --- |
| `ErroDocumentacaoApi` (network failure) | causa, impacto, proximaAcao, enderecoEsperado all non-empty in the same assertion path | `documentacaoApi.test.ts:40-45` | ✅ PASS |
| `ErroDocumentacaoApi` (non-2xx) | same 4 fields | `documentacaoApi.test.ts:54-57` | ✅ PASS |
| Indisponível render (causa/impacto/proximaAcao/enderecoEsperado) | all 4 rendered together in the alert region | `SuperficieDocumentacaoApi.test.tsx:74-83` — `toHaveTextContent` for all 4 labels against the same `alerta` element | ✅ PASS |
| OpenAPI operation summary+description (PT-BR) | both non-empty together, per operation | `test_openapi_sincronizado.py:52-56` | ✅ PASS |
| OpenAPI schema-level error description | schema-level description present | `test_openapi_sincronizado.py:59-73` | ✅ PASS |
| OpenAPI per-field property description | every property under every `/api/v1`-referenced schema | `test_openapi_sincronizado.py:76-100` — collects ALL missing fields into one list and asserts the list is empty (conjunction across every schema/field pair, not first-failure-only) | ✅ PASS |
| CORS preflight liberated methods/headers | GET, POST, Accept, Content-Type, Idempotency-Key all asserted together | `test_cors.py:46-67` — single test, all 5 asserted in sequence within the same `it`-equivalent function | ✅ PASS |

---

## Edge Cases

- [x] `openapi-typescript` + backend down during `npm run gerar-tipos-api` fails clearly, doesn't overwrite `tipos-gerados.ts` — verified manually per T6's done-when (acceptable per Test Coverage Matrix: build-gate-only layer)
- [x] Surface opened while backend is initializing (schema pending) → shows "Indisponível" with causa, doesn't hang — collapses into the general failure path (`documentacaoApi.test.ts:48-58`, `SuperficieDocumentacaoApi.test.tsx:60-85`); correct, since FastAPI has no distinct "initializing" state
- [x] Swagger UI link opens in a new tab, doesn't navigate the SPA away — `SuperficieDocumentacaoApi.test.tsx:52-54` asserts `target="_blank"` + `rel="noopener noreferrer"`; independently re-confirmed discriminating via sensor Mutation 4

---

## Code Quality

| Principle | Status |
| --- | --- |
| Minimum code | ✅ |
| Surgical changes | ✅ — fix commit `18470aa` touches only the schemas needing `Field(description=...)` and the two test files, nothing else |
| No scope creep | ✅ — `contexto.ts`/`prontidao.ts`/`dadosSinteticos.ts` correctly left untouched, per Out of Scope |
| Matches patterns | ✅ — `Field(description=...)` matches the pre-existing pattern already used on `RespostaSaude` (`saude.py:18-19`); new CORS assertions match the existing lower-case header-substring style |
| Spec-anchored outcome check (asserted values match spec) | ✅ — 19/20 clean PASS, 1 spec-precision gap (API15-03, informational) |
| Per-layer Coverage Expectation met | ✅ — backend integration layer now covers operation-level, schema-level, AND field-level PT-BR descriptions (all three dimensions API15-02 names); CORS layer covers allow + deny for both plain and preflight requests |
| Every test maps to a spec requirement — no unclaimed tests | ✅ |
| Documented guidelines followed | `AGENTS.md` (PT-BR docs/messages, OpenAPI-only integration, loopback-only) — followed |

---

## Gate Check

- **Gate command**: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright && npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`
- **Result**: backend 187 passed / 0 failed; `ruff check .` clean; `pyright` 0 errors/0 warnings; frontend 96 passed / 0 failed (16 test files); `oxlint` — 0 errors, 4 pre-existing warnings unrelated to this feature (`react/only-export-components` on `PerfilContexto.tsx`, `react/set-state-in-effect` on `SuperficieDocumentacaoApi.tsx`/`BarraContexto.tsx`/`SuperficieProntidao.tsx`); `vite build` succeeded
- **Test count before this fix** (T16 baseline, `9fc278f`): 185 backend / 96 frontend
- **Test count after this fix** (`18470aa`, independently reproduced this session): 187 backend / 96 frontend
- **Delta**: +2 backend tests (`test_todo_campo_dos_schemas_sob_api_v1_tem_description_em_portugues`, `test_preflight_recusa_uma_origem_nao_configurada`); 0 frontend delta (fix commit is backend-only)
- **Skipped tests**: none observed
- **Failures**: none in the real working tree (all sensor-induced failures occurred in a discarded scratch worktree)

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
| --- | --- | --- |
| API15-01 | ✅ Verified | ✅ Verified |
| API15-02 | ❌ Needs Fix | ✅ Verified |
| API15-03 | ⚠️ Verified with spec-precision gap | ⚠️ Verified with spec-precision gap (unchanged, informational) |
| API15-04 | ✅ Verified | ✅ Verified |
| API15-05 | ✅ Verified | ✅ Verified |
| API15-06 | ✅ Verified | ✅ Verified |
| API15-07 | ✅ Verified | ✅ Verified |
| API15-08 | ✅ Verified | ✅ Verified |
| API15-09 | ✅ Verified | ✅ Verified |
| API15-10 | ✅ Verified | ✅ Verified |
| API15-11 | ✅ Verified | ✅ Verified |
| API15-12 | ✅ Verified | ✅ Verified |
| API15-13 | ✅ Verified | ✅ Verified |
| API15-14 | ✅ Verified | ✅ Verified |
| API15-15 | ✅ Verified | ✅ Verified |
| API15-16 | ✅ Verified | ✅ Verified |
| API15-17 | ✅ Verified | ✅ Verified |
| API15-18 | ⚠️ Verified with spec-precision gap | ✅ Verified |
| API15-19 | ⚠️ Verified with spec-precision gap | ✅ Verified |
| API15-20 | ✅ Verified | ✅ Verified |

---

## Summary

**Overall**: ✅ Ready

**Spec-anchored check**: 19/20 clean PASS, 1 spec-precision gap (API15-03, informational, non-blocking — same independent judgment as the prior pass)
**Sensor**: 5/5 mutations killed
**Gate**: 187 backend + 96 frontend passed, 0 failed; ruff/pyright/oxlint/build all clean

**What works**: Both gaps from the prior Verifier pass are independently confirmed closed: (1) `test_openapi_sincronizado.py` now walks every `/api/v1`-referenced schema's `properties` and fails if any lacks a PT-BR `description` — empirically killed by mutation 1; (2) `test_cors.py` now asserts `Accept` in the preflight `access-control-allow-headers` and adds a dedicated `OPTIONS`-from-wrong-origin refusal test — the latter empirically killed by mutation 2. The OpenAPI drift lock, loopback-only Swagger UI/`openapi.json` tests, the typed `openapi-fetch` client, `documentacaoApi.ts` (all 3 branches), `SuperficieDocumentacaoApi` (loading/disponível/indisponível, no fixture data, working new-tab link), Administrador-only gating, and the CORS allow/deny boundary are all genuinely test-backed and survived fresh, independently-designed fault injection in an isolated worktree this pass.

**Issues found**: None blocking. API15-03 remains a spec-precision note (no test file directly cross-references `test_contexto_api.py`/`test_prontidao_api.py`/`test_dados_sinteticos_api.py` against the OpenAPI doc; satisfied architecturally since they share the same FastAPI route source, not by an explicit empirical cross-check). No action required unless the project wants an explicit test for it.

**Next steps**: Feature is done. No further fix→re-verify iterations needed.
