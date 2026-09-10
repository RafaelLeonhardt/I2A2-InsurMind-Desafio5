# História 6.6: Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/6-6-consultar-resultados-da-simulacao-e-a-linha-do-tempo/design.md`
**Status**: Approved

---

## Test Coverage Matrix

> Generated from codebase sampling (`src/frontend/package.json` scripts, testes existentes de `SuperficieExecucao`/`App`/`SuperficieResultados`, `.specs/LESSONS.md`) - nenhuma rota de backend nova. Guidelines found: `.specs/LESSONS.md` (L-024: toda distinção por texto+ícone+cor precisa afirmar os três sinais; antes de fechar uma história de UI, confirmar que o componente novo está de fato montado e alcançável a partir de `App.tsx`/navegação real).

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| Frontend — contexto (`PerfilContexto`) | unit | Novo `tipo` de detalhe válido/inválido por perfil (mesmo padrão de `evento-execucao`) | `src/frontend/src/contexto/PerfilContexto.test.tsx` | `npm run test --prefix src/frontend -- run PerfilContexto` |
| Frontend — composição (`SuperficieExecucao`) | unit | Rótulo de encerramento e botão "Ver resultado" só em `concluida`; navegação funcional | `src/frontend/src/funcionalidades/execucao/SuperficieExecucao.test.tsx` | `npm run test --prefix src/frontend -- run SuperficieExecucao` |
| Frontend — composição (`App`) | unit | Novo `case 'resultado-execucao'` monta `SuperficieResultados`; `case 'comunicacoes'` monta `SuperficieLinhaDoTempo` | `src/frontend/src/App.test.tsx` | `npm run test --prefix src/frontend -- run App.test` |
| Frontend — componente (`SuperficieResultados`) | unit | Estatísticas derivadas corretas (soma bate com `totaisPorEstado`); filtro por canal/estado nunca excede o total; clique abre o drawer com `mensagemId` correto; export CSV reflete só os itens filtrados | `src/frontend/src/funcionalidades/resultados/SuperficieResultados.test.tsx` | `npm run test --prefix src/frontend -- run SuperficieResultados` |

## Gate Check Commands

> Generated from codebase - confirm before Execute.

| Gate Level | When to Use | Command |
| --- | --- | --- |
| Quick | Após cada task individual | `npm run test --prefix src/frontend -- run <arquivo>` |
| Full | Fim da fase | `npm run test --prefix src/frontend && npm run lint --prefix src/frontend && npm run build --prefix src/frontend` |
| Build | Antes do Verifier | Frontend: `npm run test --prefix src/frontend && npm run lint --prefix src/frontend && npm run build --prefix src/frontend` (backend não tocado nesta história) |

---

## Execution Plan

### Phase 1: Navegação — novo destino de detalhe + slot "Comunicações"

```
T1 → T2 → T3
```

### Phase 2: `SuperficieResultados` — resumo, filtro, drill-down, exportação

```
T4 → T5 → T6 → T7
```

T4 depende de T3 (fase anterior).

---

## Task Breakdown

### T1: Estender `SuperficieDetalhe` com o tipo `resultado-execucao`

**What**: Em `PerfilContexto.tsx`, transformar `SuperficieDetalhe` de objeto único em union discriminado, adicionando `{ tipo: 'resultado-execucao'; execucaoId: string; perfilPai: 'administrador' }` ao lado de `evento-execucao`.
**Where**: `src/frontend/src/contexto/PerfilContexto.tsx`
**Depends on**: None
**Reuses**: `superficieValida`/`selecionarSuperficie` já genéricos (checam `'perfilPai' in superficieAtiva`), nenhuma mudança de lógica
**Requirement**: PAINELRES-01 (fundação de navegação)

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `SuperficieDetalhe` é um union com os dois tipos
- [ ] `Superficie = SuperficieTopo | SuperficieDetalhe` continua válido sem outras mudanças
- [ ] Teste novo em `PerfilContexto.test.tsx`: `selecionarSuperficie({tipo: 'resultado-execucao', execucaoId, perfilPai: 'administrador'})` resulta em `superficieValida === true` no perfil administrador e `false` no perfil segurado (mesmo padrão do teste existente de `evento-execucao`)
- [ ] Gate check passes: `npm run test --prefix src/frontend -- run PerfilContexto`
- [ ] Nenhum teste existente quebrado (nenhuma outra parte do código faz match exaustivo em `SuperficieDetalhe['tipo']` que precise de um novo `case`)

**Tests**: unit
**Gate**: quick

**Commit**: `feat(navegacao-admin): add resultado-execucao detail surface type`

---

### T2: Botão "Ver resultado consolidado" em `SuperficieExecucao`

**What**: Adicionar `ROTULOS_ENCERRAMENTO.concluida = 'Concluída — resultado disponível'`; quando `execucao.estado === 'concluida'`, renderizar um botão "Ver resultado consolidado" que chama `selecionarSuperficie({ tipo: 'resultado-execucao', execucaoId, perfilPai: 'administrador' })`.
**Where**: `src/frontend/src/funcionalidades/execucao/SuperficieExecucao.tsx`
**Depends on**: T1
**Reuses**: `selecionarSuperficie` (já obtido via `usePerfilContexto` na linha 130)
**Requirement**: PAINELRES-01

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `estado === 'concluida'` mostra o rótulo de encerramento "Concluída — resultado disponível" (não mais o texto bruto `concluida`)
- [ ] `estado === 'concluida'` mostra o botão "Ver resultado consolidado"; clicar navega para `{tipo: 'resultado-execucao', execucaoId, perfilPai: 'administrador'}` (confirmado via `usePerfilContexto` espiã, mesmo padrão já usado nos testes de execuções correlacionadas)
- [ ] Em qualquer outro estado, o botão não aparece
- [ ] Gate check passes: `npm run test --prefix src/frontend -- run SuperficieExecucao`

**Tests**: unit
**Gate**: quick

**Commit**: `feat(execucao-admin): add link to consolidated result when concluida`

---

### T3: Montar `SuperficieResultados`/`SuperficieLinhaDoTempo` em `App.tsx`, remover `EmConstrucao`

**What**: Novo `case 'resultado-execucao'` em `SuperficieAtiva` monta `<SuperficieResultados execucaoId={superficieAtiva.execucaoId} />`; `case 'comunicacoes'` passa a montar `<SuperficieLinhaDoTempo />`; remover a função `EmConstrucao` (fica sem chamadores).
**Where**: `src/frontend/src/App.tsx`
**Depends on**: T2
**Reuses**: `SuperficieResultados`, `SuperficieLinhaDoTempo` sem alteração nesta task
**Requirement**: PAINELRES-01, PAINELRES-06

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Forçar `{tipo: 'resultado-execucao', execucaoId, perfilPai: 'administrador'}` (mesmo padrão do teste existente de `evento-execucao` em `App.test.tsx`) monta `SuperficieResultados` com o `execucaoId` correto
- [ ] Clicar em "Comunicações" na navegação lateral monta `SuperficieLinhaDoTempo` (heading "Linha do tempo" ou título real do componente)
- [ ] `EmConstrucao` não existe mais em `App.tsx` (removida, não só desreferenciada)
- [ ] Gate check passes: `npm run test --prefix src/frontend -- run App.test`

**Tests**: unit
**Gate**: quick

**Commit**: `feat(navegacao-admin): mount SuperficieResultados and SuperficieLinhaDoTempo, drop EmConstrucao`

---

### T4: Seção de estatísticas derivadas em `SuperficieResultados`

**What**: Adicionar funções puras `totalProcessado`, `totalEntregue`, `totalComFalha` (derivadas de `resultados.totaisPorEstado`) e uma seção "Resumo" exibindo os três números, antes das tabelas existentes.
**Where**: `src/frontend/src/funcionalidades/resultados/SuperficieResultados.tsx`
**Depends on**: T3
**Reuses**: `resultados.totaisPorEstado: TotalPorChave[]` já existente
**Requirement**: PAINELRES-01

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] "Total processado" = soma de todos os `totaisPorEstado`
- [ ] "Total entregue" = total de `simulada_entregue` (0 se ausente da lista)
- [ ] "Total com falha" = soma de `falhou_conteudo` + `falhou_integracao_ia` (0 se ausentes)
- [ ] Teste confirma: entregue + com falha + demais estados (aprovada/rejeitada/excluida) somam exatamente o processado — mesma verificação do Independent Test da spec (`entregues + falhas == total processado` quando não há outras categorias no fixture de teste)
- [ ] Gate check passes: `npm run test --prefix src/frontend -- run SuperficieResultados`

**Tests**: unit
**Gate**: quick

**Commit**: `feat(resultados): add derived summary stats (processado/entregue/falha)`

---

### T5: Filtro por canal/estado em `TabelaNaoSimulaveis`

**What**: Adicionar dois `<select>` (canal, estado) que filtram `resultados.naoSimulaveis` client-side antes de passar para `TabelaNaoSimulaveis`; opções dos selects derivadas dos valores presentes nos próprios itens (sem lista fixa).
**Where**: `src/frontend/src/funcionalidades/resultados/SuperficieResultados.tsx`
**Depends on**: T4
**Reuses**: `TabelaNaoSimulaveis` já existente, só recebe uma lista pré-filtrada
**Requirement**: PAINELRES-02, PAINELRES-03

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Selecionar um canal mostra só os itens daquele canal
- [ ] Selecionar um estado mostra só os itens daquele estado
- [ ] Combinar os dois filtros aplica ambos (interseção)
- [ ] A quantidade de linhas exibidas após qualquer filtro nunca excede `resultados.naoSimulaveis.length`
- [ ] Limpar o filtro (voltar para "Todos") mostra a lista completa de novo
- [ ] Gate check passes: `npm run test --prefix src/frontend -- run SuperficieResultados`

**Tests**: unit
**Gate**: quick

**Commit**: `feat(resultados): add canal/estado filters to non-simulated messages table`

---

### T6: Drill-down para `SuperficieDetalheResultado`

**What**: Adicionar estado local `mensagemAberta: string | null`; cada linha de `TabelaNaoSimulaveis` ganha um botão "Ver detalhe" que define `mensagemAberta`; montar `<SuperficieDetalheResultado aberto={mensagemAberta !== null} execucaoId={execucaoId} mensagemId={mensagemAberta ?? ''} onFechar={() => definirMensagemAberta(null)} />`.
**Where**: `src/frontend/src/funcionalidades/resultados/SuperficieResultados.tsx`
**Depends on**: T5
**Reuses**: `SuperficieDetalheResultado` sem alteração
**Requirement**: PAINELRES-04, PAINELRES-05

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Clicar em "Ver detalhe" de uma linha abre o drawer com o `mensagemId` correto daquela linha
- [ ] Fechar o drawer (`onFechar`) limpa `mensagemAberta`
- [ ] Abrir o detalhe de um item com falha simulada mostra o motivo exatamente como persistido (comportamento já garantido pelo componente reusado, confirmado por teste de composição, não reimplementado)
- [ ] Gate check passes: `npm run test --prefix src/frontend -- run SuperficieResultados`

**Tests**: unit
**Gate**: quick

**Commit**: `feat(resultados): wire drill-down into SuperficieDetalheResultado`

---

### T7: Exportação CSV do que está filtrado

**What**: Botão "Exportar CSV" que gera um arquivo CSV client-side (via `Blob`/`URL.createObjectURL`) a partir dos itens de `naoSimulaveis` **após os filtros ativos** de T5 (canal, estado, motivo).
**Where**: `src/frontend/src/funcionalidades/resultados/SuperficieResultados.tsx`
**Depends on**: T6
**Reuses**: mesma lista filtrada de T5
**Requirement**: PAINELRES-07

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Aplicar um filtro por estado, exportar, e confirmar que o conteúdo do Blob gerado contém só os itens daquele estado (teste inspeciona o conteúdo passado a `Blob`/o `href` do link de download, sem precisar de download real no ambiente de teste)
- [ ] Sem filtro ativo, exporta todos os itens de `naoSimulaveis`
- [ ] Gate check passes: `npm run test --prefix src/frontend -- run SuperficieResultados`
- [ ] Full gate ao final: `npm run test --prefix src/frontend && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`
- [ ] Atualizar a tabela de rastreabilidade de `spec.md`: todos os PAINELRES-NN → Verified (status final "Verified" só após o Verifier independente da história inteira)

**Tests**: unit
**Gate**: full

**Commit**: `feat(resultados): add CSV export of the currently filtered table`

---

## Phase Execution Map

```
Phase 1 → Phase 2

Phase 1:  T1 ------→ T2 ------→ T3
Phase 2:  T4 ------→ T5 ------→ T6 ------→ T7

T3 → T4
```

A última linha é a aresta entre fases que não fica adjacente no traçado principal: `T3 → T4` (T4 só pode adicionar a seção de resumo em `SuperficieResultados` depois que T3 a montar de fato em `App.tsx` e a história de navegação estiver fechada).

---

## Task Granularity Check

| Task | Scope | Status |
| --- | --- | --- |
| T1: Estender `SuperficieDetalhe` | 1 arquivo, 1 tipo | ✅ Granular |
| T2: Botão "Ver resultado" em `SuperficieExecucao` | 1 arquivo, 1 rótulo + 1 condicional | ✅ Granular |
| T3: Montar 2 superfícies em `App.tsx`, remover `EmConstrucao` | 1 arquivo, 2 `case`s + 1 remoção coesa | ✅ Granular |
| T4: Seção de resumo em `SuperficieResultados` | 1 arquivo, 3 funções puras + 1 seção | ✅ Granular |
| T5: Filtro canal/estado | 1 arquivo, 2 selects + 1 função de filtro | ✅ Granular |
| T6: Drill-down para detalhe | 1 arquivo, 1 estado local + 1 embed | ✅ Granular |
| T7: Exportação CSV | 1 arquivo, 1 botão + 1 função de geração | ✅ Granular |

---

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| --- | --- | --- | --- |
| T1 | None | (início da Fase 1) | ✅ Match |
| T2 | T1 | T1 → T2 | ✅ Match |
| T3 | T1 | T2 → T3 (sequencial), dependência declarada é T1 | ✅ Match |
| T4 | T3 | T3 → T4 (aresta extra) | ✅ Match |
| T5 | T4 | T4 → T5 | ✅ Match |
| T6 | T5 | T5 → T6 | ✅ Match |
| T7 | T6 | T6 → T7 | ✅ Match |

Nenhuma dependência aponta para uma fase posterior.

---

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| --- | --- | --- | --- | --- |
| T1 | Frontend — contexto (`PerfilContexto`) | unit | unit | ✅ OK |
| T2 | Frontend — composição (`SuperficieExecucao`) | unit | unit | ✅ OK |
| T3 | Frontend — composição (`App`) | unit | unit | ✅ OK |
| T4 | Frontend — componente (`SuperficieResultados`) | unit | unit | ✅ OK |
| T5 | Frontend — componente (`SuperficieResultados`) | unit | unit | ✅ OK |
| T6 | Frontend — componente (`SuperficieResultados`) | unit | unit | ✅ OK |
| T7 | Frontend — componente (`SuperficieResultados`) | unit | unit | ✅ OK |

Nenhuma violação.
