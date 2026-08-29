# História 1.3: Verificar a Prontidão das Dependências Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/1-3-verificar-a-prontidao-das-dependencias/design.md`
**Status**: Draft

---

## Test Coverage Matrix

> Generated from codebase sampling (`test_camadas.py`, `test_configuracao.py`, `test_restauracao.py`, `test_dados_sinteticos_api.py`, `RestaurarDemonstracao.test.tsx`, `dadosSinteticos.test.ts`) and the strong default (no numeric coverage-threshold file found in the repo). Existing tests are thorough (multi-scenario, error-sanitization, accessibility) and set the floor for this feature's tests, not a ceiling. `httpx.MockTransport` (built into the `httpx` already in the dev/prod dependency set) is used to double INMET/OpenAI — no real network call in any test, per spec.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| Domínio (`dominio/estados_prontidao.py`) | unit | All branches; 1:1 to spec ACs | `src/backend/testes/test_estados_prontidao.py` | `uv run --directory src/backend pytest` |
| Aplicação — portas/DTOs (`aplicacao/portas_prontidao.py`) | none | Interfaces/exceptions only, no behavior — build gate only | `src/backend/central_preventiva/aplicacao/portas_prontidao.py` | `uv run --directory src/backend pyright` |
| Aplicação — caso de uso (`aplicacao/prontidao.py`) | unit (fake `PortaSonda`, per project convention) | All branches; 1:1 to spec ACs incl. every listed edge case (in-flight conflict, restart-loses-memory, exception→estado terminal) | `src/backend/testes/test_prontidao.py` | `uv run --directory src/backend pytest` |
| Adaptadores/prontidão — sondas (`adaptadores/prontidao/sonda_*.py`) | unit (dublês; `httpx.MockTransport` p/ INMET e OpenAI, sem rede real) | Disponível + Degradada + Indisponível + timeout, para cada sonda | `src/backend/testes/test_sonda_backend.py`, `test_sonda_banco_dados.py`, `test_sonda_inmet.py`, `test_sonda_openai.py` | `uv run --directory src/backend pytest` |
| Composição (`configuracao.py` extension) | integration | Key paths + validation errors — matches existing `test_configuracao.py` floor | `src/backend/testes/test_configuracao.py` | `uv run --directory src/backend pytest` |
| Adaptadores/http (`adaptadores/http/prontidao.py`) | e2e (`fastapi.testclient.TestClient`, matches `test_dados_sinteticos_api.py`'s pattern) | All routes: happy + every listed edge/error path | `src/backend/testes/test_prontidao_api.py` | `uv run --directory src/backend pytest` |
| Config/entity (`pyproject.toml` httpx promotion) | none | - (build gate only) | `src/backend/pyproject.toml` | `uv run --directory src/backend pytest` (import resolves) |
| Frontend — api (`api/prontidao.ts`) | unit (mocked `fetch`) | Success + every error/edge path (404, 409×2, 422×2, network failure) | `src/frontend/src/api/prontidao.test.ts` | `npm test --prefix src/frontend -- --run` |
| Frontend — funcionalidades (`funcionalidades/prontidao/*.tsx`) | integration (RTL) | Happy path + every listed UI state (`Disponível`/`Degradada`/`Indisponível`/`Verificando`), `aria-live`, toast-as-reinforcement, keyboard operability | `src/frontend/src/funcionalidades/prontidao/**/*.test.tsx` | `npm test --prefix src/frontend -- --run` |

## Gate Check Commands

> Generated from `README.md`'s documented "Execução local" commands — confirm before Execute.

| Gate Level | When to Use | Command |
| --- | --- | --- |
| Quick | After tasks with unit tests only | Backend: `uv run --directory src/backend pytest` · Frontend: `npm test --prefix src/frontend -- --run` |
| Full | After tasks with integration/e2e tests | Backend: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright` · Frontend: `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend` |
| Build | After phase completion or config/entity-only tasks | Backend: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright` · Frontend: `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend` |

---

## Execution Plan

Phases are ordered and run sequentially - each phase completes before the next begins, and tasks within a phase execute in order.

### Phase 1: Domínio e configuração

```
T1
T2
T3
```

No dependency among T1-T3 themselves; executed in listed order within the phase.

### Phase 2: Portas e sondas

```
T4 → T5
T4 → T6
T4 → T7
T4 → T8
```

T7 e T8 também dependem de T3 (Fase 1) - cross-fase, ver a lista completa de arestas no Phase Execution Map abaixo.

### Phase 3: Caso de uso de prontidão

```
T9 → T10
```

T9 também depende de T4 (Fase 2) - cross-fase, ver Phase Execution Map.

### Phase 4: HTTP e composição

```
T11 → T12
```

T11 também depende de T2 (Fase 1) e T5, T6, T7, T8, T9 (Fases 2-3); T12 também depende de T10 (Fase 3) - cross-fase, ver Phase Execution Map.

### Phase 5: Frontend

```
T13 → T14 → T15
```

T13 também depende de T12 (Fase 4) - cross-fase, ver Phase Execution Map.

---

## Task Breakdown

### T1: Criar o enum `EstadoProntidao` e a classificação terminal

**What**: `dominio/estados_prontidao.py` com `EstadoProntidao(StrEnum)` (`VERIFICANDO`, `DISPONIVEL`, `DEGRADADA`, `INDISPONIVEL`), `ESTADOS_TERMINAIS` (tudo exceto `VERIFICANDO`) e `eh_terminal()`.
**Where**: `src/backend/central_preventiva/dominio/estados_prontidao.py`
**Depends on**: None
**Reuses**: Mesmo padrão de `dominio/estados_execucao.py`
**Requirement**: PRONT-02, PRONT-09

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] `EstadoProntidao` tem exatamente os 4 estados do spec
- [x] `eh_terminal(VERIFICANDO)` é `False`; os outros 3 são `True`
- [x] `test_camadas.py::test_dominio_nao_importa_frameworks_ou_adaptadores` continua passando (arquivo novo sem import proibido)
- [x] Gate check passa: `uv run --directory src/backend pytest`
- [x] Test count: 3+ testes passam

**Tests**: unit
**Gate**: quick

---

### T2: Estender `Configuracao` com `chave_openai` e `url_base_inmet`

**What**: Adicionar `chave_openai: SecretStr | None` (`validation_alias="OPENAI_API_KEY"`, default `None`) e `url_base_inmet: str` (`validation_alias="CENTRAL_PREVENTIVA_URL_BASE_INMET"`) a `Configuracao`; atualizar `.env.example` com os nomes (sem valor secreto).
**Where**: `src/backend/central_preventiva/composicao/configuracao.py`, `.env.example`
**Depends on**: None
**Reuses**: Padrão de validação estrita já usado por `host_api`/`origem_frontend`/`caminho_banco`
**Requirement**: PRONT-05, PRONT-06

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] `Configuracao` aceita `OPENAI_API_KEY` ausente (campo `None`) sem falhar a validação
- [x] `chave_openai.get_secret_value()` nunca aparece em `repr(configuracao)` (teste que serializa/repr a config e busca a string do valor)
- [x] `.env.example` documenta `OPENAI_API_KEY=` e `CENTRAL_PREVENTIVA_URL_BASE_INMET=` sem valor secreto
- [x] Gate check passa: `uv run --directory src/backend pytest`
- [x] Test count: 2+ novos testes em `test_configuracao.py` passam, nenhum teste existente quebra

**Tests**: integration
**Gate**: quick

---

### T3: Promover `httpx` a dependência de produção

**What**: Mover `httpx` de `[dependency-groups].dev` para `[project.dependencies]` em `pyproject.toml` (mesma versão já fixada); `httpx2` permanece intocado (fora de escopo, já registrado em Risks & Concerns).
**Where**: `src/backend/pyproject.toml`
**Depends on**: None
**Reuses**: N/A
**Requirement**: PRONT-01 (pré-requisito técnico das sondas externas)

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] `httpx` aparece em `[project.dependencies]`
- [x] `uv sync` (ou equivalente já usado pelo projeto) resolve sem erro
- [x] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: none
**Gate**: build

---

### T4: Criar as portas e tipos de prontidão

**What**: `aplicacao/portas_prontidao.py` com `ResultadoSonda`, `EstadoDependencia`, `NomeDependencia`, `PortaSonda(Protocol)`, `VerificacaoEmAndamento`, `DependenciaDesconhecida`.
**Where**: `src/backend/central_preventiva/aplicacao/portas_prontidao.py`
**Depends on**: T1
**Reuses**: Estilo de `aplicacao/portas_persistencia.py` (dataclasses `frozen=True, slots=True`, exceções com mensagem PT-BR pronta)
**Requirement**: PRONT-01, PRONT-07, PRONT-08

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] `PortaSonda.verificar` é `async` e retorna `ResultadoSonda` (nunca `VERIFICANDO`)
- [x] `VerificacaoEmAndamento`/`DependenciaDesconhecida` têm mensagem em português pronta no `__init__`
- [x] `pyright` estrito não acusa erro no arquivo
- [x] Gate check passa: `uv run --directory src/backend pyright`

**Tests**: none
**Gate**: build

---

### T5: Implementar `SondaBackend`

**What**: `SondaBackend` — sem I/O externo, delega a `consultar_saude()`, sempre retorna `ResultadoSonda(estado=DISPONIVEL, causa=None, latencia_ms=None)`.
**Where**: `src/backend/central_preventiva/adaptadores/prontidao/sonda_backend.py`
**Depends on**: T4
**Reuses**: `aplicacao/saude.py::consultar_saude`
**Requirement**: PRONT-01

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] `await SondaBackend().verificar()` retorna sempre `DISPONIVEL`
- [x] Gate check passa: `uv run --directory src/backend pytest`
- [x] Test count: 1+ teste passa

**Tests**: unit
**Gate**: quick

---

### T6: Implementar `SondaBancoDados`

**What**: `SondaBancoDados` — `SELECT 1` via `abrir_conexao`; sucesso → `DISPONIVEL`; exceção → `INDISPONIVEL` com causa saneada (sem caminho de arquivo no texto exposto).
**Where**: `src/backend/central_preventiva/adaptadores/prontidao/sonda_banco_dados.py`
**Depends on**: T4
**Reuses**: `adaptadores/persistencia/conexao.py::abrir_conexao`
**Requirement**: PRONT-01

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Banco válido em `tmp_path` → `DISPONIVEL`
- [x] Banco inacessível (ex. diretório sem permissão, ou arquivo corrompido) → `INDISPONIVEL`, `causa` sem o caminho absoluto do arquivo
- [x] Gate check passa: `uv run --directory src/backend pytest`
- [x] Test count: 2+ testes passam

**Tests**: unit
**Gate**: quick

---

### T7: Implementar `SondaInmet`

**What**: `SondaInmet` — `httpx.AsyncClient(timeout=3.0).get(url_base_inmet)`; classifica `DISPONIVEL` (2xx rápido), `DEGRADADA` (2xx lento > 1.5s, ou `429`/`5xx` numa tentativa), `INDISPONIVEL` (timeout, falha de conexão/DNS).
**Where**: `src/backend/central_preventiva/adaptadores/prontidao/sonda_inmet.py`
**Depends on**: T3, T4
**Reuses**: `PortaSonda` de `portas_prontidao.py`
**Requirement**: PRONT-04

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] `httpx.MockTransport` simula 2xx rápido → `DISPONIVEL`
- [x] `httpx.MockTransport` simula 2xx com atraso > orçamento → `DEGRADADA`
- [x] `httpx.MockTransport` simula `503` → `DEGRADADA`
- [x] `httpx.MockTransport` simula `httpx.TimeoutException`/`httpx.ConnectError` → `INDISPONIVEL`
- [x] Nenhum teste faz chamada de rede real
- [x] Gate check passa: `uv run --directory src/backend pytest`
- [x] Test count: 4+ testes passam

**Tests**: unit
**Gate**: quick

---

### T8: Implementar `SondaOpenAI`

**What**: `SondaOpenAI` — recebe a chave já resolvida no construtor (a decisão "sem chave" é da camada de aplicação, não da sonda); `httpx.AsyncClient(timeout=5.0).get("https://api.openai.com/v1/models", headers={"Authorization": f"Bearer {chave}"})`; classifica `DISPONIVEL`/`DEGRADADA`/`INDISPONIVEL` (inclui `401` → `INDISPONIVEL`, "credencial inválida"); a chave nunca entra em `causa`, exceção ou log.
**Where**: `src/backend/central_preventiva/adaptadores/prontidao/sonda_openai.py`
**Depends on**: T3, T4
**Reuses**: `PortaSonda` de `portas_prontidao.py`
**Requirement**: PRONT-04, PRONT-06

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `httpx.MockTransport` simula 200 → `DISPONIVEL`
- [ ] `httpx.MockTransport` simula `429`/`5xx` → `DEGRADADA`
- [ ] `httpx.MockTransport` simula `401` → `INDISPONIVEL`, causa não contém a chave usada no teste
- [ ] `httpx.MockTransport` simula timeout → `INDISPONIVEL`
- [ ] Um teste passa uma chave sintética óbvia (`sk-teste-xyz`) e faz `assert "sk-teste-xyz" not in str(resultado)` sobre o `ResultadoSonda` e sobre qualquer exceção capturada
- [ ] Gate check passa: `uv run --directory src/backend pytest`
- [ ] Test count: 5+ testes passam

**Tests**: unit
**Gate**: quick

---

### T9: Implementar `RegistroProntidao` e `consultar_prontidao` (caminho GET)

**What**: `RegistroProntidao` (estado em memória por dependência + lock por dependência) e `consultar_prontidao(portas, registro)` — recomputa backend/banco_dados inline a cada chamada; para inmet/openai, se ausente do registro, marca `VERIFICANDO` e dispara a sonda em `asyncio.create_task`; devolve as 4 `EstadoDependencia` atuais.
**Where**: `src/backend/central_preventiva/aplicacao/prontidao.py`
**Depends on**: T4
**Reuses**: Formato de casos de uso de `aplicacao/restauracao.py`
**Requirement**: PRONT-01, PRONT-02, PRONT-03

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Primeira chamada com registro vazio: `backend`/`banco_dados` já terminais na mesma chamada; `inmet`/`openai` = `VERIFICANDO`
- [ ] Chamada seguinte, após a task de fundo concluir (aguardada no teste), reflete o estado terminal (`DISPONIVEL`/`DEGRADADA`/`INDISPONIVEL`) sem novo disparo
- [ ] Uma sonda que levanta exceção não mapeada resulta em `INDISPONIVEL` com causa genérica (nunca deixa `VERIFICANDO` pendurado — NFR11)
- [ ] `backend`/`banco_dados` nunca chamam `PortaSonda` de inmet/openai (assert com dublê que falha se chamado)
- [ ] Gate check passa: `uv run --directory src/backend pytest`
- [ ] Test count: 4+ testes passam

**Tests**: unit
**Gate**: quick

---

### T10: Implementar `solicitar_nova_verificacao` (caminho POST)

**What**: `solicitar_nova_verificacao(portas, registro, nome, chave_idempotencia, hash_requisicao)` — só para `inmet`/`openai`; usa `PortaIdempotencia` (mesmo fluxo de `restaurar_dados_sinteticos`: busca → hash igual devolve o ack já registrado → hash diferente levanta `ConflitoIdempotencia`); se já em voo com outra chave, levanta `VerificacaoEmAndamento`; se `nome` for `backend`/`banco_dados`, levanta erro de validação dedicado.
**Where**: `src/backend/central_preventiva/aplicacao/prontidao.py`
**Depends on**: T9
**Reuses**: `ConflitoIdempotencia`/`PortaIdempotencia` de `aplicacao/portas_persistencia.py`, fluxo de `restaurar_dados_sinteticos`
**Requirement**: PRONT-07, PRONT-08, PRONT-09, PRONT-10, PRONT-11

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Mesma chave + mesmo hash reenviados → mesmo ack, sem novo disparo (idempotência)
- [ ] Mesma chave + hash diferente → `ConflitoIdempotencia`
- [ ] Chave diferente enquanto uma verificação já está em voo → `VerificacaoEmAndamento`
- [ ] `nome="backend"` ou `"banco_dados"` → erro de validação dedicado, sem tocar o registro
- [ ] Gate check passa: `uv run --directory src/backend pytest`
- [ ] Test count: 4+ testes passam

**Tests**: unit
**Gate**: quick

---

### T11: Criar o recurso `GET /prontidao/dependencias` e conectar à composição

**What**: `adaptadores/http/prontidao.py::criar_roteador(configuracao)` com `GET /prontidao/dependencias` (retorna as 4 linhas via `consultar_prontidao`); instanciar `RegistroProntidao` e as 4 sondas reais (com `chave_openai`/`url_base_inmet` de `Configuracao`; `SondaOpenAI` só instanciada/chamada quando há chave — decidido na composição, não na sonda) em `composicao/api.py`; incluir o roteador em `criar_aplicacao`.
**Where**: `src/backend/central_preventiva/adaptadores/http/prontidao.py`, `src/backend/central_preventiva/composicao/api.py`
**Depends on**: T5, T6, T7, T8, T9, T2
**Reuses**: Padrão `criar_roteador(configuracao)` + registro em `composicao/api.py` de `adaptadores/http/dados_sinteticos.py`
**Requirement**: PRONT-01, PRONT-02, PRONT-03, PRONT-04, PRONT-05, PRONT-06

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `GET /api/v1/prontidao/dependencias` via `TestClient(criar_aplicacao(...))` retorna as 4 linhas com `nome`/`estado`/`verificado_em`/`causa`/`impacto`/`acao_disponivel`
- [ ] Sem `OPENAI_API_KEY` configurada, a linha `openai` é `indisponivel` sem qualquer chamada de rede (dublê de `httpx` que falha o teste se for chamado)
- [ ] `backend`/`banco_dados` respondem terminal já na primeira chamada
- [ ] Resposta HTTP completa (corpo + headers) não contém a substring de uma chave OpenAI sintética configurada no teste
- [ ] Gate check passa: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright`
- [ ] Test count: 4+ testes passam

**Tests**: e2e
**Gate**: full

---

### T12: Criar o recurso `POST /prontidao/dependencias/{nome}/verificacoes`

**What**: Adicionar ao mesmo roteador o `POST /prontidao/dependencias/{nome}/verificacoes` (exige `Idempotency-Key`), traduzindo `solicitar_nova_verificacao` para `problem+json`: `202` (aceito), `404 dependencia_desconhecida`, `409 conflito_idempotencia`, `409 verificacao_em_andamento`, `422 idempotency_key_ausente`, `422 dependencia_local_nao_reverifica`.
**Where**: `src/backend/central_preventiva/adaptadores/http/prontidao.py`
**Depends on**: T10, T11
**Reuses**: `problema()` / padrão `problem+json` de `adaptadores/http/dados_sinteticos.py`
**Requirement**: PRONT-07, PRONT-08, PRONT-09, PRONT-10, PRONT-11

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `POST` sem `Idempotency-Key` → `422 idempotency_key_ausente`
- [ ] `POST` duas vezes com a mesma chave (duplo clique) → uma única verificação disparada, mesma resposta `202`
- [ ] `POST` com chave diferente enquanto uma está em voo → `409 verificacao_em_andamento`
- [ ] `POST /prontidao/dependencias/backend/verificacoes` → `422 dependencia_local_nao_reverifica`
- [ ] `POST /prontidao/dependencias/desconhecida/verificacoes` → `404 dependencia_desconhecida`
- [ ] Gate check passa: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright`
- [ ] Test count: 5+ testes passam

**Tests**: e2e
**Gate**: full

**Commit**: `feat(prontidao): expor GET e POST de prontidao das dependencias`

---

### T13: Criar o cliente `api/prontidao.ts`

**What**: `getDependencias()` (GET) e `solicitarNovaVerificacao(nome)` (POST, gera `Idempotency-Key` via `crypto.randomUUID()`), com `ErroProntidao` tipado (mesmo formato de `ErroRestauracao`).
**Where**: `src/frontend/src/api/prontidao.ts`
**Depends on**: T12
**Reuses**: Padrão de `api/dadosSinteticos.ts` (`fetch`, `problem+json` → erro tipado, falha de rede tratada)
**Requirement**: PRONT-01, PRONT-05, PRONT-06, PRONT-07, PRONT-08

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `getDependencias()` mapeia `snake_case` → `camelCase`, sucesso e falha de rede
- [ ] `solicitarNovaVerificacao(nome)` trata `202`, `404`, `409` (dois códigos), `422` (dois códigos)
- [ ] Gate check passa: `npm test --prefix src/frontend -- --run`
- [ ] Test count: 6+ testes passam

**Tests**: unit
**Gate**: quick

---

### T14: Criar a superfície de prontidão (tabela + polling + re-verificação)

**What**: Componente de página com 4 linhas (backend/DuckDB/INMET/OpenAI), `aria-live="polite"` para `Verificando`, botão de re-verificação por linha, polling GET a cada ~2s enquanto alguma linha não for terminal (cancelado ao desmontar ou quando as 4 ficam terminais), diferenciação visual (texto+ícone+cor) de `Degradada`/`Indisponível`, e toast (se usado) como reforço não exclusivo do erro terminal.
**Where**: `src/frontend/src/funcionalidades/prontidao/SuperficieProntidao.tsx`
**Depends on**: T13
**Reuses**: Estilo de `funcionalidades/dados-sinteticos/RestaurarDemonstracao.tsx`, `componentes/Modal.tsx` (padrões de acessibilidade já validados)
**Requirement**: PRONT-01, PRONT-02, PRONT-04, PRONT-10, PRONT-11

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Renderiza as 4 linhas com estado/última verificação/causa/impacto/ação
- [ ] Linha em `Verificando` tem `aria-live="polite"`; as demais linhas não perdem seu estado enquanto uma está em voo
- [ ] `Degradada` e `Indisponível` são visualmente distintas (texto + ícone + classe de cor, verificável via `getByText`/atributos, não só CSS computado)
- [ ] Falha terminal aparece na linha mesmo sem nenhum toast renderizado no teste
- [ ] Clique no botão de re-verificação chama `solicitarNovaVerificacao` com a dependência correta
- [ ] Gate check passa: `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend`
- [ ] Test count: 6+ testes passam

**Tests**: integration
**Gate**: full

---

### T15: Cobrir operação por teclado e alvo mínimo de 44×44 px

**What**: Garantir e testar navegação por `Tab`/`Shift+Tab`/`Enter` na ordem de leitura, foco visível em cada controle da superfície, e alvo mínimo de 44×44 px nos botões de re-verificação (via classe/estilo do design system, não medição de layout real — fora do alcance do `jsdom`).
**Where**: `src/frontend/src/funcionalidades/prontidao/SuperficieProntidao.tsx` (ajustes se necessário), `src/frontend/src/funcionalidades/prontidao/SuperficieProntidao.test.tsx` (extensão)
**Depends on**: T14
**Reuses**: Padrão de foco/teclado já testado em `componentes/Modal.test.tsx`
**Requirement**: PRONT-12, PRONT-13

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `userEvent.tab()` percorre os controles na ordem de leitura; cada um recebe foco visível (classe/estilo de foco presente)
- [ ] Cada botão de re-verificação carrega a classe/estilo que define o alvo mínimo de 44×44 px (verificado por presença da classe/estilo, não por medição de pixel real — `jsdom` não layouta)
- [ ] `Enter` no botão focado dispara a mesma ação que o clique
- [ ] Gate check passa: `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend`
- [ ] Test count: 3+ testes passam

**Tests**: integration
**Gate**: full

**Commit**: `feat(prontidao): adicionar superficie de prontidao com acessibilidade por teclado`

---

## Phase Execution Map

Visual representation of task ordering. Phases run in sequence, and tasks within a phase run in order:

Phases, in order: Phase 1 (T1-T3) → Phase 2 (T4-T8) → Phase 3 (T9-T10) → Phase 4 (T11-T12) → Phase 5 (T13-T15).

Complete dependency edge list (every `Depends on` relationship, one edge per line, `source -> target` meaning target depends on source):

```
T1 -> T4
T4 -> T5
T4 -> T6
T3 -> T7
T4 -> T7
T3 -> T8
T4 -> T8
T4 -> T9
T9 -> T10
T2 -> T11
T5 -> T11
T6 -> T11
T7 -> T11
T8 -> T11
T9 -> T11
T10 -> T12
T11 -> T12
T12 -> T13
T13 -> T14
T14 -> T15
```

Execution is strictly sequential - there is no intra-phase parallelism. A single agent (or batch worker) works one task at a time, in order.

**Batch packing (15 tasks → 2 batches, ~7-8 tasks each, whole phases only):**

- **Batch A** — Phase 1 (T1-T3) + Phase 2 (T4-T8) = 8 tasks
- **Batch B** — Phase 3 (T9-T10) + Phase 4 (T11-T12) + Phase 5 (T13-T15) = 7 tasks

---

## Task Granularity Check

| Task | Scope | Status |
| --- | --- | --- |
| T1: Enum `EstadoProntidao` | 1 arquivo, 1 conceito | ✅ Granular |
| T2: `Configuracao` estendida | 1 arquivo (+`.env.example`) | ✅ Granular |
| T3: `httpx` a dependência de produção | 1 arquivo, 1 linha | ✅ Granular |
| T4: Portas `portas_prontidao.py` | 1 arquivo, tipos coesos | ✅ Granular |
| T5: `SondaBackend` | 1 componente | ✅ Granular |
| T6: `SondaBancoDados` | 1 componente | ✅ Granular |
| T7: `SondaInmet` | 1 componente | ✅ Granular |
| T8: `SondaOpenAI` | 1 componente | ✅ Granular |
| T9: `RegistroProntidao` + `consultar_prontidao` | 1 arquivo, 1 fluxo (GET) | ✅ Granular |
| T10: `solicitar_nova_verificacao` | 1 função no mesmo arquivo de T9 | ✅ Granular |
| T11: `GET` + wiring de composição | 1 endpoint + wiring necessário para testá-lo | ✅ Granular |
| T12: `POST` no mesmo roteador | 1 endpoint | ✅ Granular |
| T13: `api/prontidao.ts` | 1 arquivo | ✅ Granular |
| T14: Superfície de prontidão (tabela) | 1 componente | ✅ Granular |
| T15: Teclado/alvo mínimo | Extensão do mesmo componente/teste de T14 | ✅ Granular |

---

## Diagram-Definition Cross-Check

Checked against the complete edge list in **Phase Execution Map** (every `Depends on` has a matching `source -> target` line there, and vice versa):

| Task | Depends On (task body) | Diagram Shows (full edge list) | Status |
| --- | --- | --- | --- |
| T1 | None | None | ✅ Match |
| T2 | None | None | ✅ Match |
| T3 | None | None | ✅ Match |
| T4 | T1 | `T1 -> T4` | ✅ Match |
| T5 | T4 | `T4 -> T5` | ✅ Match |
| T6 | T4 | `T4 -> T6` | ✅ Match |
| T7 | T3, T4 | `T3 -> T7`, `T4 -> T7` | ✅ Match |
| T8 | T3, T4 | `T3 -> T8`, `T4 -> T8` | ✅ Match |
| T9 | T4 | `T4 -> T9` | ✅ Match |
| T10 | T9 | `T9 -> T10` | ✅ Match |
| T11 | T2, T5, T6, T7, T8, T9 | `T2 -> T11`, `T5 -> T11`, `T6 -> T11`, `T7 -> T11`, `T8 -> T11`, `T9 -> T11` | ✅ Match |
| T12 | T10, T11 | `T10 -> T12`, `T11 -> T12` | ✅ Match |
| T13 | T12 | `T12 -> T13` | ✅ Match |
| T14 | T13 | `T13 -> T14` | ✅ Match |
| T15 | T14 | `T14 -> T15` | ✅ Match |

**Rules:**
- Nenhuma dependência aponta para uma fase posterior.
- Toda `Depends on` do corpo da tarefa tem uma aresta correspondente na lista completa do Phase Execution Map, e vice-versa.

---

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| --- | --- | --- | --- | --- |
| T1 | Domínio (`estados_prontidao.py`) | unit | unit | ✅ OK |
| T2 | Composição (`configuracao.py`) | integration | integration | ✅ OK |
| T3 | Config (`pyproject.toml`) | none | none | ✅ OK |
| T4 | Aplicação — portas (`portas_prontidao.py`) | none | none | ✅ OK |
| T5 | Adaptadores/prontidão (`sonda_backend.py`) | unit | unit | ✅ OK |
| T6 | Adaptadores/prontidão (`sonda_banco_dados.py`) | unit | unit | ✅ OK |
| T7 | Adaptadores/prontidão (`sonda_inmet.py`) | unit | unit | ✅ OK |
| T8 | Adaptadores/prontidão (`sonda_openai.py`) | unit | unit | ✅ OK |
| T9 | Aplicação — caso de uso (`prontidao.py`) | unit | unit | ✅ OK |
| T10 | Aplicação — caso de uso (`prontidao.py`) | unit | unit | ✅ OK |
| T11 | Adaptadores/http (`prontidao.py`) + composição | e2e | e2e | ✅ OK |
| T12 | Adaptadores/http (`prontidao.py`) | e2e | e2e | ✅ OK |
| T13 | Frontend — api (`prontidao.ts`) | unit | unit | ✅ OK |
| T14 | Frontend — funcionalidades (`SuperficieProntidao.tsx`) | integration | integration | ✅ OK |
| T15 | Frontend — funcionalidades (mesmo componente) | integration | integration | ✅ OK |

**Rules:**
- Nenhum `Tests: none` fora do que a matriz already define como `none` (T3, T4).
- Nenhuma tarefa adia teste para "será testado depois" — T9/T10 e T11/T12 e T14/T15 compartilham arquivo mas cada uma testa exatamente o que adiciona.
