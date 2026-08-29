# Alternar o Contexto Demonstrativo Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/1-4-alternar-o-contexto-demonstrativo/design.md`
**Status**: Approved

---

## Test Coverage Matrix

> Generated from codebase sampling (`test_repositorio_execucoes.py`, `test_dados_sinteticos_api.py`, `App.test.tsx`, `dadosSinteticos.test.ts`) and `pyproject.toml`/`package.json` - confirm before Execute. Guidelines found: none dedicated (no `AGENTS.md`/`CONTRIBUTING.md`); strong defaults applied, floor set by existing test depth in this repo (every route/repo/domain layer already has a matching test file at 1:1 granularity).

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| Domínio (backend, `dominio/*.py`) | unit | Todos os ramos; 1:1 com os ACs que dependem dele | `src/backend/testes/test_*.py` | `uv run --directory src/backend pytest` |
| Aplicação / caso de uso (backend, `aplicacao/contexto.py`) | unit | 1:1 com CTX-07/09; sucesso e `SeguradoPadraoAusente` | `src/backend/testes/test_contexto.py` | `uv run --directory src/backend pytest` |
| Repositório (backend, `adaptadores/persistencia/repositorio_segurados.py`) | integration | Caminho encontrado + não encontrado, mesmo padrão de `test_repositorio_execucoes.py` | `src/backend/testes/test_repositorio_segurados.py` | `uv run --directory src/backend pytest` |
| Rota HTTP (backend, `adaptadores/http/contexto.py`) | e2e | Todas as rotas do escopo: sucesso (200) + falha (503) | `src/backend/testes/test_contexto_api.py` | `uv run --directory src/backend pytest` |
| Cliente HTTP (frontend, `api/contexto.ts`) | unit | Sucesso, erro `problem+json`, falha de rede - mesmo padrão de `api/dadosSinteticos.test.ts` | `src/frontend/src/api/contexto.test.ts` | `npm test --prefix src/frontend -- --run` |
| Provider de contexto (frontend, `contexto/PerfilContexto.tsx`) | unit | 1:1 com CTX-04/08/10/11/12/13/14/15; todo edge case de `localStorage` | `src/frontend/src/contexto/PerfilContexto.test.tsx` | `npm test --prefix src/frontend -- --run` |
| Componentes React isolados (`componentes/*.tsx`, `funcionalidades/segurado/*.tsx`) | unit | Caminho feliz + estado de indisponibilidade + interação por teclado | `src/frontend/src/componentes/*.test.tsx`, `src/frontend/src/funcionalidades/segurado/*.test.tsx` | `npm test --prefix src/frontend -- --run` |
| Shell integrado (`App.tsx`) | integration | Todas as ACs restantes: as duas direções de alternância, limpeza de contexto, reload, contexto inválido, larguras suportadas, teclado - mesmo padrão de `App.test.tsx` atual | `src/frontend/src/App.test.tsx` | `npm test --prefix src/frontend -- --run` |

## Gate Check Commands

> Generated from `README.md` (linhas 41-52) - confirma antes do Execute.

| Gate Level | When to Use | Command |
| --- | --- | --- |
| Quick (backend) | Após tarefas de backend com só testes unitários/integração de repositório | `uv run --directory src/backend pytest` |
| Quick (frontend) | Após tarefas de frontend com só testes unitários de componente/cliente | `npm test --prefix src/frontend -- --run` |
| Full (backend) | Após tarefas que expõem ou alteram rota HTTP | `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright` |
| Full (frontend) | Após tarefas que alteram `App.tsx` ou compõem múltiplos componentes | `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend` |
| Build | Ao final de cada fase e ao final da história | Full (backend) **e** Full (frontend) em sequência |

---

## Execution Plan

Phases are ordered and run sequentially - each phase completes before the next begins, and tasks within a phase execute in order.

Within each phase, tasks with no dependency edge between them still execute in the listed order (single worker, one task at a time) - the diagrams below show only real `Depends on` edges, per the Diagram-Definition Cross-Check rules.

### Phase 1: Fundação do backend

```
T1 → T2
T3 → T4
T1 → T5
T3 → T5
T4 → T5
T5 → T6
```

Execution order: T1, T2, T3, T4, T5, T6.

### Phase 2: Fundação do frontend

```
T7 → T11
T8 → T11
T8 → T12
```

Execution order: T7, T8, T9, T10, T11, T12, T13 (T9, T10, T13 have no dependency edges - they are independent leaves executed in this order).

### Phase 3: Integração do shell

```
T8 → T14
T9 → T14
T10 → T14
T11 → T14
T12 → T14
T13 → T14
T14 → T15
```

Execution order: T14, T15.

---

## Task Breakdown

### T1: Extrair `identificador_demonstracao` para o domínio

**What**: Criar `dominio/identificadores_demonstracao.py` com a função pura `identificador_demonstracao(nome: str) -> UUID` (mesma implementação `uuid5` hoje em `semeador.py:17-20`) e a constante `SEGURADO_PADRAO = identificador_demonstracao("segurado/chuva-elegivel")`.
**Where**: `src/backend/central_preventiva/dominio/identificadores_demonstracao.py`
**Depends on**: None
**Reuses**: lógica de `adaptadores/persistencia/semeador.py:17-20` (movida, não duplicada)
**Requirement**: CTX-07 (suporte)

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Módulo criado, sem importar `fastapi`/`pydantic`/`duckdb`/`aplicacao`/`adaptadores`/`composicao` (respeita `test_camadas.py`)
- [x] `identificador_demonstracao("segurado/chuva-elegivel")` produz o mesmo UUID que `semeador.py` produzia antes da extração
- [x] Teste novo cobre determinismo (mesma entrada → mesmo UUID) e unicidade (entradas diferentes → UUIDs diferentes)
- [x] Gate check passes: `uv run --directory src/backend pytest`
- [x] Test count: 2+ novos testes passam

**Tests**: unit
**Gate**: quick (backend)

**Commit**: `refactor(dominio): extrair identificador_demonstracao para o dominio`

---

### T2: Apontar `semeador.py` para o novo módulo de domínio

**What**: Remover a definição local de `identificador_demonstracao` em `semeador.py` e importar de `dominio.identificadores_demonstracao`.
**Where**: `src/backend/central_preventiva/adaptadores/persistencia/semeador.py`
**Depends on**: T1
**Reuses**: `dominio.identificadores_demonstracao` (T1)
**Requirement**: CTX-07 (suporte)

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] `semeador.py` não define mais `identificador_demonstracao` localmente
- [x] Nenhuma duplicação de lógica de UUID determinístico permanece no repositório
- [x] Testes existentes de `test_semeador.py` continuam passando sem alteração de asserts (comportamento inalterado)
- [x] Gate check passes: `uv run --directory src/backend pytest`
- [x] Test count: suíte de `test_semeador.py` (já existente) permanece 100% verde

**Tests**: unit (verificação de regressão nos testes já existentes; nenhum teste novo exigido para esta tarefa)
**Gate**: quick (backend)

**Commit**: `refactor(persistencia): reusar identificador_demonstracao do dominio no semeador`

---

### T3: Criar o modelo de domínio `Segurado`

**What**: Criar `dominio/segurado.py` com `@dataclass(frozen=True) class Segurado: id: UUID; nome: str`.
**Where**: `src/backend/central_preventiva/dominio/segurado.py`
**Depends on**: None
**Reuses**: estilo dos demais módulos de `dominio/` (`estados_execucao.py`, `estados_prontidao.py`)
**Requirement**: CTX-07 (suporte)

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] `Segurado` criado como dataclass imutável com `id: UUID` e `nome: str`
- [x] Módulo não importa `fastapi`/`pydantic`/`duckdb`/`aplicacao`/`adaptadores`/`composicao` (respeita `test_camadas.py`)
- [x] Gate check passes: `uv run --directory src/backend pytest`

**Tests**: none (entidade pura, sem lógica de ramificação - conforme o default da matriz para camada de entidade/config)
**Gate**: quick (backend)

**Commit**: `feat(dominio): adicionar modelo Segurado`

---

### T4: Criar `RepositorioSegurados`

**What**: Criar `RepositorioSegurados.buscar_por_id(id: UUID) -> Segurado | None`, consultando `SELECT id, nome FROM segurados WHERE id = ?`.
**Where**: `src/backend/central_preventiva/adaptadores/persistencia/repositorio_segurados.py`
**Depends on**: T3
**Reuses**: `abrir_conexao` (`conexao.py`), mesmo padrão de `repositorio_execucoes.py`
**Requirement**: CTX-07

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] `buscar_por_id` devolve um `Segurado` quando o id existe na tabela `segurados`
- [x] `buscar_por_id` devolve `None` quando o id não existe (tabela vazia ou id desconhecido)
- [x] Teste usa banco DuckDB temporário migrado (`ExecutorMigracoes`), mesmo padrão de `test_repositorio_execucoes.py`
- [x] Gate check passes: `uv run --directory src/backend pytest`
- [x] Test count: 2+ novos testes passam (encontrado, não encontrado)

**Tests**: integration
**Gate**: quick (backend)

**Commit**: `feat(persistencia): adicionar RepositorioSegurados`

---

### T5: Criar o caso de uso `consultar_segurado_padrao`

**What**: Criar `aplicacao/contexto.py` com `PortasContexto` (protocolo com `segurados: buscar_por_id`), a exceção `SeguradoPadraoAusente` e a função `consultar_segurado_padrao(portas: PortasContexto) -> Segurado`, usando `SEGURADO_PADRAO` (T1).
**Where**: `src/backend/central_preventiva/aplicacao/contexto.py`
**Depends on**: T1, T3, T4
**Reuses**: estilo de `Protocol` de `aplicacao/portas_prontidao.py`/`portas_persistencia.py`
**Requirement**: CTX-07, CTX-09

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] `consultar_segurado_padrao` devolve o `Segurado` quando `buscar_por_id(SEGURADO_PADRAO)` encontra o registro
- [x] `consultar_segurado_padrao` levanta `SeguradoPadraoAusente` quando `buscar_por_id` devolve `None`
- [x] Teste usa um dublê de `PortasContexto` (sem DuckDB real), mesmo padrão de testes de caso de uso já existentes (`test_prontidao.py`, `test_restauracao.py`)
- [x] Gate check passes: `uv run --directory src/backend pytest`
- [x] Test count: 2+ novos testes passam (encontrado, ausente)

**Tests**: unit
**Gate**: quick (backend)

**Commit**: `feat(aplicacao): adicionar caso de uso consultar_segurado_padrao`

---

### T6: Expor `GET /api/v1/segurados/padrao`

**What**: Criar `adaptadores/http/contexto.py` com `criar_roteador(configuracao) -> APIRouter` expondo `GET /segurados/padrao` (200 com `{id, nome}`; 503 `problem+json` com `codigo="segurado_padrao_ausente"` quando `SeguradoPadraoAusente` for levantada) e registrar o roteador em `composicao/api.py`, junto aos existentes.
**Where**: `src/backend/central_preventiva/adaptadores/http/contexto.py`
**Depends on**: T5
**Reuses**: `problema()`/`TIPO_PROBLEMA`/estrutura de `RespostaX`/`ProblemaX` de `prontidao.py` e `dados_sinteticos.py`
**Requirement**: CTX-07, CTX-09

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] `GET /api/v1/segurados/padrao` devolve `200` com `{"id": "...", "nome": "..."}` quando o segurado padrão existe
- [x] `GET /api/v1/segurados/padrao` devolve `503` `application/problem+json` com `codigo="segurado_padrao_ausente"` quando os dados sintéticos ainda não foram semeados
- [x] Roteador registrado em `composicao/api.py` com `prefix="/api/v1"`, mesmo padrão dos roteadores existentes
- [x] Teste usa `TestClient` sobre banco temporário migrado (e semeado / não semeado), mesmo padrão de `test_dados_sinteticos_api.py`
- [x] Gate check passes: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright`
- [x] Test count: 2+ novos testes passam (200, 503)

**Tests**: e2e
**Gate**: full (backend)

**Commit**: `feat(http): expor GET /api/v1/segurados/padrao`

---

### T7: Criar o cliente HTTP `api/contexto.ts`

**What**: Criar `getSeguradoPadrao(): Promise<SeguradoPadrao>` e `ErroContexto`, mirando `api/prontidao.ts` (mesma estrutura de `lerProblema`, `FALHA_DE_REDE`, `FALHA_INESPERADA`), consumindo `GET /api/v1/segurados/padrao`.
**Where**: `src/frontend/src/api/contexto.ts`
**Depends on**: None (contrato já fechado no design; não depende do backend estar rodando para ser escrito e testado com `fetch` mockado)
**Reuses**: estrutura completa de `src/frontend/src/api/prontidao.ts`
**Requirement**: CTX-07, CTX-09

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `getSeguradoPadrao()` resolve com `{id, nome}` quando o backend responde 200
- [ ] `getSeguradoPadrao()` rejeita com `ErroContexto` tipado quando o backend responde `503 problem+json`
- [ ] `getSeguradoPadrao()` rejeita com `ErroContexto` (`FALHA_DE_REDE`) quando `fetch` lança
- [ ] Teste usa `fetch` mockado via `vi.stubGlobal`, mesmo padrão de `api/dadosSinteticos.test.ts`
- [ ] Gate check passes: `npm test --prefix src/frontend -- --run`
- [ ] Test count: 3+ novos testes passam

**Tests**: unit
**Gate**: quick (frontend)

**Commit**: `feat(api): adicionar cliente do segurado padrao`

---

### T8: Criar `PerfilContexto` (provider e hook)

**What**: Criar `contexto/PerfilContexto.tsx` com `Perfil`, `Superficie`, `SUPERFICIES_POR_PERFIL`, `PerfilProvider` e `usePerfilContexto()` (`perfil`, `superficieAtiva`, `alternarPerfil`, `selecionarSuperficie`, `superficieValida`), persistindo só `perfil` em `localStorage` sob a chave `central-preventiva.perfil`.
**Where**: `src/frontend/src/contexto/PerfilContexto.tsx`
**Depends on**: None
**Reuses**: nenhum componente existente (peça nova central da história)
**Requirement**: CTX-04, CTX-08, CTX-10, CTX-11, CTX-12, CTX-13, CTX-14, CTX-15

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Sem valor salvo em `localStorage`, `perfil` inicial é `"administrador"`
- [ ] Valor salvo válido (`"segurado"` ou `"administrador"`) é restaurado como `perfil` inicial
- [ ] Valor salvo inválido/corrompido é tratado como ausência de preferência (`"administrador"`)
- [ ] `alternarPerfil` grava o novo valor em `localStorage` e nunca chama nenhum endpoint de rede
- [ ] `alternarPerfil` redefine `superficieAtiva` para a primeira superfície de `SUPERFICIES_POR_PERFIL[novoPerfil]`, mesmo que a superfície anterior não exista no novo perfil (CTX-04: limpeza de estado incompatível)
- [ ] `selecionarSuperficie` só aceita valores presentes em `SUPERFICIES_POR_PERFIL[perfil]`; um valor fora da lista é rejeitado e `superficieValida` reporta `false` até a próxima seleção válida
- [ ] Gate check passes: `npm test --prefix src/frontend -- --run`
- [ ] Test count: 8+ novos testes passam (default, restauração, valor corrompido, alternância nas duas direções, limpeza de estado, seleção inválida)

**Tests**: unit
**Gate**: quick (frontend)

**Commit**: `feat(contexto): adicionar PerfilContexto com persistencia local`

---

### T9: Criar `FaixaDemonstracao`

**What**: Extrair a faixa fixa "Ambiente educacional · Dados sintéticos · Sem envio real" de `App.tsx:110-113` para um componente próprio, sem nenhum controle de fechamento.
**Where**: `src/frontend/src/componentes/FaixaDemonstracao.tsx`
**Depends on**: None
**Reuses**: markup/CSS de `App.tsx:110-113`
**Requirement**: CTX-02

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Componente renderiza os três textos fixos da faixa
- [ ] Nenhum elemento interativo de fechamento existe no componente
- [ ] Gate check passes: `npm test --prefix src/frontend -- --run`
- [ ] Test count: 1+ novo teste passa

**Tests**: unit
**Gate**: quick (frontend)

**Commit**: `feat(componentes): extrair FaixaDemonstracao`

---

### T10: Criar `ContextoInconsistente`

**What**: Criar `ContextoInconsistente({ perfil, aoVoltar })`, exibindo uma mensagem explicando a inconsistência e um botão que chama `aoVoltar`.
**Where**: `src/frontend/src/componentes/ContextoInconsistente.tsx`
**Depends on**: None
**Reuses**: nenhum
**Requirement**: CTX-13, CTX-14, CTX-15

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Componente exibe uma mensagem explicando o bloqueio, sem mostrar nenhum dado de superfície
- [ ] Botão "Voltar para a Visão geral" (ou rótulo equivalente definido no design) chama `aoVoltar` ao ser ativado por clique e por `Enter`
- [ ] Gate check passes: `npm test --prefix src/frontend -- --run`
- [ ] Test count: 2+ novos testes passam

**Tests**: unit
**Gate**: quick (frontend)

**Commit**: `feat(componentes): adicionar ContextoInconsistente`

---

### T11: Criar `BarraContexto`

**What**: Criar `BarraContexto()` usando `usePerfilContexto()` para mostrar perfil ativo e data/hora de referência sempre, e (só quando `perfil === 'segurado'`) o nome do segurado padrão via `getSeguradoPadrao()` (estado de carregando/indisponível com nova tentativa em caso de falha), com o seletor "Visualizar como" e uma região `aria-live="polite"` anunciando a troca de perfil.
**Where**: `src/frontend/src/componentes/BarraContexto.tsx`
**Depends on**: T7, T8
**Reuses**: markup/CSS de `App.tsx:67-71`
**Requirement**: CTX-01, CTX-07, CTX-09, CTX-19, CTX-20

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Mostra o perfil ativo e a data/hora de referência em qualquer perfil
- [ ] No perfil Segurado, busca e mostra o nome do segurado padrão retornado por `getSeguradoPadrao()`
- [ ] No perfil Segurado, se `getSeguradoPadrao()` rejeitar, mostra um estado de indisponibilidade com causa e um botão de nova tentativa, nunca um nome fixo/vazio
- [ ] Ativar "Visualizar como" chama `alternarPerfil` com o perfil oposto ao atual
- [ ] Uma região `aria-live="polite"` anuncia o texto do perfil após cada troca
- [ ] O perfil é comunicado por texto + ícone, não só por cor (asserção de texto/ícone presentes, não de estilo)
- [ ] Gate check passes: `npm test --prefix src/frontend -- --run`
- [ ] Test count: 6+ novos testes passam

**Tests**: unit
**Gate**: quick (frontend)

**Commit**: `feat(componentes): adicionar BarraContexto com seletor de perfil`

---

### T12: Criar `NavegacaoLateral`

**What**: Criar `NavegacaoLateral()` usando `usePerfilContexto()` para listar os itens do perfil ativo (Administrador: "Prontidão", "Restaurar dados sintéticos"; Segurado: "Visão geral") e chamar `selecionarSuperficie` ao ativar um item, com ordem de leitura e foco visível de 3 px.
**Where**: `src/frontend/src/componentes/NavegacaoLateral.tsx`
**Depends on**: T8
**Reuses**: markup/CSS de `App.tsx:40-66`
**Requirement**: CTX-03, CTX-05, CTX-18, CTX-20

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] No perfil Administrador, mostra somente "Prontidão" e "Restaurar dados sintéticos"
- [ ] No perfil Segurado, mostra somente "Visão geral"
- [ ] Ativar um item por clique ou por `Enter` (com foco por `Tab`) chama `selecionarSuperficie` com o valor correspondente
- [ ] O item correspondente à `superficieAtiva` recebe `aria-current="page"`
- [ ] Gate check passes: `npm test --prefix src/frontend -- --run`
- [ ] Test count: 4+ novos testes passam

**Tests**: unit
**Gate**: quick (frontend)

**Commit**: `feat(componentes): adicionar NavegacaoLateral sensivel ao perfil`

---

### T13: Extrair `VisaoGeralSegurado`

**What**: Extrair o conteúdo estático de `App.tsx:78-109` (visão geral, alerta, ações preventivas, painel contextual) para `VisaoGeralSegurado()`, removendo o nome hardcoded "Marina Costa" (o nome real passa a vir de `BarraContexto`).
**Where**: `src/frontend/src/funcionalidades/segurado/VisaoGeralSegurado.tsx`
**Depends on**: None
**Reuses**: markup/CSS de `App.tsx:78-109`
**Requirement**: CTX-08

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Componente renderiza o alerta, as ações preventivas e o painel contextual sem nenhuma referência a "Marina Costa"
- [ ] Nenhum dado de segurado (nome) é renderizado por este componente - vem só da `BarraContexto`
- [ ] Gate check passes: `npm test --prefix src/frontend -- --run`
- [ ] Test count: 1+ novo teste passa

**Tests**: unit
**Gate**: quick (frontend)

**Commit**: `feat(segurado): extrair VisaoGeralSegurado`

---

### T14: Recompor `App.tsx` como shell do contexto demonstrativo

**What**: Reescrever `App.tsx` para envolver a árvore em `PerfilProvider`, renderizar `FaixaDemonstracao` e `BarraContexto` em toda superfície, `NavegacaoLateral`, e trocar o conteúdo principal por `superficieAtiva` (`'prontidao'` → `SuperficieProntidao`, `'restaurar-dados-sinteticos'` → `RestaurarDemonstracao`, `'visao-geral'` → `VisaoGeralSegurado`), renderizando `ContextoInconsistente` quando `superficieValida` for falso, preservando o aviso de largura < 1024 px já existente.
**Where**: `src/frontend/src/App.tsx`
**Depends on**: T8, T9, T10, T11, T12, T13
**Reuses**: `SuperficieProntidao` (já existente), `RestaurarDemonstracao` (já existente), toda a Fase 2
**Requirement**: CTX-01 a CTX-20 (composição)

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `App.tsx` não contém mais markup estático de navegação, barra de contexto, faixa ou conteúdo do Segurado diretamente - só composição dos componentes da Fase 2
- [ ] Trocar de perfil no seletor troca a navegação e o conteúdo principal de acordo com `SUPERFICIES_POR_PERFIL`
- [ ] O aviso de largura < 1024 px continua funcionando (comportamento inalterado de `App.tsx:27-33,73-77`)
- [ ] Gate check passes: `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`

**Tests**: integration (cobertas em T15 - ver "Resolving compilation dependencies": o teste completo do shell só é executável após esta composição existir; T15 absorve a bateria de testes que valida T14, ver nota de escopo abaixo)
**Gate**: full (frontend)

**Commit**: `feat(app): compor o shell com contexto demonstrativo real`

> **Nota de escopo (mescla à frente):** os testes de comportamento do shell integrado (as duas direções de alternância, limpeza de contexto, reload, contexto inválido, larguras suportadas, teclado) só são executáveis depois que `App.tsx` compõe todas as peças. Por isso ficam em T15, não nesta tarefa - T14 entrega a composição; T15 entrega e executa a bateria que a verifica. Nenhum código desta tarefa fica sem teste: a suíte de T15 cobre exatamente o que T14 produz.

---

### T15: Reescrever `App.test.tsx` com a bateria de comportamento do contexto demonstrativo

**What**: Substituir o `App.test.tsx` atual (que testa a shell estática antiga) por uma bateria cobrindo as duas direções de alternância de perfil, a limpeza de contexto incompatível (modal de restauração desmontado ao trocar), a persistência via reload (mock de `localStorage`), o valor corrompido em `localStorage`, o bloqueio de contexto inconsistente, as larguras suportadas (1024 px, 1279 px, largura ampla) e não suportada (< 1024 px), e a operação por teclado com anúncio `aria-live`.
**Where**: `src/frontend/src/App.test.tsx`
**Depends on**: T14
**Reuses**: estrutura de `definirLargura`/`afterEach` já existente em `App.test.tsx`
**Requirement**: CTX-01 a CTX-20 (verificação)

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Teste cobre Administrador → Segurado e Segurado → Administrador, verificando a navegação exibida em cada perfil (CTX-03, CTX-05)
- [ ] Teste cobre que abrir o modal "Restaurar dados sintéticos" e trocar de perfil fecha o modal (via desmontagem) sem chamar nenhuma mutação de dados (CTX-04)
- [ ] Teste cobre que nenhum texto de interface descreve a troca como login/autenticação/autorização (CTX-06)
- [ ] Teste cobre que o perfil sobrevive a uma nova montagem do componente simulando reload, lendo o valor gravado em `localStorage` (CTX-10, CTX-11)
- [ ] Teste cobre que um valor corrompido em `localStorage` resulta no perfil "Administrador" (CTX-11 edge case)
- [ ] Teste cobre o bloqueio via `ContextoInconsistente` e o retorno à Visão geral do perfil ativo (CTX-13, CTX-14, CTX-15)
- [ ] Teste cobre as larguras 1024 px, 1279 px e uma largura ampla mantendo navegação e seletor operáveis, e a largura < 1024 px exibindo o aviso sem perda de função (CTX-16, CTX-17)
- [ ] Teste cobre navegação só por teclado (`Tab`/`Shift+Tab`/`Enter`) até o seletor e um item de navegação, com foco visível e anúncio `aria-live` (CTX-18, CTX-19)
- [ ] Gate check passes: `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`
- [ ] Test count: 10+ testes passam nesta suíte (nenhuma exclusão silenciosa do que já existia em `App.test.tsx`)

**Tests**: integration
**Gate**: build (frontend Full + backend Full, ao final da história)

**Commit**: `test(app): cobrir alternancia de contexto demonstrativo no shell integrado`

---

## Phase Execution Map

```
Phase 1 → Phase 2 → Phase 3

Phase 1:  T1 → T2
          T3 → T4 → T5 → T6
          T1 → T5
          T3 → T5

Phase 2:  T7 → T11
          T8 → T11
          T8 → T12
          (T9, T10, T13 run independently, in listed order)

Phase 3:  T8 → T14
          T9 → T14
          T10 → T14
          T11 → T14
          T12 → T14
          T13 → T14
          T14 → T15
```

Execution is strictly sequential - there is no intra-phase parallelism. A single agent (or batch worker) works one task at a time, in the order listed under each phase's "Execution order" above.

**Batching**: 15 tasks total, above the ~8-task single-batch threshold. Packed by whole phases into 3 batches: Batch 1 = Phase 1 (6 tasks), Batch 2 = Phase 2 (7 tasks), Batch 3 = Phase 3 (2 tasks). Offer sub-agent delegation before starting Execute.

---

## Task Granularity Check

| Task | Scope | Status |
| --- | --- | --- |
| T1: Extrair identificador_demonstracao | 1 módulo novo | ✅ Granular |
| T2: Apontar semeador.py ao novo módulo | 1 arquivo editado | ✅ Granular |
| T3: Criar modelo Segurado | 1 módulo novo | ✅ Granular |
| T4: Criar RepositorioSegurados | 1 classe/arquivo | ✅ Granular |
| T5: Criar caso de uso consultar_segurado_padrao | 1 módulo/caso de uso | ✅ Granular |
| T6: Expor GET /segurados/padrao | 1 endpoint (+ registro de 1 linha em api.py) | ✅ Granular |
| T7: Criar cliente api/contexto.ts | 1 arquivo | ✅ Granular |
| T8: Criar PerfilContexto | 1 componente/hook | ✅ Granular |
| T9: Criar FaixaDemonstracao | 1 componente | ✅ Granular |
| T10: Criar ContextoInconsistente | 1 componente | ✅ Granular |
| T11: Criar BarraContexto | 1 componente | ✅ Granular |
| T12: Criar NavegacaoLateral | 1 componente | ✅ Granular |
| T13: Extrair VisaoGeralSegurado | 1 componente | ✅ Granular |
| T14: Recompor App.tsx | 1 arquivo (composição) | ✅ Granular |
| T15: Reescrever App.test.tsx | 1 arquivo (bateria de testes) | ✅ Granular |

---

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| --- | --- | --- | --- |
| T1 | None | None | ✅ Match |
| T2 | T1 | T1 → T2 | ✅ Match |
| T3 | None | None | ✅ Match |
| T4 | T3 | T3 → T4 | ✅ Match |
| T5 | T1, T3, T4 | T1 → T5, T3 → T5, T4 → T5 | ✅ Match |
| T6 | T5 | T5 → T6 | ✅ Match |
| T7 | None | None | ✅ Match |
| T8 | None | None | ✅ Match |
| T9 | None | None | ✅ Match |
| T10 | None | None | ✅ Match |
| T11 | T7, T8 | T7 → T11, T8 → T11 | ✅ Match |
| T12 | T8 | T8 → T12 | ✅ Match |
| T13 | None | None | ✅ Match |
| T14 | T8, T9, T10, T11, T12, T13 | T8 → T14, T9 → T14, T10 → T14, T11 → T14, T12 → T14, T13 → T14 | ✅ Match |
| T15 | T14 | T14 → T15 | ✅ Match |

**Rules check**: nenhuma tarefa depende de uma tarefa de fase posterior; toda dependência aponta para trás ou dentro da mesma fase. ✅

---

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| --- | --- | --- | --- | --- |
| T1: Extrair identificador_demonstracao | Domínio | unit | unit | ✅ OK |
| T2: Apontar semeador.py ao novo módulo | Domínio/Persistência (só reuso, sem lógica nova) | unit (regressão via suíte existente) | unit | ✅ OK |
| T3: Criar modelo Segurado | Entidade/domínio | none | none | ✅ OK |
| T4: Criar RepositorioSegurados | Repositório | integration | integration | ✅ OK |
| T5: Criar caso de uso consultar_segurado_padrao | Aplicação | unit | unit | ✅ OK |
| T6: Expor GET /segurados/padrao | Rota HTTP | e2e | e2e | ✅ OK |
| T7: Criar cliente api/contexto.ts | Cliente HTTP (frontend) | unit | unit | ✅ OK |
| T8: Criar PerfilContexto | Provider de contexto | unit | unit | ✅ OK |
| T9: Criar FaixaDemonstracao | Componente React | unit | unit | ✅ OK |
| T10: Criar ContextoInconsistente | Componente React | unit | unit | ✅ OK |
| T11: Criar BarraContexto | Componente React | unit | unit | ✅ OK |
| T12: Criar NavegacaoLateral | Componente React | unit | unit | ✅ OK |
| T13: Extrair VisaoGeralSegurado | Componente React | unit | unit | ✅ OK |
| T14: Recompor App.tsx | Shell integrado | integration | integration (mesclado à frente para T15, ver nota de escopo em T14) | ✅ OK |
| T15: Reescrever App.test.tsx | Shell integrado | integration | integration | ✅ OK |

Nenhuma violação: todo `Tests: none` corresponde a uma camada que a matriz marca como `none` (só T3); a mescla à frente de T14→T15 segue exatamente o procedimento de "Resolving compilation dependencies" do processo de Tasks, e nenhum código fica sem teste.
