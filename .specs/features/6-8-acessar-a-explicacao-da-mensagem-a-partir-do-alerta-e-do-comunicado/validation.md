# História 6.8 Validation

**Date**: 2026-09-10
**Spec**: `.specs/features/6-8-acessar-a-explicacao-da-mensagem-a-partir-do-alerta-e-do-comunicado/spec.md`
**Diff range**: `a9e5fa3` (T1) → `a31652e` (T2+T3) → `4a1e301` (T4) → `131f510` (T5) → `4a38d4c` (T6). `8283cb6` sits between `a9e5fa3` and `a31652e` and belongs to a different feature (História 6.9); excluded from this review.
**Verifier**: independent sub-agent (author ≠ verifier)

---

## Task Completion

| Task | Status  | Notes |
| ---- | ------- | ----- |
| T1   | ✅ Done | `RepositorioEntregasSimuladas.obter_id_mais_recente_por_elegibilidade`, commit `a9e5fa3` |
| T2   | ✅ Done | Combined into `a31652e` with T3 — see below |
| T3   | ✅ Done | Combined into `a31652e` with T2 |
| T4   | ✅ Done | `4a1e301` |
| T5   | ✅ Done | `131f510` |
| T6   | ✅ Done | `4a38d4c` |

**T2/T3 commit-boundary merge**: `tasks.md` documents the reason under T2's execution note — `PortasAlertaSegurado` gains a required field in T2 that only T3's composition-site changes (`montar_servico_alerta_segurado`, `montar_servico_lista_alertas_segurado`) satisfy; until both land, the app does not compose and the full `TestClient` suite cannot run. This is the same "resolving compilation dependencies" situation `implement.md` names explicitly, and merging only the commit boundary (task rows stay separate in `tasks.md`, both still individually checked off) is a reasonable resolution, not an unexplained protocol deviation. Verified independently by reading the diff of `a31652e`: it contains exactly T2's dataclass/port/resolution change and T3's schema/router/OpenAPI-snapshot change, nothing else.

---

## Spec-Anchored Acceptance Criteria

### P1: Abrir a explicação a partir de um alerta

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| ABRIREXP-01: alerta com entrega simulada associada exibe a ação | Botão "Ver como esta mensagem foi criada" presente quando `entregaSimuladaId` não é nulo | `src/frontend/src/funcionalidades/segurado/SuperficieAlertas.test.tsx:420-434` — `expect(await screen.findByRole('dialog')).toBeInTheDocument(); expect(getExplicacaoMock).toHaveBeenCalledWith(SEGURADO_ID, ENTREGA_ID)` | ✅ PASS |
| ABRIREXP-01 (backend): elegibilidade com mensagem `simulada_entregue` resolve o id certo | `entrega_simulada_id` == id da entrega associada | `src/backend/testes/test_repositorio_entregas_simuladas.py:360-373` — `assert resultado == entrega_id`; `src/backend/testes/test_alerta_segurado.py:388-393` — `assert alerta.entrega_simulada_id == entrega_id` | ✅ PASS |
| ABRIREXP-02: acionar a ação abre o drawer com `seguradoId`/`entregaSimuladaId` corretos do alerta selecionado | Chamada a `getExplicacaoComunicado(seguradoId, entregaSimuladaId)` com os valores do alerta selecionado, não de outro | `src/frontend/src/funcionalidades/segurado/SuperficieAlertas.test.tsx:454-482` (Edge Case: dois alertas, ids distintos) — `expect(getExplicacaoMock).toHaveBeenCalledWith(SEGURADO_ID, entregaOutroAlerta); expect(getExplicacaoMock).not.toHaveBeenCalledWith(SEGURADO_ID, ENTREGA_ID)` | ✅ PASS |
| ABRIREXP-02 (backend): detalhe do alerta selecionado carrega o id certo | `entrega_simulada_id` do item consultado, nunca de outro | `src/backend/testes/test_lista_alertas_segurado.py:322-338` — `assert detalhe.alerta.entrega_simulada_id == entrega_id; assert outro_detalhe.alerta.entrega_simulada_id is None`; HTTP: `src/backend/testes/test_lista_alertas_segurado_api.py:225-243` — `assert resposta.json()["alerta"]["entrega_simulada_id"] == str(entrega_id)` | ✅ PASS |
| ABRIREXP-03: alerta sem entrega simulada não exibe a ação (nunca drawer vazio/erro) | Botão ausente, nenhum drawer aberto | `src/frontend/src/funcionalidades/segurado/SuperficieAlertas.test.tsx:407-418` — `expect(screen.queryByRole('button', { name: 'Ver como esta mensagem foi criada' })).not.toBeInTheDocument()` | ✅ PASS |
| ABRIREXP-03 (backend): sem mensagem, ou mensagem não `simulada_entregue`, devolve `None` | `entrega_simulada_id` é `null` | `src/backend/testes/test_repositorio_entregas_simuladas.py:376-395` — `assert ... is None` (dois casos: sem mensagem nenhuma; mensagem existente mas não entregue) | ✅ PASS |

### P1: Abrir a explicação a partir de um comunicado

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| ABRIREXP-04: comunicado com entrega simulada exibe a mesma ação | Botão presente sempre que o comunicado carrega com sucesso (prop já garante id válido) | `src/frontend/src/funcionalidades/segurado/SuperficieComunicado.test.tsx:147-156` — `expect(await screen.findByRole('dialog')).toBeInTheDocument()` (precondição: botão precisa existir e ser clicável para o teste passar) | ✅ PASS |
| ABRIREXP-05: acionar a partir do comunicado abre com o `entregaSimuladaId` daquele comunicado específico | `getExplicacaoComunicado(seguradoId, entregaSimuladaId)` chamado com o id daquele comunicado | `src/frontend/src/funcionalidades/segurado/SuperficieComunicado.test.tsx:147-156` — `expect(getExplicacaoMock).toHaveBeenCalledWith(SEGURADO_ID, ENTREGA_ID)` | ✅ PASS |

### P1: Foco devolvido corretamente após fechar, qualquer que seja a origem

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| ABRIREXP-06: fechar a explicação aberta a partir de um alerta devolve o foco ao botão daquele alerta | `botaoAbrir` (referência ao elemento específico) recebe foco de volta | `src/frontend/src/funcionalidades/segurado/SuperficieAlertas.test.tsx:436-452` — `await waitFor(() => expect(botaoAbrir).toHaveFocus())` | ✅ PASS |
| ABRIREXP-07: fechar a explicação aberta a partir de um comunicado devolve o foco ao botão daquele comunicado | `botaoAbrir` recebe foco de volta | `src/frontend/src/funcionalidades/segurado/SuperficieComunicado.test.tsx:158-169` — `await waitFor(() => expect(botaoAbrir).toHaveFocus())` | ✅ PASS |

**Status**: ✅ All ACs covered — 7/7 requirement IDs traced to `file:line` + assertion, all matching the spec-defined outcome. No spec-precision gaps: every AC in this story specifies a precise value (button presence/absence, exact id passed to the API call, exact element receiving focus), and every assertion targets that exact value.

---

## Edge Cases

- [x] Múltiplos alertas com entregas distintas: cada botão abre a explicação da entrega correspondente ao próprio alerta, nunca a de outro — `SuperficieAlertas.test.tsx:454-482` (frontend) and `test_lista_alertas_segurado.py:322-338` (backend, `entrega_simulada_id` per-item, never mixed)
- [x] Trocar de segurado ativo com a explicação aberta fecha a explicação — `SuperficieAlertas.test.tsx:484-499` and `SuperficieComunicado.test.tsx:171-186`, both asserting `expect(screen.queryByRole('dialog')).not.toBeInTheDocument()` after a `seguradoId` prop change; backed by the `useEffect(() => definirExplicacaoAberta(false), [seguradoId])` in `SuperficieAlertas.tsx:215-217` and `SuperficieComunicado.tsx:66-68`

---

## Discrimination Sensor

Isolated scratch prepared via `git worktree add <scratch> HEAD` (frontend `node_modules` symlinked from the real tree read-only, no mutation implied). Baseline `git status --porcelain` on the real tree before sensor work: only the pre-existing, feature-unrelated `M docs/design/prototype/package-lock.json`.

| Mutation | File:line | Description | Killed? |
| --- | --- | --- | --- |
| 1 | `src/backend/central_preventiva/adaptadores/persistencia/repositorio_entregas_simuladas.py:238` | Removed the `AND m.estado = ?` filter from `obter_id_mais_recente_por_elegibilidade`'s SQL (a mensagem not yet `simulada_entregue` would now resolve an id instead of `None`) | ✅ Killed — `test_obter_id_mais_recente_por_elegibilidade_mensagem_nao_entregue_devolve_none` FAILED (`assert UUID(...) is None`) |
| 2 | `src/frontend/src/funcionalidades/segurado/SuperficieAlertas.tsx:383` | Replaced the `{detalhe.alerta.entregaSimuladaId && (` guard on the button with `{true && (` — always renders the button, even for `entregaSimuladaId === null` | ✅ Killed — `não exibe a ação quando o alerta selecionado não tem entrega simulada associada` FAILED (button found when it should be absent) |
| 3 | `src/frontend/src/funcionalidades/segurado/SuperficieComunicado.tsx:67-68` | Flipped the segurado-switch `useEffect` dependency array from `[seguradoId]` to `[]` — drawer no longer closes when the active segurado changes | ✅ Killed — `trocar de segurado ativo com o drawer aberto o fecha (Edge Case)` FAILED (dialog still present after rerender with a different `seguradoId`) |

**Sensor depth**: lightweight (3 mutations, proportional to a standard, non-P0 feature; spans both stacks and both Edge Cases).
**Result**: 3/3 killed — PASS ✅

Cleanup: `git worktree remove --force <scratch>`; `git status --porcelain` on the real tree after cleanup matches the pre-sensor baseline exactly (only the pre-existing `package-lock.json` diff).

---

## Code Quality

| Principle | Status |
| --- | --- |
| Minimum code | ✅ — every changed line traces to exposing/consuming `entrega_simulada_id` or mounting the pre-existing drawer; no unrelated refactor |
| Surgical changes | ✅ — `SuperficieExplicacaoComunicado.tsx` untouched (confirmed: `git log` shows its last commit is 5.4's `f04801a`, none of 6.8's five commits touch it); backfills to `PainelSegurado.test.tsx`/`VisaoGeralSegurado.test.tsx` are the minimum required to satisfy the new mandatory `entregaSimuladaId` field on a type those tests construct directly, not a stylistic touch |
| No scope creep | ✅ — `RespostaAlerta.entrega_simulada_id` is shared by VISAO (`alerta_segurado.py`) and ALERTAS (`lista_alertas_segurado.py`) because the schema itself is shared; VISAO's UI (`VisaoGeralSegurado.tsx`) was not touched, matching the spec's Out-of-Scope entry for that origin |
| Matches patterns | ✅ — `obter_id_mais_recente_por_elegibilidade` reuses the same JOIN/connection pattern as `listar_por_segurado`; `_resposta_alerta` translation follows the existing one-field-per-line pattern in both routers; frontend `snake_case → camelCase` translators follow the existing per-field mapping style |
| Would senior engineer approve? | ✅ |
| Spec-anchored outcome check (asserted values match spec) | ✅ — see AC table above; every assertion targets the exact id/element/presence the spec names, not a loose "something happened" check |
| Per-layer Coverage Expectation met (domain 1:1 ACs; routes happy+edge+error) | ✅ — repository (4 cases: found/none/not-yet-delivered/multi-channel tie-break), application (2 cases: populated/None), both HTTP routers (happy path + populated-value path each), OpenAPI sync test unchanged/still green, frontend api layer (mapped/null/empty/network-error), both frontend components (present/absent, correct call args, focus return, Edge Cases) |
| Every test maps to a spec requirement — no unclaimed tests | ✅ — every new test's docstring/name cites an ABRIREXP-NN or an Edge Case; the two backfills (`PainelSegurado.test.tsx:68`, `VisaoGeralSegurado.test.tsx:42`) are fixture updates required by T5's now-mandatory field, not new test cases, and are disclosed as such in `4a38d4c`'s commit message |
| Documented guidelines followed | ✅ — `.specs/LESSONS.md`'s "todo módulo `api/*.ts` precisa de teste próprio" guideline: `alertaSegurado.test.ts` and `listaAlertasSegurado.test.ts` are the first dedicated test files for those two api modules (T5), exactly per the lesson |

### T4's widened "no administrative action" assertion

`4a1e301` changes `SuperficieComunicado.test.tsx`'s `não apresenta nenhum elemento de ação administrativa` test from `expect(screen.queryAllByRole('button')).toHaveLength(0)` to iterating buttons against a forbidden-action regex list (`/editar regra/i, /gerar mensagem/i, /aprovar lote/i, /iniciar simulação/i`).

Verified independently: `PainelSegurado.test.tsx:211-220` (a different, pre-existing test file in the same feature area) already uses the identical forbidden-action list and pattern. The zero-button assumption in the old `SuperficieComunicado` test held only because, before 6.8, the component genuinely rendered no buttons at all when loaded — 6.8 adds the read-only "Ver como esta mensagem foi criada" button, which is not an administrative action (it opens a read-only explanation, mirroring `SuperficieExplicacaoComunicado`'s own already-read-only nature from 5.4). The new assertion still fails if any of the four forbidden edit/generate/approve/simulate actions were ever added to this read-only surface — it is a like-for-like adaptation to new legitimate functionality, matching an existing project pattern, not a weakened test.

---

## Gate Check

- **Gate command**: Backend full — `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright`; Frontend full — `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`; plus `npm run verificar-tipos-api --prefix src/frontend` against a live backend instance
- **Result**:
  - Backend: 1118 passed, 0 failed, 0 skipped; ruff — all checks passed; pyright — 0 errors, 0 warnings, 0 informations
  - Frontend: 543 passed (52 test files), 0 failed, 0 skipped; lint — 0 errors (pre-existing warnings only, none in files touched by 6.8); build — succeeded
  - `verificar-tipos-api`: `src/api/tipos-gerados.ts está sincronizado com o contrato OpenAPI do backend em execução` (backend started at `127.0.0.1:8000`, confirmed via `GET /api/v1/saude` → `{"status":"disponivel", ...}`, killed after the check)
- **Test count before feature**: Backend 1099 (`.specs/STATE.md`'s 6.1 completion entry); Frontend 525 (`8283cb6`'s commit message, final state of a separately-verified História 6.9)
- **Test count after feature**: Backend 1118 (+19); Frontend 543 (+18)
- **Delta**: backend +19 new tests (T1: 4, T2/T3: additional integration/unit tests across `test_alerta_segurado.py`, `test_alerta_segurado_api.py`, `test_lista_alertas_segurado.py`, `test_lista_alertas_segurado_api.py`); frontend +18 (T4: +8, T5: +10 first-ever tests for `alertaSegurado.ts`/`listaAlertasSegurado.ts`, T6: net +5 counted against T5's checkpoint after two fixture backfills are absorbed — see task-level counts in `tasks.md`, all internally consistent with the final observed 543)
- **Skipped tests**: none
- **Failures**: none

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
| --- | --- | --- |
| ABRIREXP-01 | Implementing | ✅ Verified |
| ABRIREXP-02 | Implementing | ✅ Verified |
| ABRIREXP-03 | Implementing | ✅ Verified |
| ABRIREXP-04 | Implementing | ✅ Verified |
| ABRIREXP-05 | Implementing | ✅ Verified |
| ABRIREXP-06 | Implementing | ✅ Verified |
| ABRIREXP-07 | Implementing | ✅ Verified |

---

## Summary

**Overall**: ✅ Ready

**Spec-anchored check**: 7/7 ACs matched spec outcome, 0 spec-precision gaps
**Sensor**: 3/3 mutations killed
**Gate**: backend 1118 passed / frontend 543 passed, both stacks lint+build+type-check clean, OpenAPI/TS types confirmed in sync against a live backend

**What works**: Both new entry points ("alerta" and "comunicado") to `SuperficieExplicacaoComunicado` are wired correctly, gated on a non-null `entregaSimuladaId`, resolve the correct id per item (verified against multi-item/multi-alert scenarios), close on segurado switch, and return focus to the originating button. The backend correctly resolves the most-recent `simulada_entregue` delivery per elegibilidade, tie-broken by `criado_em DESC`, and exposes it as an additive, nullable field on the shared `RespostaAlerta` contract without touching VISAO's UI (correctly Out of Scope). `SuperficieExplicacaoComunicado` itself remains byte-for-byte untouched, matching 6.8's stated scope boundary.

**Issues found**: none

**Next steps**: None required. Feature ready to be marked Verified.
