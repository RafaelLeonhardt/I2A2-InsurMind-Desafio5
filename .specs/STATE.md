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

### AD-016
- **Decision**: Uma superfície de detalhe parametrizada por id (ex.: a execução de um evento específico, o detalhe de um resultado) é modelada estendendo `Superficie` (`PerfilContexto.tsx`) para um union discriminado por `tipo` com payload opcional (`{ tipo: 'evento-execucao'; execucaoId: string; perfilPai: Perfil }`), nunca por um router de URL nem por estado local duplicado em cada componente. `NavegacaoLateral` continua listando e selecionando só os `tipo`s "de topo" (sem payload, via `SUPERFICIES_TOPO_POR_PERFIL`); uma superfície de detalhe só é alcançada por uma ação dentro da superfície de topo correspondente (ex.: clicar numa linha de `SuperficieEventos`), e "voltar" chama `selecionarSuperficie` de volta para o `tipo` de topo pai.
- **Reason**: Decisão tomada na fase de Design da História 6.1 (`.specs/features/6-1-.../design.md`), com o usuário escolhendo explicitamente entre três abordagens apresentadas (payload no `Superficie` existente vs. estado local por componente vs. `react-router`). O projeto não tem nenhuma dependência de roteamento (`grep` em `package.json` não encontra nenhuma) e nenhuma spec do produto pede deep-link/URL endereçável; estender o mecanismo já usado em todo lugar (`usePerfilContexto`) é o menor diff que resolve o problema real (telas de detalhe precisam de um id que o `Superficie` de hoje, um union de strings simples, não carrega).
- **Trade-off**: `Superficie` deixa de ser um simples literal de string, tocando os 4 arquivos que hoje o consomem diretamente (`App.tsx`, `App.test.tsx`, `PerfilContexto.test.tsx`, `NavegacaoLateral.test.tsx`) — blast radius pequeno e conhecido, mapeado no Design de 6.1. Sem histórico de navegação global (voltar do navegador não funciona) — aceitável para um PoC sem requisito de deep-link.
- **Scope**: Toda superfície de detalhe parametrizada por id introduzida pelo Épico 6 em diante (6.1 já usa; 6.5 e 6.6 devem seguir o mesmo padrão em seus próprios `design.md`).
- **Date**: 2026-09-09
- **Status**: active

## Handoff

- **Feature**: Épico 6 (Histórias 6.1–6.9) — fecha as lacunas entre o protótipo de design e a aplicação real. Especificado por completo em 2026-09-09 (`spec.md` de cada história em `.specs/features/6-*`, todos passando `validate_spec.py`). Execução história por história, seguindo a ordem de dependência (6.1 é fundacional para 6.2/6.3/6.7; 6.5 depende de 6.2; 6.6 depende de 6.5).
- **Completed**: **História 6.1 (Navegar o painel administrativo e monitorar eventos climáticos) — Design, Tasks (T1–T8) e Execute completos, Verifier PASS em 2026-09-09** (`.specs/features/6-1-.../validation.md`; 7/7 ACs ADMNAV-01..07 com evidência `file:line`, 5/5 mutações do sensor mortas, 0 sobreviventes). Decisão de arquitetura registrada como **AD-016** (`Superficie` como union discriminado com payload — drill-down padrão do Épico 6, sem router novo). Backend: `RespostaEvento` ganhou `execucao_id`/`execucao_estado` via novo método `mapear_execucoes_por_evento()` em `RepositorioEventosMeteorologicos`, sem tocar no dataclass de domínio `EventoMeteorologico`. Frontend: `SUPERFICIES_POR_PERFIL` virou `SUPERFICIES_TOPO_POR_PERFIL` (5 novos itens de negócio do admin), `NavegacaoLateral`/`App.tsx` estendidos, nova superfície `SuperficieEventos` (lista + severidade derivada de `intensidade` + status da execução em 4 categorias + navegação para `SuperficieExecucao`). Ciclo Verifier: **rodada 1 FAIL** (2 gaps reais: severidade ausente da lista — Major; status da execução como enum bruto em vez das 4 categorias da spec — Minor; +1 gap de cobertura de teste — Minor) → 1 commit de correção (`f9a00c6`) → **rodada 2 PASS**. Gate final: backend 1099 testes + ruff + pyright limpos; frontend 461 testes + lint + build limpos.
- **História 6.2 (Acompanhar a execução e a decisão do evento) — Design inline (Medium, reusa AD-016, sem decisão de arquitetura nova) e Execute completos, Verifier PASS em 2026-09-09** (`.specs/features/6-2-.../validation.md`; 5/5 ACs PAINELEXEC-01..05 com evidência `file:line`, 3/3 mutações do sensor mortas). PAINELEXEC-01 e boa parte de 04/05 já estavam satisfeitos por código pré-existente (navegação da 6.1; `SuperficieEventoDecisao` da 2.5) — só ganharam evidência própria, sem mudança. Código novo, todo em `SuperficieExecucao.tsx`: qualquer estado `falhou_*` (não só `falhou_coleta`) vira categoria "exceção"; nova seção "Execuções correlacionadas" com `execucaoOrigemId`/`retentativas` como links navegáveis (mesmo padrão AD-016); `SuperficieEventoDecisao` embutida ampliada de "só `aguardando_geracao`" para toda etapa pós-coleta (inclui `sem_risco`/`sem_elegiveis`). Uma nota de spec-precision em PAINELEXEC-05 (destilada como lição candidata L-092: a coluna condicional que a spec descreve nunca é exercitável porque o campo `motivo` nunca existe na API — o mecanismo real, uma explicação sempre presente via "Ver critérios", cumpre a intenção). Gate final: frontend 467 testes + lint + build limpos (backend não tocado).
- **História 6.3 (Editar e testar regras de negócio) — Design inline (Medium, reusa `SuperficieRegras` 2.4 já existente, sem decisão de arquitetura nova) e Execute completos, Verifier PASS em 2026-09-09** (`.specs/features/6-3-.../validation.md`; REGRASADM-01/02/03 com evidência `file:line`, 2/2 mutações do sensor mortas). Escopo entregue: `App.tsx` monta `SuperficieRegras` (2.4) no case `'regras'`; corrigida uma Assumption errada da spec original (o componente não tem "seções Evento/Público elegível/Comunicação" nem estimativa de elegíveis — é tabela versionada + formulário, "Testar" valida contra eventos sintéticos de risco, não conta segurados); teste novo cobrindo o conflito de versão 409 (REGRASADM-03), comportamento já existente sem cobertura própria até então. **REGRASADM-04 (P2, estimativa de elegíveis) ficou Deferred por decisão explícita do usuário** — exige um endpoint novo de backend (contar segurados por área/tipo de apólice/cobertura) que não existe hoje; retomar como história própria se o produto priorizar. Gap conhecido não bloqueante: `SuperficieRegras.tsx` (2.4, não tocado) não distingue "há regras mas nenhuma ativa" de "há regra ativa" — agora alcançável pela primeira vez via navegação. Gate final: frontend 469 testes + lint + build limpos (backend não tocado).
- **História 6.7 (Monitorar a fonte meteorológica INMET) — Design inline (Medium, componente `SuperficieFonteMeteorologica` já pronto e exaustivamente testado — só integração de navegação) e Execute completos, Verifier PASS em 2026-09-09** (`.specs/features/6-7-.../validation.md`; 5/5 ACs MONITORFONTE-01..05 com evidência `file:line`, 2/2 mutações do sensor mortas). Escopo entregue: `App.tsx` monta `SuperficieFonteMeteorologica` no case `'fontes-de-dados'`; nenhuma mudança no componente em si. Gate final: frontend 470 testes + lint + build limpos (backend não tocado). Três lições candidatas não bloqueantes (L-095..L-097) sobre precisão de asserção em testes pré-existentes.
- **Next step**: **História 6.4 (Consultar segurados sintéticos) em andamento** — despachada a um sub-agente em background nesta sessão (ainda não retornou ao concluir este registro). Diferente de 6.2/6.3/6.7, 6.4 exige construção real: descoberto que `GET /segurados` só devolve `id`/`nome` (a Assumption original da spec presumia bairro/apólice/canal já disponíveis, o que é falso) — o sub-agente está estendendo o backend com um endpoint novo (`lista_segurados_detalhado` ou equivalente, `LEFT JOIN` com `apolices`, sem alterar o endpoint/método existentes usados pelo seletor "Visualizar como") e construindo `SuperficieSegurados` do zero, reusando `SuperficieApolice`/`SuperficieAlertas`/`SuperficieComunicados` (já somente-leitura, aceitam `seguradoId`) para a P3 "abrir contexto". Quando retomar: conferir o resultado do sub-agente, rodar o Verifier independente, e só então seguir para 6.5/6.6 (dependem de 6.2, já pronta) ou 6.8/6.9 (lado Segurado, independentes).
- **Known open items (not blocking anything)**:
  - **Épico 5, T5 (publicação autorizada) segue pendente.** O usuário foi consultado numa sessão anterior ("Publicar agora?") e respondeu **"Not now"** — decisão explícita de não autorizar a publicação, um estado terminal válido previsto pela AC ENTREGA-06 (a história continua pendente até autorização explícita separada). Quando o usuário pedir para publicar: (1) confirmar destino (serviço, repositório novo ou existente, visibilidade); (2) publicar manualmente via `git`/`gh` (nunca script automatizado, por design); (3) em caso de sucesso, marcar ENTREGA-06/07 como Verified e a História 5.9 (e o Épico 5 inteiro) como concluída; (4) em caso de falha, registrar o erro sanitizado em `docs/evidencias/` ou similar, preservar `docs/entrega/` intacto, e manter a história pendente para nova tentativa. Não presumir nem executar a publicação sem esse pedido explícito.
  - **REGRASADM-04 (estimativa de elegíveis, 6.3) fica como história/endpoint futuro** se o produto priorizar — precisa de um endpoint novo de backend (contagem de segurados por área/tipo de apólice/cobertura); `GET /segurados` hoje só devolve id/nome.
  - Histórias 6.4–6.9 têm `spec.md` mas ainda não passaram por Design/Tasks/Execute — 6.5 e 6.6 devem seguir o padrão AD-016 (`Superficie` com payload) já estabelecido em 6.1/6.2, em vez de reabrir a discussão de arquitetura de navegação.
  - Duas telas vistas só na imagem `10-edicao-regra-negocio` ("Usuários e perfis", "Configurações") ficaram fora do Épico 6 por falta de confirmação de escopo de produto (ver Out of Scope de 6.1/6.3).
  - `PREFS-04` (5.6) e a reativação após desativação de alertas seguem sem teste de integração ponta a ponta dedicado (gaps Minor não bloqueantes, aceitos nos Verifiers de 5.5/5.6).
  - `E2E-11` (5.8) tem 9 tokens visuais medidos que divergem de `DESIGN.md` — registrados e não silenciados em `testes-e2e/responsividade/sistema-visual.spec.ts:22-32`; a correção é "Out of Scope" de 5.8 por decisão do próprio `spec.md`.
  - Documentos originais da contradição A6/A7 (2.6, terminal técnico) não foram retroativamente editados, embora resolvida na prática pela implementação.
- **Lições consolidadas ativas** (aplicar em toda história nova, ver `.specs/LESSONS.md` para a lista completa confirmada/candidata): variar valores de campos irmãos na mesma fixture desde a primeira escrita em toda camada nova; todo módulo `api/*.ts` precisa de teste próprio para a tradução `snake_case`→`camelCase`; testar o valor não-padrão de todo campo booleano/enum em cada camada; atualizar `test_openapi_sincronizado.py` e `test_saude.py` juntos ao adicionar rota; atualizar a tabela de rastreabilidade de `spec.md` a cada task concluída; declarar SPEC_DEVIATION explícito com razão sempre que a implementação divergir do design; montar toda região `aria-live` sempre presente e vazia, nunca já preenchida; antes de fechar uma história de UI, confirmar que o componente novo está de fato montado e alcançável a partir de `App.tsx`/navegação real; um SPEC_DEVIATION que troca "editar 5 arquivos" por "um novo componente de composição" deve também declarar onde esse componente é conectado à aplicação real, não só justificar a escolha estrutural; quando o Done-when de uma task cita um artefato gerado como o lugar onde um desvio/checklist fica registrado, o gerador precisa copiar esse conteúdo para o artefato; quando uma correção de produção resolve um defeito que o cabeçalho de um teste documenta como aberto, atualizar esse cabeçalho no mesmo commit; quando um valor medido diverge do contrato de design, registrar o desvio e afirmar só as propriedades que realmente valem; **novas desde 5.9 (L-084..L-091, candidatas)**: nunca comparar a saída de um gerador contra o valor devolvido pela própria função sob teste — ancorar em um literal ou numa fonte independente (fez dois testes tautológicos passarem despercebidos na rodada 1 do Verifier); ao validar um documento gerado, afirmar o conteúdo do corpo de cada seção, nunca só a presença do cabeçalho; ao testar falha explícita, afirmar a mensagem da exceção, não só o tipo, para não passar por uma exceção levantada por outro motivo mais adiante; todo filtro de defesa em profundidade exige teste unitário direto — testar só a camada anterior (ex.: `.gitignore`) deixa o filtro sem cobertura própria; teste de auto-exclusão de um artefato só discrimina se o artefato já existir no momento da execução, então a operação precisa rodar duas vezes; conferir que cada requirement ID da spec tem exatamente uma task dona antes de fechar a fase Tasks; quando a AC proíbe segredo no pacote, escanear o conteúdo dos arquivos, não só os nomes de caminho.
- **Uncommitted files**: none — `git status --porcelain` limpo.
- **Branch**: main.
