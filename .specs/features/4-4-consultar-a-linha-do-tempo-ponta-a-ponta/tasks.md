# História 4.4: Consultar a linha do tempo ponta a ponta — Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/4-4-consultar-a-linha-do-tempo-ponta-a-ponta/design.md`
**Status**: Approved

---

## Test Coverage Matrix

> Guidelines: `AGENTS.md`, `README.md`; piso em `testes/test_consolidacao_resultados.py` (4.1, agregação multi-fonte) e `testes/test_detalhe_resultado.py` (4.2, junção read-only).

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| `ServicoLinhaDoTempo.montar` | unit | Todos os branches; 1:1 com `TIMELINE-01..07`; fluxo completo, encerramentos antecipados, múltiplas tentativas, navegação correlacionada, visualização única | `testes/test_linha_do_tempo.py` | `uv run --directory src/backend pytest` |
| `ServicoLinhaDoTempo.buscar_execucoes` | unit | Todos os branches; 1:1 com `TIMELINE-08..09`; filtros combináveis, resultado vazio | `testes/test_linha_do_tempo.py` | `uv run --directory src/backend pytest` |
| Roteador HTTP (linha do tempo e busca) | integration | `GET` linha do tempo + `GET` lista filtrada: caminho feliz + execução inexistente + filtro vazio | `testes/test_linha_do_tempo_api.py` | `uv run --directory src/backend pytest` |
| Contrato OpenAPI | integration | Sincronia com as rotas novas | `testes/test_openapi_sincronizado.py` | `uv run --directory src/backend pytest` |
| Superfície da linha do tempo | unit | Localização temporal, agrupamento por mensagem, navegação por teclado/leitor de tela, rolagem interna acessível | `SuperficieLinhaDoTempo.test.tsx` | `npm test --prefix src/frontend -- --run` |

## Gate Check Commands

| Gate Level | When to Use | Command |
| --- | --- | --- |
| Quick (backend) | Tasks isoladas de aplicação | `uv run --directory src/backend pytest` |
| Quick (frontend) | Tasks isoladas de componente | `npm test --prefix src/frontend -- --run` |
| Full (backend) | Tasks de roteador HTTP | `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright` |
| Full (frontend) | Tasks de superfície visível | `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend` |
| Build (fim de fase) | Fim de fase / contrato | Backend + Frontend em paralelo, mesmos comandos acima |

---

## Execution Plan

### Phase 1: Agregação

```
T1 → T2
```

### Phase 2: API e frontend

```
T3 → T4
```

---

## Task Breakdown

### T1: `ServicoLinhaDoTempo.montar`

**What**: Agrega marcos de todas as fontes (2.1–2.6, 3.1–3.6, 4.3) por `execucao_id`, normaliza para `MarcoLinhaDoTempo`, ordena por `timestamp`, inclui a cadeia origem↔retentativas.
**Where**: `src/backend/central_preventiva/aplicacao/linha_do_tempo.py`
**Depends on**: None
**Reuses**: todos os repositórios de meteorologia (2.1/2.2), risco (2.3), elegibilidade (2.5), mensagens/críticas/decisões (3.2/3.3/3.5), exceções (2.2/3.4), entregas/visualizações (3.6/4.3)
**Requirement**: TIMELINE-01, TIMELINE-02, TIMELINE-03, TIMELINE-04, TIMELINE-05, TIMELINE-06, TIMELINE-07

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] Execução completa (coleta→simulação→visualização) retorna todos os marcos na ordem cronológica correta, cada um com data/hora, ator, ação, resultado, correlação
- [x] Execução `sem_risco`/`sem_elegiveis` retorna só os marcos até o terminal, sem etapa de geração/crítica/simulação
- [x] Mensagem com 3 tentativas retorna as 3 versões/avaliações/motivos na ordem correta, ligados à mensagem e à execução
- [x] Execução correlacionada inclui `execucao_origem_id` e a lista de retentativas conhecidas, sem misturar marcos entre execuções
- [x] Comunicado reaberto 3 vezes (dado de teste com múltiplas chamadas a 4.3) resulta em exatamente um marco de visualização na linha do tempo
- [x] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: unit
**Gate**: quick

---

### T2: `ServicoLinhaDoTempo.buscar_execucoes`

**What**: Busca execuções filtrando por segurado sintético, canal e/ou estado (todos opcionais, combináveis), sem efeito colateral.
**Where**: `src/backend/central_preventiva/aplicacao/linha_do_tempo.py` (mesmo arquivo de T1)
**Depends on**: T1
**Reuses**: `RepositorioElegibilidades` (2.5), `RepositorioMensagens` (3.2), `RepositorioExecucaoPreventiva` (2.2)
**Requirement**: TIMELINE-08, TIMELINE-09

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] Filtro por canal retorna só execuções com mensagem nesse canal
- [x] Filtro por segurado retorna só execuções com esse segurado no público elegível
- [x] Nenhuma chamada de busca altera qualquer dado
- [x] Filtro sem resultado retorna lista vazia (não erro)
- [x] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: unit
**Gate**: quick

---

### T3: Endpoints HTTP — linha do tempo e busca de execuções

**What**: `GET /api/v1/execucoes/{id}/linha-do-tempo` e `GET /api/v1/execucoes?segurado=&canal=&estado=`.
**Where**: `src/backend/central_preventiva/adaptadores/http/linha_do_tempo.py`
**Depends on**: T2
**Reuses**: padrão de roteador existente
**Requirement**: TIMELINE-01, TIMELINE-08, TIMELINE-09

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] `200` com a linha do tempo completa para execução existente
- [ ] `404` para execução inexistente
- [ ] Busca filtrada retorna só os resultados correspondentes; sem filtro retorna todas
- [ ] `openapi.json` regenerado, `test_openapi_sincronizado.py` verde
- [ ] Gate check passa: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright`

**Tests**: integration
**Gate**: full

---

### T4: Superfície da linha do tempo

**What**: Lista de execuções com busca/filtro + linha do tempo expansível por marco, agrupada por mensagem, com horários localizados (valor UTC canônico disponível), navegação por teclado/leitor de tela e rolagem interna acessível.
**Where**: `src/frontend/src/funcionalidades/linha-do-tempo/SuperficieLinhaDoTempo.tsx`
**Depends on**: T3
**Reuses**: cliente HTTP central, padrão de `SuperficieExecucao` (2.6) para estados/marcos
**Requirement**: TIMELINE-02, TIMELINE-10, TIMELINE-11

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Marcos agrupados visualmente por mensagem, mantendo a ordem cronológica geral entre grupos
- [ ] Horário exibido localizado, com o valor UTC canônico acessível (ex.: `title`/tooltip)
- [ ] Navegação por teclado anuncia ordem/agrupamento/estado expandido; rolagem interna com nome acessível quando presente
- [ ] Resultado vazio de busca explicado por texto, sem paginação/filtro fora do escopo
- [ ] `npm run gerar-tipos-api --prefix src/frontend` executado; tipos atualizados
- [ ] Gate check passa: `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`

**Tests**: unit
**Gate**: full

**Commit**: `feat(linha-do-tempo): adicionar cronologia ponta a ponta e busca de execucoes`

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
| T1: `montar` | 1 método, arquivo novo | ✅ Granular |
| T2: `buscar_execucoes` | 1 método, mesmo arquivo de T1 | ✅ Granular |
| T3: Endpoints de linha do tempo/busca | 1 componente | ✅ Granular |
| T4: Superfície da linha do tempo | 1 componente | ✅ Granular |

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
| T1: `montar` | Aplicação | unit | unit | ✅ OK |
| T2: `buscar_execucoes` | Aplicação | unit | unit | ✅ OK |
| T3: Endpoints de linha do tempo/busca | Roteador HTTP | integration | integration | ✅ OK |
| T4: Superfície da linha do tempo | Componente React | unit | unit | ✅ OK |

**Rules confirmed**: nenhum `Tests: none` nesta história; nenhuma task adia teste.
