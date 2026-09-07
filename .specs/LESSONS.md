# LESSONS - auto-maintained by scripts/lessons.py

> Machine-owned. Do NOT hand-edit. Changes are overwritten on the next `lessons.py` write.
> Canonical state lives in `.specs/lessons.json`. Edit lessons only via the script.
> promote_threshold=2 distinct features · window_days=45 · quarantine_threshold=2

## Confirmed (load these at Specify/Design)

Corroborated across multiple features. Safe to apply as guidance.

### L-003 - Name the exact HTTP status code in the spec for every refusal path; when the spec only says "explicit error", record the chosen status as a spec-precision gap instead of passing it silently.
- signal: `spec_precision_gap` · recurrence: 2 feature(s) · scope: `adaptadores/http` · harmful: 0
- features: 1-2-inicializar-e-restaurar-dados-sinteticos, 3-6-confirmar-e-executar-a-simulacao-sem-envio-real
- evidence: spec.md Edge Cases - src/backend/central_preventiva/adaptadores/http/dados_sinteticos.py:146 (adaptadores/http) (+2 more)
- last seen: 2026-09-04T20:20:21Z

### L-006 - When a spec requires a real-browser behavior jsdom cannot simulate (e.g. 200% zoom, real layout/measurement), flag it explicitly as needing manual/UAT verification in the spec or tasks file instead of leaving it silently uncovered by the automated suite.
- signal: `spec_precision_gap` · recurrence: 2 feature(s) · scope: `frontend/accessibility` · harmful: 0
- features: 1-3-verificar-a-prontidao-das-dependencias, 5-1-compreender-o-alerta-mais-relevante-na-visao-geral
- evidence: PRONT-13 (validation.md P2: Operar a superficie por teclado e em zoom 200% AC2) (frontend/accessibility) (+1 more)
- last seen: 2026-09-05T13:39:41Z

### L-013 - Fold port methods discovered during implementation back into the design document instead of leaving the deviation marker as their only record.
- signal: `spec_deviation` · recurrence: 2 feature(s) · scope: `ports` · harmful: 0
- features: 2-1-coletar-e-normalizar-dados-do-inmet, 4-3-registrar-a-primeira-visualizacao-do-comunicado
- evidence: aplicacao/portas_meteorologia.py:86,95,112 (ports) (+1 more)
- last seen: 2026-09-05T11:19:46Z

### L-014 - Test the intersection where two derivation conditions hold at once, so branch priority order is pinned instead of incidental.
- signal: `surviving_mutant` · recurrence: 2 feature(s) · scope: `frontend` · harmful: 0
- features: 2-2-operar-com-seguranca-durante-indisponibilidades-meteorologicas, 5-1-compreender-o-alerta-mais-relevante-na-visao-geral
- evidence: validation.md Sensor #3 — SuperficieFonteMeteorologica.tsx:55-58 (frontend) (+1 more)
- last seen: 2026-09-05T13:39:40Z

### L-024 - When a requirement demands distinction by text, icon and color, assert that all three signals differ across categories.
- signal: `spec_precision_gap` · recurrence: 2 feature(s) · scope: `frontend` · harmful: 0
- features: 2-3-identificar-eventos-meteorologicos-relevantes, 2-4-configurar-testar-e-versionar-regras-preventivas
- evidence: RISCO-12 - src/frontend/src/funcionalidades/evento-decisao/SuperficieEventoDecisao.test.tsx:80-126 (frontend) (+1 more)
- last seen: 2026-09-02T14:42:34Z

### L-033 - A return type declared in design.md must carry every field the acceptance criteria require to be persisted.
- signal: `spec_deviation` · recurrence: 4 feature(s) · scope: `design` · harmful: 0
- features: 3-2-gerar-mensagens-automaticamente-para-cada-canal, 3-3-avaliar-a-qualidade-e-a-seguranca-das-mensagens, 5-2-consultar-alertas-ativos-e-anteriores, 5-6-atualizar-preferencias-para-alertas-futuros
- evidence: SPEC_DEVIATION em src/backend/central_preventiva/adaptadores/ia/agente_redator.py:8 (design) (+3 more)
- last seen: 2026-09-06T23:04:54Z

### L-034 - Do not fix a migration number in design.md; assign the next number at implementation time from the migrations directory.
- signal: `spec_deviation` · recurrence: 5 feature(s) · scope: `persistence` · harmful: 0
- features: 3-2-gerar-mensagens-automaticamente-para-cada-canal, 3-3-avaliar-a-qualidade-e-a-seguranca-das-mensagens, 3-4-regenerar-mensagens-e-registrar-a-proveniencia-agentica, 3-6-confirmar-e-executar-a-simulacao-sem-envio-real, 5-6-atualizar-preferencias-para-alertas-futuros
- evidence: SPEC_DEVIATION em src/backend/central_preventiva/adaptadores/persistencia/migracoes/0010_mensagens.sql:3 (persistence) (+4 more)
- last seen: 2026-09-06T23:04:54Z

### L-059 - In a route's happy-path test, assert every field of the response contract; assertions on the use case's DTO do not discriminate the route's own field mapping.
- signal: `surviving_mutant` · recurrence: 2 feature(s) · scope: `routes` · harmful: 0
- features: 5-1-compreender-o-alerta-mais-relevante-na-visao-geral, 5-2-consultar-alertas-ativos-e-anteriores
- evidence: M11 — src/backend/testes/test_alerta_segurado_api.py:96 (validation.md rodada 2) (routes) (+1 more)
- last seen: 2026-09-05T23:01:02Z

### L-061 - A response field whose only assertion is its happy-path value is not discriminated; add a route case where the field takes its other value (synthetic origin, degraded source, false-to-true flag).
- signal: `surviving_mutant` · recurrence: 3 feature(s) · scope: `routes` · harmful: 0
- features: 5-1-compreender-o-alerta-mais-relevante-na-visao-geral, 5-2-consultar-alertas-ativos-e-anteriores, 5-3-consultar-a-apolice-sintetica-e-seu-uso-preventivo
- evidence: M14/M15 — src/backend/central_preventiva/adaptadores/http/alerta_segurado.py:115,117 (validation.md rodada 3) (routes) (+2 more)
- last seen: 2026-09-06T00:00:30Z

## Candidates (under observation - do NOT load as guidance yet)

Seen once or not yet corroborated. Tracked, not trusted.

### L-001 - When a spec precondition names an absence ("before any successful initialization"), test every database state that phrase admits - no schema at all, and schema without seed - not just the most convenient one.
- signal: `ac_gap` · recurrence: 1 feature(s) · scope: `testes/e2e` · harmful: 0
- features: 1-2-inicializar-e-restaurar-dados-sinteticos
- evidence: validation.md Fix 1 - src/backend/testes/test_dados_sinteticos_api.py:146 (testes/e2e)
- last seen: 2026-08-29T08:53:06Z

### L-002 - When the spec requires an error response to carry named fields without fixing their wording, assert each field is present and non-empty and record the missing wording as a spec-precision gap.
- signal: `spec_precision_gap` · recurrence: 1 feature(s) · scope: `adaptadores/http` · harmful: 0
- features: 1-2-inicializar-e-restaurar-dados-sinteticos
- evidence: spec.md SEED-13 - src/backend/testes/test_dados_sinteticos_api.py:174 (adaptadores/http) (+1 more)
- last seen: 2026-08-29T09:06:16Z

### L-004 - DuckDB checks foreign keys immediately and cannot defer them within a transaction, so a schema needing single-transaction delete-and-reinsert must declare relationships as documented logical foreign keys instead of REFERENCES.
- signal: `spec_deviation` · recurrence: 1 feature(s) · scope: `adaptadores/persistencia` · harmful: 0
- features: 1-2-inicializar-e-restaurar-dados-sinteticos
- evidence: tasks.md T8 SPEC_DEVIATION - src/backend/central_preventiva/adaptadores/persistencia/migracoes/0001_schema_inicial.sql:2 (adaptadores/persistencia) (+1 more)
- last seen: 2026-08-29T09:06:16Z

### L-005 - When a spec sets a numeric latency budget (e.g. p95 <= Ns), add a timing assertion (measured elapsed time against the threshold) in addition to structural evidence like 'no external I/O called' -- structural evidence alone leaves the numeric bound spec-unverified.
- signal: `spec_precision_gap` · recurrence: 1 feature(s) · scope: `backend/prontidao` · harmful: 0
- features: 1-3-verificar-a-prontidao-das-dependencias
- evidence: PRONT-03 (validation.md P1: Ver a prontidao consolidada AC3) (backend/prontidao)
- last seen: 2026-08-29T10:32:42Z

### L-007 - When a spec defines a literal fixed banner/label string, assert the exact combined text in a test, not just that its component substrings are each present somewhere in the DOM.
- signal: `ac_gap` · recurrence: 1 feature(s) · scope: `frontend` · harmful: 0
- features: 1-4-alternar-o-contexto-demonstrativo
- evidence: CTX-02 (frontend)
- last seen: 2026-08-29T20:09:23Z

### L-008 - When a spec defines a precise CSS visual value (e.g. an exact focus-outline width in pixels), add a computed-style assertion or explicitly document it as a UAT-only manual check instead of leaving it silently unasserted.
- signal: `spec_precision_gap` · recurrence: 1 feature(s) · scope: `frontend` · harmful: 0
- features: 1-4-alternar-o-contexto-demonstrativo
- evidence: CTX-18 (frontend)
- last seen: 2026-08-29T20:09:23Z

### L-009 - Assert the production default constant itself, never only a value the test injects in its place.
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `scheduling` · harmful: 0
- features: 2-1-coletar-e-normalizar-dados-do-inmet
- evidence: portas_meteorologia.py:64 (mutant M2: INTERVALO_SEGUNDOS_COLETA 900->60 survived 235/235) (scheduling)
- last seen: 2026-09-02T01:54:07Z

### L-010 - Drive route tests through the application lifespan whenever the criterion depends on background work being active.
- signal: `ac_gap` · recurrence: 1 feature(s) · scope: `routes` · harmful: 0
- features: 2-1-coletar-e-normalizar-dados-do-inmet
- evidence: INMET-04 - testes/test_meteorologia_api.py:71 (routes)
- last seen: 2026-09-02T01:54:07Z

### L-011 - Give every measurable clause of a criterion its own assertion, including latency budgets, or downgrade the clause in the spec explicitly.
- signal: `ac_gap` · recurrence: 1 feature(s) · scope: `observability` · harmful: 0
- features: 2-1-coletar-e-normalizar-dados-do-inmet
- evidence: INMET-15 - no perf_counter/p95 assertion anywhere in the repository (observability)
- last seen: 2026-09-02T01:54:07Z

### L-012 - Cover every state a criterion enumerates, not only the happy-path state.
- signal: `spec_precision_gap` · recurrence: 1 feature(s) · scope: `frontend` · harmful: 0
- features: 2-1-coletar-e-normalizar-dados-do-inmet
- evidence: INMET-06 - SuperficieFonteMeteorologica.test.tsx:128 (frontend)
- last seen: 2026-09-02T01:54:08Z

### L-015 - Implement and assert every noun listed in an acceptance criterion outcome, including derived values the API does not already return.
- signal: `ac_gap` · recurrence: 1 feature(s) · scope: `backend` · harmful: 0
- features: 2-2-operar-com-seguranca-durante-indisponibilidades-meteorologicas
- evidence: RESIL-06 — nenhuma ocorrencia de 'idade' em adaptadores/http, api/, funcionalidades/ (backend)
- last seen: 2026-09-02T03:53:01Z

### L-016 - When an acceptance criterion demands text, icon and color, assert all three dimensions, not only the text label.
- signal: `ac_gap` · recurrence: 1 feature(s) · scope: `frontend` · harmful: 0
- features: 2-2-operar-com-seguranca-durante-indisponibilidades-meteorologicas
- evidence: RESIL-15 — SuperficieFonteMeteorologica.test.tsx:225-307 asserts only text (frontend)
- last seen: 2026-09-02T03:53:01Z

### L-017 - Define in the spec which state wins when more than one state condition is true at the same time.
- signal: `spec_precision_gap` · recurrence: 1 feature(s) · scope: `spec` · harmful: 0
- features: 2-2-operar-com-seguranca-durante-indisponibilidades-meteorologicas
- evidence: RESIL-15/16 — spec.md:104 nao define precedencia entre estados (spec)
- last seen: 2026-09-02T03:53:01Z

### L-018 - State explicitly whether a configurable value must be externally configurable at runtime or a named constant is sufficient.
- signal: `spec_precision_gap` · recurrence: 1 feature(s) · scope: `spec` · harmful: 0
- features: 2-2-operar-com-seguranca-durante-indisponibilidades-meteorologicas
- evidence: RESIL-03 — spec.md:33 pede env var, README.md:89-92 entrega constantes (spec)
- last seen: 2026-09-02T03:53:01Z

### L-019 - Test a threshold or bucketing function at each exact boundary value, not only mid-range values, so a comparison operator cannot be relaxed undetected.
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `frontend` · harmful: 0
- features: 2-2-operar-com-seguranca-durante-indisponibilidades-meteorologicas
- evidence: src/frontend/src/funcionalidades/fonte-meteorologica/SuperficieFonteMeteorologica.tsx:99 - mutante 'diffMinutos < 60' -> '<= 60' sobreviveu (34/34 passaram) (frontend)
- last seen: 2026-09-02T04:09:44Z

### L-020 - Choose fixture values that differ from plausible hardcoded defaults so a wrong-value bug cannot pass the assertion.
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `testing` · harmful: 0
- features: 2-3-identificar-eventos-meteorologicos-relevantes
- evidence: M2 - src/backend/central_preventiva/aplicacao/avaliacao_risco.py:96 / testes/test_avaliacao_risco.py:30 (testing)
- last seen: 2026-09-02T12:08:04Z

### L-021 - When a NOT NULL column blocks persisting an outcome an acceptance criterion requires, relax the schema instead of silently skipping the write.
- signal: `ac_gap` · recurrence: 1 feature(s) · scope: `persistence` · harmful: 0
- features: 2-3-identificar-eventos-meteorologicos-relevantes
- evidence: RISCO-09 - src/backend/central_preventiva/aplicacao/avaliacao_risco.py:86-93 (persistence)
- last seen: 2026-09-02T12:08:04Z

### L-022 - Put threshold boundary examples in the documentation artifact the requirement names, not only in the test file.
- signal: `spec_precision_gap` · recurrence: 1 feature(s) · scope: `docs` · harmful: 0
- features: 2-3-identificar-eventos-meteorologicos-relevantes
- evidence: RISCO-02 - .specs/features/2-3-identificar-eventos-meteorologicos-relevantes/design.md:136 (docs)
- last seen: 2026-09-02T12:08:04Z

### L-023 - Compare and assert every operand a requirement enumerates, or record explicitly why an operand is not compared.
- signal: `spec_precision_gap` · recurrence: 1 feature(s) · scope: `domain` · harmful: 0
- features: 2-3-identificar-eventos-meteorologicos-relevantes
- evidence: RISCO-05/RISCO-06 - src/backend/central_preventiva/dominio/avaliador_risco.py:102-137 (domain)
- last seen: 2026-09-02T12:08:04Z

### L-025 - When a GET endpoint's response fields are added to satisfy an AC, verify the frontend actually renders those specific fields instead of independently re-fetching the same data from another endpoint - a passing test can mock unused fields without ever asserting they are displayed.
- signal: `spec_precision_gap` · recurrence: 1 feature(s) · scope: `execucao,frontend-api-contract` · harmful: 0
- features: 2-6-encerrar-ou-encaminhar-a-execucao-preventiva
- evidence: validation.md#Finding-1 (SuperficieExecucao.tsx never reads execucao.publicoElegivelTotal/publicoElegivelPrevia) (execucao,frontend-api-contract)
- last seen: 2026-09-02T18:21:42Z

### L-026 - When a spec enumerates several distinct observable attributes for a state (e.g. codigo, causa, impacto, ultimo marco), verify each one is a literal, separately inspectable field - not silently folded into another field's free text.
- signal: `spec_precision_gap` · recurrence: 1 feature(s) · scope: `execucao,estados-terminais` · harmful: 0
- features: 2-6-encerrar-ou-encaminhar-a-execucao-preventiva
- evidence: validation.md#Finding-2 (spec P2 AC5: falha interna deve expor codigo causa impacto e ultimo marco, mas nenhum campo impacto e' anexado ao marco falhou_coleta) (execucao,estados-terminais)
- last seen: 2026-09-02T18:21:42Z

### L-027 - Scope an Idempotency-Key by the resource it acts on: when the mutable POST carries its target only in the path and has an empty body, include that identifier in the request hash or the operation name.
- signal: `ac_gap` · recurrence: 1 feature(s) · scope: `http-routes` · harmful: 0
- features: 3-1-preparar-a-producao-agentica-com-dados-minimos
- evidence: spec.md Edge Case 1; src/backend/central_preventiva/adaptadores/http/preflight_ia.py:242 (http-routes)
- last seen: 2026-09-03T12:23:10Z

### L-028 - When a snapshot is copied between rows, assert column-by-column content identity, not just the number of copied rows.
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `repo-layer` · harmful: 0
- features: 3-1-preparar-a-producao-agentica-com-dados-minimos
- evidence: validation.md mutation M5; src/backend/central_preventiva/adaptadores/persistencia/repositorio_elegibilidade.py:189 (repo-layer)
- last seen: 2026-09-03T12:23:10Z

### L-029 - Do not accept an acceptance criterion that lists a catch-all clause such as other supported parameters; enumerate every configurable value the story must expose.
- signal: `spec_precision_gap` · recurrence: 1 feature(s) · scope: `spec-authoring` · harmful: 0
- features: 3-1-preparar-a-producao-agentica-com-dados-minimos
- evidence: PREFL-05 (spec-authoring)
- last seen: 2026-09-03T12:23:10Z

### L-030 - When a task leaves an acceptance criterion with no component that a user can actually reach, add the missing surface in the story rather than deferring it, and record it as a declared deviation.
- signal: `spec_deviation` · recurrence: 1 feature(s) · scope: `tasks-authoring` · harmful: 0
- features: 3-1-preparar-a-producao-agentica-com-dados-minimos
- evidence: src/backend/central_preventiva/adaptadores/ia/verificador_disponibilidade_openai.py:7; montador_contexto_agente.py:11; repositorio_contextos_agente.py:7; aplicacao/preflight_ia.py:8 (tasks-authoring)
- last seen: 2026-09-03T12:23:10Z

### L-031 - When a criterion says a rule applies before and after an operation, state what the before check validates, or it cannot be asserted precisely.
- signal: `spec_precision_gap` · recurrence: 1 feature(s) · scope: `spec` · harmful: 0
- features: 3-2-gerar-mensagens-automaticamente-para-cada-canal
- evidence: GERAR-02 (validation.md, Spec-Anchored ACs) (spec)
- last seen: 2026-09-03T17:33:20Z

### L-032 - Verify that the integration point named in design.md actually exists in the current code before implementing against it.
- signal: `spec_deviation` · recurrence: 1 feature(s) · scope: `design` · harmful: 0
- features: 3-2-gerar-mensagens-automaticamente-para-cada-canal
- evidence: SPEC_DEVIATION em src/backend/central_preventiva/aplicacao/preflight_ia.py:275 (design)
- last seen: 2026-09-03T17:33:20Z

### L-035 - When an acceptance criterion distinguishes an uninterpretable model response from a structured rejection, give the agent call a third return outcome instead of reusing the rejection value or raising.
- signal: `spec_deviation` · recurrence: 1 feature(s) · scope: `adaptadores-ia` · harmful: 0
- features: 3-3-avaliar-a-qualidade-e-a-seguranca-das-mensagens
- evidence: src/backend/central_preventiva/adaptadores/ia/agente_critico.py:14 (SPEC_DEVIATION: avaliar devolve AvaliacaoCritica | None) (adaptadores-ia)
- last seen: 2026-09-04T10:25:44Z

### L-036 - When a criterion defers half of its outcome to a later story, name the observable state this story must leave behind, or that half cannot be asserted.
- signal: `spec_precision_gap` · recurrence: 1 feature(s) · scope: `spec` · harmful: 0
- features: 3-3-avaliar-a-qualidade-e-a-seguranca-das-mensagens
- evidence: CRIT-06 (spec)
- last seen: 2026-09-04T10:25:44Z

### L-037 - Do not accept a subjective quality adjective such as accessible or clear as an acceptance criterion outcome without naming the observable text or element it requires.
- signal: `spec_precision_gap` · recurrence: 1 feature(s) · scope: `spec` · harmful: 0
- features: 3-3-avaliar-a-qualidade-e-a-seguranca-das-mensagens
- evidence: CRIT-09 (spec)
- last seen: 2026-09-04T10:25:44Z

### L-038 - When a resumption path rebuilds an attempt or sequence number from persisted state, assert that number on the row the resumption writes, not only the final state it reaches.
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `resume` · harmful: 0
- features: 3-4-regenerar-mensagens-e-registrar-a-proveniencia-agentica
- evidence: M7 - src/backend/central_preventiva/aplicacao/geracao_mensagens.py:514 (resume)
- last seen: 2026-09-04T11:41:50Z

### L-039 - Do not give a graph or pure-logic component a direct repository dependency in design.md; declare a port the use case implements, or composition acquires a cycle.
- signal: `spec_deviation` · recurrence: 1 feature(s) · scope: `design` · harmful: 0
- features: 3-4-regenerar-mensagens-e-registrar-a-proveniencia-agentica
- evidence: SPEC_DEVIATION - src/backend/central_preventiva/aplicacao/grafos/geracao_mensagem.py:27 (design)
- last seen: 2026-09-04T11:41:50Z

### L-040 - When design.md says new data arrives through an existing context object, check that context's own minimization contract admits it; otherwise change the call signature explicitly.
- signal: `spec_deviation` · recurrence: 1 feature(s) · scope: `design` · harmful: 0
- features: 3-4-regenerar-mensagens-e-registrar-a-proveniencia-agentica
- evidence: SPEC_DEVIATION - src/backend/central_preventiva/adaptadores/ia/agente_redator.py:15 (design)
- last seen: 2026-09-04T11:41:50Z

### L-041 - Declare collection fields in design.md with the project's immutable collection type when the surrounding domain values are frozen.
- signal: `spec_deviation` · recurrence: 1 feature(s) · scope: `design` · harmful: 0
- features: 3-4-regenerar-mensagens-e-registrar-a-proveniencia-agentica
- evidence: SPEC_DEVIATION - src/backend/central_preventiva/aplicacao/grafos/geracao_mensagem.py:38 (design)
- last seen: 2026-09-04T11:41:50Z

### L-042 - Seed one resumption test per durable marker the recovery code branches on, including the marker between persisting an outcome and applying its state transition.
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `resume` · harmful: 0
- features: 3-4-regenerar-mensagens-e-registrar-a-proveniencia-agentica
- evidence: validation.md M8 - src/backend/central_preventiva/aplicacao/geracao_mensagens.py:480 (resume)
- last seen: 2026-09-04T16:58:49Z

### L-043 - When a criterion requires two independent approvals, seed the case where only one of them holds and assert exclusion; otherwise the second conjunct is never discriminated.
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `application` · harmful: 0
- features: 3-5-revisar-e-decidir-o-lote-de-comunicacao
- evidence: M4 src/backend/central_preventiva/aplicacao/revisao_lote.py:645 (application)
- last seen: 2026-09-04T18:14:18Z

### L-044 - A state trigger placed inside a per-item loop never fires when the loop body is empty; also invoke it once after the loop so the zero-pending case still converges.
- signal: `ac_gap` · recurrence: 1 feature(s) · scope: `application` · harmful: 0
- features: 3-5-revisar-e-decidir-o-lote-de-comunicacao
- evidence: REVISAO-01 src/backend/central_preventiva/aplicacao/geracao_mensagens.py:467 (application)
- last seen: 2026-09-04T18:14:26Z

### L-045 - Two enums that share a literal member value are indistinguishable to behavioural tests, so a swap between them is caught only by the static type check - keep the type checker inside the mandatory gate.
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `domain` · harmful: 0
- features: 3-5-revisar-e-decidir-o-lote-de-comunicacao
- evidence: M2 src/backend/central_preventiva/aplicacao/geracao_mensagens.py:513 (domain)
- last seen: 2026-09-04T18:14:26Z

### L-046 - Extending a component that design.md declares reused without change is a deviation - mark it with the project's deviation marker even when the signature change is backward compatible.
- signal: `spec_deviation` · recurrence: 1 feature(s) · scope: `design` · harmful: 0
- features: 3-5-revisar-e-decidir-o-lote-de-comunicacao
- evidence: design.md:44 vs src/backend/central_preventiva/adaptadores/persistencia/repositorio_mensagens.py:241 (design)
- last seen: 2026-09-04T18:14:26Z

### L-047 - When a design requires a repository write to join the caller's open transaction, declare the caller-connection parameter in that method's signature; a signature without it contradicts the atomicity the same design demands.
- signal: `spec_deviation` · recurrence: 1 feature(s) · scope: `repo-layer` · harmful: 0
- features: 3-6-confirmar-e-executar-a-simulacao-sem-envio-real
- evidence: repositorio_entregas_simuladas.py:14-19 e repositorio_execucao_preventiva.py:310-315 (SPEC_DEVIATION) — design.md:75 exige atomicidade sem declarar o parametro (repo-layer)
- last seen: 2026-09-04T20:20:12Z

### L-048 - Before a task says to extend an existing endpoint, verify that endpoint belongs to the resource module named in the task's Where field; otherwise name the new route explicitly.
- signal: `spec_deviation` · recurrence: 1 feature(s) · scope: `routes` · harmful: 0
- features: 3-6-confirmar-e-executar-a-simulacao-sem-envio-real
- evidence: adaptadores/http/simulacao.py:17-22 (SPEC_DEVIATION) — tasks.md T4 manda estender GET /execucoes/{id}, rota de outro recurso (routes)
- last seen: 2026-09-04T20:20:21Z

### L-049 - Declare in design.md every use-case parameter the idempotency scoping and the error-handling table's guards require, not only the domain arguments.
- signal: `spec_deviation` · recurrence: 1 feature(s) · scope: `design` · harmful: 0
- features: 3-6-confirmar-e-executar-a-simulacao-sem-envio-real
- evidence: aplicacao/simulacao.py:38-44 (SPEC_DEVIATION) — design.md:65 omite reconhecimento e hash_requisicao (design)
- last seen: 2026-09-04T20:20:21Z

### L-050 - When testing a sortable table, assert the actual rendered row order after activating sort, not only the aria-sort attribute value.
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `frontend-tables` · harmful: 0
- features: 4-1-consolidar-resultados-e-estados-da-simulacao
- evidence: src/frontend/src/funcionalidades/resultados/SuperficieResultados.tsx:122 (frontend-tables)
- last seen: 2026-09-04T23:41:41Z

### L-051 - When a guard condition is only ever true because an invariant is enforced elsewhere in the codebase, add a direct unit test for the guard branch itself instead of relying on the invariant to keep it correct.
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `backend-aplicacao` · harmful: 0
- features: 4-2-inspecionar-o-resultado-individual
- evidence: src/backend/central_preventiva/aplicacao/detalhe_resultado.py:209-212 (backend-aplicacao)
- last seen: 2026-09-05T01:20:34Z

### L-052 - An INSERT ... ON CONFLICT DO NOTHING on a UNIQUE column does not by itself absorb a genuinely concurrent writer; wrap the INSERT in a catch for the driver's constraint/transaction-conflict exceptions (DuckDB: ConstraintException, TransactionException) whenever more than one caller can race on the same key, and prove it with a real multi-threaded test, not a simulated one.
- signal: `spec_deviation` · recurrence: 1 feature(s) · scope: `persistence,repo-layer` · harmful: 0
- features: 4-3-registrar-a-primeira-visualizacao-do-comunicado
- evidence: src/backend/central_preventiva/adaptadores/persistencia/repositorio_visualizacoes_comunicado.py:10-20 (SPEC_DEVIATION, verified independently with a real-thread stress test); same unguarded ON CONFLICT DO NOTHING pattern also present, unverified, in repositorio_meteorologia.py:107-124, repositorio_elegibilidade.py:~135, repositorio_avaliacoes_criticas.py:~99 (persistence,repo-layer)
- last seen: 2026-09-05T11:19:46Z

### L-053 - When a design gives one use case two independently reachable HTTP entry points (e.g. GET and POST) that both must enforce the same ownership check, declare the ownership id and an Optional-friendly return on every such method's signature, not only on the first one design.md happens to specify.
- signal: `spec_deviation` · recurrence: 1 feature(s) · scope: `design,application` · harmful: 0
- features: 4-3-registrar-a-primeira-visualizacao-do-comunicado
- evidence: src/backend/central_preventiva/aplicacao/visualizacao_comunicado.py:12-18 (SPEC_DEVIATION) (design,application)
- last seen: 2026-09-05T11:19:46Z

### L-054 - In an async component test, wait with waitFor or a timer tick before asserting that a discarded stale response did not render; a single microtask tick passes even when the staleness guard is removed.
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `frontend` · harmful: 0
- features: 5-1-compreender-o-alerta-mais-relevante-na-visao-geral
- evidence: validation.md sensor M6 - src/frontend/src/funcionalidades/segurado/VisaoGeralSegurado.test.tsx:207 (frontend)
- last seen: 2026-09-05T13:39:40Z

### L-055 - Assert every field an acceptance criterion says the interface must display, including dates and timestamps rendered as plain text.
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `frontend` · harmful: 0
- features: 5-1-compreender-o-alerta-mais-relevante-na-visao-geral
- evidence: validation.md sensor M8 - src/frontend/src/funcionalidades/segurado/VisaoGeralSegurado.tsx:170 (frontend)
- last seen: 2026-09-05T13:39:41Z

### L-056 - Do not write UI copy that promises navigation to surfaces a later story will build; describe only what the current shell actually offers.
- signal: `ac_gap` · recurrence: 1 feature(s) · scope: `frontend` · harmful: 0
- features: 5-1-compreender-o-alerta-mais-relevante-na-visao-geral
- evidence: validation.md VISAO-04 - src/frontend/src/funcionalidades/segurado/VisaoGeralSegurado.tsx:133 (frontend)
- last seen: 2026-09-05T13:39:41Z

### L-057 - When a marked deviation drops a dependency that design.md declared, add a test that exercises the real seeded state the deviation was chosen for, so the justification cannot silently rot.
- signal: `spec_deviation` · recurrence: 1 feature(s) · scope: `design` · harmful: 0
- features: 5-1-compreender-o-alerta-mais-relevante-na-visao-geral
- evidence: validation.md SPEC_DEVIATION - src/backend/central_preventiva/aplicacao/alerta_segurado.py:14 (design)
- last seen: 2026-09-05T13:39:41Z

### L-058 - When a boolean state flag selects which of two mutually exclusive states renders, assert the branch where it still holds its initial value, not only the branch after it flips.
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `frontend` · harmful: 0
- features: 5-1-compreender-o-alerta-mais-relevante-na-visao-geral
- evidence: M9 — VisaoGeralSegurado.tsx:67 (validation.md rodada 2) (frontend)
- last seen: 2026-09-05T21:41:14Z

### L-060 - A fix that only deletes misleading copy needs an assertion that the copy stays deleted, or nothing prevents it from returning.
- signal: `ac_gap` · recurrence: 1 feature(s) · scope: `frontend` · harmful: 0
- features: 5-1-compreender-o-alerta-mais-relevante-na-visao-geral
- evidence: VISAO-04 — src/frontend/src/funcionalidades/segurado/VisaoGeralSegurado.tsx:132 (validation.md rodada 2) (frontend)
- last seen: 2026-09-05T21:41:21Z

### L-062 - Before closing a feature, check that every scenario the Test Coverage Matrix names for each layer exists as a real test; a planned scenario can go missing without any gate failing.
- signal: `ac_gap` · recurrence: 1 feature(s) · harmful: 0
- features: 5-1-compreender-o-alerta-mais-relevante-na-visao-geral
- evidence: VISAO-05 — tasks.md Test Coverage Matrix (roteador HTTP: fonte degradada) sem teste correspondente (validation.md rodada 3)
- last seen: 2026-09-05T22:03:19Z

### L-063 - When a requirement demands distinction by text, icon and color, assert that all three signals differ across categories.
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `frontend` · harmful: 0
- features: 5-2-consultar-alertas-ativos-e-anteriores
- evidence: validation.md sensor M8 - SuperficieAlertas.tsx:60-68 (frontend)
- last seen: 2026-09-05T23:01:02Z

### L-064 - Test per-item selection and focus-restoration behaviour with a list of at least three items, acting on one that is not the first, so the right item is distinguishable from the first item.
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `frontend` · harmful: 0
- features: 5-2-consultar-alertas-ativos-e-anteriores
- evidence: validation.md sensor M7 - SuperficieAlertas.test.tsx:178-190 (frontend)
- last seen: 2026-09-05T23:01:41Z

### L-065 - Implement and assert each clause of a compound acceptance criterion separately; an empty state required to show both an explanation and a next action needs an assertion for each.
- signal: `ac_gap` · recurrence: 1 feature(s) · scope: `frontend` · harmful: 0
- features: 5-2-consultar-alertas-ativos-e-anteriores
- evidence: validation.md AC ALERTAS-02 - SuperficieAlertas.tsx:329-336 (frontend)
- last seen: 2026-09-05T23:01:41Z

### L-066 - Before a Tech Decision says to reuse an existing component, confirm that component actually exists in the codebase; a reuse claim about a nonexistent component becomes a deviation the implementer must discover.
- signal: `spec_deviation` · recurrence: 1 feature(s) · scope: `design` · harmful: 0
- features: 5-2-consultar-alertas-ativos-e-anteriores
- evidence: validation.md SPEC_DEVIATION ALERTAS-04 - design.md:108 vs SuperficieFonteMeteorologica.tsx:135 (design)
- last seen: 2026-09-05T23:01:41Z

### L-067 - When an acceptance criterion says a selection must be announced, assert the content of the live region, not only where the focus lands.
- signal: `spec_precision_gap` · recurrence: 1 feature(s) · scope: `frontend/accessibility` · harmful: 0
- features: 5-2-consultar-alertas-ativos-e-anteriores
- evidence: validation.md AC ALERTAS-03 - SuperficieAlertas.tsx:213-215 (frontend/accessibility)
- last seen: 2026-09-05T23:01:41Z

### L-068 - When a criterion requires visually distinct renderings, assert something derived from the rendered output itself, not only a test-only marker attribute that a wrong rendering could still carry.
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `frontend` · harmful: 0
- features: 5-2-consultar-alertas-ativos-e-anteriores
- evidence: validation.md sensor M8b - SuperficieAlertas.test.tsx:119-123 vs SuperficieAlertas.tsx:60-76 (frontend)
- last seen: 2026-09-05T23:27:17Z

### L-069 - Test a date comparison at its boundary - a value exactly equal to the reference date - not only values far in the past and far in the future.
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `dominio` · harmful: 0
- features: 5-3-consultar-a-apolice-sintetica-e-seu-uso-preventivo
- evidence: M1 - src/backend/central_preventiva/aplicacao/apolice_segurado.py:90 (validation.md Sensor) (dominio)
- last seen: 2026-09-06T00:00:30Z

### L-070 - A frontend API client module needs its own test asserting every translated field; component tests that mock the module whole do not discriminate its field mapping.
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `frontend/api` · harmful: 0
- features: 5-3-consultar-a-apolice-sintetica-e-seu-uso-preventivo
- evidence: MF6/MF7 - src/frontend/src/api/apoliceSegurado.ts:92,113 (validation.md Sensor) (frontend/api)
- last seen: 2026-09-06T00:00:30Z

### L-071 - An edge case that forbids showing unrelated items needs a negative assertion that the extra item is absent, scoped to the section under test - asserting the expected item is present proves nothing.
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `frontend` · harmful: 0
- features: 5-3-consultar-a-apolice-sintetica-e-seu-uso-preventivo
- evidence: MF5 - src/frontend/src/funcionalidades/segurado/SuperficieApolice.tsx:259 (validation.md Sensor) (frontend)
- last seen: 2026-09-06T00:00:30Z

### L-072 - Assert a forbidden-vocabulary rule against text produced by production code, not against strings the test itself authored.
- signal: `spec_precision_gap` · recurrence: 1 feature(s) · scope: `testes` · harmful: 0
- features: 5-3-consultar-a-apolice-sintetica-e-seu-uso-preventivo
- evidence: APOLICE-02 - src/backend/testes/test_apolice_segurado.py:229-231 (validation.md nota A) (testes)
- last seen: 2026-09-06T00:00:30Z

### L-073 - Any new HTTP route must also be added to the exhaustive OpenAPI route-allowlist guard test (test_saude.py), not only to the OpenAPI-contract-sync test — check both when a task adds an endpoint.
- signal: `gate_fail` · recurrence: 1 feature(s) · scope: `backend/api` · harmful: 0
- features: 5-4-entender-como-a-mensagem-foi-criada
- evidence: src/backend/testes/test_saude.py:30 (backend/api)
- last seen: 2026-09-06T16:22:55Z

### L-074 - Quando um critério exige manter caminhos de navegação, defina na spec a afordância verificável (link, item de menu) e asserte o papel navegável, não a presença do rótulo em prosa.
- signal: `spec_precision_gap` · recurrence: 1 feature(s) · scope: `frontend-superficies` · harmful: 0
- features: 5-5-consultar-o-historico-de-comunicados
- evidence: SuperficieComunicados.test.tsx:122-124 (AC2, P1 lista) (frontend-superficies)
- last seen: 2026-09-06T21:31:41Z

### L-075 - Monte a região aria-live sempre presente e vazia, trocando só o texto depois, porque uma região viva inserida ja preenchida nao e anunciada e toHaveTextContent nao distingue os dois casos.
- signal: `spec_precision_gap` · recurrence: 1 feature(s) · scope: `frontend-superficies` · harmful: 0
- features: 5-5-consultar-o-historico-de-comunicados
- evidence: SuperficieComunicados.test.tsx:191-192 (AC2, P2 acessibilidade) (frontend-superficies)
- last seen: 2026-09-06T21:31:49Z

### L-076 - Quando o design exige um campo derivado que o dataclass de retorno declarado nao possui, declare no proprio design o tipo de retorno novo em vez de reusar o existente.
- signal: `spec_deviation` · recurrence: 1 feature(s) · scope: `backend-persistencia` · harmful: 0
- features: 5-5-consultar-o-historico-de-comunicados
- evidence: adaptadores/persistencia/repositorio_entregas_simuladas.py:21-26 (backend-persistencia)
- last seen: 2026-09-06T21:31:49Z

### L-077 - When a design gives a PUT optimistic concurrency via versao_esperada, it must also specify the paired GET the client needs to read the current version before the first edit.
- signal: `spec_deviation` · recurrence: 1 feature(s) · scope: `adaptadores/http` · harmful: 0
- features: 5-6-atualizar-preferencias-para-alertas-futuros
- evidence: tasks.md T4 SPEC_DEVIATION - src/backend/central_preventiva/adaptadores/http/preferencias_segurado.py:8-12 (adaptadores/http)
- last seen: 2026-09-06T23:05:02Z

### L-078 - When design.md argues an AC is already guaranteed by an earlier story's architecture, add at least one integration test in the current feature that exercises the new write against that guarantee instead of relying only on the earlier story's own tests.
- signal: `spec_precision_gap` · recurrence: 1 feature(s) · scope: `aplicacao` · harmful: 0
- features: 5-6-atualizar-preferencias-para-alertas-futuros
- evidence: validation.md P1: Efeito so futuro e preservacao de historico AC1 - PREFS-04 (aplicacao)
- last seen: 2026-09-06T23:05:03Z

### L-079 - Before marking a UI story done, confirm its new top-level component is actually mounted and reachable from the app's real entry point (App.tsx / router / nav config), not just rendered in its own isolated test — a correctly tested component nobody mounts delivers zero acceptance criteria to a real user.
- signal: `ac_gap` · recurrence: 1 feature(s) · scope: `frontend-integration` · harmful: 0
- features: 5-7-alternar-o-segurado-sintetico-com-contexto-consistente
- evidence: validation.md Gap 1 / SELETOR-01..05,07,08 / src/frontend/src/App.tsx:41 / src/frontend/src/contexto/PerfilContexto.tsx:15 (frontend-integration)
- last seen: 2026-09-07T00:07:07Z

### L-080 - A SPEC_DEVIATION that introduces a new composition root instead of modifying existing components must also state where that root is wired into the running app - justifying the structural choice is not the same as justifying delivery of the story's acceptance criteria.
- signal: `spec_deviation` · recurrence: 1 feature(s) · scope: `frontend-integration` · harmful: 0
- features: 5-7-alternar-o-segurado-sintetico-com-contexto-consistente
- evidence: tasks.md T5 SPEC_DEVIATION / design.md 'Implementado como' / src/frontend/src/funcionalidades/segurado/PainelSegurado.tsx:9-26 (frontend-integration)
- last seen: 2026-09-07T00:07:07Z

### L-081 - When a task's Done-when cites a generated artifact as the place a deviation or checklist is recorded, make the generator copy that content into the artifact - leaving it only in the source file's header means the named evidence file does not carry what it promises.
- signal: `ac_gap` · recurrence: 1 feature(s) · scope: `evidencias` · harmful: 0
- features: 5-8-executar-e-comprovar-os-cenarios-ponta-a-ponta
- evidence: validation.md Achado 2 / spec.md:116 Edge Case / tasks.md:319,340 / scripts/gerar_evidencias.py:124 (evidencias)
- last seen: 2026-09-07T13:16:17Z

### L-082 - When a fix lands for a defect that a test file's header documents as open, update that header in the same commit - a stale 'known open defect' note in a verification artifact reports a problem that no longer exists.
- signal: `spec_deviation` · recurrence: 1 feature(s) · scope: `testes-e2e` · harmful: 0
- features: 5-8-executar-e-comprovar-os-cenarios-ponta-a-ponta
- evidence: testes-e2e/acessibilidade/checklist-manual.spec.ts:30-39 / fix commit 36523bf / validation.md Achado 1 (testes-e2e)
- last seen: 2026-09-07T13:16:25Z

### L-083 - When a measured value diverges from the design contract, record the deviation and assert only the properties that do hold - asserting the implemented value turns the defect into the contract.
- signal: `spec_precision_gap` · recurrence: 1 feature(s) · scope: `design-tokens` · harmful: 0
- features: 5-8-executar-e-comprovar-os-cenarios-ponta-a-ponta
- evidence: validation.md E2E-11 / testes-e2e/responsividade/sistema-visual.spec.ts:22-32 (design-tokens)
- last seen: 2026-09-07T13:16:25Z

## Quarantined (failed when applied - ignore)

A confirmed lesson that recurred alongside failure. Kept for the maintainer to review.

_none_
