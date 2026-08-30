# História 2.1: Coletar e normalizar dados do INMET — Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/2-1-coletar-e-normalizar-dados-do-inmet/design.md`
**Status**: Approved

---

## Test Coverage Matrix

> Generated from codebase sampling and spec ACs — confirm before Execute. Guidelines found: `AGENTS.md` (idioma PT-BR, dados sintéticos, MVP local); README.md (comandos de verificação); nenhum arquivo de threshold de cobertura dedicado — defaults fortes aplicados, calibrados pelo piso dos testes já existentes (`testes/test_prontidao_api.py`, `testes/test_sonda_inmet.py`, `testes/test_repositorio_execucoes.py`).

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| Domínio (`EventoMeteorologico`, tipos) | none | Dataclass sem lógica própria — mesmo piso de `dominio/segurado.py` (sem teste dedicado); coberto indiretamente pelos testes das camadas que o usam | `central_preventiva/dominio/evento_meteorologico.py` | build gate only |
| Migração/schema (`0002_meteorologia.sql`) | integration | Aplicação da migração e forma das tabelas novas, seguindo o piso de `test_migracoes.py` | `testes/test_migracoes.py` | `uv run --directory src/backend pytest` |
| Normalizador (domínio/aplicação) | unit | Todos os branches; 1:1 com os ACs `INMET-07..10`; toda amostra congelada válida e inválida coberta | `testes/test_normalizador_inmet.py` | `uv run --directory src/backend pytest` |
| Cliente HTTP (`ClienteInmet`) | unit | Sucesso, timeout, erro de transporte, status de erro — via `httpx.MockTransport`, mesmo padrão de `test_sonda_inmet.py`; nenhuma chamada de rede real | `testes/test_cliente_inmet.py` | `uv run --directory src/backend pytest` |
| Repositórios DuckDB (`RepositorioAreasMonitoradas`, `RepositorioEventosMeteorologicos`, `RepositorioSincronizacoes`) | integration | Caminhos-chave de escrita/leitura + erro, mesmo piso de `test_repositorio_execucoes.py`/`test_repositorio_segurados.py` | `testes/test_repositorio_*.py` | `uv run --directory src/backend pytest` |
| Caso de uso (`ServicoColetaMeteorologica`) | unit | Todos os branches; 1:1 com `INMET-03..06,11,12,16`; idempotência coberta | `testes/test_coleta_meteorologica.py` | `uv run --directory src/backend pytest` |
| Roteador HTTP (`/api/v1/meteorologia/*`) | integration | Todas as rotas: caminho feliz + erro + idempotência + CORS, mesmo padrão de `test_prontidao_api.py` (bloqueio de rede real via fixture `autouse`) | `testes/test_meteorologia_api.py` | `uv run --directory src/backend pytest` |
| Agendador (`AgendadorMeteorologico`) | unit | Dispara no boot e a cada intervalo configurado, cancelável, sem `asyncio.sleep` real (relógio/evento dublê) | `testes/test_agendador_meteorologico.py` | `uv run --directory src/backend pytest` |
| Contrato OpenAPI | integration | Sincronia do `openapi.json` com os novos endpoints, mesmo mecanismo de `test_openapi_sincronizado.py` | `testes/test_openapi_sincronizado.py` | `uv run --directory src/backend pytest` |
| Cliente API do frontend (`src/api/meteorologia.ts`) | unit | Mesmo piso de `src/api/prontidao.test.ts` — sucesso, erro tipado, ausência de dado fixo | `src/frontend/src/api/meteorologia.test.ts` | `npm test --prefix src/frontend -- --run` |
| Superfície "Fonte meteorológica" (componente React) | unit | Carregando/disponível/indisponível, tabela+lista acessível, mesmo piso de `SuperficieProntidao.test.tsx` | `src/frontend/src/funcionalidades/fonte-meteorologica/SuperficieFonteMeteorologica.test.tsx` | `npm test --prefix src/frontend -- --run` |
| Extensão da restauração (AD-014) | integration | Restore após coleta repõe estado inicial completo: tabelas fora da lista de exceções vazias, `areas_monitoradas_inmet`/`schema_migracoes` intactas, reseed correto | `testes/test_restauracao.py` (estendido) | `uv run --directory src/backend pytest` |

## Gate Check Commands

> Generated from `README.md` — confirm before Execute.

| Gate Level | When to Use | Command |
| --- | --- | --- |
| Quick (backend) | Após tasks de domínio/aplicação/adaptador isoladas | `uv run --directory src/backend pytest` |
| Quick (frontend) | Após tasks de componente/cliente API isoladas | `npm test --prefix src/frontend -- --run` |
| Full (backend) | Após tasks que tocam roteador HTTP ou schema | `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright` |
| Full (frontend) | Após tasks que tocam a superfície visível | `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend` |
| Build (fim de fase / OpenAPI) | Fim de fase, ou tasks somente de config/contrato | Backend: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright` — Frontend: `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend` (rodáveis em paralelo, stacks independentes) |

---

## Execution Plan

Phases are ordered and run sequentially — each phase completes before the next begins, and tasks within a phase execute in order.

### Phase 1: Fundação (domínio, schema, portas)

Execução em ordem T1, T2, T3. Dependência real: T3 depende de T1; T2 é independente (roda em paralelo de dependência, mas em sequência de execução).

```
T1 → T3
```

### Phase 2: Prova de contrato, normalização e adaptador HTTP

Execução em ordem T4, T5, T6. Dependência real: T5 depende de T4; T6 depende de T3 (fase anterior).

```
T4 → T5
```

### Phase 3: Persistência

```
T7
```

### Phase 4: Caso de uso e API

```
T8 → T9
```

### Phase 5: Agendamento automático e contrato OpenAPI

Execução em ordem T10, T11. Dependência real: T11 depende de T9 (fase anterior) e T10 (esta fase).

```
T10 → T11
```

### Phase 6: Frontend

```
T12 → T13
```

### Phase 7: Contrato de restauração (AD-014)

Execução de T14. Dependência real: T14 depende de T2 (Fase 1 — primeiras tabelas de coleta precisam existir para provar o wipe).

```
T14
```

---

## Task Breakdown

### T1: Criar modelo de domínio `EventoMeteorologico`

**What**: Dataclass imutável `EventoMeteorologico` (id, tipo, area, periodo_inicio, periodo_fim, intensidade, proveniencia, instante_observado) e os enums `TipoEventoMeteorologico`/`ProvenienciaEvento`, alinhados ao `CHECK` já existente na tabela `eventos_meteorologicos`.
**Where**: `src/backend/central_preventiva/dominio/evento_meteorologico.py`
**Depends on**: None
**Reuses**: `dominio/segurado.py` (padrão `@dataclass(frozen=True, slots=True)`), `dominio/estados_execucao.py` (padrão `StrEnum`)
**Requirement**: INMET-07

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `EventoMeteorologico`, `TipoEventoMeteorologico`, `ProvenienciaEvento` definidos com docstring PT-BR
- [x] Valores dos enums batem exatamente com os `CHECK` de `eventos_meteorologicos.tipo`/`proveniencia`
- [x] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: none
**Gate**: quick

---

### T2: Migração `0002_meteorologia.sql` (áreas monitoradas + histórico de sincronização)

**What**: Nova migração DuckDB criando `areas_monitoradas_inmet` e `sincronizacoes_meteorologicas` (colunas conforme `design.md`), registrada em `schema_migracoes`; atualizar `adaptadores/persistencia/README.md` com as duas tabelas novas.
**Where**: `src/backend/central_preventiva/adaptadores/persistencia/migracoes/0002_meteorologia.sql`
**Depends on**: None
**Reuses**: convenção de `migracoes/0001_schema_inicial.sql` e `ExecutorMigracoes` (nenhuma mudança de código, só novo arquivo `.sql`)
**Requirement**: INMET-11

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Migração aplica em transação própria e é idempotente (roda seguro em banco já migrado)
- [x] `adaptadores/persistencia/README.md` documenta as duas tabelas novas e suas chaves estrangeiras lógicas
- [x] `testes/test_migracoes.py` cobre a aplicação da migração `0002` (teste adicionado nesta task)
- [x] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: integration
**Gate**: quick

---

### T3: Portas de aplicação da meteorologia

**What**: Protocolos `ColetorMeteorologico`, `RepositorioAreasMonitoradas`, `RepositorioEventosMeteorologicos`, `RepositorioSincronizacoes` em `aplicacao/portas_meteorologia.py`, sem implementação concreta.
**Where**: `src/backend/central_preventiva/aplicacao/portas_meteorologia.py`
**Depends on**: T1
**Reuses**: padrão de `aplicacao/portas_prontidao.py` (portas como `Protocol`/dataclasses de resultado)
**Requirement**: INMET-07

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Cada porta declara exatamente os métodos que os componentes do `design.md` precisam (sem métodos especulativos)
- [x] Tipos de retorno usam `EventoMeteorologico`/tipos de T1
- [x] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: none
**Gate**: quick

---

### T4: Prova limitada registrada contra o INMET real + amostras congeladas

**What**: Executar uma prova limitada e pontual contra `https://apitempo.inmet.gov.br` (fora da suíte automatizada), registrar em `adaptadores/meteorologia/README.md` o endpoint escolhido, os campos consumidos, unidades, normalizações e o mapeamento para `EventoMeteorologico`; salvar como fixtures congeladas em `testes/fixtures/inmet/`: ao menos uma amostra real válida de chuva (leitura de estação com precipitação), uma amostra real inválida (campo obrigatório ausente) e uma amostra sintética de granizo derivada do cenário de contingência do conjunto demonstrativo (AD-013 — estações automáticas não reportam granizo).
**Where**: `src/backend/central_preventiva/adaptadores/meteorologia/README.md`
**Depends on**: T1
**Reuses**: nenhum (primeira integração real do domínio meteorológico); segue o padrão de documentação de contrato já usado por `adaptadores/persistencia/README.md`
**Requirement**: INMET-01, INMET-02

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `README.md` do módulo lista endpoint, parâmetros, campos consumidos, unidades e mapeamento campo-a-campo para `EventoMeteorologico`
- [x] Ao menos uma amostra JSON real válida de chuva, uma amostra real inválida (campo obrigatório ausente) e uma amostra sintética congelada de granizo (rotulada como sintética — AD-013) estão salvas em `testes/fixtures/inmet/`
- [x] O `README.md` do módulo registra explicitamente que as leituras de estações automáticas não contêm campo de granizo e que `granizo` entra só pelo cenário sintético (AD-013)
- [x] Nenhuma amostra contém dado pessoal ou sensível (dados são meteorológicos públicos, permitido por ADR-0013)
- [x] Gate check passa: `uv run --directory src/backend pytest` (nenhum teste ainda depende das fixtures — apenas confirma que nada quebrou)

**Tests**: none
**Gate**: quick

---

### T5: `NormalizadorInmet` com testes determinísticos de parsing

**What**: Implementar `NormalizadorInmet.normalizar(bruta, area) -> ResultadoNormalizacao`, convertendo a resposta bruta (formato registrado em T4) em `EventoMeteorologico` ou motivo de rejeição tipado (campo ausente / medida inválida / geografia não reconhecida), sem lançar exceção para entrada malformada.
**Where**: `src/backend/central_preventiva/adaptadores/meteorologia/normalizador_inmet.py`
**Depends on**: T4
**Reuses**: nada existente (primeiro normalizador do domínio); usa as fixtures de T4
**Requirement**: INMET-01, INMET-02, INMET-07, INMET-08, INMET-09, INMET-10

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Amostra real válida de chuva normaliza para `EventoMeteorologico` com `tipo = chuva_intensa` e `proveniencia = real_inmet`
- [x] Amostra sintética de granizo normaliza para `EventoMeteorologico` com `tipo = granizo` (a proveniência final `sintetico` é atribuída pelo caminho de cenário sintético da 2.2 — AD-013; leituras reais nunca produzem `granizo`)
- [x] Amostra inválida (campo ausente) retorna motivo de rejeição sem criar evento
- [x] Amostra com medida fora de faixa plausível retorna motivo de rejeição sem criar evento
- [x] Amostra com geografia não reconhecida (sem entrada em `areas_monitoradas_inmet`) retorna motivo de rejeição
- [x] Nenhum teste depende de rede
- [x] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: unit
**Gate**: quick

---

### T6: `ClienteInmet` (adaptador HTTP real) e `AdaptadorInmetFalso` (dublê)

**What**: Implementar `ClienteInmet.coletar(area) -> RespostaColetaInmet` (chamada `httpx.AsyncClient` real, timeout de 5s, uma única tentativa, sem tratamento especial de falha) e `AdaptadorInmetFalso`, mesma porta, devolvendo respostas programáveis para teste.
**Where**: `src/backend/central_preventiva/adaptadores/meteorologia/cliente_inmet.py`
**Depends on**: T3
**Reuses**: padrão de transporte injetável e timeout explícito de `adaptadores/prontidao/sonda_inmet.py`
**Requirement**: INMET-01, INMET-12

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `ClienteInmet` usa `Configuracao.url_base_inmet`, timeout de 5s, transporte injetável (para teste)
- [x] `ClienteInmet` não loga cabeçalhos, credenciais nem o corpo íntegro da resposta
- [x] Teste com `httpx.MockTransport`: sucesso, timeout, erro de transporte, status de erro — todos sem rede real
- [x] `AdaptadorInmetFalso` implementa a mesma porta (`ColetorMeteorologico`) e é reutilizável pelos testes de T8/T9
- [x] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: unit
**Gate**: quick

---

### T7: Repositórios DuckDB de meteorologia

**What**: `RepositorioAreasMonitoradas`, `RepositorioEventosMeteorologicos`, `RepositorioSincronizacoes` implementando as portas de T3 sobre as tabelas de T2, seguindo o padrão de conexão explícita já usado no projeto.
**Where**: `src/backend/central_preventiva/adaptadores/persistencia/repositorio_meteorologia.py`
**Depends on**: T2, T3
**Reuses**: `adaptadores/persistencia/conexao.py` (`abrir_conexao`), padrão de `repositorio_execucoes.py`/`repositorio_segurados.py`
**Requirement**: INMET-11, INMET-15

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `RepositorioEventosMeteorologicos.salvar` persiste um `EventoMeteorologico` em `eventos_meteorologicos`
- [x] `RepositorioSincronizacoes` cria/atualiza uma linha de `sincronizacoes_meteorologicas` (início, término, estado, `registros_validos`, `requisicao_id`) e lista o histórico mais recente primeiro
- [x] `RepositorioAreasMonitoradas.buscar_por_codigo_estacao` resolve a área sintética a partir do código real da estação
- [x] Teste de erro: consulta a uma sincronização/evento inexistente não lança exceção não tratada
- [x] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: integration
**Gate**: quick

---

### T8: `ServicoColetaMeteorologica` (caso de uso)

**What**: `solicitar_coleta_manual(area_id, chave_idempotencia)` (reserva idempotência, persiste sincronização em `coletando`, responde antes do processamento concluir) e `executar_coleta(area, requisicao_id)` (chama o coletor, normaliza, persiste evento ou motivo de falha, fecha a sincronização), reutilizando `RepositorioIdempotencia` já existente.
**Where**: `src/backend/central_preventiva/aplicacao/coleta_meteorologica.py`
**Depends on**: T5, T6, T7
**Reuses**: `aplicacao/portas_persistencia.py`/`RepositorioIdempotencia` (mecanismo genérico de `Idempotency-Key`, AD-002), padrão de "persistir antes de responder" de `aplicacao/restauracao.py`
**Requirement**: INMET-03, INMET-04, INMET-05, INMET-06, INMET-11, INMET-12, INMET-16

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Solicitação manual persiste a sincronização em `coletando` antes de qualquer resposta
- [x] `executar_coleta` com `AdaptadorInmetFalso` (sucesso) produz evento normalizado e sincronização `concluido`
- [x] `executar_coleta` com resposta inválida produz sincronização `falha` com `motivo_falha`, sem criar evento
- [x] Repetir `solicitar_coleta_manual` com a mesma `Idempotency-Key` não dispara nova coleta e devolve a resposta registrada
- [x] Nenhum log do caso de uso expõe corpo externo íntegro ou credenciais
- [x] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: unit
**Gate**: quick

---

### T9: Roteador HTTP `/api/v1/meteorologia/*`

**What**: `criar_roteador(configuracao) -> APIRouter` com `POST /api/v1/meteorologia/coletas` (exige `Idempotency-Key`, `202 Accepted`), `GET /api/v1/meteorologia/eventos` e `GET /api/v1/meteorologia/sincronizacoes`; incluir no `composicao/api.py`.
**Where**: `src/backend/central_preventiva/adaptadores/http/meteorologia.py`
**Depends on**: T8
**Reuses**: padrão de fábrica de roteador de `adaptadores/http/prontidao.py`/`contexto.py`; fixture `autouse` de bloqueio de rede real de `test_prontidao_api.py`
**Requirement**: INMET-05, INMET-06, INMET-15, INMET-16

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `POST /api/v1/meteorologia/coletas` sem `Idempotency-Key` retorna erro `application/problem+json`
- [x] `POST /api/v1/meteorologia/coletas` com `Idempotency-Key` nova retorna `202 Accepted`
- [x] Repetir a mesma `Idempotency-Key` devolve a resposta já registrada, sem nova chamada ao coletor (dublê instrumentado)
- [x] `GET /api/v1/meteorologia/eventos` e `GET /api/v1/meteorologia/sincronizacoes` retornam `200` com os campos exigidos pelo AC (tipo, local, período, intensidade, origem, horário / última tentativa, última válida, próxima consulta, resultados anteriores)
- [x] Roteador incluído em `composicao/api.py` com prefixo `/api/v1`
- [x] CORS restrito à origem configurada (mesmo padrão de `test_cors.py`)
- [x] Gate check passa: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright`

**Tests**: integration
**Gate**: full

---

### T10: `AgendadorMeteorologico` (coleta automática in-process)

**What**: Task `asyncio` única, iniciada no `lifespan` do FastAPI, que dispara `executar_coleta` para cada área monitorada ativa uma vez no boot e depois a cada 15 minutos (`INTERVALO_SEGUNDOS = 900`), cancelável no shutdown.
**Where**: `src/backend/central_preventiva/composicao/agendador_meteorologico.py`
**Depends on**: T8
**Reuses**: infraestrutura assíncrona já presente no FastAPI/uvicorn do projeto (AD-006); wiring do `lifespan` em `composicao/api.py`
**Requirement**: INMET-03

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Task dispara uma coleta imediatamente ao iniciar (sem esperar o primeiro intervalo)
- [x] Task dorme exatamente `INTERVALO_SEGUNDOS` entre coletas (testado com relógio/evento dublê, sem `asyncio.sleep` real)
- [x] Task é cancelável de forma limpa (sem exceção não tratada) no shutdown do lifespan
- [x] `composicao/api.py` inicia a task no `lifespan` e a cancela no encerramento
- [x] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: unit
**Gate**: quick

---

### T11: Sincronizar contrato OpenAPI

**What**: Regenerar `composicao/openapi.json` a partir da aplicação real (incluindo os endpoints de T9) e confirmar `test_openapi_sincronizado.py` verde.
**Where**: `src/backend/central_preventiva/composicao/openapi.json`
**Depends on**: T9, T10
**Reuses**: `composicao/openapi_export.py` (comando já existente, História 1.5)
**Requirement**: INMET-06, INMET-15

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `uv run --directory src/backend python -m central_preventiva.composicao.openapi_export` executado com o backend no ar
- [x] `openapi.json` versionado inclui os três endpoints novos com descrições em português brasileiro
- [x] Gate check passa: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright`

**Tests**: integration
**Gate**: build

---

### T12: Cliente HTTP do frontend para meteorologia

**What**: `src/api/meteorologia.ts` — funções tipadas (via `tipos-gerados.ts` regenerado) para `POST /coletas`, `GET /eventos`, `GET /sincronizacoes`, seguindo o mesmo formato de erro tipado de `src/api/prontidao.ts`.
**Where**: `src/frontend/src/api/meteorologia.ts`
**Depends on**: T11
**Reuses**: `src/api/clienteHttp.ts` (cliente central, História 1.5), padrão de erro tipado de `src/api/prontidao.ts`
**Requirement**: INMET-13, INMET-14

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `npm run gerar-tipos-api --prefix src/frontend` executado com o backend no ar; `tipos-gerados.ts` inclui os três endpoints novos
- [ ] Módulo expõe funções tipadas sem redeclarar manualmente campos cobertos pelo contrato
- [ ] Testes cobrem sucesso e erro tipado (mesmo piso de `src/api/prontidao.test.ts`)
- [ ] Gate check passa: `npm test --prefix src/frontend -- --run`

**Tests**: unit
**Gate**: quick

---

### T13: Superfície "Fonte meteorológica" (Monitoramento)

**What**: Componente React que exibe eventos normalizados (tipo, local, período, intensidade, origem, horário) e o histórico de sincronização (última tentativa, última válida, próxima consulta, resultados anteriores), com uma lista operável por teclado/leitor de tela equivalente a qualquer seleção visual por mapa.
**Where**: `src/frontend/src/funcionalidades/fonte-meteorologica/SuperficieFonteMeteorologica.tsx`
**Depends on**: T12
**Reuses**: padrão de `funcionalidades/prontidao/SuperficieProntidao.tsx` (estados carregando/disponível/indisponível), `componentes/` existentes de layout/tabela
**Requirement**: INMET-13, INMET-14, INMET-06

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Estado de carregamento até a primeira resposta real (sem dado fixo simulando disponibilidade)
- [ ] Lista/tabela exibe tipo, local, período, intensidade, origem e horário de cada evento
- [ ] Alternativa em lista operável por teclado/leitor de tela para a seleção de eventos (sem depender de mapa)
- [ ] Histórico de sincronização exibido (última tentativa, última válida, próxima consulta, resultados anteriores)
- [ ] Testes cobrem carregando/disponível/indisponível e navegação por teclado (mesmo piso de `SuperficieProntidao.test.tsx`)
- [ ] Gate check passa: `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`

**Tests**: unit
**Gate**: full

---

### T14: Estender a restauração ao estado inicial completo (AD-014)

**What**: Ampliar `portas.dados.restaurar()` (semeador) para, dentro da mesma transação já existente, apagar todas as tabelas enumeradas pelo catálogo do DuckDB exceto a lista explícita de exceções (`schema_migracoes` e configuração versionada — hoje só `areas_monitoradas_inmet`) antes do reseed; a lista de exceções vive como constante nomeada ao lado do semeador. Sem código novo em `aplicacao/restauracao.py` (guarda DW-002 e idempotência inalteradas).
**Where**: `src/backend/central_preventiva/adaptadores/persistencia/semeador.py`
**Depends on**: T2
**Reuses**: transação única e idempotência da restauração do Épico 1 (`aplicacao/restauracao.py`, intocada); `testes/test_restauracao.py` estendido
**Requirement**: INMET-17

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Restauração após uma coleta deixa `sincronizacoes_meteorologicas` (e qualquer tabela futura fora da lista de exceções) vazia, na mesma transação do reseed
- [ ] `areas_monitoradas_inmet` e `schema_migracoes` permanecem intactas após a restauração
- [ ] O wipe é orientado pelo catálogo (nenhuma lista manual de tabelas de execução a manter); a lista de exceções é uma constante nomeada e documentada (AD-014)
- [ ] Teste cobre reseed correto das tabelas semeadas após o wipe ampliado (mesmos IDs determinísticos)
- [ ] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: integration
**Gate**: quick

**Commit**: `feat(meteorologia): adicionar coleta e normalizacao de dados do INMET`

---

## Phase Execution Map

Phases run in sequence, and tasks within a phase run in order:

```
Phase 1:  T1 → T3
Phase 2:  T4 → T5
Phase 3:  T7
Phase 4:  T8 → T9
Phase 5:  T10 → T11
Phase 6:  T12 → T13
Phase 7:  T14
```

Grafo completo de dependências (todas as arestas `Depends on`, uma por linha, incluindo as que cruzam fases):

```
T1 → T3
T1 → T4
T4 → T5
T3 → T6
T2 → T7
T3 → T7
T5 → T8
T6 → T8
T7 → T8
T8 → T9
T8 → T10
T9 → T11
T10 → T11
T11 → T12
T12 → T13
T2 → T14
```

Ordem de execução dentro de cada fase (nem toda tarefa tem dependência intra-fase — as demais rodam em sequência, mas sem dependência de dado entre si): Fase 1 executa T1, T2, T3 nessa ordem (T2 é independente; T3 depende de T1). Fase 2 executa T4, T5, T6 nessa ordem (T6 depende de T3, da Fase 1). Fase 3 executa T7 (depende de T2 e T3, da Fase 1). Fase 4 executa T8, T9 (T8 depende de T5/T6 da Fase 2 e T7 da Fase 3). Fase 5 executa T10, T11 (T10 depende de T8 da Fase 4; T11 depende de T9 da Fase 4 e de T10 desta fase). Fase 6 executa T12, T13 (T12 depende de T11 da Fase 5). Fase 7 executa T14 (depende de T2, da Fase 1 — deixada por último por ser transversal: prova o wipe ampliado com as tabelas desta história já em uso).

Execution is strictly sequential — there is no intra-phase parallelism. A single agent (or batch worker) works one task at a time, in order.

---

## Task Granularity Check

| Task | Scope | Status |
| --- | --- | --- |
| T1: Modelo `EventoMeteorologico` | 1 arquivo, 1 conceito | ✅ Granular |
| T2: Migração `0002_meteorologia.sql` | 1 arquivo `.sql` + doc | ✅ Granular |
| T3: Portas de aplicação | 1 arquivo | ✅ Granular |
| T4: Prova + amostras congeladas | 1 doc + fixtures | ✅ Granular |
| T5: `NormalizadorInmet` | 1 componente | ✅ Granular |
| T6: `ClienteInmet` + dublê | 1 componente (porta única) | ✅ Granular |
| T7: Repositórios de meteorologia | 1 arquivo, 3 classes coesas da mesma porta | ⚠️ OK — coesas |
| T8: `ServicoColetaMeteorologica` | 1 caso de uso | ✅ Granular |
| T9: Roteador `meteorologia` | 1 componente (roteador) | ✅ Granular |
| T10: `AgendadorMeteorologico` | 1 componente | ✅ Granular |
| T11: Sincronizar OpenAPI | 1 artefato gerado | ✅ Granular |
| T12: Cliente HTTP frontend | 1 arquivo | ✅ Granular |
| T13: Superfície "Fonte meteorológica" | 1 componente | ✅ Granular |
| T14: Restauração — estado inicial completo | 1 arquivo (semeador) + teste estendido | ✅ Granular |

---

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| --- | --- | --- | --- |
| T1 | None | — | ✅ Match |
| T2 | None | — | ✅ Match |
| T3 | T1 | T1 → T3 (Phase 1 diagram) | ✅ Match |
| T4 | T1 | cross-phase (Phase 1 → Phase 2); no in-phase arrow required, validated by forward-phase check | ✅ Match |
| T5 | T4 | T4 → T5 (Phase 2 diagram) | ✅ Match |
| T6 | T3 | cross-phase (Phase 1 → Phase 2); no in-phase arrow required, validated by forward-phase check | ✅ Match |
| T7 | T2, T3 | cross-phase (Phase 1 → Phase 3); no in-phase arrow required, validated by forward-phase check | ✅ Match |
| T8 | T5, T6, T7 | cross-phase (Phase 2/3 → Phase 4); no in-phase arrow required, validated by forward-phase check | ✅ Match |
| T9 | T8 | T8 → T9 (Phase 4 diagram) | ✅ Match |
| T10 | T8 | cross-phase (Phase 4 → Phase 5); no in-phase arrow required, validated by forward-phase check | ✅ Match |
| T11 | T9, T10 | T10 → T11 in-phase (Phase 5 diagram); T9 dependency is cross-phase, validated by forward-phase check | ✅ Match |
| T12 | T11 | cross-phase (Phase 5 → Phase 6); no in-phase arrow required, validated by forward-phase check | ✅ Match |
| T13 | T12 | T12 → T13 (Phase 6 diagram) | ✅ Match |
| T14 | T2 | cross-phase (Phase 1 → Phase 7); no in-phase arrow required, validated by forward-phase check | ✅ Match |

**Rules confirmed**: every `Depends on` points backward or within the same phase; no task depends on a later phase.

---

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| --- | --- | --- | --- | --- |
| T1: Modelo `EventoMeteorologico` | Domínio (entidade) | none | none | ✅ OK |
| T2: Migração `0002` | Migração/schema | integration | integration | ✅ OK |
| T3: Portas de aplicação | Domínio (entidade/porta) | none | none | ✅ OK |
| T4: Prova + amostras | Documentação/fixtures | none (não é código executável) | none | ✅ OK |
| T5: `NormalizadorInmet` | Normalizador (domínio/aplicação) | unit | unit | ✅ OK |
| T6: `ClienteInmet` + dublê | Cliente HTTP | unit | unit | ✅ OK |
| T7: Repositórios | Repositório/data-access | integration | integration | ✅ OK |
| T8: `ServicoColetaMeteorologica` | Caso de uso (domínio/aplicação) | unit | unit | ✅ OK |
| T9: Roteador `meteorologia` | Roteador HTTP | integration | integration | ✅ OK |
| T10: `AgendadorMeteorologico` | Caso de uso (aplicação) | unit | unit | ✅ OK |
| T11: Sincronizar OpenAPI | Contrato OpenAPI | integration | integration | ✅ OK |
| T12: Cliente HTTP frontend | Cliente API frontend | unit | unit | ✅ OK |
| T13: Superfície "Fonte meteorológica" | Componente React | unit | unit | ✅ OK |
| T14: Restauração — estado inicial completo | Semeador/restauração (data-access) | integration | integration | ✅ OK |

**Rules confirmed**: nenhum `Tests: none` fora das camadas marcadas `none` na matriz; nenhuma task adia teste para outra task.
