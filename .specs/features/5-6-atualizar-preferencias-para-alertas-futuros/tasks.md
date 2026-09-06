# História 5.6: Atualizar preferências para alertas futuros — Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/5-6-atualizar-preferencias-para-alertas-futuros/design.md`
**Status**: Approved

---

## Test Coverage Matrix

> Guidelines: `AGENTS.md`, `README.md`; piso em `testes/test_repositorio_regras.py` (2.4, concorrência+idempotência) e `testes/test_repositorio_execucao_preventiva.py` (2.2).

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| Migração `0014_versao_segurados.sql` | integration | Aplicação, coluna nova | `testes/test_migracoes.py` | `uv run --directory src/backend pytest` |
| Extensão de `RepositorioSegurados.atualizar_preferencias` | integration | Versão correta/incorreta (`ConflitoVersao`) | `testes/test_repositorio_segurados.py` (estendido) | `uv run --directory src/backend pytest` |
| `ServicoPreferenciasSegurado` | unit | Todos os branches; 1:1 com `PREFS-01..07`; idempotência | `testes/test_preferencias_segurado.py` | `uv run --directory src/backend pytest` |
| Roteador HTTP (preferências) | integration | Caminho feliz + `409` concorrência + `409` idempotência conteúdo diferente | `testes/test_preferencias_segurado_api.py` | `uv run --directory src/backend pytest` |
| Contrato OpenAPI | integration | Sincronia com a rota nova | `testes/test_openapi_sincronizado.py` | `uv run --directory src/backend pytest` |
| Superfície de Meus Dados | unit | `Salvando`/`Salvo`, preservação de valor em erro, formulário acessível por teclado | `SuperficieMeusDados.test.tsx` | `npm test --prefix src/frontend -- --run` |

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

### Phase 1: Schema e escrita versionada

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

### T1: Migração `0014_versao_segurados.sql`

**What**: Adicionar `versao INTEGER NOT NULL DEFAULT 1` a `segurados`; atualizar `README.md` de persistência.
**Where**: `src/backend/central_preventiva/adaptadores/persistencia/migracoes/0014_versao_segurados.sql`
**Depends on**: None
**Reuses**: convenção de migração numerada
**Requirement**: PREFS-02

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] Migração aplica em transação própria, registrada em `schema_migracoes`
- [x] `README.md` documenta a coluna nova
- [x] `testes/test_migracoes.py` cobre a aplicação da migração `0014`
- [x] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: integration
**Gate**: quick

**Status**: ✅ Complete — migração entrou como `0016` (`0014`/`0015` já consumidos pelas Histórias 3.1–3.5/4.3), mesma renumeração já registrada desde a 2.4.

---

### T2: Extensão de `RepositorioSegurados.atualizar_preferencias`

**What**: Escrita versionada de `canal_preferido`/`participa_de_alertas` com concorrência otimista.
**Where**: `src/backend/central_preventiva/adaptadores/persistencia/repositorio_segurados.py` (extensão de Épico 1)
**Depends on**: T1
**Reuses**: padrão de concorrência otimista de `RepositorioExecucaoPreventiva` (2.2)
**Requirement**: PREFS-02, PREFS-04

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] `versao_esperada` correta atualiza e incrementa a versão
- [x] `versao_esperada` incorreta levanta `ConflitoVersao`, sem mutar a linha
- [x] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: integration
**Gate**: quick

**Status**: ✅ Complete — `PreferenciasSegurado` ganhou `versao` (extensão retrocompatível: `apolice_segurado.py` só lê `canal_preferido`/`participa_de_alertas`, não constrói o dataclass).

---

### T3: `ServicoPreferenciasSegurado`

**What**: `atualizar` com idempotência (`Idempotency-Key`) + escrita versionada.
**Where**: `src/backend/central_preventiva/aplicacao/preferencias_segurado.py`
**Depends on**: T2
**Reuses**: `RepositorioIdempotencia` (AD-002)
**Requirement**: PREFS-02, PREFS-03, PREFS-06

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] Alteração válida persiste e retorna o segurado atualizado
- [x] Repetir com a mesma chave e conteúdo idêntico devolve a resposta registrada, sem nova versão
- [x] Repetir com a mesma chave e conteúdo diferente retorna `409`
- [x] `versao_esperada` desatualizada retorna `409`, sem mutar
- [x] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: unit
**Gate**: quick

**Status**: ✅ Complete — `409` é responsabilidade do roteador HTTP (T4); aqui o caso de uso propaga `ConflitoVersao`/`ConflitoIdempotencia`, mesmo padrão de `ServicoGestaoRegras.ativar` (2.4).

---

### T4: Roteador HTTP de preferências

**What**: `PUT /api/v1/segurados/{segurado_id}/preferencias` (idempotente, `versao_esperada` no corpo).
**Where**: `src/backend/central_preventiva/adaptadores/http/preferencias_segurado.py`
**Depends on**: T3
**Reuses**: padrão de roteador existente
**Requirement**: PREFS-01, PREFS-03

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] `200` com o segurado atualizado em caso de sucesso
- [ ] `409` para conflito de versão e para idempotência com conteúdo diferente
- [ ] `openapi.json` regenerado, `test_openapi_sincronizado.py` verde
- [ ] Gate check passa: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright`

**Tests**: integration
**Gate**: full

---

### T5: Superfície de Meus Dados

**What**: Formulário com canal preferencial e participação em alertas; estados `Salvando`/`Salvo`; preserva valores editados em erro; explica efeito "só futuro" ao desativar participação; totalmente acessível por teclado, sem depender só de toast/cor.
**Where**: `src/frontend/src/funcionalidades/segurado/SuperficieMeusDados.tsx`
**Depends on**: T4
**Reuses**: cliente HTTP central, padrão de formulário validado de `SuperficieRegras` (2.4)
**Requirement**: PREFS-01, PREFS-02, PREFS-05, PREFS-06, PREFS-07

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Só canal e participação são editáveis, nenhum outro campo de cadastro presente
- [ ] `Salvando`→`Salvo` exibidos corretamente; erro preserva valores editados sem "Salvo" antecipado
- [ ] Desativar participação exibe explicação de efeito "só futuro"
- [ ] Formulário navegável inteiramente por teclado, com foco visível em cada etapa
- [ ] `npm run gerar-tipos-api --prefix src/frontend` executado; tipos atualizados
- [ ] Gate check passa: `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`

**Tests**: unit
**Gate**: full

**Commit**: `feat(segurado): adicionar edicao de canal preferencial e participacao em alertas`

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
| T1: Migração `0014` | 1 arquivo `.sql` + doc | ✅ Granular |
| T2: `atualizar_preferencias` | 1 método, mesmo arquivo | ✅ Granular |
| T3: `ServicoPreferenciasSegurado` | 1 caso de uso | ✅ Granular |
| T4: Roteador de preferências | 1 componente | ✅ Granular |
| T5: Superfície de Meus Dados | 1 componente | ✅ Granular |

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
| T1: Migração `0014` | Migração/schema | integration | integration | ✅ OK |
| T2: `atualizar_preferencias` | Repositório | integration | integration | ✅ OK |
| T3: `ServicoPreferenciasSegurado` | Aplicação | unit | unit | ✅ OK |
| T4: Roteador de preferências | Roteador HTTP | integration | integration | ✅ OK |
| T5: Superfície de Meus Dados | Componente React | unit | unit | ✅ OK |

**Rules confirmed**: nenhum `Tests: none` nesta história; nenhuma task adia teste.
