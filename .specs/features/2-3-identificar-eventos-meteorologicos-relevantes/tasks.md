# História 2.3: Identificar eventos meteorológicos relevantes — Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/2-3-identificar-eventos-meteorologicos-relevantes/design.md`
**Status**: Approved

---

## Test Coverage Matrix

> Guidelines: `AGENTS.md`, `README.md` — nenhum threshold dedicado; defaults fortes aplicados.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| Migração `0004_avaliacao_risco.sql` | integration | Aplicação e forma da tabela nova | `testes/test_migracoes.py` | `uv run --directory src/backend pytest` |
| `AvaliadorRisco` (domínio, função pura) | unit | Todos os branches; 1:1 com `RISCO-01..10`; toda fronteira inclusiva/exclusiva testada | `testes/test_avaliador_risco.py` | `uv run --directory src/backend pytest` |
| `RepositorioRegras` / `RepositorioAvaliacoesRisco` | integration | Leitura da regra ativa; escrita/leitura do snapshot | `testes/test_repositorio_regras.py`, `testes/test_repositorio_avaliacoes_risco.py` | `uv run --directory src/backend pytest` |
| `ServicoAvaliacaoRisco` | unit | Todos os branches; 1:1 com `RISCO-09..10`; repetibilidade e transições permitidas | `testes/test_avaliacao_risco.py` | `uv run --directory src/backend pytest` |
| Roteador HTTP (evento e decisão) | integration | `GET` do detalhe da decisão: caminho feliz + tipo não suportado + sem regra ativa | `testes/test_avaliacao_risco_api.py` | `uv run --directory src/backend pytest` |
| Contrato OpenAPI | integration | Sincronia com a rota nova | `testes/test_openapi_sincronizado.py` | `uv run --directory src/backend pytest` |
| Superfície "Evento e decisão" (detalhe de risco) | unit | Progresso real da máquina de estados, sem recálculo no frontend; relevância/sem risco/dado inválido distinguíveis | `SuperficieEventoDecisao.test.tsx` | `npm test --prefix src/frontend -- --run` |

## Gate Check Commands

| Gate Level | When to Use | Command |
| --- | --- | --- |
| Quick (backend) | Tasks isoladas de domínio/aplicação/adaptador | `uv run --directory src/backend pytest` |
| Quick (frontend) | Tasks isoladas de componente | `npm test --prefix src/frontend -- --run` |
| Full (backend) | Tasks de roteador HTTP ou schema | `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright` |
| Full (frontend) | Tasks de superfície visível | `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend` |
| Build (fim de fase) | Fim de fase / contrato | Backend + Frontend em paralelo, mesmos comandos acima |

---

## Execution Plan

### Phase 1: Schema e motor determinístico

T1 e T2 são independentes entre si (nenhuma depende da outra); execução em ordem T1, T2.

```
T1
T2
```

### Phase 2: Persistência

```
T3
```

### Phase 3: Caso de uso e API

```
T4 → T5
```

### Phase 4: Frontend

```
T6
```

---

## Task Breakdown

### T1: Migração `0004_avaliacao_risco.sql`

**What**: Criar `avaliacoes_risco`; atualizar `adaptadores/persistencia/README.md`.
**Where**: `src/backend/central_preventiva/adaptadores/persistencia/migracoes/0004_avaliacao_risco.sql`
**Depends on**: None
**Reuses**: convenção de migração numerada
**Requirement**: RISCO-09

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] Migração aplica em transação própria, registrada em `schema_migracoes`
- [x] `README.md` documenta `avaliacoes_risco`
- [x] `testes/test_migracoes.py` cobre a aplicação da migração `0004`
- [x] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: integration
**Gate**: quick

---

### T2: `AvaliadorRisco` (motor determinístico)

**What**: Função pura que compara `EventoMeteorologico` a `RegraSnapshot` e retorna `ResultadoAvaliacaoRisco` (relevante/não relevante/não suportado, com critérios avaliados).
**Where**: `src/backend/central_preventiva/dominio/avaliador_risco.py`
**Depends on**: None
**Reuses**: `EventoMeteorologico` (2.1)
**Requirement**: RISCO-01, RISCO-02, RISCO-03, RISCO-04, RISCO-05, RISCO-06, RISCO-07, RISCO-08

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] Evento de tipo não suportado retorna resultado "não suportado" sem avaliar limiar
- [x] Chuva intensa abaixo do limiar (49.9mm) → não relevante; no limiar exato (50.0mm) → relevante (fronteira inclusiva); acima (50.1mm) → relevante
- [x] Granizo com `tipo = granizo` → sempre relevante (gatilho por ocorrência)
- [x] Mesma entrada avaliada duas vezes produz resultado e justificativa idênticos
- [x] Nenhuma chamada a qualquer porta de IA em nenhum caminho
- [x] Gate check passa: `uv run --directory src/backend pytest`

**Nota de implementação**: granizo também checa "área aplicável" (não só ocorrência) — a spec/design falam de "comparar medidas, área, severidade e período" para AMBOS os produtos, e o edge case "evento sem área reconhecida → não relevante, não erro técnico" se aplica aos dois tipos, não só chuva. O teste de "tipo não suportado" usa um valor de string arbitrário no campo `tipo` (o `EventoMeteorologico` não valida em runtime) já que `TipoEventoMeteorologico` só tem os dois valores suportados — o branch é uma defesa contra dado externo malformado, não um caminho alcançável pelo enum em si.

**Tests**: unit
**Gate**: quick

---

### T3: `RepositorioRegras` (leitura) e `RepositorioAvaliacoesRisco`

**What**: `RepositorioRegras.obter_ativa(evento_tipo)`; `RepositorioAvaliacoesRisco.salvar`/`obter_por_execucao`.
**Where**: `src/backend/central_preventiva/adaptadores/persistencia/repositorio_regras.py`, `repositorio_avaliacoes_risco.py`
**Depends on**: T1
**Reuses**: padrão de conexão explícita
**Requirement**: RISCO-09

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] `obter_ativa` retorna a regra com `estado = ativa` para o tipo de evento; `None` se nenhuma existir
- [x] `salvar` persiste snapshot completo (evento, regra, versão, critérios serializados, motivo)
- [x] `obter_por_execucao` recupera o snapshot salvo sem recalcular
- [x] Gate check passa: `uv run --directory src/backend pytest`

**Nota de implementação**: `salvar` ganhou um parâmetro explícito `regra_versao: int` além dos listados no design — `regra_id` (UUID) e `ResultadoAvaliacaoRisco` não carregam a versão, mas `avaliacoes_risco.regra_versao` é `NOT NULL` (AD-11: snapshot de versão, não referência viva). `AvaliacaoRisco` (registro completo persistido, distinto do `ResultadoAvaliacaoRisco` puro do domínio) vive em `repositorio_avaliacoes_risco.py`, mesmo padrão de `SnapshotExecucao` em `repositorio_execucao_preventiva.py` (2.2 T2).

**Tests**: integration
**Gate**: quick

---

### T4: `ServicoAvaliacaoRisco`

**What**: Orquestra `RepositorioRegras.obter_ativa` → `AvaliadorRisco.avaliar` → `RepositorioAvaliacoesRisco.salvar` → `RepositorioExecucaoPreventiva.transicionar` (`sem_risco` ou `avaliando_elegibilidade`).
**Where**: `src/backend/central_preventiva/aplicacao/avaliacao_risco.py`
**Depends on**: T2, T3
**Reuses**: `RepositorioExecucaoPreventiva` (2.2), sem alteração de assinatura
**Requirement**: RISCO-09, RISCO-10

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Evento não relevante transiciona a execução para `sem_risco` com snapshot salvo, sem criar elegibilidade/mensagem/chamada de IA
- [ ] Evento relevante transiciona para `avaliando_elegibilidade` com snapshot salvo
- [ ] Ausência de regra ativa é tratada como `sem_risco` com motivo específico
- [ ] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: unit
**Gate**: quick

---

### T5: Endpoint HTTP de detalhe da decisão de risco

**What**: `GET /api/v1/execucoes/{execucao_id}/avaliacao-risco` retornando operando, valor observado, resultado e justificativa de cada critério.
**Where**: `src/backend/central_preventiva/adaptadores/http/avaliacao_risco.py`
**Depends on**: T4
**Reuses**: padrão de roteador existente
**Requirement**: RISCO-11, RISCO-12

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] `200` com os critérios detalhados quando a avaliação existe
- [ ] `404`/`application/problem+json` quando a execução não tem avaliação de risco ainda
- [ ] Roteador incluído em `composicao/api.py`
- [ ] `openapi.json` regenerado e `test_openapi_sincronizado.py` verde
- [ ] Gate check passa: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright`

**Tests**: integration
**Gate**: full

---

### T6: Superfície "Evento e decisão" — detalhe de risco

**What**: Componente que exibe operando/valor observado/resultado/justificativa por critério, distinguindo relevância/sem risco/dado inválido por texto+ícone+cor; progresso reflete a etapa real da máquina de estados (sem recálculo no frontend).
**Where**: `src/frontend/src/funcionalidades/evento-decisao/SuperficieEventoDecisao.tsx`
**Depends on**: T5
**Reuses**: padrão de `SuperficieProntidao.tsx`, cliente HTTP central
**Requirement**: RISCO-11, RISCO-12, RISCO-13

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Critérios exibidos em colunas estáveis (operando, valor, resultado, justificativa)
- [ ] Relevância/sem risco/dado inválido distinguíveis sem depender só de cor
- [ ] Nenhum cálculo de relevância replicado no componente
- [ ] `npm run gerar-tipos-api --prefix src/frontend` executado; tipos atualizados
- [ ] Gate check passa: `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`

**Tests**: unit
**Gate**: full

**Commit**: `feat(risco): adicionar avaliacao deterministica de relevancia meteorologica`

---

## Phase Execution Map

```
Phase 1:  T1   T2
Phase 2:  T3
Phase 3:  T4 → T5
Phase 4:  T6
```

Grafo completo de dependências:

```
T1 → T3
T2 → T4
T3 → T4
T4 → T5
T5 → T6
```

(T1 e T2 são independentes entre si na Fase 1, ambas sem dependência.)

---

## Task Granularity Check

| Task | Scope | Status |
| --- | --- | --- |
| T1: Migração `0004` | 1 arquivo `.sql` + doc | ✅ Granular |
| T2: `AvaliadorRisco` | 1 componente | ✅ Granular |
| T3: Repositórios de leitura | 2 arquivos, mesma família de porta | ⚠️ OK — coesos |
| T4: `ServicoAvaliacaoRisco` | 1 caso de uso | ✅ Granular |
| T5: Endpoint HTTP | 1 componente | ✅ Granular |
| T6: Superfície "Evento e decisão" | 1 componente | ✅ Granular |

---

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| --- | --- | --- | --- |
| T1 | None | — | ✅ Match |
| T2 | None | — | ✅ Match |
| T3 | T1 | T1 → T3 (grafo completo) | ✅ Match |
| T4 | T2, T3 | T2 → T4, T3 → T4 (grafo completo) | ✅ Match |
| T5 | T4 | T4 → T5 | ✅ Match |
| T6 | T5 | T5 → T6 (grafo completo) | ✅ Match |

**Rules confirmed**: toda dependência aponta para trás ou dentro da mesma fase.

---

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| --- | --- | --- | --- | --- |
| T1: Migração `0004` | Migração/schema | integration | integration | ✅ OK |
| T2: `AvaliadorRisco` | Domínio (motor) | unit | unit | ✅ OK |
| T3: Repositórios | Repositório | integration | integration | ✅ OK |
| T4: `ServicoAvaliacaoRisco` | Aplicação | unit | unit | ✅ OK |
| T5: Endpoint HTTP | Roteador HTTP | integration | integration | ✅ OK |
| T6: Superfície "Evento e decisão" | Componente React | unit | unit | ✅ OK |

**Rules confirmed**: nenhum `Tests: none` nesta história; nenhuma task adia teste.
