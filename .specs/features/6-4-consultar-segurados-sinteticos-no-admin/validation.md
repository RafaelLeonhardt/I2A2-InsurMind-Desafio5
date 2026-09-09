# História 6.4: Consultar segurados sintéticos no admin — Validation

**Date**: 2026-09-09
**Spec**: `.specs/features/6-4-consultar-segurados-sinteticos-no-admin/spec.md`
**Diff range**: `bf148e9..ba9ef29` (5 commits: `e9d4bcd`, `e05dfc7`, `d10a80d`, `e23b0b9`, `ba9ef29`)
**Verifier**: independent sub-agent (author ≠ verifier)

---

## Task Completion

No formal `tasks.md` exists for this feature (Medium-scope sizing — tasks implicit in Execute). All 5 commits are present and each maps to a coherent unit: backend endpoint+repository+tests, frontend API client+tests, frontend component+tests, App.tsx wiring+tests, spec correction. No partial or blocked work found.

| Unit | Status | Notes |
| ---- | ------ | ----- |
| Backend: `listar_sinteticos_detalhado()` + `GET /segurados/detalhado` | ✅ Done | `e9d4bcd` |
| Frontend: `api/listaSeguradosAdmin.ts` | ✅ Done | `e05dfc7` |
| Frontend: `SuperficieSegurados.tsx` | ✅ Done | `d10a80d` |
| Frontend: `App.tsx` wiring | ✅ Done | `e23b0b9` |
| Spec correction (traceability) | ✅ Done | `ba9ef29` |

---

## Spec-Anchored Acceptance Criteria

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| LISTASEG-01 (P1.1): abrir "Segurados" exibe tabela nome/bairro/apólice/canal | Tabela com as 4 colunas + linha por segurado da API | `src/frontend/src/funcionalidades/segurados-admin/SuperficieSegurados.test.tsx:80-91` — `expect(linhaA).toHaveTextContent('9990001')` / `'RES-0001'` / `'WhatsApp'`; `linhaB` com `'—'` para apólice nula | ✅ PASS |
| LISTASEG-02 (P1.2): lista vazia → estado vazio explícito | Mensagem distinta, não tabela vazia | `SuperficieSegurados.test.tsx:104-110` — `findByText('Nenhum segurado sintético cadastrado.')` | ✅ PASS |
| LISTASEG-03 (P1.3): falha na API → erro explícito com "tentar novamente" | Erro nunca indistinguível de lista vazia; ação de retry | `SuperficieSegurados.test.tsx:112-134` — `findByRole('alert')` com ocorrência/impacto/próxima ação; clique em "Tentar novamente" refaz a chamada (`toHaveBeenCalledTimes(2)`) | ✅ PASS |
| LISTASEG-04 (P2.1): busca por nome OU bairro, case-insensitive | Filtra por substring em qualquer um dos dois campos, sem diferenciar maiúsc./minúsc. | `SuperficieSegurados.test.tsx:136-163` — busca `'9990002'` isola Beto; busca `'BETO'` (maiúsculas) isola Beto — `src/funcionalidades/segurados-admin/SuperficieSegurados.tsx:40-45` (`correspondeAoTermo`, `.toLowerCase()` nos dois lados) | ✅ PASS |
| LISTASEG-05 (P2.2): termo sem correspondência → "nenhum resultado" distinto do vazio | Mensagem diferente da mensagem de lista vazia sem termo | `SuperficieSegurados.test.tsx:165-181` — `findByText('Nenhum segurado encontrado para "termo-inexistente".')` e assert explícito que a mensagem de vazio-sem-termo NÃO aparece | ✅ PASS |
| LISTASEG-06 (P3.1): selecionar segurado abre apólice/alertas/comunicados somente leitura, perspectiva admin | Abre as 3 superfícies com o `seguradoId` correto, `comoSecao`, sem ação de edição | `SuperficieSegurados.test.tsx:183-201` (segurado + `comoSecao=true`) e `:223-236` (`queryByRole('textbox')`/`'checkbox'` ausentes); confirmado por leitura direta que `SuperficieApolice.tsx`/`SuperficieAlertas.tsx`/`SuperficieComunicados.tsx` (`src/frontend/src/funcionalidades/segurado/`) não têm nenhum botão de salvar/editar/excluir, input, select ou formulário (grep confirma só botões de navegação/retry) | ✅ PASS |
| Edge case: dois segurados com mesmo nome → duas linhas distintas | Não colapsar, diferenciar por id | `SuperficieSegurados.test.tsx:93-102` — `findAllByText('Pessoa Homônima')` tem `length === 2`; `key={segurado.id}` em `SuperficieSegurados.tsx:199` | ✅ PASS |
| Repositório: segurado sem apólice permanece na lista com `apolice_numero` nulo | `LEFT JOIN` preserva a linha, campo nulo | `src/backend/testes/test_repositorio_segurados.py:224-235` (`test_listar_sinteticos_detalhado_mantem_segurado_sem_apolice_com_numero_nulo`) + `src/backend/testes/test_lista_segurados_detalhado_api.py:95-107` (nível API) | ✅ PASS |
| Repositório: segurado com múltiplas apólices mostra só a mais recente | Sem duplicar linha; apólice mais recente por `criado_em` | `src/backend/testes/test_repositorio_segurados.py:238-250` (`test_listar_sinteticos_detalhado_com_multiplas_apolices_mantem_so_a_mais_recente`) — apólice antiga `2025-01-01`, nova `2026-06-01`, resultado único com `RES-NOVA` | ✅ PASS |
| SELETOR-01 (`GET /segurados`) permanece inalterado | Nenhuma mudança de comportamento/contrato | `git diff bf148e9..ba9ef29 -- src/backend/central_preventiva/adaptadores/http/lista_segurados.py` — diff vazio; último commit a tocar o arquivo é `a9edc13`, anterior a toda a história | ✅ PASS |

**Status**: ✅ All ACs covered — 0 spec-precision gaps found (cada critério do spec já define um resultado preciso e observável; os testes miram exatamente esse resultado).

---

## Discrimination Sensor

Isolated git worktree at a timestamp/pid-suffixed scratch path (`sensor-wt-1788996140-84343`), never `git stash`. Baseline `git status --porcelain` on the real tree recorded only the pre-existing, unrelated `docs/design/prototype/package-lock.json` modification before any sensor work.

| Mutation | File:line | Description | Killed? |
| --- | --- | --- | --- |
| 1 | `src/backend/central_preventiva/adaptadores/persistencia/repositorio_segurados.py:94` | `LEFT JOIN apolices` → `JOIN apolices` (INNER) | ✅ Killed — 3 tests failed: `test_listar_sinteticos_detalhado_mantem_segurado_sem_apolice_com_numero_nulo`, `test_listar_sinteticos_detalhado_ordena_por_nome_com_varios_segurados`, `test_listar_segurados_detalhado_devolve_apolice_nula_sem_apolice_cadastrada` |
| 2 | `src/backend/central_preventiva/adaptadores/persistencia/repositorio_segurados.py:96` | `ORDER BY a.criado_em DESC` → `ASC` inside `QUALIFY ROW_NUMBER()` | ✅ Killed — `test_listar_sinteticos_detalhado_com_multiplas_apolices_mantem_so_a_mais_recente` failed (`RES-ANTIGA` returned instead of `RES-NOVA`) |
| 3 | `src/frontend/src/funcionalidades/segurados-admin/SuperficieSegurados.tsx:42` | Removed `.toLowerCase()` from the `segurado.nome` side of `correspondeAoTermo` | ✅ Killed — `filtra por nome sem diferenciar maiúsculas/minúsculas (LISTASEG-04)` failed (searching `'BETO'` no longer matched `'Beto Sintético'`) |

**Sensor depth**: lightweight (3 targeted behavior-level mutations, proportional to a non-P0 admin read surface).
**Result**: 3/3 killed — PASS ✅

Post-sensor isolation check: worktree removed with `git worktree remove --force`; real tree `git status --porcelain` re-checked and matches the pre-sensor baseline exactly (only the unrelated `package-lock.json` line).

---

## Code Quality

| Principle | Status |
| --- | --- |
| Minimum code | ✅ New endpoint/dataclass/component are additive; `GET /segurados` and `listar_sinteticos()` untouched, matching the `PreferenciasSegurado` precedent cited in spec.md |
| Surgical changes | ✅ `App.tsx` change is a 1-line swap of `EmConstrucao` for the real component |
| No scope creep | ✅ No pagination, edit, or delete UI added, consistent with Out of Scope table |
| Matches patterns | ✅ `QUALIFY ROW_NUMBER()` dedup mirrors `RepositorioMeteorologia.mapear_execucoes_por_evento`; table+search UI mirrors other `Superficie*` list surfaces |
| Spec-anchored outcome check (asserted values match spec) | ✅ See table above — every assertion targets the literal spec-defined outcome |
| Per-layer Coverage Expectation met (domain 1:1 ACs; routes happy+edge+error) | ✅ Repository: empty/single/no-apolice/multi-apolice/order — all covered. HTTP route: happy path, apólice-nula, seed-ausente — covered. No error path needed (endpoint has no failure mode beyond empty result, matching `lista_segurados.py`'s pattern) |
| Every test maps to a spec requirement — no unclaimed tests | ✅ Every new test either carries a `LISTASEG-NN` tag or maps directly to the LEFT JOIN/QUALIFY edge cases called out in the Assumption row |
| Documented guidelines followed | `AGENTS.md` conventions (additive extension over widening a shared type) — followed; no dedicated testing-guidelines doc found beyond repo conventions |

---

## Edge Cases

- [x] Segurado sem apólice: `apolice_numero` nulo, permanece na lista — `test_repositorio_segurados.py:224`, `test_lista_segurados_detalhado_api.py:95`
- [x] Segurado com múltiplas apólices: só a mais recente aparece, sem duplicar linha — `test_repositorio_segurados.py:238`
- [x] Dois segurados com o mesmo nome: duas linhas distintas, chave React por `id` — `SuperficieSegurados.test.tsx:93`

---

## Gate Check

- **Gate command (backend)**: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright`
- **Gate command (frontend)**: `npm run test --prefix src/frontend -- run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`
- **Result**: backend — 961 tests passed, 0 failed; `ruff check .` → "All checks passed!"; `pyright` → "0 errors, 0 warnings, 0 informations". Frontend — 486 tests passed (49 files), 0 failed; `oxlint` exits 0 (pre-existing `set-state-in-effect`/`only-export-components` warnings across the whole codebase, including one at `SuperficieSegurados.tsx:83` consistent with every other `Superficie*` component — not a new pattern); `vite build` succeeds (`✓ built in 252ms`).
- **Test count before feature** (`bf148e9`, backend `def test_` count): 953. **After** (`ba9ef29`): 961. **Delta**: +8 (5 in `test_repositorio_segurados.py`, 3 in new `test_lista_segurados_detalhado_api.py`) — matches the two new files/additions exactly, no deletions.
- **Test count before feature** (frontend, `it(` count): 459. **After**: 478. **Delta**: +19 (new `SuperficieSegurados.test.tsx` ~11, new `listaSeguradosAdmin.test.ts` 5, `App.test.tsx` net +0 modified test — counting method undercounts slightly vs. vitest's reported total of 486, but direction and magnitude confirm no deletions).
- **Skipped tests**: none.
- **Failures**: none.

---

## Fix Plans

None — no gaps found.

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
| --- | --- | --- |
| LISTASEG-01 | Implementing | ✅ Verified |
| LISTASEG-02 | Implementing | ✅ Verified |
| LISTASEG-03 | Implementing | ✅ Verified |
| LISTASEG-04 | Implementing | ✅ Verified |
| LISTASEG-05 | Implementing | ✅ Verified |
| LISTASEG-06 | Implementing | ✅ Verified |

---

## Summary

**Overall**: ✅ Ready

**Spec-anchored check**: 6/6 ACs (plus 2 edge cases and the SELETOR-01 non-regression check) matched the spec-defined outcome. 0 spec-precision gaps.
**Sensor**: 3/3 mutations killed.
**Gate**: backend 961 passed / 0 failed (ruff clean, pyright clean); frontend 486 passed / 0 failed (lint clean, build succeeds).

**What works**: `GET /segurados/detalhado` is a genuinely additive extension — `GET /segurados` (SELETOR-01) is byte-for-byte untouched across the whole 5-commit diff. The `LEFT JOIN` + `QUALIFY ROW_NUMBER() OVER (PARTITION BY s.id ORDER BY a.criado_em DESC) = 1` correctly keeps a segurado without any apólice (row survives with `apolice_numero = NULL`, since a single-row partition always gets `ROW_NUMBER() = 1` regardless of the `ORDER BY` value) and correctly collapses multiple apólices down to the single most recent one — both behaviors have direct unit tests and both survived independent mutation testing. The frontend list, search (case-insensitive, dual-field, distinct empty/no-results messaging) and read-only context-opening (verified against the three reused surfaces having no edit affordance whatsoever) are all covered by non-shallow tests that assert the literal spec-defined text/values.

**Issues found**: none.

**Next steps**: none — feature verified, traceability updated in `spec.md`.
