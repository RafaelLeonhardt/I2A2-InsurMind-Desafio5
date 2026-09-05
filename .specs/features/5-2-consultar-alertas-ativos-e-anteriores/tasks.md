# História 5.2: Consultar alertas ativos e anteriores — Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/5-2-consultar-alertas-ativos-e-anteriores/design.md`
**Status**: Approved

---

## Test Coverage Matrix

> Guidelines: `AGENTS.md`, `README.md`; piso em `testes/test_alerta_segurado.py` (5.1) e `testes/test_detalhe_resultado.py` (4.2, não-enumeração).

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| Extensão de `RepositorioElegibilidades.listar_todas_por_segurado` | integration | Lista todas as `incluido`, ordenadas | `testes/test_repositorio_elegibilidade.py` (estendido) | `uv run --directory src/backend pytest` |
| `ServicoListaAlertasSegurado` | unit | Todos os branches; 1:1 com `ALERTAS-01..06` | `testes/test_lista_alertas_segurado.py` | `uv run --directory src/backend pytest` |
| Roteador HTTP (lista e detalhe de alertas) | integration | Caminho feliz + vazio + inexistente/outro segurado + ainda não simulado | `testes/test_lista_alertas_segurado_api.py` | `uv run --directory src/backend pytest` |
| Contrato OpenAPI | integration | Sincronia com as rotas novas | `testes/test_openapi_sincronizado.py` | `uv run --directory src/backend pytest` |
| Superfície de Alertas (lista + detalhe) | unit | Rótulo ativo/anterior, mapa+lista equivalentes, foco na seleção, `Não encontrado`, `Ainda não simulado` | `SuperficieAlertas.test.tsx` | `npm test --prefix src/frontend -- --run` |

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

### Phase 1: Consulta agregada

```
T1 → T2
```

### Phase 2: API e frontend

```
T3 → T4
```

---

## Task Breakdown

### T1: Extensão de `RepositorioElegibilidades.listar_todas_por_segurado`

**What**: Lista todas as elegibilidades `incluido` de um segurado, ordenadas por `criado_em` decrescente.
**Where**: `src/backend/central_preventiva/adaptadores/persistencia/repositorio_elegibilidade.py` (extensão de 2.5/5.1)
**Depends on**: None
**Reuses**: mesma tabela `elegibilidades_historicas`
**Requirement**: ALERTAS-01

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] Retorna todas as elegibilidades `incluido` do segurado, ordenadas
- [x] Retorna lista vazia quando não houver nenhuma
- [x] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: integration
**Gate**: quick

---

### T2: `ServicoListaAlertasSegurado`

**What**: `listar` (classifica ativo/anterior/ainda-não-simulado) e `obter_detalhe` (com não-enumeração e linha do tempo).
**Where**: `src/backend/central_preventiva/aplicacao/lista_alertas_segurado.py`
**Depends on**: T1
**Reuses**: `AlertaSegurado` (5.1), `RepositorioExecucaoPreventiva` (2.2), `ServicoLinhaDoTempo` (4.4)
**Requirement**: ALERTAS-01, ALERTAS-02, ALERTAS-03, ALERTAS-05, ALERTAS-06

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Alerta com execução ainda não terminal de simulação classifica como "ainda não simulado"
- [ ] Alerta com execução concluída dentro do período do evento classifica como "ativo"; fora, como "anterior"
- [ ] `obter_detalhe` de `elegibilidade_id` de outro segurado retorna `None`, mesmo resultado de inexistente
- [ ] `obter_detalhe` de alerta válido retorna origem, período, localização, impactos, recomendações, contexto da apólice, linha do tempo
- [ ] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: unit
**Gate**: quick

---

### T3: Endpoints HTTP — lista e detalhe de alertas

**What**: `GET /api/v1/segurados/{segurado_id}/alertas` e `GET /api/v1/segurados/{segurado_id}/alertas/{elegibilidade_id}`.
**Where**: `src/backend/central_preventiva/adaptadores/http/lista_alertas_segurado.py`
**Depends on**: T2
**Reuses**: padrão de roteador existente
**Requirement**: ALERTAS-05

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] `GET` da lista retorna `200` com todos os alertas classificados
- [ ] `GET` do detalhe de outro segurado retorna `404` genérico idêntico ao de inexistente
- [ ] `openapi.json` regenerado, `test_openapi_sincronizado.py` verde
- [ ] Gate check passa: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright`

**Tests**: integration
**Gate**: full

---

### T4: Superfície de Alertas (lista + detalhe)

**What**: Lista com rótulo ativo/anterior por ícone+texto; detalhe com mapa (pinos com ícone+legenda) e lista equivalente por teclado/leitor de tela; seleção anunciada sem mover foco inesperadamente; `Não encontrado` e `Ainda não simulado` explícitos.
**Where**: `src/frontend/src/funcionalidades/segurado/SuperficieAlertas.tsx`
**Depends on**: T3
**Reuses**: cliente HTTP central, componente de mapa+lista de Fonte meteorológica (2.1)
**Requirement**: ALERTAS-01, ALERTAS-02, ALERTAS-03, ALERTAS-04, ALERTAS-05, ALERTAS-06

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Ativos e anteriores distinguíveis por rótulo+ícone+texto, não só cor
- [ ] Seleção de pino no mapa e na lista equivalente produzem o mesmo resultado
- [ ] Estado vazio explicativo mantém navegação para as demais superfícies
- [ ] `npm run gerar-tipos-api --prefix src/frontend` executado; tipos atualizados
- [ ] Gate check passa: `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`

**Tests**: unit
**Gate**: full

**Commit**: `feat(segurado): adicionar lista e detalhe de alertas ativos e anteriores`

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
| T1: `listar_todas_por_segurado` | 1 método, mesmo arquivo | ✅ Granular |
| T2: `ServicoListaAlertasSegurado` | 1 caso de uso | ✅ Granular |
| T3: Endpoints de alertas | 1 componente | ✅ Granular |
| T4: Superfície de Alertas | 1 componente | ✅ Granular |

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
| T1: `listar_todas_por_segurado` | Repositório | integration | integration | ✅ OK |
| T2: `ServicoListaAlertasSegurado` | Aplicação | unit | unit | ✅ OK |
| T3: Endpoints de alertas | Roteador HTTP | integration | integration | ✅ OK |
| T4: Superfície de Alertas | Componente React | unit | unit | ✅ OK |

**Rules confirmed**: nenhum `Tests: none` nesta história; nenhuma task adia teste.
