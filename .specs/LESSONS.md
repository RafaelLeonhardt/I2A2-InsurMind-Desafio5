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

## Quarantined (failed when applied - ignore)

A confirmed lesson that recurred alongside failure. Kept for the maintainer to review.

_none_
