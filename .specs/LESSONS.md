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

## Quarantined (failed when applied - ignore)

A confirmed lesson that recurred alongside failure. Kept for the maintainer to review.

_none_
