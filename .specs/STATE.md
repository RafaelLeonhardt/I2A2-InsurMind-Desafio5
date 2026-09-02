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

- **Feature**: Épicos 2, 3, 4 e 5 (Histórias 2.1–2.6, 3.1–3.6, 4.1–4.4, 5.1–5.9) planejados; execução em andamento, história por história, seguindo a ordem de dependência.
- **Completed**: `spec.md`+`design.md`+`tasks.md` das 25 histórias (2.1–5.9) — ver auditoria de consistência cruzada e ADs no histórico desta seção. **História 2.1 (Coletar e normalizar dados do INMET) implementada e verificada PASS** (2026-09-01/02): Fix 1–4 em `552b378`, PASS confirmado em `c95279f`. **História 2.2 (Operar com segurança durante indisponibilidades meteorológicas) implementada e verificada PASS** (2026-09-02): T1–T7 `e7a3410..2a6efa8`; Verifier rodada 1 (FAIL) → Fix 1–6 `50e31fa` → rodada 2 (2 lacunas residuais de teste) → Fix 7–8 `5575981` → rodada 3 (`67ec913`) **PASS pleno — 18/18 RESIL verificados**, sensor 2/2 morto. **História 2.3 (Identificar eventos meteorológicos relevantes) implementada e verificada PASS** (2026-09-02): T1–T6 `6b2108c..22b2906`; Verifier rodada 1 achou FAIL (RISCO-09 + mutante M2 + 3 lacunas menores); Fix 1–5 em `1122288` (migração `0005` relaxa `regra_id`/`regra_versao` para `NULL`, AD-015); rodada 2 **PASS pleno — 13/13 RISCO cobertos**, sensor 3/3 morto; doc fix em `20a2b98`. **História 2.4 (Configurar, testar e versionar regras preventivas) implementada e verificada PASS** (2026-09-02): T1–T5 `73d2409..e0876e2` — `ValidadorRegra` (4 classes de invalidez, AD-013 evento↔produto), `RepositorioRegras.criar_nova_versao` (concorrência otimista, `ConflitoVersao`, mesmo padrão de `RepositorioExecucaoPreventiva`), `ServicoGestaoRegras.testar`/`.ativar` (reusa `AvaliadorRisco` de 2.3 contra cenários sintéticos já semeados, idempotente AD-002), roteador HTTP `regras` (4 rotas), superfície "Regras" (tabela versionada, formulário com erro por campo, painel de teste). Verifier rodada 1 (`e0876e2`) achou FAIL: 4 GAPs (REGRA-02/03/04/14) + 1 Partial (REGRA-10), 3/6 mutantes sobreviventes (M4 filtro `proveniencia=sintetico`, M5 off-by-one de `antecedencia_horas`, M6 ícones colapsados) + `ativar()` não chamava `avaliar` de fato, contradizendo a própria docstring/OpenAPI; Fix 1–8 em `6b33e16` (destaque: `ativar` passou a delegar a `self.testar(...)`, removendo 6 linhas duplicadas e tornando a promessa do contrato verdadeira). Rodada 2 achou 1 gap Minor residual (REGRA-04: "indicador visual" sem asserção, mutante M10 sobrevivente); Fix 9 em `c0d50d1` (6 linhas de asserção, zero produção). Rodada 3 (final) **PASS pleno — 15/15 REGRA verificados**, 15/16 mutantes mortos ao longo da história (M10 morto na correção), 340 backend + 189 frontend testes verdes; lição **L-024 promovida a `confirmed`** (2ª recorrência: distinção por texto+ícone+cor exige asserir os três sinais). **História 2.5 (Selecionar e explicar o público elegível) implementada e verificada PASS** (2026-09-02): T1–T6 `18a3547..36aafd6` — migração `0006` estende `elegibilidades_historicas` (`execucao_id` nulo=seed, `criterios`, `canal`, `UNIQUE` de dedução AD-10), `RegraSnapshot` (2.3) ganha `cobertura_exigida`, `AvaliadorElegibilidade` (5 critérios: área, tipo/situação de apólice, cobertura, participação em alertas — reusa `Criterio` de 2.3), `RepositorioCandidatosElegibilidade`/`RepositorioElegibilidades`, `ServicoAvaliacaoElegibilidade.avaliar_publico` (sem transição de estado, deferida à 2.6), roteador HTTP `elegibilidade` (quantidades + detalhe), extensão de `SuperficieEventoDecisao` com a seção "Público elegível". Verifier rodada 1 (`36aafd6`) achou FAIL grave: **1 blocker de produção real** — `obter_por_id` lançava `TypeError` em qualquer linha semeada (backfill de `criterios` na migração `0006` gravou um objeto JSON em vez de lista), fazendo a rota HTTP devolver `500` em vez de `404` — mais 3 GAPs/3 Partial de ELEG-04..09 (nome/área/canal lidos ao vivo via `JOIN`, violando AD-11; `UNIQUE` sem guarda de `apolice_id`; colunas da explicação sem asserção). Fix 1–8 em `c7c202e`: nova migração `0007` corrige o backfill (`'[]'`) e acrescenta `nome_segurado` como snapshot; `codigo_ibge_area` passa a ser derivado do próprio `criterios` já persistido, não mais via `JOIN`. Rodada 2 achou 4 lacunas residuais de asserção (nenhuma de produção); Fix 9–12 em `49bf647`, incluindo a extração de uma constante `OPERANDO_AREA_AFETADA` para eliminar por construção o acoplamento posicional entre o avaliador e o repositório. Rodada 3 (final) **PASS pleno — 10/10 ELEG verificados**, 22/35 mutantes mortos ao longo das três rodadas, 379 backend + 202 frontend testes verdes. `validate_state.py` confirma 0 erros para as cinco histórias.
- **In-progress**: nada — Histórias 2.1, 2.2, 2.3, 2.4 e 2.5 fechadas (implementação + fix + verificação, todos commitados; `git status` limpo).
- **Next step**: implementar **História 2.6** (Encerrar ou encaminhar a execução preventiva) — última história do Épico 2, seguindo a mesma ordem de dependência já registrada: Épico 2 (2.1 ✅ → 2.2 ✅ → 2.3 ✅ → 2.4 ✅ → 2.5 ✅ → 2.6) → Épico 3 (3.1→3.2→3.3→3.4→3.5→3.6) → Épico 4 (4.1/4.3 em paralelo lógico, 4.2 depois de 3.5/3.6, 4.4 por último) → Épico 5 (5.1–5.6 independentes/paralelizáveis, 5.7 depende de 5.1–5.6, 5.8 depende de tudo, 5.9 por último, publicação final sempre sob autorização explícita do usuário). A 2.6 tem um papel especial: é a que decide o terminal `aguardando_geracao`/`sem_elegiveis` a partir da contagem que a 2.5 devolve (`ServicoAvaliacaoElegibilidade.avaliar_publico` foi deliberadamente projetada para não transicionar estado, por conta disso), e é também a que a Review de planejamento (achado A5) apontou como responsável por decidir se existe uma execução "guarda-chuva" por ciclo completo de demonstração. Mesmo protocolo já rodado cinco vezes nesta sessão: implementar as tasks → gate verde → Verifier automático → fix→re-verify (máx. 3 rodadas) → commit da verificação → atualizar este Handoff.
- **Review**: revisão independente do planejamento (2026-08-30) produziu 8 achados. A1–A4 (críticos/altos) corrigidos como AD-012–AD-015. **A6/A7 permanecem abertos** (contradição spec↔design na 2.6 sobre o terminal técnico; critério de atribuição de `tipo` no `EventoMeteorologico` sem decisão formal, campos temporais já ancorados). **A5 parcialmente endereçado pela 2.2**: cada coleta esgotada (manual, automática ou nova tentativa) cria e fecha sua própria `ExecucaoPreventiva` lazy (só na falha) — RUNNER-01 ainda não tem uma execução "guarda-chuva" por ciclo completo de demonstração, decisão que cabe à 2.6 orquestrar. **A8 fica moot no MVP atual**: o único tipo sintético é `granizo` (AD-013) e o único tipo real é `chuva_intensa` — como a `UNIQUE(tipo, area, periodo_inicio, periodo_fim)` inclui `tipo`, um evento sintético nunca pode colidir com um real na prática; revisitar se uma história futura introduzir um cenário sintético de `chuva_intensa`.
- **Blockers**: nenhum. Riscos conhecidos: (1) Fix 5 da 2.1 (prova ao vivo do INMET) segue pendente por falta de rede na sessão — não bloqueia histórias seguintes; (2) `langchain`/`langchain-openai`/`langgraph` (3.1) e Playwright/`@axe-core/playwright` (5.8) são dependências novas sem versão fixada; (3) agregação de 4.4 lê ~9 fontes (custo aceito de PoC); (4) ferramenta de conversão Markdown→PDF (5.9) ainda não escolhida; (5) achados A6/A7 acima; (6) `EstadoSincronizacao.NORMALIZANDO` (2.1) e o estado `coletando` "em andamento" (2.2, RESIL-05) são inobserváveis em produção porque a coleta é síncrona ponta a ponta — limitação estrutural conhecida desde a Verificação rodada 2 da 2.1, reconfirmada na 2.2; o edge case de spec "reinício do backend com execução em `coletando`" (2.2) segue sem tratamento por causa dela; (7) `areas_monitoradas_inmet` (tabela de configuração versionada, AD-007) não é semeada por nenhum código — confirmado durante o smoke test manual da 2.2 T7 (banco de dev real veio vazio); nenhuma história ainda decidiu como/quando essa tabela é populada fora de testes, vale endereçar antes da demonstração final; (8) L-023 (2.3, aberta por decisão): RISCO-05/06 exigem comparar "medidas, área, severidade e período", mas `RegraSnapshot` não carrega nenhum campo de janela temporal e "período" nunca é comparado — a spec não define o resultado preciso, então não há defeito a corrigir, mas uma futura história que precise comparar período terá que estender `RegraSnapshot`; (9) `ServicoAvaliacaoRisco.avaliar_evento` (2.3), `ServicoAvaliacaoElegibilidade.avaliar_publico` (2.5), `SuperficieEventoDecisao` (2.3/2.5) e `SuperficieRegras` (2.4) não são chamados/roteados por nenhum caminho de produção ainda — mesma lacuna de integração já aceita para `SuperficieFonteMeteorologica` desde 2.1/2.2 (nenhuma das quatro superfícies está em `App.tsx`), a fechar quando a 2.6 ligar coleta → avaliação de risco → elegibilidade → encerramento/encaminhamento ponta a ponta e a navegação real for construída; (10) `ServicoAvaliacaoElegibilidade.avaliar_publico` (2.5) devolve a contagem de incluídos/excluídos mas deliberadamente não transiciona o estado da execução — por design, essa decisão (`aguardando_geracao` vs. `sem_elegiveis`) foi reservada à 2.6, que ainda não existe; qualquer teste E2E ponta a ponta só é possível depois dela.
- **Uncommitted files**: nenhum.
- **Branch**: `main`.
