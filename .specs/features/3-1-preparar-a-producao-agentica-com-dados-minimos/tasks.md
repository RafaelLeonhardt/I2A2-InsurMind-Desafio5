# História 3.1: Preparar a produção agêntica com dados mínimos — Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/3-1-preparar-a-producao-agentica-com-dados-minimos/design.md`
**Status**: Approved

---

## Test Coverage Matrix

> Guidelines: `AGENTS.md`, `README.md`; piso em `testes/test_sonda_openai.py` (Épico 1, chamada real sem expor chave) e `testes/test_coleta_meteorologica.py` (2.2, retry com dublê de tempo).

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| Migração `0007_preflight_ia.sql` | integration | Aplicação, coluna nova, tabela nova | `testes/test_migracoes.py` | `uv run --directory src/backend pytest` |
| `RetryComBackoff[T]` (extração genérica) | unit | Mesmo comportamento observável de `ColetorComRetry` (2.2), sem regressão | `testes/test_retry_com_backoff.py` | `uv run --directory src/backend pytest` |
| `VerificadorDisponibilidadeOpenAI` | unit | Disponível, indisponível (401/429/5xx/timeout), nunca expõe a chave em nenhum campo do resultado | `testes/test_verificador_disponibilidade_openai.py` | `uv run --directory src/backend pytest` |
| `MontadorContextoAgente` | unit | Todos os branches; 1:1 com `PREFL-11..15`; campo ausente isola só o item | `testes/test_montador_contexto_agente.py` | `uv run --directory src/backend pytest` |
| `RepositorioContextosAgente` | integration | Salvar/obter, categorias usadas/não usadas | `testes/test_repositorio_contextos_agente.py` | `uv run --directory src/backend pytest` |
| `ServicoPreflightIA` | unit | Todos os branches; 1:1 com `PREFL-01..10`; nova tentativa correlacionada, idempotência | `testes/test_preflight_ia.py` | `uv run --directory src/backend pytest` |
| `Configuracao` (extensão) | none | Validação de inicialização já coberta pelo piso existente (`test_configuracao.py`) — sem teste dedicado novo além do já existente estendido | `testes/test_configuracao.py` (estendido) | `uv run --directory src/backend pytest` |
| Roteador HTTP (preflight + nova tentativa) | integration | Caminho feliz + falha + navegação origem↔retentativa | `testes/test_preflight_ia_api.py` | `uv run --directory src/backend pytest` |
| Contrato OpenAPI | integration | Sincronia com as rotas novas | `testes/test_openapi_sincronizado.py` | `uv run --directory src/backend pytest` |
| Superfície de bloqueio de preparação | unit | Explicação de indisponibilidade, ação de nova tentativa, nenhum conteúdo fictício | `SuperficiePreparacaoIA.test.tsx` | `npm test --prefix src/frontend -- --run` |

## Gate Check Commands

| Gate Level | When to Use | Command |
| --- | --- | --- |
| Quick (backend) | Tasks isoladas de domínio/aplicação/adaptador | `uv run --directory src/backend pytest` |
| Quick (frontend) | Tasks isoladas de componente | `npm test --prefix src/frontend -- --run` |
| Full (backend) | Tasks de roteador HTTP, schema ou config | `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright` |
| Full (frontend) | Tasks de superfície visível | `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend` |
| Build (fim de fase) | Fim de fase / contrato / dependência nova | Backend + Frontend em paralelo, mesmos comandos acima |

---

## Execution Plan

### Phase 1: Dependência, schema e retry genérico

```
T1
T2
T3
```

### Phase 2: Disponibilidade e contexto mínimo

```
T4
T5 → T6
```

### Phase 3: Caso de uso e API

```
T7 → T8
```

### Phase 4: Frontend

```
T9
```

---

## Task Breakdown

### T1: Adicionar dependências `langchain`, `langchain-openai`, `langgraph`

**What**: Adicionar as três dependências ao `pyproject.toml` do backend, com a versão estável mais recente compatível verificada no momento da implementação (Knowledge Verification Chain, PyPI/docs oficiais — não fabricar número de versão).
**Where**: `src/backend/pyproject.toml`
**Depends on**: None
**Reuses**: nenhuma — primeira adição dessas dependências
**Requirement**: PREFL-05

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] `uv sync --project src/backend --locked` (ou regeneração do lock) resolve sem conflito
- [x] Versões documentadas no `pyproject.toml`, coerentes com a versão mínima de Python do projeto (3.14.4)
- [x] Gate check passa: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright`

**Tests**: none
**Gate**: build

**Status**: ✅ Completo — `langchain 1.3.18`, `langchain-openai 1.6.0`, `langgraph 1.2.11` (versões estáveis mais recentes verificadas no PyPI em 2026-09-03; convergem em `langchain-core >=1.6.0,<2`). Gate: 414 testes, ruff e pyright limpos.

---

### T2: Migração `0007_preflight_ia.sql`

**What**: Adicionar `execucao_origem_id` a `execucao_preventiva`; criar `contextos_agente`; atualizar `README.md` de persistência.
**Where**: `src/backend/central_preventiva/adaptadores/persistencia/migracoes/0007_preflight_ia.sql`
**Depends on**: None
**Reuses**: convenção de migração numerada
**Requirement**: PREFL-07, PREFL-12

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] Migração aplica em transação própria, registrada em `schema_migracoes`
- [x] `README.md` documenta a coluna e a tabela novas
- [x] `testes/test_migracoes.py` cobre a aplicação da migração `0009`
- [x] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: integration
**Gate**: quick

**Status**: ✅ Completo — a migração entrou como `0009_preflight_ia.sql`, não `0007`: as versões
`0007` e `0008` já foram usadas pelas Histórias 2.5 e 2.6 depois do planejamento desta história
(mesma renumeração já registrada em 2.4/2.5/2.6). Gate: 417 testes.

---

### T3: Extrair `RetryComBackoff[T]` genérico

**What**: Extrair a política de retry (3 tentativas, backoff 1s/2s/4s, registro por tentativa) de `ColetorComRetry` (2.2) para um wrapper genérico reusável; `ColetorComRetry` passa a usá-lo internamente, sem mudança de comportamento observável.
**Where**: `src/backend/central_preventiva/aplicacao/_retry.py`
**Depends on**: None
**Reuses**: lógica de `ColetorComRetry` (2.2)
**Requirement**: PREFL-01

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] `testes/test_coletor_com_retry.py` (2.2) continua passando sem alteração de asserção — comportamento observável preservado
- [x] Novo teste dedicado ao wrapper genérico cobre sucesso na 1ª/2ª/3ª tentativa e esgotamento
- [x] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: unit
**Gate**: quick

**Status**: ✅ Completo — `RetryComBackoff[T]` em `aplicacao/_retry.py`; `ColetorComRetry` (2.2)
passa a delegar a ele, e `RetentativasEsgotadas` vira subclasse de `TentativasEsgotadas`
preservando `ultima_resposta`. Os 4 testes de 2.2 seguem sem uma linha alterada. Gate: 425 testes.

---

### T4: `VerificadorDisponibilidadeOpenAI`

**What**: Verificação real de disponibilidade (chave válida + serviço respondendo), classificando disponível/indisponível sem nunca incluir a chave no resultado.
**Where**: `src/backend/central_preventiva/adaptadores/ia/verificador_disponibilidade_openai.py`
**Depends on**: T1
**Reuses**: padrão de classificação de `SondaOpenAI` (Épico 1)
**Requirement**: PREFL-03, PREFL-04

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] Chave ausente classifica como indisponível sem chamada de rede
- [x] Resposta 401/429/5xx/timeout classifica como indisponível com causa sanitizada
- [x] Resposta válida classifica como disponível
- [x] Nenhum teste ou asserção contém a chave em texto claro
- [x] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: unit
**Gate**: quick (executado como full — a task também estende `Configuracao`)

**Status**: ✅ Completo. Duas decisões registradas:

1. **SPEC_DEVIATION (chamada de disponibilidade)**: o design cita `langchain_openai.ChatOpenAI`
   e admite "ou chamada HTTP equivalente de baixo custo" no mesmo item. Foi escolhida a chamada
   HTTP `GET /v1/models`: PREFL-03 proíbe iniciar qualquer chamada de geração antes do terminal
   (uma invocação de `ChatOpenAI` seria exatamente isso), e é o catálogo devolvido por
   `/v1/models` que permite tratar "modelo configurado não existe mais" como falha de preparação
   (Edge Case da spec). Marcador no topo de `verificador_disponibilidade_openai.py`.
2. **Extensão de `Configuracao`**: `modelo_openai`, `temperatura_openai`, `versao_prompt` e
   `timeout_openai_segundos` (limite operacional, AD-8) entraram aqui, com validação estrita de
   inicialização e documentação no `.env.example`. Nenhuma task os reivindicava, e T4 é a
   primeira a consumir `modelo_openai`. Cobre PREFL-05 e PREFL-06.

Gate: 462 testes, ruff e pyright limpos.

---

### T5: `MontadorContextoAgente`

**What**: Função pura que monta o contexto mínimo (evento, localização aproximada, coberturas relevantes, canal, orientações de segurança) a partir de um `ResultadoElegibilidade` + `EventoMeteorologico`, validando campos obrigatórios.
**Where**: `src/backend/central_preventiva/dominio/montador_contexto_agente.py`
**Depends on**: None
**Reuses**: `ResultadoElegibilidade` (2.5), `EventoMeteorologico` (2.1)
**Requirement**: PREFL-11, PREFL-12, PREFL-15

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] Contexto montado contém exatamente os 5 campos permitidos, nenhum a mais
- [x] Nenhum documento, dado financeiro, pagamento ou credencial aparece no objeto produzido
- [x] Campo obrigatório ausente/inconsistente retorna erro tipado identificando o item, sem lançar exceção não tratada
- [x] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: unit
**Gate**: quick

**Status**: ✅ Completo. **SPEC_DEVIATION (assinatura)**: `montar` recebe `elegibilidade_id`
como primeiro parâmetro, além do par `(elegibilidade, evento)` do design — o próprio T5 exige
um erro tipado "identificando o item", e `ResultadoElegibilidade` (2.5) não carrega identidade.
Marcador no topo de `montador_contexto_agente.py`.

`avaliador_elegibilidade.py` ganhou `OPERANDO_COBERTURA_EXIGIDA`, seguindo o mesmo padrão já
adotado em `OPERANDO_AREA_AFETADA` (2.5): o montador busca o critério pelo nome estável, nunca
por posição nem por literal duplicado. Gate: 475 testes, ruff e pyright limpos.

---

### T6: `RepositorioContextosAgente`

**What**: `salvar`/`obter_por_elegibilidade` persistindo o contexto e as categorias usadas/não usadas.
**Where**: `src/backend/central_preventiva/adaptadores/persistencia/repositorio_contextos_agente.py`
**Depends on**: T2, T5
**Reuses**: padrão de conexão explícita
**Requirement**: PREFL-13, PREFL-14

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] `salvar` persiste conteúdo serializado e as duas listas de categorias
- [x] `obter_por_elegibilidade` recupera sem recalcular
- [x] Nenhum conteúdo sensível aparece em log durante a persistência
- [x] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: integration
**Gate**: quick

**Status**: ✅ Completo. **SPEC_DEVIATION (tipo de retorno)**: `obter_por_elegibilidade` devolve
`RegistroContextoAgente` (contexto + as duas listas de categorias), não `ContextoAgente | None`
como no design — PREFL-14 exige consultar a proveniência, e o tipo do design não a expõe.
`listar_por_execucao` entrou pela mesma razão: é a leitura de proveniência por execução que a
rota de consulta (T8) usa. Gate: 480 testes, ruff e pyright limpos.

---

### T7: `ServicoPreflightIA`

**What**: `preparar` (verifica disponibilidade via `RetryComBackoff`, monta contexto por item, transiciona estado) e `solicitar_nova_tentativa` (valida snapshots, cria execução correlacionada e copia as elegibilidades da origem — AD-012); estende `RepositorioElegibilidades` (2.5) com `copiar_para_execucao`.
**Where**: `src/backend/central_preventiva/aplicacao/preflight_ia.py`, `src/backend/central_preventiva/adaptadores/persistencia/repositorio_elegibilidade.py` (extensão)
**Depends on**: T3, T4, T6
**Reuses**: `RepositorioExecucaoPreventiva` (2.2), `RepositorioElegibilidades` (2.5, estendido), padrão de execução correlacionada de `ServicoColetaMeteorologica.solicitar_nova_tentativa` (2.2)
**Requirement**: PREFL-01, PREFL-02, PREFL-06, PREFL-08, PREFL-09, PREFL-10

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] Disponibilidade confirmada transiciona a execução para `processando_mensagens`
- [x] Indisponibilidade esgotada transiciona para `falhou_preparacao_ia` com exceção sanitizada
- [x] Item com contexto inválido gera exceção só desse item, sem afetar os demais nem chamar a OpenAI
- [x] `solicitar_nova_tentativa` com snapshot corrompido/versão não suportada rejeita sem criar execução
- [x] `solicitar_nova_tentativa` válida cria execução nova com `execucao_origem_id`, chave idempotente própria; origem permanece terminal
- [x] `solicitar_nova_tentativa` copia todas as linhas de elegibilidade da origem (incluídas e excluídas) para a nova execução — novos `id`s, novo `execucao_id`, conteúdo idêntico — na mesma transação da criação (AD-012); a nova execução não referencia nenhuma linha da origem
- [x] Teste cobre retentativa de origem que já possui `contextos_agente`: o preflight da nova execução monta contextos para as elegibilidades copiadas sem violar a `UNIQUE(elegibilidade_id)` (AD-012)
- [x] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: unit (mais um cenário integrado contra DuckDB real para o AD-012)
**Gate**: quick

**Status**: ✅ Completo. **SPEC_DEVIATION (assinatura de `preparar`)**: recebe também
`chave_idempotencia` e `hash_requisicao` — o AD-002 exige `Idempotency-Key` em todo `POST`
mutável e o T8 exige que repetir a chave devolva a resposta registrada sem novo preflight, o
que precisa ser decidido onde o efeito acontece (mesmo padrão de `ServicoColetaMeteorologica`).

Para tornar a cópia atômica com a criação (AD-012), `RepositorioExecucaoPreventiva` ganhou
`criar_correlacionada(estado, origem, apos_criar)`, que roda o callback dentro da própria
transação, e `listar_correlacionadas` (navegação origem↔retentativas, PREFL-10);
`SnapshotExecucao` ganhou `execucao_origem_id`. `RepositorioElegibilidades.copiar_para_execucao`
aceita a conexão do chamador, como o design previa ("dentro da transação aberta pelo chamador").
Um teste prova a atomicidade: se a cópia falha, nenhuma execução correlacionada permanece.

Gate: 511 testes, ruff e pyright limpos.

---

### T8: Roteador HTTP — preflight e nova tentativa

**What**: `POST /api/v1/execucoes/{id}/preflight` (idempotente) e `POST /api/v1/execucoes/{origem_id}/nova-tentativa-ia`; `GET /api/v1/execucoes/{id}` estendido com `execucao_origem_id` e navegação origem↔retentativas.
**Where**: `src/backend/central_preventiva/adaptadores/http/preflight_ia.py`
**Depends on**: T7
**Reuses**: padrão de roteador existente, fixture `autouse` de bloqueio de rede real
**Requirement**: PREFL-02, PREFL-09, PREFL-10

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] Preflight sem `Idempotency-Key` retorna erro `application/problem+json`
- [x] Repetir a chave devolve a resposta registrada, sem novo preflight
- [x] `GET` de uma execução correlacionada expõe `execucao_origem_id`
- [x] `openapi.json` regenerado, `test_openapi_sincronizado.py` verde
- [x] Gate check passa: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright`

**Tests**: integration
**Gate**: full

**Status**: ✅ Completo — três rotas: `POST /execucoes/{id}/preflight`,
`POST /execucoes/{origem_id}/nova-tentativa-ia` e `GET /execucoes/{id}/contextos`.
`GET /execucoes/{id}` ganhou `execucao_origem_id` e `retentativas` (navegação nos dois
sentidos, sem mesclar marcos).

**SPEC_DEVIATION (rota a mais)**: `GET /execucoes/{id}/contextos` não está no T8. PREFL-14
("Marina consulta a proveniência antes ou depois da geração") não tinha nenhuma task que a
expusesse fora do repositório, e um método de repositório não é algo que Marina consulta. A
rota devolve só nomes de categoria, nunca conteúdo — o teste prova que canal e área não
aparecem na resposta. Gate: 524 testes, ruff e pyright limpos.

---

### T9: Superfície de bloqueio de preparação da IA

**What**: Componente que explica indisponibilidade da OpenAI com a próxima ação segura (nova tentativa), e navega entre execução original e correlacionada; nenhum conteúdo fictício exibido como se fosse real.
**Where**: `src/frontend/src/funcionalidades/preparacao-ia/SuperficiePreparacaoIA.tsx`
**Depends on**: T8
**Reuses**: cliente HTTP central, padrão de `SuperficieProntidao.tsx`
**Requirement**: PREFL-16, PREFL-17

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Bloqueio exibido com causa e ação de nova tentativa, sem texto fictício de mensagem gerada
- [ ] Link de navegação origem↔retentativa funcional
- [ ] `npm run gerar-tipos-api --prefix src/frontend` executado; tipos atualizados
- [ ] Gate check passa: `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`

**Tests**: unit
**Gate**: full

**Commit**: `feat(preflight-ia): adicionar preparacao agentica com verificacao de disponibilidade e contexto minimo`

---

## Phase Execution Map

```
Phase 1:  T1   T2   T3
Phase 2:  T4   T5 → T6
Phase 3:  T7 → T8
Phase 4:  T9
```

Grafo completo de dependências:

```
T1 → T4
T2 → T6
T5 → T6
T3 → T7
T4 → T7
T6 → T7
T7 → T8
T8 → T9
```

(T1, T2 e T3 são independentes entre si na Fase 1; T4 e T5 são independentes entre si na Fase 2.)

---

## Task Granularity Check

| Task | Scope | Status |
| --- | --- | --- |
| T1: Dependências novas | 1 arquivo (`pyproject.toml`) | ✅ Granular |
| T2: Migração `0007` | 1 arquivo `.sql` + doc | ✅ Granular |
| T3: `RetryComBackoff[T]` | 1 componente | ✅ Granular |
| T4: `VerificadorDisponibilidadeOpenAI` | 1 componente | ✅ Granular |
| T5: `MontadorContextoAgente` | 1 componente | ✅ Granular |
| T6: `RepositorioContextosAgente` | 1 componente | ✅ Granular |
| T7: `ServicoPreflightIA` | 1 caso de uso | ✅ Granular |
| T8: Roteador preflight | 1 componente | ✅ Granular |
| T9: Superfície de bloqueio | 1 componente | ✅ Granular |

---

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| --- | --- | --- | --- |
| T1 | None | — | ✅ Match |
| T2 | None | — | ✅ Match |
| T3 | None | — | ✅ Match |
| T4 | T1 | T1 → T4 (grafo completo) | ✅ Match |
| T5 | None | — | ✅ Match |
| T6 | T2, T5 | T2 → T6, T5 → T6 (grafo completo) | ✅ Match |
| T7 | T3, T4, T6 | T3 → T7, T4 → T7, T6 → T7 (grafo completo) | ✅ Match |
| T8 | T7 | T7 → T8 | ✅ Match |
| T9 | T8 | T8 → T9 (grafo completo) | ✅ Match |

**Rules confirmed**: toda dependência aponta para trás ou dentro da mesma fase.

---

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| --- | --- | --- | --- | --- |
| T1: Dependências novas | Build/config | none | none | ✅ OK |
| T2: Migração `0007` | Migração/schema | integration | integration | ✅ OK |
| T3: `RetryComBackoff[T]` | Aplicação | unit | unit | ✅ OK |
| T4: `VerificadorDisponibilidadeOpenAI` | Adaptador | unit | unit | ✅ OK |
| T5: `MontadorContextoAgente` | Domínio | unit | unit | ✅ OK |
| T6: `RepositorioContextosAgente` | Repositório | integration | integration | ✅ OK |
| T7: `ServicoPreflightIA` | Aplicação | unit | unit | ✅ OK |
| T8: Roteador preflight | Roteador HTTP | integration | integration | ✅ OK |
| T9: Superfície de bloqueio | Componente React | unit | unit | ✅ OK |

**Rules confirmed**: `Tests: none` só em T1 (build/config), conforme a matriz; nenhuma task adia teste.
