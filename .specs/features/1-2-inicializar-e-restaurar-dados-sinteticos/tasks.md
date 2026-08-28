# Inicializar e Restaurar Dados Sintéticos Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/1-2-inicializar-e-restaurar-dados-sinteticos/design.md`
**Status**: Draft

---

## Test Coverage Matrix

> Generated from codebase sampling (`test_camadas.py`, `test_configuracao.py`, `test_saude.py`, `test_servidor.py`, `App.test.tsx`) and the strong default (no coverage-threshold guideline file found; `AGENTS.md` sets PT-BR/synthetic-data/loopback conventions but no numeric coverage target). Existing tests are thorough (multi-scenario, error-sanitization, accessibility) and set the floor for this feature's tests, not a ceiling.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| Domínio (`dominio/estados_execucao.py`) | unit | All branches; 1:1 to spec ACs | `src/backend/testes/test_estados_execucao.py` | `uv run --directory src/backend pytest` |
| Aplicação — casos de uso (`aplicacao/inicializacao.py`, `aplicacao/restauracao.py`) | unit (fake ports, per project convention) | All branches; 1:1 to spec ACs incl. every listed edge case | `src/backend/testes/test_inicializacao.py`, `test_restauracao.py` | `uv run --directory src/backend pytest` |
| Aplicação — portas/DTOs (`aplicacao/portas_persistencia.py`) | none | Interfaces/exceptions only, no behavior — build gate only | `src/backend/central_preventiva/aplicacao/portas_persistencia.py` | `uv run --directory src/backend pyright` |
| Adaptadores/persistência (`migracoes.py`, `semeador.py`, `repositorio_execucoes.py`, `repositorio_idempotencia.py`, `conexao.py`) | integration (real tmp-path DuckDB) | Key transaction paths + every listed edge case (future version, mid-sequence failure/resume, restore rollback) | `src/backend/testes/test_migracoes.py`, `test_semeador.py`, `test_repositorio_execucoes.py`, `test_repositorio_idempotencia.py`, `test_conexao.py` | `uv run --directory src/backend pytest` |
| Adaptadores/api (`adaptadores/api/dados_sinteticos.py`) | e2e (`fastapi.testclient.TestClient`, matches `test_saude.py`'s pattern) | All routes: happy + every listed edge/error path | `src/backend/testes/test_dados_sinteticos_api.py` | `uv run --directory src/backend pytest` |
| Composição (`configuracao.py` extension, `inicializador.py`, `servidor.py` extension) | integration | Key paths + error handling — matches existing `test_configuracao.py`/`test_servidor.py` floor | `src/backend/testes/test_configuracao.py`, `test_inicializador.py`, `test_servidor.py` | `uv run --directory src/backend pytest` |
| Frontend — componentes (`componentes/Modal.tsx`) | unit (React Testing Library) | All interaction branches: open/confirm/cancel, focus trap, `Esc`, focus return | `src/frontend/src/componentes/*.test.tsx` | `npm test --prefix src/frontend -- --run` |
| Frontend — api (`api/dadosSinteticos.ts`) | unit (mocked `fetch`) | Success + every error/edge path (409, 422, network failure) | `src/frontend/src/api/*.test.ts` | `npm test --prefix src/frontend -- --run` |
| Frontend — funcionalidades (`funcionalidades/dados-sinteticos/RestaurarDemonstracao.tsx`) | integration (RTL) | Happy path + every listed UI state (`Confirmação`/`Restaurando`/`Concluído`/`Falha`) | `src/frontend/src/funcionalidades/**/*.test.tsx` | `npm test --prefix src/frontend -- --run` |

## Gate Check Commands

> Generated from `README.md`'s documented "Execução local" commands — confirm before Execute.

| Gate Level | When to Use | Command |
| --- | --- | --- |
| Quick | After tasks with unit tests only | Backend: `uv run --directory src/backend pytest` · Frontend: `npm test --prefix src/frontend -- --run` |
| Full | After tasks with integration/e2e tests | Backend: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright` · Frontend: `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend` |
| Build | After phase completion or config/entity-only tasks | Backend: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright` · Frontend: `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend` |

---

## Execution Plan

Phases are ordered and run sequentially - each phase completes before the next begins, and tasks within a phase execute in order.

### Phase 1: Foundation

```
T1 → T2
```

T3 and T4 have no dependency on T1/T2/each other; executed in listed order within the phase (T1, T2, T3, T4).

### Phase 2: Persistence core

```
T5
T6
T7
T8
```

No dependency among T5-T8 themselves (each depends on T4/T5 from Phase 1 - see the full edge list in Phase Execution Map below); executed in listed order within the phase.

### Phase 3: Application use cases

```
T9
T10
```

No dependency between T9 and T10 (both depend only on T2); executed in listed order within the phase.

### Phase 4: API and composition wiring

```
T11
T12
T13
```

No dependency among T11-T13 themselves; executed in listed order within the phase.

### Phase 5: Frontend

```
T14
T15
```

```
T14 → T16
T15 → T16
```

T14 and T15 have no dependency on each other; T16 depends on both.

---

## Task Breakdown

### T1: Criar o enum canônico de estados de execução

**What**: `EstadoExecucao` (`StrEnum`, 12 states from `ARCHITECTURE-SPINE.md` AD-4), `ESTADOS_TERMINAIS: frozenset[EstadoExecucao]`, `eh_terminal(estado) -> bool`.
**Where**: `src/backend/central_preventiva/dominio/estados_execucao.py`
**Depends on**: None
**Reuses**: none (first domain module)
**Requirement**: SEED-10

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] All 12 states from AD-4's canonical diagram are present with matching names (AD-4's diagram actually defines **13** distinct states; all 13 implemented, matching `design.md`'s enumerated list)
- [x] `ESTADOS_TERMINAIS` contains exactly `falhou_coleta`, `sem_risco`, `sem_elegiveis`, `falhou_preparacao_ia`, `falhou_simulacao`, `concluida`
- [x] `eh_terminal()` correctly classifies every state
- [x] Docstrings in Portuguese on the module, enum, and function

**Tests**: unit
**Gate**: quick

**Commit**: `feat(dominio): adicionar enum de estados de execucao preventiva`

**Status**: ✅ Complete

---

### T2: Definir as portas e tipos compartilhados da persistência

**What**: `Protocol`s (`PortaMigracoes`, `PortaDadosSinteticos`, `PortaExecucoes`, `PortaIdempotencia`) and shared result/exception types (`ResultadoMigracao`, `ResultadoInicializacao`, `ResultadoRestauracao`, `RespostaRegistrada`, `VersaoSchemaFutura`, `MigracaoFalhou`, `MigracoesPendentes`, `ExecucaoAtivaImpedeRestauracao`, `ConflitoIdempotencia`, `NaoInicializado`).
**Where**: `src/backend/central_preventiva/aplicacao/portas_persistencia.py`
**Depends on**: T1
**Reuses**: `dominio.estados_execucao` (typing only)
**Requirement**: SEED-01

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Every method used by T9/T10 (use cases) and implemented by T5-T8 (adapters) exists on the matching Protocol with correct signatures (added `PortaMigracoes.versao_conhecida()`: `verificar_versao_schema` lives in `aplicacao` and cannot compare versions without it)
- [x] Exception types carry the fields the error-handling table in `design.md` requires (e.g., `MigracaoFalhou.versao`, `VersaoSchemaFutura`); added `RegistroMigracoesInvalido` for `spec.md`'s ledger-ausente/corrompido edge case
- [x] `pyright --strict` passes with no errors
- [x] Docstrings in Portuguese on every public symbol

**Tests**: none (interfaces/DTOs only, verified by every task that implements/consumes them)
**Gate**: build

**Commit**: `feat(aplicacao): definir portas e tipos da inicializacao e restauracao`

**Status**: ✅ Complete

---

### T3: Adicionar `caminho_banco` à configuração local

**What**: Extend `Configuracao` with a required `caminho_banco: Path` field (validated, e.g. must not be empty / must resolve under the project's `var/` directory), following the same `field_validator` + explicit-error pattern already used for `host_api`/`origem_frontend`.
**Where**: `src/backend/central_preventiva/composicao/configuracao.py` (modify), `.env.example` (add `CENTRAL_PREVENTIVA_CAMINHO_BANCO`)
**Depends on**: None
**Reuses**: existing `Configuracao`/`obter_configuracao` pattern in the same file
**Requirement**: SEED-05

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] `Configuracao` accepts a valid `caminho_banco` and rejects an invalid/empty one with `ValidationError`
- [x] `obter_configuracao()` still sanitizes errors (no value leakage), consistent with `test_erro_de_configuracao_nao_revela_valores`
- [x] `.env.example` documents the new variable with a non-secret example value
- [x] Existing `test_configuracao.py` tests still pass; new tests added for `caminho_banco`

**Deviation**: the field has a validated default (`var/central_preventiva.duckdb`, resolved from the project root) instead of being strictly required. A required field would break every existing `Configuracao(...)` construction in `test_saude.py`/`test_servidor.py` (files outside this task's `Where`) on a clean checkout, and would break existing local `.env` files because the README uses `cp -n`, which never overwrites. The default matches the `*.duckdb` and `var/central_preventiva.duckdb` entries already in `.gitignore` (SEED-05). Validation (non-empty name, `.duckdb` suffix, project-root resolution) still applies to any supplied value.

**Tests**: unit
**Gate**: quick

**Commit**: `feat(composicao): adicionar caminho do banco DuckDB a configuracao local`

**Status**: ✅ Complete

---

### T4: Criar o helper de conexão explícita ao DuckDB

**What**: `abrir_conexao(caminho: Path) -> AbstractContextManager[duckdb.DuckDBPyConnection]` — opens one connection per call, closes on exit, propagates exceptions.
**Where**: `src/backend/central_preventiva/adaptadores/persistencia/conexao.py`
**Depends on**: None
**Reuses**: none
**Requirement**: SEED-05

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Opens a connection to a `tmp_path`-based file, creates a table, and the change is visible after closing and reopening
- [x] Connection is closed even when the wrapped block raises
- [x] No shared/global connection object exists anywhere in the module

**Note**: also creates the file's parent directory when missing (`var/` is gitignored and absent on a fresh clone), which SEED-05's "integralmente recriável" requires. Adds the package's `__init__.py`.

**Tests**: integration
**Gate**: quick

**Commit**: `feat(persistencia): adicionar helper de conexao explicita ao DuckDB`

**Status**: ✅ Complete

---

### T5: Implementar o executor de migrações versionadas

**What**: `ExecutorMigracoes` implementing `PortaMigracoes`, plus `migracoes/0001_schema_inicial.sql` (all 8 tables from `design.md`'s Data Models section, including `schema_migracoes` itself). Applies pending migrations in order, each in its own transaction; raises `VersaoSchemaFutura` if the recorded version exceeds the known list (no mutation); on mid-sequence failure, leaves prior migrations committed, does not record the failed one, and raises `MigracaoFalhou`.
**Where**: `src/backend/central_preventiva/adaptadores/persistencia/migracoes.py`, `src/backend/central_preventiva/adaptadores/persistencia/migracoes/0001_schema_inicial.sql`
**Depends on**: T2, T4
**Reuses**: `conexao.abrir_conexao`
**Requirement**: SEED-01, SEED-03, SEED-04, SEED-05, SEED-06

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Applying against an empty `tmp_path` DuckDB file creates all 8 tables and one `schema_migracoes` row
- [x] Re-running against an already-current database applies nothing and reports no pending work
- [x] A `schema_migracoes` row seeded with a future version number causes `aplicar_pendentes()` to raise `VersaoSchemaFutura` with zero file mutation (verified by re-querying table absence and the unchanged ledger)
- [x] A simulated failure in a second migration (e.g. a deliberately invalid SQL migration injected via a test double) leaves migration 1 committed, does not record migration 2, and raises `MigracaoFalhou(versao=2, ...)`
- [x] Re-running after "fixing" the failing migration resumes from migration 2 without re-applying migration 1
- [x] Schema documentation (columns, keys, constraints, timestamps, migration strategy) is written to a versioned doc per `SEED-06` (`src/backend/central_preventiva/adaptadores/persistencia/README.md`)
- [x] Also covers `spec.md`'s edge case "banco existente com `schema_migracoes` ausente ou corrompida" via `RegistroMigracoesInvalido`

**Tests**: integration
**Gate**: full

**Commit**: `feat(persistencia): adicionar executor de migracoes versionadas do DuckDB`

**Status**: ✅ Complete

---

### T6: Implementar o repositório de guarda de execuções ativas

**What**: `RepositorioExecucoes` implementing `PortaExecucoes.existe_execucao_nao_terminal()` — `SELECT EXISTS(...)` against `execucao_preventiva.estado NOT IN (<ESTADOS_TERMINAIS>)`.
**Where**: `src/backend/central_preventiva/adaptadores/persistencia/repositorio_execucoes.py`
**Depends on**: T1, T4, T5
**Reuses**: `conexao.abrir_conexao`, `dominio.estados_execucao.ESTADOS_TERMINAIS`
**Requirement**: SEED-10

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Returns `False` against an empty `execucao_preventiva` table
- [x] Returns `True` after inserting a fixture row with a non-terminal `estado` (parametrizado sobre todos os estados não terminais)
- [x] Returns `False` when all rows present have a terminal `estado`

**Tests**: integration
**Gate**: full

**Commit**: `feat(persistencia): adicionar repositorio de guarda de execucoes ativas`

**Status**: ✅ Complete

---

### T7: Implementar o repositório genérico de chaves de idempotência

**What**: `RepositorioIdempotencia` implementing `PortaIdempotencia.buscar`/`registrar` against `chaves_idempotencia`, scoped by `(chave, operacao)`.
**Where**: `src/backend/central_preventiva/adaptadores/persistencia/repositorio_idempotencia.py`
**Depends on**: T4, T5
**Reuses**: `conexao.abrir_conexao`
**Requirement**: SEED-11, SEED-12

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] `buscar()` returns `None` for an unknown `(chave, operacao)`
- [x] `registrar()` then `buscar()` returns the exact stored `hash_requisicao`/`resposta_status`/`resposta_corpo`
- [x] The same `chave` used under a different `operacao` does not collide (composite key proven by a test)
- [x] Reregistrar o mesmo par é recusado pela chave primária e preserva a resposta original

**Tests**: integration
**Gate**: full

**Commit**: `feat(persistencia): adicionar repositorio generico de chaves de idempotencia`

**Status**: ✅ Complete

---

### T8: Implementar o semeador de dados sintéticos

**What**: `SemeadorDadosSinteticos` implementing `PortaDadosSinteticos` (`esta_semeado`, `semear`, `restaurar`), backed by one shared `dataset_sintetico_v1()` function providing segurados, apólices, regras, eventos meteorológicos, and eligible/non-eligible `elegibilidades_historicas` for both chuva intensa and granizo, all with unambiguously fictitious identifiers.
**Where**: `src/backend/central_preventiva/adaptadores/persistencia/semeador.py`
**Depends on**: T4, T5
**Reuses**: `conexao.abrir_conexao`
**Requirement**: SEED-01, SEED-02, SEED-07, SEED-09, SEED-13

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] `esta_semeado()` is `False` on an empty schema, `True` after `semear()`
- [x] `semear()` inserts at least one eligible and one non-eligible example for both `chuva_intensa` and `granizo`, with fictitious IDs (marcador `DEMO-` nos identificadores legíveis e UUIDs derivados do namespace da demonstração)
- [x] `restaurar()` reverts a manually-mutated reference row back to the canonical dataset, inside one transaction
- [x] A simulated failure partway through `restaurar()` (constraint violation injected via a corrupted `ConjuntoSintetico` test double) leaves the pre-restore dataset fully intact and queryable — no partial delete/reinsert
- [x] No real personal data, credential, or usable contact appears anywhere in `dataset_sintetico_v1()`

**SPEC_DEVIATION (afeta também T5)**: `design.md` declara `REFERENCES` nas tabelas de referência e descreve a restauração como delete + reinsert numa única transação. As duas coisas são incompatíveis no DuckDB: ele não adia a verificação de chave estrangeira, então recusa apagar uma tabela referenciada na mesma transação em que suas filhas foram apagadas, e recusa até atualizar uma coluna `LIST` (`apolices.coberturas`) de uma tabela referenciada (duckdb/duckdb#13819, confirmado experimentalmente). Escolha: manter a restauração transacional exigida por SEED-09 e declarar as relações como chave estrangeira **lógica**, documentada no `README.md` da persistência e em comentário no `0001_schema_inicial.sql`, em vez de `REFERENCES`. O conjunto sintético versionado é o único escritor destas tabelas. Isso alterou `migracoes/0001_schema_inicial.sql` e o `README.md` da persistência, arquivos criados em T5.

**Tests**: integration
**Gate**: build

**Commit**: `feat(persistencia): adicionar semeador de dados sinteticos reproduziveis`

**Status**: ✅ Complete

---

### T9: Implementar o caso de uso de inicialização

**What**: `inicializar_dados_sinteticos(portas) -> ResultadoInicializacao` and `verificar_versao_schema(portas) -> None`, orchestrating `PortaMigracoes`/`PortaDadosSinteticos` with **fake** port doubles in tests (per the project's "casos de uso recebem portas falsas" convention).
**Where**: `src/backend/central_preventiva/aplicacao/inicializacao.py`
**Depends on**: T2
**Reuses**: `portas_persistencia` Protocols
**Requirement**: SEED-01, SEED-02, SEED-03, SEED-04

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Against a fake "not yet migrated, not yet seeded" pair of ports: applies migrations then seeds, in that order
- [x] Against a fake "already current, already seeded" pair: does nothing and returns `"ja_preparado"`
- [x] `verificar_versao_schema` re-raises `VersaoSchemaFutura`/surfaces `MigracoesPendentes` from a fake `PortaMigracoes` without calling any mutating method
- [x] No `adaptadores`/`duckdb` import anywhere in this module (verified by the equivalent AST check in `test_inicializacao.py`, keeping `test_camadas.py` outside this task's `Where`)

**Note**: `PortasInicializacao` (frozen dataclass agrupando `PortaMigracoes` + `PortaDadosSinteticos`) é declarada neste módulo, conforme a assinatura do `design.md`.

**Tests**: unit
**Gate**: quick

**Commit**: `feat(aplicacao): adicionar caso de uso de inicializacao dos dados sinteticos`

**Status**: ✅ Complete

---

### T10: Implementar o caso de uso de restauração

**What**: `restaurar_dados_sinteticos(portas, chave_idempotencia, hash_requisicao) -> ResultadoRestauracao`, orchestrating `PortaIdempotencia`/`PortaExecucoes`/`PortaDadosSinteticos` with **fake** port doubles in tests.
**Where**: `src/backend/central_preventiva/aplicacao/restauracao.py`
**Depends on**: T2
**Reuses**: `portas_persistencia` Protocols
**Requirement**: SEED-08, SEED-09, SEED-10, SEED-11, SEED-12, SEED-13

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] A fake `PortaIdempotencia` returning a stored response short-circuits: `restaurar()` is never called on the fake `PortaDadosSinteticos`
- [ ] A fake idempotency hit with a **different** `hash_requisicao` raises `ConflitoIdempotencia`, no mutation
- [ ] A fake `PortaExecucoes.existe_execucao_nao_terminal() -> True` raises `ExecucaoAtivaImpedeRestauracao` without calling `restaurar()` or `registrar()`
- [ ] A fake `PortaDadosSinteticos.esta_semeado() -> False` raises `NaoInicializado` without calling the guard or `restaurar()`
- [ ] Happy path calls the guard, then `restaurar()`, then `registrar()`, in that order, and returns a populated `ResultadoRestauracao`

**Tests**: unit
**Gate**: quick

**Commit**: `feat(aplicacao): adicionar caso de uso de restauracao dos dados sinteticos`

---

### T11: Adicionar o comando CLI de inicialização

**What**: `composicao/inicializador.py:executar()` — validates `Configuracao`, wires the concrete `ExecutorMigracoes`/`SemeadorDadosSinteticos` from `caminho_banco`, calls `inicializar_dados_sinteticos`, prints a clear PT-BR result (created vs. `"já preparado"`), documented as a new README command.
**Where**: `src/backend/central_preventiva/composicao/inicializador.py`, `README.md` (add the command)
**Depends on**: T3, T5, T8, T9
**Reuses**: `servidor.py`'s validate-then-act shape
**Requirement**: SEED-01, SEED-02, SEED-06

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Running `executar()` against a `tmp_path` DuckDB path with no file present creates schema + seed end-to-end
- [ ] Running it again reports "já preparado" with unchanged row counts
- [ ] A structurally invalid/missing configuration exits with a PT-BR error revealing no secret values (consistent with `ConfiguracaoInvalida`'s existing behavior)
- [ ] README documents the exact reproducible command under "Execução local"

**Tests**: integration
**Gate**: full

**Commit**: `feat(composicao): adicionar comando de inicializacao dos dados sinteticos`

---

### T12: Expor o endpoint de restauração

**What**: `POST /api/v1/dados-sinteticos/restauracoes` router requiring `Idempotency-Key`; `201` with `RespostaRestauracao {status, restaurado_em}` on success; `application/problem+json` (`codigo`, `correlacao_id`) for `409` (idempotency conflict or active-execution guard) and `422`/`500`. Registered into `composicao/api.py` with concrete adapters from T6/T7/T8 wired via `caminho_banco`.
**Where**: `src/backend/central_preventiva/adaptadores/api/dados_sinteticos.py`, `src/backend/central_preventiva/composicao/api.py` (modify)
**Depends on**: T3, T6, T7, T8, T10
**Reuses**: `saude.py`'s router shape (Pydantic response model + thin translation), `api.py`'s app-factory + CORS pattern
**Requirement**: SEED-09, SEED-10, SEED-11, SEED-12, SEED-13, SEED-15

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Happy path against a `tmp_path` DuckDB (already seeded, no active execution): `201`, response matches `RespostaRestauracao`
- [ ] Missing `Idempotency-Key` header: `422` problem+json
- [ ] Same `Idempotency-Key` + same body repeated: second call returns the identical stored response, no second restore executed (verified by row-timestamp/mutation check)
- [ ] Same `Idempotency-Key` + different body: `409` problem+json, no mutation
- [ ] Fixture non-terminal `execucao_preventiva` row present: `409` problem+json naming the active-execution guard, no mutation
- [ ] JSON body uses `snake_case`; OpenAPI description in Portuguese, matching `test_openapi_em_portugues_nao_antecipa_recursos_futuros`'s style

**Tests**: e2e
**Gate**: full

**Commit**: `feat(api): adicionar endpoint de restauracao dos dados sinteticos`

---

### T13: Verificar a versão do schema na inicialização do servidor

**What**: `servidor.py:executar()` calls `verificar_versao_schema` (via the concrete `ExecutorMigracoes`) before `uvicorn.run`; refuses to start with a clear PT-BR error on a future or pending schema version, without attempting any migration.
**Where**: `src/backend/central_preventiva/composicao/servidor.py` (modify)
**Depends on**: T3, T5, T9
**Reuses**: existing `servidor.executar()` structure, `test_servidor.py`'s monkeypatch style
**Requirement**: SEED-03

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Against a `tmp_path` DuckDB at the current known version: `uvicorn.run` is called (unchanged behavior)
- [ ] Against a `tmp_path` DuckDB seeded with a future `schema_migracoes` version: `uvicorn.run` is never called, process exits with a PT-BR error, no file mutation
- [ ] Against a `tmp_path` DuckDB with pending migrations (older version): `uvicorn.run` is never called, error directs the operator to run the init command
- [ ] Existing `test_servidor_repassa_host_validado_e_porta_fixa` still passes

**Tests**: integration
**Gate**: build

**Commit**: `feat(composicao): recusar inicializacao do servidor com schema pendente ou futuro`

---

### T14: Criar o componente `Modal` de confirmação

**What**: Generic, reusable confirmation modal implementing `UX-DR20`: title, objeto, impacto, focus trap, `Esc` to close (when allowed), focus returned to the triggering control on close, confirm/cancel callbacks.
**Where**: `src/frontend/src/componentes/Modal.tsx` (+ `Modal.test.tsx`, `Modal.css` if needed)
**Depends on**: None
**Reuses**: `@phosphor-icons/react` (already installed), existing `@fontsource` tokens
**Requirement**: SEED-08, SEED-14

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Renders `titulo`, `objeto`, `impacto` text content
- [ ] `Tab`/`Shift+Tab` stays trapped within the modal while open
- [ ] `Esc` closes the modal when closable, calling the provided close handler
- [ ] Focus returns to the element that opened the modal after it closes
- [ ] Confirm action calls the provided callback exactly once per click/`Enter`

**Tests**: unit
**Gate**: quick

**Commit**: `feat(componentes): adicionar modal de confirmacao acessivel`

---

### T15: Criar o cliente de API para restauração

**What**: `restaurarDadosSinteticos(): Promise<ResultadoRestauracao>` — generates an `Idempotency-Key` (`crypto.randomUUID()`), `POST`s to `/api/v1/dados-sinteticos/restauracoes`, parses success and `application/problem+json` error responses into typed results/errors.
**Where**: `src/frontend/src/api/dadosSinteticos.ts` (+ `dadosSinteticos.test.ts`)
**Depends on**: None
**Reuses**: none (first frontend API module; matches the contract T12 defines)
**Requirement**: SEED-11, SEED-12, SEED-15

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Mocked `fetch` returning `201` resolves with the parsed `ResultadoRestauracao`
- [ ] Mocked `fetch` returning `409` problem+json rejects with a typed error carrying `codigo`/`correlacao_id`
- [ ] Mocked `fetch` returning `422` problem+json rejects with a typed error
- [ ] A network failure (`fetch` rejecting) surfaces as a typed error, not an unhandled rejection
- [ ] Every call sends a freshly generated `Idempotency-Key` header

**Tests**: unit
**Gate**: quick

**Commit**: `feat(api): adicionar cliente de restauracao dos dados sinteticos`

---

### T16: Criar a superfície "Restaurar demonstração"

**What**: `RestaurarDemonstracao.tsx` — page wiring `Modal` (T14) + `restaurarDadosSinteticos` (T15), presenting the `Confirmação`/`Restaurando`/`Concluído`/`Falha` states from `SEED-14`; mounted reachable via a plain-`pathname` check in `main.tsx` (no router dependency added, consistent with the architecture spine's deferred routing decision) at `/administracao/restaurar-demonstracao`, alongside the existing static `App` shell at `/`.
**Where**: `src/frontend/src/funcionalidades/dados-sinteticos/RestaurarDemonstracao.tsx` (+ test), `src/frontend/src/main.tsx` (modify)
**Depends on**: T14, T15
**Reuses**: `Modal`, `restaurarDadosSinteticos`
**Requirement**: SEED-08, SEED-14

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Clicking "Restaurar demonstração" opens the `Modal` in the `Confirmação` state; nothing is called yet
- [ ] Confirming moves to `Restaurando` (loading indicator, action disabled) and calls the mocked API client
- [ ] A mocked success response moves to `Concluído`
- [ ] A mocked failure response moves to `Falha`, showing occurrence/impact/next-safe-action text, and the previous content remains visible/consultable
- [ ] Visiting `/administracao/restaurar-demonstracao` renders this page instead of the existing `App` shell; visiting `/` is unaffected

**Tests**: integration
**Gate**: build

**Commit**: `feat(frontend): adicionar superficie de restauracao da demonstracao`

---

## Phase Execution Map

Visual representation of task ordering. Phases run in sequence, and tasks within a phase run in order:

Phases, in order: Phase 1 (T1-T4) → Phase 2 (T5-T8) → Phase 3 (T9-T10) → Phase 4 (T11-T13) → Phase 5 (T14-T16).

Complete dependency edge list (every `Depends on` relationship, one edge per line, `source -> target` meaning target depends on source):

```
T1 -> T2
T2 -> T5
T4 -> T5
T1 -> T6
T4 -> T6
T5 -> T6
T4 -> T7
T5 -> T7
T4 -> T8
T5 -> T8
T2 -> T9
T2 -> T10
T3 -> T11
T5 -> T11
T8 -> T11
T9 -> T11
T3 -> T12
T6 -> T12
T7 -> T12
T8 -> T12
T10 -> T12
T3 -> T13
T5 -> T13
T9 -> T13
T14 -> T16
T15 -> T16
```

Execution is strictly sequential - there is no intra-phase parallelism. A single agent (or batch worker) works one task at a time, in order.

**Batching for Execute**: 16 tasks total → 2 batches at the ~7-8 task budget, cut on a phase boundary: **Batch 1 = Phase 1 + Phase 2** (T1-T8, 8 tasks), **Batch 2 = Phase 3 + Phase 4 + Phase 5** (T9-T16, 8 tasks).

---

## Task Granularity Check

| Task | Scope | Status |
| --- | --- | --- |
| T1: Enum de estados de execução | 1 file, 1 concept | ✅ Granular |
| T2: Portas e tipos da persistência | 1 file, 1 concept (Protocols + DTOs) | ✅ Granular |
| T3: `caminho_banco` na configuração | 1 file (+ `.env.example`) | ✅ Granular |
| T4: Helper de conexão DuckDB | 1 file | ✅ Granular |
| T5: Executor de migrações | 1 file + 1 SQL file, 1 component | ✅ Granular |
| T6: Repositório de guarda de execuções | 1 file | ✅ Granular |
| T7: Repositório de idempotência | 1 file | ✅ Granular |
| T8: Semeador de dados sintéticos | 1 file, 1 component | ✅ Granular |
| T9: Caso de uso de inicialização | 1 file | ✅ Granular |
| T10: Caso de uso de restauração | 1 file | ✅ Granular |
| T11: CLI de inicialização | 1 file (+ README edit) | ✅ Granular |
| T12: Endpoint de restauração | 1 file (+ 1 registration edit) | ✅ Granular |
| T13: Verificação de versão no startup | 1 file (modify) | ✅ Granular |
| T14: Componente `Modal` | 1 component | ✅ Granular |
| T15: Cliente de API de restauração | 1 file | ✅ Granular |
| T16: Superfície "Restaurar demonstração" | 1 component (+ 1 mounting edit) | ✅ Granular |

---

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| --- | --- | --- | --- |
| T1 | None | None | ✅ Match |
| T2 | T1 | T1 | ✅ Match |
| T3 | None | None | ✅ Match |
| T4 | None | None | ✅ Match |
| T5 | T2, T4 | T2, T4 | ✅ Match |
| T6 | T1, T4, T5 | T1, T4, T5 | ✅ Match |
| T7 | T4, T5 | T4, T5 | ✅ Match |
| T8 | T4, T5 | T4, T5 | ✅ Match |
| T9 | T2 | T2 | ✅ Match |
| T10 | T2 | T2 | ✅ Match |
| T11 | T3, T5, T8, T9 | T3, T5, T8, T9 | ✅ Match |
| T12 | T3, T6, T7, T8, T10 | T3, T6, T7, T8, T10 | ✅ Match |
| T13 | T3, T5, T9 | T3, T5, T9 | ✅ Match |
| T14 | None | None | ✅ Match |
| T15 | None | None | ✅ Match |
| T16 | T14, T15 | T14, T15 | ✅ Match |

No dependency points to a later phase; all deps point backward or within the same phase.

---

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| --- | --- | --- | --- | --- |
| T1: Enum de estados | Domínio | unit | unit | ✅ OK |
| T2: Portas e tipos | Aplicação — portas/DTOs | none | none | ✅ OK |
| T3: `caminho_banco` | Composição | integration (unit-level, matches existing `test_configuracao.py` floor) | unit | ✅ OK |
| T4: Conexão DuckDB | Adaptadores/persistência | integration | integration | ✅ OK |
| T5: Executor de migrações | Adaptadores/persistência | integration | integration | ✅ OK |
| T6: Repositório de execuções | Adaptadores/persistência | integration | integration | ✅ OK |
| T7: Repositório de idempotência | Adaptadores/persistência | integration | integration | ✅ OK |
| T8: Semeador | Adaptadores/persistência | integration | integration | ✅ OK |
| T9: Caso de uso de inicialização | Aplicação — casos de uso | unit | unit | ✅ OK |
| T10: Caso de uso de restauração | Aplicação — casos de uso | unit | unit | ✅ OK |
| T11: CLI de inicialização | Composição | integration | integration | ✅ OK |
| T12: Endpoint de restauração | Adaptadores/api | e2e | e2e | ✅ OK |
| T13: Verificação de versão | Composição | integration | integration | ✅ OK |
| T14: Modal | Frontend — componentes | unit | unit | ✅ OK |
| T15: Cliente de API | Frontend — api | unit | unit | ✅ OK |
| T16: Superfície de restauração | Frontend — funcionalidades | integration | integration | ✅ OK |

No violations. `T3`'s matrix row is labeled "integration" generically in the coverage table's composição bucket, but its actual required depth (unit tests on a Pydantic `BaseSettings` field, matching the existing `test_configuracao.py` floor) is `unit` — noted above as the correct, non-lesser depth for this specific layer.

---

## Tips

- **Phases are ordered** - Each phase completes before the next; tasks run in order within a phase
- **Reuses = Token saver** - Always reference existing code
- **Tools per task** - MCPs and Skills prevent wrong approaches
- **Dependencies are gates** - Clear what blocks what
- **Done when = Testable** - If you can't verify it, rewrite it
- **Requirement ID = Traceable** - Every task traces back to a spec requirement
- **One commit per task** - Plan the commit message format in advance
