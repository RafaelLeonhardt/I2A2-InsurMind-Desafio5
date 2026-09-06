# História 5.4: Entender como a mensagem foi criada — Validation

**Date**: 2026-09-06
**Spec**: `.specs/features/5-4-entender-como-a-mensagem-foi-criada/spec.md`
**Diff range**: `7e67591..4b5de5f` (9bc9a75 T1, 08cfdc8 T2, f04801a T3, 4b5de5f fix)
**Verifier**: independent pass by the orchestrating session (two dispatched sub-agent Verifiers stalled on infrastructure grounds — stream watchdog timeout mid-run, not a code finding — before writing any report; this pass re-derives everything from spec.md/design.md/tasks.md with no inherited assumptions from the implementer's session)

---

## Task Completion

| Task | Status  | Notes |
| ---- | ------- | ----- |
| T1   | ✅ Done | `ServicoExplicacaoComunicado` (`aplicacao/explicacao_comunicado.py`) |
| T2   | ⚠️ Done, with a gap found and fixed | HTTP endpoint shipped; missed updating the shared OpenAPI route-allowlist guard test (`test_saude.py`) — fixed in `4b5de5f` |
| T3   | ✅ Done | `SuperficieExplicacaoComunicado.tsx` drawer |

---

## Spec-Anchored Acceptance Criteria

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| EXPLICACAO-01: evento/regra rotulados determinístico, distinguindo de atividade de IA | `origem` = `DETERMINISTICA` no evento/regra, `AGENTE` na seção de geração/crítica | `testes/test_explicacao_comunicado.py:243-248` — `assert explicacao.evento_e_regra.origem is OrigemInformacao.DETERMINISTICA` / `assert explicacao.agente.origem is OrigemInformacao.AGENTE`; HTTP: `testes/test_explicacao_comunicado_api.py:199,203` — `corpo["evento_e_regra"]["origem"] == "deterministica"` / `corpo["agente"]["origem"] == "agente"` | ✅ PASS |
| EXPLICACAO-02: papéis do redator/crítico, decisão crítica, tentativas e aprovação humana visíveis | Tentativa expõe `modelo_redator`, `avaliacao_critica.aprovada`, `decisoes_humanas[].resultado`; regeneração automática ≠ humana | `testes/test_explicacao_comunicado.py:253-257` — `tentativa.avaliacao_critica.avaliacao.aprovada is True`, `tentativa.decisoes_humanas[0].resultado is ResultadoDecisaoHumana.APROVAR`; edge case automática vs. humana: `testes/test_explicacao_comunicado.py:312-318` — `origens == [PRIMEIRA_TENTATIVA, AUTOMATICA, HUMANA]` | ✅ PASS |
| EXPLICACAO-03: categorias usadas/não usadas, sem documentos/financeiro/pagamentos/credenciais/prompt completo | `contexto.categorias_usadas`/`categorias_nao_usadas` presentes; `"documentos"`/`"dados_financeiros"` nunca em `categorias_usadas` | `testes/test_explicacao_comunicado.py:334-337` — `explicacao.contexto.categorias_usadas == CATEGORIAS_USADAS`; `"documentos" not in ...`; `"dados_financeiros" not in ...`; HTTP: `test_explicacao_comunicado_api.py:211-213` | ✅ PASS |
| EXPLICACAO-04: prévia idêntica à versão aprovada/simulada, com aviso de simulação | `apresentacao_simulada` == cópia de `entregas_simuladas.apresentacao` (nunca recalculada) | `testes/test_explicacao_comunicado.py:349-351` — `explicacao.apresentacao_simulada.corpo == "Chuva forte hoje."` (valor semeado só em `entregas_simuladas`, nunca em `versoes_mensagem` diretamente); frontend aviso: `SuperficieExplicacaoComunicado.test.tsx:260-278` (seção "prévia fiel sem promessa oficial") | ✅ PASS |
| EXPLICACAO-05: lacuna de proveniência mostra `Procedência parcial`/`Exceção`, nunca inferência | `status == PARCIAL` quando avaliação intermediária ausente; `status == EXCECAO` com `causa_excecao` quando nunca chegou a `criticando` | `testes/test_explicacao_comunicado.py:391-393` — `explicacao.agente.status is StatusProcedencia.PARCIAL`, `tentativas[0].avaliacao_critica is None`; exceção: `testes/test_explicacao_comunicado.py:434-435` — `status is StatusProcedencia.EXCECAO`, `causa_excecao == "falha_integracao_ia"` | ✅ PASS |
| EXPLICACAO-06/07: foco preso, `Esc` fecha e devolve foco, título sempre visível, sem 2ª camada modal | `Tab`/`Shift+Tab` não saem do drawer; `Esc` chama `onFechar` e o foco volta ao elemento de origem; título visível mesmo carregando; fechado não renderiza nada | `SuperficieExplicacaoComunicado.test.tsx:392-425` — `expect(aoFechar).toHaveBeenCalledTimes(1)`, `expect(document.activeElement).toBe(origem)`; título: `:428-441`; sem render quando fechado: `:443-451` | ✅ PASS |
| Ownership / non-enumeração (AD-011) — comunicado de outro segurado | `obter` devolve `None`; endpoint devolve `404` idêntico ao caso inexistente | `testes/test_explicacao_comunicado.py:464-465`; HTTP: `testes/test_explicacao_comunicado_api.py:232-236` — mesmos `status_code`/`codigo` para os dois casos | ✅ PASS |
| Execução correlacionada indicada sem misturar proveniência (Edge Case) | `execucao_origem_id` presente só na retentativa, `execucao_id` correto em cada uma | `testes/test_explicacao_comunicado.py:451-455` | ✅ PASS |
| Identificador inválido não é `500` | `422` com `codigo: identificador_invalido` | `testes/test_explicacao_comunicado_api.py:247-248` | ✅ PASS |

**Status**: ✅ All ACs covered with spec-matching outcomes. No spec-precision gaps found — every AC in spec.md defines a precise, testable outcome and each is matched exactly.

---

## Discrimination Sensor

Isolated `git worktree` at `HEAD` (`4b5de5f`), never `git stash`. Baseline `git status --porcelain` on the real tree was empty before and after.

| Mutation | File:line | Description | Killed? |
| --- | --- | --- | --- |
| 1 | `aplicacao/explicacao_comunicado.py:259` | Flipped ownership check `!= segurado_id` → `== segurado_id` | ✅ Killed (10 tests failed across both `test_explicacao_comunicado.py` and `test_explicacao_comunicado_api.py`) |
| 2 | `aplicacao/explicacao_comunicado.py:226` | Inverted lacuna-detection condition (`is None` → `is not None`) | ✅ Killed (exactly `test_avaliacao_critica_ausente_de_tentativa_intermediaria_mostra_procedencia_parcial` failed) |
| 3 | `SuperficieExplicacaoComunicado.tsx:110` | Disabled the `Escape` key match | ✅ Killed (exactly `Esc fecha o drawer e devolve o foco à origem` failed) |

**Sensor depth**: lightweight (3 targeted mutations — ownership guard, gap-detection logic, drawer keyboard handling: the three highest-risk new behaviors this story introduces).
**Result**: 3/3 killed — ✅ PASS

---

## Gate Check

**Gate command** (from tasks.md, Build level):
- Backend: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright`
- Frontend: `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`

**Initial run (before fix, at `f04801a`)**: backend **FAILED** — `testes/test_saude.py::test_openapi_em_portugues_nao_antecipa_recursos_futuros` (an exhaustive OpenAPI-path allowlist guard test predating this story) did not include the new route `/api/v1/segurados/{segurado_id}/comunicados/{entrega_simulada_id}/explicacao` added by T2. This is a real, deterministic gate failure — reproduced identically on a second run — not a sensor mutation or flake.

**Fix applied**: `4b5de5f` adds the missing route to the guard test's expected set (see Fix Plans below).

**Re-run (after fix, at `4b5de5f`)**:
- Backend: `pytest` — **0 failed**, all green; `ruff check .` — all checks passed; `pyright` — 0 errors, 0 warnings.
- Frontend: `npm run lint` — exit 0 (pre-existing repo-wide `set-state-in-effect`/`only-export-components` warnings only, same pattern across every other story's surfaces, non-blocking); `npm run build` — succeeded.
- Frontend `vitest --run` (full suite, 39 files / 393 tests): passed 3 times in a row after the fix. One earlier full-suite run (at `f04801a`, before any code change) showed a single failure in `SuperficieComunicado.test.tsx` — a file this feature never touches (confirmed via `git diff 7e67591..f04801a --stat`) — that did not reproduce on any of 3 subsequent full-suite runs, nor in isolated runs of that file alone or paired with the new test file. Treated as pre-existing test-suite flakiness under load, not a regression introduced by this feature; not blocking, no fix task created.

**Test count**: 393 frontend tests (unchanged file count baseline + this feature's new `SuperficieExplicacaoComunicado.test.tsx` at 15 tests and `explicacaoComunicado.test.ts`); backend suite green end-to-end, no skips.
**Skipped tests**: none.
**Failures**: 1 found and fixed (see above). 0 remaining.

---

## Code Quality

| Principle | Status |
| --- | --- |
| Minimum code | ✅ — reuses `ServicoDetalheResultado` (4.2) by composition, no duplicated query, matches design.md exactly |
| Surgical changes | ✅ — no unrelated files touched beyond the fix's single-line addition to `test_saude.py` |
| No scope creep | ✅ |
| Matches existing patterns | ✅ — same non-enumeration (AD-011), same `OrigemInformacao`/status enum style as sibling features |
| Spec-anchored outcome check (asserted values match spec) | ✅ |
| Per-layer Coverage Expectation met (domain 1:1 ACs; routes happy+edge+error) | ✅ — HTTP layer covers happy path, other-segurado 404, and 422 invalid id |
| Every test maps to a spec requirement — no unclaimed tests | ✅ (spot-checked; no speculative tests found) |
| Documented guidelines followed | AGENTS.md/README.md conventions; test co-location matches `testes/` and colocated `.test.tsx` pattern used repo-wide |

**Observation (non-blocking)**: `SuperficieExplicacaoComunicado.tsx` is not wired into `SuperficieComunicado.tsx`, `App.tsx`, or `PerfilContexto.tsx` — it is another orphaned surface, consistent with the already-tracked pattern in `.specs/STATE.md` Handoff (previously 15 surfaces after 5.3; now 16). Not a new risk introduced by this story — a pre-existing, deliberately deferred UI-integration gap already flagged for a dedicated future story.

---

## Edge Cases

- [x] Mensagem nunca chegou a `criticando` (`falhou_integracao_ia`) → mostra `Exceção`, não seção vazia — `test_explicacao_comunicado.py:433-435`
- [x] Regeneração automática (3.4) distinta de regeneração por decisão humana (3.5) — `test_explicacao_comunicado.py:312-318`
- [x] Execução correlacionada (retentativa) indicada sem misturar proveniência — `test_explicacao_comunicado.py:451-455`

---

## Fix Plans

### Fix 1: OpenAPI route-allowlist guard test not updated for the new endpoint

- **Root cause**: `test_saude.py::test_openapi_em_portugues_nao_antecipa_recursos_futuros` hardcodes the full exhaustive set of exposed OpenAPI paths as a scope-creep guard. T2 added a new real route but the task's "Where"/Test Coverage Matrix only named `test_openapi_sincronizado.py` (contract sync), not this separate guard test — so it wasn't updated.
- **Fix task**: Add `"/api/v1/segurados/{segurado_id}/comunicados/{entrega_simulada_id}/explicacao"` to the expected path set in `test_saude.py`.
- **Priority**: Blocker (build gate was red) — **fixed**, commit `4b5de5f`.

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
| --- | --- | --- |
| EXPLICACAO-01 | Pending | ✅ Verified |
| EXPLICACAO-02 | Pending | ✅ Verified |
| EXPLICACAO-03 | Pending | ✅ Verified |
| EXPLICACAO-04 | Pending | ✅ Verified |
| EXPLICACAO-05 | Pending | ✅ Verified |
| EXPLICACAO-06 | Pending | ✅ Verified |
| EXPLICACAO-07 | Pending | ✅ Verified |

(`spec.md`'s traceability table was left at "Pending" through all three tasks — a process gap distilled as a lesson below — updated to Verified here as part of closing out validation.)

---

## Summary

**Overall**: ✅ Ready

**Spec-anchored check**: 9/9 criteria groups matched spec-defined outcomes, 0 spec-precision gaps
**Sensor**: 3/3 mutations killed
**Gate**: found 1 real failure (OpenAPI route guard), fixed in `4b5de5f`, all green on re-run

**What works**: Full determinístico/agente separation, minimized-context category exposure, faithful preview, honest partial-provenance/exception reporting, accessible focus-trapped drawer — all independently verified against spec.md, not just against the implementation.

**Issues found**: 1 (OpenAPI route-allowlist guard test) — fixed during this validation pass, commit `4b5de5f`.

**Next steps**: Mark História 5.4 done. Carry the two non-blocking observations forward in `.specs/STATE.md`: (1) 16th orphaned frontend surface (UI-integration story still pending), (2) spec.md traceability table needs per-task updates going forward, not just at validation.
