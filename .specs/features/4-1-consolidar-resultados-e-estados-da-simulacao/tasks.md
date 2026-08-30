# História 4.1: Consolidar resultados e estados da simulação — Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/4-1-consolidar-resultados-e-estados-da-simulacao/design.md`
**Status**: Approved

---

## Test Coverage Matrix

> Guidelines: `AGENTS.md`, `README.md`; piso em `testes/test_repositorio_elegibilidade.py` (2.5, agregação/contagem) e `testes/test_prontidao_api.py` (acessibilidade de nomes de campo).

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| Extensão de `RepositorioMensagens.listar_por_execucao` | integration | Retorna estado e canal de cada mensagem da execução | `testes/test_repositorio_mensagens.py` (estendido) | `uv run --directory src/backend pytest` |
| `ServicoConsolidacaoResultados` | unit | Todos os branches; 1:1 com `RESULT-01..07,09`; divergência detectada | `testes/test_consolidacao_resultados.py` | `uv run --directory src/backend pytest` |
| Roteador HTTP (resultados) | integration | `GET` de totais: caminho feliz + execução não concluída + divergência simulada | `testes/test_resultados_api.py` | `uv run --directory src/backend pytest` |
| Contrato OpenAPI | integration | Sincronia com a rota nova | `testes/test_openapi_sincronizado.py` | `uv run --directory src/backend pytest` |
| Superfície de Resultados | unit | Totais por canal/estado, "Enviada — simulação" por extenso, `totais_divergentes` visível, acessibilidade de tabela | `SuperficieResultados.test.tsx` | `npm test --prefix src/frontend -- --run` |

## Gate Check Commands

| Gate Level | When to Use | Command |
| --- | --- | --- |
| Quick (backend) | Tasks isoladas de aplicação/adaptador | `uv run --directory src/backend pytest` |
| Quick (frontend) | Tasks isoladas de componente | `npm test --prefix src/frontend -- --run` |
| Full (backend) | Tasks de roteador HTTP | `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright` |
| Full (frontend) | Tasks de superfície visível | `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend` |
| Build (fim de fase) | Fim de fase / contrato | Backend + Frontend em paralelo, mesmos comandos acima |

---

## Execution Plan

### Phase 1: Consulta e agregação

```
T1 → T2
```

### Phase 2: API e frontend

```
T3 → T4
```

---

## Task Breakdown

### T1: `RepositorioMensagens.listar_por_execucao`

**What**: Retorna todas as mensagens de uma execução com estado atual e canal (extensão, se ainda não coberto exatamente assim por 3.2/4.1).
**Where**: `src/backend/central_preventiva/adaptadores/persistencia/repositorio_mensagens.py` (extensão de 3.2)
**Depends on**: None
**Reuses**: mesma tabela `mensagens`
**Requirement**: RESULT-02, RESULT-03

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Retorna todas as mensagens da execução informada, com `estado` e `canal`
- [ ] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: integration
**Gate**: quick

---

### T2: `ServicoConsolidacaoResultados`

**What**: Agrega totais por canal/estado, separa não-simuláveis, detecta divergência entre `mensagens.simulada_entregue` e `entregas_simuladas`.
**Where**: `src/backend/central_preventiva/aplicacao/consolidacao_resultados.py`
**Depends on**: T1
**Reuses**: `RepositorioEntregasSimuladas.listar_por_execucao` (3.6)
**Requirement**: RESULT-01, RESULT-02, RESULT-03, RESULT-04, RESULT-05, RESULT-06, RESULT-07, RESULT-09

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Lote com 3 simuladas + 1 rejeitada + 1 em exceção retorna totais corretos, com as 2 últimas em `nao_simulaveis`, não somadas às entregas simuladas
- [ ] Execução em `falhou_simulacao` retorna zero entregas simuladas, mensagens listadas como `aprovada`, nenhum texto de falha de canal
- [ ] Chamar `consolidar` duas vezes seguidas para a mesma execução retorna resultado idêntico, sem efeito colateral
- [ ] Divergência forçada (dado de teste com contagens diferentes) retorna `divergencia` preenchida com correlação, sem "corrigir" o total
- [ ] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: unit
**Gate**: quick

---

### T3: Endpoint HTTP de resultados

**What**: `GET /api/v1/execucoes/{id}/resultados` retornando `ResultadoConsolidado`.
**Where**: `src/backend/central_preventiva/adaptadores/http/resultados.py`
**Depends on**: T2
**Reuses**: padrão de roteador existente
**Requirement**: RESULT-02, RESULT-09

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] `200` com totais para execução concluída
- [ ] Execução em `simulando` retorna progresso, não totais finais
- [ ] `openapi.json` regenerado, `test_openapi_sincronizado.py` verde
- [ ] Gate check passa: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright`

**Tests**: integration
**Gate**: full

---

### T4: Superfície de Resultados

**What**: Tabela de resultados por canal/estado, com "Enviada — simulação" por extenso (texto+ícone+cor), estado `totais_divergentes` visível quando aplicável, nomes acessíveis em cabeçalhos/ordenação/ações.
**Where**: `src/frontend/src/funcionalidades/resultados/SuperficieResultados.tsx`
**Depends on**: T3
**Reuses**: cliente HTTP central, padrão de tabela acessível de `SuperficieRegras` (2.4)
**Requirement**: RESULT-08, RESULT-09, RESULT-10

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Totais por canal e por estado exibidos, com "Enviada — simulação" por extenso
- [ ] Tabela navegável por teclado, cabeçalhos/ordenação/ações com nomes acessíveis
- [ ] `totais_divergentes` exibido com correlação/impacto quando presente na resposta
- [ ] `npm run gerar-tipos-api --prefix src/frontend` executado; tipos atualizados
- [ ] Gate check passa: `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`

**Tests**: unit
**Gate**: full

**Commit**: `feat(resultados): adicionar consolidacao e reconciliacao de totais da simulacao`

---

## Phase Execution Map

```
Phase 1:  T1 → T2
Phase 2:  T3 → T4
```

Grafo completo de dependências:

```
T1 → T2
T2 → T3
T3 → T4
```

---

## Task Granularity Check

| Task | Scope | Status |
| --- | --- | --- |
| T1: `listar_por_execucao` | 1 método, mesmo arquivo | ✅ Granular |
| T2: `ServicoConsolidacaoResultados` | 1 caso de uso | ✅ Granular |
| T3: Endpoint de resultados | 1 componente | ✅ Granular |
| T4: Superfície de Resultados | 1 componente | ✅ Granular |

---

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| --- | --- | --- | --- |
| T1 | None | — | ✅ Match |
| T2 | T1 | T1 → T2 | ✅ Match |
| T3 | T2 | T2 → T3 | ✅ Match |
| T4 | T3 | T3 → T4 | ✅ Match |

**Rules confirmed**: toda dependência aponta para trás ou dentro da mesma fase.

---

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| --- | --- | --- | --- | --- |
| T1: `listar_por_execucao` | Repositório | integration | integration | ✅ OK |
| T2: `ServicoConsolidacaoResultados` | Aplicação | unit | unit | ✅ OK |
| T3: Endpoint de resultados | Roteador HTTP | integration | integration | ✅ OK |
| T4: Superfície de Resultados | Componente React | unit | unit | ✅ OK |

**Rules confirmed**: nenhum `Tests: none` nesta história; nenhuma task adia teste.
