# História 4.4: Consultar a linha do tempo ponta a ponta — Validation

**Date**: 2026-09-05
**Spec**: `.specs/features/4-4-consultar-a-linha-do-tempo-ponta-a-ponta/spec.md`
**Diff range**: `48ece26..52a78c1` (T1 `f60a11b`, T2 `2235b48`, T3 `be32d6e`, T4 `52a78c1`)
**Verifier**: independent sub-agent (author ≠ verifier)

---

## Task Completion

| Task | Status  | Notes |
| ---- | ------- | ----- |
| T1   | ✅ Done | `ServicoLinhaDoTempo.montar` — `src/backend/central_preventiva/aplicacao/linha_do_tempo.py` |
| T2   | ✅ Done | `ServicoLinhaDoTempo.buscar_execucoes` — same file |
| T3   | ✅ Done | HTTP router — `src/backend/central_preventiva/adaptadores/http/linha_do_tempo.py`, registered in `composicao/api.py` |
| T4   | ✅ Done | `SuperficieLinhaDoTempo.tsx` + client `src/frontend/src/api/linhaDoTempo.ts` |

All boxes in `tasks.md` are checked; no partial/blocked tasks.

**SPEC_DEVIATION claims independently verified:**

1. **`sincronizacoes_meteorologicas`/`tentativas_coleta_meteorologica` have no `execucao_id`.** Confirmed against the actual migration SQL: `migracoes/0002_meteorologia.sql` keys `sincronizacoes_meteorologicas` by `area_monitorada_id`/`requisicao_id`; `migracoes/0003_resiliencia_meteorologica.sql` keys `tentativas_coleta_meteorologica` by `sincronizacao_id` only — neither table declares `execucao_id`. `RepositorioSincronizacoes`/`RepositorioTentativasColeta` (`repositorio_meteorologia.py`) expose no execution-scoped read method. `gerenciador_execucoes.py` confirms `registrar_marco(execucao_id, EstadoExecucao.FALHOU_COLETA.value)` on failure and `registrar_marco(execucao_id, MARCO_COLETA_CONCLUIDA)` on success — `marcos_execucao` is indeed the real, correlated source for the coleta stage. Claim accurate.
2. **`RepositorioExecucaoPreventiva.listar_todas()`** (`repositorio_execucao_preventiva.py:150`, `SELECT ... ORDER BY criado_em DESC`, no filter) and **`RepositorioExcecoesOperacionais.listar_por_execucao()`** (same file, `WHERE execucao_id = ?`) are both absent from `design.md`'s Code Reuse Analysis but are load-bearing: `listar_todas` is called from `buscar_execucoes` (`aplicacao/linha_do_tempo.py:243`), `listar_por_execucao` from `montar` (`aplicacao/linha_do_tempo.py:200`). Scope isolation is proven by a dedicated test: `testes/test_repositorio_execucao_preventiva.py::test_listar_por_execucao_das_excecoes_nao_traz_excecao_de_outra_execucao` creates two executions, registers one exception on each, and asserts `listar_por_execucao` for the first returns only `["falha_desta"]`. Claim accurate.
3. **Diff surface is additive.** `git diff --stat 48ece26..52a78c1` touches 16 files: 2 new spec/tasks docs, 2 new backend source files, 1 extended backend repository file (2 new methods only, confirmed by reading the full diff — no existing method body changed), 1 line-count-neutral registration addition to `composicao/api.py` (new import + `include_router` call, nothing else touched), regenerated `openapi.json`/`tipos-gerados.ts` contract snapshots, and new/extended test files. No migration file, no existing repository method for 2.1–4.3, and no unrelated route touched.

---

## Spec-Anchored Acceptance Criteria

### P1: Cronologia completa com marcos correlacionados

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| TIMELINE-01: linha do tempo completa exibe coleta→...→visualização em ordem cronológica | Todos os marcos presentes, ordem cronológica não decrescente | `testes/test_linha_do_tempo.py:249-294` — `tipos_presentes == {...8 tipos...}`; `timestamps == sorted(timestamps)` | ✅ PASS |
| TIMELINE-02: cada marco tem data/hora, ator, ação, resultado, correlação | Todos os 5 campos presentes e não vazios em cada marco | `testes/test_linha_do_tempo.py:286-291` — `for marco in ...: assert marco.timestamp/ator/acao/resultado/correlacao` | ✅ PASS |
| TIMELINE-03: execução `sem_risco`/`sem_elegiveis` termina no motivo, sem etapa inexistente | Nenhum marco de geração/crítica/simulação/visualização presente | `testes/test_linha_do_tempo.py:297-315` (`sem_risco`) e `:317-334` (`sem_elegiveis`) — `TIPO_GERACAO/TIPO_CRITICA/TIPO_SIMULACAO/TIPO_VISUALIZACAO not in tipos_presentes` | ✅ PASS |
| TIMELINE-04: mensagem com 3 tentativas expande versões/avaliações/motivos na ordem correta | Ordem real das tentativas, não ordem de inserção; proveniência ligada à mensagem | `testes/test_linha_do_tempo.py:337-380` — timestamps forçados via `UPDATE versoes_mensagem SET criado_em` fora de ordem de inserção (`definir_timestamp`, linha 362-365); `[m.timestamp ...] == sorted(...)`; `[m.acao ...] == ["geração — tentativa 1", "2", "3"]`; `all(m.mensagem_id == mensagem_id ...)` | ✅ PASS — genuinely proves chronological ordering, not insertion-speed luck (see Discrimination Sensor #1) |

### P1: Navegação entre execuções correlacionadas

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| TIMELINE-05: origem↔retentativa navegáveis, IDs/estados/marcos separados nas duas direções | `execucao_origem_id`/`retentativas` corretos em ambas; marcos nunca se misturam | `testes/test_linha_do_tempo.py:383-406` — `linha_origem.retentativas == (retentativa_id,)`; `linha_retentativa.execucao_origem_id == cenario.execucao_id`; `{m.acao for m in linha_origem.marcos} == {"falhou_coleta"}` vs `{"coleta_concluida"}` for retentativa | ✅ PASS |

### P1: Marco único de visualização e ausência de duplicação

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| TIMELINE-06/07: comunicado reaberto 3× → 1 único marco de visualização | `len(marcos_visualizacao) == 1` | `testes/test_linha_do_tempo.py:409-427` — visualiza 3× (2 mesmo segurado, 1 outro), assert `len == 1` | ✅ PASS |

### P2: Pesquisa, localização temporal e acessibilidade

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| TIMELINE-08: filtro por canal/segurado/estado retorna só correspondentes | Lista restrita, combinável, sem alterar dado | `testes/test_linha_do_tempo.py:462-489,516-526` (unit) + `testes/test_linha_do_tempo_api.py:127-141` (HTTP); `test_buscar_execucoes_nao_altera_nenhum_dado` (linha 492) confirma idempotência | ✅ PASS |
| TIMELINE-09: filtro sem correspondência mostra explicação, nunca erro técnico | `resultado == []`, status 200 (não erro) | `testes/test_linha_do_tempo.py:505-513`; `testes/test_linha_do_tempo_api.py:184-194` — `status_code == 200`, `resultados == []`; frontend: `SuperficieLinhaDoTempo.test.tsx:150-157` — texto "Nenhuma execução corresponde à busca informada." | ✅ PASS |
| TIMELINE-10: horários UTC localizados de forma consistente, valor canônico auditável | Exibição localizada + `title`/`dateTime` com valor UTC original | `SuperficieLinhaDoTempo.tsx:69-76` (`<time dateTime={marco.timestamp} title={marco.timestamp}>`); `SuperficieLinhaDoTempo.test.tsx:126-137` — `elemento.getAttribute('title') === '2026-09-01T08:00:00+00:00'` e `textContent !== timestamp` bruto | ✅ PASS |
| TIMELINE-11: navegação por teclado/leitor de tela anuncia ordem/agrupamento/estado expandido; rolagem interna com nome acessível | `role="group"` nativo via `<details>`, `aria-label`/`role="region"` + `tabIndex` na rolagem | `SuperficieLinhaDoTempo.test.tsx:141-172` — `grupo.tagName === 'DETAILS'`, `toHaveAttribute('open')`, clique fecha e `not.toHaveAttribute('open')`; `regiao` tem `role="region"`, `aria-label="Linha do tempo"`, `tabindex="0"` | ✅ PASS |

**Status**: ✅ All 11 ACs covered with `file:line` evidence matching the spec-defined outcome — no spec-precision gaps.

---

## Discrimination Sensor

Isolated `git worktree add <scratch> HEAD` at `/private/tmp/.../scratchpad/wt-4-4` (never `git stash`). Baseline `git status --porcelain` on the real tree: empty, before and after.

| # | File:line | Description | Killed? |
| - | --- | --- | --- |
| 1 | `aplicacao/linha_do_tempo.py:246` | `sorted(marcos, key=..., reverse=True)` — flipped chronological sort | ✅ Killed — 2 tests failed (`test_execucao_completa_...`, `test_mensagem_com_tres_tentativas_...`) |
| 2 | `aplicacao/linha_do_tempo.py:196` | `if excecao.mensagem_id is None:` → `is not None:` — miscategorizes execution/message exceptions | ✅ Killed — `test_excecao_de_execucao_e_de_mensagem_aparecem_intercaladas_na_ordem_real` failed (`1 == 2`) |
| 3 | `aplicacao/linha_do_tempo.py` (canal filter) | `any(...)` → `all(...)` in `buscar_execucoes` canal check | ✅ Killed — `test_buscar_execucoes_sem_correspondencia_devolve_lista_vazia` failed (execution with zero messages leaked through via vacuous `all()`) |
| 4 | `adaptadores/http/linha_do_tempo.py` | `404` → `410` on execução inexistente | ✅ Killed — `test_consultar_linha_do_tempo_de_execucao_inexistente_devolve_404` failed |
| 5 | `SuperficieLinhaDoTempo.tsx` (agruparPorMensagem) | Removed `mensagensVistas.has(...)` dedup guard — each marco of the same message re-triggers a new group | ✅ Killed — grouping test failed (`expected length 2 but got 3`) |

**Sensor depth**: P0-full (5 mutations, closing story of Épico 4)
**Result**: 5/5 killed — PASS ✅
Worktree removed with `git worktree remove --force`; `git status --porcelain` on the real tree confirmed unchanged (empty) after cleanup.

---

## Code Quality

| Principle | Status |
| --- | --- |
| No features beyond what was asked | ✅ |
| No abstractions for single-use code | ✅ — `Protocol` classes per source mirror the existing pattern from 4.1/4.2's aggregation services |
| No unnecessary "flexibility" added | ✅ |
| Only touched files required for task | ✅ — confirmed by diff-stat surface (Task Completion #3) |
| Didn't "improve" unrelated code | ✅ |
| Matches existing patterns/style | ✅ — `problem+json` error shape, `RepositorioX(caminho)` constructor pattern, `clienteApi.GET` typed client all match sibling features |
| Would senior engineer approve? | ✅ |
| Tests map to acceptance criteria and are non-shallow (spot-check one story) | ✅ — spot-checked TIMELINE-04: the "3 tentativas" test forces `criado_em` via raw `UPDATE` (line 362-365) specifically so the assertion cannot pass by accident of insertion order; this is a materially stronger test than a naive happy-path assertion |
| Spec-anchored outcome check | ✅ — see table above, no vague assertions accepted |
| Per-layer Coverage Expectation met | ✅ — domain (`montar`/`buscar_execucoes`) has 1:1 AC mapping; HTTP router covers happy path, 404, 422 (both invalid UUID and invalid canal), and empty-filter paths |
| Every test in scope maps to a spec AC/edge case/Done-when | ✅ — no unclaimed tests found across `test_linha_do_tempo.py`, `test_linha_do_tempo_api.py`, the 3 new `test_repositorio_execucao_preventiva.py` tests, and the frontend test file |
| Documented guidelines followed | ✅ — `AGENTS.md`/`README.md`; read-only aggregation pattern matches `testes/test_consolidacao_resultados.py` (4.1) and `testes/test_detalhe_resultado.py` (4.2) floors named in the Test Coverage Matrix |

**N+1 query pattern in `buscar_execucoes` — judged defensible for this PoC.** `buscar_execucoes` loops every execution from `listar_todas()` and issues a `listar_por_execucao` query against `mensagens`/`elegibilidades` per execution to apply filters. This is O(n) round-trips against an embedded DuckDB file with no network hop, over a synthetic demo dataset (tens of executions, not thousands); `design.md`'s own Risks & Concerns section names this exact trade-off and accepts it explicitly, and each underlying repository call is itself index-appropriate (filtered by `execucao_id`, not a full-table scan). This crosses into a real problem only if the dataset volume assumption changes (e.g. thousands of executions in the demo), which is out of scope for a PoC. Verdict: defensible as documented, not a defect — no fix task warranted.

---

## Edge Cases

- [x] Execução com múltiplas mensagens agrupa por mensagem sem intercalar de forma confusa — `SuperficieLinhaDoTempo.tsx:41-62` (`agruparPorMensagem`, position = first marco's index) + `SuperficieLinhaDoTempo.test.tsx:92-108` (coleta solto → grupo A (08:05) → grupo B (08:10), verified via `textContent.indexOf` ordering)
- [x] Filtro sem correspondência mostra explicação, nunca erro técnico — `testes/test_linha_do_tempo_api.py:184-194` (`200`, `resultados: []`) + `SuperficieLinhaDoTempo.test.tsx:150-157` (explanatory text, no `role="alert"`)
- [x] Exceções técnicas intercaladas com marcos de sucesso aparecem na ordem cronológica real, sem esconder nem reordenar — `testes/test_linha_do_tempo.py:430-451` (`test_excecao_de_execucao_e_de_mensagem_aparecem_intercaladas_na_ordem_real`), independently confirmed discriminating by Sensor mutation #2

---

## Gate Check

- **Gate command (backend)**: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright`
- **Gate command (frontend)**: `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`
- **Result**: all green — pytest 963 passed / 0 failed; ruff `All checks passed!`; pyright `0 errors, 0 warnings, 0 informations`; vitest 320 passed (34 files) / 0 failed; oxlint exit 0 (21 pre-existing warnings, none in files touched by this feature); vite build succeeded
- **Test count before feature**: 940 backend / 312 frontend
- **Test count after feature**: 963 backend / 320 frontend
- **Delta**: +23 backend (T1: 13 unit in `test_linha_do_tempo.py` for `montar`/`buscar_execucoes` scenarios, T3: 6 in `test_linha_do_tempo_api.py`, +3 in `test_repositorio_execucao_preventiva.py`, +1 in `test_saude.py`) / +8 frontend (`SuperficieLinhaDoTempo.test.tsx`)
- **Skipped tests**: none
- **Failures**: none

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
| --- | --- | --- |
| TIMELINE-01 | Implementing | ✅ Verified |
| TIMELINE-02 | Implementing | ✅ Verified |
| TIMELINE-03 | Implementing | ✅ Verified |
| TIMELINE-04 | Implementing | ✅ Verified |
| TIMELINE-05 | Implementing | ✅ Verified |
| TIMELINE-06 | Implementing | ✅ Verified |
| TIMELINE-07 | Implementing | ✅ Verified |
| TIMELINE-08 | Implementing | ✅ Verified |
| TIMELINE-09 | Implementing | ✅ Verified |
| TIMELINE-10 | Implementing | ✅ Verified |
| TIMELINE-11 | Implementing | ✅ Verified |

---

## Summary

**Overall**: ✅ Ready

**Spec-anchored check**: 11/11 ACs matched spec outcome, 0 spec-precision gaps
**Sensor**: 5/5 mutations killed (P0-full tier)
**Gate**: backend 963 passed (ruff clean, pyright clean); frontend 320 passed (lint clean, build succeeded)

**What works**: Full 9-source aggregation (`marcos_execucao`, `avaliacoes_risco`, `elegibilidades_historicas`, `versoes_mensagem`+`avaliacoes_criticas`+`decisoes_humanas`, `excecoes_operacionais`, `entregas_simuladas`+`visualizacoes_comunicado`) sorted into one chronological, correlation-preserving timeline; correlated-execution navigation never mixes marcos; single-visualization guarantee holds under repeated reopens; combinable segurado/canal/estado search with no side effects and graceful empty-result handling; frontend grouping/localization/accessibility all independently test-covered and mutation-confirmed. Both documented SPEC_DEVIATIONs (missing `execucao_id` on meteorology tables; two new undocumented-in-design repository methods) were independently verified against the actual migration SQL and repository code, not just trusted from the docstring.

**Issues found**: none.

**Next steps**: None — feature verified, ready to close Épico 4.

---

## Épico 4 Closing Verdict

With História 4.4 verified, Épico 4 (Histórias 4.1–4.4) is closed. Cross-cutting invariants checked across the épico:

- **Read-only aggregation, no new tables across all 4 stories.** Confirmed for 4.4 (no migration file in this diff; `design.md`'s Data Models section explicitly states "Nenhuma migração nova"). Consistent with the pattern established in 4.1 (`test_consolidacao_resultados.py`) and 4.2 (`test_detalhe_resultado.py`), both named as the coverage floor in this story's own Test Coverage Matrix.
- **Non-enumeration pattern for cross-owner/cross-segurado lookups (4.2/4.3).** 4.4 introduces the one deliberate, explicitly justified exception: `listar_todas()` enumerates every execution, but only to power the MVP's own search-before-open flow (an explicit Assumption in this story's `spec.md`, not a departure from 4.2/4.3's per-segurado scoping — those still resolve by exact id, never listing across owners).
- **"Enviada — simulação"/simulated-only framing never implies a real provider.** Confirmed literally reused, unchanged, in `_marcos_simulacao_e_visualizacao` (`aplicacao/linha_do_tempo.py`): `resultado="Enviada — simulação"` is read verbatim from 3.6's own literal, not re-derived or reworded.
- **Terminal states never reopen (AD-7).** 4.4 reads this invariant rather than enforcing it (it's a pure read layer), and its own tests exercise it faithfully: `TransicaoInvalida` guard in `RepositorioExecucaoPreventiva.transicionar` is untouched by this diff, and the single-visualization test (TIMELINE-06/07) demonstrates the downstream consequence — a terminal fact (first visualization) recorded once and read once, never duplicated by repeated reopens.

All four invariants hold consistently through the épico's last story. Épico 4 verdict: ✅ **Closed — all cross-cutting invariants upheld.**
