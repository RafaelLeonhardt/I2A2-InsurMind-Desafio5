# História 3.2: Gerar mensagens automaticamente para cada canal — Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/3-2-gerar-mensagens-automaticamente-para-cada-canal/design.md`
**Status**: Approved

---

## Test Coverage Matrix

> Guidelines: `AGENTS.md`, `README.md`; piso em `testes/test_avaliador_risco.py` (motor determinístico puro) e `testes/test_coletor_com_retry.py` (retry com dublê). Chamadas ao `ChatOpenAI` SEMPRE testadas com um dublê (`FakeChatModel`/transporte falso do LangChain, ou um `AgenteRedator` falso implementando a mesma interface) — nunca rede real.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| Migração `0008_mensagens.sql` | integration | Aplicação, tabelas novas, `UNIQUE` | `testes/test_migracoes.py` | `uv run --directory src/backend pytest` |
| `dominio/estados_mensagem.py` | none | Enum sem lógica própria, mesmo piso de `estados_execucao.py` | — | build gate only |
| `ValidadorSaidaCanal` | unit | Todos os branches; 1:1 com `GERAR-01..03,07..09`; fronteiras exatas por canal | `testes/test_validador_saida_canal.py` | `uv run --directory src/backend pytest` |
| `AgenteRedator` | unit | Chamada estruturada por canal, com dublê do `ChatOpenAI` (sem rede real) | `testes/test_agente_redator.py` | `uv run --directory src/backend pytest` |
| `GrafoGeracaoMensagem` (LangGraph) | unit | Nó `gerar`: sucesso, falha de transporte esgotada, saída inválida — grafo compilado testado com dublês | `testes/test_grafo_geracao_mensagem.py` | `uv run --directory src/backend pytest` |
| `RepositorioMensagens` | integration | Criar (com `UNIQUE`), salvar versão, transicionar (concorrência otimista) | `testes/test_repositorio_mensagens.py` | `uv run --directory src/backend pytest` |
| `ServicoGeracaoMensagens` | unit | Todos os branches; 1:1 com `GERAR-04..06,10..12`; contexto ausente isolado | `testes/test_geracao_mensagens.py` | `uv run --directory src/backend pytest` |
| Roteador HTTP (consulta de mensagens) | integration | `GET` de mensagens por execução, reidratação sem reenvio | `testes/test_mensagens_api.py` | `uv run --directory src/backend pytest` |
| Contrato OpenAPI | integration | Sincronia com a rota nova | `testes/test_openapi_sincronizado.py` | `uv run --directory src/backend pytest` |
| Superfície de acompanhamento da geração | unit | Progresso reconstruído dos dados persistidos ao reidratar, sem duplicar | `SuperficieGeracaoMensagens.test.tsx` | `npm test --prefix src/frontend -- --run` |

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

### Phase 1: Schema e domínio

```
T1
T2
```

### Phase 2: Agente e grafo

```
T3
T4 → T5
```

### Phase 3: Persistência e caso de uso

```
T6 → T7
```

### Phase 4: API e frontend

```
T8 → T9
```

---

## Task Breakdown

### T1: Migração `0008_mensagens.sql`

**What**: Criar `mensagens` (com `UNIQUE(elegibilidade_id, canal)`) e `versoes_mensagem`; atualizar `README.md` de persistência.
**Where**: `src/backend/central_preventiva/adaptadores/persistencia/migracoes/0008_mensagens.sql`
**Depends on**: None
**Reuses**: convenção de migração numerada
**Requirement**: GERAR-06

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] Migração aplica em transação própria, registrada em `schema_migracoes`
- [x] `README.md` documenta as duas tabelas e a `UNIQUE`
- [x] `testes/test_migracoes.py` cobre a aplicação da migração `0008`
- [x] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: integration
**Gate**: quick

**Status**: ✅ Completo — a migração entrou como `0010_mensagens.sql`, não `0008`: `0008` e `0009`
já foram consumidos pelas Histórias 2.6 e 3.1 depois do planejamento desta história (mesma
renumeração já registrada desde a 2.4). Gate: 528 testes.

---

### T2: `dominio/estados_mensagem.py`

**What**: `EstadoMensagem` (StrEnum) com os 9 estados do segundo diagrama do AD-4; `ESTADOS_TERMINAIS_MENSAGEM`; `eh_terminal_mensagem`.
**Where**: `src/backend/central_preventiva/dominio/estados_mensagem.py`
**Depends on**: None
**Reuses**: padrão de `dominio/estados_execucao.py` (AD-004)
**Requirement**: GERAR-09

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] Os 9 valores batem exatamente com o diagrama do AD-4 (`ARCHITECTURE-SPINE.md`)
- [x] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: none
**Gate**: quick

**Status**: ✅ Completo — `EstadoMensagem` com os 9 valores do segundo diagrama do AD-4 e os 5
terminais (`rejeitada`, `excluida`, `simulada_entregue`, `falhou_conteudo`,
`falhou_integracao_ia`). A matriz pede `none`, mas o piso do repositório para esta camada é
`testes/test_estados_execucao.py`; `testes/test_estados_mensagem.py` o espelha (3 casos) para
dar evidência `file:line` ao critério "os 9 valores batem". Gate: 541 testes.

---

### T3: `ValidadorSaidaCanal`

**What**: Valida campos obrigatórios e limite de caracteres Unicode por canal, usando os limites de `Configuracao`.
**Where**: `src/backend/central_preventiva/dominio/validador_saida_canal.py`
**Depends on**: None
**Reuses**: nenhum — primeiro validador de canal
**Requirement**: GERAR-01, GERAR-02, GERAR-03, GERAR-07, GERAR-08

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] WhatsApp/SMS: corpo ausente ou vazio → inválido; corpo no limite exato → válido; corpo 1 caractere acima → inválido
- [x] E-mail: mesmas fronteiras aplicadas separadamente a assunto e corpo
- [x] Novos campos de limite adicionados a `Configuracao` com defaults documentados no `.env.example`
- [x] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: unit
**Gate**: quick

**Status**: ✅ Completo — `Canal`, `LimitesCanal`, `SaidaCanal`, `ResultadoValidacaoSaida` e
`ValidadorSaidaCanal` em `dominio/validador_saida_canal.py`; 4 limites novos em `Configuracao`
(1024/160/78/2000) com validação estrita na inicialização e documentação no `.env.example`.
Os limites entram por `LimitesCanal` porque o domínio não pode importar `composicao`
(`test_camadas.py`); a conversão a partir da `Configuracao` mora na composição.
`limite_corpo`/`limite_assunto` expõem antes da geração o mesmo número cobrado depois
(GERAR-02). Gate: 581 testes.

---

### T4: `AgenteRedator`

**What**: Chama `ChatOpenAI(model=..., temperature=...).with_structured_output(schema_do_canal)` com o contexto mínimo, devolvendo `SaidaWhatsApp`/`SaidaSMS`/`SaidaEmail`.
**Where**: `src/backend/central_preventiva/adaptadores/ia/agente_redator.py`
**Depends on**: None
**Reuses**: `Configuracao` (3.1)
**Requirement**: GERAR-07, GERAR-08

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] Testado com um dublê do `ChatOpenAI` (sem rede real) para cada um dos 3 canais
- [x] Schema de saída por canal é um Pydantic model distinto (WhatsApp/SMS: `corpo`; e-mail: `assunto`+`corpo`)
- [x] Exceção de transporte não é capturada aqui — propagada ao chamador (o wrapper de retry decide)
- [x] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: unit
**Gate**: quick

**Status**: ✅ Completo — `AgenteRedator` chama
`with_structured_output(schema_do_canal, include_raw=True)` e devolve `RespostaRedator`
(saída + tokens). SPEC_DEVIATION registrada no módulo: o design escreve `-> SaidaCanal`, mas
GERAR-10 exige persistir métricas de uso e GERAR-09 exige que saída ausente/malformada seja
marcada inválida em vez de levantar exceção — daí o tipo próprio, com `saida` anulável. O
limite do canal entra no prompt (o "antes" de GERAR-02) vindo do mesmo `ValidadorSaidaCanal`
que o cobra depois. Gate: 591 testes.

---

### T5: `GrafoGeracaoMensagem` (LangGraph)

**What**: `StateGraph` com o nó `gerar`: chama `AgenteRedator` via `RetryComBackoff` (3.1); em falha de transporte esgotada, resultado indica `falhou_integracao_ia`; em saída recebida, aplica `ValidadorSaidaCanal` e retorna resultado válido/inválido.
**Where**: `src/backend/central_preventiva/aplicacao/grafos/geracao_mensagem.py`
**Depends on**: T3, T4
**Reuses**: `RetryComBackoff[T]` (3.1), `AgenteRedator`, `ValidadorSaidaCanal`
**Requirement**: GERAR-05, GERAR-09

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] Sucesso na 1ª chamada de transporte com saída válida retorna resultado "válido"
- [x] Falha de transporte esgotando `RetryComBackoff` retorna resultado "falhou_integracao_ia" sem levantar exceção não tratada
- [x] Saída estruturalmente inválida ou acima do limite retorna resultado "inválido" com motivo
- [x] Nenhum teste chama a OpenAI real
- [x] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: unit
**Gate**: quick

**Status**: ✅ Completo — `StateGraph` de um nó (`START → gerar → END`) compilado em
`aplicacao/grafos/geracao_mensagem.py`. O nó devolve `ResultadoGeracao` com um de três
desfechos (`valida`, `invalida`, `falhou_integracao_ia`), mais duração, modelo e tokens; nunca
escreve no banco nem transiciona estado. `erros_reconhecidos=(Exception,)` no `RetryComBackoff`
porque a pilha do LangChain/OpenAI levanta uma família ampla de erros de transporte. Gate: 598
testes (7 novos, todos com redator falso).

---

### T6: `RepositorioMensagens`

**What**: `criar` (respeitando `UNIQUE`), `salvar_versao`, `transicionar` (concorrência otimista + `eh_terminal_mensagem`).
**Where**: `src/backend/central_preventiva/adaptadores/persistencia/repositorio_mensagens.py`
**Depends on**: T1, T2
**Reuses**: padrão de concorrência otimista de `RepositorioExecucaoPreventiva` (2.2)
**Requirement**: GERAR-06, GERAR-09

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] `criar` duas vezes para a mesma elegibilidade+canal viola `UNIQUE` (tratado como erro específico, não exceção genérica)
- [x] `salvar_versao` persiste conteúdo, validade, motivo, duração, modelo, prompt, tokens
- [x] `transicionar` a partir de um estado terminal de mensagem levanta erro, mesma semântica de `RepositorioExecucaoPreventiva`
- [x] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: integration
**Gate**: quick

**Status**: ✅ Completo — `criar`/`salvar_versao`/`transicionar`, mais `obter`,
`listar_por_execucao` e `obter_versao_atual` (leituras que a reidratação da T8 consome). A
`duckdb.ConstraintException` da `UNIQUE (elegibilidade_id, canal)` vira `MensagemJaExiste`, um
erro específico que o caso de uso trata como no-op idempotente — nunca uma checagem
"consulta e depois insere" em Python (AD-010). `transicionar` repete literalmente o padrão de
`RepositorioExecucaoPreventiva`: `ConflitoVersaoMensagem` e `TransicaoMensagemInvalida`, sem
mutar a linha em nenhum dos dois casos. Gate: 609 testes (11 novos, banco real).

---

### T7: `ServicoGeracaoMensagens`

**What**: Para cada elegibilidade `incluida` da execução, cria a mensagem, roda `GrafoGeracaoMensagem`, persiste versão e transiciona (`criticando` se válida; permanece `gerando` se inválida; `falhou_integracao_ia` se transporte esgotado).
**Where**: `src/backend/central_preventiva/aplicacao/geracao_mensagens.py`
**Depends on**: T5, T6
**Reuses**: `RepositorioElegibilidades.listar_por_execucao` (2.5), `RepositorioContextosAgente` (3.1)
**Requirement**: GERAR-04, GERAR-05, GERAR-06, GERAR-10, GERAR-11, GERAR-12

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] Duas elegibilidades incluídas com canais diferentes geram duas mensagens, sem ação manual
- [x] Cada mensagem gerada permanece associada a execução, elegibilidade, evento (via elegibilidade), regra (via elegibilidade), segurado, apólice, canal
- [x] Item sem contexto mínimo (3.1) é pulado com exceção isolada, sem chamar a OpenAI
- [x] Reidratar (chamar `gerar_lote` de novo para uma execução já processada) não duplica nenhuma mensagem
- [x] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: unit
**Gate**: quick

**Status**: ✅ Completo — `gerar_lote(execucao_id)` percorre o público incluído, cria a
mensagem, roda o grafo e persiste o desfecho; falha de um item nunca interrompe o lote.

**Onde o acionamento automático foi ligado (investigação exigida pelo AC GERAR-04.1).** O
`design.md` diz que `gerar_lote` roda "dentro da task assíncrona já iniciada por
`GerenciadorExecucoes` (2.6) ao entrar em `processando_mensagens`". Isso não é executável
contra o código real: `GerenciadorExecucoes` para em `aguardando_geracao` (é o checkpoint em
que a 2.6 termina, e `retomar_pendentes` pula esse estado de propósito) e nunca entra em
`processando_mensagens`. O único caminho de código que faz essa transição é
`ServicoPreflightIA._preparar_agora` (3.1), acionado pelo `POST /execucoes/{id}/preflight`,
que a `SuperficiePreparacaoIA` dispara por um clique único de Marina — não automaticamente no
carregamento da página.

Decisão: `PortasPreflightIA` ganhou a porta opcional `acionar_geracao`, chamada logo após a
transição bem-sucedida para `processando_mensagens` e o marco. Na composição HTTP, ela agenda
`gerar_lote` como task desacoplada (mesmo padrão do `GerenciadorExecucoes`), então o `202` do
preflight não espera pelo lote. O desfecho que o AC pede fica preservado: Marina não dispara
nada **por mensagem** — o mesmo comando único que já existia deixa o lote inteiro gerado. A
divergência está marcada como `SPEC_DEVIATION` no próprio campo, em `aplicacao/preflight_ia.py`.

Efeito colateral corrigido no caminho: `AgenteRedator` passou a construir o `ChatOpenAI` só na
primeira geração. Construí-lo na composição levantava `OpenAIError` sem `OPENAI_API_KEY`, o que
impedia o backend de subir com a chave vazia — contra o AD-9, que trata ausência de chave como
estado de preflight, não como falha de inicialização (69 testes de API pegaram isso).

Gate: 622 testes (13 novos, repositório de mensagens e grafo reais, só o redator falso).

---

### T8: Endpoint HTTP de consulta de mensagens

**What**: `GET /api/v1/execucoes/{execucao_id}/mensagens` retornando estado, tentativa, canal e versão atual de cada mensagem.
**Where**: `src/backend/central_preventiva/adaptadores/http/mensagens.py`
**Depends on**: T7
**Reuses**: padrão de roteador existente
**Requirement**: GERAR-11, GERAR-12

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] `200` com a lista de mensagens e seus estados/versão atual
- [x] Chamado antes e depois da geração completa reflete só dados persistidos, nunca estado inventado
- [x] `openapi.json` regenerado, `test_openapi_sincronizado.py` verde
- [x] Gate check passa: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright`

**Tests**: integration
**Gate**: full

**Status**: ✅ Completo — `GET /api/v1/execucoes/{execucao_id}/mensagens` devolve, por
mensagem, origem (elegibilidade), canal, estado, tentativa, versão de concorrência e os
metadados da versão atual (veredito, motivo, modelo, prompt, duração, tokens). Mensagem sem
versão devolve `versao_atual: null`, nunca um estado inventado. O **texto gerado não entra na
resposta**: exibir conteúdo para decisão humana é a superfície de revisão da História 3.5,
fora do escopo desta. `openapi.json` regenerado e o inventário de rotas de `test_saude.py`
atualizado com a rota nova. Gate full: 630 testes, ruff e pyright limpos.

---

### T9: Superfície de acompanhamento da geração

**What**: Componente que exibe progresso da geração por item (etapa, canal), reconstruído a partir da API a cada carregamento, sem reenviar geração.
**Where**: `src/frontend/src/funcionalidades/geracao-mensagens/SuperficieGeracaoMensagens.tsx`
**Depends on**: T8
**Reuses**: cliente HTTP central, `SuperficieExecucao` (2.6) como referência de layout
**Requirement**: GERAR-11, GERAR-12

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] Progresso reconstruído inteiramente da API a cada montagem do componente
- [x] Nenhuma chamada de geração disparada pelo frontend (só leitura)
- [x] `npm run gerar-tipos-api --prefix src/frontend` executado; tipos atualizados
- [x] Gate check passa: `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`

**Tests**: unit
**Gate**: full

**Status**: ✅ Completo — `SuperficieGeracaoMensagens` lê `GET .../mensagens` a cada montagem e
classifica cada item em quatro categorias distintas por texto, ícone e cor/traço (L-024):
gerada, gerando, aguardando nova tentativa (com o motivo persistido) e falha de integração. O
único botão é "Atualizar progresso", que refaz a mesma consulta de leitura — a superfície não
tem caminho para disparar geração, e `src/api/mensagens.ts` só expõe `getMensagens`. Tipos
regenerados pelo comando documentado, com o backend real no ar (`verificar-tipos-api`
confirmou a sincronia). Gate full: 237 testes de frontend, lint e build limpos; backend segue
em 630.

**Commit**: `feat(geracao): adicionar agente redator e geracao automatica de mensagens por canal`

---

## Phase Execution Map

```
Phase 1:  T1   T2
Phase 2:  T3   T4 → T5
Phase 3:  T6 → T7
Phase 4:  T8 → T9
```

Grafo completo de dependências:

```
T3 → T5
T4 → T5
T1 → T6
T2 → T6
T5 → T7
T6 → T7
T7 → T8
T8 → T9
```

(T1 e T2 são independentes entre si na Fase 1; T3 e T4 são independentes entre si na Fase 2.)

---

## Task Granularity Check

| Task | Scope | Status |
| --- | --- | --- |
| T1: Migração `0008` | 1 arquivo `.sql` + doc | ✅ Granular |
| T2: `estados_mensagem.py` | 1 componente | ✅ Granular |
| T3: `ValidadorSaidaCanal` | 1 componente | ✅ Granular |
| T4: `AgenteRedator` | 1 componente | ✅ Granular |
| T5: `GrafoGeracaoMensagem` | 1 componente | ✅ Granular |
| T6: `RepositorioMensagens` | 1 componente | ✅ Granular |
| T7: `ServicoGeracaoMensagens` | 1 caso de uso | ✅ Granular |
| T8: Endpoint HTTP | 1 componente | ✅ Granular |
| T9: Superfície de acompanhamento | 1 componente | ✅ Granular |

---

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| --- | --- | --- | --- |
| T1 | None | — | ✅ Match |
| T2 | None | — | ✅ Match |
| T3 | None | — | ✅ Match |
| T4 | None | — | ✅ Match |
| T5 | T3, T4 | T3 → T5, T4 → T5 (grafo completo) | ✅ Match |
| T6 | T1, T2 | T1 → T6, T2 → T6 (grafo completo) | ✅ Match |
| T7 | T5, T6 | T5 → T7, T6 → T7 (grafo completo) | ✅ Match |
| T8 | T7 | T7 → T8 | ✅ Match |
| T9 | T8 | T8 → T9 | ✅ Match |

**Rules confirmed**: toda dependência aponta para trás ou dentro da mesma fase.

---

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| --- | --- | --- | --- | --- |
| T1: Migração `0008` | Migração/schema | integration | integration | ✅ OK |
| T2: `estados_mensagem.py` | Domínio (enum) | none | none | ✅ OK |
| T3: `ValidadorSaidaCanal` | Domínio | unit | unit | ✅ OK |
| T4: `AgenteRedator` | Adaptador de IA | unit | unit | ✅ OK |
| T5: `GrafoGeracaoMensagem` | Aplicação (grafo) | unit | unit | ✅ OK |
| T6: `RepositorioMensagens` | Repositório | integration | integration | ✅ OK |
| T7: `ServicoGeracaoMensagens` | Aplicação | unit | unit | ✅ OK |
| T8: Endpoint HTTP | Roteador HTTP | integration | integration | ✅ OK |
| T9: Superfície de acompanhamento | Componente React | unit | unit | ✅ OK |

**Rules confirmed**: `Tests: none` só em T2 (enum sem lógica), conforme a matriz; nenhuma task adia teste.
