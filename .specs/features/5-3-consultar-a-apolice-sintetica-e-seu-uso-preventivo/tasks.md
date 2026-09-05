# História 5.3: Consultar a apólice sintética e seu uso preventivo — Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/5-3-consultar-a-apolice-sintetica-e-seu-uso-preventivo/design.md`
**Status**: Approved

---

## Test Coverage Matrix

> Guidelines: `AGENTS.md`, `README.md`; piso em `testes/test_repositorio_segurados.py` (Épico 1, mesmo padrão de repositório).

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| `RepositorioApolices` | integration | Buscar por segurado, buscar por id, ausência | `testes/test_repositorio_apolices.py` | `uv run --directory src/backend pytest` |
| `ServicoApoliceSegurado` | unit | Todos os branches; 1:1 com `APOLICE-01..06` | `testes/test_apolice_segurado.py` | `uv run --directory src/backend pytest` |
| Roteador HTTP (apólice e explicação) | integration | Caminho feliz + inativa/sem cobertura + outro segurado + histórico divergente | `testes/test_apolice_segurado_api.py` | `uv run --directory src/backend pytest` |
| Contrato OpenAPI | integration | Sincronia com as rotas novas | `testes/test_openapi_sincronizado.py` | `uv run --directory src/backend pytest` |
| Superfície de Apólice | unit | Campos do AC, estado objetivo sem erro técnico, ausência de promessa de cobertura, aviso de efeito futuro | `SuperficieApolice.test.tsx` | `npm test --prefix src/frontend -- --run` |

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

### Phase 1: Persistência e consulta

```
T1 → T2
```

### Phase 2: API e frontend

```
T3 → T4
```

---

## Task Breakdown

### T1: `RepositorioApolices`

**What**: `buscar_por_segurado`, `buscar_por_id`.
**Where**: `src/backend/central_preventiva/adaptadores/persistencia/repositorio_apolices.py`
**Depends on**: None
**Reuses**: padrão de `repositorio_segurados.py`
**Requirement**: APOLICE-01

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] `buscar_por_segurado` retorna a apólice do segurado quando existir
- [x] `buscar_por_id` retorna `None` para id inexistente
- [x] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: integration
**Gate**: quick

---

### T2: `ServicoApoliceSegurado`

**What**: `obter` (dados cadastrais + estado objetivo) e `obter_explicacao` (critérios do snapshot de 2.5, filtrados).
**Where**: `src/backend/central_preventiva/aplicacao/apolice_segurado.py`
**Depends on**: T1
**Reuses**: `RepositorioElegibilidades` (2.5)
**Requirement**: APOLICE-01, APOLICE-02, APOLICE-03, APOLICE-04, APOLICE-05, APOLICE-06

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Apólice ativa retorna todos os campos do AC
- [ ] Apólice `cancelada`/`suspensa`/expirada retorna estado objetivo textual, sem exceção técnica
- [ ] `obter`/`obter_explicacao` de outro segurado retornam `None`
- [ ] `obter_explicacao` nunca contém frase de cobertura/indenização/sinistro (testado por ausência de palavras-chave proibidas na lista de motivos)
- [ ] Alterar a apólice atual (dado de teste) não muda a explicação de uma execução histórica já concluída
- [ ] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: unit
**Gate**: quick

---

### T3: Endpoints HTTP — apólice e explicação

**What**: `GET /api/v1/segurados/{segurado_id}/apolice` e `GET /api/v1/segurados/{segurado_id}/apolice/explicacao/{elegibilidade_id}`.
**Where**: `src/backend/central_preventiva/adaptadores/http/apolice_segurado.py`
**Depends on**: T2
**Reuses**: padrão de roteador existente
**Requirement**: APOLICE-04

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] `200` com os dados da apólice/explicação quando pertencer ao segurado
- [ ] `404` genérico para apólice/explicação de outro segurado
- [ ] `openapi.json` regenerado, `test_openapi_sincronizado.py` verde
- [ ] Gate check passa: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright`

**Tests**: integration
**Gate**: full

---

### T4: Superfície de Apólice

**What**: Exibe número, situação, vigência, endereço sintético, coberturas relevantes, canal preferencial, participação em alertas; explicação de critério sem promessa de cobertura; estado objetivo para inativa/sem cobertura; aviso de "afeta só o futuro" ao lado dos dados editáveis.
**Where**: `src/frontend/src/funcionalidades/segurado/SuperficieApolice.tsx`
**Depends on**: T3
**Reuses**: cliente HTTP central, padrão visual de `VisaoGeralSegurado.tsx` (5.1)
**Requirement**: APOLICE-01, APOLICE-02, APOLICE-03, APOLICE-05, APOLICE-06

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Todos os campos do AC exibidos, obtidos da API real
- [ ] Estado inativo/sem cobertura exibido como texto explicativo, nunca como tela de erro
- [ ] `npm run gerar-tipos-api --prefix src/frontend` executado; tipos atualizados
- [ ] Gate check passa: `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`

**Tests**: unit
**Gate**: full

**Commit**: `feat(segurado): adicionar consulta de apolice e explicacao do uso preventivo`

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
| T1: `RepositorioApolices` | 1 componente | ✅ Granular |
| T2: `ServicoApoliceSegurado` | 1 caso de uso | ✅ Granular |
| T3: Endpoints de apólice | 1 componente | ✅ Granular |
| T4: Superfície de Apólice | 1 componente | ✅ Granular |

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
| T1: `RepositorioApolices` | Repositório | integration | integration | ✅ OK |
| T2: `ServicoApoliceSegurado` | Aplicação | unit | unit | ✅ OK |
| T3: Endpoints de apólice | Roteador HTTP | integration | integration | ✅ OK |
| T4: Superfície de Apólice | Componente React | unit | unit | ✅ OK |

**Rules confirmed**: nenhum `Tests: none` nesta história; nenhuma task adia teste.
