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

### AD-008
- **Decision**: Optimistic concurrency via a `versao INTEGER` column + a client-supplied `versao_esperada` is the only concurrency-control mechanism for any mutable domain aggregate — never a pessimistic lock, never `atualizado_em` used as a version proxy.
- **Reason**: Independently re-derived and applied identically four times (`RepositorioExecucaoPreventiva` in 2.2, `RepositorioRegras` in 2.4, `RepositorioMensagens` in 3.2, `RepositorioSegurados` in 5.6) — each design cited the previous one as precedent rather than a shared source. Formalizing it once prevents a future implementer (or a context-less sub-agent) from inventing a divergent mechanism for the next mutable table.
- **Trade-off**: None beyond what each individual adoption already accepted — this AD only centralizes an already-uniform practice, it doesn't change behavior anywhere.
- **Scope**: Every future table backing a mutable domain aggregate (`CREATE TABLE` with an `UPDATE` path reachable from the API).
- **Date**: 2026-08-31
- **Status**: active

### AD-009
- **Decision**: "Retry after a terminal failure" always creates a new, correlated `ExecucaoPreventiva` (`execucao_origem_id` pointing at the terminal execution, a fresh `execucao_id`, its own `Idempotency-Key`) — it never reopens, mutates, or reuses the terminal execution's row.
- **Reason**: Independently re-derived three times for three different terminal states (`falhou_coleta` in 2.2, `falhou_preparacao_ia` in 3.1, `falhou_simulacao` in 3.6), each citing the prior as precedent. AD-7 (`ARCHITECTURE-SPINE.md`) already mandates this at the architecture level; this AD makes the *exact shape* (which fields, which snapshot-validity check before creating the row) a single citable pattern instead of three parallel descriptions.
- **Trade-off**: None new — same three-time-validated shape, just centralized.
- **Scope**: Any future terminal execution state that a user can explicitly retry from.
- **Date**: 2026-08-31
- **Status**: active

### AD-010
- **Decision**: Domain-content deduplication (as opposed to command-level idempotency, AD-002) is enforced by a DB `UNIQUE` constraint on the natural content key, written via insert-or-noop (`INSERT ... ON CONFLICT DO NOTHING` or equivalent) — never an application-level "check then insert" that races.
- **Reason**: Applied identically five times for five different content types (`eventos_meteorologicos` in 2.2, `elegibilidades_historicas` in 2.5, `mensagens` in 3.2, `entregas_simuladas` in 3.6, `visualizacoes_comunicado` in 4.3). AD-002 already covers *replaying the same command*; this AD covers the separate concern of *two different commands producing the same domain fact* (e.g. a real coleta and a retried coleta both observing the same weather event). Naming both prevents either concern from being solved by the other's mechanism.
- **Trade-off**: Requires picking the correct natural key up front per table (already done correctly five times); a wrong key silently under-deduplicates. No behavior change from formalizing it.
- **Scope**: Any future table where two independent operations could legitimately produce the same domain fact.
- **Date**: 2026-08-31
- **Status**: active

### AD-011
- **Decision**: Any endpoint that resolves a resource scoped to an owner (`segurado_id`, `execucao_id`, etc.) returns an identical "not found" response whether the resource doesn't exist at all or exists but belongs to a different owner — the response body, status code, and message never differ between the two cases.
- **Reason**: Applied identically six times across the Segurado-facing and Marina-facing surfaces (4.2, 4.3, 5.2, 5.3, 5.4, 5.5), each design independently restating the same non-enumeration rationale. Centralizing it as a project-wide rule (rather than six local restatements) makes it the default a future endpoint must actively opt out of, not something each new history has to remember to add.
- **Trade-off**: None — this is a security/privacy hardening with no functional cost; it only forbids a more informative (and leakier) error message.
- **Scope**: Every future API endpoint that looks up a resource by ID scoped to a caller-supplied owner ID.
- **Date**: 2026-08-31
- **Status**: active

### AD-012
- **Decision**: A correlated retry execution that starts in `aguardando_geracao` (retry from `falhou_preparacao_ia` or `falhou_simulacao`) materializes its own copies of the origin's eligibility snapshot rows: every `elegibilidades_historicas` row of the origin (included and excluded) is duplicated with a fresh `id` and the new execution's `execucao_id`, identical snapshot content, in the same transaction that creates the new execution. The new execution never references the origin's eligibility rows directly.
- **Reason**: `contextos_agente.elegibilidade_id` (3.1) and `mensagens (elegibilidade_id, canal)` (3.2) carry `UNIQUE` constraints, and an origin that reached `simulando` already owns a context and a message per included eligibility — a retry that "redoes preflight, geração, crítica" against the same rows violates both on the first insert. `elegibilidades_historicas`'s `UNIQUE` includes `execucao_id` (2.5), which is exactly what makes per-execution copies legal. This operationalizes the snapshot copy that `ARCHITECTURE-SPINE.md` AD-11 requires but no design had made concrete. (Independent review, finding A1.)
- **Trade-off**: Snapshot rows are duplicated per retry — negligible at PoC volume, and it buys full per-execution audit (each execution's public preview and timeline stay self-contained).
- **Scope**: `ServicoPreflightIA.solicitar_nova_tentativa` (3.1), `ServicoSimulacao.solicitar_nova_tentativa` (3.6), and any future retry entering `aguardando_geracao`. Retries from `falhou_coleta` (2.2) are out of scope — they restart at `coletando` with no eligibility to copy.
- **Date**: 2026-08-30
- **Status**: active

### AD-013
- **Decision**: `granizo` events are synthetic-only in the MVP. `real_inmet` provenance is reserved for `chuva_intensa` (derived from station precipitation readings); `tipo = granizo` enters exclusively through the synthetic contingency scenario (2.2, `AdaptadorCenarioSintetico`), always labeled `proveniencia = 'sintetico'`.
- **Reason**: Hourly readings of INMET automatic stations (the endpoint chosen in 2.1) expose precipitation, temperature, wind, pressure, humidity — there is no hail field, so the "real granizo sample" 2.1 T4 originally demanded is unobtainable, and 2.3's "granizo é binário na fonte pública" rationale was unverified. Switching to INMET's alert endpoint would add a second unproven external contract days before the deadline. (Independent review, finding A2.)
- **Trade-off**: The "real weather → eligible policyholder" demo path exists only for chuva_intensa; the granizo end-to-end scenario (5.8) runs on the labeled synthetic scenario — explicit and acceptable for a PoC whose E2E suite already runs without real external integration.
- **Scope**: 2.1 normalizer and fixtures, 2.3 relevance rationale, 2.2 synthetic scenario, 5.8 granizo E2E scenario, and any future event type the chosen INMET endpoint cannot observe.
- **Date**: 2026-08-30
- **Status**: active

### AD-014
- **Decision**: The synthetic-data restore returns the database to the complete versioned initial state. Inside its single transaction it wipes, catalog-driven (enumerating tables from the DuckDB catalog), every table except an explicit allowlist — `schema_migracoes` plus versioned-config tables (today only `areas_monitoradas_inmet`) — then reseeds the seeded tables as before. New tables are covered automatically; only a new versioned-config table must join the allowlist in the story that creates it.
- **Reason**: Epic 1's restore deleted only the seeded tables. Epics 2–4 add 14 execution-produced tables that would survive a restore, leaving orphaned references (no FK backstop, per AD-005) and silently breaking 5.8's assumption that a freshly restored database yields deterministic E2E runs (`UNIQUE` collisions across runs). Catalog-driven enumeration removes the "each story must remember to register its table" failure mode. (Independent review, finding A3.)
- **Trade-off**: Restore is more destructive — it also clears execution history and idempotency keys. That is the correct semantics for a demo reset; the DW-002 guard (no restore while a non-terminal execution exists) still applies.
- **Scope**: `aplicacao/restauracao.py` + `adaptadores/persistencia/semeador.py` (extended by 2.1 T14), and allowlist maintenance in any future story that adds a versioned-config table.
- **Date**: 2026-08-30
- **Status**: active

### AD-015
- **Decision**: Adding a constraint (`UNIQUE`, `CHECK`, `NOT NULL`) or a backfilled column to an existing DuckDB table is always done by recreate-and-copy inside the migration's own transaction: `CREATE TABLE <nome>_nova (...)` with the constraints declared in the `CREATE`, `INSERT INTO ... SELECT` with explicit backfill expressions for pre-existing rows, `DROP TABLE`, `ALTER TABLE ... RENAME`. Never `ALTER TABLE ADD CONSTRAINT` (unsupported by DuckDB), and never a post-hoc `CREATE UNIQUE INDEX` for a dedup key (AD-010's insert-or-noop relies on table-constraint `ON CONFLICT` semantics; index interplay would require separate verification).
- **Reason**: Migrations `0003` (adds `UNIQUE` to `eventos_meteorologicos`) and `0005` (adds `NOT NULL` columns + `UNIQUE` to `elegibilidades_historicas`, which already holds seeded rows with no execution to reference) were unimplementable as originally written. AD-005 (no `REFERENCES` declared) is precisely what makes drop/rename inside a transaction safe. (Independent review, finding A4.)
- **Trade-off**: Migrations copy whole tables — trivial at PoC volume — and the `.sql` files get longer.
- **Scope**: Migrations `0003` (2.2) and `0005` (2.5), and every future migration that adds constraints or backfilled columns to an existing table.
- **Date**: 2026-08-30
- **Status**: active

## Handoff

- **Feature**: Épicos 2, 3, 4 e 5 (Histórias 2.1–2.6, 3.1–3.6, 4.1–4.4, 5.1–5.9) — **projeto inteiro planejado** (spec+design+tasks), execução não iniciada por pedido explícito do usuário ("apenas especifique, não implemente") repetido a cada épico.
- **Completed**: `spec.md`+`design.md`+`tasks.md` das 25 histórias (2.1–5.9), todas validadas por `validate_spec.py`/`validate_tasks.py` (0 erros; avisos de granularidade aceitos, mesma prática de `1-2-inicializar-e-restaurar-dados-sinteticos/tasks.md`). Auditoria de consistência cruzada feita: migrações `0002`–`0014` sequenciais sem colisão (batem com o `0001_schema_inicial.sql` real do repositório), 27 prefixos de Requirement ID todos únicos, 14 tabelas novas todas com nome único entre os 25 designs. AD-006 (runner `asyncio` in-process) e AD-007 (mapeamento estação real→área sintética), do Épico 2. AD-008 (concorrência otimista `versao`/`versao_esperada`, 4×), AD-009 (execução correlacionada em retentativa, 3×), AD-010 (dedução por `UNIQUE`/conteúdo, distinto de AD-002 por comando, 5×) e AD-011 (não-enumeração de recurso por dono, 6×) registrados nesta sessão, centralizando padrões que já eram aplicados de forma uniforme mas só documentados localmente em cada `design.md`. Demais decisões de arquitetura (LangGraph por mensagem em 3.2–3.5, `RetryComBackoff[T]` genérico em 3.1, agregação de leitura pura em 4.1–4.4/5.1–5.5, `SeguradoContexto` simétrico a `PerfilContexto` em 5.7, Playwright+`@axe-core/playwright` em 5.8) permanecem documentadas localmente por decorrerem de ADRs/AD já aprovados ou de pesquisa pontual, sem repetição suficiente para justificar um AD central.
- **In-progress**: nada — nenhum código foi tocado; um sub-agente de implementação da 2.1 (T1-T7) foi despachado e explicitamente interrompido antes de tocar qualquer arquivo (`git status` confirmado limpo).
- **Next step**: quando o usuário pedir para implementar, seguir a ordem de dependência: Épico 2 (2.1→2.2→2.3/2.4→2.5→2.6) → Épico 3 (3.1→3.2→3.3→3.4→3.5→3.6) → Épico 4 (4.1/4.3 em paralelo lógico, 4.2 depois de 3.5/3.6, 4.4 por último — agrega tudo) → Épico 5: 5.1–5.6 são independentes entre si e paralelizáveis (cada uma só depende de dado já produzido por 2–4), 5.7 depende de 5.1–5.6 estarem prontas (estende as 5 superfícies), 5.8 depende de TUDO (Épicos 1–4 + 5.1–5.7) estar implementado antes de seus testes E2E poderem passar, 5.9 depende só de 5.8 (`docs/evidencias/`) e é a última história do projeto — sua publicação final permanece bloqueada até autorização explícita do usuário, por design (nunca automatizada).
- **Review**: revisão independente do planejamento (2026-08-30) produziu 8 achados (parecer publicado como artefato "Revisão Central Preventiva"). **A1–A4 (críticos/altos) corrigidos nesta sessão** nos specs/designs/tasks e registrados como AD-012 (cópia de elegibilidades em retentativa correlacionada), AD-013 (granizo exclusivamente sintético), AD-014 (restauração catalog-driven ao estado inicial completo — novo INMET-17 e T14 na 2.1) e AD-015 (recreate-and-copy para constraint em tabela existente — migrações 0003/0005 reescritas nos designs de 2.2/2.5). **A5–A8 (médios) permanecem abertos**, a resolver no fluxo normal das histórias: A5 costura agendador↔runner sem decisão (coleta agendada não cria execução; RUNNER-01 insatisfeito para coletas automáticas), A6 contradição spec↔design na 2.6 sobre o terminal técnico, A7 "medidas normalizadas" ausentes do modelo `EventoMeteorologico` + critério de atribuição de `tipo` não especificado na 2.1, A8 chave de dedup de eventos sem `proveniencia` (evento sintético pode suprimir evento real idêntico). Recomendação de escopo do parecer: linha de corte contra o prazo 13/09 — núcleo Épico 2 (P1s) → Épico 3 (P1s) → 4.1+4.3 → 5.9; 5.1–5.7/P2s/auditoria WCAG plena como incrementos.
- **Blockers**: nenhum para o planejamento. Riscos já registrados nos próprios `design.md`, todos não-bloqueantes para Execute: (1) campos de leitura horária do INMET não confirmados ao vivo (2.1); (2) `langchain`/`langchain-openai`/`langgraph` (3.1) e Playwright/`@axe-core/playwright` (5.8) são dependências novas sem versão fixada — cada task que as adiciona deve verificar a versão estável no momento da implementação; (3) agregação de 4.4 lê ~9 fontes (custo aceito de PoC); (4) ferramenta de conversão Markdown→PDF (5.9) ainda não escolhida — verificada na implementação; (5) achados A5–A8 da revisão independente (ver **Review** acima).
- **Uncommitted files**: nenhum (todos os artefatos `.specs/` já estão na árvore de trabalho, não commitados; nenhuma alteração em código-fonte).
- **Branch**: `main`.
