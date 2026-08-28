# Inicializar e Restaurar Dados Sintéticos — Context

**Gathered:** 2026-08-28
**Spec:** `.specs/features/1-2-inicializar-e-restaurar-dados-sinteticos/spec.md`
**Status:** Ready for design

---

## Feature Boundary

Story 1.2 of the BMAD backlog (`_bmad-output/planning-artifacts/epics.md`). On first run, the backend initializes a versioned DuckDB schema and a reproducible synthetic seed (segurados, apólices, regras, eventos, histórico de elegibilidade para chuva intensa e granizo). Re-running initialization is a no-op that reports the data was already prepared. A `Restaurar demonstração` action (API endpoint + admin UI surface) resets the reference data to the versioned seed inside one transaction, gated by a confirmation modal, idempotent via `Idempotency-Key`, and safe under failure — the previous dataset stays intact and queryable if the restore transaction cannot complete.

This story does not implement `ExecucaoPreventiva`'s behavior (risk evaluation, eligibility, messaging, simulation) — that belongs to Epic 2 and Epic 3. It only needs enough of that table's shape to make the restore-guard testable now (see Implementation Decisions).

---

## Implementation Decisions

### Schema scope

- Story 1.2's migrations create only the reference/master tables the seed needs: `segurados`, `apolices`, `regras`, `eventos_meteorologicos`, and a `elegibilidades_historicas` table holding the demo's eligible/non-eligible chuva-intensa/granizo examples.
- Epic 2 and Epic 3 stories add `execucao_preventiva`, `mensagem`, `revisao_humana`, `entrega_simulada`, `marco_execucao`, etc. via their own migrations when those features are actually built. Story 1.2 does not pre-scaffold their full structure.
- **Reconciling with the restore guard below:** because the restore guard needs a real column to check, 1.2's migrations also create a *minimal* `execucao_preventiva` table — just `id`, `estado` (status enum), `versao`, `criado_em`, `atualizado_em`. This is enough for a test to insert a fixture row with a non-terminal `estado` and prove the guard blocks restore. The table's full aggregate structure (children: elegibilidade, mensagem, revisão, entrega, marcos) is added later by Epic 2/3 migrations, which extend this table rather than replace it.

### Restore-vs-active-execution guard (resolves DW-002)

- Restore checks whether any row in `execucao_preventiva` has a non-terminal `estado`. If so, restore refuses with a safe, explicit error (no mutation) naming that an active execution blocks restoration — no partial reset, no silent overwrite.
- Proven by a test that inserts a fixture row with a non-terminal `estado` directly (since no production code creates such a row yet at this story's scope) and asserts the restore command is refused.
- With no non-terminal rows present (the common case at this story's scope, since nothing populates that table yet), restore proceeds normally.

### Schema version / migration mechanism (resolves DW-003)

- A `schema_migracoes` table tracks applied migrations (version number, description, applied-at timestamp).
- Each migration file runs inside its own DuckDB transaction — a migration either fully applies or leaves no trace; there is no "half-applied migration" to recover from at the level of one migration.
- On startup, the app compares the highest version recorded in `schema_migracoes` against the highest version the running code knows about:
  - Recorded version newer than code knows → refuse to start, safe PT-BR error, no mutation attempted (protects against running older code against a newer database).
  - Recorded version older or absent → apply pending migrations in order, each in its own transaction, recording success before moving to the next.
  - If migration N of a multi-migration run fails, migrations 1..N-1 remain applied (each already committed), N is not recorded, and startup halts with a clear error identifying the failed migration — the operator reruns startup once the cause is fixed; already-applied migrations are skipped via `schema_migracoes`.

### Agent's Discretion

- Exact column lists/types beyond what's named above, exact synthetic seed content (specific segurado/apólice/evento examples), and the confirmation-modal component wiring are left to Design/Tasks — Design will follow the existing `Configuracao`/repository patterns already in `src/backend/central_preventiva/composicao/` and the `Modal de confirmação` contract already defined in the UX artifacts (`UX-DR20`).

### Declined / Undiscussed Gray Areas → Assumptions

None declined — all three gray areas raised were discussed and resolved above with the recommended defaults.

---

## Specific References

- BMAD Story 1.2 acceptance criteria: `_bmad-output/planning-artifacts/epics.md` (História 1.2).
- Deferred work items resolved here: `_bmad-output/implementation-artifacts/deferred-work.md` DW-002, DW-003.
- Architecture invariants governing persistence/idempotency: `ARCHITECTURE-SPINE.md` AD-2, AD-7, AD-9, AD-11, and the "Persistência" row of Consistency Conventions.
- UX contract for the restore modal: `UX-DR20` (Modal de confirmação) in `epics.md`'s UX requirement list.

---

## Deferred Ideas

None — discussion stayed within Story 1.2's scope. `ExecucaoPreventiva`'s full behavior and DW-001 (coalescing scheduled/manual weather triggers, targets História 2.1) remain out of scope for this feature.
