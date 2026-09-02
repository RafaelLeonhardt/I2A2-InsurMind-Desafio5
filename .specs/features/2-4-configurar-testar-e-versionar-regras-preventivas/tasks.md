# História 2.4: Configurar, testar e versionar regras preventivas — Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/2-4-configurar-testar-e-versionar-regras-preventivas/design.md`
**Status**: Approved

---

## Test Coverage Matrix

> Guidelines: `AGENTS.md`, `README.md`; piso em `testes/test_repositorio_execucao_preventiva.py` (concorrência otimista, 2.2).

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| `ValidadorRegra` | unit | Todos os branches; cada classe de invalidez (tipo, faixa, combinação, coerência evento↔produto) | `testes/test_validador_regra.py` | `uv run --directory src/backend pytest` |
| `RepositorioRegras` (extensão de escrita) | integration | `criar_nova_versao` com versão correta/incorreta (409), histórico preservado | `testes/test_repositorio_regras.py` (estendido) | `uv run --directory src/backend pytest` |
| `ServicoGestaoRegras` | unit | Todos os branches; 1:1 com `REGRA-07..10`; teste determinístico, ativação, idempotência | `testes/test_gestao_regras.py` | `uv run --directory src/backend pytest` |
| Roteador HTTP (regras) | integration | Consulta, teste, ativação: caminho feliz + cada invalidez + 409 concorrência/idempotência | `testes/test_regras_api.py` | `uv run --directory src/backend pytest` |
| Contrato OpenAPI | integration | Sincronia com as rotas novas | `testes/test_openapi_sincronizado.py` | `uv run --directory src/backend pytest` |
| Superfície "Regras" | unit | Tabela, formulário, teste — navegação por teclado, foco visível, erros por campo | `SuperficieRegras.test.tsx` | `npm test --prefix src/frontend -- --run` |

## Gate Check Commands

| Gate Level | When to Use | Command |
| --- | --- | --- |
| Quick (backend) | Tasks isoladas de domínio/aplicação/adaptador | `uv run --directory src/backend pytest` |
| Quick (frontend) | Tasks isoladas de componente | `npm test --prefix src/frontend -- --run` |
| Full (backend) | Tasks de roteador HTTP | `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright` |
| Full (frontend) | Tasks de superfície visível | `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend` |
| Build (fim de fase) | Fim de fase / contrato | Backend + Frontend em paralelo, mesmos comandos acima |

---

## Execution Plan

### Phase 1: Validação e escrita versionada

```
T1
T2
```

### Phase 2: Caso de uso

```
T3
```

### Phase 3: API

```
T4
```

### Phase 4: Frontend

```
T5
```

---

## Task Breakdown

### T1: `ValidadorRegra`

**What**: Validação de tipos, faixas, combinações obrigatórias e coerência evento↔produto, com mensagens por campo em português brasileiro.
**Where**: `src/backend/central_preventiva/dominio/validador_regra.py`
**Depends on**: None
**Reuses**: nada — primeira validação de regra
**Requirement**: REGRA-05, REGRA-06

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] Configuração válida não produz erro
- [x] Cada classe de invalidez (tipo errado, faixa fora do limite, combinação obrigatória ausente, evento↔produto incoerente) produz erro específico com o campo identificado
- [x] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: unit
**Gate**: quick

---

### T2: `RepositorioRegras` — escrita versionada

**What**: `listar`, `obter_por_id`, `criar_nova_versao` (concorrência otimista por `versao_esperada`, transação única: substitui a anterior e insere a nova ativa).
**Where**: `src/backend/central_preventiva/adaptadores/persistencia/repositorio_regras.py` (extensão de 2.3)
**Depends on**: None
**Reuses**: padrão de concorrência otimista de `RepositorioExecucaoPreventiva` (2.2)
**Requirement**: REGRA-09, REGRA-11

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] `criar_nova_versao` com `versao_esperada` correta cria nova linha `ativa` e marca a anterior `substituida`, na mesma transação
- [x] `criar_nova_versao` com `versao_esperada` incorreta levanta `ConflitoVersao`, sem mutar nenhuma linha
- [x] `listar`/`obter_por_id` retornam versões anteriores inalteradas
- [x] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: integration
**Gate**: quick

---

### T3: `ServicoGestaoRegras`

**What**: `testar` (aplica `AvaliadorRisco` de 2.3 a cenários sintéticos do `evento_tipo`) e `ativar` (bloqueia se inválida ou não testada; idempotente).
**Where**: `src/backend/central_preventiva/aplicacao/gestao_regras.py`
**Depends on**: T1, T2
**Reuses**: `AvaliadorRisco` (2.3), `RepositorioIdempotencia`
**Requirement**: REGRA-07, REGRA-08, REGRA-12, REGRA-13

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] Configuração inválida bloqueia `testar`/`ativar` com motivo específico, sem criar versão
- [x] `testar` retorna, por cenário sintético, operando/valor observado/resultado/justificativa
- [x] `ativar` após teste válido cria nova versão ativa
- [x] Repetir `ativar` com a mesma `Idempotency-Key` e conteúdo idêntico devolve a resposta registrada; conteúdo diferente retorna `409`
- [x] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: unit
**Gate**: quick

---

### T4: Roteador HTTP `regras`

**What**: `GET /api/v1/regras`, `GET /api/v1/regras/{id}`, `POST /api/v1/regras/{id}/testar`, `POST /api/v1/regras/{id}/ativar` (idempotente, `versao_esperada` no corpo).
**Where**: `src/backend/central_preventiva/adaptadores/http/regras.py`
**Depends on**: T3
**Reuses**: padrão de roteador existente, fixture `autouse` de bloqueio de rede real
**Requirement**: REGRA-11, REGRA-12, REGRA-13

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] Ativação concorrente com `versao_esperada` desatualizada retorna `409`
- [x] Ativação com `Idempotency-Key` repetida segue o contrato de idempotência
- [x] `openapi.json` regenerado, `test_openapi_sincronizado.py` verde
- [x] Gate check passa: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright`

**Tests**: integration
**Gate**: full

---

### T5: Superfície "Regras"

**What**: Tabela de regras (tipo, severidade, limiar, área, produto, coberturas, antecedência, canal, versão, estado), formulário de edição com erro por campo, painel de teste com resultado por cenário; tudo operável por teclado com foco visível.
**Where**: `src/frontend/src/funcionalidades/regras/SuperficieRegras.tsx`
**Depends on**: T4
**Reuses**: cliente HTTP central, padrão de tabela/formulário existente
**Requirement**: REGRA-01, REGRA-02, REGRA-03, REGRA-04, REGRA-14

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] Regra ativa identificada por texto+ícone+indicador, não só cor
- [x] Erro de validação aparece junto ao campo sem descartar os demais valores
- [x] Navegação, edição e confirmação totalmente por teclado, com foco visível
- [x] `npm run gerar-tipos-api --prefix src/frontend` executado; tipos atualizados (gerado via `openapi-typescript` direto do `openapi.json` local, sem servidor ao vivo)
- [x] Gate check passa: `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`

**Tests**: unit
**Gate**: full

**Commit**: `feat(regras): adicionar gestao versionada de regras preventivas`

---

## Phase Execution Map

```
Phase 1:  T1   T2
Phase 2:  T3
Phase 3:  T4
Phase 4:  T5
```

Grafo completo de dependências:

```
T1 → T3
T2 → T3
T3 → T4
T4 → T5
```

(T1 e T2 são independentes entre si na Fase 1.)

---

## Task Granularity Check

| Task | Scope | Status |
| --- | --- | --- |
| T1: `ValidadorRegra` | 1 componente | ✅ Granular |
| T2: `RepositorioRegras` escrita | 1 arquivo, extensão coesa | ✅ Granular |
| T3: `ServicoGestaoRegras` | 1 caso de uso | ✅ Granular |
| T4: Roteador `regras` | 1 componente | ✅ Granular |
| T5: Superfície "Regras" | 1 componente | ✅ Granular |

---

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| --- | --- | --- | --- |
| T1 | None | — | ✅ Match |
| T2 | None | — | ✅ Match |
| T3 | T1, T2 | T1 → T3, T2 → T3 (grafo completo) | ✅ Match |
| T4 | T3 | T3 → T4 | ✅ Match |
| T5 | T4 | T4 → T5 | ✅ Match |

**Rules confirmed**: toda dependência aponta para trás ou dentro da mesma fase.

---

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| --- | --- | --- | --- | --- |
| T1: `ValidadorRegra` | Domínio | unit | unit | ✅ OK |
| T2: `RepositorioRegras` escrita | Repositório | integration | integration | ✅ OK |
| T3: `ServicoGestaoRegras` | Aplicação | unit | unit | ✅ OK |
| T4: Roteador `regras` | Roteador HTTP | integration | integration | ✅ OK |
| T5: Superfície "Regras" | Componente React | unit | unit | ✅ OK |

**Rules confirmed**: nenhum `Tests: none` nesta história; nenhuma task adia teste.
