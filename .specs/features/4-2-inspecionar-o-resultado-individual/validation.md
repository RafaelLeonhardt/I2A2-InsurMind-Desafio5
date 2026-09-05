# História 4.2 "Inspecionar o resultado individual" Validation

**Date**: 2026-09-04
**Spec**: `.specs/features/4-2-inspecionar-o-resultado-individual/spec.md`
**Diff range**: `ed0ffa9..1647699` (T1 `432de2b`, T2 `ae91854`, T3 `1647699`)
**Verifier**: independent sub-agent (author ≠ verifier)

---

## Task Completion

| Task | Status  | Notes |
| ---- | ------- | ----- |
| T1: `ServicoDetalheResultado` | ✅ Done | `src/backend/central_preventiva/aplicacao/detalhe_resultado.py` |
| T2: Endpoint HTTP de detalhe | ✅ Done | `src/backend/central_preventiva/adaptadores/http/detalhe_resultado.py`, registered in `composicao/api.py:22-24,177-180` |
| T3: Drawer de detalhe | ✅ Done | `src/frontend/src/funcionalidades/resultados/SuperficieDetalheResultado.tsx` |

All Done-when boxes in `tasks.md` are checked and independently corroborated by evidence below.

---

## Spec-Anchored Acceptance Criteria

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion expression | Result |
| --- | --- | --- | --- |
| DETALHE-01: abrir ação de linha mostra segurado, apólice, canal, conteúdo, horários, estado, evento, versão da regra, aprovações agêntica e humana | Todos os campos presentes e corretos | `src/backend/testes/test_detalhe_resultado.py:211-232` — `assert detalhe.nome_segurado == "Marina Teste"`, `assert detalhe.regra_versao == REGRA_VERSAO`, `assert detalhe.versoes[0].avaliacao_critica.avaliacao.aprovada is True`, `assert detalhe.versoes[0].decisoes_humanas[0].resultado is ResultadoDecisaoHumana.APROVAR`; API: `src/backend/testes/test_detalhe_resultado_api.py:162-175` | ✅ PASS |
| DETALHE-02: e-mail mostra assunto+corpo na prévia, rotulada como simulação | `rotulo == "simulada"`, assunto/corpo exatos | `test_detalhe_resultado.py:224-227` — `assert detalhe.apresentacao_simulada.assunto == "Alerta preventivo"`; `assert detalhe.apresentacao_simulada.rotulo == "simulada"`; frontend `SuperficieDetalheResultado.test.tsx:112-121` — `expect(screen.getByText('Prévia da simulação — nenhuma comunicação real foi enviada.')).toBeInTheDocument()` | ✅ PASS |
| DETALHE-03: WhatsApp/SMS mostra corpo+limite, sem telefone real nem ação de envio | limite exato do canal; nenhum campo de telefone | `test_detalhe_resultado.py:247-254` — `assert detalhe_whatsapp.limite_canal_corpo == LIMITES.whatsapp`; `assert not any("telefone" in nome or "celular" in nome for nome in nomes_dos_campos)`; API `test_detalhe_resultado_api.py:194-196` — `assert "telefone" not in resposta.text.lower()` | ✅ PASS |
| DETALHE-04: versões relacionadas às críticas/regenerações/decisão humana, ordem correta, imutáveis | 3 versões, ordem [1,2,3], cada uma com sua própria avaliação/decisão | `test_detalhe_resultado.py:298-308` — `assert [v.versao.numero_tentativa for v in detalhe.versoes] == [1, 2, 3]`; `assert detalhe.versoes[0].avaliacao_critica.avaliacao.aprovada is False`; `assert detalhe.versoes[2].decisoes_humanas[0].resultado is ResultadoDecisaoHumana.APROVAR` | ✅ PASS |
| DETALHE-05: ID inexistente ou de outra execução responde com problema identificável sem revelar outro registro; interface mostra `Não encontrado` | Resposta 404 idêntica (`codigo`/`impacto`/`proxima_acao`) para os dois casos | Service: `test_detalhe_resultado.py:320-324` — `assert resultado_de_outra_execucao is None` == `assert resultado_inexistente is None`; API: `test_detalhe_resultado_api.py:235,242-246` — `assert resposta_de_outra_execucao.status_code == resposta_inexistente.status_code == 404` + `assert corpo_outra["codigo"] == corpo_inexistente["codigo"]`; frontend: `SuperficieDetalheResultado.test.tsx:200-217` — `expect(alerta).toHaveTextContent('Não encontrado')` | ✅ PASS |
| DETALHE-06: navegação por teclado prende o foco na camada ativa | `Tab`/`Shift+Tab` nunca saem do drawer | `SuperficieDetalheResultado.test.tsx:221-233` — `expect(fechar).toHaveFocus()` after `usuario.tab()` and after `usuario.tab({shift:true})` | ✅ PASS |
| DETALHE-07: `Esc` fecha a camada ativa e devolve o foco à origem | Dialog removido do DOM, `document.activeElement` volta ao elemento de origem | `SuperficieDetalheResultado.test.tsx:235-246` — `expect(screen.queryByRole('dialog')).not.toBeInTheDocument()`; `expect(abrir).toHaveFocus()` | ✅ PASS |
| DETALHE-08: nunca empilha mais de uma camada modal adicional | No máximo 1 `dialog` presente, mesmo reaberto de outra origem | `SuperficieDetalheResultado.test.tsx:270-279` — `expect(screen.getAllByRole('dialog')).toHaveLength(1)` | ✅ PASS |

**Status**: ✅ All 8/8 ACs covered with exact spec-defined outcomes — no spec-precision gaps.

Note on DETALHE-08's Edge Case wording ("foco/Esc idêntico" entre origens diferentes): the "nunca empilha" test (line 248-279) proves single-origin re-open safety across two distinct trigger buttons, and the separate Esc/focus-return test (line 235-246) proves the generic, origin-agnostic mechanism (`document.activeElement` capture/restore, not a hardcoded origin). Together they demonstrate the edge case; no test explicitly re-asserts focus-to-Origem-B in the same test as the no-stacking check, which would have been marginally stronger but is not a gap given the mechanism is proven origin-agnostic.

---

## Discrimination Sensor

Isolated scratch worktrees only (`git worktree add`), never `git stash`. Baseline `git status --porcelain` was clean before and after all sensor work; confirmed after each worktree removal.

| Mutation | File:line | Description | Killed? |
| --- | --- | --- | --- |
| 1 | `aplicacao/detalhe_resultado.py:159` | Flipped isolation guard `registro.execucao_id != execucao_id` → `==` | ✅ Killed (6 unit + 3 API tests failed, incl. the direct DETALHE-05 tests) |
| 2 | `aplicacao/detalhe_resultado.py:211` | Narrowed the exception guard tuple to `(EstadoMensagem.FALHOU_INTEGRACAO_IA,)` only, dropping `FALHOU_CONTEUDO` | ✅ Killed (`test_mensagem_em_falhou_conteudo_traz_ultima_versao_e_a_excecao_associada` failed: `assert detalhe.excecao is not None` → `None`) |
| 3 | `funcionalidades/resultados/SuperficieDetalheResultado.tsx:304` | Flipped channel branch `detalhe.canal === 'email'` → `!== 'email'` | ✅ Killed (email-preview test failed: `Alerta preventivo` text not found) |

**Sensor depth**: lightweight (3 mutations)
**Result**: 3/3 killed - PASS ✅

**Exploratory note (not counted against the sensor quota):** a fourth attempt — removing the entire `estado in (FALHOU_CONTEUDO, FALHOU_INTEGRACAO_IA)` guard so `excecao` is always looked up — **survived** (all tests still passed). Investigation showed this branch is provably redundant given a domain invariant enforced elsewhere: `ServicoGeracaoMensagens.esgotar_tentativas` (`aplicacao/geracao_mensagens.py:399-413`) always registers the exception and transitions to the terminal failure state in the same call, and AD-7 guarantees that terminal state never reopens — so a message can never have an `excecoes_operacionais` row while being outside `(FALHOU_CONTEUDO, FALHOU_INTEGRACAO_IA)` in production. No reachable state distinguishes the guarded from the unguarded behavior, so this is not a spec-anchored coverage gap. It is, however, defensive code whose necessity is currently unverified by any test — logged as a Minor code-quality note below rather than a blocking gap.

---

## Code Quality

| Principle | Status |
| --- | --- |
| No features beyond what was asked | ✅ |
| No abstractions for single-use code | ✅ (Protocol-based ports mirror the existing DI pattern used by other `aplicacao/*` services) |
| No unnecessary "flexibility" added | ✅ |
| Only touched files required for task | ✅ |
| Didn't "improve" unrelated code | ✅ |
| Matches existing patterns/style | ✅ (problem+json shape, roteador composition, protocol ports all match prior stories) |
| Would senior engineer approve? | ⚠️ Yes, with two minor non-blocking notes (below) |
| Tests map to acceptance criteria and are non-shallow (spot-check one story) | ✅ — spot-checked P1 "Detalhe completo": every assertion targets a specific field value (`regra_versao == REGRA_VERSAO`, `rotulo == "simulada"`), not mere presence |
| Spec-anchored outcome check (asserted values match spec-defined outcome) | ✅ |
| Per-layer Coverage Expectation met (domain 1:1 ACs; routes happy+edge+error) | ✅ — routes cover 200 (email, WhatsApp), 404 (inexistente, outra execução), 422 (UUID inválido) |
| Every test maps to a spec requirement — no unclaimed tests | ✅ |
| Documented project guidelines followed | `AGENTS.md`, `README.md`; piso de `test_avaliacao_elegibilidade.py` (junção de múltiplas fontes) e `test_prontidao_api.py` (não-enumeração) — both followed |

**Minor notes (non-blocking):**
1. `SuperficieDetalheResultado.tsx` reimplements `Modal.tsx`'s focus-trap/`Esc` mechanism verbatim (identical `SELETOR_FOCAVEIS` constant, identical focus-capture/restore effect, identical Tab-wrap `aoTeclar` logic — `componentes/Modal.tsx:4-11,57-107` vs. `funcionalidades/resultados/SuperficieDetalheResultado.tsx:10-17,105-152`). The module docstring justifies this by Modal's confirm/cancel footer and `objeto`/`impacto` contract not fitting a read-only drawer — that reasoning is sound for the *footer/content* contract, but the focus-trap logic itself has no dependency on that contract and is duplicated, not merely parallel. A senior reviewer would likely ask for a shared `useFocoPreso` hook extracted from both. Recommended as a follow-up refactor, not a defect — both implementations are independently correct and tested identically.
2. The `estado in (FALHOU_CONTEUDO, FALHOU_INTEGRACAO_IA)` guard on the `excecao` lookup (`aplicacao/detalhe_resultado.py:209-212`) is untested in isolation (see Discrimination Sensor exploratory note) — its correctness currently rests entirely on an invariant enforced in a different module. A cheap unit test asserting `excecao is None` when a message has an exception row but is not in a failure state would make this branch's necessity independently verifiable, decoupled from that invariant holding forever.

---

## Edge Cases

- [x] Mensagem em exceção (`falhou_conteudo`/`falhou_integracao_ia`) mostra a última versão disponível e a exceção associada — `test_detalhe_resultado.py:327-356`
- [x] Mensagem sem decisão humana ainda (nunca chegou a `aguardando_revisao`) não gera erro técnico — `test_detalhe_resultado.py:359-377` (`assert detalhe.versoes[0].decisoes_humanas == ()`, `assert detalhe.excecao is None`)
- [x] Drawer aberto de contextos diferentes tem foco/`Esc` idêntico — `SuperficieDetalheResultado.test.tsx:248-279` (no double-stacking across two distinct origins) + `:235-246` (origin-agnostic focus-return mechanism)

---

## Gate Check

- **Gate command**: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright` (backend); `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend` (frontend)
- **Result**:
  - Backend: `pytest` 916 passed, 0 failed; `ruff check .` — All checks passed!; `pyright` — 0 errors, 0 warnings, 0 informations
  - Frontend: `vitest --run` — 32 test files, 305 tests passed, 0 failed; `oxlint` exit 0 (pre-existing `set-state-in-effect`/`only-export-components` warnings across the codebase, none new to this feature's logic beyond the same pattern already used elsewhere); `vite build` succeeded
- **Test count before feature**: 911 backend / 296 frontend
- **Test count after feature**: 916 backend / 305 frontend
- **Delta**: +5 backend (4 in `test_detalhe_resultado.py`+`test_detalhe_resultado_api.py` net of shared scenarios, 1 in `test_repositorio_execucao_preventiva.py`, plus `test_saude.py` path-set update) / +9 frontend (`SuperficieDetalheResultado.test.tsx`)
- **Skipped tests**: none
- **Failures**: none

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
| --- | --- | --- |
| DETALHE-01 | Implementing | ✅ Verified |
| DETALHE-02 | Implementing | ✅ Verified |
| DETALHE-03 | Implementing | ✅ Verified |
| DETALHE-04 | Implementing | ✅ Verified |
| DETALHE-05 | Implementing | ✅ Verified |
| DETALHE-06 | Implementing | ✅ Verified |
| DETALHE-07 | Implementing | ✅ Verified |
| DETALHE-08 | Implementing | ✅ Verified |

---

## Summary

**Overall**: ✅ Ready

**Spec-anchored check**: 8/8 ACs matched spec outcome, 0 spec-precision gaps
**Sensor**: 3/3 mutations killed (lightweight tier); 1 exploratory mutation on a provably-redundant defensive guard survived and is logged as a Minor code-quality note, not a spec/behavior gap
**Gate**: backend 916 passed / 0 failed; frontend 305 passed / 0 failed; lint + build + ruff + pyright all clean

**What works**: Full detail aggregation (segurado, apólice, canal, conteúdo, horários, estado, evento, versão da regra, aprovações agêntica e humana) via `ServicoDetalheResultado`; channel-specific previews (e-mail assunto+corpo vs. WhatsApp/SMS corpo+limite, no telefone field ever); version-to-critique-to-decision relating across 3 versions in order; non-enumerating 404 for both "inexistent" and "other execution" identifiers, both at the service and HTTP layer; accessible drawer with verified focus trap, `Esc` restore-to-origin, and no-double-stacking. Both documented SPEC_DEVIATIONs are independently verified as correctly justified: `RepositorioAvaliacoesRisco` genuinely isn't needed (no AC asks for risk-relevance criteria) and `RepositorioExcecoesOperacionais.obter_por_mensagem` is correctly scoped (own-mensagem test, cross-mensagem `None` test, and `mensagem_id = ?` SQL naturally excludes execution-level rows with `mensagem_id IS NULL`).

**Issues found**: None blocking. Two Minor non-blocking notes recorded under Code Quality (Modal/drawer focus-trap duplication; untested defensive guard on the exception lookup) — recommended as low-priority follow-ups, not fix tasks required before closing this story.

**Next steps**: None required. Optionally file a small follow-up task to extract a shared `useFocoPreso` hook and add one unit test for the exception-guard branch.
