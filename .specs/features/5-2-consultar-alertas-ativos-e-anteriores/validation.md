# História 5.2: Consultar alertas ativos e anteriores — Validation (rodada 2)

**Date**: 2026-09-05
**Spec**: `.specs/features/5-2-consultar-alertas-ativos-e-anteriores/spec.md`
**Diff range (feature, ponta a ponta)**: `8e11b9e..HEAD` (`19b29ce`, `dec4419`, `e25ddbf`, `b2138c8`, `c1a9bd2`, `850aa5b`)
**Diff range (correções desta rodada)**: `b2138c8..HEAD`
**Verifier**: sub-agente independente (autor ≠ verificador), somente leitura sobre a árvore real
**Rodada**: 2 de no máximo 3 (rodada 1 = ❌ FAIL com 5 mutantes sobreviventes / 7 tarefas de correção)

**Veredito**: ✅ **PASS** — os 5 mutantes que sobreviveram na rodada 1 estão mortos, as 7
tarefas de correção landaram de fato (verificadas no código, não no texto do commit), os
dois gates de Build saem com código 0 e 12 injeções de falha de comportamento (5 delas
inéditas, sobre código que a rodada 1 não estressou) foram todas mortas.

Este relatório é auto-contido: nenhuma parte depende de ler a rodada 1.

---

## Task Completion

| Task | Status | Notes |
| --- | --- | --- |
| T1 `listar_todas_por_segurado` | ✅ Done | `19b29ce`; `ORDER BY e.criado_em DESC, e.id DESC` (`repositorio_elegibilidade.py:243`); desempate agora exercitado (M10 morto) |
| T2 `ServicoListaAlertasSegurado` | ✅ Done | `dec4419`; 2 SPEC_DEVIATIONs marcadas e verificadas abaixo |
| T3 Endpoints HTTP | ✅ Done | `e25ddbf` + `c1a9bd2`; `_resposta_alerta` agora tem asserção campo a campo com valores não colidentes (M5/M5c/M6/M6b/M6c mortos) |
| T4 Superfície de Alertas | ✅ Done | `b2138c8` + `c1a9bd2`; foco discriminante, ícones distintos, `aria-live` asserido, estado vazio com ação real (M7/M8/M9/M12 mortos) |

---

## Verificação das 7 correções da rodada 1

| # | Achado da rodada 1 | Landou? | Evidência independente |
| --- | --- | --- | --- |
| Fix 1 (Blocker) | `_resposta_alerta` sem asserção discriminante | ✅ Sim | `test_lista_alertas_segurado_api.py:193-203` assere 10 campos de `RespostaAlerta`; a fixture `criar_evento` (`:79-104`) agora devolve o `EventoMeteorologico` inteiro e usa `instante_observado = periodo_inicio - 1h`, tornando os três instantes **distintos entre si** — pré-condição sem a qual uma troca seria indetectável. Dois casos dedicados: origem sintética (`:206-223`) e fonte degradada (`:226-253`) |
| Fix 2 (Major) | Restauração de foco testada com lista de 1 item | ✅ Sim | `SuperficieAlertas.test.tsx:230-251` monta 3 itens com `elegibilidadeId` distintos, assere `toHaveLength(3)`, clica no **último** (`botoesVerDetalhe[2]`) e assere `document.getElementById('botao-detalhe-item-3')).toHaveFocus()` — "botão de origem" e "primeiro botão" passam a ser distinguíveis |
| Fix 3 (Major) | Distinção por ícone sem asserção | ✅ Sim | `SuperficieAlertas.tsx:60-76` dá `data-icone-nome` a cada um dos três ícones; `SuperficieAlertas.test.tsx:119-123` assere `Set(...).size === 3` |
| Fix 4 (Major) | "Próxima ação válida" do ALERTAS-02 não implementada | ✅ Sim, e é ação real | `SuperficieAlertas.tsx:342-344` — `<button onClick={() => void carregarLista()}>Atualizar</button>`; `carregarLista` (`:117-130`) é o mesmo `useCallback` que faz a consulta inicial. **Não é rótulo decorativo**: o teste `:126-137` clica no botão com a lista mockada para devolver um item e assere que `Ativo` aparece — a lista foi de fato reconsultada. Confirmado por mutação (M9) |
| Fix 5 (Minor) | Edge case "simulado ≠ visualizado" sem teste | ✅ Sim | `SuperficieAlertas.test.tsx:193-217` — detalhe `anterior` com marco `simulacao_concluida` e sem marco de visualização; assere `findByText(/simulacao_concluida/)` presente e `queryByText(/[Vv]isualizad[ao]/)` ausente |
| Fix 6 (Minor) | Desempate `id DESC` nunca exercitado | ✅ Sim | `test_repositorio_elegibilidade.py:668-711` — dois registros com `criado_em` forçado ao **mesmo** valor via `UPDATE`, `esperado = sorted([id_1, id_2], reverse=True)`, e duas chamadas consecutivas asseridas iguais (estabilidade entre carregamentos, que é o texto exato do edge case) |
| Fix 7 (Minor) | `aria-live` sem asserção; cobertura rasa de estados; `design.md` factualmente errado | ✅ Sim, os três | (a) `SuperficieAlertas.test.tsx:180-191` — `expect(regiaoAnuncio).toHaveTextContent('Alerta selecionado. Mostrando detalhe.')`; (b) `test_lista_alertas_segurado_api.py:274-292` cobre `FALHOU_PREPARACAO_IA` (terminal técnico **antes** da simulação), classe de estado que nenhum teste tocava; (c) **`design.md:108` foi de fato corrigido** — hoje lê "não existe nenhum componente de mapa em 2.1 nem em nenhum outro lugar do projeto — a suposição original desta linha estava incorreta", e `design.md:110` registra a generalização da classificação. Verificado lendo o arquivo, não o commit |

---

## Spec-Anchored Acceptance Criteria (re-derivado ponta a ponta)

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| **ALERTAS-01** — lista com evento, severidade, período, localização, origem e estado | Os 6 campos visíveis | `SuperficieAlertas.test.tsx:90-95` — `findByRole('cell',{name:'Chuva intensa'})`, `getByText('72.5 mm — atinge o limiar.')`, `getByText(/2026-09-04T12:00:00 a 2026-09-04T18:00:00/)`, `getByText('9990001')`, `getByText('Observação real (INMET)')`, `getByText('Ativo')` | ✅ PASS |
| **ALERTAS-01** — ativos e anteriores distinguíveis por **rótulo** | `Ativo`/`Anterior`/`Ainda não simulado` | `SuperficieAlertas.test.tsx:113-115` — `findByText('Ativo')`, `getByText('Anterior')`, `getByText('Ainda não simulado')` | ✅ PASS |
| **ALERTAS-01** — distinguíveis por **ícone** | Ícone diferente por classificação | `SuperficieAlertas.test.tsx:119-123` — `expect(new Set([...document.querySelectorAll('[data-icone-nome]')].map(e => e.getAttribute('data-icone-nome'))).size).toBe(3)` | ✅ PASS (M8 morto) |
| **ALERTAS-01** — distinguíveis por **texto** | Texto, não só cor | mesmo `:113-115` (os rótulos são texto real, não `aria-label` sobre cor) | ✅ PASS |
| **ALERTAS-01** — classificação ativo/anterior/ainda-não-simulado (backend) | `ativo` = desfecho de simulação **e** dentro do período; `anterior` = fora; demais estados = `ainda_nao_simulado` | `test_lista_alertas_segurado.py:189` — `assert item.classificacao is ClassificacaoAlerta.ATIVO`; `:203` — `... is ANTERIOR`; `:175` — `... is AINDA_NAO_SIMULADO`; `test_lista_alertas_segurado_api.py:271` e `:292` — `assert resposta.json()["classificacao"] == "ainda_nao_simulado"` (estado em andamento **e** terminal técnico) | ✅ PASS |
| **ALERTAS-01** — contrato HTTP não mistura campos | Cada campo de `RespostaAlerta` carrega o seu próprio valor | `test_lista_alertas_segurado_api.py:193-202` — `assert alerta["origem"]=="real_inmet"`, `alerta["localizacao"]==AREA`, `alerta["fonte_degradada"] is False`, `alerta["periodo_inicio"]==evento.periodo_inicio.isoformat()`, `alerta["periodo_fim"]==evento.periodo_fim.isoformat()`, `alerta["instante_observado"]==evento.instante_observado.isoformat()`, `"62.5" in alerta["severidade"]`, `alerta["impactos_esperados"]==["alagamento"]`; `:223` — `["alerta"]["origem"]=="sintetico"`; `:253` — `item["alerta"]["fonte_degradada"] is True` | ✅ PASS (M5/M5c/M6/M6b/M6c mortos) |
| **ALERTAS-01** — ordenação determinística (Tech Decision + edge case) | `criado_em DESC`, empate por `id DESC`, estável entre carregamentos | `test_repositorio_elegibilidade.py:665` — `assert [r.id for r in resultado]==[id_novo, id_antigo]`; `:710-711` — `assert [r.id for r in resultado_1]==esperado` e `... resultado_2 == esperado` com `criado_em` **idêntico** | ✅ PASS (M10 morto) |
| **ALERTAS-02** — estado vazio com **explicação** | Texto explicativo | `SuperficieAlertas.test.tsx:131` — `findByRole('heading',{name:'Nenhum alerta no momento'})`; `SuperficieAlertas.tsx:341` — parágrafo explicativo | ✅ PASS |
| **ALERTAS-02** — estado vazio com **próxima ação válida** | Uma próxima ação oferecida e funcional | `SuperficieAlertas.tsx:342-344` botão `Atualizar` → `carregarLista()`; `SuperficieAlertas.test.tsx:132-136` — clica no botão e `expect(await screen.findByText('Ativo')).toBeInTheDocument()` (a lista foi reconsultada) | ✅ PASS — qualificado (ver nota abaixo) |
| **ALERTAS-02** — sem exibir dado de outro segurado sintético | Lista vazia mesmo com alerta de outro segurado no banco | `test_lista_alertas_segurado.py:226` — `assert contexto.servico.listar(SEGURADO_ID) == []`; `test_lista_alertas_segurado_api.py:167` — `assert resposta.json() == {"alertas": []}` | ✅ PASS (M3 morto na rodada 1) |
| **ALERTAS-03** — detalhe com origem, período, localização, impactos, recomendações, contexto da apólice e linha do tempo | Os 7 blocos visíveis | `SuperficieAlertas.test.tsx:170-177` — `findByRole('heading',{name:'Chuva intensa'})`, `getByText('Observação real (INMET)')`, `getByText(/2026-09-04T12:00:00 a 2026-09-04T18:00:00/)`, `getByText('9990001')`, `getByText('alagamento')`, `getByText('Evite áreas alagadas.')`, `getByText('Segurado e apólice atendem à regra ativa.')`, `getByText(/coleta_concluida/)` | ✅ PASS |
| **ALERTAS-03** — detalhe (backend) | apólice, justificativa, classificação, evento, linha do tempo | `test_lista_alertas_segurado.py:259-263` — `assert detalhe.apolice_id == APOLICE_ID`, `... justificativa == "Segurado e apólice atendem à regra ativa."`, `... classificacao is ATIVO`, `... evento_tipo is CHUVA_INTENSA`, `len(detalhe.linha_do_tempo) > 0`; `test_lista_alertas_segurado_api.py:189-191`, `:203` | ✅ PASS |
| **ALERTAS-03** — seleção **anunciada** | Anúncio numa região `aria-live` | `SuperficieAlertas.test.tsx:189-190` — `document.querySelector('[aria-live="polite"]')`, `expect(regiaoAnuncio).toHaveTextContent('Alerta selecionado. Mostrando detalhe.')` | ✅ PASS (M12 morto) |
| **ALERTAS-03** — **sem mover o foco inesperadamente** | Foco vai ao título do detalhe; volta ao botão **de origem** | `SuperficieAlertas.test.tsx:227` — `expect(titulo).toHaveFocus()`; `:241-250` — lista de 3 itens, abre o **terceiro**, volta, `expect(document.getElementById('botao-detalhe-item-3')).toHaveFocus()` | ✅ PASS (M7 morto) |
| **ALERTAS-04** — pinos com ícone e legenda; toda seleção também numa lista equivalente | Equivalência mapa↔lista | SPEC_DEVIATION reverificada: **nenhum componente de mapa existe no projeto** (`SuperficieFonteMeteorologica.tsx:135` — "sem depender de um mapa (fora do MVP)"). A tabela acessível é a única representação; a equivalência é satisfeita por construção. Operabilidade por teclado: `SuperficieAlertas.test.tsx:324-328` — `await usuario.tab()`, `expect(getByRole('button',{name:'Ver detalhe'})).toHaveFocus()`, `await usuario.keyboard('{Enter}')`, detalhe abre | ✅ PASS (por construção; agora corretamente documentado em `design.md:108`, `tasks.md:137`, `SuperficieAlertas.tsx:93-95`) |
| **ALERTAS-05** — alerta inexistente/de outro segurado → `Não encontrado`, sem revelar outro registro | `None` no caso de uso; `404` **idêntico** nos dois casos | `test_lista_alertas_segurado.py:232` — `assert ...obter_detalhe(SEGURADO_ID, uuid4()) is None`; `:244` — `... is None` para o de outro segurado; `test_lista_alertas_segurado_api.py:324-327` — `assert resposta_outro.status_code == 404`, `corpo_outro["codigo"] == corpo_inexistente["codigo"] == "alerta_nao_encontrado"`, `corpo_outro["impacto"] == corpo_inexistente["impacto"]`, `corpo_outro["proxima_acao"] == corpo_inexistente["proxima_acao"]`; UI: `SuperficieAlertas.test.tsx:286-289` | ✅ PASS |
| **ALERTAS-05** — com retorno à lista | Botão de volta funcional a partir do `Não encontrado` | `SuperficieAlertas.test.tsx:310-312` — clica em `Voltar à lista`, `expect(await screen.findByRole('button',{name:'Ver detalhe'})).toBeInTheDocument()` | ✅ PASS |
| **ALERTAS-06** — `Ainda não simulado` explícito, sem comunicado nem visualização antecipada | Rótulo explícito; nenhum comunicado | `test_lista_alertas_segurado.py:175`; `test_lista_alertas_segurado_api.py:271`, `:292`; `SuperficieAlertas.test.tsx:260-264` — `findByText(/Ainda não simulado — nenhum comunicado foi produzido/)`, `queryByText(/[Cc]omunicado simulado/)).not.toBeInTheDocument()`, `queryByText(/[Vv]isualizad[ao]/)).not.toBeInTheDocument()` | ✅ PASS (M2/M11 mortos) |

**Status**: ✅ Todas as 18 cláusulas cobertas com `file:line` + expressão de asserção. 0 GAP,
0 spec-precision gap, 1 PASS qualificado (ALERTAS-02, ver nota).

### Nota de qualificação — ALERTAS-02

A cláusula do AC ("estado vazio com explicação **e próxima ação válida**") está satisfeita:
`Atualizar` é uma ação real que reexecuta a consulta, provada por asserção e por mutação.

O que **não** está satisfeito é o bullet de Success Criteria da spec "Estado vazio de alertas
mantém navegação para as demais superfícies" — a superfície não tem nenhuma navegação, nem no
estado vazio nem no estado cheio, porque `SUPERFICIES_POR_PERFIL.segurado` continua sendo
apenas `['visao-geral']` e `SuperficieAlertas` não está montada no shell. Isso é a condição de
superfície órfã já registrada como item (9) do `STATE.md` e comum a todas as histórias
anteriores; **não é regressão desta história** e a alternativa (prometer navegação para uma
superfície que 5.3/5.5 ainda não entregaram) seria pior — seria exatamente o rótulo decorativo
que a rodada 1 pediu para evitar. A escolha do implementador é a honesta disponível hoje.

### Estados cobertos pela classificação

`_ESTADOS_COM_DESFECHO_DE_SIMULACAO = {CONCLUIDA, FALHOU_SIMULACAO}`
(`lista_alertas_segurado.py:38-42`); todo o resto é `ainda_nao_simulado` — generalização mais
ampla que os 4 estados do diagrama do `design.md`, agora **registrada** em `design.md:110`.
Cobertura de teste: `SIMULANDO` (`test_lista_alertas_segurado.py:170`),
`PROCESSANDO_MENSAGENS` (`test_..._api.py:256-271`) e `FALHOU_PREPARACAO_IA`
(`test_..._api.py:274-292`) — em andamento **e** terminal técnico antes da simulação, as duas
classes semânticas distintas. A cobertura não é exaustiva (≥ 9 estados caem no ramo), mas as
duas classes de comportamento estão exercitadas e o mutante que apaga a distinção (M11) morre.

### SPEC_DEVIATIONs verificadas

| Deviation | Local | Veredito |
| --- | --- | --- |
| `listar` devolve `list[ItemAlertaListado]` em vez do `list[AlertaSegurado]` do `design.md:75` | `lista_alertas_segurado.py:9-13` | ✅ **Necessária e correta.** Sem a classificação no retorno, ALERTAS-01 é insatisfazível; o próprio diagrama do Approach (`design.md:25-31`) já descreve a classificação no fluxo — a assinatura é que estava desatualizada |
| Linha semeada com `execucao_id IS NULL` classificada só pelo período | `lista_alertas_segurado.py:15-19` | ✅ **Documentada e coerente com 5.1.** A linha semeada não tem execução alguma, então não representa mal uma execução em andamento. Coberta por `test_lista_alertas_segurado.py:216` e `:277`; mutante M4 morto na rodada 1 |
| Nenhum componente de mapa (ALERTAS-04) | `design.md:108`, `tasks.md:137`, `SuperficieAlertas.tsx:93-95` | ✅ **Honesta e agora consistente nos três artefatos.** A Tech Decision do `design.md` foi corrigida nesta rodada; nenhum artefato alega mais reuso de um componente inexistente |

---

## Discrimination Sensor (rodada 2)

Scratch isolado: `git worktree add /tmp/verify-5-2-round2-scratch HEAD`, removido com
`git worktree remove --force` + `git worktree prune`. Nenhum `git stash` usado.
`git status --porcelain` da árvore real: **vazio antes e vazio depois** (idêntico).
`git worktree list` após a limpeza mostra **apenas** a árvore principal; `/tmp/verify-5-2-round2-scratch`
não existe mais.

### Reconfirmação dos 5 mutantes que sobreviveram na rodada 1

| # | File:line | Description | Rodada 1 | Rodada 2 |
| --- | --- | --- | --- | --- |
| M5 | `adaptadores/http/lista_alertas_segurado.py:164-165` | `periodo_inicio`/`periodo_fim` trocados | ❌ Survived | ✅ **Killed** — `test_..._api.py:197` |
| M6 | `adaptadores/http/lista_alertas_segurado.py:171` | `fonte_degradada=True` fixo | ❌ Survived | ✅ **Killed** — `test_..._api.py:196` |
| M6b | `adaptadores/http/lista_alertas_segurado.py:166` | `localizacao=alerta.severidade` | ❌ Survived | ✅ **Killed** — `test_..._api.py:195` |
| M7 | `SuperficieAlertas.tsx:178` | `getElementById(...)` → `querySelector('[id^="botao-detalhe-"]')` (foca sempre o primeiro) | ❌ Survived | ✅ **Killed** — `SuperficieAlertas.test.tsx:250` |
| M8 | `SuperficieAlertas.tsx:60-76` | os três ícones colapsados num só | ❌ Survived | ✅ **Killed** — `SuperficieAlertas.test.tsx:123` |
| M5+M6+M6b | os três simultâneos, contra a **suíte backend completa** | (1004 testes passavam na rodada 1) | ❌ Survived | ✅ **Killed** — `test_..._api.py:195` |

### Mutações inéditas sobre código que a rodada 1 não estressou

| # | File:line | Description | Killed? |
| --- | --- | --- | --- |
| M5c | `http/lista_alertas_segurado.py:170` | `instante_observado=alerta.periodo_inicio` (o "alias" que a fixture antiga tornava indetectável) | ✅ Killed — `test_..._api.py:199` |
| M6c | `http/lista_alertas_segurado.py:171` | `fonte_degradada=False` fixo (direção oposta a M6) | ✅ Killed — `test_..._api.py:253` |
| M9 | `SuperficieAlertas.tsx:342-344` | Botão `Atualizar` sem `onClick` (rótulo decorativo) | ✅ Killed — `SuperficieAlertas.test.tsx:136` |
| M10 | `repositorio_elegibilidade.py:243` | `ORDER BY e.criado_em DESC, e.id DESC` → `... e.id ASC` | ✅ Killed — `test_repositorio_elegibilidade.py:710` |
| M11 | `aplicacao/lista_alertas_segurado.py:38-40` | `FALHOU_PREPARACAO_IA` acrescentado a `_ESTADOS_COM_DESFECHO_DE_SIMULACAO` (terminal técnico passa a ser `ativo`/`anterior`) | ✅ Killed — `test_..._api.py:292` |
| M12 | `SuperficieAlertas.tsx:142` | `definirAnuncio('Alerta selecionado. Mostrando detalhe.')` → `definirAnuncio('')` | ✅ Killed — `SuperficieAlertas.test.tsx:190` |

**Sensor depth**: expandido / P0-full — 12 injeções de falha de comportamento (piso: 5)
**Result**: **12/12 killed** — ✅ **PASS**

### Observação de robustez da sonda (fora do placar, não bloqueante)

Foi testada uma variante adversarial **M8b**: manter os três `data-icone-nome` distintos mas
renderizar o **mesmo glifo** (`WarningIcon`) nas três classificações. Ela **sobrevive**, porque
a asserção compara marcadores de teste, não o glifo renderizado.

Isso é uma fraqueza da **instrumentação**, não uma falha de comportamento não detectada: M8b
falsifica o próprio marcador da sonda, o que nenhuma regressão plausível faria (um
desenvolvedor que troca o componente de ícone troca também o marcador colado nele, e essa é
exatamente a mutação M8, que morre). Registrada como melhoria opcional — asserir o conteúdo
renderizado do `<svg>` em vez do atributo — e explicitamente **não** contada como mutante
sobrevivente. Vale notar que a abordagem por marcador foi a prescrita pela própria tarefa de
correção da rodada 1.

---

## Code Quality

| Principle | Status |
| --- | --- |
| No features beyond what was asked | ✅ A única adição de produção desta rodada é o botão `Atualizar` (3 linhas) exigido pela cláusula do ALERTAS-02, e os `data-icone-nome` |
| No abstractions for single-use code | ✅ Nenhuma abstração nova |
| No unnecessary "flexibility" added | ✅ |
| Only touched files required for task | ✅ 4 arquivos de código/teste + 3 de spec/design/lessons |
| Didn't "improve" unrelated code | ✅ A mudança de assinatura de `criar_evento` (devolve `EventoMeteorologico` em vez de `UUID`) é **necessária** para a asserção campo a campo e ficou contida no próprio arquivo de teste |
| Matches existing patterns/style | ✅ Roteador, `problem+json`, `Protocol` ports, docstrings em pt-BR |
| Would senior engineer approve? | ✅ Os comentários nos testes explicam **por que** a fixture precisa de valores não colidentes e por que o último item é o selecionado — a intenção discriminante fica preservada contra futuras "simplificações" |
| Tests map to ACs and are non-shallow | ✅ Spot-check em ALERTAS-01: 6 campos + 3 rótulos + 3 ícones + 10 campos do contrato HTTP + ordenação com empate |
| Spec-anchored outcome check | ✅ 18/18 cláusulas asseridas contra o valor definido pela spec |
| Per-layer Coverage Expectation | ✅ Domínio 1:1 com os ACs; rotas cobrem feliz + vazio + 404 (duas origens) + 422 + `ainda_nao_simulado` (2 classes de estado) + contrato campo a campo |
| Every test maps to a spec requirement | ✅ Os 4 testes backend e 2 frontend novos desta rodada rastreiam a um AC ou a um edge case listado |
| Documented guidelines followed | ✅ `AGENTS.md`, `README.md`, Test Coverage Matrix de `tasks.md:20-26` |

**Nota de escopo (pré-existente, não regressão)**: `SuperficieAlertas` não está ligada a
`App.tsx` nem a `PerfilContexto.tsx`; a superfície é inalcançável no shell. Item (9) do
`STATE.md`, padrão de todas as histórias anteriores.

---

## Edge Cases

- [x] **Alerta anterior simulado com sucesso mas comunicado não visualizado (4.3)** — coberto:
  `SuperficieAlertas.test.tsx:193-217` exibe o marco `simulacao_concluida` e assere que a
  interface **não** afirma "visualizado". Asserção parcialmente negativa (prova que "simulado"
  não é apresentado como "visualizado"), que é exatamente o que o edge case pede.
- [x] **Dois alertas com o mesmo período → ordenação determinística** — coberto:
  `test_repositorio_elegibilidade.py:668-711` com `criado_em` idêntico, asserindo `id DESC`
  exato e estabilidade entre duas chamadas. M10 morto.
- [x] **Alerta deixa de existir entre a listagem e a abertura do detalhe** — mesmo caminho do
  `404`: `test_lista_alertas_segurado_api.py:295-302` e `test_lista_alertas_segurado.py:232`;
  UI em `SuperficieAlertas.test.tsx:269-290`.

---

## Gate Check (Build, ambos os stacks)

- **Gate command (backend)**: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright`
- **Result**: **1008 passed**, 0 failed, 0 skipped (107 s); ruff `All checks passed!`;
  pyright `0 errors, 0 warnings, 0 informations` — **exit 0**
- **Gate command (frontend)**: `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`
- **Result**: **354 passed** (35 arquivos), 0 failed, 0 skipped; lint exit 0 (8 warnings
  pré-existentes em `SuperficieEventoDecisao`, `SuperficieGeracaoMensagens`,
  `SuperficieFonteMeteorologica`, `SuperficiePreparacaoIA`, `SuperficieRevisaoLote` — **nenhum**
  em `SuperficieAlertas`); build `✓ built in 239ms` — **exit 0**
- **Test count antes da história**: 982 backend + 339 frontend
- **Test count após a rodada 1**: 1004 backend + 352 frontend
- **Test count após a rodada 2**: 1008 backend + 354 frontend
- **Delta da história**: +26 backend, +15 frontend
- **Delta desta rodada**: +4 backend (`sintetico`, `fonte_degradada=True`, `FALHOU_PREPARACAO_IA`,
  desempate por `id`), +2 frontend (`aria-live`, `simulado ≠ visualizado`)
- **Integridade**: nenhum teste removido. Duas asserções foram **substituídas por versões mais
  fortes**, não enfraquecidas: `expect(await findByText('Ativo'))` → `await findByText('Ativo')`
  (o `await` já é a asserção; a linha seguinte cobre o mesmo) e a restauração de foco por role
  → por `id` específico. Verificado no diff.
- **Skipped tests**: nenhum
- **Failures**: nenhuma

---

## Fix Plans

Nenhuma correção bloqueante. Uma sugestão opcional, não bloqueante, registrada acima:

### Sugestão (Cosmético, opcional): sonda de ícone independente do marcador

- **Root cause**: `SuperficieAlertas.test.tsx:119-123` compara `data-icone-nome`, que é
  instrumentação de teste, não o glifo. A variante M8b (mesmo glifo, marcadores distintos)
  sobrevive.
- **Sugestão**: asserir que o `innerHTML` dos três `<svg>` difere entre si, ou usar a
  `<title>`/`aria-label` do próprio ícone.
- **Priority**: Cosmetic — nenhuma regressão plausível escapa da sonda atual.

---

## Requirement Traceability Update

| Requirement | Status rodada 1 | Status rodada 2 |
| --- | --- | --- |
| ALERTAS-01 | ❌ Needs Fix (ícone sem asserção) | ✅ **Verified** |
| ALERTAS-02 | ❌ Needs Fix ("próxima ação válida" ausente) | ✅ **Verified** (qualificado: o AC está cumprido pelo botão `Atualizar` funcional; o bullet de Success Criteria "mantém navegação para as demais superfícies" continua não satisfeito pela condição pré-existente de superfície órfã, item 9 do `STATE.md`) |
| ALERTAS-03 | ✅ Verified (parcial — foco não discriminado) | ✅ **Verified** (integral: foco discriminado com lista de 3 itens; anúncio `aria-live` asserido) |
| ALERTAS-04 | ✅ Verified (por construção) | ✅ **Verified** (por construção; SPEC_DEVIATION agora consistente em `design.md`, `tasks.md` e no código) |
| ALERTAS-05 | ✅ Verified | ✅ **Verified** |
| ALERTAS-06 | ✅ Verified | ✅ **Verified** |

---

## Summary

**Overall**: ✅ **Ready**

**Spec-anchored check**: 18/18 cláusulas com evidência `file:line`; 0 GAP, 0 spec-precision
gap, 1 PASS qualificado (ALERTAS-02, qualificação de escopo pré-existente, não de implementação)
**Sensor**: 12/12 mutações de comportamento mortas (5 delas eram sobreviventes da rodada 1);
1 observação de robustez de sonda registrada fora do placar
**Gate**: 1008 backend + 354 frontend passed, 0 failed, 0 skipped; ruff/pyright/lint/build exit 0

**What works**: as três fronteiras que a rodada 1 apontou como cegas agora discriminam de fato.
O contrato HTTP é asserido campo a campo contra valores deliberadamente não colidentes — a
fixture foi reprojetada para que `periodo_inicio`, `periodo_fim` e `instante_observado` sejam
três instantes distintos, que é a condição sem a qual qualquer asserção de troca seria vazia.
A restauração de foco é provada num cenário de 3 itens abrindo o **último**. O estado vazio
oferece uma ação executável de verdade, não um rótulo. O desempate de ordenação por `id` é
exercitado com `criado_em` idêntico e estabilidade entre chamadas. A classificação cobre as
duas classes semânticas de "ainda não simulado" (em andamento e terminal técnico). E as três
correções documentais (`design.md:108` sobre o mapa inexistente, `design.md:110` sobre a
generalização dos estados, `tasks.md:137`) foram verificadas lendo os arquivos, não os commits.

**Issues found**: nenhuma bloqueante. Uma sugestão cosmética (sonda de ícone) e uma nota de
escopo pré-existente (superfície órfã, item 9 do `STATE.md`) — nenhuma das duas é regressão
desta história.

**Next steps**: história pronta. Atualizar o Requirement Traceability da `spec.md` para
`Verified` nos seis ALERTAS-NN (com a qualificação de ALERTAS-02 preservada literalmente) e
fechar a 5.2 no `STATE.md`. A condição de superfície órfã permanece como dívida conhecida da
história de integração de UI, não desta.
