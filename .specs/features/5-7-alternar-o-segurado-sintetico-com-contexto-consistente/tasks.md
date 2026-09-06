# História 5.7: Alternar o segurado sintético com contexto consistente — Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/5-7-alternar-o-segurado-sintetico-com-contexto-consistente/design.md`
**Status**: Approved

---

## Test Coverage Matrix

> Guidelines: `AGENTS.md`, `README.md`; piso em `src/frontend/src/contexto/PerfilContexto.test.tsx` (1.4, mesmo padrão de provider testado).

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| Extensão de `RepositorioSegurados.listar_sinteticos` | integration | Lista todos os segurados do seed | `testes/test_repositorio_segurados.py` (estendido) | `uv run --directory src/backend pytest` |
| Roteador HTTP (lista de segurados sintéticos) | integration | Caminho feliz + seed ausente | `testes/test_lista_segurados_api.py` | `uv run --directory src/backend pytest` |
| Contrato OpenAPI | integration | Sincronia com a rota nova | `testes/test_openapi_sincronizado.py` | `uv run --directory src/backend pytest` |
| `SeguradoContexto` (provider) | unit | Todos os branches; 1:1 com `SELETOR-01..06`; persistência em `localStorage`, reversão em falha, descarte de resposta tardia | `SeguradoContexto.test.tsx` | `npm test --prefix src/frontend -- --run` |
| Extensão das 5 superfícies (5.1–5.6) | unit | Cada uma consome `seguradoAtivoId` corretamente; nenhuma mistura de dado entre segurados | testes já existentes de cada superfície (estendidos) | `npm test --prefix src/frontend -- --run` |
| Seletor "Visualizar como" | unit | Rótulo não-autenticação, teclado, alvo mínimo 44×44px, motivo textual quando desabilitado | `SeletorSegurado.test.tsx` | `npm test --prefix src/frontend -- --run` |

## Gate Check Commands

| Gate Level | When to Use | Command |
| --- | --- | --- |
| Quick (backend) | Tasks isoladas de adaptador | `uv run --directory src/backend pytest` |
| Quick (frontend) | Tasks isoladas de componente | `npm test --prefix src/frontend -- --run` |
| Full (backend) | Tasks de roteador HTTP | `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright` |
| Full (frontend) | Tasks de superfície visível | `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend` |
| Build (fim de fase) | Fim de fase / contrato | Backend + Frontend em paralelo, mesmos comandos acima |

---

## Execution Plan

### Phase 1: Backend — lista de segurados

```
T1 → T2
```

### Phase 2: Contexto e seletor

```
T3 → T4
```

### Phase 3: Integração com as 5 superfícies existentes

```
T5
```

---

## Task Breakdown

### T1: Extensão de `RepositorioSegurados.listar_sinteticos`

**What**: Lista todos os segurados do conjunto sintético semeado.
**Where**: `src/backend/central_preventiva/adaptadores/persistencia/repositorio_segurados.py` (extensão de Épico 1)
**Depends on**: None
**Reuses**: mesma tabela `segurados`
**Requirement**: SELETOR-01

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] Retorna todos os segurados do seed
- [x] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: integration
**Gate**: quick

---

### T2: Endpoint HTTP de segurados sintéticos

**What**: `GET /api/v1/segurados`.
**Where**: `src/backend/central_preventiva/adaptadores/http/lista_segurados.py`
**Depends on**: T1
**Reuses**: padrão de roteador existente
**Requirement**: SELETOR-01

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] `200` com a lista de segurados sintéticos
- [x] `openapi.json` regenerado, `test_openapi_sincronizado.py` verde
- [x] Gate check passa: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright`

**Tests**: integration
**Gate**: full

---

### T3: `SeguradoContexto` (provider React)

**What**: `SeguradoProvider`/`useSeguradoContexto`, mesmo padrão de `PerfilContexto` (1.4): `seguradoAtivoId`, lista disponível, estado `ocioso`/`trocando`/`erro`, persistência em `localStorage`, reversão ao contexto íntegro anterior em falha, descarte de resposta tardia por comparação de `segurado_id`.
**Where**: `src/frontend/src/contexto/SeguradoContexto.tsx`
**Depends on**: T2
**Reuses**: padrão estrutural de `PerfilContexto.tsx` (1.4)
**Requirement**: SELETOR-02, SELETOR-03, SELETOR-04, SELETOR-06

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] Trocar de segurado persiste a escolha em `localStorage` e restaura ao recarregar
- [x] Falha simulada durante a troca reverte ao `seguradoAtivoId` anterior, com causa/impacto/próxima ação expostos
- [x] Resposta tardia de um `segurado_id` que não é mais o ativo é descartada (testado com dublê de temporização)
- [x] Gate check passa: `npm test --prefix src/frontend -- --run`

**Tests**: unit
**Gate**: quick

---

### T4: Seletor "Visualizar como"

**What**: Componente de seleção acessível (teclado, alvo mínimo 44×44px, motivo textual quando desabilitado), rótulo `Visualizar como`, nunca sugerindo autenticação.
**Where**: `src/frontend/src/funcionalidades/segurado/SeletorSegurado.tsx`
**Depends on**: T3
**Reuses**: `SeguradoContexto` (T3)
**Requirement**: SELETOR-01, SELETOR-07, SELETOR-08

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] Rótulo e texto nunca mencionam "login"/"senha"/"entrar"
- [x] Navegação por teclado anuncia rótulo, opção ativa, foco e mudança
- [x] Alvo clicável mede pelo menos 44×44px
- [x] Gate check passa: `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`

**Tests**: unit
**Gate**: full

---

### T5: Integrar `SeguradoContexto` às 5 superfícies existentes (5.1–5.6)

**What**: `VisaoGeralSegurado.tsx`, `SuperficieAlertas.tsx`, `SuperficieApolice.tsx`, `SuperficieComunicados.tsx`, `SuperficieMeusDados.tsx` passam a ler `seguradoAtivoId` de `useSeguradoContexto()` em vez de um valor fixo, com descarte de resposta tardia e ausência total de ação administrativa confirmada.
**Where**: `src/frontend/src/funcionalidades/segurado/VisaoGeralSegurado.tsx`, `SuperficieAlertas.tsx`, `SuperficieApolice.tsx`, `SuperficieComunicados.tsx`, `SuperficieMeusDados.tsx` (extensão pontual de 5.1–5.6)
**Depends on**: T4
**Reuses**: `SeguradoContexto` (T3), componentes já existentes de 5.1–5.6
**Requirement**: SELETOR-02, SELETOR-03, SELETOR-05, SELETOR-06

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Trocar de segurado atualiza as 5 superfícies em conjunto, sem mistura de dado (testado disparando a troca com requisições em voo)
- [ ] Nenhuma das 5 superfícies expõe qualquer ação administrativa (editar regra, gerar mensagem, aprovar lote, iniciar simulação)
- [ ] Voltar ao perfil Administrador reconstrói as superfícies administrativas sem alteração de autoridade no backend
- [ ] Testes existentes de cada uma das 5 superfícies (5.1–5.6) continuam passando após a extensão, sem contagem de teste reduzida
- [ ] Gate check passa: `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`

**Tests**: unit
**Gate**: full

**Commit**: `feat(segurado): adicionar alternancia entre segurados sinteticos com contexto consistente`

---

## Phase Execution Map

```
Phase 1:  T1 → T2
Phase 2:  T3 → T4
Phase 3:  T5
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
| T1: `listar_sinteticos` | 1 método, mesmo arquivo | ✅ Granular |
| T2: Endpoint de segurados | 1 componente | ✅ Granular |
| T3: `SeguradoContexto` | 1 componente | ✅ Granular |
| T4: Seletor "Visualizar como" | 1 componente | ✅ Granular |
| T5: Integração das 5 superfícies | 5 arquivos, mesma mudança lógica coesa | ⚠️ OK — mudança pontual idêntica em cada, não redesenho |

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
| T1: `listar_sinteticos` | Repositório | integration | integration | ✅ OK |
| T2: Endpoint de segurados | Roteador HTTP | integration | integration | ✅ OK |
| T3: `SeguradoContexto` | Componente/contexto React | unit | unit | ✅ OK |
| T4: Seletor "Visualizar como" | Componente React | unit | unit | ✅ OK |
| T5: Integração das 5 superfícies | Componente React (extensão) | unit | unit | ✅ OK |

**Rules confirmed**: nenhum `Tests: none` nesta história; nenhuma task adia teste.
