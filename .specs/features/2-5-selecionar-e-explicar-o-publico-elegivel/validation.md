# História 2.5: Selecionar e explicar o público elegível — Validation

**Date**: 2026-09-02
**Rodada**: **ROUND 2**
**Spec**: `.specs/features/2-5-selecionar-e-explicar-o-publico-elegivel/spec.md`
**Diff range**: `621d4ab..c7c202e` (7 commits — T1 `18a3547`, T2 `9853eee`, T3 `e6b4e5b`, T4 `7df1876`, T5 `e0338a6`, T6 `36aafd6` + correções `c7c202e`)
**Diff da correção desta rodada em isolado**: `36aafd6..c7c202e`
**Verifier**: sub-agente independente (author ≠ verifier), **distinto do verificador da Round 1** — read-only sobre a árvore real; mutações apenas em worktree descartável

**Verdict**: ❌ **FAIL** (mas **grande avanço**: 4/10 → 7/10 ACs, 3/10 → 14/18 mutantes mortos, blocker fechado)

**Histórico**: Round 1 (`621d4ab..36aafd6`) → ❌ FAIL (1 Blocker de produção + 3 GAP + 3 Partial; **7/10 mutantes sobreviveram**) → Fix 1–8 em `c7c202e` → Round 2 (este relatório) → ❌ **FAIL por 4 mutantes sobreviventes**, sendo **um deles o Success Criterion #3 literal da spec**.

**Resumo em uma frase**: o **defeito blocker de produção está genuinamente corrigido e comprovado por mutação** (reverter o semeador para o objeto JSON reproduz o `TypeError`/500 exato da Round 1 e mata o teste novo), e 5 dos 8 Fixes fecharam integralmente — mas **três Fixes foram executados só pela metade** (o congelamento do **canal** ficou de fora do Fix 2/3, a fixture **assimétrica do frontend** ficou de fora do Fix 7, o **conjunto de cabeçalhos** ficou de fora do Fix 5) e a **derivação nova de `codigo_ibge_area`** — código de produção criado nesta rodada de correção — é **posicional e não guardada**: trocar `criterios[0]` por `criterios[-1]` deixa os 378 testes verdes.

---

## Task Completion

| Task | Status | Notes |
| --- | --- | --- |
| T1 — Migração `0006_elegibilidade.sql` | ✅ Done | Inalterada; o defeito do seu backfill foi corrigido por `0007` (ver abaixo), não por reescrita retroativa — decisão correta (migrações aplicadas são imutáveis) |
| **T1b — Migração `0007_elegibilidade_correcoes.sql`** (nova, rodada de correção) | ✅ Done | Recreate-and-copy (AD-015) em `migracoes/0007_elegibilidade_correcoes.sql:20-55`; sequência `(1..7)` asserida em `test_migracoes.py:81-92` e `test_inicializador.py:73,99`; backfill de `criterios` (`:45`) e de `nome_segurado` (`:47`) asseridos valor a valor em `test_migracoes.py:246-255`. Mutantes **F2** e **F3** mortos. Nota Minor: o `JOIN segurados` de `:51` é um **INNER JOIN** — uma linha órfã (FK só lógica) seria descartada silenciosamente pela migração; não alcançável hoje, mas registrado |
| T2 — `AvaliadorElegibilidade` | ✅ **Done** (era ⚠️ Partial) | ELEG-05 agora guardada: `len(resultado.criterios) == 5` nos **6** testes de exclusão (`test_avaliador_elegibilidade.py:78,88,99,109,119,135`). Mutante **M9 morto** |
| T3 — Repositórios de elegibilidade | ⚠️ **Partial** (era ⚠️ Partial) | `apolice_id` na `UNIQUE` (M3) e coluna de área (M2) fechados; `nome_segurado` congelado em coluna própria e `codigo_ibge_area` derivado do snapshot (M4a/M4b mortos). **Mas**: o `canal` congelado continua sem guarda (**M4c sobreviveu**) e a derivação posicional de `codigo_ibge_area` continua sem guarda (**F1 sobreviveu**) |
| T4 — `ServicoAvaliacaoElegibilidade` | ✅ Done | `nome_segurado` propagado do candidato para o repositório (`aplicacao/avaliacao_elegibilidade.py:95`), asserido em `test_avaliacao_elegibilidade.py:176` (`nome_salvo == candidato.nome_segurado`) |
| T5 — Endpoint HTTP | ✅ **Done** (era ⚠️ Partial) | Caminho de 500 fechado (`test_elegibilidade_api.py:250-269`, semeia o conjunto **real** e confirma `404` + `codigo`); contagens assimétricas 2/1 (`:190-192`) matam a troca de contadores no backend. Mutante **M5 morto por dois testes** agora |
| T6 — Superfície "Evento e decisão" | ⚠️ **Partial** (era ⚠️ Partial) | Regra+versão, valor observado e resultado agora asseridos dentro da `region` da explicação (`SuperficieEventoDecisao.test.tsx:321-334`) — **M6 e M8 mortos**. **Mas**: as quantidades continuam com fixture simétrica `1`/`1` (**F4 sobreviveu**) e o conjunto de cabeçalhos continua sem asserção (**F5 sobreviveu**) |

**Lacuna de integração declarada (não é defeito desta história, inalterada)**: `SuperficieEventoDecisao` continua não montada em rota no `App.tsx` (`grep -rn "SuperficieEventoDecisao" src/frontend/src/App.tsx` → zero ocorrências, reconferido). Mesmo padrão já aceito para 2.1/2.2/2.3/2.4. Registrado, **não contado como lacuna**.

---

## Verificação das correções da Round 1

Cada Fix foi reverificado **item a item contra o texto da própria fix task da Round 1**, não contra a lista de alegações do orquestrador.

| Fix | O que a Round 1 pediu | Verificação independente (Round 2) | Resultado |
| --- | --- | --- | --- |
| **Fix 1 (Blocker)** — `obter_por_id` quebra em qualquer linha semeada | Fazer as linhas semeadas usarem formato de lista **ou** tolerar payload não-lista; **preferir a primeira opção**; teste que semeia o conjunto demonstrativo e chama `obter_por_id`/a rota de detalhe sobre uma linha semeada, asserindo **404** com `codigo`, nunca 500; a mutação "voltar o backfill para o objeto" deve matá-lo | Feito **exatamente como pedido**, na opção preferida. Migração nova `0007_elegibilidade_correcoes.sql:45` — `CASE WHEN e.execucao_id IS NULL THEN '[]' ELSE e.criterios END` (mesma convenção de `avaliacoes_risco`/`0005`); `semeador.py:270,282,294,306` — literal `"[]"` para reseedagens futuras. Teste HTTP end-to-end **com o semeador real**: `test_elegibilidade_api.py:250-269` — `SemeadorDadosSinteticos(caminho).semear()`, `SELECT id … WHERE execucao_id IS NULL`, `GET /api/v1/execucoes/{uuid4()}/elegibilidade/{id}` → `status_code == 404` **e** `codigo == "resultado_elegibilidade_inexistente"`. Teste de repositório irmão: `test_repositorio_elegibilidade.py:300-327` (`criterios == ()`, `codigo_ibge_area == ""`). **Mutação de regressão exigida pela task reinjetada (F6): reverter `semeador.py` para `'{"origem": "seed_demonstrativo"}'` → `TypeError: string indices must be integers` em `serializacao_criterios.py:33`, teste vermelho.** O `0007` também é guardado independentemente (F2 morto) | ✅ **Fechado** |
| **Fix 2 (Major)** — ELEG-06: canal congelado sem guarda (M4) | Teste que (1) salva com `canal='whatsapp'`, (2) **`UPDATE segurados SET canal_preferido='sms'`** e `UPDATE apolices SET codigo_ibge_area=…`, (3) relê e assere **`registro.canal == 'whatsapp'`** e `criterios` idêntico; *Done when*: **M4 morto** | ❌ **Executado pela metade.** O teste novo `test_repositorio_elegibilidade.py:330-365` faz o `UPDATE segurados SET nome` e o `UPDATE apolices SET codigo_ibge_area`, mas **não faz o `UPDATE … canal_preferido`** e **não assere `registro.canal`**. `tasks.md:288` reescreveu a task como "Fix 2/3" cobrindo só `nome_segurado`/`codigo_ibge_area` — o canal saiu silenciosamente do escopo. **M4c (reinjeção literal do M4: `JOIN segurados` + `s.canal_preferido` no lugar de `e.canal`) sobreviveu com 378 testes verdes.** É o **Success Criterion #3 literal** da spec | ❌ **Ainda aberto** |
| **Fix 3 (Major)** — ELEG-06: `nome_segurado`/`codigo_ibge_area` lidos ao vivo | Decidir entre (a) congelar em colunas próprias e (b) derivar a área do critério congelado; teste que altera `apolices.codigo_ibge_area` e assere coerência com `criterios[área].valor_observado` | Feito, com decisão híbrida bem justificada (a) para o nome + (b) para a área. **(a) migração**: `0007:30` (`nome_segurado VARCHAR NOT NULL`), backfill por `JOIN` em `:47,51`, asserido em `test_migracoes.py:254` (`linha[3] == "Teste"`). **(b) `salvar` grava a coluna**: `repositorio_elegibilidade.py:113` (parâmetro), `:130` (lista de colunas do `INSERT`), `:143` (valor) — asserido por releitura real em `:172` do teste. **(c) derivação**: `_codigo_ibge_area_de` (`repositorio_elegibilidade.py:196-207`) devolve `criterios[0].valor_observado if criterios else ""`; o `_SELECT_REGISTRO_ENRIQUECIDO` (`:187-193`) **não faz mais `JOIN` em `segurados` nem em `apolices`** — só em `regras` (seguro: cada versão é linha imutável). O fallback vazio não quebra em linha semeada (`test_repositorio_elegibilidade.py:327`). **(d) teste de sobrevivência**: `:330-365` — após `UPDATE` no nome e na área, `nome_segurado == "Nome Original"` e `codigo_ibge_area == AREA`. **M4a e M4b (reinjeções: voltar a ler `s.nome` / `a.codigo_ibge_area` ao vivo) mortos.** **Mas** a derivação é **posicional e não guardada**: nenhum teste persiste um snapshot com os 5 critérios reais, então `criterios[0]` → `criterios[-1]` (**F1**) **sobrevive** — com o avaliador real isso exibiria `"True"` (participação em alertas) na coluna Localização | ⚠️ **Fechado com nova lacuna** (o requisito de imutabilidade está atendido; a **corretude** da derivação nova não está guardada) |
| **Fix 4 (Major)** — `apolice_id` na `UNIQUE` sem guarda (M3) | Teste que salva dois resultados na mesma execução/evento/regra/segurado com `apolice_id` diferentes e assere `len(listar_por_execucao) == 2`; *Done when*: **M3 morto** | Feito. `test_repositorio_elegibilidade.py:368-405` — duas apólices do mesmo segurado (`ativa`/`cancelada`), `len(registros) == 2` (`:403`) **e** `{apolice_id} == {id_apolice_1, id_apolice_2}` (`:405`, identidade, não só contagem). **M3 reinjetado no lugar certo — `0007:33`, que é a definição final da tabela — e morto** (`1 = len([…])`) | ✅ **Fechado** |
| **Fix 5 (Major)** — ELEG-09: regra+versão, valor observado e resultado sem asserção (M6, M8) | Asserir o **conjunto exato de cabeçalhos** (`toEqual(['Operando','Valor observado','Resultado','Justificativa'])`), o texto `regra v3` no título e as células `9990001` e `Atende`; *Done when*: **M6 e M8 mortos** | ⚠️ **Executado em 3 de 4 itens.** `SuperficieEventoDecisao.test.tsx:321-334` — a asserção passou a ancorar numa `findByRole('region', {name: /Explicação — Maria Sintética/})` e, **dentro dela**, `getByText(/regra v3/)` (`:324`), `getByText('área afetada')` (`:325`), `getByText('9990001')` (`:326`), `getByText('Atende')` (`:327`) e a justificativa completa (`:328-332`). **M6 e M8 mortos**, como a task exigia. **Mas o conjunto de cabeçalhos não foi asserido**: `SuperficieEventoDecisao.tsx:339-342` (`Operando`/`Valor observado`/`Resultado`/`Justificativa`) segue livre — **F5** (remover os dois `<th>` do meio, mantendo os `<td>`) **sobrevive**, e a metade "em **colunas estáveis**" da ELEG-09 continua sem evidência | ⚠️ **Parcialmente fechado** |
| **Fix 6 (Major)** — ELEG-05: resultado excluído sem prova de carregar **cada** critério (M9) | `assert len(resultado.criterios) == 5` em **pelo menos um** teste de exclusão; *Done when*: **M9 morto** | Feito **acima do pedido**: a asserção foi acrescentada aos **6** testes de exclusão — `test_avaliador_elegibilidade.py:78,88,99,109,119,135`. **M9 reinjetado literalmente** (`criterios if elegivel else tuple(c for c in criterios if not c.atende)`) e **morto em 6 testes simultaneamente** | ✅ **Fechado** |
| **Fix 7 (Minor)** — contagens incluídos/excluídos intercambiáveis (M7) | Quantidades **assimétricas** em `test_repositorio_elegibilidade.py`, `test_elegibilidade_api.py` **e na fixture `elegibilidade()` do frontend**; no frontend, asserir cada quantidade **junto do seu rótulo** em vez de `getAllByText('1')`; *Done when*: **M7 morto** | ⚠️ **Executado só no backend.** `test_elegibilidade_api.py:174-193` — terceiro registro `Ana Sintética` incluído, `corpo["incluidos"] == 2` / `corpo["excluidos"] == 1`, `len(registros) == 3`. **M7 (troca dos dois `count(*) FILTER` em `repositorio_elegibilidade.py:156`) morto.** **Mas** a fixture do frontend continua `incluidos: 1, excluidos: 1` (`SuperficieEventoDecisao.test.tsx:60-61`) e a asserção continua `getAllByText('1')).toHaveLength(2)` (`:258`) — **F4** (trocar `incluidos`↔`excluidos` no render, `SuperficieEventoDecisao.tsx:270-272`) **sobrevive**, exatamente a lacuna que a task nomeava. `test_repositorio_elegibilidade.py:260-261` também segue `1`/`1`, mas o teste HTTP cobre a mesma consulta | ⚠️ **Parcialmente fechado** |
| **Fix 8 (Minor)** — ELEG-01: coluna de área não pinada (M2) | Segurado com `codigo_ibge_area` **diferente** da área da sua apólice; asserir que `listar_candidatos` usa a **da apólice**; *Done when*: **M2 morto** | Feito. `test_repositorio_elegibilidade.py:408-422` — `inserir_segurado(area="9990099")` + `inserir_apolice(area=AREA)`, `len(candidatos) == 1`, `apolice_id` correto, `codigo_ibge_area == AREA`. **M2 reinjetado** (`WHERE a.codigo_ibge_area` → `WHERE s.codigo_ibge_area`, `repositorio_elegibilidade.py:79`) **e morto** | ✅ **Fechado** |

**Placar dos Fixes**: **5 fechados** (1, 4, 6, 8 e — com ressalva — 3), **3 parcialmente executados** (2, 5, 7).

**Diff da correção**: `36aafd6..c7c202e` toca 14 arquivos — 1 migração nova, 4 arquivos de produção (`repositorio_elegibilidade.py`, `semeador.py`, `avaliacao_elegibilidade.py`, README de persistência), 7 arquivos de teste backend, 1 de teste frontend e 2 de spec. Nenhuma rota, nenhum contrato: `openapi.json` inalterado e ainda sincronizado (`test_openapi_sincronizado.py` verde), conjunto exato de caminhos sob `/api/v1` inalterado (`test_saude.py:46-47`).

---

## Spec-Anchored Acceptance Criteria

Mapeamento ID→AC pela ordem da `spec.md`: ELEG-01..03 = as 3 ACs da 1ª story P1; ELEG-04..07 = as 4 ACs da 2ª story P1; ELEG-08..10 = as 3 ACs da story P2.

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + asserção | Result |
| --- | --- | --- | --- |
| **ELEG-01** — avaliar considerando **somente** segurados e apólices sintéticos do conjunto demonstrativo | Candidatos vêm exclusivamente de `segurados`/`apolices` semeados, filtrados pela área **da apólice** | `repositorio_elegibilidade.py:75-81` — único `SELECT`, sobre `apolices JOIN segurados`, `WHERE a.codigo_ibge_area = ?`, sem nenhuma fonte externa. Testes: `test_repositorio_elegibilidade.py:109-117` (identidade + 5 campos de valor); `:127` (`candidatos == []` para outra área); **novo `:408-422`** — segurado em `9990099`, apólice em `9990001`, `len(candidatos) == 1` **e** `candidatos[0].codigo_ibge_area == AREA`, pinando a **coluna da apólice**. **M2 morto** | ✅ **PASS** (era ⚠️ Partial) |
| **ELEG-02** — avaliar área, tipo e situação da apólice, coberturas e participação em alertas | Exatamente esses 5 critérios, cada um capaz de excluir sozinho | `avaliador_elegibilidade.py:149-155` — a tupla dos 5. `test_avaliador_elegibilidade.py:66` — `len == 5` no caso incluído; exclusão isolada de cada um em `:75,86,96,107,116,130`, agora **todas com `len(criterios) == 5`**. **M1 morto** | ✅ **PASS** |
| **ELEG-03** — canal preferencial preservado para a comunicação futura, **sem alterar** o resultado dos demais critérios | Mesma decisão com canais diferentes; `canal` do resultado igual ao do candidato | `test_avaliador_elegibilidade.py:139-141,149` — `elegivel` idêntico com `whatsapp`/`email`, `canal` copiado; Independent Test literal da spec em `:122-135` (`participa_de_alertas=False` + `canal_preferido="sms"` → excluído, `canal == "sms"`, `len(criterios) == 5`). Código: `avaliador_elegibilidade.py:168` — `canal` só é copiado, nunca comparado | ✅ **PASS** (no domínio; o **congelamento na persistência** é ELEG-06, e lá segue a lacuna) |
| **ELEG-04** — segurado+apólice que atendem integralmente → resultado `incluido` **associado à execução, evento, versão da regra, segurado e apólice**, com **todos** os critérios satisfeitos | Linha `elegivel = true` ligada às 5 chaves, com os 5 critérios `atende = true` | Domínio: `test_avaliador_elegibilidade.py:63-66`. Serviço: `test_avaliacao_elegibilidade.py:169-177` — a tupla inteira passada a `salvar` (execução, evento, regra, segurado, apólice, **nome**) + `resultado.elegivel is True`. Persistência (round-trip real de DuckDB): `test_repositorio_elegibilidade.py:166-174` — `execucao_id`, `elegivel`, `canal`, `criterios == RESULTADO_INCLUIDO.criterios`, `nome_segurado`, `codigo_ibge_area`, `regra_versao == 1`. HTTP: `test_elegibilidade_api.py:229-234` — `regra_id`, `regra_versao == 3`, `elegivel is True` | ✅ **PASS** |
| **ELEG-05** — ao menos um critério não atendido → resultado `excluido` **com o resultado de cada critério**, identificando objetivamente o que impediu | Resultado excluído carrega **os 5** critérios (satisfeitos e não satisfeitos) + motivo/justificativa específicos | Motivo e justificativa por causa: `test_avaliador_elegibilidade.py:74-77,86-88,95-99,105-109,114-119,130-135`. **"Cada critério" agora asserido nos 6**: `:78,88,99,109,119,135` — `len(resultado.criterios) == 5`. **M9 morto** | ✅ **PASS** (era ❌ GAP) |
| **ELEG-06** — dados originais alterados **depois** de uma execução concluída → snapshots imutáveis conservados, **sem que a explicação histórica seja reescrita** | Reler o registro após `UPDATE` em `segurados`/`apolices`/`regras` devolve exatamente os valores do momento da avaliação | **Nome** ✅: coluna `nome_segurado` (`0007:30`), gravada em `repositorio_elegibilidade.py:143`; `test_repositorio_elegibilidade.py:353-364` — `UPDATE segurados SET nome='Nome Alterado Depois'` e a releitura devolve `"Nome Original"`. **Área** ✅: derivada do snapshot (`repositorio_elegibilidade.py:196-207,223`); `:357-365` — `UPDATE apolices SET codigo_ibge_area='9999999'` e a releitura devolve `AREA`. **`regra_versao`** ✅ estrutural (versões de regra são linhas imutáveis, 2.4). **Canal** ❌: a coluna `e.canal` existe e é lida (`:189`), mas **nenhum teste altera `segurados.canal_preferido` depois da execução e relê** | ❌ **GAP** — **M4c sobreviveu**: reintroduzir `JOIN segurados` + `s.canal_preferido` deixa os **378** testes verdes. É o **Success Criterion #3 literal** ("Alterar o canal preferencial de um segurado depois de uma execução concluída não altera o resultado histórico dessa execução"), e o `README.md` de persistência (`:155`) promete "nunca referência viva a `segurados.canal_preferido`" — promessa ainda **não executável**. Segunda lacuna: **F1 sobreviveu** (`criterios[0]` → `criterios[-1]` em `_codigo_ibge_area_de`), então a **corretude** da derivação nova não é medida por nenhum teste |
| **ELEG-07** — mesma combinação (execução, evento, versão de regra, segurado, apólice) reprocessada/retomada → **no máximo um** resultado, sem originar mensagem duplicada | Exatamente 1 linha por combinação; 2ª tentativa é no-op; **e uma linha por apólice distinta** | Dedup (round-trip real de banco): `test_repositorio_elegibilidade.py:207-209` — `primeiro is not None`, **`segundo is None`**, `len(listar_por_execucao) == 1`. Nível SQL: `test_migracoes.py:290-321`. Serviço: `test_avaliacao_elegibilidade.py:188-190`. **`apolice_id` na `UNIQUE` agora guardado**: `test_repositorio_elegibilidade.py:368-405` — duas apólices do mesmo segurado → `len == 2` e os dois ids presentes. **M3 e M10 mortos** | ✅ **PASS** (era ⚠️ Partial) |
| **ELEG-08** — a interface exibe quantidades de incluídos/excluídos e tabela com segurado, apólice, localização, canal e resultado, permitindo abrir critérios e justificativa **sem depender de hover** | As duas quantidades corretas e distinguíveis; as 5 colunas; abertura por teclado | Backend: `test_elegibilidade_api.py:190-193` — **`incluidos == 2`**, `excluidos == 1`, `len == 3`, `nomes` e `canais` como conjuntos de 3. **M7 morto.** Frontend tabela: `SuperficieEventoDecisao.test.tsx:280-285` — 6 valores de célula reais. Teclado: `:311-341` — `focus()` + `toHaveFocus()` + `{Enter}` abre a explicação e `getDetalheElegibilidade` é chamado com os dois argumentos certos (sem hover em nenhum ponto). Quantidades no frontend: `:257-260` — `getAllByText('1')).toHaveLength(2)` + `getByText(/incluído/)` + `getByText(/excluído/)` | ⚠️ **Partial** — a distinção **é** guardada no backend, mas **não na interface**, que é o sujeito literal da AC ("a **interface** SHALL exibir as quantidades de incluídos e excluídos"). Fixture continua simétrica (`:60-61`, `1`/`1`) e a asserção conta ocorrências do dígito: **F4 sobreviveu** (trocar `incluidos`↔`excluidos` em `SuperficieEventoDecisao.tsx:270-272` deixa os 15 testes verdes) |
| **ELEG-09** — a explicação exibe **regra e versão, operando, valor observado, resultado e justificativa** em colunas estáveis, distinguindo inclusões e exclusões por **texto, ícone e cor** | Os 5 campos visíveis em colunas fixas + os 3 sinais de distinção | **Texto+ícone+cor** ✅: `SuperficieEventoDecisao.test.tsx:298-303` — classe modificadora **de cada estado** + `svg[data-icone-nome="check-circle"]`/`"x-circle"` + o texto (`:284-285`). **Os 5 campos** ✅ (**novo**): dentro de `findByRole('region', {name:/Explicação — Maria Sintética/})` (`:321-323`) — `regra v3` (`:324`), `área afetada` (`:325`), `9990001` (`:326`), `Atende` (`:327`) e a justificativa completa (`:328-332`). **M6 e M8 mortos.** **Colunas estáveis** ❌: os `<th>` de `SuperficieEventoDecisao.tsx:339-342` não são asseridos | ⚠️ **Partial** — 4 dos 5 elementos da AC agora com evidência discriminante; **F5 sobreviveu** (apagar os `<th>` `Valor observado` e `Resultado` da tabela de critérios deixa os 15 testes verdes, desalinhando a tabela sem nenhum teste vermelho). É a metade "em **colunas estáveis**", e era o item explicitamente nomeado pela Fix task 5 (`toEqual([...])`, padrão de `SuperficieRegras.test.tsx:118-130`) |
| **ELEG-10** — nenhum registro satisfaz a regra → conjunto vazio **válido**, não falha técnica, **sem chamada à OpenAI e sem criar mensagem** | `200`/contagem zero/lista vazia; zero chamadas de IA; nenhuma mensagem | Serviço: `test_avaliacao_elegibilidade.py:143-145` — `incluidos == 0`, `excluidos == 0`, **`elegibilidades.chamadas == []`** (prova de **ausência** de escrita). HTTP: `test_elegibilidade_api.py:131-135` — `200`, `incluidos == 0`, `excluidos == 0`, `registros == []`. Repositório: `test_repositorio_elegibilidade.py:267`. Frontend: `SuperficieEventoDecisao.test.tsx:269-270` — texto de vazio **e** `queryByRole('alert')` ausente. Sem IA: garantia **estrutural** — `PortasAvaliacaoElegibilidade` não expõe porta de IA e `grep -rn "openai"` nos módulos da história devolve zero | ✅ **PASS** (nota A — o caso literal "candidatos existem mas **nenhum** satisfaz" segue não testado: o teste de vazio usa **zero candidatos**) |

**Status**: ❌ **Gaps presentes** — **7 PASS**, **2 Partial**, **1 GAP** de 10 ACs (Round 1: 4 PASS / 3 Partial / 3 GAP).

**Spec-precision gaps**: **nenhum**. A `spec.md` 2.5 define resultado preciso para as 10 ACs; todas as lacunas restantes são de **evidência de teste**.

### Notas de julgamento

**Nota A — ELEG-10.** Herdada da Round 1, não endereçada: falta um teste de serviço com candidatos que **existem** e nenhum satisfaz (`incluidos == 0`, `excluidos == N`). Minor, não bloqueante.

**Nota B — 404 por execução divergente.** `test_elegibilidade_api.py:286` continua asserindo só o status. **Mitigado nesta rodada**: o teste irmão novo `:250-269` exercita o **mesmo** ramo do roteador (`http/elegibilidade.py:237`) e assere `codigo == "resultado_elegibilidade_inexistente"`. M5 agora morre em **dois** testes.

**Nota C — `role="status"` perdido.** `SuperficieEventoDecisao.test.tsx:127` segue com `getByText('Carregando decisão de risco…')` no lugar de `getByRole('status')` (contorno da ambiguidade dos dois indicadores). Minor, inalterado.

**Nota D — INNER JOIN na migração `0007`.** `0007:44-51` copia via `JOIN segurados`. As FKs de `elegibilidades_historicas` são **lógicas**, não impostas pelo DuckDB; uma linha cujo `segurado_id` não exista em `segurados` seria **descartada silenciosamente** pela migração. Não alcançável com o conjunto semeado atual (as 4 linhas têm segurado), mas um `LEFT JOIN` com `COALESCE(s.nome, '')` seria estritamente mais seguro. Minor, registrado.

**Nota E — semeador vs. migração.** `semeador.py:272,284,296,308` repete literalmente `"Pessoa Segurada Sintética DEMO-00N"` em `nome_segurado`, duplicando o valor de `segurados.nome` (`:79,86,93,100`). Estão corretos hoje (conferido linha a linha), mas **nenhum teste assere a coerência** entre as duas colunas do próprio seed — um dos dois pode ser editado sem o outro.

**Nota F — acoplamento posicional novo.** `_codigo_ibge_area_de` (`repositorio_elegibilidade.py:207`) depende de "área afetada" ser sempre `criterios[0]` em `avaliador_elegibilidade.py:150`. É verdade hoje e está documentado no docstring, mas é um acoplamento **implícito entre dois módulos de camadas diferentes**, sem teste que o segure (F1 sobreviveu). Filtrar por `operando == "área afetada"` (ou asserir a posição num teste do avaliador) removeria a fragilidade.

---

## Discrimination Sensor

Uma worktree isolada e descartável (`git worktree add --detach <scratch> c7c202e`), revertida com `git checkout -- .` entre mutações e removida com `git worktree remove --force` + `git worktree prune`. O `node_modules` do frontend foi apenas **symlinkado** para dentro da worktree e o link removido antes da remoção — nada foi escrito na árvore real. Nenhum `git stash` usado. **Baseline na worktree antes de mutar**: 378 testes backend verdes; 15/15 em `SuperficieEventoDecisao.test.tsx`.

### Mutantes reinjetados da Round 1

| # | Mutação | File:line | Descrição | Testes executados | Killed? |
| --- | --- | --- | --- | --- | --- |
| **M1** | Critério de alertas sempre atende | `dominio/avaliador_elegibilidade.py:110` | `atende = candidato.participa_de_alertas` → `atende = True` | `testes/` (378) | ✅ **Killed** — `test_sem_nenhuma_participacao_de_alertas_exclui_independente_do_canal` falha em `:132` |
| **M2** | Área lida do segurado, não da apólice | `repositorio_elegibilidade.py:79` | `WHERE a.codigo_ibge_area = ?` → `WHERE s.codigo_ibge_area = ?` | `testes/` (378) | ✅ **Killed** (era Survived) — `test_listar_candidatos_filtra_pela_area_da_apolice_nao_do_segurado` falha em `:420` |
| **M3** | `apolice_id` fora da `UNIQUE` | `migracoes/0007_elegibilidade_correcoes.sql:33` (definição **final** da tabela) | `UNIQUE (…, segurado_id, apolice_id)` → `UNIQUE (…, segurado_id)` | `testes/` (378) | ✅ **Killed** (era Survived) — `test_duas_apolices_do_mesmo_segurado_geram_dois_resultados_distintos` falha em `:403` (`1 = len([…])`) |
| **M4a** | `nome_segurado` lido ao vivo | `repositorio_elegibilidade.py:189,191` | `e.nome_segurado` → `s.nome` + `JOIN segurados AS s ON s.id = e.segurado_id` | `testes/` (378) | ✅ **Killed** — `test_nome_segurado_e_area_persistidos_sobrevivem_a_mudanca_dos_dados_originais` falha em `:364` |
| **M4b** | `codigo_ibge_area` lido ao vivo | `repositorio_elegibilidade.py:190,191,223` | `JOIN apolices AS a` + coluna extra `a.codigo_ibge_area`, `codigo_ibge_area=_codigo_ibge_area_de(criterios)` → `str(linha[13])` | `testes/` (378) | ✅ **Killed** — falha em `:365` **e** em `test_obter_por_id_de_linha_semeada_com_criterios_vazio_nao_lanca:327` |
| **M4c** | **Canal lido ao vivo em vez de congelado** (reinjeção literal do M4 da Round 1) | `repositorio_elegibilidade.py:189,191` | `e.canal` → `s.canal_preferido` + `JOIN segurados AS s ON s.id = e.segurado_id` | `testes/` (378) | ❌ **Survived** — **378 passed**. O snapshot de canal (AD-11, ELEG-06, **Success Criterion #3**) segue sem nenhuma guarda: nenhum teste faz `UPDATE segurados SET canal_preferido` depois da avaliação |
| **M5** | Guarda de execução no detalhe HTTP | `adaptadores/http/elegibilidade.py:237` | `if registro is None or registro.execucao_id != execucao_uuid:` → `if registro is None:` | `testes/` (378) | ✅ **Killed** — agora por **dois** testes: `test_get_registro_elegibilidade_de_outra_execucao_retorna_404` **e** `test_get_registro_elegibilidade_semeado_retorna_404_nao_500:268` |
| **M6** | Regra+versão fora da explicação | `SuperficieEventoDecisao.tsx:330` | `Explicação — {nomeSegurado} (regra v{regraVersao})` → `Explicação — {nomeSegurado}` | `SuperficieEventoDecisao.test.tsx` (15) | ✅ **Killed** (era Survived) — 1 failed \| 14 passed; falha em `:324` (`getByText(/regra v3/)`) |
| **M7** | Contagens trocadas (SQL) | `repositorio_elegibilidade.py:156` | os dois `count(*) FILTER` invertidos | `testes/` (378) | ✅ **Killed** (era Survived) — `test_get_elegibilidade_retorna_quantidades_e_lista_completa` falha em `:192` (a fixture assimétrica 2/1 torna a troca visível) |
| **M8** | Duas células da explicação apagadas | `SuperficieEventoDecisao.tsx:349-350` | remoção de `<td>{criterio.valorObservado}</td>` e `<td>{criterio.atende ? 'Atende' : 'Não atende'}</td>` | `SuperficieEventoDecisao.test.tsx` (15) | ✅ **Killed** (era Survived) — 1 failed \| 14 passed |
| **M9** | Resultado excluído perde os critérios satisfeitos | `dominio/avaliador_elegibilidade.py:167` | `criterios=criterios` → `criterios=criterios if elegivel else tuple(c for c in criterios if not c.atende)` | `testes/` (378) | ✅ **Killed** (era Survived) — **6 testes** vermelhos simultaneamente (`test_avaliador_elegibilidade.py`, todos os casos de exclusão) |
| **M10** | Dedup removida do `INSERT` | `repositorio_elegibilidade.py:132` | `"ON CONFLICT DO NOTHING RETURNING id"` → `"RETURNING id"` | `testes/` (378) | ✅ **Killed** — `_duckdb.ConstraintException` em `repositorio_elegibilidade.py:127`, prova de round-trip real de banco |

### Mutantes novos desta rodada (sobre o código criado pela correção)

| # | Mutação | File:line | Descrição | Testes executados | Killed? |
| --- | --- | --- | --- | --- | --- |
| **F1** | **Derivação de área trocada de posição** | `repositorio_elegibilidade.py:207` | `return criterios[0].valor_observado if criterios else ""` → `criterios[-1]…` | `testes/` (378) | ❌ **Survived** — **378 passed**. Todas as fixtures persistidas têm **um único** critério, então `[0]` e `[-1]` coincidem. Com o avaliador real (5 critérios), a coluna Localização passaria a exibir `"True"` (valor observado de "participação em alertas"), contradizendo o `criterios[área].valor_observado` do mesmo payload — exatamente o defeito que o Fix 3 dizia estar fechando |
| **F2** | **Backfill de `criterios` revertido** | `migracoes/0007_elegibilidade_correcoes.sql:45` | `CASE WHEN e.execucao_id IS NULL THEN '[]' ELSE e.criterios END` → `e.criterios` | `testes/` (378) | ✅ **Killed** — `test_migracao_elegibilidade_preserva_linha_semeada_com_backfill_correto` falha em `:252` (`+ {"origem": "seed_demonstrativo"}`) |
| **F3** | **Backfill de `nome_segurado` esvaziado** | `migracoes/0007_elegibilidade_correcoes.sql:47` | `s.nome` → `''` (satisfaz o `NOT NULL`, perde o dado) | `testes/` (378) | ✅ **Killed** — mesmo teste falha em `:254` (`linha[3] == "Teste"`) |
| **F4** | **Contadores trocados na interface** | `SuperficieEventoDecisao.tsx:270-272` | `{elegibilidade.incluidos}` ↔ `{elegibilidade.excluidos}` (nos três pontos: valor, pluralização e valor) | `SuperficieEventoDecisao.test.tsx` (15) | ❌ **Survived** — **15 passed**. Fixture simétrica (`test.tsx:60-61`, `1`/`1`) + asserção por contagem de dígito (`:258`). A ELEG-08 fala da **interface**, e é lá que a troca é invisível |
| **F5** | **Cabeçalhos da explicação removidos** | `SuperficieEventoDecisao.tsx:340-341` | remoção dos `<th scope="col">Valor observado</th>` e `<th scope="col">Resultado</th>` (as `<td>` permanecem, a tabela desalinha) | `SuperficieEventoDecisao.test.tsx` (15) | ❌ **Survived** — **15 passed**. As asserções novas do Fix 5 olham **células**, não o conjunto de **colunas**; "colunas estáveis" da ELEG-09 segue sem guarda |
| **F6** | **Regressão do blocker no semeador** | `adaptadores/persistencia/semeador.py:270,282,294,306` | `"[]"` → `'{"origem": "seed_demonstrativo"}'` (4 ocorrências) | `testes/` (378) | ✅ **Killed** — `test_get_registro_elegibilidade_semeado_retorna_404_nao_500` levanta `TypeError: string indices must be integers, not 'str'` em `serializacao_criterios.py:33`. **Prova que o teste de regressão do Fix 1 reproduz exatamente o defeito da Round 1, e não apenas "um caminho parecido"** |

**Sensor depth**: **P0-full** (integridade de dados — 18 mutações nesta rodada: 12 reinjetadas + 6 novas; ≥5 exigidas pelo protocolo)

**Result**: **14/18 killed, 4 survived** — ❌ **FAIL**. Acumulado da história: **17/28 mutantes mortos** (Round 1: 3/10). Dos 7 sobreviventes da Round 1, **6 morreram**; o remanescente (M4, agora M4c) segue vivo.

**Verificação de isolamento**: `git status --porcelain` vazio **antes** (`BASELINE:[]`) e **depois** (`POST-SENSOR STATUS:[]`) do ciclo de mutações; `git worktree list` mostra apenas a árvore real em `c7c202e`; o diretório de scratch não existe mais; `src/frontend/node_modules` da árvore real segue diretório real (não symlink). Nenhum arquivo do projeto foi modificado por esta rodada exceto este `validation.md`.

---

## Payload / Conjunction Rule

Regra aplicada: a asserção precisa olhar **valor devolvido e/ou estado persistido**, não "a chamada aconteceu" nem um status isolado.

| Alvo | Asserção verifica valor real? | Evidência |
| --- | --- | --- |
| `GET .../elegibilidade` 200 vazio | ✅ Sim | `test_elegibilidade_api.py:131-135` — status **+** `incluidos == 0`, `excluidos == 0`, `registros == []` |
| `GET .../elegibilidade` 200 preenchido | ✅ **Sim (fechado nesta rodada)** | `:190-193` — status **+** `incluidos == 2` **≠** `excluidos == 1` **+** `len == 3` **+** conjunto de 3 nomes **+** conjunto de 3 canais. M7 morto |
| `GET .../elegibilidade` 422 | ✅ Sim | `:206-208` — status + `content-type: application/problem+json` + `codigo == "execucao_id_invalido"` |
| `GET .../elegibilidade/{id}` 200 | ✅ Sim | `:226-235` — status **+** `id`, `regra_id`, `regra_versao == 3`, `elegivel is True`, `len(criterios) == 1`, `operando`, `atende is True`, `justificativa.startswith(...)` |
| `GET .../elegibilidade/{id}` 404 inexistente | ✅ Sim | `:246-247` — status + `codigo` |
| `GET .../elegibilidade/{id}` 404 **de linha semeada real** | ✅ **Sim (novo)** | `:268-269` — status **+** `codigo == "resultado_elegibilidade_inexistente"`, com o conjunto demonstrativo **realmente semeado** no banco. Fecha o caminho de 500 da Round 1 |
| `GET .../elegibilidade/{id}` 404 de outra execução | ⚠️ **Parcial** | `:286` — só `status_code == 404` (nota B); mitigado pelo teste irmão acima, que exercita o mesmo ramo com `codigo` |
| `GET .../elegibilidade/{id}` 422 | ✅ Sim | `:296-297` — status + `codigo == "identificador_invalido"` |
| `RepositorioElegibilidades.salvar` | ✅ Sim | `test_repositorio_elegibilidade.py:165-174` — id devolvido **e** releitura real do banco com 7 asserções de valor |
| `RepositorioElegibilidades.salvar` (dedup) | ✅ Sim | `:207-209` — `primeiro is not None` **e** `segundo is None` **e** estado persistido relido |
| `RepositorioElegibilidades.salvar` (duas apólices) | ✅ **Sim (novo)** | `:402-405` — `len(registros) == 2` **e** `{apolice_id}` **de identidade**, não só contagem |
| **Snapshot imutável (nome/área)** | ✅ **Sim (novo)** | `:353-365` — dois `UPDATE` reais nas tabelas fonte **e** releitura por `obter_por_id` asserindo os valores originais |
| **Snapshot imutável (canal)** | ❌ **Não** | Nenhum teste faz `UPDATE segurados SET canal_preferido` depois da avaliação. **M4c sobreviveu** |
| `contar_por_execucao` | ⚠️ **Parcial** | `test_repositorio_elegibilidade.py:260-261` — valores reais, mas ainda simétricos (`1`/`1`); a assimetria vive só no teste HTTP |
| `listar_candidatos` (área da apólice) | ✅ **Sim (novo)** | `:420-422` — `len == 1` **+** `apolice_id` **+** `codigo_ibge_area == AREA`, com a área do segurado **diferente** |
| Migração `0007` (backfill) | ✅ Sim | `test_migracoes.py:246-255` — os 5 valores da linha semeada relidos do banco (`execucao_id`, `criterios == "[]"`, `canal`, `nome_segurado`, `justificativa`) |
| Migração `0007` (`UNIQUE`) | ✅ Sim | `:296` e `:321` — contagens reais após inserções concorrentes |
| `ServicoAvaliacaoElegibilidade` — efeito | ✅ Sim | `test_avaliacao_elegibilidade.py:169-177` — a **tupla inteira** passada a `salvar`, incluindo `nome_salvo == candidato.nome_segurado`; `:145` — `chamadas == []` prova **ausência** de escrita |
| Cliente HTTP frontend | ✅ Sim | `elegibilidade.test.ts:52,74,137-139,90,99,166` |
| Superfície — tabela | ✅ Sim | `SuperficieEventoDecisao.test.tsx:280-285` — 6 valores de célula reais |
| Superfície — distinção | ✅ Sim | `:298-303` — classe modificadora **de cada estado** **e** ícone **de cada estado** **e** o texto |
| **Superfície — explicação** | ✅ **Sim (fechado nesta rodada)** | `:321-334` — `region` nomeada **+** `regra v3` **+** operando **+** valor observado **+** `Atende` **+** justificativa completa **+** os dois argumentos da chamada. M6 e M8 mortos |
| **Superfície — quantidades** | ❌ **Não** | `:258` — `getAllByText('1')).toHaveLength(2)`: conta ocorrências do dígito, não liga cada quantidade ao seu rótulo. **F4 sobreviveu** |
| **Superfície — colunas da explicação** | ❌ **Não** | Os `<th>` de `SuperficieEventoDecisao.tsx:339-342` não são asseridos. **F5 sobreviveu** |

---

## Code Quality

| Princípio | Status |
| --- | --- |
| Minimum code | ✅ — a correção acrescenta 1 migração, 1 coluna, 1 parâmetro e 1 função de 1 linha; a alternativa (2ª coluna para a área) foi corretamente evitada |
| Surgical changes | ✅ — 14 arquivos em `36aafd6..c7c202e`, todos rastreáveis a um Fix nomeado; nenhuma rota, nenhum contrato, `openapi.json` inalterado |
| No scope creep | ✅ — nenhuma transição de estado de execução, nenhuma geração de mensagem, nenhuma rota extra (`test_saude.py:46-47` fixa o conjunto exato de caminhos) |
| Matches patterns | ✅ — `0007` segue o recreate-and-copy de `0005`/`0006` (AD-015); `'[]'` reusa a convenção de `avaliacoes_risco`; `nome_segurado` segue o padrão de snapshot de `regra_versao` em 2.3 |
| Spec-anchored outcome check | ⚠️ — **7/10** ACs com asserção casando o resultado da spec (era 4/10); ELEG-06 sem evidência para o canal, ELEG-08 e ELEG-09 sem evidência para uma metade cada |
| Per-layer Coverage Expectation | ⚠️ — domínio 1:1 (ELEG-05 fechada); rota cobre feliz + vazio + 404 (×3 causas, incluindo linha semeada real) + 422 (×2) ✅; componente cobre carregando/vazio/erro/tabela/teclado/explicação, mas não quantidades por rótulo nem conjunto de colunas |
| Every test maps to a spec requirement | ✅ — os 5 testes backend novos mapeiam a Fix 1 (×2), Fix 3, Fix 4 e Fix 8; nenhum teste órfão |
| Documented guidelines followed | ✅ — `README.md` de persistência atualizado com a coluna nova, a correção do backfill e a **decisão de derivar a área** (`:164-166`), com justificativa AD-11 (fecha a lição L-022 de 2.4) |
| Docstring/contrato correspondem ao comportamento | ⚠️ — `README.md:155` continua prometendo que `canal` "nunca [é] referência viva a `segurados.canal_preferido`": **verdade hoje**, mas M4c mostra que nenhum teste sustenta a promessa (mesma pendência da Round 1). O docstring de `_codigo_ibge_area_de` (`:197-205`) afirma corretamente o acoplamento posicional, mas nenhum teste o segura (F1) |

---

## Edge Cases

- [x] **Segurado com mais de uma apólice na área afetada, uma elegível e outra não → um resultado distinto por combinação** — **fechado nesta rodada**. Listagem: `test_repositorio_elegibilidade.py:142-144`. **Persistência**: `:368-405` — as duas linhas salvas e as duas identidades de apólice conferidas. **M3 morto**
- [x] **Área do evento cobre parcialmente a área de risco da apólice → mesmo critério objetivo, sem inferência probabilística** — igualdade exata de código IBGE (`avaliador_elegibilidade.py:49`); `test_avaliador_elegibilidade.py:70-78` cobre o não-casamento; determinismo asserido em `:157-161`
- [x] **Retomada após reinicialização do backend no meio do processamento → continua do progresso persistido, sem recriar resultados já gravados** — `test_repositorio_elegibilidade.py:207-209` e `test_avaliacao_elegibilidade.py:186-190`; M10 confirma que a garantia é da `UNIQUE` do banco
- [x] **Conjunto vazio válido** — `test_avaliacao_elegibilidade.py:143-145`, `test_elegibilidade_api.py:131-135`, `SuperficieEventoDecisao.test.tsx:269-270` (nota A)
- [x] **Linha semeada consultada pelo detalhe HTTP** — **defeito de produção da Round 1 corrigido e guardado**: `test_elegibilidade_api.py:250-269` + `test_repositorio_elegibilidade.py:300-327`; regressão comprovada por F6
- [ ] **Canal preferencial alterado depois da execução concluída** (Success Criterion #3) — **ainda sem teste**; M4c sobrevive

---

## Gate Check

- **Gate command (Build)**: `uv run pytest -q && uv run ruff check . && uv run pyright` (em `src/backend`) + `npx vitest run && npm run lint && npm run build` (em `src/frontend`)
- **Executado nesta rodada pelo próprio Verificador** (não herdado do orquestrador), na árvore real em `c7c202e`:
  - `pytest`: **378 passed**, 0 failed, 0 skipped (exit 0, 20.91s)
  - `ruff check .`: **All checks passed!** (exit 0)
  - `pyright`: **0 errors, 0 warnings, 0 informations** (exit 0)
  - `vitest run`: **202 passed** em 23 arquivos, 0 failed (exit 0, 7.27s)
  - `npm run lint` (`oxlint`): exit 0 — **11 warnings**, todas pré-existentes de `react(set-state-in-effect)` / `react(only-export-components)`; nenhuma nova nesta rodada de correção
  - `npm run build`: **✓ built in 229ms** (exit 0)
- **Test count antes da feature** (fim de 2.4, `621d4ab`): 340 backend / 189 frontend
- **Test count na Round 1** (`36aafd6`): 373 backend / 202 frontend
- **Test count na Round 2** (`c7c202e`): **378 backend / 202 frontend**
- **Delta da rodada de correção**: **+5 backend / +0 frontend** — coerente: 5 testes backend novos (2 do Fix 1, 1 do Fix 3, 1 do Fix 4, 1 do Fix 8) e, no frontend, o Fix 5 **fortaleceu um teste existente** em vez de criar outro
- **Delta total da história**: **+38 backend / +13 frontend**
- **Test Integrity**: ✅ nenhum teste removido no diff `36aafd6..c7c202e`; **nenhuma asserção enfraquecida**. As edições em testes pré-existentes são todas **fortalecimentos ou adaptações mecânicas** ao parâmetro/coluna novos: `(1..6)` → `(1..7)` em `test_migracoes.py`/`test_inicializador.py` (migração nova), a tupla de `chamadas` do repositório falso ganhou um elemento, os `INSERT` de teste ganharam a coluna `nome_segurado`, a fixture HTTP passou de 1/1 para 2/1 e as asserções de `SuperficieEventoDecisao.test.tsx:321-334` **aumentaram** de 2 para 6 — aumento de poder discriminante medido (M6 e M8 morrem hoje e sobreviviam na Round 1). Um valor asserido **mudou**: `test_migracoes.py:252`, de `'{"origem": "seed_demonstrativo"}'` para `"[]"` — é a correção do defeito, não um enfraquecimento (F2 prova que a nova asserção é viva)
- **Skipped**: nenhum
- **Failures**: nenhuma

---

## Fix Plans

### Fix 9 (**Major**) — ELEG-06 / Success Criterion #3: canal congelado ainda sem guarda (M4c)

- **Root cause**: o Fix 2 da Round 1 pedia três `UPDATE` e três asserções; a implementação entregou dois (`nome`, `codigo_ibge_area`) e **omitiu o canal**, que era justamente o campo nomeado no Success Criterion. `tasks.md:288` reescreveu a task como "Fix 2/3" sem o canal.
- **Fix task** — *What*: no teste já existente `test_nome_segurado_e_area_persistidos_sobrevivem_a_mudanca_dos_dados_originais` (`testes/test_repositorio_elegibilidade.py:330-365`), acrescentar `conexao.execute("UPDATE segurados SET canal_preferido = 'sms' WHERE id = ?", [id_segurado])` ao bloco de `:353-359` e `assert registro.canal == "whatsapp"` (mais `assert registro.criterios == RESULTADO_INCLUIDO.criterios`) ao bloco de `:363-365`. Renomear o teste para incluir o canal. **Zero linhas de produção.** *Verify*: reinjetar M4c literalmente (`e.canal` → `s.canal_preferido` em `repositorio_elegibilidade.py:189` + `JOIN segurados AS s ON s.id = e.segurado_id` em `:191`) e confirmar vermelho. *Done when*: **M4c morto**.
- **Priority**: **Major** (Success Criterion #3 literal da spec; promessa explícita do `README.md:155`)

### Fix 10 (**Major**) — ELEG-06: derivação de `codigo_ibge_area` posicional e sem guarda (F1)

- **Root cause**: `_codigo_ibge_area_de` (`repositorio_elegibilidade.py:207`) assume `criterios[0]`, mas nenhuma fixture persistida tem mais de um critério — `[0]` e `[-1]` são indistinguíveis em todos os 378 testes. Um reordenamento futuro da tupla de `avaliador_elegibilidade.py:149-155` reescreveria silenciosamente a Localização exibida.
- **Fix task** — *What*: preferencialmente **selecionar por nome** em vez de por posição (`next((c.valor_observado for c in criterios if c.operando == "área afetada"), "")`), e **em qualquer caso** acrescentar um teste que persista um `ResultadoElegibilidade` produzido pelo **avaliador real** (`avaliar(candidato, evento, regra)`, com os 5 critérios) e assere, na releitura, `registro.codigo_ibge_area == AREA` **e** `len(registro.criterios) == 5`. *Where*: `repositorio_elegibilidade.py:196-207` e `testes/test_repositorio_elegibilidade.py`. *Verify*: reinjetar F1 (`criterios[0]` → `criterios[-1]`) e confirmar vermelho. *Done when*: **F1 morto**.
- **Priority**: **Major** (código de produção novo, criado pela própria rodada de correção, sem guarda; o defeito seria um payload internamente contraditório — a Localização exibida divergindo do `valor_observado` do critério de área)

### Fix 11 (**Minor**) — ELEG-08: quantidades intercambiáveis **na interface** (F4)

- **Root cause**: o Fix 7 da Round 1 pedia a assimetria também na fixture do frontend e a asserção de cada quantidade junto do seu rótulo; só o backend foi ajustado.
- **Fix task** — *What*: mudar a fixture `elegibilidade()` (`SuperficieEventoDecisao.test.tsx:60-61`) para `incluidos: 2, excluidos: 1` e trocar `getAllByText('1')).toHaveLength(2)` (`:258`) por asserções ligadas ao rótulo — p.ex. `expect(within(secao).getByText(/2 incluídos/)).toBeInTheDocument()` e `getByText(/1 excluído/)`, ou expor `data-contador="incluidos"/"excluidos"` em `SuperficieEventoDecisao.tsx:270-272` e asserir `toHaveTextContent`. Ajustar `test_repositorio_elegibilidade.py:260-261` para 2/1 na mesma varredura. *Verify*: reinjetar F4 (trocar `incluidos`↔`excluidos` no render). *Done when*: **F4 morto**.
- **Priority**: **Minor** (o dado do backend está correto e guardado; o risco é de exibição invertida)

### Fix 12 (**Minor**) — ELEG-09: "colunas estáveis" da explicação sem guarda (F5)

- **Root cause**: o Fix 5 da Round 1 nomeava explicitamente `toEqual(['Operando','Valor observado','Resultado','Justificativa'])`; a implementação escolheu asserir células. Células e cabeçalhos são sinais independentes.
- **Fix task** — *What*: dentro da `region` da explicação (`SuperficieEventoDecisao.test.tsx:321-323`), acrescentar `const cabecalhos = within(explicacao).getAllByRole('columnheader').map((c) => c.textContent)` e `expect(cabecalhos).toEqual(['Operando','Valor observado','Resultado','Justificativa'])` — padrão já vigente em `SuperficieRegras.test.tsx:118-130`. *Verify*: reinjetar F5 (remover os dois `<th>` do meio, `SuperficieEventoDecisao.tsx:340-341`). *Done when*: **F5 morto**.
- **Priority**: **Minor**

### Itens Minor adicionais, opcionais (não bloqueantes)

- **Nota A** — ELEG-10: teste de serviço com candidatos que **existem** e nenhum satisfaz (`incluidos == 0`, `excluidos == N`).
- **Nota B** — acrescentar `codigo == "resultado_elegibilidade_inexistente"` a `test_elegibilidade_api.py:286` (o teste irmão já cobre o ramo).
- **Nota C** — recuperar a asserção de `role="status"` em `SuperficieEventoDecisao.test.tsx:127` com `getAllByRole('status')` + `toHaveTextContent`.
- **Nota D** — trocar o `JOIN segurados` de `0007:51` por `LEFT JOIN` + `COALESCE(s.nome, '')`, para que a migração nunca descarte linha órfã em silêncio.
- **Nota E** — asserir, num teste do semeador, que `elegibilidades_historicas.nome_segurado` casa com `segurados.nome` para a mesma linha semeada.
- **Nota F** — ver Fix 10 (seleção por `operando` em vez de posição).
- **Integração** — montar `SuperficieEventoDecisao` em rota no `App.tsx` (lacuna declarada, compartilhada com 2.1/2.2/2.3/2.4; item próprio).

---

## Lições candidatas (grounding para `.specs/lessons.json`)

| Origem fundamentada | Lição proposta |
| --- | --- |
| Fix 2 e Fix 7 executados pela metade; `tasks.md:288` funde "Fix 2/3" e perde o canal | **Uma fix task que enumera N asserções precisa ser reverificada item a item contra o texto original da task, não contra o resumo do implementador.** Quando a rodada de correção reagrupa ou renomeia as tasks ("Fix 2/3"), um item enumerado pode sair de escopo silenciosamente — foi o que aconteceu com o canal, que era o **Success Criterion literal** da spec. Reincidência direta da lição equivalente registrada em 2.4 (R1→R2) |
| **F1 sobreviveu** (código novo do Fix 3) | **Toda rodada de correção deve mutar o código que ela mesma criou.** A correção do Fix 3 substituiu um `JOIN` vivo por uma derivação nova, e a derivação nasceu sem guarda: as fixtures existentes tinham **um único** critério, tornando `criterios[0]` e `criterios[-1]` indistinguíveis. Corolário prático: **quando uma função indexa uma coleção por posição, a fixture precisa ter pelo menos 3 elementos** — com 1 elemento, todo índice é o mesmo índice |
| F1 + o docstring de `_codigo_ibge_area_de` | **Um acoplamento posicional entre camadas ("o critério X é sempre o primeiro") documentado em docstring é uma promessa não executável.** Selecionar por identificador (`operando == "área afetada"`) custa uma linha e elimina a classe inteira de defeito; se a posição for mesmo necessária, ela precisa de um teste no módulo que a produz |
| **F4 e F5 sobreviveram**; **L-024 reincide pela quinta superfície** | **Reforçar L-024**: quando a AC enumera N campos/colunas da interface, asserir os N — e asserir **célula e cabeçalho separadamente**, porque são sinais independentes (F5 prova que asserir só as células deixa as colunas livres para sumir). O padrão barato é `expect(getAllByRole('columnheader').map(c => c.textContent)).toEqual([...])` |
| F4; a fixture simétrica do frontend não acompanhou a do backend | **Quando uma fixture simétrica é corrigida numa camada, a mesma correção precisa ser aplicada em todas as camadas que a espelham.** `1`/`1` no frontend anula, sozinho, o ganho da assimetria `2`/`1` no backend — a AD-08 fala da *interface* |
| **F6 morto** | **Um teste de regressão de blocker deve ser validado reinjetando o defeito original literalmente.** Aqui reverter `semeador.py` para o objeto JSON reproduziu o `TypeError` exato da Round 1 no teste novo — evidência de que o teste mede o defeito, não um caminho vizinho. Este é o padrão a exigir de todo Fix marcado Blocker |
| Migração `0007` como **correção aditiva** de `0006` | **Um backfill errado numa migração já aplicada corrige-se com uma migração nova, nunca editando a antiga.** A `0007` faz recreate-and-copy, corrige o valor e ainda acrescenta a coluna de snapshot na mesma transação — e o teste de migração assere **linha por valor**, matando F2 e F3 |
| Nota D (INNER JOIN em `0007:51`) | **Um `INSERT … SELECT … JOIN` numa migração de recreate-and-copy descarta linhas órfãs em silêncio.** Com FKs apenas lógicas, o padrão seguro é `LEFT JOIN` + `COALESCE`, e o teste de migração deve conferir a **contagem** de linhas antes e depois, não só os valores de uma linha |

---

## Requirement Traceability Update

| Requirement | Previous Status (Round 1) | New Status (Round 2) |
| --- | --- | --- |
| ELEG-01 | ⚠️ Parcial — Needs Fix (Fix 8) | ✅ **Verified** (M2 morto) |
| ELEG-02 | ✅ Verified | ✅ Verified |
| ELEG-03 | ✅ Verified | ✅ Verified |
| ELEG-04 | ✅ Verified | ✅ Verified |
| ELEG-05 | ❌ Needs Fix (Fix 6) | ✅ **Verified** (M9 morto em 6 testes) |
| ELEG-06 | ❌ Needs Fix (Fix 2, Fix 3) | ❌ **Needs Fix** (Fix 9, Fix 10) — nome e área fechados (M4a/M4b mortos); **canal** e **corretude da derivação** abertos |
| ELEG-07 | ⚠️ Parcial — Needs Fix (Fix 4) | ✅ **Verified** (M3 e M10 mortos) |
| ELEG-08 | ⚠️ Parcial — Needs Fix (Fix 7) | ⚠️ **Parcial — Needs Fix** (Fix 11) — backend fechado (M7 morto); interface aberta (F4) |
| ELEG-09 | ❌ Needs Fix (Fix 5) | ⚠️ **Parcial — Needs Fix** (Fix 12) — os 5 campos fechados (M6/M8 mortos); "colunas estáveis" aberta (F5) |
| ELEG-10 | ✅ Verified (nota A) | ✅ Verified (nota A) |

**7/10 Verified, 2 Parciais, 1 Needs Fix** (Round 1: 4/10 Verified, 3 Parciais, 3 Needs Fix).

---

## Summary

**Overall**: ❌ **Not Ready** — a história não fecha nesta rodada, mas fica a **um passo curto** de fechar

**Spec-anchored check**: **7/10 ACs** com asserção casando integralmente o resultado definido pela spec (era 4/10); 2 parciais e 1 com lacuna. **Zero spec-precision gaps**
**Sensor**: **14/18 mutantes mortos, 4 sobreviveram** (P0-full: 12 reinjeções + 6 mutações novas). Dos 7 sobreviventes da Round 1, **6 morreram**
**Gate**: 378 backend + 202 frontend passed, 0 failed, 0 skipped; `ruff`/`pyright`/`lint`/`build` verdes — todos re-executados pelo Verificador na árvore real

**O que funciona**: o **defeito blocker está genuinamente fechado**, e isso foi medido, não aceito — reverter `semeador.py` para o objeto JSON reproduz o `TypeError: string indices must be integers` exato da Round 1 dentro do teste novo (F6 morto), e o backfill da migração é guardado por conta própria (F2 e F3 mortos). A escolha de corrigir por **migração aditiva** (`0007`, recreate-and-copy) em vez de editar a `0006` já aplicada é a decisão certa, e o `README.md` de persistência documenta o porquê. A decisão híbrida do Fix 3 — congelar o **nome** em coluna e **derivar** a área do snapshot de critérios, sem uma segunda cópia armazenada — é elegante e está comprovada nas duas pontas: reintroduzir qualquer um dos dois `JOIN` vivos mata testes (M4a e M4b). E os quatro Fixes de asserção que a Round 1 pediu por escrito foram entregues com poder discriminante real: `apolice_id` na `UNIQUE` (M3), coluna de área do candidato (M2), "cada critério" numa exclusão (M9, vermelho em 6 testes de uma vez) e os cinco campos da explicação na interface (M6 e M8). Sete ACs agora casam com o resultado da spec, contra quatro na rodada anterior.

**Problemas encontrados**: quatro, todos de **evidência**, nenhum de produção. (1) **O canal congelado continua sem guarda** — o Fix 2 da Round 1 pedia três `UPDATE` e três asserções; entregou dois e deixou de fora justamente o campo que a spec nomeia no **Success Criterion #3** ("alterar o canal preferencial depois da execução não altera o resultado histórico"). Reintroduzir a leitura viva de `segurados.canal_preferido` deixa os 378 testes verdes. (2) **A derivação nova de `codigo_ibge_area` é posicional e não guardada**: todas as fixtures persistidas têm **um único** critério, então `criterios[0]` e `criterios[-1]` são indistinguíveis — com o avaliador real (5 critérios) a coluna Localização passaria a exibir `"True"`, contradizendo o `valor_observado` do critério de área no mesmo payload. É código de produção **criado por esta rodada de correção**, e a rodada não o mutou. (3) e (4) Duas metades de AC ficaram para trás porque os Fixes 7 e 5 foram aplicados só numa camada: a fixture do frontend continua simétrica (`1`/`1`, trocar os contadores na tela é invisível) e o conjunto de cabeçalhos da explicação continua sem asserção (apagar dois `<th>` desalinha a tabela sem teste vermelho).

**Next steps**: rotear os **Fix 9–12** de volta ao implementador. **Nenhum deles exige mudança de produção**, exceto uma linha opcional no Fix 10 (trocar a indexação posicional por seleção pelo `operando`); são quatro edições de teste, três delas dentro de testes que já existem. Depois da correção, **reverificar reinjetando literalmente M4c, F1, F4 e F5** e confirmando que cada um morre — e, ao fazê-lo, conferir cada fix task **item a item contra o seu texto**, que é exatamente onde esta rodada perdeu três itens. Esta foi a **iteração 2 de no máximo 3**; o orçamento restante é suficiente, dado que os quatro itens abertos são pequenos e bem localizados.
