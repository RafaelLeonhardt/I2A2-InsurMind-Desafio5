# História 6.5: Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/6-5-gerar-revisar-e-confirmar-o-envio-simulado-das-comunicacoes/design.md`
**Status**: Approved

---

## Test Coverage Matrix

> Generated from codebase sampling (`src/frontend/package.json` scripts, testes existentes de `SuperficieExecucao`/`SuperficieRevisaoLote`/`SuperficieSimulacao`, `.specs/LESSONS.md`) - nenhuma rota de backend nova, então nenhuma amostra de backend necessária. Guidelines found: `.specs/LESSONS.md` (L-024: toda distinção por texto+ícone+cor precisa afirmar os três sinais; testar sempre o valor não-padrão de todo campo booleano/enum).

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| Frontend — composição (`SuperficieExecucao`) | unit | Cada novo bloco condicional (preparação IA, geração, revisão, simulação) monta seu componente só no `estado` correto; seção genérica "Execuções correlacionadas" some quando `SuperficiePreparacaoIA` está embutida | `src/frontend/src/funcionalidades/execucao/SuperficieExecucao.test.tsx` | `npm run test --prefix src/frontend -- run SuperficieExecucao` |
| Frontend — componente (`SuperficieRevisaoLote`) | unit | Toggle de avaliação crítica abre/fecha por `versao.id`; `SuperficieAvaliacaoCritica` embutida recebe `mensagemId`+`versaoId` corretos; fecha ao trocar de item | `src/frontend/src/funcionalidades/revisao-lote/SuperficieRevisaoLote.test.tsx` | `npm run test --prefix src/frontend -- run SuperficieRevisaoLote` |
| Frontend — componente (`SuperficieSimulacao`) | unit | Edge case da spec: duplo clique em "Confirmar simulação" não dispara `confirmarSimulacao` duas vezes (botão desabilitado durante o envio) | `src/frontend/src/funcionalidades/simulacao/SuperficieSimulacao.test.tsx` | `npm run test --prefix src/frontend -- run SuperficieSimulacao` |

## Gate Check Commands

> Generated from codebase - confirm before Execute.

| Gate Level | When to Use | Command |
| --- | --- | --- |
| Quick | Após cada task individual | `npm run test --prefix src/frontend -- run <arquivo>` |
| Full | Fim da fase | `npm run test --prefix src/frontend && npm run lint --prefix src/frontend && npm run build --prefix src/frontend` |
| Build | Antes do Verifier | Frontend: `npm run test --prefix src/frontend && npm run lint --prefix src/frontend && npm run build --prefix src/frontend` (backend não tocado nesta história) |

---

## Execution Plan

### Phase 1: Encadear as etapas de produção em `SuperficieExecucao`

```
T1 → T2 → T3 → T4
```

### Phase 2: Avaliação crítica alcançável e cobertura do edge case de idempotência

```
T5 → T6
```

---

## Task Breakdown

### T1: Embutir `SuperficiePreparacaoIA` em `SuperficieExecucao` e suprimir a seção genérica duplicada

**What**: Em `SuperficieExecucao`, quando `execucao.estado` for `aguardando_geracao` ou `falhou_preparacao_ia`, renderizar `<SuperficiePreparacaoIA execucaoId={execucaoId} aoNavegar={abrirExecucao} />` logo após a seção de progresso; nesses dois estados, a seção genérica "Execuções correlacionadas" (linhas 243-278 atuais) não deve renderizar (D-1 do design).
**Where**: `src/frontend/src/funcionalidades/execucao/SuperficieExecucao.tsx`
**Depends on**: None
**Reuses**: `abrirExecucao` (já existe, linhas 174-183); `SuperficiePreparacaoIA` sem alteração
**Requirement**: FLUXOMSG-01

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `estado === 'aguardando_geracao'` monta `SuperficiePreparacaoIA` com `aoNavegar` funcional (clicar em "Ver execução de origem"/"Ver nova tentativa" navega via `selecionarSuperficie`)
- [ ] `estado === 'falhou_preparacao_ia'` também monta `SuperficiePreparacaoIA` (mostra o bloqueio)
- [ ] Nesses dois estados, a seção "Execuções correlacionadas" genérica não aparece (sem duplicar `execucaoOrigemId`/`retentativas`)
- [ ] Em qualquer outro estado, nada muda (seção genérica continua aparecendo quando aplicável, `SuperficiePreparacaoIA` não monta)
- [ ] Gate check passes: `npm run test --prefix src/frontend -- run SuperficieExecucao`
- [ ] Nenhum teste existente de `SuperficieExecucao.test.tsx` quebrado

**Tests**: unit
**Gate**: quick

**Commit**: `feat(execucao-admin): embed SuperficiePreparacaoIA by estado, dedupe correlated-executions section`

---

### T2: Embutir `SuperficieGeracaoMensagens` em `SuperficieExecucao`

**What**: Quando `execucao.estado === 'processando_mensagens'`, renderizar `<SuperficieGeracaoMensagens embutido execucaoId={execucaoId} />`.
**Where**: `src/frontend/src/funcionalidades/execucao/SuperficieExecucao.tsx`
**Depends on**: T1
**Reuses**: `SuperficieGeracaoMensagens` sem alteração
**Requirement**: FLUXOMSG-02, FLUXOMSG-03

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `estado === 'processando_mensagens'` monta `SuperficieGeracaoMensagens` embutida
- [ ] Em qualquer outro estado, não monta
- [ ] Gate check passes: `npm run test --prefix src/frontend -- run SuperficieExecucao`

**Tests**: unit
**Gate**: quick

**Commit**: `feat(execucao-admin): embed SuperficieGeracaoMensagens when processando_mensagens`

---

### T3: Embutir `SuperficieRevisaoLote` em `SuperficieExecucao`

**What**: Quando `execucao.estado === 'aguardando_revisao'`, renderizar `<SuperficieRevisaoLote embutido execucaoId={execucaoId} />`.
**Where**: `src/frontend/src/funcionalidades/execucao/SuperficieExecucao.tsx`
**Depends on**: T2
**Reuses**: `SuperficieRevisaoLote` (ainda sem o toggle de T5 nesta task)
**Requirement**: FLUXOMSG-06, FLUXOMSG-07

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `estado === 'aguardando_revisao'` monta `SuperficieRevisaoLote` embutida
- [ ] Em qualquer outro estado, não monta
- [ ] Gate check passes: `npm run test --prefix src/frontend -- run SuperficieExecucao`

**Tests**: unit
**Gate**: quick

**Commit**: `feat(execucao-admin): embed SuperficieRevisaoLote when aguardando_revisao`

---

### T4: Embutir `SuperficieSimulacao` em `SuperficieExecucao`

**What**: Quando `execucao.estado` for `aguardando_confirmacao`, `simulando` ou `falhou_simulacao`, renderizar `<SuperficieSimulacao embutido execucaoId={execucaoId} />`.
**Where**: `src/frontend/src/funcionalidades/execucao/SuperficieExecucao.tsx`
**Depends on**: T3
**Reuses**: `SuperficieSimulacao` sem alteração
**Requirement**: FLUXOMSG-08

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Os três estados montam `SuperficieSimulacao` embutida
- [ ] `estado === 'concluida'` NÃO monta nada novo (fora de escopo — História 6.6)
- [ ] Gate check passes: `npm run test --prefix src/frontend -- run SuperficieExecucao`
- [ ] Atualizar a tabela de rastreabilidade de `spec.md` (FLUXOMSG-01, 02, 03, 06, 07, 08 → Verified quando os testes desta fase passarem; FLUXOMSG-04/05 continuam Pending até T5)

**Tests**: unit
**Gate**: full

**Commit**: `feat(execucao-admin): embed SuperficieSimulacao by estado, close phase 1 traceability`

---

### T5: Drill-down para `SuperficieAvaliacaoCritica` dentro de `SuperficieRevisaoLote`

**What**: Adicionar estado local `versaoAvaliacaoAberta: string | null`; na seção "Contexto de IA, origem e proveniência", cada `<li>` de tentativa ganha um botão que alterna avaliação crítica aberta/fechada por `versao.id`; quando aberta, embute `<SuperficieAvaliacaoCritica embutido mensagemId={item.mensagemId} versaoId={versao.id} />` logo após o item correspondente.
**Where**: `src/frontend/src/funcionalidades/revisao-lote/SuperficieRevisaoLote.tsx`
**Depends on**: T4
**Reuses**: `SuperficieAvaliacaoCritica` sem alteração; `item.versoes[].id` já existente em `api/revisaoLote.ts`
**Requirement**: FLUXOMSG-04, FLUXOMSG-05

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Clicar em "Ver avaliação crítica completa" de uma tentativa embute `SuperficieAvaliacaoCritica` com `mensagemId`/`versaoId` corretos
- [ ] Clicar novamente fecha (toggle)
- [ ] Abrir a avaliação de outra tentativa fecha a anterior (só uma aberta por vez)
- [ ] Trocar de item do lote (`mensagemAberta` muda) fecha qualquer avaliação crítica aberta
- [ ] Teste cobre uma mensagem com 2 tentativas: confirma que a origem final (agente/humana) e a contagem de tentativas aparecem corretamente, reusando o comportamento já testado de `SuperficieAvaliacaoCritica`
- [ ] Gate check passes: `npm run test --prefix src/frontend -- run SuperficieRevisaoLote`

**Tests**: unit
**Gate**: quick

**Commit**: `feat(revisao-lote): add per-attempt drill-down into SuperficieAvaliacaoCritica`

---

### T6: Cobertura de teste do edge case de duplo clique em "Confirmar simulação"

**What**: Adicionar teste em `SuperficieSimulacao.test.tsx` confirmando que dois cliques consecutivos rápidos no botão de confirmação (com `reconhecido=true`) resultam em exatamente UMA chamada a `confirmarSimulacao` (comportamento já existente via `disabled={enviando}`; ganhando cobertura própria).
**Where**: `src/frontend/src/funcionalidades/simulacao/SuperficieSimulacao.test.tsx`
**Depends on**: T5
**Reuses**: mocks já existentes do arquivo (`confirmarSimulacao` mockado)
**Requirement**: Edge case (spec.md linha 87)

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Teste novo dispara dois cliques seguidos no botão de confirmação e afirma `confirmarSimulacao` chamado exatamente 1 vez
- [ ] Teste falha se `disabled={enviando}` for removido (validado manualmente comentando a linha antes de reverter — não persistido)
- [ ] Gate check passes: `npm run test --prefix src/frontend -- run SuperficieSimulacao`
- [ ] Full gate ao final: `npm run test --prefix src/frontend && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`
- [ ] Atualizar a tabela de rastreabilidade de `spec.md`: FLUXOMSG-04, FLUXOMSG-05 → Verified

**Tests**: unit
**Gate**: full

**Commit**: `test(simulacao): cover double-click confirm idempotency edge case`

---

## Phase Execution Map

```
Phase 1 → Phase 2

Phase 1:  T1 ------→ T2 ------→ T3 ------→ T4
Phase 2:  T5 ------→ T6

T4 → T5
```

A última linha é a aresta entre fases que não fica adjacente no traçado principal: `T4 → T5` (T5 só pode adicionar o drill-down em `SuperficieRevisaoLote` depois que T4 fechar a Fase 1 e a rastreabilidade parcial).

---

## Task Granularity Check

| Task | Scope | Status |
| --- | --- | --- |
| T1: Embutir `SuperficiePreparacaoIA` + suprimir seção duplicada | 1 arquivo, 1 condicional + 1 supressão | ✅ Granular |
| T2: Embutir `SuperficieGeracaoMensagens` | 1 arquivo, 1 condicional | ✅ Granular |
| T3: Embutir `SuperficieRevisaoLote` | 1 arquivo, 1 condicional | ✅ Granular |
| T4: Embutir `SuperficieSimulacao` + fechar rastreabilidade da fase | 1 arquivo, 1 condicional | ✅ Granular |
| T5: Drill-down avaliação crítica em `SuperficieRevisaoLote` | 1 arquivo, 1 estado local + 1 toggle | ✅ Granular |
| T6: Teste de duplo clique em `SuperficieSimulacao` | 1 arquivo de teste, 1 cenário | ✅ Granular |

---

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| --- | --- | --- | --- |
| T1 | None | (início da Fase 1) | ✅ Match |
| T2 | T1 | T1 → T2 | ✅ Match |
| T3 | T2 | T2 → T3 | ✅ Match |
| T4 | T3 | T3 → T4 | ✅ Match |
| T5 | T4 | T4 → T5 | ✅ Match |
| T6 | T5 | T5 → T6 | ✅ Match |

Nenhuma dependência aponta para uma fase posterior. Todas as tasks da Fase 1 editam o mesmo arquivo (`SuperficieExecucao.tsx`) em série, cada uma acrescentando um bloco condicional independente — a cadeia linear reflete a ordem real de commits, não uma dependência de conteúdo entre as condições.

---

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| --- | --- | --- | --- | --- |
| T1 | Frontend — composição (`SuperficieExecucao`) | unit | unit | ✅ OK |
| T2 | Frontend — composição (`SuperficieExecucao`) | unit | unit | ✅ OK |
| T3 | Frontend — composição (`SuperficieExecucao`) | unit | unit | ✅ OK |
| T4 | Frontend — composição (`SuperficieExecucao`) | unit | unit | ✅ OK |
| T5 | Frontend — componente (`SuperficieRevisaoLote`) | unit | unit | ✅ OK |
| T6 | Frontend — componente (`SuperficieSimulacao`) | unit | unit | ✅ OK |

Nenhuma violação.
