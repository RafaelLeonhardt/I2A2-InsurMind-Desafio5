# História 2.6: Encerrar ou encaminhar a execução preventiva — Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/2-6-encerrar-ou-encaminhar-a-execucao-preventiva/design.md`
**Status**: Approved

---

## Test Coverage Matrix

> Guidelines: `AGENTS.md`, `README.md`; piso em `testes/test_servidor.py` (lifespan) e `testes/test_repositorio_execucao_preventiva.py` (2.2).

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| Migração `0006_marcos_execucao.sql` | integration | Aplicação e forma da tabela nova | `testes/test_migracoes.py` | `uv run --directory src/backend pytest` |
| Extensão de `RepositorioExecucaoPreventiva` | integration | `listar_nao_terminais`, `registrar_marco` | `testes/test_repositorio_execucao_preventiva.py` (estendido) | `uv run --directory src/backend pytest` |
| `GerenciadorExecucoes` | unit | Todos os branches; 1:1 com `RUNNER-01..09`; os três terminais, falha técnica, retomada, idempotência | `testes/test_gerenciador_execucoes.py` | `uv run --directory src/backend pytest` |
| Roteador HTTP (iniciar execução) | integration | Caminho feliz + idempotência + os três resultados observáveis via `GET` | `testes/test_execucao_preventiva_api.py` | `uv run --directory src/backend pytest` |
| Wiring do lifespan (`retomar_pendentes`) | integration | Retomada no boot com execução não terminal persistida | `testes/test_servidor.py` (estendido) | `uv run --directory src/backend pytest` |
| Contrato OpenAPI | integration | Sincronia com a rota nova | `testes/test_openapi_sincronizado.py` | `uv run --directory src/backend pytest` |
| Superfície de acompanhamento da execução | unit | Etapas concluídas/corrente/encerramento/exceção distinguíveis; anúncio acessível | `SuperficieExecucao.test.tsx` | `npm test --prefix src/frontend -- --run` |

## Gate Check Commands

| Gate Level | When to Use | Command |
| --- | --- | --- |
| Quick (backend) | Tasks isoladas de aplicação/adaptador | `uv run --directory src/backend pytest` |
| Quick (frontend) | Tasks isoladas de componente | `npm test --prefix src/frontend -- --run` |
| Full (backend) | Tasks de roteador HTTP, schema ou lifespan | `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright` |
| Full (frontend) | Tasks de superfície visível | `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend` |
| Build (fim de fase) | Fim de fase / contrato | Backend + Frontend em paralelo, mesmos comandos acima |

---

## Execution Plan

### Phase 1: Schema e extensão de repositório

```
T1 → T2
```

### Phase 2: Orquestrador

```
T3
```

### Phase 3: API e wiring do lifespan

```
T4 → T5
```

### Phase 4: Frontend

```
T6
```

---

## Task Breakdown

### T1: Migração `0008_marcos_execucao.sql`

**What**: Criar `marcos_execucao`; atualizar `adaptadores/persistencia/README.md`.
**Where**: `src/backend/central_preventiva/adaptadores/persistencia/migracoes/0008_marcos_execucao.sql`
**Depends on**: None
**Reuses**: convenção de migração numerada
**Requirement**: RUNNER-02

**Nota de implementação**: o Design nomeou a migração `0006`, mas as Histórias 2.5 (`0006_elegibilidade`) e sua correção (`0007`) já ocuparam esse espaço antes desta história começar — mesma situação já registrada em 2.4 e 2.5: os designs das 25 histórias foram escritos em lote antes da numeração sequencial real. Renumerada para `0008`, próximo número livre, mesmo conteúdo do Design.

**Done when**:

- [x] Migração aplica em transação própria, registrada em `schema_migracoes`
- [x] `README.md` documenta `marcos_execucao`
- [x] `testes/test_migracoes.py` cobre a aplicação da migração `0008`
- [x] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: integration
**Gate**: quick

---

### T2: Extensão de `RepositorioExecucaoPreventiva`

**What**: `listar_nao_terminais()` e `registrar_marco(execucao_id, marco, causa=None)`.
**Where**: `src/backend/central_preventiva/adaptadores/persistencia/repositorio_execucao_preventiva.py` (extensão de 2.2)
**Depends on**: T1
**Reuses**: `EstadoExecucao`/`ESTADOS_TERMINAIS` (AD-004)
**Requirement**: RUNNER-02, RUNNER-07

**Tools**: MCP: NONE — Skill: NONE

**Nota de implementação**: acrescentado também `listar_marcos(execucao_id) -> list[Marco]` (não pedido literalmente pelo Design, mas necessário para o `GET` de T4 e a reidratação de RUNNER-07 exibirem os marcos já persistidos).

**Done when**:

- [x] `listar_nao_terminais` retorna apenas execuções fora de `ESTADOS_TERMINAIS`
- [x] `registrar_marco` persiste marco com timestamp e causa opcional
- [x] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: integration
**Gate**: quick

---

### T3: `GerenciadorExecucoes`

**What**: `iniciar`, `continuar` (encadeia coleta→risco→elegibilidade, registra marco por transição, para em terminal ou `aguardando_geracao`), `retomar_pendentes`.
**Where**: `src/backend/central_preventiva/aplicacao/gerenciador_execucoes.py`
**Depends on**: T2
**Reuses**: `ServicoColetaMeteorologica` (2.1/2.2), `ServicoAvaliacaoRisco` (2.3), `ServicoAvaliacaoElegibilidade` (2.5), sem alteração de suas assinaturas
**Requirement**: RUNNER-01, RUNNER-02, RUNNER-03, RUNNER-04, RUNNER-07, RUNNER-08, RUNNER-09

**Tools**: MCP: NONE — Skill: NONE

**Nota de implementação (pré-requisito)**: `ServicoColetaMeteorologica.executar_coleta` (2.1/2.2) não aceita `execucao_id` e nunca devolve o `EventoMeteorologico` no sucesso — só transiciona uma execução própria criada de forma preguiçosa na falha (RESIL-06). Alterar sua assinatura quebraria 13+ chamadores/testes já verificados PASS em 2.1/2.2. Em vez disso, foi adicionado um método novo e aditivo, `coletar_para_execucao(execucao_id, versao_esperada, area) -> EventoMeteorologico | None`, que reaproveita os mesmos helpers internos (`ColetorComRetry`, `_fechar`, `_causa_de`) e opera sobre uma execução já existente — nunca cria a sua própria. `executar_coleta` não foi tocado; sua suíte de 19 testes continua passando.

**Nota de implementação (terminal técnico)**: confirmado por `testes/test_estados_execucao.py::test_enum_cobre_exatamente_os_estados_canonicos_do_ad4` que o conjunto de `EstadoExecucao` é guardado por um teste que trava qualquer valor novo — a Tech Decision do Design ("nenhum novo estado, reusar o padrão de estado terminal com causa") é, portanto, testada e obrigatória, não uma sugestão a ser substituída (diferente de outras divergências design-vs-spec resolvidas nas histórias anteriores). `GerenciadorExecucoes._registrar_falha_processamento` reusa `falhou_coleta` como o único terminal técnico de toda a cadeia determinística (coleta, risco ou elegibilidade); a causa registrada no marco sempre nomeia a exceção real, então o nome do estado não é ambíguo na prática.

**Nota de implementação (retomada de `coletando`)**: não existe coluna `area_id` em `execucao_preventiva`, então `retomar_pendentes()` não tem como reobter a área monitorada de uma execução presa em `coletando` no boot. Como a coleta já é conhecidamente síncrona ponta a ponta (limitação registrada desde 2.1/2.2, item 6 dos Blockers em `.specs/STATE.md`) e o Teste Independente da spec só cobre retomada a partir de `avaliando_elegibilidade`, uma execução em `coletando` no boot é tratada como falha técnica imediata (`falhou_coleta`, causa explicando o reinício) em vez de deixada presa (RUNNER-11).

**Done when**:

- [x] Coleta válida com evento relevante e público elegível avança sozinha até `aguardando_geracao`, com marco `publico_elegivel_formado` persistido
- [x] Evento não relevante para em `sem_risco` sem chamar avaliação de elegibilidade
- [x] Evento relevante sem elegíveis para em `sem_elegiveis`
- [x] Nenhum dos dois terminais antecipados chama qualquer porta de IA
- [x] Falha interna não recuperável simulada (exceção não tratada de um dos serviços) resulta em terminal técnico explícito com causa e último marco durável, não em travamento
- [x] `retomar_pendentes` com uma execução persistida em `avaliando_elegibilidade` retoma sem recriar evento nem recalcular elegibilidade já persistida
- [x] Repetir `iniciar` com a mesma `Idempotency-Key` devolve o `execucao_id` já criado
- [x] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: unit
**Gate**: quick

---

### T4: Endpoint HTTP de início/consulta da execução

**What**: `POST /api/v1/execucoes` (idempotente, `202`) e `GET /api/v1/execucoes/{id}` (estado, marcos, prévia do público quando `aguardando_geracao`).
**Where**: `src/backend/central_preventiva/adaptadores/http/execucao_preventiva.py`
**Depends on**: T3
**Reuses**: padrão de roteador existente
**Requirement**: RUNNER-04, RUNNER-08

**Tools**: MCP: NONE — Skill: NONE

**Nota de implementação**: `RepositorioExecucaoPreventiva.obter` (2.2) assume que a execução existe (`assert`) — adequado para chamadores internos que acabaram de criar/ler a linha, mas não para um `execucao_id` vindo de uma URL externa. Adicionado `buscar(execucao_id) -> SnapshotExecucao | None`, sem alterar `obter`.

**Done when**:

- [x] `POST` sem `Idempotency-Key` retorna erro `application/problem+json`
- [x] `POST` com chave nova retorna `202` com `execucao_id`
- [x] `GET` reflete estado, marcos e, quando `aguardando_geracao`, quantidade total + prévia do público
- [x] `openapi.json` regenerado, `test_openapi_sincronizado.py` verde
- [x] Gate check passa: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright`

**Tests**: integration
**Gate**: full

---

### T5: Wiring do lifespan — retomada no boot

**What**: `composicao/api.py` chama `GerenciadorExecucoes.retomar_pendentes()` uma vez no `lifespan`, antes do `AgendadorMeteorologico` (2.1) iniciar.
**Where**: `src/backend/central_preventiva/composicao/api.py` (extensão)
**Depends on**: T4
**Reuses**: `lifespan` já existente (2.1, T10), AD-006
**Requirement**: RUNNER-07

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] Uma execução não terminal persistida antes do boot é retomada automaticamente ao iniciar o servidor
- [x] Ordem de inicialização documentada (retomada antes do agendador de coleta)
- [x] Gate check passa: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright`

**Tests**: integration
**Gate**: full

---

### T6: Superfície de acompanhamento da execução

**What**: Componente que distingue etapas concluídas, etapa corrente, encerramento e exceção por texto+ícone+traço, com anúncio acessível em mudanças de estado importantes/terminais.
**Where**: `src/frontend/src/funcionalidades/execucao/SuperficieExecucao.tsx`
**Depends on**: T5
**Reuses**: cliente HTTP central, `SuperficieEventoDecisao` (2.3/2.5) para a prévia do público
**Requirement**: RUNNER-03, RUNNER-04, RUNNER-09

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Progresso reflete os marcos reais retornados pela API, sem recalcular no frontend
- [ ] Mudança para estado terminal ou `aguardando_geracao` é anunciada de forma acessível (`aria-live` ou equivalente)
- [ ] `npm run gerar-tipos-api --prefix src/frontend` executado; tipos atualizados
- [ ] Gate check passa: `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`

**Tests**: unit
**Gate**: full

**Commit**: `feat(execucao): orquestrar coleta risco e elegibilidade ate o checkpoint de geracao`

---

## Phase Execution Map

```
Phase 1:  T1 → T2
Phase 2:  T3
Phase 3:  T4 → T5
Phase 4:  T6
```

Grafo completo de dependências:

```
T1 → T2
T2 → T3
T3 → T4
T4 → T5
T5 → T6
```

---

## Task Granularity Check

| Task | Scope | Status |
| --- | --- | --- |
| T1: Migração `0006` | 1 arquivo `.sql` + doc | ✅ Granular |
| T2: Extensão do repositório | 1 arquivo, extensão coesa | ✅ Granular |
| T3: `GerenciadorExecucoes` | 1 componente | ✅ Granular |
| T4: Endpoint HTTP | 1 componente | ✅ Granular |
| T5: Wiring do lifespan | 1 arquivo | ✅ Granular |
| T6: Superfície de acompanhamento | 1 componente | ✅ Granular |

---

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| --- | --- | --- | --- |
| T1 | None | — | ✅ Match |
| T2 | T1 | T1 → T2 | ✅ Match |
| T3 | T2 | T2 → T3 (grafo completo) | ✅ Match |
| T4 | T3 | T3 → T4 (grafo completo) | ✅ Match |
| T5 | T4 | T4 → T5 | ✅ Match |
| T6 | T5 | T5 → T6 (grafo completo) | ✅ Match |

**Rules confirmed**: toda dependência aponta para trás ou dentro da mesma fase.

---

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| --- | --- | --- | --- | --- |
| T1: Migração `0006` | Migração/schema | integration | integration | ✅ OK |
| T2: Extensão do repositório | Repositório | integration | integration | ✅ OK |
| T3: `GerenciadorExecucoes` | Aplicação (orquestrador) | unit | unit | ✅ OK |
| T4: Endpoint HTTP | Roteador HTTP | integration | integration | ✅ OK |
| T5: Wiring do lifespan | Integração/composição | integration | integration | ✅ OK |
| T6: Superfície de acompanhamento | Componente React | unit | unit | ✅ OK |

**Rules confirmed**: nenhum `Tests: none` nesta história; nenhuma task adia teste.
