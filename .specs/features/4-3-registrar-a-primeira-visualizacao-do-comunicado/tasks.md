# História 4.3: Registrar a primeira visualização do comunicado — Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/4-3-registrar-a-primeira-visualizacao-do-comunicado/design.md`
**Status**: Approved

---

## Test Coverage Matrix

> Guidelines: `AGENTS.md`, `README.md`; piso em `testes/test_repositorio_eventos_meteorologicos.py`-style dedução por `UNIQUE` (2.2) e `testes/test_contexto_api.py` (Épico 1, consulta de segurado padrão).

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| Migração `0013_visualizacoes_comunicado.sql` | integration | Aplicação, tabela nova, `UNIQUE` | `testes/test_migracoes.py` | `uv run --directory src/backend pytest` |
| `RepositorioVisualizacoesComunicado` | integration | Primeira gravação, gravação concorrente/repetida convergindo para a mesma linha | `testes/test_repositorio_visualizacoes_comunicado.py` | `uv run --directory src/backend pytest` |
| `ServicoVisualizacaoComunicado` | unit | Todos os branches; 1:1 com `VISU-01..07`; não-enumeração cross-segurado | `testes/test_visualizacao_comunicado.py` | `uv run --directory src/backend pytest` |
| Roteador HTTP (comunicado e visualização) | integration | `GET` comunicado + `POST` visualização: caminho feliz + concorrência + não elegível + isolamento por segurado | `testes/test_visualizacao_comunicado_api.py` | `uv run --directory src/backend pytest` |
| Contrato OpenAPI | integration | Sincronia com as rotas novas | `testes/test_openapi_sincronizado.py` | `uv run --directory src/backend pytest` |
| Superfície do comunicado (perfil Segurado) | unit | Conteúdo/canal/natureza simulada exibidos, sem ação administrativa; erro local nunca antecipa "Visualizada no portal" | `SuperficieComunicado.test.tsx` | `npm test --prefix src/frontend -- --run` |

## Gate Check Commands

| Gate Level | When to Use | Command |
| --- | --- | --- |
| Quick (backend) | Tasks isoladas de aplicação/adaptador | `uv run --directory src/backend pytest` |
| Quick (frontend) | Tasks isoladas de componente | `npm test --prefix src/frontend -- --run` |
| Full (backend) | Tasks de roteador HTTP ou schema | `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright` |
| Full (frontend) | Tasks de superfície visível | `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend` |
| Build (fim de fase) | Fim de fase / contrato | Backend + Frontend em paralelo, mesmos comandos acima |

---

## Execution Plan

### Phase 1: Schema e persistência da visualização

```
T1 → T2
```

### Phase 2: Caso de uso

```
T3
```

### Phase 3: API e frontend

```
T4 → T5
```

---

## Task Breakdown

### T1: Migração `0013_visualizacoes_comunicado.sql`

**What**: Criar `visualizacoes_comunicado` (`UNIQUE(entrega_simulada_id)`); atualizar `README.md` de persistência.
**Where**: `src/backend/central_preventiva/adaptadores/persistencia/migracoes/0013_visualizacoes_comunicado.sql`
**Depends on**: None
**Reuses**: convenção de migração numerada
**Requirement**: VISU-01

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Migração aplica em transação própria, registrada em `schema_migracoes`
- [ ] `README.md` documenta a tabela nova e a `UNIQUE`
- [ ] `testes/test_migracoes.py` cobre a aplicação da migração `0013`
- [ ] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: integration
**Gate**: quick

---

### T2: `RepositorioVisualizacoesComunicado`

**What**: `registrar_primeira_visualizacao` (`INSERT ... ON CONFLICT DO NOTHING` + `SELECT` na mesma transação), `obter_por_entrega`.
**Where**: `src/backend/central_preventiva/adaptadores/persistencia/repositorio_visualizacoes_comunicado.py`
**Depends on**: T1
**Reuses**: padrão de dedução por `UNIQUE` de 2.2/2.5
**Requirement**: VISU-01, VISU-02, VISU-03

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Primeira chamada cria a linha e devolve sua `visualizada_em`
- [ ] Segunda chamada para a mesma `entrega_simulada_id` devolve a mesma `visualizada_em`, sem criar segunda linha
- [ ] Chamadas concorrentes simuladas (duas transações abertas antes de qualquer commit) convergem para uma única linha persistida
- [ ] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: integration
**Gate**: quick

---

### T3: `ServicoVisualizacaoComunicado`

**What**: `obter_comunicado` (com verificação de pertencimento ao `segurado_id`, não-enumeração) e `registrar_visualizacao` (valida `estado = simulada_entregue` antes de gravar).
**Where**: `src/backend/central_preventiva/aplicacao/visualizacao_comunicado.py`
**Depends on**: T2
**Reuses**: `RepositorioMensagens` (3.2), `RepositorioEntregasSimuladas` (3.6), `consultar_segurado_padrao` (Épico 1)
**Requirement**: VISU-01, VISU-04, VISU-05

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Mensagem em `simulada_entregue`: `registrar_visualizacao` grava com sucesso
- [ ] Mensagem em `falhou_conteudo`/`rejeitada`/`excluida`/ainda em `gerando`: levanta `MensagemNaoElegivelParaComunicado`, sem gravar
- [ ] `obter_comunicado` com `entrega_simulada_id` de outro segurado retorna `None` (mesmo resultado de inexistente)
- [ ] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: unit
**Gate**: quick

---

### T4: Roteador HTTP — comunicado e visualização

**What**: `GET /api/v1/segurados/{segurado_id}/comunicados/{entrega_simulada_id}` e `POST /api/v1/segurados/{segurado_id}/comunicados/{entrega_simulada_id}/visualizacao`.
**Where**: `src/backend/central_preventiva/adaptadores/http/visualizacao_comunicado.py`
**Depends on**: T3
**Reuses**: padrão de roteador existente
**Requirement**: VISU-04, VISU-05

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] `GET`/`POST` de mensagem não elegível retorna erro de domínio explícito, `application/problem+json`
- [ ] `GET`/`POST` de `entrega_simulada_id` de outro segurado retorna `404` genérico
- [ ] `openapi.json` regenerado, `test_openapi_sincronizado.py` verde
- [ ] Gate check passa: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright`

**Tests**: integration
**Gate**: full

---

### T5: Superfície do comunicado (perfil Segurado)

**What**: Componente que renderiza o comunicado (conteúdo, canal, natureza simulada, linha do tempo disponível), dispara `POST` de visualização só após render bem-sucedido, sem nenhuma ação administrativa; erro local preserva estado consultável sem antecipar "Visualizada no portal".
**Where**: `src/frontend/src/funcionalidades/segurado/SuperficieComunicado.tsx`
**Depends on**: T4
**Reuses**: cliente HTTP central, padrão de `VisaoGeralSegurado.tsx` (Épico 1)
**Requirement**: VISU-01, VISU-02, VISU-05, VISU-06, VISU-07

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] `POST` de visualização disparado só após o conteúdo renderizar com sucesso, não no `GET` inicial
- [ ] Nenhum elemento de ação administrativa presente na tela
- [ ] Falha local simulada mantém estado de erro visível, sem mostrar "Visualizada no portal"
- [ ] `npm run gerar-tipos-api --prefix src/frontend` executado; tipos atualizados
- [ ] Gate check passa: `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`

**Tests**: unit
**Gate**: full

**Commit**: `feat(comunicado): adicionar visualizacao do comunicado pelo segurado com marco unico`

---

## Phase Execution Map

```
Phase 1:  T1 → T2
Phase 2:  T3
Phase 3:  T4 → T5
```

Grafo completo de dependências:

```
T1 → T2
T2 → T3
T3 → T4
T4 → T5
```

---

## Task Granularity Check

| Task | Scope | Status |
| --- | --- | --- |
| T1: Migração `0013` | 1 arquivo `.sql` + doc | ✅ Granular |
| T2: `RepositorioVisualizacoesComunicado` | 1 componente | ✅ Granular |
| T3: `ServicoVisualizacaoComunicado` | 1 caso de uso | ✅ Granular |
| T4: Roteador de comunicado | 1 componente | ✅ Granular |
| T5: Superfície do comunicado | 1 componente | ✅ Granular |

---

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| --- | --- | --- | --- |
| T1 | None | — | ✅ Match |
| T2 | T1 | T1 → T2 | ✅ Match |
| T3 | T2 | T2 → T3 | ✅ Match |
| T4 | T3 | T3 → T4 | ✅ Match |
| T5 | T4 | T4 → T5 | ✅ Match |

**Rules confirmed**: toda dependência aponta para trás ou dentro da mesma fase.

---

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| --- | --- | --- | --- | --- |
| T1: Migração `0013` | Migração/schema | integration | integration | ✅ OK |
| T2: `RepositorioVisualizacoesComunicado` | Repositório | integration | integration | ✅ OK |
| T3: `ServicoVisualizacaoComunicado` | Aplicação | unit | unit | ✅ OK |
| T4: Roteador de comunicado | Roteador HTTP | integration | integration | ✅ OK |
| T5: Superfície do comunicado | Componente React | unit | unit | ✅ OK |

**Rules confirmed**: nenhum `Tests: none` nesta história; nenhuma task adia teste.
