# STATE

## Decisions

### AD-001
- **Decision**: DuckDB schema evolves through numbered `.sql` migration files tracked in a `schema_migracoes` ledger table; each migration runs in its own transaction, applied only by an explicit CLI command (`composicao.inicializador`) — the server never auto-migrates on boot, it only refuses to start if the recorded version is pending or newer than the code knows.
- **Reason**: Makes schema evolution auditable and safe to reason about (DuckDB fully supports transactional DDL); an explicit trigger avoids a server accidentally mutating a shared demo database on every restart.
- **Trade-off**: One extra manual step (`uv run ... composicao.inicializador`) documented in the README, instead of "just works on boot."
- **Scope**: All backend persistence work (`adaptadores/persistencia`), every future story that adds or evolves DuckDB tables.
- **Date**: 2026-08-28
- **Status**: active

### AD-002
- **Decision**: A generic `chaves_idempotencia` table (`chave`, `operacao`, `hash_requisicao`, `resposta_status`, `resposta_corpo`), scoped by operation name, is the standard `Idempotency-Key` mechanism for every mutable `POST` endpoint — not a per-endpoint table.
- **Reason**: `ARCHITECTURE-SPINE.md` AD-7 already mandates idempotency on every mutable `POST`; building one small reusable store now avoids every future story (coleta manual, geração, revisão, simulação) reinventing it.
- **Trade-off**: Slightly more generic/abstract than a restore-specific table would be, for a benefit only later stories cash in.
- **Scope**: Every `adaptadores/api` router exposing a mutable `POST`.
- **Date**: 2026-08-28
- **Status**: active

### AD-003
- **Decision**: Story 1.2's frontend restore surface uses a plain `fetch` call (`src/frontend/src/api/dadosSinteticos.ts`) and a hand-rolled `Modal` component, built ahead of História 1.5's OpenAPI-generated client and História 1.4's navigation shell.
- **Reason**: Story 1.2's acceptance criteria require a real, demoable confirmation-modal UI now; waiting for 1.4/1.5 would mean shipping this story backend-only and reopening its already-approved spec.
- **Trade-off**: The `fetch` call and page wiring will need rework once 1.5 introduces `openapi-typescript`-generated types and 1.4 introduces real navigation/routing — accepted as a small, contained cost since the `Modal` component itself is generic and reusable.
- **Scope**: `src/frontend/src/api/`, `src/frontend/src/componentes/Modal.tsx`, `src/frontend/src/funcionalidades/dados-sinteticos/` until Histórias 1.4/1.5 land.
- **Date**: 2026-08-28
- **Status**: active

### AD-004
- **Decision**: `dominio/estados_execucao.py` defines the canonical `EstadoExecucao` enum and terminal/non-terminal classification now, ahead of `ExecucaoPreventiva`'s actual behavior (Epic 2/3).
- **Reason**: Story 1.2's restore guard (DW-002) needs a real, testable notion of "non-terminal execution"; defining the state names now, matching `ARCHITECTURE-SPINE.md` AD-4's canonical diagram exactly, means Epic 2/3 extend an existing enum instead of introducing a second one that has to be reconciled.
- **Trade-off**: A domain module exists before the workflow it describes is implemented — a future reader needs this note to understand why.
- **Scope**: `dominio/estados_execucao.py`, `execucao_preventiva` table, every future story that transitions or reads execution state.
- **Date**: 2026-08-28
- **Status**: active

### AD-005
- **Decision**: DuckDB tables do not declare `REFERENCES` foreign-key constraints. Relationships between tables (e.g. `apolices.segurado_id → segurados.id`) are documented as logical foreign keys in the migration file's comments and in `adaptadores/persistencia/README.md`, not enforced by the schema.
- **Reason**: DuckDB does not defer foreign-key checks within a transaction. With `REFERENCES` declared, it refuses to delete a referenced table in the same transaction its children are deleted, and refuses to update a `LIST` column (`apolices.coberturas`) on a referenced table (`duckdb/duckdb#13819`). That makes the single-transaction delete-and-reinsert restore required by `spec.md`'s `SEED-09` impossible to implement as designed.
- **Trade-off**: The database itself no longer catches an orphaned/dangling reference at write time; integrity depends on the versioned seed being the only writer of these tables (true for this story) and on future stories that mutate them respecting the documented relationships without a DB-level backstop.
- **Scope**: `adaptadores/persistencia/migracoes/`, every future migration that adds a table with a relationship to an existing one, and any future story that needs transactional delete/replace semantics against related tables.
- **Date**: 2026-08-28
- **Status**: active

### AD-006
- **Decision**: All in-process periodic/background work in the backend runs as a single `asyncio` task started in the FastAPI `lifespan` (e.g. `composicao/agendador_meteorologico.py`), never a new scheduling dependency (APScheduler, Celery, etc.) or an OS-level cron.
- **Reason**: `ARCHITECTURE-SPINE.md` AD-7 already mandates a single in-process runner for asynchronous work; a bare `asyncio` loop reuses that same mechanism for scheduled INMET collection (História 2.1) with zero new dependencies, and keeps `README.md`'s "starts without hidden manual steps" promise intact.
- **Trade-off**: Doesn't survive a process restart or scale to multiple workers — accepted because the PoC is explicitly single-process (AD-2).
- **Scope**: Any future story that needs periodic or scheduled backend work (weather polling, retries, cleanup).
- **Date**: 2026-08-30
- **Status**: active

### AD-007
- **Decision**: A dedicated, versioned mapping table (`areas_monitoradas_inmet`) maps a real, monitored INMET station code to the synthetic `codigo_ibge_area` values used by the demonstration's `segurados`/`apolices` (e.g. `9990001`, `9990002`) — the domain never assumes real INMET geography aligns with the synthetic dataset's area codes.
- **Reason**: `semeador.py` seeds policyholders with fictional area codes, not real IBGE codes; without an explicit mapping, a real INMET event could never match a synthetic eligible policyholder, silently breaking the "real weather → synthetic eligibility" demo path required by História 2.1/2.5.
- **Trade-off**: Adds one small configuration table that must be kept in sync with whatever areas the synthetic dataset uses; acceptable because the demo's area set is small and fixed.
- **Scope**: `adaptadores/persistencia/migracoes/0002_meteorologia.sql`, `adaptadores/meteorologia/`, any future story that normalizes real external geography into the synthetic demonstration's area codes.
- **Date**: 2026-08-30
- **Status**: active

## Handoff
