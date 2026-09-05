# História 5.2: Consultar alertas ativos e anteriores — Validation

**Date**: 2026-09-05
**Spec**: `.specs/features/5-2-consultar-alertas-ativos-e-anteriores/spec.md`
**Diff range**: `8e11b9e..HEAD` (`19b29ce`, `dec4419`, `e25ddbf`, `b2138c8`)
**Verifier**: independent sub-agent (author ≠ verifier), read-only over the real tree

**Verdict**: ❌ **FAIL** — 5 of 9 injected faults survived. Gates are green and the ACs are
broadly implemented, but the assertions that would detect a regression in the HTTP field
mapping, the focus restoration and the icon distinction do not exist.

---

## Task Completion

| Task | Status | Notes |
| --- | --- | --- |
| T1 `listar_todas_por_segurado` | ✅ Done | `19b29ce`; ordena `criado_em DESC, id DESC` |
| T2 `ServicoListaAlertasSegurado` | ✅ Done | `dec4419`; 2 SPEC_DEVIATIONs marcadas no módulo |
| T3 Endpoints HTTP | ⚠️ Partial | `e25ddbf`; rotas corretas, mas o mapeamento de campos de `_resposta_alerta` não tem nenhuma asserção discriminante (3 mutantes sobreviventes) |
| T4 Superfície de Alertas | ⚠️ Partial | `b2138c8`; 2 mutantes sobreviventes (foco e ícone); cláusula "próxima ação válida" do ALERTAS-02 não implementada |

---

## Spec-Anchored Acceptance Criteria

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| ALERTAS-01 — lista com evento, severidade, período, localização, origem e estado | Os 6 campos visíveis na lista | `src/frontend/src/funcionalidades/segurado/SuperficieAlertas.test.tsx:90-95` — `findByRole('cell',{name:'Chuva intensa'})`, `getByText('72.5 mm — atinge o limiar.')`, `getByText(/2026-09-04T12:00:00 a 2026-09-04T18:00:00/)`, `getByText('9990001')`, `getByText('Observação real (INMET)')`, `getByText('Ativo')` | ✅ PASS |
| ALERTAS-01 — ativos e anteriores distinguíveis por **rótulo** e **texto** | Rótulos `Ativo`/`Anterior`/`Ainda não simulado` | `SuperficieAlertas.test.tsx:113-115` — `findByText('Ativo')`, `getByText('Anterior')`, `getByText('Ainda não simulado')` | ✅ PASS |
| ALERTAS-01 — distinguíveis por **ícone** | Ícone diferente por classificação | nenhuma asserção de ícone em todo o arquivo de teste | ❌ GAP (mutante M8 sobreviveu) |
| ALERTAS-01 — classificação ativo/anterior/ainda-não-simulado (backend) | `ativo` = desfecho de simulação + dentro do período; `anterior` = fora; demais estados = `ainda_nao_simulado` | `src/backend/testes/test_lista_alertas_segurado.py:189` — `assert item.classificacao is ClassificacaoAlerta.ATIVO`; `:203` — `... is ClassificacaoAlerta.ANTERIOR`; `:175` — `... is ClassificacaoAlerta.AINDA_NAO_SIMULADO` | ✅ PASS |
| ALERTAS-01 — ordenação determinística (Tech Decision) | `criado_em DESC`, empate por `id DESC` | `src/backend/testes/test_repositorio_elegibilidade.py:665` — `assert [registro.id for registro in resultado] == [id_novo, id_antigo]` | ⚠️ Parcial — só a ordem por `criado_em`; o desempate por `id` nunca é exercitado |
| ALERTAS-02 — estado vazio com **explicação** | Texto explicativo, sem dado de outro segurado | `SuperficieAlertas.test.tsx:123` — `findByRole('heading',{name:'Nenhum alerta no momento'})` | ✅ PASS |
| ALERTAS-02 — estado vazio com **próxima ação válida** | Uma próxima ação oferecida ao usuário | `SuperficieAlertas.tsx:329-336` renderiza apenas `<h1>` + `<p>`; nenhum link, botão ou ação. Nenhuma asserção | ❌ GAP |
| ALERTAS-02 — sem exibir dado de outro segurado sintético | Lista vazia mesmo com alerta de outro segurado no banco | `test_lista_alertas_segurado.py:226` — `assert contexto.servico.listar(SEGURADO_ID) == []`; `src/backend/testes/test_lista_alertas_segurado_api.py:152` — `assert resposta.json() == {"alertas": []}` | ✅ PASS |
| ALERTAS-03 — detalhe com origem, período, localização, impactos, recomendações, contexto da apólice e linha do tempo | Os 7 blocos visíveis | `SuperficieAlertas.test.tsx:157-164` — `findByRole('heading',{name:'Chuva intensa'})`, `getByText('Observação real (INMET)')`, `getByText(/2026-09-04T12:00:00 a 2026-09-04T18:00:00/)`, `getByText('9990001')`, `getByText('alagamento')`, `getByText('Evite áreas alagadas.')`, `getByText('Segurado e apólice atendem à regra ativa.')`, `getByText(/coleta_concluida/)` | ✅ PASS |
| ALERTAS-03 — detalhe (backend) | apólice, justificativa, classificação, evento e linha do tempo | `test_lista_alertas_segurado.py:259-263` — `assert detalhe.apolice_id == APOLICE_ID`, `assert detalhe.justificativa == "Segurado e apólice atendem à regra ativa."`, `assert detalhe.classificacao is ClassificacaoAlerta.ATIVO`, `assert len(detalhe.linha_do_tempo) > 0` | ✅ PASS |
| ALERTAS-03 — sem mover o foco inesperadamente | Foco vai ao título do detalhe; volta ao botão de origem | `SuperficieAlertas.test.tsx:175` — `expect(titulo).toHaveFocus()`; `:189` — `expect(await screen.findByRole('button',{name:'Ver detalhe'})).toHaveFocus()` | ⚠️ Parcial — a restauração é testada com lista de **1 item**; não discrimina "o botão de origem" de "o primeiro botão" (mutante M7 sobreviveu) |
| ALERTAS-03 — seleção **anunciada** | Anúncio em região `aria-live` | `SuperficieAlertas.tsx:103,134,213-215` implementa `anuncio`; nenhuma asserção sobre o texto anunciado | ⚠️ Spec-precision gap — a spec não define o texto; nenhum teste cobre a região |
| ALERTAS-04 — pinos com ícone e legenda; toda seleção também numa lista equivalente | Equivalência mapa↔lista | SPEC_DEVIATION verificada: não existe nenhum componente de mapa no projeto (confirmado em `src/frontend/src/funcionalidades/fonte-meteorologica/SuperficieFonteMeteorologica.tsx:135` — "sem depender de um mapa (fora do MVP)"). A única representação é a tabela acessível; equivalência satisfeita por construção. Operabilidade por teclado: `SuperficieAlertas.test.tsx:263-267` — `await usuario.tab(); expect(getByRole('button',{name:'Ver detalhe'})).toHaveFocus(); await usuario.keyboard('{Enter}')` | ✅ PASS (por construção, deviation documentada em `tasks.md:137` e `SuperficieAlertas.tsx:85-87`) |
| ALERTAS-05 — alerta inexistente/de outro segurado → `Não encontrado`, sem revelar outro registro | `None` no caso de uso; `404` idêntico nos dois casos | `test_lista_alertas_segurado.py:232` — `assert ...obter_detalhe(SEGURADO_ID, uuid4()) is None`; `:244` — `assert ...obter_detalhe(SEGURADO_ID, id_registro) is None`; `test_lista_alertas_segurado_api.py:223-226` — `assert resposta_outro.status_code == 404`, `assert corpo_outro["codigo"] == corpo_inexistente["codigo"] == "alerta_nao_encontrado"`, `assert corpo_outro["impacto"] == corpo_inexistente["impacto"]`, `assert corpo_outro["proxima_acao"] == corpo_inexistente["proxima_acao"]` | ✅ PASS |
| ALERTAS-05 — com retorno à lista | Botão de volta funcional a partir do `Não encontrado` | `SuperficieAlertas.test.tsx:225-228` — `findByRole('heading',{name:'Não encontrado'})`, `getByText('Este alerta não existe ou não pertence a você.')`; `:251` — `expect(await screen.findByRole('button',{name:'Ver detalhe'})).toBeInTheDocument()` após "Voltar à lista" | ✅ PASS |
| ALERTAS-06 — `Ainda não simulado` explícito, sem comunicado nem visualização antecipada | Rótulo explícito; nenhum comunicado | `test_lista_alertas_segurado.py:175` — `assert item.classificacao is ClassificacaoAlerta.AINDA_NAO_SIMULADO`; `test_lista_alertas_segurado_api.py:193` — `assert resposta.json()["classificacao"] == "ainda_nao_simulado"`; `SuperficieAlertas.test.tsx:200-203` — `findByText(/Ainda não simulado — nenhum comunicado foi produzido/)`, `queryByText(/[Cc]omunicado simulado/)).not.toBeInTheDocument()`, `queryByText(/[Vv]isualizad[ao]/)).not.toBeInTheDocument()` | ✅ PASS |

**Status**: ❌ Gaps present — 11 cláusulas ✅ PASS, 2 ❌ GAP, 3 ⚠️ parciais/spec-precision.

### Estados cobertos pela classificação (verificação do item 1 do briefing)

O código classifica como `ainda_nao_simulado` **qualquer** estado fora de
`{CONCLUIDA, FALHOU_SIMULACAO}` — mais amplo que os quatro estados que o diagrama do
`design.md` enumera. A generalização está documentada em
`src/backend/central_preventiva/aplicacao/lista_alertas_segurado.py:41-42` e é defensável
(nenhum outro estado tem desfecho de simulação). **Mas a cobertura é rasa**: só
`SIMULANDO` (`test_lista_alertas_segurado.py:170`) e `PROCESSANDO_MENSAGENS`
(`test_lista_alertas_segurado_api.py:185`) são exercitados. `AGUARDANDO_REVISAO`,
`AGUARDANDO_CONFIRMACAO` e todos os estados terminais-antes-da-simulação
(`SEM_RISCO`, `SEM_ELEGIVEIS`, `FALHOU_COLETA`, `FALHOU_PREPARACAO_IA`, …) não têm nenhum
teste. Para esses últimos a cópia da interface ("Ainda não simulado — nenhum comunicado foi
produzido") é literalmente verdadeira mas semanticamente enganosa: "ainda" sugere pendência
onde a execução já terminou e nunca simulará.

### SPEC_DEVIATIONs verificadas

| Deviation | Local | Veredito |
| --- | --- | --- |
| `listar` devolve `list[ItemAlertaListado]` em vez do `list[AlertaSegurado]` declarado no `design.md:75` | `lista_alertas_segurado.py:9-13` | ✅ **Necessária e correta.** Sem a classificação no retorno, ALERTAS-01 ("ativos e anteriores distinguíveis") é insatisfazível. O próprio diagrama do Approach (`design.md:25-31`) já descreve a classificação como parte do fluxo — a assinatura é que estava desatualizada. Repete a lição confirmada L-033. |
| Linha semeada com `execucao_id IS NULL` classificada só pelo período | `lista_alertas_segurado.py:15-19`, `:166` | ✅ **Documentada e coerente com 5.1.** Não representa mal uma execução em andamento: a linha semeada não tem execução alguma. Coberta por `test_lista_alertas_segurado.py:216` (`assert item.classificacao is ClassificacaoAlerta.ATIVO`) e `:277` (`assert detalhe.linha_do_tempo == ()`); mutante M4 morto. Atende à lição L-057. |
| Nenhum componente de mapa (ALERTAS-04) | `tasks.md:137`, `SuperficieAlertas.tsx:85-87` | ✅ **Descrição honesta.** O comentário afirma corretamente que nenhum componente de mapa existe no projeto e **não** alega ter construído ou reusado um. Confirmado independentemente: 2.1 tem apenas tabela acessível. A Tech Decision do `design.md:108` ("reusa o componente já existente da superfície de Fonte meteorológica") está factualmente errada e não foi corrigida no `design.md`. |

### Refatoração `montar_para_registro` (item 6 do briefing)

✅ **Preservadora de comportamento.** O diff (`git diff 8e11b9e..HEAD -- .../alerta_segurado.py`)
adiciona 6 linhas e não remove nenhuma: `obter_mais_relevante` passa a delegar a
`montar_para_registro`, cujo corpo é exatamente o bloco que já existia após o `return None`.
Toda a lógica de evento/regra/risco/fonte-degradada ficou intacta. Os testes de 5.1
(`test_alerta_segurado.py`, `test_alerta_segurado_api.py`) seguem verdes na suíte completa
de 1004 testes, sem nenhuma alteração.

---

## Discrimination Sensor

Scratch isolado: `git worktree add /tmp/verify-5-2-scratch HEAD`, removido com
`--force` + `git worktree prune`. `git status --porcelain` da árvore real: vazio antes e
vazio depois (idêntico). Nenhum `git stash` usado.

| # | File:line | Description | Killed? |
| --- | --- | --- | --- |
| M1 | `aplicacao/lista_alertas_segurado.py:172` | `if alerta.periodo_fim >= agora` → `<` (troca ativo↔anterior) | ✅ Killed (4 testes) |
| M2 | `aplicacao/lista_alertas_segurado.py:168` | Removida a checagem `snapshot.estado not in _ESTADOS_COM_DESFECHO_DE_SIMULACAO` (ignora o estado da execução) | ✅ Killed (3 testes) |
| M3 | `aplicacao/lista_alertas_segurado.py:134` | Removido `or registro.segurado_id != segurado_id` (fim da não-enumeração) | ✅ Killed (2 testes) |
| M4 | `aplicacao/lista_alertas_segurado.py:166` | Linha semeada sem execução → sempre `AINDA_NAO_SIMULADO` | ✅ Killed (1 teste) |
| M5 | `adaptadores/http/lista_alertas_segurado.py:163-164` | `_resposta_alerta`: `periodo_inicio`/`periodo_fim` trocados | ❌ **Survived** |
| M6 | `adaptadores/http/lista_alertas_segurado.py:171` | `_resposta_alerta`: `fonte_degradada` fixado em `True` | ❌ **Survived** |
| M6b | `adaptadores/http/lista_alertas_segurado.py:165` | `_resposta_alerta`: `localizacao=alerta.severidade` (campo trocado) | ❌ **Survived** |
| M7 | `funcionalidades/segurado/SuperficieAlertas.tsx:170` | `getElementById('botao-detalhe-'+id)` → `querySelector('[id^="botao-detalhe-"]')` (foca sempre o **primeiro** botão) | ❌ **Survived** |
| M8 | `funcionalidades/segurado/SuperficieAlertas.tsx:60-68` | `IconeClassificacao` devolve o **mesmo** ícone para as três classificações | ❌ **Survived** |

M5+M6+M6b foram reconfirmados juntos contra a **suíte backend completa**: 1004 testes
passaram com os três defeitos injetados simultaneamente.

**Sensor depth**: expandido (9 mutações, > o piso de 5 para caminho crítico)
**Result**: 4/9 killed — ❌ **FAIL**

---

## Code Quality

| Principle | Status |
| --- | --- |
| Minimum code | ✅ Extensão direta de 5.1, sem camada nova |
| Surgical changes | ✅ `alerta_segurado.py` ganhou 6 linhas, nada removido |
| No scope creep | ✅ Nenhuma funcionalidade além dos ACs |
| Matches patterns | ✅ Roteador, `problem+json`, Protocol ports e docstrings em pt-BR seguem o padrão do repositório |
| Spec-anchored outcome check (asserted values match spec) | ⚠️ 2 GAPs + 3 parciais (tabela acima) |
| Per-layer Coverage Expectation met (domain 1:1 ACs; routes happy+edge+error) | ⚠️ Rotas cobrem happy/vazio/404/422, mas o **contrato de resposta** não é asserido campo a campo (L-059/L-061 reincidentes) |
| Every test maps to a spec requirement — no unclaimed tests | ✅ Todos os 22 testes backend novos e os 13 frontend mapeiam a um AC ou Done-when |
| Documented guidelines followed | ✅ `AGENTS.md`, `README.md`, Test Coverage Matrix de `tasks.md` |

**Nota de escopo (pré-existente, não regressão desta história)**: `SuperficieAlertas` não
está ligada a `App.tsx` nem a `PerfilContexto.tsx` — `SUPERFICIES_POR_PERFIL.segurado`
continua sendo apenas `['visao-geral']`. A superfície é inalcançável no shell. Isso é o
item (9) já registrado no `STATE.md` (agora 14 superfícies órfãs) e segue o padrão das
histórias anteriores; não é uma falha introduzida aqui, mas significa que "abrir Alertas"
(ALERTAS-01) não é executável pelo usuário até a história de integração de UI.

---

## Edge Cases

- [ ] **Alerta anterior simulado com sucesso mas comunicado não visualizado (4.3)** — o
  `DetalheAlertaSegurado` não carrega nenhum conceito de "visualizado"; a única asserção
  que menciona visualização (`SuperficieAlertas.test.tsx:203`) é a **ausência** dela no
  caso `ainda_nao_simulado`. Nenhum teste prova que um alerta anterior simulado-e-não-visto
  é exibido sem confundir "simulado" com "visualizado". **NÃO coberto.**
- [x] **Dois alertas com o mesmo período → ordenação determinística** — implementado em
  `repositorio_elegibilidade.py` (`ORDER BY e.criado_em DESC, e.id DESC`). Coberto apenas
  parcialmente: `test_repositorio_elegibilidade.py:665` fixa `criado_em` distintos, então o
  desempate por `id` (o caso exato do edge case) nunca é exercitado.
- [x] **Alerta deixa de existir entre a listagem e a abertura do detalhe** — mesmo caminho
  do `404`: `test_lista_alertas_segurado_api.py:201-203`, `test_lista_alertas_segurado.py:232`.

---

## Gate Check

- **Gate command (backend)**: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright`
- **Result**: 1004 passed, 0 failed, 0 skipped; ruff "All checks passed!"; pyright "0 errors, 0 warnings, 0 informations" — exit 0
- **Gate command (frontend)**: `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`
- **Result**: 352 passed (35 arquivos), 0 failed, 0 skipped; lint exit 0 (4 warnings pré-existentes em `SuperficiePreparacaoIA`, `SuperficieFonteMeteorologica`, `SuperficieRevisaoLote` — nenhum no código novo); build "✓ built in 238ms" — exit 0
- **Test count before feature**: 982 backend + 339 frontend
- **Test count after feature**: 1004 backend + 352 frontend
- **Delta**: +22 backend, +13 frontend — nenhum teste removido, nenhuma asserção enfraquecida
- **Skipped tests**: nenhum
- **Failures**: nenhuma

---

## Fix Plans

### Fix 1 (Blocker): asserir o contrato de resposta das rotas campo a campo

- **Root cause**: `test_lista_alertas_segurado_api.py` só assere `alerta.evento_tipo`
  (`:174`) do objeto `RespostaAlerta`. `severidade`, `periodo_inicio`, `periodo_fim`,
  `localizacao`, `impactos_esperados`, `recomendacoes`, `origem`, `instante_observado` e
  `fonte_degradada` não têm nenhuma asserção — três defeitos distintos em `_resposta_alerta`
  passam despercebidos pela suíte inteira. É reincidência das lições confirmadas **L-059** e
  **L-061**, ambas registradas na história 5.1 pelo mesmo motivo.
- **Fix task**: no teste de caminho feliz da **lista** e no do **detalhe**, asserir cada
  campo de `RespostaAlerta` contra o valor esperado (períodos distintos entre si, para que
  uma troca seja detectável) e adicionar um caso com valores não-padrão
  (`proveniencia=sintetico` e fonte degradada) que discrimine `origem` e `fonte_degradada`.
- **Verify**: reaplicar M5, M6 e M6b em worktree descartável e confirmar que agora falham.
- **Priority**: Blocker

### Fix 2 (Major): testar a restauração de foco com lista de mais de um item

- **Root cause**: `SuperficieAlertas.test.tsx:178-190` usa `[item()]` — uma lista de um
  único elemento. "Focar o botão de origem" e "focar o primeiro botão" são indistinguíveis
  nessa fixture (mutante M7). É a mesma família de L-054..L-062 (fixtura que não discrimina).
- **Fix task**: montar a lista com ≥ 3 itens de `elegibilidadeId` distintos, abrir o detalhe
  do **último**, voltar, e asserir que o foco está no botão daquele item específico
  (`document.getElementById('botao-detalhe-<id-do-ultimo>')`), não em qualquer botão.
- **Verify**: M7 passa a morrer.
- **Priority**: Major

### Fix 3 (Major): asserir a distinção por ícone (ALERTAS-01)

- **Root cause**: o AC exige distinção por "rótulo, ícone e texto"; só rótulo/texto são
  asseridos. Substituir os três ícones por um único não quebra nenhum teste (mutante M8).
  Reincidência da lição confirmada **L-024**.
- **Fix task**: dar a cada ícone um marcador estável (ex.: `data-testid` ou `data-icone`) e
  asserir que as três classificações renderizam marcadores diferentes entre si.
- **Verify**: M8 passa a morrer.
- **Priority**: Major

### Fix 4 (Major): estado vazio precisa de "próxima ação válida" (ALERTAS-02)

- **Root cause**: `SuperficieAlertas.tsx:329-336` renderiza só título + explicação. A
  cláusula "e próxima ação válida" do AC não está implementada nem asserida. Atenção à
  lição **L-056**: a próxima ação oferecida precisa ser uma superfície que realmente exista
  na navegação do perfil Segurado hoje (`visao-geral`), não uma prometida por 5.3/5.5.
- **Fix task**: adicionar uma próxima ação real e verdadeira ao estado vazio e asseri-la.
- **Priority**: Major

### Fix 5 (Minor): cobrir o edge case "simulado ≠ visualizado"

- **Root cause**: nenhum teste prova que o detalhe de um alerta anterior simulado com
  sucesso e ainda não visualizado é exibido corretamente.
- **Fix task**: teste de detalhe com classificação `anterior` cuja linha do tempo contenha o
  marco de simulação sem o de visualização, asserindo que a interface não afirma
  "visualizado".
- **Priority**: Minor

### Fix 6 (Minor): exercitar o desempate de ordenação por `id`

- **Root cause**: `ORDER BY e.criado_em DESC, e.id DESC` — o segundo critério, que é
  exatamente o edge case da spec, nunca é exercitado.
- **Fix task**: teste de repositório com dois registros de `criado_em` **idêntico**,
  asserindo a ordem exata por `id DESC` e sua estabilidade entre chamadas.
- **Priority**: Minor

### Fix 7 (Minor): asserir o anúncio de seleção e ampliar a cobertura de estados

- **Root cause**: (a) a região `aria-live` (`SuperficieAlertas.tsx:213-215`) e o texto
  "Alerta selecionado. Mostrando detalhe." não têm nenhuma asserção, embora ALERTAS-03 exija
  "seleção anunciada"; (b) só 2 dos ≥ 9 estados que caem em `ainda_nao_simulado` são
  testados, e nenhum estado terminal-antes-da-simulação (`SEM_RISCO`, `FALHOU_COLETA`).
- **Fix task**: asserir o conteúdo da região `aria-live` após a seleção; acrescentar um caso
  de classificação para `AGUARDANDO_CONFIRMACAO` e um para um estado terminal-sem-simulação,
  e registrar no `design.md` a generalização do conjunto (o diagrama lista só 4 estados).
- **Priority**: Minor

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
| --- | --- | --- |
| ALERTAS-01 | Implementing | ❌ Needs Fix (distinção por ícone sem asserção — M8) |
| ALERTAS-02 | Implementing | ❌ Needs Fix ("próxima ação válida" ausente) |
| ALERTAS-03 | Implementing | ✅ Verified (parcial — restauração de foco não discriminada, M7) |
| ALERTAS-04 | Implementing | ✅ Verified (por construção; SPEC_DEVIATION documentada) |
| ALERTAS-05 | Implementing | ✅ Verified |
| ALERTAS-06 | Implementing | ✅ Verified |

---

## Summary

**Overall**: ❌ Not Ready

**Spec-anchored check**: 11/16 cláusulas ✅ PASS, 2 ❌ GAP, 3 ⚠️ parciais/spec-precision
**Sensor**: 4/9 mutantes mortos (5 sobreviveram)
**Gate**: 1004 backend + 352 frontend passed, 0 failed, lint/tipos/build verdes

**What works**: a classificação `ativo`/`anterior`/`ainda_nao_simulado` no caso de uso é
sólida e discriminante (M1, M2, M4 mortos); a não-enumeração de 4.2/4.3 está corretamente
reusada e comprovada idêntica entre "inexistente" e "de outro segurado" (M3 morto, mais
asserção campo a campo do corpo do `404`); as duas SPEC_DEVIATIONs são necessárias,
documentadas e honestas; a ausência de mapa é descrita com precisão, sem alegar reuso de um
componente inexistente; a extração de `montar_para_registro` é preservadora de comportamento.

**Issues found**: os cinco mutantes sobreviventes estão concentrados nas duas fronteiras que
5.1 já havia sinalizado — o mapeamento de campos da resposta HTTP (M5/M6/M6b, reincidência
de L-059 e L-061) e as fixtures de interface de item único que não distinguem "o item
correto" de "o primeiro item" (M7, M8, reincidência de L-024). Some-se a cláusula
"próxima ação válida" do ALERTAS-02, não implementada.

**Next steps**: executar Fix 1–4 (Blocker/Major) e, se houver folga, Fix 5–7 (Minor);
re-despachar o Verifier. Esta é a **iteração 1 de no máximo 3** rodadas fix→re-verify antes
de escalar ao usuário.
