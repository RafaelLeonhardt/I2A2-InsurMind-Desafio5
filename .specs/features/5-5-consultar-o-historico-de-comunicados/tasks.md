# História 5.5: Consultar o histórico de comunicados — Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/5-5-consultar-o-historico-de-comunicados/design.md`
**Status**: Approved

---

## Test Coverage Matrix

> Guidelines: `AGENTS.md`, `README.md`; piso em `testes/test_visualizacao_comunicado.py` (4.3, reuso direto).

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| Extensão de `RepositorioEntregasSimuladas.listar_por_segurado` | integration | Isolamento por segurado, assunto/resumo por canal | `testes/test_repositorio_entregas_simuladas.py` (estendido) | `uv run --directory src/backend pytest` |
| `ServicoListaComunicados` | unit | Todos os branches; 1:1 com `COMUNICADOS-01..02` | `testes/test_lista_comunicados.py` | `uv run --directory src/backend pytest` |
| Roteador HTTP (lista de comunicados) | integration | Caminho feliz + vazio + isolamento | `testes/test_lista_comunicados_api.py` | `uv run --directory src/backend pytest` |
| Contrato OpenAPI | integration | Sincronia com a rota nova | `testes/test_openapi_sincronizado.py` | `uv run --directory src/backend pytest` |
| Superfície de Comunicados (lista + reuso do detalhe de 4.3) | unit | Isolamento visual, estado vazio, erro sem conteúdo fixo, navegação por teclado/leitor de tela | `SuperficieComunicados.test.tsx` | `npm test --prefix src/frontend -- --run` |

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

### T1: Extensão de `RepositorioEntregasSimuladas.listar_por_segurado`

**What**: Lista entregas simuladas de um segurado, com assunto (e-mail) ou resumo truncado (WhatsApp/SMS).
**Where**: `src/backend/central_preventiva/adaptadores/persistencia/repositorio_entregas_simuladas.py` (extensão de 3.6)
**Depends on**: None
**Reuses**: mesma tabela `entregas_simuladas`
**Requirement**: COMUNICADOS-01

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] Retorna só entregas do segurado informado
- [x] E-mail retorna `assunto` real; WhatsApp/SMS retornam resumo truncado do corpo
- [x] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: integration
**Gate**: quick

---

### T2: `ServicoListaComunicados`

**What**: Monta a lista com canal, assunto/resumo, data, estado (incluindo `Visualizada no portal` quando aplicável).
**Where**: `src/backend/central_preventiva/aplicacao/lista_comunicados.py`
**Depends on**: T1
**Reuses**: `RepositorioVisualizacoesComunicado` (4.3)
**Requirement**: COMUNICADOS-01, COMUNICADOS-02

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Lista com comunicados visualizados e não visualizados retorna o estado correto de cada um
- [ ] Segurado sem comunicados retorna lista vazia
- [ ] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: unit
**Gate**: quick

---

### T3: Endpoint HTTP de lista de comunicados

**What**: `GET /api/v1/segurados/{segurado_id}/comunicados`.
**Where**: `src/backend/central_preventiva/adaptadores/http/lista_comunicados.py`
**Depends on**: T2
**Reuses**: padrão de roteador existente; endpoints de detalhe/visualização já existentes de 4.3
**Requirement**: COMUNICADOS-01

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] `200` com a lista completa
- [ ] `openapi.json` regenerado, `test_openapi_sincronizado.py` verde
- [ ] Gate check passa: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright`

**Tests**: integration
**Gate**: full

---

### T4: Superfície de Comunicados

**What**: Lista com canal/assunto-resumo/data/estado, seleção anunciada, ações sem hover; ao abrir um item, reusa o detalhe e o registro de visualização já existentes de 4.3; estado vazio e erro honesto.
**Where**: `src/frontend/src/funcionalidades/segurado/SuperficieComunicados.tsx`
**Depends on**: T3
**Reuses**: cliente HTTP central, `SuperficieComunicado.tsx` (4.3) para o detalhe
**Requirement**: COMUNICADOS-01, COMUNICADOS-02, COMUNICADOS-03, COMUNICADOS-04, COMUNICADOS-05, COMUNICADOS-06

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Lista nunca mostra dado de outro segurado (testado com dois segurados)
- [ ] Reabrir um comunicado já visualizado não altera a data exibida
- [ ] Erro de carregamento nunca mostra lista de exemplo
- [ ] `npm run gerar-tipos-api --prefix src/frontend` executado; tipos atualizados
- [ ] Gate check passa: `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`

**Tests**: unit
**Gate**: full

**Commit**: `feat(segurado): adicionar lista do historico de comunicados`

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
| T1: `listar_por_segurado` | 1 método, mesmo arquivo | ✅ Granular |
| T2: `ServicoListaComunicados` | 1 caso de uso | ✅ Granular |
| T3: Endpoint de lista | 1 componente | ✅ Granular |
| T4: Superfície de Comunicados | 1 componente | ✅ Granular |

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
| T1: `listar_por_segurado` | Repositório | integration | integration | ✅ OK |
| T2: `ServicoListaComunicados` | Aplicação | unit | unit | ✅ OK |
| T3: Endpoint de lista | Roteador HTTP | integration | integration | ✅ OK |
| T4: Superfície de Comunicados | Componente React | unit | unit | ✅ OK |

**Rules confirmed**: nenhum `Tests: none` nesta história; nenhuma task adia teste.
