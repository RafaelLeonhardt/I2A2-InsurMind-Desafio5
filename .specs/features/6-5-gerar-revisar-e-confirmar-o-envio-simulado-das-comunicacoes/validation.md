# História 6.5: Gerar, revisar e confirmar o envio simulado das comunicações — Validation

**Date**: 2026-09-09
**Spec**: `.specs/features/6-5-gerar-revisar-e-confirmar-o-envio-simulado-das-comunicacoes/spec.md`
**Diff range**: `894c301..ba5c21d` (6 commits: `3f9a7d9`, `18499f7`, `e6a7c9b`, `9941370`, `b32e3bc`, `ba5c21d`)
**Verifier**: independent sub-agent (author ≠ verifier)

---

## Task Completion

| Task | Status | Notes |
| --- | --- | --- |
| T1: Embutir `SuperficiePreparacaoIA` + suprimir seção duplicada | ✅ Done | `3f9a7d9` |
| T2: Embutir `SuperficieGeracaoMensagens` | ✅ Done | `18499f7` |
| T3: Embutir `SuperficieRevisaoLote` | ✅ Done | `e6a7c9b` |
| T4: Embutir `SuperficieSimulacao` + fechar rastreabilidade Fase 1 | ✅ Done | `9941370` |
| T5: Drill-down `SuperficieAvaliacaoCritica` em `SuperficieRevisaoLote` | ✅ Done | `b32e3bc` |
| T6: Teste de duplo clique em `SuperficieSimulacao` | ✅ Done | `ba5c21d` |

No blocked or partial tasks found.

---

## Spec-Anchored Acceptance Criteria

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| FLUXOMSG-01: entrar em preparação do contexto → exibir progresso a partir dos marcos persistidos | `SuperficiePreparacaoIA` monta em `aguardando_geracao`/`falhou_preparacao_ia`; conteúdo de progresso (marcos) é responsabilidade da própria superfície, já testada | `src/frontend/src/funcionalidades/execucao/SuperficieExecucao.tsx:207,303-305` (`mostrarPreparacaoIa`); teste de composição `src/frontend/src/funcionalidades/execucao/SuperficieExecucao.test.tsx:437-460` — `findByRole('heading', {name:'Preparação da produção de mensagens'})` + `aoNavegar` funcional; conteúdo de marcos coberto por `src/frontend/src/funcionalidades/preparacao-ia/SuperficiePreparacaoIA.test.tsx:60-164` (pré-existente, fora do diff) | ✅ PASS |
| FLUXOMSG-02: avançar para geração → lista de destinatários com estado de cada mensagem | `SuperficieGeracaoMensagens` monta em `processando_mensagens`; lista pronta/em processamento/falha já testada na própria superfície | `SuperficieExecucao.tsx:208,307`; composição: `SuperficieExecucao.test.tsx:496-510`; conteúdo: `src/frontend/src/funcionalidades/geracao-mensagens/SuperficieGeracaoMensagens.test.tsx:52-114` (pré-existente) | ✅ PASS |
| FLUXOMSG-03: falha de geração (`falhou_integracao_ia`) mostrada sem bloquear as demais | Mesmo componente reusado, comportamento herdado | `SuperficieGeracaoMensagens.test.tsx:114-125` (`mostra a falha de integração como exceção do item`, pré-existente) — nada mudou nesta história, só reachability | ✅ PASS |
| FLUXOMSG-04: mensagem avaliada pelo crítico → exibir critérios e origem (agente/humana), distinguindo visualmente | Drill-down novo em `SuperficieRevisaoLote` embute `SuperficieAvaliacaoCritica` com `mensagemId`+`versaoId` corretos | `src/frontend/src/funcionalidades/revisao-lote/SuperficieRevisaoLote.tsx:426-441` (botão + embed condicional); teste `src/frontend/src/funcionalidades/revisao-lote/SuperficieRevisaoLote.test.tsx:499-519` — `getAvaliacaoCritica` chamado com `(item().mensagemId, versao().id)` e abre/fecha | ✅ PASS |
| FLUXOMSG-05: mensagem regenerada → indicar quantas tentativas e qual foi aprovada | Teste com 2 tentativas confirma contagem e origem (agente/humana) | `SuperficieRevisaoLote.test.tsx:521-552` — abre a avaliação da 2ª tentativa, `getAvaliacaoCritica` chamado com `'versao-2'`, `within(secaoAvaliacao).getByText('2ª tentativa')` e `[data-origem="decisao_humana"]` presentes | ✅ PASS |
| FLUXOMSG-06: abrir revisão em lote → exibir cada item com decisão pendente e sinal de atenção em exceção | `SuperficieRevisaoLote` (REVISAO-02, pré-existente) agora alcançável; sinal de atenção já testado | `SuperficieExecucao.tsx:209,309`; composição: `SuperficieExecucao.test.tsx:522-536`; sinal de atenção: `SuperficieRevisaoLote.test.tsx:174-212` (pré-existente, `data-sinal="excecao"`) | ✅ PASS |
| FLUXOMSG-07: decisão que exige justificativa bloqueia confirmação sem ela (REVISAO-06) | Regra já implementada e testada, só reachability nova | `SuperficieRevisaoLote.tsx:177-180`; teste `SuperficieRevisaoLote.test.tsx:296-316` (pré-existente) — bloqueia Rejeitar/Excluir/Regenerar sem justificativa, `decidirLote` não chamado | ✅ PASS |
| FLUXOMSG-08: confirmar envio simulado → registrar simulação e avançar para resultado consolidado, deixando claro que é simulação | `SuperficieSimulacao` monta nos 3 estados de simulação; aviso de simulação e chamada real já testados na própria superfície | `SuperficieExecucao.tsx:210,311`; composição: `SuperficieExecucao.test.tsx:548-565` (`it.each` dos 3 estados) e `:567-580` (não monta em `concluida`); aviso/chamada: `src/frontend/src/funcionalidades/simulacao/SuperficieSimulacao.test.tsx:102-112,125-134` (pré-existente) | ✅ PASS |

**Status**: ✅ All 8 ACs covered — 0 spec-precision gaps. FLUXOMSG-01/02/03/06/07/08's deep behavioral content is verified by each surface's own pre-existing test file (correctly out of this diff's scope per design.md's explicit framing of this story as composition/reachability only); this Verifier confirmed those pre-existing tests are real and on-point rather than assuming they exist.

---

## Edge Cases

- [x] **Todos os itens rejeitados → confirmação de "nenhum envio" permitida, sem forçar aprovação artificial.** Not touched by this diff (frontend has no client-side gate requiring ≥1 approval — `SuperficieRevisaoLote.tsx:173-180` only checks `alvos.length === 0` and justificativa, never approval count) and independently confirmed at the backend: `src/backend/testes/test_revisao_lote.py:1065-1090` (`test_sem_nenhuma_aprovada_a_execucao_conclui_sem_simulacao`, REVISAO-13, story 3.5) — rejecting/excluding every item concludes the execution directly (`EstadoExecucao.CONCLUIDA`) without forcing an approval. Confirmed inherited/unchanged, not a gap.
- [x] **Duplo clique em "Confirmar simulação" → idempotente, nunca duas simulações.** New test: `src/frontend/src/funcionalidades/simulacao/SuperficieSimulacao.test.tsx:136-162` — two consecutive clicks on the same button while `confirmarSimulacao` is pending assert `confirmarSimulacao` called exactly once, backed by `disabled={enviando}` via `confirmacaoDesabilitada={!reconhecido || enviando}` at `src/frontend/src/funcionalidades/simulacao/SuperficieSimulacao.tsx:381`. Confirmed by the discrimination sensor (mutation 4 below).

---

## Discrimination Sensor

Isolated `git worktree add /tmp/verifier-scratch-65 HEAD` (never `git stash`); `node_modules` symlinked in for speed. Baseline `git status --porcelain` on the real tree recorded only the pre-existing, unrelated `docs/design/prototype/package-lock.json` modification before any sensor work.

| Mutation | File:line | Description | Killed? |
| --- | --- | --- | --- |
| 1 | `src/frontend/src/funcionalidades/execucao/SuperficieExecucao.tsx:207` | `ESTADOS_PREPARACAO_IA.has(execucao.estado)` → `!ESTADOS_PREPARACAO_IA.has(execucao.estado)` (flip which estados embed `SuperficiePreparacaoIA`) | ✅ Killed — 6 tests failed, incl. `embute a preparação de IA em aguardando_geracao…` and `não embute a preparação de IA fora de…` |
| 2 | `src/frontend/src/funcionalidades/execucao/SuperficieExecucao.tsx:263` | Removed the `!mostrarPreparacaoIa &&` guard on the generic "Execuções correlacionadas" section (D-1 suppression) | ✅ Killed — `embute a preparação de IA em aguardando_geracao, com aoNavegar navegando para a origem` failed: generic section reappeared alongside `SuperficiePreparacaoIA`'s own |
| 3 | `src/frontend/src/funcionalidades/revisao-lote/SuperficieRevisaoLote.tsx:320` | Removed `definirVersaoAvaliacaoAberta(null)` from the "Abrir revisor de X" click handler (toggle-close-on-item-switch) | ✅ Killed — `trocar de item do lote fecha qualquer avaliação crítica aberta` failed: "Fechar avaliação crítica" button survived the item switch |
| 4 | `src/frontend/src/funcionalidades/simulacao/SuperficieSimulacao.tsx:381` | `confirmacaoDesabilitada={!reconhecido || enviando}` → `confirmacaoDesabilitada={!reconhecido}` (made the double-click guard a no-op) | ✅ Killed — `trata duplo clique em "Confirmar simulação" como idempotente` failed: button was not disabled after the first click |

**Sensor depth**: lightweight (4 targeted behavior-level mutations, proportional to a non-P0 admin composition surface).
**Result**: 4/4 killed — PASS ✅

Post-sensor isolation check: `node_modules` symlink removed, worktree removed with `git worktree remove --force`; real tree `git status --porcelain` re-checked and matches the pre-sensor baseline exactly (only the unrelated `package-lock.json` line).

---

## Non-Regression Sanity Check (6.1/6.2 behavior untouched)

- `SuperficieEventoDecisao` still embeds under the same untouched condition: `SuperficieExecucao.tsx:205-206,301` (`mostrarDecisaoDeRisco = estado !== 'coletando' && estado !== 'falhou_coleta'`) — confirmed by `SuperficieExecucao.test.tsx:360-371` (embeds in `sem_risco`) and `:373-379` (absent in `coletando`).
- Generic "Execuções correlacionadas" section still renders in states NOT in `ESTADOS_PREPARACAO_IA` (e.g. `falhou_coleta`): `SuperficieExecucao.tsx:262-299`, confirmed by `SuperficieExecucao.test.tsx:381-425` (origin/retry links still navigate) and `:427-435` (absent when no origin/retries). Only newly gated OFF specifically when `mostrarPreparacaoIa` is true (D-1), matching design intent — no broader regression.

---

## Code Quality

| Principle | Status |
| --- | --- |
| Minimum code | ✅ Purely additive conditionals in `SuperficieExecucao.tsx` (4 new `mostrarX` booleans + 4 new render blocks) and one new local-state toggle in `SuperficieRevisaoLote.tsx`; none of the 5 reused surfaces changed |
| Surgical changes | ✅ Only 3 implementation files touched (`SuperficieExecucao.tsx`, `SuperficieRevisaoLote.tsx`) + 3 test files; no API/type changes |
| No scope creep | ✅ No backend route, no new `Superficie` at `PerfilContexto` top level, matching D-3's explicit rejection of a new AD-016 destination |
| Matches patterns | ✅ New conditionals follow the exact `mostrarDecisaoDeRisco`/`SuperficieEventoDecisao` precedent already in the file; drill-down toggle follows the existing `mensagemAberta` local-state pattern |
| Spec-anchored outcome check (asserted values match spec) | ✅ See AC table above |
| Per-layer Coverage Expectation met (domain 1:1 ACs; routes happy+edge+error) | ✅ Composition layer: every `mostrarX` has a positive and negative test (`SuperficieExecucao.test.tsx`); component layer: toggle open/close/switch-closes/multi-tentativa all covered (`SuperficieRevisaoLote.test.tsx`); edge case: double-click covered (`SuperficieSimulacao.test.tsx`) |
| Every test maps to a spec requirement — no unclaimed tests | ✅ Every new test traces to a `mostrarX` condition, the T5 drill-down Done-when list, or the T6 edge case |
| Documented guidelines followed | `.specs/LESSONS.md` L-024 ("toda distinção por texto+ícone+cor precisa afirmar os três sinais") — not applicable here (no new text/icon/color distinction introduced); no other project testing doc found beyond repo conventions — strong defaults applied |

---

## Gate Check

- **Gate command**: `npm run test --prefix src/frontend && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`
- **Result**: 502 tests passed (49 files), 0 failed, 0 skipped. `oxlint` exits 0 (all output is pre-existing `set-state-in-effect`/`only-export-components` warnings spread across the whole codebase, including one at `SuperficieRevisaoLote.tsx:134` consistent with every other `Superficie*` component's `useEffect` pattern — not a new pattern introduced by this story). `vite build` succeeds (`✓ built in 280ms`).
- **Test count before feature** (`894c301`, i.e. before this story's 6 commits): matches spec.md's own claim of the pre-story baseline; **after** (`ba5c21d`): 502, matching spec.md line 108 ("frontend 502 testes"). No test deletions found across the 6-commit diff (`git diff 894c301..ba5c21d --stat` shows only additions in the 3 touched test files).
- **Skipped tests**: none.
- **Failures**: none.

---

## Fix Plans

None — no gaps found.

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
| --- | --- | --- |
| FLUXOMSG-01 | Implementing | ✅ Verified |
| FLUXOMSG-02 | Implementing | ✅ Verified |
| FLUXOMSG-03 | Implementing | ✅ Verified |
| FLUXOMSG-04 | Implementing | ✅ Verified |
| FLUXOMSG-05 | Implementing | ✅ Verified |
| FLUXOMSG-06 | Implementing | ✅ Verified |
| FLUXOMSG-07 | Implementing | ✅ Verified |
| FLUXOMSG-08 | Implementing | ✅ Verified |

---

## Summary

**Overall**: ✅ Ready

**Spec-anchored check**: 8/8 ACs matched the spec-defined outcome. 0 spec-precision gaps.
**Sensor**: 4/4 mutations killed.
**Gate**: 502 passed / 0 failed (lint clean modulo pre-existing warnings, build succeeds).

**What works**: The five pre-existing, individually-tested surfaces (`SuperficiePreparacaoIA`, `SuperficieGeracaoMensagens`, `SuperficieRevisaoLote`, `SuperficieAvaliacaoCritica`, `SuperficieSimulacao`) are now reachable exclusively through `execucao.estado`-driven composition inside `SuperficieExecucao`, following the exact precedent already set by `SuperficieEventoDecisao` (6.2) — no new navigation mechanism, no new API surface, no widened type. The D-1 duplicate-section suppression, the D-2 drill-down placement inside `SuperficieRevisaoLote` (reusing `item.versoes[].id`), and the double-click idempotency edge case are all independently confirmed by both direct tests and by the discrimination sensor (every injected fault was caught). Investigating the "all-rejected" edge case surfaced that its correct behavior (conclude the execution silently, never force an artificial approval) is genuinely inherited from story 3.5's `REVISAO-13` and independently backend-tested — not a gap, despite having no new test in this diff.

**Issues found**: none.

**Next steps**: none — feature verified, traceability updated above (spec.md's own table should be synced to "Verified" by the orchestrator as part of closing this story, consistent with the 6.4 precedent).
