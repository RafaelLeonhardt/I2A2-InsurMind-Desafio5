# LESSONS - auto-maintained by scripts/lessons.py

> Machine-owned. Do NOT hand-edit. Changes are overwritten on the next `lessons.py` write.
> Canonical state lives in `.specs/lessons.json`. Edit lessons only via the script.
> promote_threshold=2 distinct features · window_days=45 · quarantine_threshold=2

## Confirmed (load these at Specify/Design)

Corroborated across multiple features. Safe to apply as guidance.

_none_

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

### L-024 - When a requirement demands distinction by text, icon and color, assert that all three signals differ across categories.
- signal: `spec_precision_gap` · recurrence: 1 feature(s) · scope: `frontend` · harmful: 0
- features: 2-3-identificar-eventos-meteorologicos-relevantes
- evidence: RISCO-12 - src/frontend/src/funcionalidades/evento-decisao/SuperficieEventoDecisao.test.tsx:80-126 (frontend)
- last seen: 2026-09-02T12:08:04Z

## Quarantined (failed when applied - ignore)

A confirmed lesson that recurred alongside failure. Kept for the maintainer to review.

_none_
