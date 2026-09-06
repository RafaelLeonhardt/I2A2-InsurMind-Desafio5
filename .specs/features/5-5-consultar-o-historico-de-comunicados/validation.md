# História 5.5: Consultar o histórico de comunicados — Validation

**Date**: 2026-09-06
**Spec**: `.specs/features/5-5-consultar-o-historico-de-comunicados/spec.md`
**Diff range**: `e462393..b8d53ce` (8ed4ae1 T1, babb33c T2, 97ef431 T3, b8d53ce T4)
**Verifier**: independent sub-agent (author ≠ verifier) — every citation below was re-derived from the diff and the test files, with no reliance on the implementer's claims.

---

## Task Completion

| Task | Status  | Notes |
| ---- | ------- | ----- |
| T1   | ✅ Done | `RepositorioEntregasSimuladas.listar_por_segurado` + `EntregaDoSegurado` (`adaptadores/persistencia/repositorio_entregas_simuladas.py:185-201`, `:105-113`); commit `8ed4ae1` matches the task's Where/What exactly |
| T2   | ✅ Done | `ServicoListaComunicados` (`aplicacao/lista_comunicados.py`); commit `babb33c` |
| T3   | ✅ Done | `GET /api/v1/segurados/{segurado_id}/comunicados` (`adaptadores/http/lista_comunicados.py`), router wired in `composicao/api.py:226-229`, `openapi.json` regenerated, route-allowlist guard `testes/test_saude.py:72` updated in the same commit `97ef431` (the 5.4 miss did not recur) |
| T4   | ✅ Done | `SuperficieComunicados.tsx` + `api/listaComunicados.ts`, `tipos-gerados.ts` regenerated; commit `b8d53ce` |

All four tasks are marked `[x]` in `tasks.md` and every `[x]` is backed by code actually present in the diff. No blocked or partial task.

**Reuse claim verified**: `git diff --name-only e462393..HEAD` contains **no** 4.3 file — `aplicacao/visualizacao_comunicado.py`, `adaptadores/http/visualizacao_comunicado.py` and `SuperficieComunicado.tsx` are untouched. `design.md`'s "zero duplication/alteração" requirement holds: `SuperficieComunicados.tsx:149` renders `<SuperficieComunicado …/>` and the HTTP layer only imports 4.3's `RespostaVisualizacaoComunicado` (`adaptadores/http/lista_comunicados.py:17-19`) rather than redeclaring it.

---

## Spec-Anchored Acceptance Criteria

### P1: Lista de comunicados isolada por segurado ⭐ MVP

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| AC1 — WHEN existirem comunicados THEN exibir canal, assunto ou resumo, data e estado de cada registro | Os quatro campos visíveis por linha; e-mail usa `assunto` real, WhatsApp/SMS resumo truncado do corpo | `SuperficieComunicados.test.tsx:83-86` — `findByRole('cell', {name:'E-mail'})`, `getByText('Aviso preventivo')`, `getByText('2026-09-05T12:00:00Z')`, `getByText('Enviada — simulação')`; derivação assunto/resumo: `testes/test_repositorio_entregas_simuladas.py:321-322` — `entregas[0].assunto_ou_resumo == ASSUNTO_EMAIL` e `entregas[1].assunto_ou_resumo == CORPO_LONGO_WHATSAPP[:60].rstrip() + "…"`; sem truncar corpo curto: `:335` — `entrega.assunto_ou_resumo == corpo_curto`; contrato HTTP: `testes/test_lista_comunicados_api.py:137-139` — `item["canal"] == "email"`, `item["assunto_ou_resumo"] == "Aviso preventivo"`, `item["visualizacao"] is None` | ✅ PASS |
| AC1 (cont.) — "retornando somente comunicados do segurado sintético ativo" | Comunicado de outro segurado nunca aparece: lista do segurado A é vazia quando só B tem entregas | Repositório: `testes/test_repositorio_entregas_simuladas.py:320` — `[e.id for e in entregas] == [entrega_email, entrega_whatsapp]` (a entrega de `OUTRO_SEGURADO_ID` semeada em `:318` está ausente); serviço: `testes/test_lista_comunicados.py:154` — `cenario.servico.listar(CARLOS_ID) == []`; HTTP: `testes/test_lista_comunicados_api.py:166` — `resposta.json() == {"comunicados": []}`; UI (dois segurados): `SuperficieComunicados.test.tsx:107-113` — `findByText('Aviso preventivo')` para A, `findByRole('heading', {name:'Nenhum comunicado no momento'})` para B e `toHaveBeenCalledWith(OUTRO_SEGURADO_ID)` | ✅ PASS |
| AC2 — IF Carlos não possuir comunicados THEN estado vazio explicativo | Lista vazia → estado vazio, nunca erro | Serviço: `testes/test_lista_comunicados.py:116` — `cenario.servico.listar(CARLOS_ID) == []`; HTTP `200` (não 404): `testes/test_lista_comunicados_api.py:120-121` — `resposta.status_code == 200` e `resposta.json() == {"comunicados": []}`; UI: `SuperficieComunicados.test.tsx:121` — `findByRole('heading', {name:'Nenhum comunicado no momento'})` | ✅ PASS |
| AC2 (cont.) — "mantendo caminhos válidos para Alertas, Apólice e Meus Dados" | **Não precisamente definido na spec**: "caminho válido" não é operacionalizado (link navegável? item de menu? menção textual?) | `SuperficieComunicados.test.tsx:122-124` — `getByText(/Alertas/)`, `getByText(/Apólice/)`, `getByText(/Meus Dados/)`. A implementação (`SuperficieComunicados.tsx:158-161`) entrega **prosa** ("…você pode consultar Alertas, Apólice ou Meus Dados no menu lateral"), não afordâncias navegáveis; o teste afirma apenas a presença dos rótulos. Os caminhos reais moram no shell lateral, cuja gestão é da 5.7 (a superfície ainda não está montada em nenhum roteador — igual à `SuperficieAlertas` de 5.2). | ⚠️ Spec-precision gap |

### P1: Detalhe com visualização idempotente e sem regressão de estado ⭐ MVP

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| AC1 — WHEN selecionar um comunicado THEN exibir conteúdo, prévia do canal e linha do tempo; primeira abertura segue o registro idempotente de 4.3 | Ao selecionar, o detalhe de 4.3 é montado com `(seguradoId, entregaSimuladaId)` corretos e renderiza corpo + cabeçalho de canal + secção "Linha do tempo" | Seleção → detalhe de 4.3: `SuperficieComunicados.test.tsx:179-180` — `findByText('Chuva forte hoje na sua região.')` e `expect(getComunicadoMock).toHaveBeenCalledWith(SEGURADO_ID, ENTREGA_ID)`; prévia do canal e rótulo de simulação (4.3, reusado sem alteração): `SuperficieComunicado.test.tsx:97-103` — `getByText(/E-mail/)`, `getByText(/Simulação/)`, aviso de simulação; linha do tempo: `SuperficieComunicado.tsx:140-157` (`<h2>Linha do tempo</h2>` + `Criado`/`Visualização`), asserida em `SuperficieComunicados.test.tsx:227` — `findByText(/Visualizada no portal em 2026-09-05T12:05:00Z/)`; idempotência de 4.3 preservada: `SuperficieComunicado.test.tsx:83-85` — `expect(registrarVisualizacaoComunicado).not.toHaveBeenCalled()` | ✅ PASS |
| AC2 — WHEN um comunicado já `Visualizada no portal` for reaberto THEN estado e data permanecem inalterados, sem criar novo comunicado/entrega/marco | Data exibida idêntica após reabrir; **nenhum** POST de visualização disparado | `SuperficieComunicados.test.tsx:226-232` — abre, volta, reabre e então `findByText(/Visualizada no portal em 2026-09-05T12:05:00Z/)` (mesma data, valor exato) **e** `expect(registrarVisualizacaoComunicadoMock).not.toHaveBeenCalled()` (nenhum marco novo). Backend: a lista projeta a visualização já registrada sem escrever — `testes/test_lista_comunicados.py:145` — `item.visualizacao == visualizacao` (identidade com a linha criada por `registrar_primeira_visualizacao`); HTTP: `testes/test_lista_comunicados_api.py:153-156` — `item["visualizacao"] == {"id": str(visualizacao.id), "visualizada_em": visualizacao.visualizada_em.isoformat()}` | ✅ PASS |

### P2: Erro visível sem conteúdo fixo e navegação acessível

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| AC1 — IF a API responder com erro THEN falha visível com impacto e próxima ação, nunca conteúdo fixo | `role="alert"` com ocorrência/impacto/próxima ação **e** nenhuma tabela de exemplo renderizada | `SuperficieComunicados.test.tsx:140-142` — `findByRole('alert')` com `toHaveTextContent('Falha ao consultar os comunicados.')` **e** `expect(screen.queryByRole('table')).not.toBeInTheDocument()` (prova negativa do "conteúdo fixo"); falha de contexto: `:165-167` — `findByRole('alert')` com `toHaveTextContent('Não foi possível falar com o backend.')`; recuperação real (não conteúdo fixo mascarado): `:144-148`; cliente: `api/listaComunicados.test.ts:110-112` — `toBeInstanceOf(ErroListaComunicados)`, `codigo === 'identificador_invalido'`, `status === 422`; `:120-121` — `codigo === 'falha_de_rede'`; backend `422` tipado: `testes/test_lista_comunicados_api.py:174-176` — `status_code == 422`, `headers["content-type"] == "application/problem+json"`, `json()["codigo"] == "identificador_invalido"` | ✅ PASS |
| AC2 — WHEN operada por teclado/leitor de tela THEN seleção, canal, data e estado anunciados; ações nunca dependem de hover; cada linha preserva relações semânticas | Canal/data/estado em células com `<th scope="col">` correspondente; seleção anunciada; ação = `<button>` alcançável por `Tab` e ativável por `Enter`; foco devolvido à origem | Relações semânticas: `SuperficieComunicados.tsx:172-202` (`<table>` com `<caption class="sr-only">`, `<th scope="col">` para Canal/Assunto ou resumo/Data/Estado/Seleção), asserido por papel em `SuperficieComunicados.test.tsx:83` — `findByRole('cell', {name:'E-mail'})`; estado por valor exato: `:86` — `getByText('Enviada — simulação')` e `:98-99` — `findByText('Visualizada no portal')` **com** `queryByText('Enviada — simulação')` ausente; teclado sem hover: `:243-247` — `await usuario.tab()` → `toHaveFocus()` no botão "Ver detalhe" → `keyboard('{Enter}')` abre o detalhe; foco: `:202` — `findByRole('button',{name:'Voltar à lista'})).toHaveFocus()` e `:213` — foco devolvido ao botão de origem | ✅ PASS |
| AC2 (cont.) — "seleção … anunciada" | **Não precisamente definido na spec**: "anunciado" não é operacionalizado como comportamento verificável de leitor de tela | `SuperficieComunicados.test.tsx:191-192` — `document.querySelector('[aria-live="polite"]')` com `toHaveTextContent('Comunicado selecionado. Mostrando detalhe.')`. A asserção verifica **texto no DOM**, não anúncio: a região `aria-live` (`SuperficieComunicados.tsx:143-145`) é montada **junto com** o conteúdo, dentro do ramo `entregaSelecionada !== null`; leitores de tela geralmente não anunciam uma região viva inserida já preenchida. Padrão idêntico ao da `SuperficieAlertas` (5.2, `:221-222`) — não é regressão desta história, mas o teste não discrimina o comportamento real. | ⚠️ Spec-precision gap |

**Status**: ⚠️ Spec-precision gaps flagged — 6/6 requisitos `COMUNICADOS-01..06` cobertos com evidência `file:line` e valor asserido igual ao resultado definido na spec; 2 sub-cláusulas (`AC2` de P1-lista e `AC2` de P2) são imprecisas na própria spec e por isso não podem passar como "casadas com o resultado esperado". Nenhum critério ficou sem citação; nenhum ❌.

---

## Discrimination Sensor

Scratch isolado via `git worktree add …/scratchpad/sensor HEAD` (nunca `git stash`). Baseline `git status --porcelain` da árvore real: **vazio antes e depois**; worktree removido com `git worktree remove --force` e `git worktree list` volta a mostrar só a árvore principal. Baseline dos testes no scratch sem mutação: 22 passed (3 arquivos backend) e 13 passed (`SuperficieComunicados.test.tsx`).

| Mutation | File:line | Description | Killed? |
| --- | --- | --- | --- |
| 1 | `adaptadores/persistencia/repositorio_entregas_simuladas.py:199` | Removeu o isolamento por segurado no SQL (`WHERE el.segurado_id = ?` → `WHERE (el.segurado_id = ? OR TRUE)`) | ✅ Killed — 3 falhas nas três camadas: `test_listar_por_segurado_isola_por_segurado_e_deriva_assunto_ou_resumo_por_canal`, `test_listar_nao_mistura_comunicados_de_outro_segurado`, `test_listar_nao_devolve_comunicados_de_outro_segurado` |
| 2 | `adaptadores/persistencia/repositorio_entregas_simuladas.py:199` | Removeu o filtro de estado `m.estado = 'simulada_entregue'` (`→ (m.estado = ? OR TRUE)`) — ataca o Edge Case da execução não concluída | ✅ Killed — exatamente `test_listar_por_segurado_exclui_mensagem_ainda_nao_simulada_entregue` falhou |
| 3 | `adaptadores/persistencia/repositorio_entregas_simuladas.py:249` | Off-by-one no truncamento do resumo (`corpo[:_TAMANHO_RESUMO]` → `corpo[:_TAMANHO_RESUMO + 1]`) | ✅ Killed — `test_listar_por_segurado_isola_por_segurado_e_deriva_assunto_ou_resumo_por_canal` falhou (`testes/test_repositorio_entregas_simuladas.py:322`) |
| 4 | `aplicacao/lista_comunicados.py:82` | Removeu o efeito exigido: `visualizacao=self._portas.visualizacoes.obter_por_entrega(entrega.id)` → `visualizacao=None` | ✅ Killed — `test_listar_retorna_visualizacao_registrada_quando_ja_visualizado` e `test_listar_traz_visualizacao_registrada_quando_ja_visualizado` (HTTP) falharam |
| 5 | `adaptadores/http/lista_comunicados.py:156` | Guard de UUID inválido devolve `200` com lista vazia em vez do `422` problem+json | ✅ Killed — `test_listar_com_identificador_invalido_devolve_422` falhou (`200 != 422`) |
| 6 | `SuperficieComunicados.tsx:31` | `rotuloEstado` sempre `'Visualizada no portal'` (perde a distinção de estado da AC1) | ✅ Killed — 1 de 13 testes de `SuperficieComunicados.test.tsx` falhou |

**Robustez extra verificada**: `test_listar_por_segurado_ordena_por_data_e_desempata_por_id` compara a ordem do DuckDB (`ORDER BY e.criado_em, e.id`) com `sorted()` de UUIDs aleatórios do Python — executado 8 vezes consecutivas na árvore real, 8 verdes: o desempate por `id` é estável, não uma coincidência de uma execução.

**Sensor depth**: lightweight (6 mutações — acima do piso de 1-3 —, cobrindo as quatro superfícies de maior risco desta história: isolamento por segurado, filtro de elegibilidade do Edge Case, derivação do resumo, busca da visualização, tradução HTTP/422 e o rótulo de estado na UI).
**Result**: 6/6 killed — ✅ PASS

---

## Code Quality

| Principle | Status |
| --------- | ------ |
| Minimum code | ✅ — `ServicoListaComunicados` tem um único método público (`listar`) e um helper privado; nenhuma camada extra |
| Surgical changes | ✅ — 16 arquivos, todos previstos pelas tasks (4 código novo, 5 testes, `api.py`/`test_saude.py`/`openapi.json`/`tipos-gerados.ts` gerados ou de fiação, 2 `.specs`) |
| No scope creep | ✅ — nenhuma alteração em 4.3, nenhuma migração, nenhuma rota extra; o `openapi.json` só ganhou os 4 schemas + 1 path desta rota |
| No abstractions for single-use code | ✅ — `PortasListaComunicados` e os `Protocol`s privados replicam o padrão já usado por `visualizacao_comunicado.py` (4.3) e `lista_alertas_segurado.py` (5.2), não são invenção desta história |
| Matches patterns/style | ✅ — `SuperficieComunicados.tsx` espelha `SuperficieAlertas.tsx` (5.2) linha a linha nos seams: prop `seguradoId?` opcional com `getSeguradoPadrao`, `EstadoLista`, `falhaDe`, tabela com `<caption class="sr-only">`, região `aria-live`, foco devolvido à origem. O roteador HTTP replica o problem+json e o guard de UUID das rotas irmãs |
| Didn't "improve" unrelated code | ✅ — nenhum arquivo fora do escopo foi tocado |
| Spec-anchored outcome check (asserted values match spec) | ⚠️ — 2 sub-cláusulas imprecisas na spec (tabela acima); todo o restante casa com valor exato |
| Per-layer Coverage Expectation met (domain 1:1 ACs; routes happy+edge+error) | ✅ — repositório 5 testes de integração (isolamento, assunto real, resumo truncado, corpo curto, vazio, edge case de estado, ordenação); serviço 4 testes unitários mapeados 1:1 a `COMUNICADOS-01/02`; rota 5 testes cobrindo feliz + vazio + isolamento + já-visualizado + `422` |
| Every test maps to a spec requirement — no unclaimed tests | ✅ — cada `it`/`def test_` tem docstring ou `describe` citando `COMUNICADOS-NN`, um Edge Case da spec ou um "Done when" de `tasks.md` |
| Documented guidelines followed | ✅ — `AGENTS.md`/`README.md` (nomenclatura em pt-BR, docstrings obrigatórias, `ConfigDict(extra="forbid")`, problem+json, `ruff`/`pyright` estritos), conforme a Test Coverage Matrix de `tasks.md` |
| Would a senior engineer approve? | ✅ — sim; os dois pontos abertos são de precisão da spec e de padrão herdado da 5.2, não defeitos introduzidos aqui |

**`SPEC_DEVIATION` encontrado no diff** (`adaptadores/persistencia/repositorio_entregas_simuladas.py:21-26`): o `design.md` declara `listar_por_segurado(...) -> list[EntregaSimulada]` mas exige "assunto/resumo derivado" no mesmo componente — campo que `EntregaSimulada`/`ApresentacaoSimulada` não possuem. A implementação devolve um `EntregaDoSegurado` novo com `assunto_ou_resumo` já calculado e documenta o desvio no módulo. **Julgamento do Verifier**: o desvio está corretamente marcado, é a leitura mais fiel da Tech Decision do próprio `design.md` (linha 97) e não amplia escopo — aceito, mas contabilizado como sinal.

---

## Edge Cases

- [x] **Comunicado ainda não visualizado mostra "Enviada — simulação", sem antecipar a visualização** — `testes/test_lista_comunicados.py:133` (`item.visualizacao is None`), `testes/test_lista_comunicados_api.py:139` (`item["visualizacao"] is None`), UI `SuperficieComunicados.test.tsx:86` (`getByText('Enviada — simulação')`) e a prova negativa em `:99` (`queryByText('Enviada — simulação')` ausente quando já visualizado). Mutação 6 confirma que essa distinção é discriminada.
- [x] **Duas datas iguais → ordenação determinística por critério secundário estável (`id`)** — `ORDER BY e.criado_em, e.id` (`repositorio_entregas_simuladas.py:200`), asserido em `testes/test_repositorio_entregas_simuladas.py:375` — `[entrega.id for entrega in entregas] == ids_ordenados` após forçar `criado_em` idêntico via `UPDATE`. Estabilidade confirmada em 8 execuções repetidas.
- [x] **Mensagem não `simulada_entregue` não aparece na lista** — filtro `AND m.estado = ?` com `EstadoMensagem.SIMULADA_ENTREGUE` (`repositorio_entregas_simuladas.py:199,201`), asserido em `testes/test_repositorio_entregas_simuladas.py:357` — `cenario.entregas.listar_por_segurado(CARLOS_ID) == []` para uma mensagem em `REJEITADA`. Mutação 2 confirma que o teste mata a remoção do filtro.

---

## Gate Check

- **Gate command (Build)**: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright` **+** `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`
- **Result**: **1479 passed, 0 failed, 0 skipped** (backend 1068 + frontend 411). `ruff`: `All checks passed!`. `pyright`: `0 errors, 0 warnings, 0 informations`. `eslint`: exit 0 (apenas warnings pré-existentes em arquivos não tocados por esta história — `SuperficieSimulacao.tsx`, `BarraContexto.tsx`, `SuperficieResultados.tsx` etc.; **nenhum** warning nos arquivos novos). `vite build`: `✓ built in 295ms`.
- **Test count before feature** (`e462393`): backend 1054, frontend 393 → 1447
- **Test count after feature** (`b8d53ce`): backend 1068, frontend 411 → 1479
- **Delta**: +32 novos testes (backend +14, frontend +18) — nenhum teste removido, nenhuma asserção enfraquecida. `test_saude.py` só **ganhou** uma entrada no conjunto exaustivo de rotas (`:72`), mantendo o guard de não-antecipação intacto.
- **Skipped tests**: nenhum.
- **Failures**: nenhuma.

---

## Fix Plans

Nenhum bloqueador. Os dois pontos abaixo ficam registrados como observações para as histórias seguintes, não como fix tasks desta:

### Obs. 1: "caminhos válidos para Alertas, Apólice e Meus Dados" no estado vazio

- **Root cause**: a spec não operacionaliza "caminho válido"; a superfície ainda não está montada em roteador algum (a 5.7 é dona da navegação), então a implementação entrega a menção textual.
- **Onde resolver**: História 5.7, ao montar as superfícies do Segurado no shell — verificar então que o estado vazio leva de fato a Alertas/Apólice/Meus Dados.
- **Priority**: Minor.

### Obs. 2: região `aria-live` montada já preenchida

- **Root cause**: `SuperficieComunicados.tsx:143-145` renderiza a região viva dentro do ramo do detalhe, junto com o texto — leitores de tela costumam não anunciar uma região inserida já com conteúdo. Padrão herdado de `SuperficieAlertas.tsx:221-222` (5.2), não introduzido aqui; o teste assere `toHaveTextContent`, que não distingue os dois casos.
- **Onde resolver**: transversal às superfícies do Segurado (montar a região sempre e só trocar seu texto).
- **Priority**: Minor.

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
| ----------- | --------------- | ---------- |
| COMUNICADOS-01 | Implementing | ✅ Verified |
| COMUNICADOS-02 | Implementing | ✅ Verified |
| COMUNICADOS-03 | Implementing | ✅ Verified |
| COMUNICADOS-04 | Implementing | ✅ Verified |
| COMUNICADOS-05 | Implementing | ✅ Verified |
| COMUNICADOS-06 | Implementing | ✅ Verified (com a observação 2 sobre o anúncio da seleção) |

---

## Summary

**Overall**: ✅ Ready

**Spec-anchored check**: 6/6 requisitos com evidência `file:line` e valor asserido igual ao resultado definido na spec; 2 spec-precision gaps sinalizados em sub-cláusulas que a própria spec deixa imprecisas.
**Sensor**: 6/6 mutações mortas.
**Gate**: 1479 passed, 0 failed, 0 skipped; ruff/pyright/eslint/build limpos.

**What works**:

- Isolamento por segurado provado nas três camadas (repositório, serviço, HTTP) **e** na UI com dois segurados, com a mutação 1 confirmando que a prova é discriminante.
- Os três Edge Cases da spec têm teste dedicado, cada um com uma mutação correspondente que o mata.
- O reuso de 4.3 é real e verificável: nenhum arquivo de 4.3 no diff, e a reabertura de um comunicado já visualizado prova data idêntica **e** `registrarVisualizacaoComunicado` nunca chamado.
- Erro honesto com a prova negativa certa (`queryByRole('table')` ausente), e não só a presença do alerta.
- `test_saude.py` atualizado no mesmo commit da rota — o esquecimento que gerou o fix `4b5de5f` na 5.4 não se repetiu.

**Issues found**: nenhum bloqueador. Duas observações Minor (estado vazio sem afordância navegável até a 5.7; região `aria-live` montada já preenchida, padrão herdado da 5.2) e um `SPEC_DEVIATION` corretamente marcado e justificado no módulo do repositório.

**Next steps**: fechar a História 5.5. Levar as observações 1 e 2 para a 5.7 (navegação do perfil Segurado), onde as superfícies passam a ser montadas no shell.
