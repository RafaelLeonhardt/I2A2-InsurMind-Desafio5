# História 1.5: Consumir e inspecionar a API real — Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/1-5-consumir-e-inspecionar-a-api-real/design.md`
**Status**: Draft

---

## Test Coverage Matrix

> Generated from codebase sampling and project guidelines - confirm before Execute. Guidelines found: `AGENTS.md` (PT-BR docs/messages, OpenAPI-only frontend/backend integration, loopback-only) - no numeric coverage threshold stated, so strong defaults apply for depth.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| Backend OpenAPI export/snapshot (`openapi_export.py`, `openapi.json`) | none | Build/import gate only - pure serialization of `criar_aplicacao().openapi()`, exercised indirectly by the drift test | - | `uv run --directory src/backend pyright` |
| Backend OpenAPI drift + PT-BR + CORS (route/integration) | integration | Every `/api/v1` operation has PT-BR summary/description; snapshot matches live schema exactly; CORS allows configured origin and blocks another; `/docs`/`/openapi.json` return 200 | `src/backend/testes/test_openapi_sincronizado.py`, `src/backend/testes/test_cors.py` | `uv run --directory src/backend pytest` |
| Frontend build/config (`package.json` scripts) | none | Build gate only - verified by actually running the documented commands | - | `npm run build --prefix src/frontend` |
| Frontend generated types (`tipos-gerados.ts`) | none | Generated artifact; correctness enforced by `tsc -b` consuming it, not a hand-written test | - | `npm run build --prefix src/frontend` |
| Frontend HTTP client (`clienteHttp.ts`) | none | Thin `createClient` config wrapper; covered indirectly by `documentacaoApi.test.ts` mocking `fetch`, and by `tsc -b` | - | `npm run build --prefix src/frontend` |
| Frontend API service (`documentacaoApi.ts`) | unit | All branches: success, network failure, non-2xx - matching `contexto.test.ts`/`prontidao.test.ts` depth | `src/frontend/src/api/documentacaoApi.test.ts` | `npm test --prefix src/frontend -- --run` |
| Frontend component (`SuperficieDocumentacaoApi.tsx`) | unit (RTL) | Loading, disponível (with working link), indisponível (with causa + endereço) - matching `SuperficieProntidao.test.tsx` depth | `src/frontend/src/funcionalidades/documentacao-api/SuperficieDocumentacaoApi.test.tsx` | `npm test --prefix src/frontend -- --run` |
| Frontend context/nav/routing extension (`PerfilContexto.tsx`, `NavegacaoLateral.tsx`, `App.tsx`) | unit (RTL) | New surface reachable only from perfil Administrador - extends existing `PerfilContexto.test.tsx`/`NavegacaoLateral.test.tsx`/`App.test.tsx` | same 3 existing test files | `npm test --prefix src/frontend -- --run` |
| README / npm scripts wiring | none | Build gate only - verified by actually running the documented commands | - | manual command run during task |

**Coverage Expectation values** used above follow the strong default (no numeric guideline found): domain/service logic gets full-branch unit coverage 1:1 with spec ACs; route/integration layers cover happy + edge + error paths; generated/config-only artifacts get build-gate-only.

## Gate Check Commands

> Generated from `README.md`'s documented local verification commands - confirm before Execute.

| Gate Level | When to Use | Command |
| --- | --- | --- |
| Quick (backend) | After a backend-only task with new/changed tests | `uv run --directory src/backend pytest` |
| Quick (frontend) | After a frontend-only task with new/changed tests | `npm test --prefix src/frontend -- --run` |
| Full | After a task touching both backend and frontend, or wiring between them | `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright && npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend` |
| Build | After phase completion | Full gate command above, run once at the end of each phase |

---

## Execution Plan

Phases are ordered and run sequentially - each phase completes before the next begins, and tasks within a phase execute in order.

### Phase 1: Backend OpenAPI contract discipline

```
T1 → T2 → T3 → T4 → T5
```

### Phase 2: Frontend typed client foundation

```
T6 → T7 → T8
```

### Phase 3: "Documentação da API" surface

```
T9 → T10 → T11 → T12 → T13 → T14
```

### Phase 4: Docs and wiring

```
T15 → T16
```

---

## Task Breakdown

### T1: Create `openapi_export.py` export module

**What**: Add `gerar_documento_openapi(configuracao)` and `escrever_documento_openapi(caminho, documento)` functions, plus a `__main__` CLI entry writing to the default snapshot path, built on `criar_aplicacao`.
**Where**: `src/backend/central_preventiva/composicao/openapi_export.py`
**Depends on**: None
**Reuses**: `criar_aplicacao` (`src/backend/central_preventiva/composicao/api.py`), `obter_configuracao` (`src/backend/central_preventiva/composicao/configuracao.py`)
**Requirement**: API15-01

**Tools**: MCP: NONE / Skill: NONE

**Done when**:
- [x] `gerar_documento_openapi` returns `criar_aplicacao(configuracao).openapi()` unchanged
- [x] `escrever_documento_openapi` writes `json.dumps(documento, ensure_ascii=False, indent=2, sort_keys=True)` to the given path
- [x] `python -m central_preventiva.composicao.openapi_export` run manually writes a valid JSON file
- [x] `uv run --directory src/backend pyright` passes

**Tests**: none (per matrix)
**Gate**: quick (backend)

**Commit**: `feat(backend): expor exportador do documento OpenAPI`

---

### T2: Generate and commit the OpenAPI snapshot

**What**: Run T1's exporter with the project's default configuration and commit the resulting `openapi.json`.
**Where**: `src/backend/central_preventiva/composicao/openapi.json`
**Depends on**: T1
**Reuses**: T1's exporter
**Requirement**: API15-01

**Tools**: MCP: NONE / Skill: NONE

**Done when**:
- [x] `central_preventiva/composicao/openapi.json` exists, is valid JSON, and matches the current app's `.openapi()` output byte-for-byte
- [x] File is committed to version control

**Tests**: none (per matrix)
**Gate**: quick (backend)

**Commit**: `chore(backend): versionar o snapshot do documento OpenAPI`

---

### T3: Add the OpenAPI drift + PT-BR completeness test

**What**: Add `test_openapi_sincronizado.py` asserting the live app's `.openapi()` output equals the committed T2 snapshot, and that every `/api/v1` operation has a non-empty PT-BR `summary` and `description`.
**Where**: `src/backend/testes/test_openapi_sincronizado.py`
**Depends on**: T2
**Reuses**: `configuracao_para`/`cliente_para` helper pattern from `src/backend/testes/test_contexto_api.py:17-35`
**Requirement**: API15-01, API15-02, API15-04

**Tools**: MCP: NONE / Skill: NONE

**Done when**:
- [x] Test fails if a single character of a route's `summary`/`description` changes (verified manually during the task by a throwaway edit + revert)
- [x] Test asserts every `/api/v1` path's operations have non-empty PT-BR `summary` and `description`
- [x] `uv run --directory src/backend pytest` passes, test count increases by the number of new test functions added

**Tests**: integration
**Gate**: quick (backend)

**Commit**: `test(backend): travar o contrato OpenAPI com um snapshot versionado`

---

### T4: Close PT-BR summary/description gaps found by T3 (conditional)

**What**: For any `/api/v1` operation T3's test flags as missing or non-PT-BR `summary`/`description`, add it directly on the FastAPI route decorator; regenerate and recommit the T2 snapshot if any route text changed. Skip this task's commit entirely if T3 found zero gaps (existing routes already carry PT-BR text per the Design's codebase scan).
**Where**: `src/backend/central_preventiva/adaptadores/http/*.py` (only files with gaps)
**Depends on**: T3
**Reuses**: existing `summary`/`description` pattern already present in `contexto.py`, `dados_sinteticos.py`, `prontidao.py`, `saude.py`
**Requirement**: API15-02

**Tools**: MCP: NONE / Skill: NONE

**Done when**:
- [x] T3's drift/PT-BR test passes with zero gaps (confirmed: all existing routes already carry PT-BR `summary`/`description`; no route edits needed)
- [x] `uv run --directory src/backend pytest` passes

**Tests**: integration (extends T3's test, no new test file)
**Gate**: quick (backend)

**Commit**: `docs(backend): completar descricoes OpenAPI em portugues onde faltarem` (omit if T3 found zero gaps)

---

### T5: Add CORS + docs-availability boundary test

**What**: Add `test_cors.py` asserting the app returns `Access-Control-Allow-Origin: http://127.0.0.1:5173` for a request with that `Origin` header and not for `http://evil.example`; assert `GET /docs` and `GET /openapi.json` return `200`.
**Where**: `src/backend/testes/test_cors.py`
**Depends on**: T4
**Reuses**: `configuracao_para`/`cliente_para` pattern from `test_contexto_api.py`
**Requirement**: API15-05, API15-06, API15-07, API15-18, API15-19

**Tools**: MCP: NONE / Skill: NONE

**Done when**:
- [x] Test asserts CORS header present for the configured origin
- [x] Test asserts CORS header absent (or request rejected) for an unconfigured origin
- [x] Test asserts `GET /docs` and `GET /openapi.json` return `200`
- [x] `uv run --directory src/backend pytest` passes, test count increases by the number of new test functions added

**Tests**: integration
**Gate**: build (end of Phase 1: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright`)

**Commit**: `test(backend): validar fronteira de CORS e disponibilidade de docs via loopback`

---

### T6: Add `openapi-typescript`/`openapi-fetch` dependencies and npm scripts

**What**: Add `openapi-typescript` as a devDependency and `openapi-fetch` as a dependency in `src/frontend/package.json`; add npm scripts `gerar-tipos-api` (`openapi-typescript http://127.0.0.1:8000/openapi.json -o src/api/tipos-gerados.ts`) and `verificar-tipos-api` (regenerates to a temp file and diffs against the committed one, non-zero exit on mismatch).
**Where**: `src/frontend/package.json`
**Depends on**: None
**Reuses**: existing npm script conventions (`dev`, `build`, `test`)
**Requirement**: API15-09, API15-12

**Tools**: MCP: NONE / Skill: NONE

**Done when**:
- [x] `npm install --prefix src/frontend` succeeds with both packages present
- [x] Both scripts defined in `package.json`
- [x] Manually confirmed: running `gerar-tipos-api` with the backend down exits non-zero with a clear stderr message and writes no file

**Tests**: none (per matrix)
**Gate**: quick (frontend)

**Commit**: `build(frontend): adicionar openapi-typescript e openapi-fetch com scripts de geracao e verificacao`

---

### T7: Generate and commit `tipos-gerados.ts`

**What**: With the backend running locally (migrated + seeded per README), run `gerar-tipos-api` to produce `src/api/tipos-gerados.ts` and commit it.
**Where**: `src/frontend/src/api/tipos-gerados.ts`
**Depends on**: T6, T5 (needs the backend's real `/openapi.json`, which must already reflect the fully committed backend OpenAPI contract)
**Reuses**: T6's `gerar-tipos-api` script
**Requirement**: API15-09, API15-20

**Tools**: MCP: NONE / Skill: NONE

**Done when**:
- [x] `tipos-gerados.ts` committed and includes a `paths` type with `/api/v1/saude`
- [x] `npm run verificar-tipos-api --prefix src/frontend` passes against the current backend
- [x] Manually confirmed: editing `tipos-gerados.ts` by hand and re-running `verificar-tipos-api` fails
- [x] `npm run build --prefix src/frontend` (`tsc -b`) passes

**Tests**: none (per matrix)
**Gate**: quick (frontend)

**Commit**: `feat(frontend): gerar tipos da API a partir do contrato OpenAPI`

---

### T8: Create `clienteHttp.ts` central typed client

**What**: Create `src/frontend/src/api/clienteHttp.ts` exporting `clienteApi = createClient<paths>({ baseUrl: 'http://127.0.0.1:8000' })` from `openapi-fetch`, importing `paths` from `./tipos-gerados`.
**Where**: `src/frontend/src/api/clienteHttp.ts`
**Depends on**: T7
**Reuses**: `paths` type from `tipos-gerados.ts`
**Requirement**: API15-10

**Tools**: MCP: NONE / Skill: NONE

**Done when**:
- [x] `clienteApi.GET('/api/v1/saude')` type-checks with an autocompleted, known response shape
- [x] `npm run build --prefix src/frontend` passes

**Tests**: none (per matrix - covered indirectly by T9's `documentacaoApi.test.ts`)
**Gate**: quick (frontend)

**Commit**: `feat(frontend): criar cliente HTTP central tipado a partir do contrato OpenAPI`

---

### T9: Create `documentacaoApi.ts` service

**What**: Create `verificarDocumentacaoApi()` calling `clienteApi.GET('/api/v1/saude')`, returning `{ estado: 'disponivel', enderecoSwaggerUi: 'http://127.0.0.1:8000/docs', enderecoOpenApi: 'http://127.0.0.1:8000/openapi.json' }` on success, and throwing `ErroDocumentacaoApi` (causa/impacto/proximaAcao/enderecoEsperado) on network failure or non-2xx, with a co-located test file covering all three branches.
**Where**: `src/frontend/src/api/documentacaoApi.ts`
**Depends on**: T8
**Reuses**: causa/impacto/proximaAcao error shape and mock-`fetch` test pattern from `src/frontend/src/api/contexto.ts`/`contexto.test.ts`
**Requirement**: API15-13, API15-14, API15-15, API15-16, API15-17

**Tools**: MCP: NONE / Skill: NONE

**Done when**:
- [x] Success path returns the expected `ResultadoDocumentacaoApi`
- [x] Network-failure path throws `ErroDocumentacaoApi` with non-empty causa/impacto/proximaAcao/enderecoEsperado
- [x] Non-2xx path throws `ErroDocumentacaoApi` with the same shape
- [x] `documentacaoApi.test.ts` created co-located with the module; `npm test --prefix src/frontend -- --run` passes, test count increases by at least 3

**Tests**: unit
**Gate**: quick (frontend)

**Commit**: `feat(frontend): criar servico de verificacao de disponibilidade da documentacao da API`

---

### T10: Create `SuperficieDocumentacaoApi.tsx` component

**What**: Render carregando/disponível/indisponível based on `verificarDocumentacaoApi()` called in a `useEffect` on mount; disponível shows both local addresses and a `target="_blank" rel="noopener noreferrer"` link to `/docs`; indisponível shows causa, impacto, próxima ação, and the expected address; no fixed placeholder response content before the first real response resolves. Includes a co-located test file covering the 3 states.
**Where**: `src/frontend/src/funcionalidades/documentacao-api/SuperficieDocumentacaoApi.tsx`
**Depends on**: T9
**Reuses**: fetch-on-mount + state pattern and RTL test pattern from `src/frontend/src/funcionalidades/prontidao/SuperficieProntidao.tsx`/`.test.tsx`
**Requirement**: API15-14, API15-15, API15-16, API15-17

**Tools**: MCP: NONE / Skill: NONE

**Done when**:
- [ ] Component shows a loading state before the first response
- [ ] Component shows "Disponível" with both addresses and a working `target="_blank"`/`rel="noopener noreferrer"` link on success
- [ ] Component shows "Indisponível" with causa/impacto/próxima ação/endereço esperado on failure
- [ ] No literal example API response value appears anywhere in the component's default/placeholder render
- [ ] `SuperficieDocumentacaoApi.test.tsx` created co-located with the component; `npm test --prefix src/frontend -- --run` passes, test count increases by at least 3

**Tests**: unit (RTL)
**Gate**: quick (frontend)

**Commit**: `feat(frontend): criar superficie Documentacao da API`

---

### T11: Add `'documentacao-api'` to `PerfilContexto`

**What**: Add `'documentacao-api'` to the `Superficie` union and to `SUPERFICIES_POR_PERFIL.administrador` (not `segurado`) in `PerfilContexto.tsx`.
**Where**: `src/frontend/src/contexto/PerfilContexto.tsx`
**Depends on**: T10
**Reuses**: existing `Superficie` union, `SUPERFICIES_POR_PERFIL` pattern
**Requirement**: API15-13

**Tools**: MCP: NONE / Skill: NONE

**Done when**:
- [ ] `'documentacao-api'` is a valid `Superficie` value, present only in `SUPERFICIES_POR_PERFIL.administrador`
- [ ] `PerfilContexto.test.tsx` extended with a case asserting `'documentacao-api'` is absent from `segurado`'s surfaces
- [ ] `npm test --prefix src/frontend -- --run` passes, test count increases by at least 1

**Tests**: unit (RTL) - extends existing test file
**Gate**: quick (frontend)

**Commit**: `feat(frontend): adicionar documentacao-api ao perfil Administrador`

---

### T12: Add nav entry to `NavegacaoLateral`

**What**: Add an icon and the label `'Documentação da API'` for `'documentacao-api'` in `NavegacaoLateral.tsx`.
**Where**: `src/frontend/src/componentes/NavegacaoLateral.tsx`
**Depends on**: T11
**Reuses**: existing `ROTULOS`/`IconeSuperficie` pattern
**Requirement**: API15-13

**Tools**: MCP: NONE / Skill: NONE

**Done when**:
- [ ] Nav item renders for `'documentacao-api'` with a label and icon, following the existing pattern
- [ ] `NavegacaoLateral.test.tsx` extended with a case asserting the item renders for the Administrador profile
- [ ] `npm test --prefix src/frontend -- --run` passes, test count increases by at least 1

**Tests**: unit (RTL) - extends existing test file
**Gate**: quick (frontend)

**Commit**: `feat(frontend): adicionar item de navegacao Documentacao da API`

---

### T13: Wire `SuperficieAtiva` in `App.tsx`

**What**: Add a `case 'documentacao-api': return <SuperficieDocumentacaoApi />` branch to `App.tsx`'s `SuperficieAtiva`.
**Where**: `src/frontend/src/App.tsx`
**Depends on**: T12
**Reuses**: existing `switch` pattern in `SuperficieAtiva`
**Requirement**: API15-13

**Tools**: MCP: NONE / Skill: NONE

**Done when**:
- [ ] Selecting `'documentacao-api'` renders `SuperficieDocumentacaoApi`
- [ ] `App.test.tsx` extended with a case navigating to the new surface and asserting it renders
- [ ] `npm test --prefix src/frontend -- --run` passes, test count increases by at least 1

**Tests**: unit (RTL) - extends existing test file
**Gate**: full (end of the wiring sub-sequence: full backend + frontend gate)

**Commit**: `feat(frontend): renderizar a superficie Documentacao da API na navegacao`

---

### T14: Manual end-to-end confirmation (backend up / backend down)

**What**: With the backend built per README (`inicializador`, then `servidor`), open the frontend, navigate to "Documentação da API" as Administrador, confirm "Disponível" + working `/docs` link; stop the backend, reload, confirm "Indisponível" with causa and expected address.
**Where**: N/A (manual verification step; any defect found is fixed under the task it belongs to, not here)
**Depends on**: T13
**Reuses**: README's documented local run commands
**Requirement**: API15-13, API15-14, API15-15, API15-16, API15-17

**Tools**: MCP: `mcp__Claude_Browser__*` (preview_start, navigate, computer, read_page) / Skill: NONE

**Done when**:
- [ ] Evidence (read_page/screenshot): "Disponível" state with working `/docs` link, backend running
- [ ] Evidence (read_page/screenshot): "Indisponível" state with causa and expected address, backend stopped
- [ ] No regression observed in other surfaces (Prontidão, Restaurar dados sintéticos, Visão geral) while backend was toggled

**Tests**: none (manual verification; a defect found is fixed under its owning task, not as a new task)
**Gate**: none (manual step)

**Commit**: none (no code change if verification passes cleanly)

---

### T15: Document commands in README

**What**: Update `README.md`'s "Execução local" section: (a) the OpenAPI snapshot regeneration command and the Swagger UI address, (b) the `gerar-tipos-api`/`verificar-tipos-api` commands with a note that the backend must be running.
**Where**: `README.md`
**Depends on**: T14
**Reuses**: existing README command-block style
**Requirement**: API15-08, API15-11, API15-20

**Tools**: MCP: NONE / Skill: NONE

**Done when**:
- [ ] README lists the OpenAPI snapshot regeneration command
- [ ] README lists `npm run gerar-tipos-api` and `npm run verificar-tipos-api` with the backend-running note
- [ ] README states the Swagger UI address (`http://127.0.0.1:8000/docs`)
- [ ] Every command listed was actually run successfully during this task

**Tests**: none (documentation)
**Gate**: build (full gate)

**Commit**: `docs: registrar comandos de documentacao e sincronizacao de tipos da API`

---

### T16: Full-suite regression gate

**What**: Run the complete gate check command once more on the final branch state to confirm no cross-task regression.
**Where**: N/A (verification only)
**Depends on**: T15
**Reuses**: Gate Check Commands table above
**Requirement**: API15-01 through API15-20 (full-story regression check)

**Tools**: MCP: NONE / Skill: NONE

**Done when**:
- [ ] `uv run --directory src/backend pytest` passes, full count reported
- [ ] `uv run --directory src/backend ruff check .` passes
- [ ] `uv run --directory src/backend pyright` passes
- [ ] `npm test --prefix src/frontend -- --run` passes, full count reported
- [ ] `npm run lint --prefix src/frontend` passes
- [ ] `npm run build --prefix src/frontend` passes

**Tests**: none (aggregate gate run)
**Gate**: build

**Commit**: none (verification only; a regression fix lands as a new commit under the task that introduced it)

---

## Phase Execution Map

```
Phase 1 → Phase 2 → Phase 3 → Phase 4

Phase 1:  T1 ------→ T2 ------→ T3 ------→ T4 ------→ T5
Phase 2:  T6 ------→ T7 ------→ T8
Phase 3:  T9 ------→ T10 ------→ T11 ------→ T12 ------→ T13 ------→ T14
Phase 4:  T15 ------→ T16

Cross-phase dependencies (in addition to the intra-phase chains above):
T5 ------→ T7
T8 ------→ T9
T14 ------→ T15
```

Execution is strictly sequential - there is no intra-phase parallelism. A single agent (or batch worker) works one task at a time, in order.

16 tasks total → exceeds the single-batch budget (~7-8), so this qualifies for the sub-agent offer at Execute time. Natural split at phase boundaries: Batch 1 = Phase 1 + Phase 2 (8 tasks), Batch 2 = Phase 3 + Phase 4 (8 tasks).

---

## Task Granularity Check

| Task | Scope | Status |
| --- | --- | --- |
| T1: `openapi_export.py` | 1 file | ✅ Granular |
| T2: commit snapshot | 1 file (generated artifact) | ✅ Granular |
| T3: drift + PT-BR test | 1 file | ✅ Granular |
| T4: PT-BR gap-filling | Bounded to "only files with gaps" - conditionally empty | ✅ Granular |
| T5: CORS test | 1 file | ✅ Granular |
| T6: deps + npm scripts | 1 file (`package.json`) | ✅ Granular |
| T7: commit generated types | 1 file (generated artifact) | ✅ Granular |
| T8: `clienteHttp.ts` | 1 file | ✅ Granular |
| T9: `documentacaoApi.ts` + co-located test | 1 module + its own test file (co-located tests, not a separate task per skill rules) | ✅ Granular |
| T10: `SuperficieDocumentacaoApi.tsx` + co-located test | 1 component + its own test file | ✅ Granular |
| T11: `PerfilContexto.tsx` | 1 file | ✅ Granular |
| T12: `NavegacaoLateral.tsx` | 1 file | ✅ Granular |
| T13: `App.tsx` | 1 file | ✅ Granular |
| T14: manual E2E | 0 files (verification) | ✅ Granular |
| T15: README | 1 file | ✅ Granular |
| T16: regression gate | 0 files (verification) | ✅ Granular |

---

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| --- | --- | --- | --- |
| T1 | None | (start of Phase 1) | ✅ Match |
| T2 | T1 | T1 → T2 | ✅ Match |
| T3 | T2 | T2 → T3 | ✅ Match |
| T4 | T3 | T3 → T4 | ✅ Match |
| T5 | T4 | T4 → T5 | ✅ Match |
| T6 | None | (start of Phase 2) | ✅ Match |
| T7 | T6, T5 | T6 → T7 (Phase 2 internal); cross-phase dependency on T5 satisfied because Phase 1 fully completes before Phase 2 starts | ✅ Match |
| T8 | T7 | T7 → T8 | ✅ Match |
| T9 | T8 | (start of Phase 3) - cross-phase dependency on T8 satisfied since Phase 2 completes before Phase 3 | ✅ Match |
| T10 | T9 | T9 → T10 | ✅ Match |
| T11 | T10 | T10 → T11 | ✅ Match |
| T12 | T11 | T11 → T12 | ✅ Match |
| T13 | T12 | T12 → T13 | ✅ Match |
| T14 | T13 | T13 → T14 | ✅ Match |
| T15 | T14 | (start of Phase 4) - cross-phase dependency on T14 satisfied since Phase 3 completes before Phase 4 | ✅ Match |
| T16 | T15 | T15 → T16 | ✅ Match |

No task depends on a later-phase task; all dependencies point backward or within the same phase.

---

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| --- | --- | --- | --- | --- |
| T1: `openapi_export.py` | Backend export module | none | none | ✅ OK |
| T2: commit snapshot | Backend export/snapshot | none | none | ✅ OK |
| T3: drift + PT-BR test | Backend route/integration | integration | integration | ✅ OK |
| T4: PT-BR gap-filling | Backend route/integration (extends T3's test) | integration | integration | ✅ OK |
| T5: CORS test | Backend route/integration | integration | integration | ✅ OK |
| T6: deps + npm scripts | Frontend build/config | none | none | ✅ OK |
| T7: commit generated types | Frontend generated types | none | none | ✅ OK |
| T8: `clienteHttp.ts` | Frontend HTTP client (thin wrapper) | none | none | ✅ OK |
| T9: `documentacaoApi.ts` | Frontend API service | unit | unit | ✅ OK |
| T10: `SuperficieDocumentacaoApi.tsx` | Frontend component | unit (RTL) | unit (RTL) | ✅ OK |
| T11: `PerfilContexto.tsx` | Frontend context/nav extension | unit (RTL) | unit (RTL) | ✅ OK |
| T12: `NavegacaoLateral.tsx` | Frontend context/nav extension | unit (RTL) | unit (RTL) | ✅ OK |
| T13: `App.tsx` | Frontend context/nav extension | unit (RTL) | unit (RTL) | ✅ OK |
| T14: manual E2E | N/A (verification) | N/A | none | ✅ OK |
| T15: README | N/A (documentation) | none | none | ✅ OK |
| T16: regression gate | N/A (verification) | N/A | none | ✅ OK |

No violations. `Tests: none` is used only where the matrix says `none` for that layer, or where the task is explicitly a non-code verification/documentation step.
