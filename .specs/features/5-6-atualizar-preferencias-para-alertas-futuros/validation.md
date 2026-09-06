# História 5.6: Atualizar preferências para alertas futuros — Validation

**Date**: 2026-09-06
**Spec**: `.specs/features/5-6-atualizar-preferencias-para-alertas-futuros/spec.md`
**Diff range**: `59b4650..HEAD` (5 commits: 90ae814, 278d9d1, b9e6bc8, c2ebef6, 9fab6e8)
**Verifier**: independent sub-agent (author ≠ verifier)

---

## Task Completion

| Task | Status  | Notes |
| ---- | ------- | ----- |
| T1   | ✅ Done | Migração entrou como `0016` (SPEC_DEVIATION registrado em `tasks.md`, `0014`/`0015` já consumidos) |
| T2   | ✅ Done | `atualizar_preferencias` retorna `PreferenciasSegurado` (não `Segurado`) — SPEC_DEVIATION razoável, `Segurado` só tem id+nome |
| T3   | ✅ Done | `ServicoPreferenciasSegurado` propaga `ConflitoVersao`/`ConflitoIdempotencia`, roteador (T4) traduz para `409` |
| T4   | ✅ Done | `GET /segurados/{id}/preferencias` acrescentado (SPEC_DEVIATION documentado no código e em `tasks.md`) — necessário para o frontend obter `versao` antes da 1ª edição |
| T5   | ✅ Done | Superfície montada, mas ainda não roteada em `App.tsx` — mesma pendência já registrada em `STATE.md` (item 9), fora do escopo desta história |

All 3 documented SPEC_DEVIATIONs are reasonable: they don't weaken any acceptance criterion, and each is narrowly scoped to what T5 (frontend) actually needs.

---

## Spec-Anchored Acceptance Criteria

### P1: Editar canal e participação com concorrência e idempotência

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| WHEN Carlos abrir Meus Dados THEN exibe canal atual (whatsapp/e-mail/SMS) e participação, sem outro cadastro | combobox com valor atual, checkbox com estado atual, nenhum outro campo de cadastro | `src/frontend/.../SuperficieMeusDados.test.tsx:44-55` — `expect(...combobox...).toHaveValue('whatsapp')`, `expect(...checkbox...).toBeChecked()`, `expect(screen.queryByLabelText(/endereço/i)).not.toBeInTheDocument()` | ✅ PASS |
| WHEN Carlos salvar alteração válida THEN persistida com `Idempotency-Key` + `versao_esperada`; UI mostra `Salvando` depois `Salvo` | header `Idempotency-Key` presente, corpo com `versao_esperada`, sequência de estado `Salvando…`→`Salvo` | `src/backend/testes/test_preferencias_segurado_api.py:86-104` — `assert resposta.status_code == 200`, `corpo["versao"] == 2` com header `Idempotency-Key` e `versao_esperada` no corpo; `src/frontend/.../SuperficieMeusDados.test.tsx:67-89` — `expect(screen.getAllByText('Salvando…').length).toBeGreaterThan(0)` seguido de `await screen.findByText('Salvo')` | ✅ PASS |
| WHEN comando repetido com conteúdo idêntico THEN devolve resposta registrada sem nova versão; conteúdo diferente com mesma chave OU `versao_esperada` desatualizada THEN `409` | mesma versão preservada no repeat idêntico; `409` nos outros dois casos | `test_preferencias_segurado_api.py:153-181` (`assert primeira.json() == segunda.json()`; `consulta.json()["versao"] == 2`, não 3); `:184-201` (`assert resposta.status_code == 409` e `codigo == "conflito_idempotencia"`); `:107-118` (`codigo == "conflito_versao"`); espelhado em unit no caso de uso: `test_preferencias_segurado.py:91-124` | ✅ PASS |

### P1: Efeito só futuro e preservação de histórico

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| WHEN nova execução preventiva iniciar THEN canal/participação atualizados orientam o futuro, execuções/snapshots/mensagens/comunicados anteriores permanecem inalterados | uma alteração de `segurados.canal_preferido`/`participa_de_alertas` nunca reescreve `elegibilidades_historicas` | Nenhum `file:line` **nesta diff** exercita esse caminho ponta a ponta (nenhuma nova execução preventiva é disparada nos testes de 5.6). A garantia é estrutural, herdada de 2.5: `elegibilidades_historicas.canal` é congelado por design (`src/backend/central_preventiva/adaptadores/persistencia/README.md:157`), e `RepositorioSegurados.atualizar_preferencias` (novo, `repositorio_segurados.py:75-101`) só escreve na linha viva de `segurados`, nunca em `elegibilidades_historicas`. | ⚠️ Spec-precision gap (evidence-or-zero: sem citação de teste desta feature) |
| WHEN participação desativada THEN resultado explica "só alertas futuros", histórico continua consultável | texto explicando o efeito futuro aparece ao desmarcar | `SuperficieMeusDados.tsx:187-192` renderiza a explicação; `SuperficieMeusDados.test.tsx:119-131` — `expect(screen.getByText(/vale só para alertas futuros/)).toBeInTheDocument()` e `expect(screen.getByText(/comunicados e alertas já registrados continuam disponíveis/)).toBeInTheDocument()` | ✅ PASS |

### P2: Falha honesta e formulário acessível

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| IF API não confirmar (falha/conflito) THEN valores editados preservados, erro explicado, sem `Salvo` antecipado | formulário mantém o valor editado, `role="alert"` com a ocorrência, nenhum `Salvo` visível | `SuperficieMeusDados.test.tsx:91-117` — após `409` simulado: `expect(erro).toHaveTextContent('A versão esperada não corresponde...')`, `expect(screen.queryByText('Salvo')).not.toBeInTheDocument()`, `expect(seletorCanal).toHaveValue('sms')` (valor editado, não o original `whatsapp`) | ✅ PASS |
| WHEN formulário usado por teclado THEN campos/ajuda/pendente/erro/confirmação com nomes e foco visíveis, nada só em toast/cor | navegação só por Tab/Enter/Espaço alcança todos os controles; estados usam `role="status"`/`role="alert"`, não cor isolada | `SuperficieMeusDados.test.tsx:133-163` — `usuario.tab()` + `toHaveFocus()` para select, checkbox e botão; `usuario.keyboard('{Enter}')` submete; `expect(salvo).toHaveAttribute('role', 'status')`; erro usa `role="alert"` (`SuperficieMeusDados.tsx:204`) | ✅ PASS |

**Status**: ⚠️ 6/7 ACs matched spec outcome with direct evidence in this diff; 1 spec-precision gap (PREFS-04's execution-integration half) — architecturally sound but not independently exercised by a test introduced in this feature.

---

## Discrimination Sensor

Isolated in a temporary git worktree (`git worktree add`/`git worktree remove --force`); frontend `node_modules` symlinked into the worktree (never installed/modified in place). Baseline and post-cleanup `git status --porcelain` on the real tree were both empty — real tree confirmed untouched.

| # | File:line | Description | Killed? |
| - | --------- | ----------- | ------- |
| 1 | `repositorio_segurados.py:92-93` | Dropped `AND versao = ?` from the optimistic-concurrency `UPDATE` (always matches on `id` alone) | ✅ Killed — 3 tests failed: `test_repositorio_segurados.py::test_atualizar_preferencias_com_versao_incorreta_levanta_conflito_sem_mutar`, `test_preferencias_segurado_api.py::test_put_preferencias_versao_esperada_desatualizada_retorna_409`, `::test_put_preferencias_duas_edicoes_concorrentes_so_a_primeira_confirma` |
| 2 | `preferencias_segurado.py:141` | Flipped idempotency hash check `!=` → `==` (treats matching content as a conflict and mismatched content as a repeat) | ✅ Killed — 4 tests failed: `test_preferencias_segurado.py::test_atualizar_repete_mesma_chave_conteudo_identico_nao_persiste_de_novo`, `::test_atualizar_repete_mesma_chave_conteudo_diferente_levanta_conflito_idempotencia`, `test_preferencias_segurado_api.py::test_put_preferencias_repetido_com_mesma_chave_e_corpo_devolve_a_mesma_resposta`, `::test_put_preferencias_mesma_chave_com_corpo_diferente_retorna_409` |
| 3 | `SuperficieMeusDados.tsx` (catch block of `salvar`) | On save failure, reset `formulario` back to the last-persisted `preferencias` (destroys the edited-but-unsaved values) | ✅ Killed — 1 test failed: `SuperficieMeusDados.test.tsx > em falha ao salvar, preserva os valores editados e explica o erro sem indicar Salvo` (`expect(seletorCanal).toHaveValue('sms')` received `'whatsapp'`) |

**Sensor depth**: lightweight (default tier)
**Result**: 3/3 killed — PASS ✅

---

## Payload/Conjunction Check

`PUT`/`GET` response bodies are asserted on actual field values, not just call-happened:
- `test_preferencias_segurado_api.py:96-104` asserts `corpo["segurado_id"]`, `corpo["canal_preferido"]`, `corpo["participa_de_alertas"]`, `corpo["versao"]` all together, plus a round-trip `consulta.json() == corpo`.
- Frontend: `SuperficieMeusDados.test.tsx:88` asserts `atualizarPreferenciasMock` was called with the exact tuple `(SEGURADO_ID, 1, 'whatsapp', true)`, not merely that it was called.

No shallow "assert a call occurred" pattern found in this diff.

---

## Code Quality

| Principle | Status |
| --- | --- |
| Minimum code | ✅ |
| Surgical changes | ✅ |
| No scope creep | ✅ (GET endpoint SPEC_DEVIATION is narrowly justified, not gold-plating) |
| Matches patterns | ✅ (mirrors `RepositorioExecucaoPreventiva.transicionar` 2.2, `ServicoGestaoRegras.ativar` 2.4, `apolice_segurado.py` router shape) |
| Spec-anchored outcome check | ⚠️ 6/7 ACs with direct evidence; PREFS-04's execution-integration half relies on inherited 2.5 architecture, not a new test |
| Per-layer coverage (domain 1:1 ACs; routes happy+edge+error) | ✅ — router covers 200/404/409/422 across id, canal, idempotency-key-missing, version-conflict, idempotency-conflict |
| Every test maps to a spec AC/edge case | ✅ — no unclaimed tests found in the new/modified test files |
| Documented guidelines followed | `AGENTS.md`, `README.md`; concurrency/idempotency floor from `test_repositorio_regras.py` (2.4) and `test_repositorio_execucao_preventiva.py` (2.2), per `tasks.md`'s Test Coverage Matrix |

---

## Edge Cases

- [x] Mesmo valor já vigente é alteração válida idempotente normal: `test_preferencias_segurado_api.py:261-280`, `test_preferencias_segurado.py:127-136` — both assert `200`/success with version incremented, no error.
- [x] Duas edições concorrentes com a mesma `versao_esperada`, só a primeira confirma: `test_preferencias_segurado_api.py:121-150` — `primeira.status_code == 200`, `segunda.status_code == 409`. Also proven live by sensor mutation #1.
- [ ] Reativação da participação após desativação não retroage: **not independently tested** in this diff. No test simulates deactivate→reactivate and checks that the reactivation only takes effect from that point on. Architecturally implausible to violate (the repository only ever mutates the current row; there is no historical/retroactive write path anywhere in `atualizar_preferencias`), but evidence-or-zero means this specific scenario has no dedicated `file:line`.

---

## Gate Check

- **Gate command (backend)**: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright`
- **Gate command (frontend)**: `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`
- **Result**: all four commands exit 0. Backend: 1091 passed, 0 failed, 0 skipped; ruff clean; pyright 0 errors/0 warnings. Frontend: 418 passed (42 files), 0 failed; oxlint exits 0 (30 pre-existing warnings, none new besides one `set-state-in-effect` warning on `SuperficieMeusDados.tsx:86` that follows the same pattern already present in ~15 other surfaces in the codebase); `vite build` succeeds.
- **Test count before feature** (59b4650): backend ≈1068, frontend ≈411
- **Test count after feature** (HEAD): backend 1091, frontend 418
- **Delta**: backend +23 new test functions, frontend +7 new `it(...)` cases — matches the diff exactly, no deletions
- **Skipped tests**: none
- **Failures**: none

---

## Fix Plans

No blocking fix required — the report is a PASS with one flagged spec-precision gap and one untested-but-architecturally-sound edge case, both non-blocking:

### Note 1: PREFS-04 execution-integration half has no dedicated test in this diff

- **Root cause**: `design.md` itself argues (Risks & Concerns, Tech Decisions) that no new mechanism or test is needed because `elegibilidades_historicas.canal` (2.5) already freezes the channel at evaluation time, and `avaliador_elegibilidade`/`repositorio_elegibilidade` already read `segurados` live. This reasoning is sound and consistent with the project's existing pattern (same argument would apply to any future write to `segurados`). Not a functional bug.
- **Suggested follow-up** (optional, not blocking): an integration test that updates a segurado's preferences, then triggers a new elegibility evaluation and asserts the new evaluation used the updated channel while a pre-existing `elegibilidades_historicas` row is untouched, would close this gap with direct evidence. Low priority — the underlying mechanism (2.5) is independently tested elsewhere in the suite.

### Note 2: Reactivation-after-deactivation has no dedicated test

- **Root cause**: same class of gap — the mechanism (plain row update) makes retroactivity structurally impossible, but no test explicitly walks deactivate→reactivate and checks timing.
- **Suggested follow-up** (optional, not blocking): a repository-level test performing two sequential `atualizar_preferencias` calls (`participa_de_alertas=False` then `True`) and asserting only the current row value changes, with no other table touched, would make this explicit.

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
| --- | --- | --- |
| PREFS-01 | Implementing | ✅ Verified |
| PREFS-02 | Implementing | ✅ Verified |
| PREFS-03 | Implementing | ✅ Verified |
| PREFS-04 | Implementing | ⚠️ Verified (spec-precision gap — see Note 1) |
| PREFS-05 | Implementing | ✅ Verified |
| PREFS-06 | Implementing | ✅ Verified |
| PREFS-07 | Implementing | ✅ Verified |

---

## Summary

**Overall**: ✅ Ready

**Spec-anchored check**: 6/7 ACs matched spec outcome with direct file:line evidence; 1 spec-precision gap (PREFS-04, non-blocking, architecturally guaranteed)
**Sensor**: 3/3 mutations killed
**Gate**: backend 1091 passed / frontend 418 passed, 0 failed, both stacks lint+build clean

**What works**: Full PUT/GET preferences flow (concurrency via `versao_esperada`, idempotency via `Idempotency-Key`), same-value-is-valid and concurrent-edit edge cases, frontend Salvando/Salvo states, error preserves edited form values, keyboard-only operability, "only future" explanation on deactivation. All 3 documented SPEC_DEVIATIONs (migration `0016`, `PreferenciasSegurado` return type, added `GET` endpoint) are reasonable and narrowly scoped.

**Issues found**: (1) PREFS-04's execution-integration half and (2) reactivation-after-deactivation are both structurally guaranteed but lack a dedicated test in this diff — non-blocking, optional follow-up tests suggested above.

**Next steps**: Ship as-is. If a future story touches `avaliador_elegibilidade`/`repositorio_elegibilidade` or adds more `segurados` writes, add the two optional tests above at that time rather than as a blocking gate now.
