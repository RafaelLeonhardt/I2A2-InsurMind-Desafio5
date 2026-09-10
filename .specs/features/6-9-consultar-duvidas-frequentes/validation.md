# História 6.9 (Consultar dúvidas frequentes) Validation

**Date**: 2026-09-10
**Spec**: `.specs/features/6-9-consultar-duvidas-frequentes/spec.md`
**Diff range**: `fd2c1ef~1..fd2c1ef` (`fd2c1ef feat(faq): add static FAQ section to PainelSegurado`)
**Verifier**: independent sub-agent (author ≠ verifier)

---

## Task Completion

No `tasks.md` exists for this feature — Design was inline (Medium: static content, no new architecture decision), same pattern as 6.2/6.3/6.7. Scope delivered matches the spec's single P1 story + P2 story in full:

| Deliverable | Status | Notes |
| --- | --- | --- |
| `SuperficieFAQ.tsx` (new, four static Q&A pairs, native `<details open>`) | ✅ Done | - |
| `SuperficieFAQ.test.tsx` (new, 4 tests) | ✅ Done | - |
| `PainelSegurado.tsx` mounts `<SuperficieFAQ comoSecao />` as sixth stacked section | ✅ Done | `PainelSegurado.tsx:9,50` |
| `PainelSegurado.test.tsx` composition test | ✅ Done | 1 new test |
| `spec.md` traceability table updated | ✅ Done | FAQ-01..04 → Implementing (this report promotes to Verified) |

---

## Spec-Anchored Acceptance Criteria

### P1: Consultar as perguntas e respostas do FAQ

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion expression | Result |
| --- | --- | --- | --- |
| FAQ-01: WHEN o segurado acessar a seção "Dúvidas frequentes" THEN a interface SHALL exibir a lista de perguntas com suas respectivas respostas | All 4 prototype questions present, each with its answer visible on access (no extra click needed) | `src/frontend/src/funcionalidades/segurado/SuperficieFAQ.test.tsx:14-23` — for each of the 4 `PERGUNTAS`, `screen.getByText(pergunta).closest('details')` is non-null and `toHaveAttribute('open')` | ✅ PASS |
| FAQ-02: The conteúdo exibido SHALL declarar explicitamente que o ambiente é educacional, os dados são sintéticos e nenhuma comunicação real é enviada | Exact three-part disclosure text present | `SuperficieFAQ.test.tsx:25-33` — `screen.getByText('Ambiente educacional. Dados sintéticos. Nenhum envio real de mensagens é realizado.')` (exact string match, not a substring/regex) | ✅ PASS |

**Status**: ✅ Both ACs covered with precise, spec-matching assertions.

### P2: Expandir/recolher cada pergunta individualmente

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion expression | Result |
| --- | --- | --- | --- |
| FAQ-03: WHEN o segurado selecionar uma pergunta fechada THEN a interface SHALL expandir sua resposta sem afetar o estado das demais | Selected question's `open` flips to expanded; sibling question's state is untouched | `SuperficieFAQ.test.tsx:52-54` — after collapsing item 1 (see FAQ-04 row), a second click re-expands it: `expect(primeiroDetalhe.open).toBe(true)`, and in the same assertion block `expect(segundoDetalhe.open).toBe(true)` (unchanged throughout) | ✅ PASS |
| FAQ-04: WHEN o segurado selecionar uma pergunta já expandida THEN a interface SHALL recolhê-la novamente | Selected question's `open` flips to collapsed; sibling unaffected | `SuperficieFAQ.test.tsx:48-50` — `await usuario.click(primeiraPergunta)`, then `expect(primeiroDetalhe.open).toBe(false)` while `expect(segundoDetalhe.open).toBe(true)` | ✅ PASS |

**Note on test sequencing**: because FAQ-01 requires every question open by default, the test at `SuperficieFAQ.test.tsx:35-55` necessarily starts both `details` open and exercises the *collapse* action first (FAQ-04's scenario) then the *expand* action second (FAQ-03's scenario), rather than spec's narrative order. Both directions of the toggle are exercised and the sibling's untouched state is asserted after each click — the outcome matches the spec precisely, only the walkthrough order differs. Not a gap.

**Status**: ✅ Both ACs covered with precise assertions.

---

## Edge Cases

- [x] **"A lista de perguntas SHALL nunca ficar vazia"**: `ITENS_FAQ` (`SuperficieFAQ.tsx:13-44`) is a compile-time literal array of exactly 4 entries, typed `ItemFAQ[]`, with zero external/async loading path (no `fetch`, no file read) — there is no runtime state that could produce an empty list, so the edge case is satisfied by construction, consistent with the spec's Out-of-Scope decision to keep FAQ content static and non-CMS. Indirectly enforced by `SuperficieFAQ.test.tsx:14-23`: if `ITENS_FAQ` were ever emptied, every iteration of that test's hardcoded 4-question loop would fail with "unable to find element." No dedicated "list is non-empty" assertion exists, but none is needed given the static-array design — flagging this as a spec-precision observation, not a gap.

---

## Discrimination Sensor

Ran in an isolated `git worktree` (`git worktree add <scratch> HEAD`, `node_modules` symlinked from the real tree read-only, never mutated). Baseline `git status --porcelain` on the real tree captured before the sensor run and confirmed identical after `git worktree remove --force`.

| Mutation | File:line | Description | Killed? |
| --- | --- | --- | --- |
| 1 | `SuperficieFAQ.tsx:65` | Removed `open` from `<details key={item.pergunta} open>` (all questions default to collapsed) | ✅ Killed — 2/4 tests in `SuperficieFAQ.test.tsx` failed |
| 2 | `SuperficieFAQ.tsx:61` | Swapped the FAQ-02 disclosure paragraph text for unrelated copy ("Ambiente de demonstração interna, apenas para uso da equipe de produto.") | ✅ Killed — 1/4 tests failed (`getByText` could not find the exact string) |
| 3 | `SuperficieFAQ.tsx:54` | Flipped the `comoSecao` ternary: `comoSecao ? 'section' : 'main'` → `comoSecao ? 'main' : 'section'` | ✅ Killed — 1/4 tests in `SuperficieFAQ.test.tsx` failed (`main` found when `comoSecao` set) |

**Sensor depth**: lightweight (3 mutations, within the 1-3 default tier)
**Result**: 3/3 killed — PASS ✅
**Isolation check**: `git status --porcelain` on the real tree before and after the sensor run were identical (pre-existing unrelated dirty state: `docs/design/prototype/package-lock.json`, two backend files, two untracked 6-8 files — none touched by the sensor).

---

## Code Quality

| Principle | Status |
| --- | --- |
| No features beyond what was asked | ✅ — exactly the four prototype questions, adapted copy, no search/filter/CMS (explicitly Out of Scope in spec.md) |
| No abstractions for single-use code | ✅ — `ItemFAQ`/`ITENS_FAQ` is the minimum shape needed for a `.map()`; no factory/hook introduced |
| No unnecessary "flexibility" added | ✅ — `comoSecao` is not new flexibility; it's the pre-existing composition seam already used by `SuperficieAlertas`/`SuperficieApolice`/`SuperficieComunicados`/`SuperficieMeusDados` |
| Only touched files required for task | ✅ — `SuperficieFAQ.tsx` (new), `SuperficieFAQ.test.tsx` (new), `PainelSegurado.tsx` (mount), `PainelSegurado.test.tsx` (1 test), `spec.md` (traceability). No unrelated file touched |
| Didn't "improve" unrelated code | ✅ — the one comment edit in `PainelSegurado.tsx` is the doc-comment describing the six sections, directly caused by adding the sixth |
| Matches existing patterns/style | ✅ — `ElementoRaiz`/`atributosRaiz` ternary, `className="conteudo"`/`"introducao"` reuse pre-existing global CSS classes (`App.css:123,149`) verbatim, no new CSS file added |
| Would senior engineer approve? | ✅ |
| Tests map to acceptance criteria and are non-shallow (spot-check one story) | ✅ — spot-checked P1: both tests assert exact visible content/attributes, not just "renders without crashing" |
| Spec-anchored outcome check: each test's asserted value matches the spec-defined outcome (or gap flagged) | ✅ — see AC tables above, all 4 ACs precise |
| Per-layer Coverage Expectation met: domain logic has 1:1 AC mapping; routes/e2e cover happy + edge + error paths for every route in scope | ✅ — no domain/API layer in this feature (static content only); 4 ACs ↔ 3 `SuperficieFAQ.test.tsx` tests + composition confirmed in `PainelSegurado.test.tsx` |
| Every test in scope maps to a spec AC, listed edge case, or Done-when criterion (no unclaimed tests) | ✅ — 4 `SuperficieFAQ.test.tsx` tests map to FAQ-01, FAQ-02, FAQ-03/04, and the `comoSecao` composition contract (pre-existing pattern, not a new requirement but required for correct mounting); 1 `PainelSegurado.test.tsx` test confirms the mount itself |
| Documented project quality/testing guidelines followed | ✅ — `.claude/skills/tlc-spec-driven/references/coding-principles.md`; no project-specific frontend test-style guide found beyond established file-per-component convention, which is followed |

---

## Gate Check

- **Gate command**: `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`
- **Result**: 525 passed, 0 failed, 0 skipped; lint exit 0 (pre-existing warnings only, none in files touched by this commit); build succeeded (`✓ built in 266ms`)
- **Test count before feature**: 520 (per `.specs/STATE.md` Handoff, História 6.6 gate: "frontend 520 testes")
- **Test count after feature**: 525
- **Delta**: +5 new tests (4 in `SuperficieFAQ.test.tsx`, 1 in `PainelSegurado.test.tsx`)
- **Skipped tests**: none
- **Failures**: none

---

## Fix Plans

None — no gaps found.

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
| --- | --- | --- |
| FAQ-01 | Implementing | ✅ Verified |
| FAQ-02 | Implementing | ✅ Verified |
| FAQ-03 | Implementing | ✅ Verified |
| FAQ-04 | Implementing | ✅ Verified |

---

## Summary

**Overall**: ✅ Ready

**Spec-anchored check**: 4/4 ACs matched spec outcome, 0 spec-precision gaps
**Sensor**: 3/3 mutations killed
**Gate**: 525 passed, 0 failed

**What works**: All four FAQ questions render open by default with the exact adapted answers; the required educational/synthetic-data/no-real-send disclosure is asserted verbatim; each `<details>` collapses/expands independently via native browser behavior with zero extra React state, verified in both directions; the surface mounts correctly as the sixth stacked section in `PainelSegurado` via the pre-existing `comoSecao` seam, with no `id`/`main` landmark collision; the edge case (list never empty) holds by construction since the content is a static literal array with no external loading path.

**Issues found**: none.

**Next steps**: None required for this feature. Épico 6 status update belongs in `.specs/STATE.md` Handoff (orchestrator's responsibility, not this report).
