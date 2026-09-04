# História 3.6: Confirmar e executar a simulação sem envio real — Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/3-6-confirmar-e-executar-a-simulacao-sem-envio-real/design.md`
**Status**: Approved

---

## Test Coverage Matrix

> Guidelines: `AGENTS.md`, `README.md`; piso em `testes/test_restauracao.py` (Épico 1, transação única) e `testes/test_coleta_meteorologica.py`/`testes/test_preflight_ia.py` (2.2/3.1, execução correlacionada).

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| Migração `0012_entregas_simuladas.sql` | integration | Aplicação, tabela nova, `UNIQUE` | `testes/test_migracoes.py` | `uv run --directory src/backend pytest` |
| `RepositorioEntregasSimuladas` | integration | Criar lote atomicamente, listar por execução | `testes/test_repositorio_entregas_simuladas.py` | `uv run --directory src/backend pytest` |
| `ServicoSimulacao.confirmar` | unit | Todos os branches; 1:1 com `SIMUL-01..09`; reclamação atômica, rollback local, idempotência, concorrência | `testes/test_simulacao.py` | `uv run --directory src/backend pytest` |
| `ServicoSimulacao.solicitar_nova_tentativa` | unit | Validação de snapshot, execução correlacionada, origem permanece terminal | `testes/test_simulacao.py` | `uv run --directory src/backend pytest` |
| Roteador HTTP (confirmação e nova tentativa) | integration | Caminho feliz + `409` + idempotência + navegação origem↔retentativa | `testes/test_simulacao_api.py` | `uv run --directory src/backend pytest` |
| Contrato OpenAPI | integration | Sincronia com as rotas novas | `testes/test_openapi_sincronizado.py` | `uv run --directory src/backend pytest` |
| Modal de confirmação e superfície de progresso | unit | Bloqueio sem reconhecimento, 5 estados (`Bloqueada`…`Falha local`), caráter simulado sempre visível | `SuperficieSimulacao.test.tsx` | `npm test --prefix src/frontend -- --run` |

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

### Phase 1: Schema e persistência

```
T1 → T2
```

### Phase 2: Caso de uso da simulação

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

### T1: Migração `0012_entregas_simuladas.sql` ✅

**What**: Criar `entregas_simuladas` (`UNIQUE(mensagem_id)`); atualizar `README.md` de persistência.
**Where**: `src/backend/central_preventiva/adaptadores/persistencia/migracoes/0012_entregas_simuladas.sql`
**Depends on**: None
**Reuses**: convenção de migração numerada
**Requirement**: SIMUL-05

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] Migração aplica em transação própria, registrada em `schema_migracoes` (renumerada para `0014`: `0009`–`0013` já consumidas por 3.1–3.5; `SPEC_DEVIATION` no topo do `.sql`)
- [x] `README.md` documenta a tabela nova e a `UNIQUE`
- [x] `testes/test_migracoes.py` cobre a aplicação da migração `0014`
- [x] Gate check passa: `uv run --directory src/backend pytest` (832 passed)

**Tests**: integration
**Gate**: quick

---

### T2: `RepositorioEntregasSimuladas`

**What**: `criar_lote` (dentro da transação do chamador), `listar_por_execucao`.
**Where**: `src/backend/central_preventiva/adaptadores/persistencia/repositorio_entregas_simuladas.py`
**Depends on**: T1
**Reuses**: padrão de conexão explícita
**Requirement**: SIMUL-05, SIMUL-06

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] `criar_lote` insere uma entrega por mensagem+canal, com `apresentacao` copiada do `conteudo` da versão aprovada
- [ ] `listar_por_execucao` retorna todas as entregas de uma execução
- [ ] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: integration
**Gate**: quick

---

### T3: `ServicoSimulacao`

**What**: `confirmar` (reclamação atômica, transação 1 de entregas+transição de mensagens, rollback+transação 2 de `falhou_simulacao` em falha local) e `solicitar_nova_tentativa` (execução correlacionada).
**Where**: `src/backend/central_preventiva/aplicacao/simulacao.py`
**Depends on**: T2
**Reuses**: `RepositorioMensagens.transicionar` (3.2), `RepositorioExecucaoPreventiva.transicionar` (2.2), padrão de execução correlacionada de 2.2/3.1
**Requirement**: SIMUL-04, SIMUL-05, SIMUL-06, SIMUL-07, SIMUL-08, SIMUL-09, SIMUL-10

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Reclamação atômica reconsulta o estado real das mensagens (não confia em estado enviado pelo cliente); só as `aprovada` são reclamadas
- [ ] Sucesso: entregas criadas, mensagens `simulada_entregue`, execução `concluida`, tudo na mesma transação 1
- [ ] Falha local injetada (via `injecao_falha_teste`): rollback da transação 1 (mensagens permanecem `aprovada`, nenhuma entrega parcial), transação 2 move para `falhou_simulacao` com `Exceção` sanitizada
- [ ] Repetir `confirmar` com a mesma `Idempotency-Key` devolve o resultado já registrado, sem criar segunda entrega
- [ ] Duas chamadas concorrentes para a mesma `versao_esperada`: só uma reclama; a outra recebe idempotente ou conflito, sem duplicação
- [ ] `solicitar_nova_tentativa` com snapshot corrompido rejeita sem criar execução; com snapshot válido cria execução correlacionada em `aguardando_geracao` com `execucao_origem_id`, origem permanece terminal
- [ ] `solicitar_nova_tentativa` copia as elegibilidades da origem para a nova execução na mesma transação (`RepositorioElegibilidades.copiar_para_execucao`, AD-012); teste cobre origem que chegou a `simulando` (com contextos e mensagens existentes) e confirma que a nova execução gera contexto e mensagem sem violar as `UNIQUE`s de `contextos_agente`/`mensagens`
- [ ] Nenhum teste ou código de produção invoca qualquer conector real de canal
- [ ] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: unit
**Gate**: quick

---

### T4: Roteador HTTP — confirmação e nova tentativa

**What**: `POST /api/v1/execucoes/{id}/confirmar-simulacao` (idempotente, exige campo de reconhecimento) e `POST /api/v1/execucoes/{origem_id}/nova-tentativa-simulacao`; `GET /api/v1/execucoes/{id}` estendido com o resumo da simulação (destinatários, distribuição por canal, estado).
**Where**: `src/backend/central_preventiva/adaptadores/http/simulacao.py`
**Depends on**: T3
**Reuses**: padrão de roteador existente, fixture `autouse` de bloqueio de rede real
**Requirement**: SIMUL-01, SIMUL-07, SIMUL-11

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Confirmação sem o campo de reconhecimento marcado retorna erro `application/problem+json`
- [ ] Confirmação com `versao_esperada` desatualizada retorna `409`
- [ ] Repetir a mesma `Idempotency-Key` devolve a resposta registrada
- [ ] `openapi.json` regenerado, `test_openapi_sincronizado.py` verde
- [ ] Gate check passa: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright`

**Tests**: integration
**Gate**: full

---

### T5: Modal de confirmação e superfície de progresso da simulação

**What**: Modal com evento/regra/período/quantidade/distribuição por canal, checkbox de reconhecimento bloqueando a ação principal até marcado; superfície de progresso com os 5 estados (`Bloqueada`, `Pronta`, `Simulando`, `Concluída`, `Falha local`) e navegação origem↔retentativa.
**Where**: `src/frontend/src/funcionalidades/simulacao/SuperficieSimulacao.tsx`
**Depends on**: T4
**Reuses**: cliente HTTP central, `Modal` (Épico 1) como base do componente de confirmação
**Requirement**: SIMUL-02, SIMUL-03, SIMUL-11, SIMUL-12

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Botão de confirmar desabilitado até o reconhecimento ser marcado
- [ ] Os 5 estados exibidos distintamente, caráter simulado sempre visível (durante e depois)
- [ ] Link de navegação origem↔retentativa funcional
- [ ] `npm run gerar-tipos-api --prefix src/frontend` executado; tipos atualizados
- [ ] Gate check passa: `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`

**Tests**: unit
**Gate**: full

**Commit**: `feat(simulacao): adicionar confirmacao e execucao da simulacao local sem envio real`

---

## Phase Execution Map

```
Phase 1:  T1 → T2
Phase 2:  T3
Phase 3:  T4
Phase 4:  T5
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
| T1: Migração `0012` | 1 arquivo `.sql` + doc | ✅ Granular |
| T2: `RepositorioEntregasSimuladas` | 1 componente | ✅ Granular |
| T3: `ServicoSimulacao` | 1 caso de uso | ✅ Granular |
| T4: Roteador de simulação | 1 componente | ✅ Granular |
| T5: Modal + superfície de progresso | 1 componente | ✅ Granular |

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
| T1: Migração `0012` | Migração/schema | integration | integration | ✅ OK |
| T2: `RepositorioEntregasSimuladas` | Repositório | integration | integration | ✅ OK |
| T3: `ServicoSimulacao` | Aplicação | unit | unit | ✅ OK |
| T4: Roteador de simulação | Roteador HTTP | integration | integration | ✅ OK |
| T5: Modal + superfície de progresso | Componente React | unit | unit | ✅ OK |

**Rules confirmed**: nenhum `Tests: none` nesta história; nenhuma task adia teste.
