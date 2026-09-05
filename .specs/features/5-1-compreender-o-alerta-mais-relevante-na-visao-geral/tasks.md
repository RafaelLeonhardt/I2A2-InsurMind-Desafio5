# História 5.1: Compreender o alerta mais relevante na visão geral — Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/5-1-compreender-o-alerta-mais-relevante-na-visao-geral/design.md`
**Status**: Approved

---

## Test Coverage Matrix

> Guidelines: `AGENTS.md`, `README.md`; piso em `testes/test_avaliacao_elegibilidade.py` (junção multi-fonte) e `src/frontend/src/funcionalidades/segurado/VisaoGeralSegurado.test.tsx` (já existe, hoje testando o mockup — será reescrito para a versão real).

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| Extensão de `RepositorioElegibilidades` | integration | `obter_mais_recente_por_segurado`: com/sem resultado | `testes/test_repositorio_elegibilidade.py` (estendido) | `uv run --directory src/backend pytest` |
| `ServicoAlertaSegurado` | unit | Todos os branches; 1:1 com `VISAO-01..06` | `testes/test_alerta_segurado.py` | `uv run --directory src/backend pytest` |
| Roteador HTTP (alerta do segurado) | integration | Caminho feliz + sem alerta + fonte degradada | `testes/test_alerta_segurado_api.py` | `uv run --directory src/backend pytest` |
| Contrato OpenAPI | integration | Sincronia com a rota nova | `testes/test_openapi_sincronizado.py` | `uv run --directory src/backend pytest` |
| `VisaoGeralSegurado.tsx` (reescrita) | unit | 5 estados (`Carregando`…`Erro`), sem texto fixo, acessibilidade de teclado/zoom | `VisaoGeralSegurado.test.tsx` (reescrito) | `npm test --prefix src/frontend -- --run` |

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

### T1: Extensão de `RepositorioElegibilidades.obter_mais_recente_por_segurado`

**What**: Encontra a elegibilidade `incluido` mais recente do segurado informado.
**Where**: `src/backend/central_preventiva/adaptadores/persistencia/repositorio_elegibilidade.py` (extensão de 2.5)
**Depends on**: None
**Reuses**: mesma tabela `elegibilidades_historicas`
**Requirement**: VISAO-01

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] Retorna a elegibilidade `incluido` mais recente quando existir
- [x] Retorna `None` quando o segurado não tiver nenhuma elegibilidade `incluido`
- [x] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: integration
**Gate**: quick

---

### T2: `ServicoAlertaSegurado`

**What**: Monta `AlertaSegurado` (tipo, severidade, período, localização, impactos, recomendações, origem, horário, estado de fonte) a partir da elegibilidade mais recente.
**Where**: `src/backend/central_preventiva/aplicacao/alerta_segurado.py`
**Depends on**: T1
**Reuses**: `RepositorioAvaliacoesRisco` (2.3), `RepositorioContextosAgente` (3.1), `RepositorioSincronizacoes` (2.1/2.2)
**Requirement**: VISAO-01, VISAO-02, VISAO-03, VISAO-04, VISAO-05

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] Alerta real (`real_inmet`) retorna todos os campos do AC, origem nunca rotulada como sintética
- [x] Alerta sintético retorna origem claramente rotulada como tal
- [x] Sem elegibilidade: retorna `None`
- [x] Fonte degradada: retorna snapshot com idade calculada e caráter informativo
- [x] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: unit
**Gate**: quick

---

### T3: Endpoint HTTP do alerta do segurado

**What**: `GET /api/v1/segurados/{segurado_id}/alerta-mais-relevante`.
**Where**: `src/backend/central_preventiva/adaptadores/http/alerta_segurado.py`
**Depends on**: T2
**Reuses**: padrão de roteador existente
**Requirement**: VISAO-01, VISAO-06

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] `200` com o alerta quando existir
- [ ] `200` com corpo indicando ausência quando não existir (não `404` — ausência de alerta é um resultado válido, não um erro)
- [ ] `openapi.json` regenerado, `test_openapi_sincronizado.py` verde
- [ ] Gate check passa: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright`

**Tests**: integration
**Gate**: full

---

### T4: Reescrever `VisaoGeralSegurado.tsx` com dado real

**What**: Substituir todo o texto fixo por consumo real da API (T3), com os 5 estados (`Carregando`, `Alerta`, `Sem alerta`, `Contexto trocando`, `Erro`), preservando último contexto válido em erro, acessível por teclado/zoom 200%.
**Where**: `src/frontend/src/funcionalidades/segurado/VisaoGeralSegurado.tsx`
**Depends on**: T3
**Reuses**: estrutura visual já existente do componente (Épico 1), cliente HTTP central
**Requirement**: VISAO-01, VISAO-02, VISAO-03, VISAO-04, VISAO-05, VISAO-06, VISAO-07, VISAO-08

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Nenhum texto fixo de alerta/localização/apólice/regra permanece no componente
- [ ] Os 5 estados renderizam corretamente, com `Erro` preservando o último contexto válido exibido
- [ ] Teste de navegação por teclado confirma ordem/foco/nomes acessíveis; teste de zoom 200% (viewport reduzido) confirma que nenhuma informação essencial desaparece
- [ ] `npm run gerar-tipos-api --prefix src/frontend` executado; tipos atualizados
- [ ] Gate check passa: `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`

**Tests**: unit
**Gate**: full

**Commit**: `feat(segurado): substituir mockup da visao geral por alerta real do segurado`

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
| T1: `obter_mais_recente_por_segurado` | 1 método, mesmo arquivo | ✅ Granular |
| T2: `ServicoAlertaSegurado` | 1 caso de uso | ✅ Granular |
| T3: Endpoint do alerta | 1 componente | ✅ Granular |
| T4: Reescrita da Visão geral | 1 componente | ✅ Granular |

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
| T1: `obter_mais_recente_por_segurado` | Repositório | integration | integration | ✅ OK |
| T2: `ServicoAlertaSegurado` | Aplicação | unit | unit | ✅ OK |
| T3: Endpoint do alerta | Roteador HTTP | integration | integration | ✅ OK |
| T4: Reescrita da Visão geral | Componente React | unit | unit | ✅ OK |

**Rules confirmed**: nenhum `Tests: none` nesta história; nenhuma task adia teste.
