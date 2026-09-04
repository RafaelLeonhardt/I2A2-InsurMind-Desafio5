# LESSONS - auto-maintained by scripts/lessons.py

> Machine-owned. Do NOT hand-edit. Changes are overwritten on the next `lessons.py` write.
> Canonical state lives in `.specs/lessons.json`. Edit lessons only via the script.
> promote_threshold=2 distinct features · window_days=45 · quarantine_threshold=2

## Confirmed (load these at Specify/Design)

Corroborated across multiple features. Safe to apply as guidance.

### L-024 - When a requirement demands distinction by text, icon and color, assert that all three signals differ across categories.
- signal: `spec_precision_gap` · recurrence: 2 feature(s) · scope: `frontend` · harmful: 0
- features: 2-3-identificar-eventos-meteorologicos-relevantes, 2-4-configurar-testar-e-versionar-regras-preventivas
- evidence: RISCO-12 - src/frontend/src/funcionalidades/evento-decisao/SuperficieEventoDecisao.test.tsx:80-126 (frontend) (+1 more)
- last seen: 2026-09-02T14:42:34Z

### L-033 - A return type declared in design.md must carry every field the acceptance criteria require to be persisted.
- signal: `spec_deviation` · recurrence: 2 feature(s) · scope: `design` · harmful: 0
- features: 3-2-gerar-mensagens-automaticamente-para-cada-canal, 3-3-avaliar-a-qualidade-e-a-seguranca-das-mensagens
- evidence: SPEC_DEVIATION em src/backend/central_preventiva/adaptadores/ia/agente_redator.py:8 (design) (+1 more)
- last seen: 2026-09-04T10:25:44Z

### L-034 - Do not fix a migration number in design.md; assign the next number at implementation time from the migrations directory.
- signal: `spec_deviation` · recurrence: 3 feature(s) · scope: `persistence` · harmful: 0
- features: 3-2-gerar-mensagens-automaticamente-para-cada-canal, 3-3-avaliar-a-qualidade-e-a-seguranca-das-mensagens, 3-4-regenerar-mensagens-e-registrar-a-proveniencia-agentica
- evidence: SPEC_DEVIATION em src/backend/central_preventiva/adaptadores/persistencia/migracoes/0010_mensagens.sql:3 (persistence) (+2 more)
- last seen: 2026-09-04T11:41:50Z

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

### L-003 - Name the exact HTTP status code in the spec for every refusal path; when the spec only says "explicit error", record the chosen status as a spec-precision gap instead of passing it silently.
- signal: `spec_precision_gap` · recurrence: 1 feature(s) · scope: `adaptadores/http` · harmful: 0
- features: 1-2-inicializar-e-restaurar-dados-sinteticos
- evidence: spec.md Edge Cases - src/backend/central_preventiva/adaptadores/http/dados_sinteticos.py:146 (adaptadores/http) (+1 more)
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

### L-006 - When a spec requires a real-browser behavior jsdom cannot simulate (e.g. 200% zoom, real layout/measurement), flag it explicitly as needing manual/UAT verification in the spec or tasks file instead of leaving it silently uncovered by the automated suite.
- signal: `spec_precision_gap` · recurrence: 1 feature(s) · scope: `frontend/accessibility` · harmful: 0
- features: 1-3-verificar-a-prontidao-das-dependencias
- evidence: PRONT-13 (validation.md P2: Operar a superficie por teclado e em zoom 200% AC2) (frontend/accessibility)
- last seen: 2026-08-29T10:32:47Z

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

### L-013 - Fold port methods discovered during implementation back into the design document instead of leaving the deviation marker as their only record.
- signal: `spec_deviation` · recurrence: 1 feature(s) · scope: `ports` · harmful: 0
- features: 2-1-coletar-e-normalizar-dados-do-inmet
- evidence: aplicacao/portas_meteorologia.py:86,95,112 (ports)
- last seen: 2026-09-02T01:54:08Z

### L-014 - Test the intersection where two derivation conditions hold at once, so branch priority order is pinned instead of incidental.
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `frontend` · harmful: 0
- features: 2-2-operar-com-seguranca-durante-indisponibilidades-meteorologicas
- evidence: validation.md Sensor #3 — SuperficieFonteMeteorologica.tsx:55-58 (frontend)
- last seen: 2026-09-02T03:53:01Z

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

## Quarantined (failed when applied - ignore)

A confirmed lesson that recurred alongside failure. Kept for the maintainer to review.

_none_
