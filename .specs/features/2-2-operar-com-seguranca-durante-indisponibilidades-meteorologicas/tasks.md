# História 2.2: Operar com segurança durante indisponibilidades meteorológicas — Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/2-2-operar-com-seguranca-durante-indisponibilidades-meteorologicas/design.md`
**Status**: Approved

---

## Test Coverage Matrix

> Gerada por amostragem do código (mesma base de 2.1) e dos ACs desta história. Guidelines: `AGENTS.md`, `README.md` — nenhum threshold dedicado; defaults fortes aplicados, piso em `testes/test_sonda_inmet.py` (dublê de tempo), `testes/test_repositorio_execucoes.py` (versionamento otimista).

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| Migração `0003_resiliencia_meteorologica.sql` | integration | Aplicação da migração e forma das tabelas novas | `testes/test_migracoes.py` | `uv run --directory src/backend pytest` |
| `RepositorioExecucaoPreventiva` | integration | Criar/obter/transicionar, incluindo `ConflitoVersao` e `TransicaoInvalida` sobre estado terminal | `testes/test_repositorio_execucao_preventiva.py` | `uv run --directory src/backend pytest` |
| `RepositorioTentativasColeta` / `RepositorioExcecoesOperacionais` | integration | Registrar e listar tentativas; registrar exceção | `testes/test_repositorio_meteorologia.py` (estendido) | `uv run --directory src/backend pytest` |
| `ColetorComRetry` | unit | Todos os branches; 1:1 com `RESIL-01..05`; recuperação em cada tentativa, esgotamento das 3, backoff exato com dublê de tempo, sem `asyncio.sleep` real | `testes/test_coletor_com_retry.py` | `uv run --directory src/backend pytest` |
| `AdaptadorCenarioSintetico` | unit | Proveniência `sintetico`, dados do cenário demonstrativo | `testes/test_adaptador_cenario_sintetico.py` | `uv run --directory src/backend pytest` |
| `ServicoColetaMeteorologica` (extensão) | unit | Todos os branches; 1:1 com `RESIL-06..14`; nova tentativa após `falhou_coleta`, ativação sintética, recuperação sem duplicar, idempotência | `testes/test_coleta_meteorologica.py` (estendido) | `uv run --directory src/backend pytest` |
| Roteador HTTP (extensão de `meteorologia`) | integration | Nova rota de nova tentativa + ativação de cenário sintético: caminho feliz + erro + idempotência | `testes/test_meteorologia_api.py` (estendido) | `uv run --directory src/backend pytest` |
| Contrato OpenAPI | integration | Sincronia com as rotas novas | `testes/test_openapi_sincronizado.py` | `uv run --directory src/backend pytest` |
| Cliente API do frontend (extensão) | unit | Nova tentativa, ativação sintética, estados da fonte | `src/frontend/src/api/meteorologia.test.ts` (estendido) | `npm test --prefix src/frontend -- --run` |
| Superfície "Fonte meteorológica" (extensão) | unit | Seis estados (`Operacional`…`Recuperada`) distinguíveis, ações por estado | `SuperficieFonteMeteorologica.test.tsx` (estendido) | `npm test --prefix src/frontend -- --run` |

## Gate Check Commands

| Gate Level | When to Use | Command |
| --- | --- | --- |
| Quick (backend) | Tasks de domínio/aplicação/adaptador isoladas | `uv run --directory src/backend pytest` |
| Quick (frontend) | Tasks de componente/cliente API isoladas | `npm test --prefix src/frontend -- --run` |
| Full (backend) | Tasks que tocam roteador HTTP ou schema | `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright` |
| Full (frontend) | Tasks que tocam a superfície visível | `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend` |
| Build (fim de fase / OpenAPI) | Fim de fase, ou config/contrato | Backend: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright` — Frontend: `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend` (paralelizáveis) |

---

## Execution Plan

### Phase 1: Schema e execução preventiva

```
T1 → T2
```

### Phase 2: Retry, snapshot e cenário sintético

T3 e T4 são independentes entre si (T3 depende de T2, da Fase 1; T4 não depende de nada). Execução em ordem T3, T4; nenhuma aresta intra-fase a desenhar.

```
T3
T4
```

### Phase 3: Caso de uso e API

```
T5 → T6
```

### Phase 4: Frontend

```
T7
```

---

## Task Breakdown

### T1: Migração `0003_resiliencia_meteorologica.sql`

**What**: Criar `tentativas_coleta_meteorologica`, `excecoes_operacionais`, `cenarios_sinteticos_ativados`, e adicionar `UNIQUE(tipo, area, periodo_inicio, periodo_fim)` a `eventos_meteorologicos`; atualizar `adaptadores/persistencia/README.md`.
**Where**: `src/backend/central_preventiva/adaptadores/persistencia/migracoes/0003_resiliencia_meteorologica.sql`
**Depends on**: None
**Reuses**: convenção de `0001_schema_inicial.sql`/`0002_meteorologia.sql`
**Requirement**: RESIL-06, RESIL-13

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Migração aplica em transação própria, registrada em `schema_migracoes`
- [ ] `README.md` documenta as três tabelas novas e a `UNIQUE` adicionada
- [ ] `testes/test_migracoes.py` cobre a aplicação da migração `0003`
- [ ] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: integration
**Gate**: quick

---

### T2: `RepositorioExecucaoPreventiva`

**What**: `criar`, `obter`, `transicionar` (com `versao_esperada` e checagem de `eh_terminal`) sobre a tabela `execucao_preventiva`.
**Where**: `src/backend/central_preventiva/adaptadores/persistencia/repositorio_execucao_preventiva.py`
**Depends on**: T1
**Reuses**: `dominio/estados_execucao.py`, padrão de `repositorio_execucoes.py`
**Requirement**: RESIL-08

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] `criar` insere com `versao = 1` e o estado inicial informado
- [ ] `transicionar` com `versao_esperada` correta atualiza estado e incrementa versão
- [ ] `transicionar` com `versao_esperada` incorreta levanta `ConflitoVersao` sem mutar a linha
- [ ] `transicionar` a partir de um estado terminal levanta `TransicaoInvalida`
- [ ] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: integration
**Gate**: quick

---

### T3: `ColetorComRetry`

**What**: Wrapper de retry (3 tentativas, backoff 1s/2s/4s, timeout de cada tentativa herdado do coletor delegado) implementando `ColetorMeteorologico`, registrando cada tentativa via `RepositorioTentativasColeta`.
**Where**: `src/backend/central_preventiva/aplicacao/coleta_meteorologica.py` (extensão)
**Depends on**: T2
**Reuses**: `ColetorMeteorologico` (porta de 2.1), padrão de relógio/espera injetável de `SondaInmet`
**Requirement**: RESIL-01, RESIL-02, RESIL-03, RESIL-04, RESIL-05

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Sucesso na 1ª tentativa não aguarda backoff nem tenta de novo
- [ ] Falha na 1ª e 2ª tentativa, sucesso na 3ª: 3 tentativas registradas, backoff 1s depois 2s (dublê de tempo, sem espera real)
- [ ] 3 falhas consecutivas: 3 tentativas registradas, resultado final de falha propagado ao chamador
- [ ] Cada tentativa registrada tem número, início, término e código do resultado
- [ ] Nenhum teste depende de tempo real ou rede
- [ ] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: unit
**Gate**: quick

---

### T4: `AdaptadorCenarioSintetico`

**What**: Implementação de `ColetorMeteorologico` que devolve dados de um cenário sintético do conjunto demonstrativo do Épico 1.
**Where**: `src/backend/central_preventiva/adaptadores/meteorologia/adaptador_cenario_sintetico.py`
**Depends on**: None
**Reuses**: mesma porta de `ClienteInmet`/`AdaptadorInmetFalso` (2.1)
**Requirement**: RESIL-10, RESIL-11

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Devolve resposta bruta determinística de um cenário sintético existente
- [ ] Normalizado pelo `NormalizadorInmet` de 2.1, resulta em `proveniencia = sintetico`
- [ ] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: unit
**Gate**: quick

---

### T5: Extensão de `ServicoColetaMeteorologica` — retry, falha terminal, contingência

**What**: Injeta `ColetorComRetry` no lugar do coletor de tentativa única; adiciona `ativar_cenario_sintetico`, `solicitar_nova_tentativa` (cria execução correlacionada nova após `falhou_coleta`); na falha esgotada, transiciona a execução a `falhou_coleta` e registra `Exceção`.
**Where**: `src/backend/central_preventiva/aplicacao/coleta_meteorologica.py` (extensão)
**Depends on**: T3, T4
**Reuses**: `RepositorioExecucaoPreventiva` (T2), `RepositorioExcecoesOperacionais`, idempotência genérica (AD-002)
**Requirement**: RESIL-06, RESIL-07, RESIL-08, RESIL-09, RESIL-10, RESIL-11, RESIL-12, RESIL-14

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] 3 falhas consecutivas transicionam a execução a `falhou_coleta` com `Exceção` (causa, tentativas, impacto) registrada
- [ ] Snapshot anterior continua consultável, sem disparar nova avaliação de risco
- [ ] `solicitar_nova_tentativa` cria execução nova em `coletando`, correlacionada, sem reabrir a execução terminal anterior
- [ ] Repetir `solicitar_nova_tentativa` com a mesma `Idempotency-Key` não duplica a nova coleta
- [ ] `ativar_cenario_sintetico` cria coleta separada com `proveniencia = sintetico`, nunca combinada a `real_inmet`
- [ ] Recuperação real após falha/sintético não duplica evento já persistido (via `UNIQUE` de T1)
- [ ] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: unit
**Gate**: quick

---

### T6: Extensão do roteador HTTP `meteorologia`

**What**: `POST /api/v1/meteorologia/{sincronizacao_id}/nova-tentativa` e `POST /api/v1/meteorologia/cenarios-sinteticos/{identificador}/ativar`, ambos exigindo `Idempotency-Key`; `GET /api/v1/meteorologia/sincronizacoes` passa a incluir tentativas e estado atual.
**Where**: `src/backend/central_preventiva/adaptadores/http/meteorologia.py` (extensão)
**Depends on**: T5
**Reuses**: padrão de roteador de 2.1, fixture `autouse` de bloqueio de rede real
**Requirement**: RESIL-08, RESIL-10, RESIL-15, RESIL-16

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Nova tentativa sem `Idempotency-Key` retorna erro `application/problem+json`
- [ ] Nova tentativa com chave nova retorna `202`; repetição da chave devolve a resposta registrada
- [ ] Ativação de cenário sintético segue o mesmo contrato de idempotência
- [ ] `GET /api/v1/meteorologia/sincronizacoes` reflete tentativa atual e limite de 3
- [ ] Gate check passa: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright`

**Tests**: integration
**Gate**: full

---

### T7: Frontend — seis estados da fonte meteorológica

**What**: Estender `SuperficieFonteMeteorologica` (2.1) e `src/api/meteorologia.ts` para distinguir `Operacional`, `Em tentativa`, `Degradada`, `Indisponível`, `Sintética`, `Recuperada` por texto/ícone/cor, com ações por estado e botões de nova tentativa/ativação sintética.
**Where**: `src/frontend/src/funcionalidades/fonte-meteorologica/SuperficieFonteMeteorologica.tsx` (extensão)
**Depends on**: T6
**Reuses**: componente de 2.1, padrão de `SuperficieProntidao.tsx` para múltiplos estados
**Requirement**: RESIL-15, RESIL-16

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Os seis estados são visualmente distinguíveis (texto + ícone + cor, não só cor)
- [ ] Cada estado mostra somente ações seguras e aplicáveis a ele
- [ ] `npm run gerar-tipos-api --prefix src/frontend` executado; tipos atualizados
- [ ] Gate check passa: `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`

**Tests**: unit
**Gate**: full

**Commit**: `feat(meteorologia): adicionar resiliencia e contingencia sintetica a coleta do INMET`

---

## Phase Execution Map

```
Phase 1:  T1 → T2
Phase 2:  T3   T4
Phase 3:  T5 → T6
Phase 4:  T7
```

Grafo completo de dependências:

```
T1 → T2
T2 → T3
T3 → T5
T4 → T5
T5 → T6
T6 → T7
```

(T4 não depende de nenhuma outra task; T5 depende de T3 e T4, ambas da Fase 2 — cruza fase, validado pela checagem de dependência para trás.)

---

## Task Granularity Check

| Task | Scope | Status |
| --- | --- | --- |
| T1: Migração `0003` | 1 arquivo `.sql` + doc | ✅ Granular |
| T2: `RepositorioExecucaoPreventiva` | 1 componente | ✅ Granular |
| T3: `ColetorComRetry` | 1 componente | ✅ Granular |
| T4: `AdaptadorCenarioSintetico` | 1 componente | ✅ Granular |
| T5: Extensão do caso de uso | 1 arquivo, mesma classe estendida | ✅ Granular |
| T6: Extensão do roteador | 1 arquivo | ✅ Granular |
| T7: Extensão da superfície | 1 componente | ✅ Granular |

---

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| --- | --- | --- | --- |
| T1 | None | — | ✅ Match |
| T2 | T1 | T1 → T2 | ✅ Match |
| T3 | T2 | T2 → T3 (cruza fase; grafo completo confirma) | ✅ Match |
| T4 | None | — | ✅ Match |
| T5 | T3, T4 | T3 → T5, T4 → T5 (cruza fase; grafo completo confirma) | ✅ Match |
| T6 | T5 | T5 → T6 | ✅ Match |
| T7 | T6 | T6 → T7 (cruza fase; grafo completo confirma) | ✅ Match |

**Rules confirmed**: toda dependência aponta para trás ou dentro da mesma fase.

---

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| --- | --- | --- | --- | --- |
| T1: Migração `0003` | Migração/schema | integration | integration | ✅ OK |
| T2: `RepositorioExecucaoPreventiva` | Repositório | integration | integration | ✅ OK |
| T3: `ColetorComRetry` | Aplicação | unit | unit | ✅ OK |
| T4: `AdaptadorCenarioSintetico` | Adaptador | unit | unit | ✅ OK |
| T5: Extensão do caso de uso | Aplicação | unit | unit | ✅ OK |
| T6: Extensão do roteador | Roteador HTTP | integration | integration | ✅ OK |
| T7: Extensão da superfície | Componente React | unit | unit | ✅ OK |

**Rules confirmed**: nenhum `Tests: none` nesta história; nenhuma task adia teste.
