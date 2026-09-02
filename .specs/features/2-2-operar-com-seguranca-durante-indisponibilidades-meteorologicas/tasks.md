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

**What**: Criar `tentativas_coleta_meteorologica`, `excecoes_operacionais`, `cenarios_sinteticos_ativados`, e adicionar `UNIQUE(tipo, area, periodo_inicio, periodo_fim)` a `eventos_meteorologicos` por recreate-and-copy na mesma transação (AD-015 — DuckDB não suporta `ALTER ADD CONSTRAINT`); atualizar `adaptadores/persistencia/README.md`.
**Where**: `src/backend/central_preventiva/adaptadores/persistencia/migracoes/0003_resiliencia_meteorologica.sql`
**Depends on**: None
**Reuses**: convenção de `0001_schema_inicial.sql`/`0002_meteorologia.sql`
**Requirement**: RESIL-06, RESIL-13

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] Migração aplica em transação própria, registrada em `schema_migracoes`
- [x] `eventos_meteorologicos` é recriada por recreate-and-copy (`CREATE` nova com a `UNIQUE` declarada → `INSERT ... SELECT` → `DROP` → `RENAME`), preservando todas as linhas existentes (AD-015)
- [x] Teste cobre `INSERT ... ON CONFLICT DO NOTHING` sobre a `UNIQUE` recriada — o insert-or-noop (AD-010) funciona na tabela resultante
- [x] `README.md` documenta as três tabelas novas e a `UNIQUE` adicionada (com a estratégia de recreate registrada)
- [x] `testes/test_migracoes.py` cobre a aplicação da migração `0003`
- [x] Gate check passa: `uv run --directory src/backend pytest`

**Nota de implementação**: a `UNIQUE` nova quebrava imediatamente `RepositorioEventosMeteorologicos.salvar` (2.1), que fazia `INSERT` simples — fixtures de teste reusam os mesmos campos-chave entre chamadas. Corrigido nesta task (não em T5) para manter o gate verde entre tasks: `salvar` passou a usar `INSERT ... ON CONFLICT DO NOTHING` (AD-010), efeito colateral direto e inevitável de adicionar a constraint.

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

- [x] `criar` insere com `versao = 1` e o estado inicial informado
- [x] `transicionar` com `versao_esperada` correta atualiza estado e incrementa versão
- [x] `transicionar` com `versao_esperada` incorreta levanta `ConflitoVersao` sem mutar a linha
- [x] `transicionar` a partir de um estado terminal levanta `TransicaoInvalida`
- [x] Gate check passa: `uv run --directory src/backend pytest`

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

- [x] Sucesso na 1ª tentativa não aguarda backoff nem tenta de novo
- [x] Falha na 1ª e 2ª tentativa, sucesso na 3ª: 3 tentativas registradas, backoff 1s depois 2s (dublê de tempo, sem espera real)
- [x] 3 falhas consecutivas: 3 tentativas registradas, resultado final de falha propagado ao chamador
- [x] Cada tentativa registrada tem número, início, término e código do resultado
- [x] Nenhum teste depende de tempo real ou rede
- [x] Gate check passa: `uv run --directory src/backend pytest`

**Nota de implementação**: `RepositorioTentativasColeta`/`TentativaColeta`/`CodigoResultadoTentativa` (porta em `aplicacao/portas_meteorologia.py`, implementação em `adaptadores/persistencia/repositorio_meteorologia.py`) não tinham T-número próprio no plano — criados aqui por serem dependência direta de `ColetorComRetry`, conforme a Location já designada no `design.md`. `RetentativasEsgotadas` (exceção dedicada) é levantada de forma uniforme ao esgotar as 3 tentativas, seja por timeout/erro de transporte ou por status HTTP de erro — dá a T5 um único sinal para transicionar a execução a `falhou_coleta`, distinto do caminho de rejeição de conteúdo (1 tentativa bem-sucedida em HTTP mas malformada), que continua sendo tratado pelo normalizador de 2.1 sem tocar `execucao_preventiva`.

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

- [x] Devolve resposta bruta determinística de um cenário sintético existente
- [x] Normalizado pelo `NormalizadorInmet` de 2.1, resulta em `proveniencia = sintetico`
- [x] Gate check passa: `uv run --directory src/backend pytest`

**Nota de implementação**: o período do payload usa o horário corrente (`agora`, injetável) em vez dos valores históricos literais de `semeador.py` (`2026-03-12 14h–20h`) — reproduzi-los ativaria sempre a mesma `UNIQUE(tipo, area, periodo_inicio, periodo_fim)` (T1) já ocupada pelo evento semeado, e o `ON CONFLICT DO NOTHING` faria a ativação do cenário nunca produzir um evento novo visível durante a demonstração.

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

- [x] 3 falhas consecutivas transicionam a execução a `falhou_coleta` com `Exceção` (causa, tentativas, impacto) registrada
- [x] Snapshot anterior continua consultável, sem disparar nova avaliação de risco
- [x] `solicitar_nova_tentativa` cria execução nova em `coletando`, correlacionada, sem reabrir a execução terminal anterior
- [x] Repetir `solicitar_nova_tentativa` com a mesma `Idempotency-Key` não duplica a nova coleta
- [x] `ativar_cenario_sintetico` cria coleta separada com `proveniencia = sintetico`, nunca combinada a `real_inmet`
- [x] Recuperação real após falha/sintético não duplica evento já persistido (via `UNIQUE` de T1)
- [x] Gate check passa: `uv run --directory src/backend pytest`

**Nota de implementação**: cada coleta esgotada (manual, automática ou nova tentativa) cria e fecha sua própria `ExecucaoPreventiva` — a 2.6 ainda não existe para orquestrar um ciclo já em andamento, então esta história não pressupõe uma execução criada antes da falha (achado A5 do parecer independente permanece registrado em `STATE.md` para quando 2.6 unificar o ciclo). `PortasColetaMeteorologica` ganhou `tentativas`/`execucoes`/`excecoes`/`cenario_sintetico`/`cenarios_ativados`/`esperar` — todos os 3 call sites existentes (produção em `montar_portas_coleta`, e os dois arquivos de teste de 2.1) foram atualizados. `RepositorioSincronizacoes.buscar_por_id` (novo `# SPEC_DEVIATION`) resolve a área da sincronização de origem para `solicitar_nova_tentativa`. O teste de deduplicação por `UNIQUE` (T1) usa repositórios DuckDB reais em vez dos dublês em memória do resto do arquivo, porque os dublês não enforçam a constraint.

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

- [x] Nova tentativa sem `Idempotency-Key` retorna erro `application/problem+json`
- [x] Nova tentativa com chave nova retorna `202`; repetição da chave devolve a resposta registrada
- [x] Ativação de cenário sintético segue o mesmo contrato de idempotência
- [x] `GET /api/v1/meteorologia/sincronizacoes` reflete tentativa atual e limite de 3
- [x] Gate check passa: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright`

**Nota de implementação**: `RespostaSincronizacao` ganhou `tentativas`/`limite_tentativas`; `RepositorioSincronizacoes.buscar_por_id` (T5) alimenta o erro 404 de nova tentativa. Os testes de nova tentativa esgotam 3 tentativas reais via `httpx.AsyncClient.send` monkeypatched (sem clock injetável no `montar_portas_coleta` de produção) — custo aceito de ~3,3s por teste (3 testes, ~10s no total), preferível a introduzir uma configuração de teste na composição de produção sem AC que a peça. Contrato OpenAPI regenerado (`openapi_export`).

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

- [x] Os seis estados são visualmente distinguíveis (texto + ícone + cor, não só cor)
- [x] Cada estado mostra somente ações seguras e aplicáveis a ele
- [x] `npm run gerar-tipos-api --prefix src/frontend` executado; tipos atualizados
- [x] Gate check passa: `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`

**Nota de implementação**: `calcularEstadoFonte(historico, eventos)` (função pura, exportada e testada isoladamente) deriva os 6 estados só de dados já persistidos, sem estado especulativo: `em_tentativa`/`indisponivel` do `estado` da última sincronização, `sintetica` do `proveniencia` do evento mais recente, `recuperada` quando a última concluiu logo após uma falha, `degradada` quando precisou de mais de uma tentativa, `operacional` no default (inclui "nunca coletou"). Ações seguras por estado: `indisponivel` oferece nova tentativa E ativar cenário sintético; `sintetica` oferece só nova tentativa (reativar o mesmo cenário seria redundante); os demais não oferecem ação. `ativar_cenario_sintetico` exigia `area_id`, que a superfície não tinha como obter — `RespostaSincronizacao` ganhou `area_monitorada_id` (extensão retroativa mínima do contrato de T6, mesmo padrão de adicionar campo já usado para `tentativas`/`limite_tentativas`). Tipos gerados a partir do `openapi.json` local (sem precisar do backend no ar) via `openapi-typescript ../backend/.../openapi.json -o src/api/tipos-gerados.ts`, equivalente ao `gerar-tipos-api` contra um servidor ao vivo. Verificado manualmente: backend+frontend reais no ar, ciclo completo `ativar_cenario_sintetico` → `GET /sincronizacoes` → `GET /eventos` conferido campo a campo, módulo do componente compilado pelo Vite sem erro; banco de desenvolvimento restaurado ao final.

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
