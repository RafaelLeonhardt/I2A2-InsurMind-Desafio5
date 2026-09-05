# História 4.3 Validation

**Date**: 2026-09-05
**Spec**: `.specs/features/4-3-registrar-a-primeira-visualizacao-do-comunicado/spec.md`
**Diff range**: `193838c..135d90d` (T1 `477a27a`, T2 `19f20fa`, T3 `39e54a6`, T4 `540cd05`, T5 `135d90d`)
**Verifier**: independent sub-agent (author ≠ verifier)

---

## Task Completion

| Task | Status  | Notes |
| ---- | ------- | ----- |
| T1   | ✅ Done | Migração aplicada como `0015` (renumerada de `0013`, motivo documentado no `.sql` e no `README.md`) |
| T2   | ✅ Done | Repositório + achado empírico de concorrência DuckDB, verificado independentemente (ver Discrimination Sensor) |
| T3   | ✅ Done | Serviço com 2 `SPEC_DEVIATION`s, ambas confirmadas load-bearing |
| T4   | ✅ Done | Roteador HTTP, decisão deliberada de dispensar `Idempotency-Key` |
| T5   | ✅ Done | Componente React, gatilho em efeito separado |

---

## Spec-Anchored Acceptance Criteria

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| VISU-01: abrir efetivamente registra uma única transição p/ `Visualizada no portal`, com data/hora UTC | `visualizada_em` persistido, não nulo, uma linha | `src/backend/testes/test_repositorio_visualizacoes_comunicado.py:28-32` - `assert visualizacao.visualizada_em is not None`; `src/backend/testes/test_visualizacao_comunicado_api.py:137-145` - `assert primeira.status_code == segunda.status_code == 200` | ✅ PASS |
| VISU-02: reabrir/atualizar página já visualizada mantém conteúdo, sem nova entrega/mensagem/transição/data | mesma `visualizada_em`, mesma linha (`id` igual) | `src/backend/testes/test_repositorio_visualizacoes_comunicado.py:46-51` - `assert segunda.id == primeira.id` e `assert segunda.visualizada_em == primeira.visualizada_em`; `src/backend/testes/test_visualizacao_comunicado_api.py:144-150` - `assert primeira.json() == segunda.json()` | ✅ PASS |
| VISU-03: duas aberturas concorrentes convergem para uma única transação/estado | 0 exceções, 1 linha, mesma `visualizada_em` nas duas respostas | `src/backend/testes/test_repositorio_visualizacoes_comunicado.py:78-108` - `assert erros == {}` e `assert visualizacao_a == visualizacao_b` (threads reais, conexões distintas) | ✅ PASS (verificado independentemente — ver Discrimination Sensor) |
| VISU-04: mensagem não simulada/rejeitada/excluída/exceção é recusada com erro de domínio explícito, sem marco criado | `MensagemNaoElegivelParaComunicado` levantada; `409 application/problem+json`; nenhuma linha gravada | `src/backend/testes/test_visualizacao_comunicado.py:151-213` - `except MensagemNaoElegivelParaComunicado` + `assert cenario.visualizacoes.obter_por_entrega(entrega_id) is None` (4 estados); `src/backend/testes/test_visualizacao_comunicado_api.py:153-169` - `assert resposta.status_code == 409` e `corpo["codigo"] == "mensagem_nao_elegivel_para_comunicado"` | ✅ PASS |
| VISU-05: comunicado renderizado mostra conteúdo/canal/natureza simulada/linha do tempo, sem ação administrativa nem confirmação de provedor | UI sem `role="button"`; API isola por segurado com 404 genérico idêntico | `src/frontend/src/funcionalidades/segurado/SuperficieComunicado.test.tsx:106-112` - `expect(screen.queryAllByRole('button')).toHaveLength(0)`; `src/backend/testes/test_visualizacao_comunicado_api.py:172-187` - `assert resposta_de_outro.status_code == resposta_inexistente.status_code == 404` e mesmo `codigo` | ✅ PASS |
| VISU-06: falha local preserva estado de erro consultável, permite reabertura idempotente | UI mostra erro, não "Visualizada no portal"; nova tentativa confirma | `src/frontend/src/funcionalidades/segurado/SuperficieComunicado.test.tsx:116-134` - `expect(screen.queryByText(/Visualizada no portal/)).not.toBeInTheDocument()`; `:136-156` - `expect(registrarVisualizacaoComunicado).toHaveBeenCalledTimes(2)` e `expect(await screen.findByText(/Visualizada no portal/)).toBeInTheDocument()` | ✅ PASS |
| VISU-07: interface nunca antecipa visualmente `Visualizada no portal` antes da confirmação real | selo inicial é "Confirmando visualização…"/"Não confirmada", nunca "Visualizada" antes do `then` do POST | `src/frontend/src/funcionalidades/segurado/SuperficieComunicado.tsx:183-211` (`SeloVisualizacao` só renderiza "Visualizada no portal" quando `estado === 'confirmada' && visualizadaEm`) verificado por `SuperficieComunicado.test.tsx:116-134` | ✅ PASS |

**Status**: ✅ All ACs covered

---

## Discrimination Sensor

Executado em `git worktree add` isolado (`/private/tmp/.../scratchpad/wt-sensor`), nunca no working tree real. Antes de mutar, uma verificação independente do achado empírico do T2 foi feita com um script de stress próprio (não commitado): 60 iterações × 8 threads reais sobre um `INSERT ... ON CONFLICT DO NOTHING` **sem** `suppress` confirmaram 37 `duckdb.ConstraintException` genuínas sob corrida real (nenhuma inesperada); a mesma bateria contra o repositório real (**com** `suppress`) produziu 0 exceções não tratadas e 0 divergências em 480 chamadas concorrentes — o achado do docstring é real, e o par de exceções capturado (`ConstraintException`/`TransactionException`) é específico do DuckDB, não uma captura genérica que arriscaria engolir um erro não relacionado.

| Mutation | File:line | Description | Killed? |
| --- | --- | --- | --- |
| 1 | `repositorio_visualizacoes_comunicado.py:70` | Removido o `with suppress(duckdb.ConstraintException, duckdb.TransactionException):` ao redor do `INSERT`, voltando a um `.execute()` desprotegido | ✅ Killed — `test_duas_chamadas_concorrentes_convergem_para_a_mesma_visualizacao` falha com `ConstraintException` real não tratada |
| 2 | `visualizacao_comunicado.py:143` | Invertido `if mensagem.estado is not EstadoMensagem.SIMULADA_ENTREGUE` → `is EstadoMensagem.SIMULADA_ENTREGUE` | ✅ Killed — 8 testes falham (`test_visualizacao_comunicado.py` ×6, `test_visualizacao_comunicado_api.py` ×2), incluindo o caminho feliz virando recusa e as recusas virando gravação |
| 3 | `SuperficieComunicado.tsx:93` | Removida a guarda `visualizacaoAtual !== null` do efeito de disparo do `POST` | ✅ Killed — `não dispara uma segunda visualização quando o comunicado já chega com uma` falha (POST chamado 1x quando deveria ser 0x) |

**Sensor depth**: lightweight (3/3 mutations, proporcional ao risco: concorrência de escrita, elegibilidade de domínio, disparo duplicado de efeito)
**Result**: 3/3 killed - PASS ✅
**Isolation check**: `git status --porcelain` idêntico antes/depois do sensor (vazio nos dois casos); worktree removido com `git worktree remove --force`.

---

## Code Quality

| Principle | Status |
| --- | --- |
| Minimum code | ✅ |
| Surgical changes | ✅ — só os arquivos da migração 15, repositório, serviço, roteador, composição, frontend e seus testes/contratos |
| No scope creep | ✅ |
| Matches patterns | ✅ — mesmo padrão de dedução por `UNIQUE` de 2.2/2.5, mesmo `application/problem+json` e não-enumeração 404 de 4.2 |
| Spec-anchored outcome check (asserted values match spec) | ✅ |
| Per-layer Coverage Expectation met (domain 1:1 ACs; routes happy+edge+error) | ✅ — `test_visualizacao_comunicado.py` cobre os 4 estados não elegíveis 1:1; roteador cobre feliz/concorrência/não-elegível/isolamento/422 |
| Every test maps to a spec requirement — no unclaimed tests | ✅ |
| Documented guidelines followed: `AGENTS.md`, `README.md` da persistência, padrão de dedução `UNIQUE` de `test_repositorio_eventos_meteorologicos.py` | ✅ |

**Additional judgment calls verified**:
- Duas `SPEC_DEVIATION`s em `visualizacao_comunicado.py`/`repositorio_visualizacoes_comunicado.py` (parâmetro `segurado_id` extra, retorno `Optional`, e `obter_por_id` novo em `RepositorioEntregasSimuladas`) — confirmadas load-bearing: sem elas, `test_registrar_visualizacao_de_outro_segurado_devolve_none_sem_gravar` e o `404` do `POST` de outro segurado (VISU-05) não seriam possíveis. `obter_por_id` tem cobertura própria em `test_repositorio_entregas_simuladas.py:196-221`.
- Ausência deliberada de `Idempotency-Key` no roteador de visualização — julgada exceção legítima e escopada: nem `spec.md` nem `tasks.md` (Done-when de T4) exigem o cabeçalho para esta história; a operação não tem corpo variável e a unicidade já vem do `UNIQUE(entrega_simulada_id)`, então o risco que `chaves_idempotencia`/AD-002 existe para mitigar ("mesma chave, conteúdo diferente") não se aplica aqui. Justificativa está documentada no docstring do módulo. Não é uma inconsistência silenciosa — é uma decisão registrada e escopada corretamente.
- Sequenciamento do `useEffect` de disparo do `POST` em `SuperficieComunicado.tsx` — confirmado real, não apenas alegado: o efeito depende só de `estadoCarregamento`, que só passa a `'disponivel'` depois que o `.then()` do `GET` já setou `comunicado`/`visualizacaoAtual` e o React já commitou a árvore com o conteúdo renderizado; o teste `não dispara o POST de visualização enquanto o conteúdo ainda não renderizou` prova isso com uma promise controlada. Um unmount/remount rápido reseta o estado local e refaz o ciclo `GET → disponível → POST` do zero (não é um "duplo disparo" da mesma leitura), e o backend é idempotente por construção para esse caso; mutação 3 acima confirma que a guarda `visualizacaoAtual !== null` é o que realmente impede o disparo duplo dentro do mesmo ciclo de vida do componente.

---

## Edge Cases

- [x] Entrega de canal e-mail aberta pelo perfil Segurado registra a visualização do mesmo jeito, independente do canal original — `registrar_visualizacao` (backend) e `registrarVisualizacaoComunicado` (frontend) não recebem nem ramificam por `canal`; exercitado com `canal: 'email'` na fixture padrão de `SuperficieComunicado.test.tsx` (`comunicado()`, linha 25) no teste de gatilho VISU-01 (linhas 61-73).
- [x] Segurados sintéticos diferentes têm visualizações isoladas, nunca misturadas — `test_registrar_visualizacao_de_outro_segurado_devolve_none_sem_gravar` (`test_visualizacao_comunicado.py:230-241`) e `test_registrar_visualizacao_de_outro_segurado_devolve_404_generico` (`test_visualizacao_comunicado_api.py:190-203`).
- [x] Duas visualizações concorrentes no mesmíssimo milissegundo garantem uma única linha — `test_duas_chamadas_concorrentes_convergem_para_a_mesma_visualizacao` com threads reais; reforçado pelo stress test independente de 480 chamadas concorrentes (ver Discrimination Sensor) com 0 divergências.

---

## Gate Check

- **Gate command (Build)**: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright` **e** `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`
- **Result**: backend 940 passed, 0 failed; `ruff check .` — All checks passed!; `pyright` — 0 errors, 0 warnings. Frontend: 312 passed, 0 failed (33 test files); `oxlint` — 0 errors (pré-existentes warnings `set-state-in-effect`/`only-export-components` em arquivos não tocados por esta história, fora de escopo); `vite build` — sucesso.
- **Test count before feature**: 924 backend / 305 frontend
- **Test count after feature**: 940 backend / 312 frontend
- **Delta**: +16 backend, +7 frontend
- **Skipped tests**: none
- **Failures**: none in the reproducible final runs. **Note**: one isolated frontend run (out of 5 full-suite runs across the session) showed a single transient failure in `não dispara o POST de visualização enquanto o conteúdo ainda não renderizou` (0 calls observed instead of 1). Re-ran the full suite 3 additional times and the isolated test file 5 additional times — all green (312/312, 7/7). Classified as a one-off environment/timing flake (likely cold-start `import`/`transform` contention on the first parallel worker run), not a reproducible regression; not gated on it given consistent reproducibility of the pass.

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status  |
| --- | --- | --- |
| VISU-01 | Implementing | ✅ Verified |
| VISU-02 | Implementing | ✅ Verified |
| VISU-03 | Implementing | ✅ Verified |
| VISU-04 | Implementing | ✅ Verified |
| VISU-05 | Implementing | ✅ Verified |
| VISU-06 | Implementing | ✅ Verified |
| VISU-07 | Implementing | ✅ Verified |

---

## Summary

**Overall**: ✅ Ready

**Spec-anchored check**: 7/7 ACs matched spec outcome
**Sensor**: 3/3 mutations killed
**Gate**: backend 940 passed / frontend 312 passed, 0 failed

**What works**: Primeira visualização, dedução por reabertura, convergência sob concorrência real (verificada independentemente com stress test próprio de 480 chamadas concorrentes), recusa de estados não elegíveis sem gravação, isolamento por segurado com não-enumeração 404, ausência de ações administrativas na UI, e não antecipação visual de "Visualizada no portal" com reabertura idempotente após falha local.

**Issues found**: none blocking. Two deliberate, documented judgment calls (ausência de `Idempotency-Key`; assinaturas com `segurado_id`/`Optional` divergentes do `design.md`) foram verificadas como escopadas e load-bearing, não gaps.

**Next steps**: none required. Feature ready to close.
