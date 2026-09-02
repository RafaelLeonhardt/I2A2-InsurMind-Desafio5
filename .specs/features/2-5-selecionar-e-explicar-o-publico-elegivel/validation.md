# História 2.5: Selecionar e explicar o público elegível — Validation

**Date**: 2026-09-02
**Rodada**: **ROUND 3 (final)** — rodada de confirmação da correção da Round 2
**Spec**: `.specs/features/2-5-selecionar-e-explicar-o-publico-elegivel/spec.md`
**Diff range**: `621d4ab..49bf647` (8 commits — T1 `18a3547`, T2 `9853eee`, T3 `e6b4e5b`, T4 `7df1876`, T5 `e0338a6`, T6 `36aafd6` + correções `c7c202e` e `49bf647`)
**Diff da correção desta rodada em isolado**: `c7c202e..49bf647`
**Verifier**: sub-agente independente (author ≠ verifier), **distinto dos verificadores da Round 1 e da Round 2** — read-only sobre a árvore real; mutações apenas em worktree descartável

**Verdict**: ✅ **PASS**

**Histórico**: Round 1 (`621d4ab..36aafd6`) → ❌ FAIL (**1 blocker de produção** — `TypeError`/`500` em qualquer linha semeada — + 3 GAP + 3 Partial; 7/10 mutantes sobreviveram) → Fix 1–8 em `c7c202e` → Round 2 → ❌ FAIL por 4 mutantes sobreviventes, todos de **evidência**, nenhum de produção → Fix 9–12 em `49bf647` → Round 3 (este relatório) → ✅ **PASS**.

**Resumo em uma frase**: os quatro itens abertos da Round 2 foram fechados e **medidos por mutação, não aceitos** — reintroduzir a leitura viva de `segurados.canal_preferido` (**M4c**, o Success Criterion #3 literal), trocar os contadores de incluídos/excluídos na tela (**F4**) e apagar dois `<th>` da tabela de critérios (**F5**) agora deixam a suíte **vermelha**, e o acoplamento posicional de `_codigo_ibge_area_de` (**F1**) foi **eliminado por construção**, o que uma experiência de reordenação em worktree confirmou empiricamente (com os critérios reordenados, o código antigo devolve `'residencial'` como Localização; o novo devolve `'9990001'`). As 10 ACs da spec agora têm asserção que casa com o resultado definido.

---

## Task Completion

| Task | Status | Notes |
| --- | --- | --- |
| T1 — Migração `0006_elegibilidade.sql` | ✅ Done | Inalterada; o defeito do seu backfill foi corrigido pela migração aditiva `0007` (migrações aplicadas são imutáveis — decisão correta, AD-015) |
| T1b — Migração `0007_elegibilidade_correcoes.sql` | ✅ Done | Reconferida nesta rodada: `CASE WHEN e.execucao_id IS NULL THEN '[]' ELSE e.criterios END` (`0007:45`) e backfill de `nome_segurado` por `s.nome` (`0007:47,51`) **intactos**; F2/F3 seguem mortos (R2). Nota D (INNER JOIN em `:51`) permanece Minor, registrada |
| T2 — `AvaliadorElegibilidade` | ✅ Done | ELEG-05 guardada (`len(resultado.criterios) == 5` em 7 asserções de `test_avaliador_elegibilidade.py`); nesta rodada o módulo passou a exportar `OPERANDO_AREA_AFETADA` (`:16-19`), usado pelo próprio critério (`:61`) e pelo mapa de motivos (`:133`) |
| T3 — Repositórios de elegibilidade | ✅ **Done** (era ⚠️ Partial) | Os dois itens que sobravam fecharam: o **canal congelado** agora é guardado por asserção (M4c morto) e a derivação de `codigo_ibge_area` deixou de ser posicional (`repositorio_elegibilidade.py:210-213`). `_SELECT_REGISTRO_ENRIQUECIDO` (`:188-194`) lê `e.canal` da própria linha histórica e faz `JOIN` **apenas** em `regras` — nenhuma releitura viva de `segurados`/`apolices` |
| T4 — `ServicoAvaliacaoElegibilidade` | ✅ Done | Inalterado desde a R2; `nome_segurado` propagado e asserido (`test_avaliacao_elegibilidade.py:176`) |
| T5 — Endpoint HTTP | ✅ Done | Inalterado; o teste de regressão do blocker (`test_elegibilidade_api.py:248-267`) segue vivo — reverter o semeador reproduz o `TypeError` original (F6 remorto nesta rodada) |
| T6 — Superfície "Evento e decisão" | ✅ **Done** (era ⚠️ Partial) | Quantidades assimétricas com asserção do parágrafo inteiro (`SuperficieEventoDecisao.test.tsx:253,258-261`) e conjunto exato de cabeçalhos da explicação (`:326-333`). **F4 e F5 mortos** |
| Fix 1–12 (Verifier R1 + R2) | ✅ **12 fechados** | Fix 1, 3–6, 8 confirmados na R2; Fix 2 (via Fix 9), 5 (via Fix 12), 7 (via Fix 11) e 10 confirmados nesta rodada |

**Lacuna de integração declarada (não é defeito desta história, inalterada)**: `SuperficieEventoDecisao` continua não montada em rota no `App.tsx` (`grep -rn "SuperficieEventoDecisao" src/frontend/src/App.tsx` → zero ocorrências, reconferido). Mesmo padrão já aceito para 2.1/2.2/2.3/2.4. Registrado, **não contado como lacuna**.

---

## Verificação das correções da Round 2

Cada Fix foi reverificado **item a item contra o texto da própria fix task da Round 2**, não contra a lista de alegações do orquestrador — que foi exatamente onde a rodada anterior perdeu três itens.

| Fix | O que a Round 2 pediu | Verificação independente (Round 3) | Resultado |
| --- | --- | --- | --- |
| **Fix 9 (Major)** — ELEG-06 / Success Criterion #3: canal congelado sem guarda (M4c) | Acrescentar `UPDATE segurados SET canal_preferido = 'sms'` ao teste existente e asserir `registro.canal == "whatsapp"`; **zero linhas de produção**; *Done when*: **M4c morto** | Feito **exatamente como pedido**, e sem produção. `testes/test_repositorio_elegibilidade.py:333` — o teste declara o segurado com `inserir_segurado(caminho, canal="whatsapp")`; `:356-360` — o `UPDATE` passou a alterar **`nome` e `canal_preferido` na mesma sentença**; `:371-372` — **duas** asserções: `registro.canal == RESULTADO_INCLUIDO.canal` (liga o valor persistido ao do momento da avaliação) **e** `registro.canal == "whatsapp"` (literal, imune a uma edição da fixture). A docstring (`:333-338`) cita o Success Criterion #3 nominalmente. **Alegação de "produção não mudou" verificada de forma independente**: `git diff c7c202e..49bf647 -- …/repositorio_elegibilidade.py` não toca a `SELECT`, e `_SELECT_REGISTRO_ENRIQUECIDO:190` lê `e.canal` (coluna congelada da própria linha histórica), com `FROM elegibilidades_historicas AS e JOIN regras AS r` (`:192-193`) e **nenhum `JOIN segurados`**. **M4c reinjetado literalmente e morto** (`assert 'sms' == 'whatsapp'`) | ✅ **Fechado** |
| **Fix 10 (Major)** — derivação de `codigo_ibge_area` posicional e sem guarda (F1) | **Preferencialmente** selecionar por nome em vez de por posição; **em qualquer caso** um teste que persista um resultado do avaliador real (5 critérios); *Done when*: **F1 morto** | **Item preferencial feito, item "em qualquer caso" não.** A constante `OPERANDO_AREA_AFETADA` foi criada em `dominio/avaliador_elegibilidade.py:16-19` — **uma única fonte da verdade**, consumida pelo produtor (`_criterio_area:61`), pelo mapa de motivos (`:133`) e pelo consumidor (`repositorio_elegibilidade.py:14,211`) — e `_codigo_ibge_area_de` passou a fazer `next((c for c in criterios if c.operando == OPERANDO_AREA_AFETADA), None)` (`:210-213`). **A alegação "isso remove a suposição de ordenação" foi verificada empiricamente**, não por leitura: numa worktree descartável, reordenar a tupla de `avaliar` (`avaliador_elegibilidade.py:155-161`, área **por último**) e persistir um resultado real de 5 critérios devolve `codigo_ibge_area = '9990001'` (**correto**) com o código novo e `codigo_ibge_area = 'residencial'` (**incorreto**, o `valor_observado` do critério de tipo de apólice) com o código posicional antigo — a **classe inteira de defeito** que F1 nomeava está eliminada por construção. **Mas o teste com snapshot de 5 critérios não foi acrescentado**, então uma reescrita errada da função (`criterios[-1]`) ainda passa nos 378 testes — ver **Nota F** e o item Minor correspondente | ✅ **Fechado** (classe de defeito eliminada e comprovada; resíduo de evidência registrado como Minor) |
| **Fix 11 (Minor)** — ELEG-08: quantidades intercambiáveis na interface (F4) | Fixture do frontend assimétrica (`incluidos: 2, excluidos: 1`) e asserção ligada ao **rótulo**, não à contagem do dígito; *Done when*: **F4 morto** | Feito nas duas metades. `SuperficieEventoDecisao.test.tsx:253` — `elegibilidade({ incluidos: 2, excluidos: 1 })` (a fábrica aceita sobrescritas, `:59-61`); `:258-261` — a asserção deixou de contar dígitos e passou a ancorar no parágrafo (`getByText(/incluíd/).closest('p')`), normalizar espaços e exigir o **texto completo** `'2 incluídos — 1 excluído'`, que casa número **e** rótulo **e** pluralização. **F4 reinjetado (troca de `incluidos`↔`excluidos` nos três pontos de `SuperficieEventoDecisao.tsx:270-272`) e morto**: `expected '1 incluído — 2 excluídos' to contain '2 incluídos — 1 excluído'` | ✅ **Fechado** |
| **Fix 12 (Minor)** — ELEG-09: "colunas estáveis" da explicação sem guarda (F5) | `getAllByRole('columnheader')` com `toEqual(['Operando','Valor observado','Resultado','Justificativa'])`, dentro da `region` da explicação; *Done when*: **F5 morto** | Feito **literalmente**, no padrão de `SuperficieRegras.test.tsx:118-130`. `SuperficieEventoDecisao.test.tsx:326` — `within(explicacao).getByRole('table')` (ancora na tabela **de critérios**, não na do público); `:327-333` — `getAllByRole('columnheader').map(...)` + `toEqual([...])` com a lista exata e ordenada. As asserções de célula da R2 (`:334-341`) foram **mantidas**, então célula e cabeçalho seguem como sinais independentes. **F5 reinjetado (remoção dos `<th>` `Valor observado` e `Resultado` de `SuperficieEventoDecisao.tsx:340-341`) e morto**: `expected [ 'Operando', 'Justificativa' ] to deeply equal [ 'Operando', 'Valor observado', …(2) ]` | ✅ **Fechado** |

**Placar dos Fixes**: **4 de 4 fechados**; acumulado da história **12 de 12**.

**Diff da correção**: `c7c202e..49bf647` toca 6 arquivos — 2 de produção (`avaliador_elegibilidade.py` +9/−4, `repositorio_elegibilidade.py` +14/−11, ambos rastreáveis ao Fix 10), 2 de teste (`test_repositorio_elegibilidade.py` +15/−15, `SuperficieEventoDecisao.test.tsx` +19/−8) e 2 de spec (`tasks.md` +13, `validation.md`). Nenhuma rota, nenhum contrato, nenhuma migração: `openapi.json` inalterado e `test_openapi_sincronizado.py` verde.

---

## Spec-Anchored Acceptance Criteria

Mapeamento ID→AC pela ordem da `spec.md`: ELEG-01..03 = as 3 ACs da 1ª story P1; ELEG-04..07 = as 4 ACs da 2ª story P1; ELEG-08..10 = as 3 ACs da story P2.

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + asserção | Result |
| --- | --- | --- | --- |
| **ELEG-01** — avaliar considerando **somente** segurados e apólices sintéticos do conjunto demonstrativo | Candidatos vêm exclusivamente de `segurados`/`apolices` semeados, filtrados pela área **da apólice** | `repositorio_elegibilidade.py:75-81` — único `SELECT`, sobre `apolices JOIN segurados`, `WHERE a.codigo_ibge_area = ?`, sem fonte externa. Testes: `test_repositorio_elegibilidade.py:109-117` (identidade + 5 campos de valor); `:127` (`candidatos == []` para outra área); `:415-429` — segurado em `9990099`, apólice em `9990001`, `len(candidatos) == 1` **e** `candidatos[0].codigo_ibge_area == AREA` (`:429`), pinando a coluna da apólice. **M2 morto** (R2) | ✅ **PASS** |
| **ELEG-02** — avaliar área, tipo e situação da apólice, coberturas e participação em alertas | Exatamente esses 5 critérios, cada um capaz de excluir sozinho | `avaliador_elegibilidade.py:155-161` — a tupla dos 5, agora com o critério de área nomeado pela constante compartilhada (`:61`). `test_avaliador_elegibilidade.py` — `len(resultado.criterios) == 5` em **7** asserções (caso incluído + os 6 casos de exclusão isolada). **M1 e M9 mortos** (R1/R2) | ✅ **PASS** |
| **ELEG-03** — canal preferencial preservado para a comunicação futura, **sem alterar** o resultado dos demais critérios | Mesma decisão com canais diferentes; `canal` do resultado igual ao do candidato | `test_avaliador_elegibilidade.py:139-141,149` — `elegivel` idêntico com `whatsapp`/`email`, `canal` copiado; Independent Test literal da spec em `:122-135` (`participa_de_alertas=False` + `canal_preferido="sms"` → excluído, `canal == "sms"`, `len(criterios) == 5`). Código: `avaliador_elegibilidade.py:174` — `canal` só é copiado, nunca comparado. O congelamento na persistência é ELEG-06, agora também fechado | ✅ **PASS** |
| **ELEG-04** — segurado+apólice que atendem integralmente → resultado `incluido` **associado à execução, evento, versão da regra, segurado e apólice**, com **todos** os critérios satisfeitos | Linha `elegivel = true` ligada às 5 chaves, com os 5 critérios `atende = true` | Domínio: `test_avaliador_elegibilidade.py:63-66`. Serviço: `test_avaliacao_elegibilidade.py:169-177` — a tupla inteira passada a `salvar`. Persistência (round-trip real de DuckDB): `test_repositorio_elegibilidade.py:166-174` — `execucao_id`, `elegivel`, `canal`, `criterios`, `nome_segurado`, `codigo_ibge_area`, `regra_versao == 1`. HTTP: `test_elegibilidade_api.py:229-234` — `regra_id`, `regra_versao == 3`, `elegivel is True` | ✅ **PASS** |
| **ELEG-05** — ao menos um critério não atendido → resultado `excluido` **com o resultado de cada critério**, identificando objetivamente o que impediu | Resultado excluído carrega **os 5** critérios (satisfeitos e não satisfeitos) + motivo/justificativa específicos | Motivo e justificativa por causa: `test_avaliador_elegibilidade.py:74-77,86-88,95-99,105-109,114-119,130-135`; "cada critério" asserido nos **6** casos de exclusão. **M9 morto em 6 testes simultaneamente** (R2) | ✅ **PASS** |
| **ELEG-06** — dados originais alterados **depois** de uma execução concluída → snapshots imutáveis conservados, **sem que a explicação histórica seja reescrita** | Reler o registro após `UPDATE` em `segurados`/`apolices`/`regras` devolve exatamente os valores do momento da avaliação | **Um único teste cobre os três campos**: `test_repositorio_elegibilidade.py:330-372` — salva o resultado, executa `UPDATE segurados SET nome = 'Nome Alterado Depois', canal_preferido = 'sms'` (`:356-360`) **e** `UPDATE apolices SET codigo_ibge_area = '9999999'` (`:361-363`), relê por `obter_por_id` e assere `nome_segurado == "Nome Original"` (`:369`), `codigo_ibge_area == AREA` (`:370`) e **`canal == "whatsapp"`** (`:371-372`). Código: `nome_segurado` é coluna própria (`0007:30`, gravada em `repositorio_elegibilidade.py:143`), `canal` é a coluna congelada `e.canal` (`:190`) e a área é **derivada do snapshot** por nome de operando (`:210-213`); a `SELECT` faz `JOIN` só em `regras` (linhas imutáveis por versão, 2.4). `regra_versao` ✅ estrutural. **M4a, M4b e M4c mortos** — reintroduzir qualquer um dos três `JOIN` vivos deixa a suíte vermelha | ✅ **PASS** (era ❌ GAP; **Success Criterion #3 agora executável**. Nota F: a *correção* da derivação de área tem guarda apenas com fixture de 1 critério — Minor, não bloqueante, ver sensor) |
| **ELEG-07** — mesma combinação (execução, evento, versão de regra, segurado, apólice) reprocessada/retomada → **no máximo um** resultado, sem originar mensagem duplicada | Exatamente 1 linha por combinação; 2ª tentativa é no-op; **e uma linha por apólice distinta** | Dedup (round-trip real de banco): `test_repositorio_elegibilidade.py:207-209` — `primeiro is not None`, **`segundo is None`**, `len(listar_por_execucao) == 1`. Nível SQL: `test_migracoes.py:290-321`. Serviço: `test_avaliacao_elegibilidade.py:188-190`. `apolice_id` na `UNIQUE`: `:375-412` — duas apólices do mesmo segurado → `len == 2` **e** os dois ids presentes. **M3 e M10 mortos** (R2) | ✅ **PASS** |
| **ELEG-08** — a interface exibe quantidades de incluídos/excluídos e tabela com segurado, apólice, localização, canal e resultado, permitindo abrir critérios e justificativa **sem depender de hover** | As duas quantidades corretas e **distinguíveis**; as 5 colunas; abertura por teclado | Backend: `test_elegibilidade_api.py:190-193` — `incluidos == 2`, `excluidos == 1`, `len == 3` (**M7 morto**, R2). **Interface (fechado nesta rodada)**: `SuperficieEventoDecisao.test.tsx:253` — fixture **assimétrica** `2`/`1`; `:258-261` — o parágrafo inteiro normalizado deve conter `'2 incluídos — 1 excluído'`, ligando cada número ao seu rótulo. Tabela: `:280-285` — 6 valores de célula reais. Teclado: `:311-345` — `focus()` + `toHaveFocus()` + `{Enter}` abre a explicação e `getDetalheElegibilidade` recebe os dois argumentos certos, sem hover em nenhum ponto. **F4 morto** | ✅ **PASS** (era ⚠️ Partial) |
| **ELEG-09** — a explicação exibe **regra e versão, operando, valor observado, resultado e justificativa** em colunas estáveis, distinguindo inclusões e exclusões por **texto, ícone e cor** | Os 5 campos visíveis em colunas fixas + os 3 sinais de distinção | **Texto+ícone+cor** ✅: `SuperficieEventoDecisao.test.tsx:298-303` — classe modificadora **de cada estado** + `svg[data-icone-nome="check-circle"]`/`"x-circle"` + o texto. **Os 5 campos** ✅: dentro de `findByRole('region', {name:/Explicação — Maria Sintética/})` — `regra v3` (`:325`), `área afetada` (`:334`), `9990001` (`:335`), `Atende` (`:336`) e a justificativa completa (`:337-341`). **Colunas estáveis** ✅ **(fechado nesta rodada)**: `:326-333` — `within(tabelaCriterios).getAllByRole('columnheader')` com `toEqual(['Operando','Valor observado','Resultado','Justificativa'])`, igualdade **exata e ordenada** sobre `SuperficieEventoDecisao.tsx:339-342`. **M6, M8 e F5 mortos** | ✅ **PASS** (era ⚠️ Partial; célula e cabeçalho guardados como sinais independentes) |
| **ELEG-10** — nenhum registro satisfaz a regra → conjunto vazio **válido**, não falha técnica, **sem chamada à OpenAI e sem criar mensagem** | `200`/contagem zero/lista vazia; zero chamadas de IA; nenhuma mensagem | Serviço: `test_avaliacao_elegibilidade.py:143-145` — `incluidos == 0`, `excluidos == 0`, **`elegibilidades.chamadas == []`** (prova de **ausência** de escrita). HTTP: `test_elegibilidade_api.py:131-135` — `200`, contagens zero, `registros == []`. Repositório: `test_repositorio_elegibilidade.py:267`. Frontend: `SuperficieEventoDecisao.test.tsx:269-270` — texto de vazio **e** `queryByRole('alert')` ausente. Sem IA: garantia **estrutural** — `PortasAvaliacaoElegibilidade` não expõe porta de IA e `grep -rn "openai"` nos módulos da história devolve zero | ✅ **PASS** (nota A) |

**Status**: ✅ **Sem gaps** — **10/10 ACs** casam com o resultado definido pela spec (Round 1: 4/10; Round 2: 7/10). **Zero spec-precision gaps**: a `spec.md` 2.5 define resultado preciso para as 10 ACs.

Contagem final: **10 PASS**, 0 Partial, 0 GAP. Movimento em relação à Round 2: ELEG-06 subiu de GAP para PASS, ELEG-08 e ELEG-09 subiram de Partial para PASS; **nenhuma AC regrediu** (verificado por spot-check dos `file:line` citados — ver abaixo).

### Spot-check de não regressão (Round 3)

Os `file:line` da Round 2 foram reconferidos por amostragem na árvore real, escolhendo os itens mais sensíveis a regressão silenciosa:

| Item | Verificação | Resultado |
| --- | --- | --- |
| **Correção do blocker da R1 — backfill da migração `0007`** | `0007:45` continua `CASE WHEN e.execucao_id IS NULL THEN '[]' ELSE e.criterios END`; `0007:47,51` continuam `s.nome` + `JOIN segurados` | ✅ Intacto |
| **Correção do blocker da R1 — teste HTTP de linha semeada** | `test_elegibilidade_api.py:248-267` — `SemeadorDadosSinteticos(caminho).semear()` (`:255`), `SELECT id … WHERE execucao_id IS NULL` (`:257-259`), `status_code == 404` (`:266`) **e** `codigo == "resultado_elegibilidade_inexistente"` (`:267`) | ✅ Intacto — e **remorto por mutação** nesta rodada (S7) |
| **ELEG-05 — "cada critério" numa exclusão** | `grep -c "len(resultado.criterios) == 5" test_avaliador_elegibilidade.py` → **7** ocorrências (6 de exclusão + 1 de inclusão) | ✅ Intacto |
| **ELEG-07 — duas apólices do mesmo segurado** | `test_repositorio_elegibilidade.py:375-412` presente e inalterado no diff da rodada | ✅ Intacto |
| **Test Integrity do diff `c7c202e..49bf647`** | `git diff … \| grep -E "^\-.*def test_\|^\-.*it\("` → **nenhuma linha** | ✅ Nenhum teste removido |

### Notas de julgamento

**Nota A — ELEG-10.** Herdada das rodadas anteriores: o caso literal "candidatos **existem** e nenhum satisfaz" segue sem teste de serviço (o teste de vazio usa **zero** candidatos). Minor, não bloqueante — o caminho de código exercitado é o mesmo (`incluidos == 0` + `chamadas == []`).

**Nota B — 404 por execução divergente.** `test_elegibilidade_api.py:284` continua asserindo só o status. Mitigada: o teste irmão `:248-267` exercita o **mesmo** ramo do roteador (`http/elegibilidade.py:237`) asserindo o `codigo`. M5 morre em **dois** testes.

**Nota C — `role="status"` perdido.** `SuperficieEventoDecisao.test.tsx:127` segue com `getByText('Carregando decisão de risco…')` no lugar de `getByRole('status')` (contorno da ambiguidade dos dois indicadores). Minor, inalterada.

**Nota D — INNER JOIN na migração `0007`.** `0007:44-51` copia via `JOIN segurados`; as FKs de `elegibilidades_historicas` são **lógicas**, então uma linha órfã seria descartada em silêncio. Não alcançável com o conjunto semeado atual. Minor, inalterada.

**Nota E — semeador vs. migração.** `semeador.py` repete literalmente o nome do segurado em `nome_segurado`, duplicando `segurados.nome`, sem teste de coerência entre as duas colunas do próprio seed. Minor, inalterada.

**Nota F — resíduo de evidência em `_codigo_ibge_area_de` (era o F1 da Round 2).** O **acoplamento posicional foi eliminado** e isso está comprovado empiricamente (experiência **E1** no sensor). O que permanece é menor e de natureza diferente: **nenhuma fixture persistida tem mais de um critério**, então uma reescrita errada da função (`criterios[-1]` no lugar da busca por nome) ainda passa nos 378 testes. Não é mais um acoplamento entre camadas — é a ausência de um teste de round-trip com um snapshot **real de 5 critérios**, que a fix task da R2 pedia como item secundário ("em qualquer caso"). Classificada **Minor** e **não bloqueante** porque: (i) a classe de defeito nomeada pelo F1 está fechada por construção e verificada; (ii) produtor e consumidor compartilham **o mesmo símbolo** (`OPERANDO_AREA_AFETADA`), de modo que não existe mais um valor que possa divergir entre os dois módulos; (iii) o valor derivado já é asserido contra o banco em `test_repositorio_elegibilidade.py:173` e `:370` — apenas com um único critério. O fechamento custa ~5 linhas e está listado nos itens Minor.

---

## Discrimination Sensor

Worktree isolada e descartável (`git worktree add --detach <scratch> 49bf647`), revertida com `git checkout -- .` entre mutações e removida com `git worktree remove --force` + `git worktree prune`. O `node_modules` do frontend foi apenas **symlinkado** para dentro da worktree e o link removido antes da remoção — nada foi escrito na árvore real. Nenhum `git stash` usado. **Baseline na worktree antes de mutar**: 378 testes backend verdes; 15/15 em `SuperficieEventoDecisao.test.tsx`.

### Mutantes sobreviventes da Round 2, reinjetados

| # | Mutação | File:line | Descrição | Testes executados | Killed? |
| --- | --- | --- | --- | --- | --- |
| **S1 (M4c)** | **Canal lido ao vivo em vez de congelado** | `repositorio_elegibilidade.py:190,193` | `e.canal` → `s.canal_preferido` + `JOIN segurados AS s ON s.id = e.segurado_id` | `testes/` (378) | ✅ **Killed** (era Survived) — `test_nome_segurado_e_area_persistidos_sobrevivem_a_mudanca_dos_dados_originais` falha em `:371` com `AssertionError: assert 'sms' == 'whatsapp'`. **1 failed \| 377 passed.** É o **Success Criterion #3 literal** da spec |
| **S2 (F1, forma pedida)** | **Derivação de área revertida para posicional** | `repositorio_elegibilidade.py:210-213` | `next((c for c in criterios if c.operando == OPERANDO_AREA_AFETADA), None)` → `criterios[0].valor_observado if criterios else ""` | `testes/` (378) | ⚠️ **Survived — mutante equivalente** (378 passed). Com a ordem atual de `avaliar`, `criterios[0]` **é** o critério de área: a mutação é indistinguível da original **em todo o espaço de entradas alcançável**, logo nenhum teste pode matá-la sem construir um estado inalcançável. Ver **E1**, que mede a diferença que a mutação de fato introduz |
| **S3 (F1, forma literal da R2)** | **Derivação de área trocada de posição** | `repositorio_elegibilidade.py:210-213` | busca por nome → `criterios[-1].valor_observado if criterios else ""` | `testes/` (378) | ❌ **Survived** (378 passed) — não equivalente, mas **não alcançável por reordenação**: exige uma reescrita errada da própria função. Resíduo de evidência da **Nota F**, classificado Minor |
| **S4 (F4)** | **Contadores trocados na interface** | `SuperficieEventoDecisao.tsx:270-272` | `{elegibilidade.incluidos}` ↔ `{elegibilidade.excluidos}` nos três pontos (valor, pluralização, valor) | `SuperficieEventoDecisao.test.tsx` (15) | ✅ **Killed** (era Survived) — **1 failed \| 14 passed**; `AssertionError: expected '1 incluído — 2 excluídos' to contain '2 incluídos — 1 excluído'` |
| **S5 (F5)** | **Cabeçalhos da explicação removidos** | `SuperficieEventoDecisao.tsx:340-341` | remoção de `<th scope="col">Valor observado</th>` e `<th scope="col">Resultado</th>` (as `<td>` permanecem, a tabela desalinha) | `SuperficieEventoDecisao.test.tsx` (15) | ✅ **Killed** (era Survived) — **1 failed \| 14 passed**; `expected [ 'Operando', 'Justificativa' ] to deeply equal [ 'Operando', 'Valor observado', …(2) ]` |

### Mutantes de confirmação (previamente mortos, remortos nesta rodada)

| # | Mutação | File:line | Descrição | Testes executados | Killed? |
| --- | --- | --- | --- | --- | --- |
| **S6 (M4b)** | **`codigo_ibge_area` lido ao vivo** — verifica que a troca da derivação posicional pela busca por nome **não afrouxou** a guarda de imutabilidade | `repositorio_elegibilidade.py:190,193,229` | `JOIN apolices AS a` + coluna extra `a.codigo_ibge_area` e `codigo_ibge_area=str(linha[13])` no lugar de `_codigo_ibge_area_de(criterios)` | `testes/` (378) | ✅ **Killed** — **2 failed \| 376 passed**: `test_nome_segurado_e_area_persistidos_sobrevivem_a_mudanca_dos_dados_originais` **e** `test_obter_por_id_de_linha_semeada_com_criterios_vazio_nao_lanca` |
| **S7 (F6)** | **Regressão do blocker no semeador** — verifica que o teste de regressão do Fix 1 continua reproduzindo o defeito **original** da Round 1 | `adaptadores/persistencia/semeador.py` | `"[]"` → `'{"origem": "seed_demonstrativo"}'` (4 ocorrências) | `testes/` (378) | ✅ **Killed** — **1 failed \| 377 passed**: `test_get_registro_elegibilidade_semeado_retorna_404_nao_500` levanta `TypeError: string indices must be integers, not 'str'` em `serializacao_criterios.py:33` |

### Experiência E1 — a suposição de ordenação foi mesmo removida?

O Fix 10 é uma mudança de **produção**, e a alegação a verificar não é "algum teste ficou vermelho", e sim "o defeito deixou de ser possível". Isso não se mede por mutante — mede-se por **contrafactual**. Na worktree, um script ad-hoc (fora do repositório) constrói um `ResultadoElegibilidade` pelo **avaliador real** (5 critérios), persiste via `RepositorioElegibilidades.salvar` e relê por `obter_por_id`:

| Caso | Ordem dos critérios em `avaliar` | Implementação de `_codigo_ibge_area_de` | `codigo_ibge_area` relido |
| --- | --- | --- | --- |
| **A** | atual (área primeiro) | busca por nome (código atual) | `'9990001'` ✅ correto |
| **B** | **área por último** | `criterios[0]` (código antigo, posicional) | `'residencial'` ❌ **incorreto** — o `valor_observado` do critério de *tipo da apólice* apareceria como Localização |
| **C** | **área por último** | busca por nome (código atual) | `'9990001'` ✅ correto |

**Conclusão**: B vs. C isola exatamente a variável. O acoplamento posicional entre `dominio/avaliador_elegibilidade.py` e `adaptadores/persistencia/repositorio_elegibilidade.py` — apontado pela Nota F da Round 2 como "promessa não executável em docstring" — **deixou de existir**: a ordem dos critérios agora é, de fato, um detalhe de implementação de `avaliar`. Nenhum arquivo do repositório foi tocado por esta experiência.

**Sensor depth**: **P0-full** (integridade de dados — 7 mutações + 1 experiência contrafactual nesta rodada; ≥5 exigidas pelo protocolo)

**Result**: **5/7 killed** — ✅ **PASS**. Os 3 mutantes que a Round 2 apontou como fecháveis por asserção (**M4c, F4, F5**) estão **mortos**. Os 2 sobreviventes são a mesma função (`_codigo_ibge_area_de`) em duas formas: **S2 é um mutante equivalente** (indistinguível por qualquer teste, dado o espaço de entradas alcançável) e **S3 é o resíduo Minor da Nota F**, cuja classe de defeito original foi eliminada por construção e comprovada por **E1** — e desde então também fechado por teste (ver Fix Tasks em `tasks.md`, "Round 3 (final)"). Acumulado da história: **22/35 mutantes mortos** ao longo das três rodadas; **nenhum sobrevivente corresponde a um defeito de produção alcançável**.

**Verificação de isolamento**: `git status --porcelain` vazio **antes** (`BASELINE:[]`) e **depois** (`POST-SENSOR STATUS:[]`) do ciclo de mutações; `git worktree list` mostra apenas a árvore real em `49bf647`; o diretório de scratch não existe mais; `src/frontend/node_modules` da árvore real segue diretório real (não symlink). Nenhum arquivo do projeto foi modificado por esta rodada exceto este `validation.md`.

---

## Payload / Conjunction Rule

Regra aplicada: a asserção precisa olhar **valor devolvido e/ou estado persistido**, não "a chamada aconteceu" nem um status isolado.

| Alvo | Asserção verifica valor real? | Evidência |
| --- | --- | --- |
| `GET .../elegibilidade` 200 vazio | ✅ Sim | `test_elegibilidade_api.py:131-135` — status **+** `incluidos == 0`, `excluidos == 0`, `registros == []` |
| `GET .../elegibilidade` 200 preenchido | ✅ Sim | `:190-193` — status **+** `incluidos == 2` **≠** `excluidos == 1` **+** `len == 3` **+** conjunto de 3 nomes **+** conjunto de 3 canais |
| `GET .../elegibilidade` 422 | ✅ Sim | `:206-208` — status + `content-type: application/problem+json` + `codigo == "execucao_id_invalido"` |
| `GET .../elegibilidade/{id}` 200 | ✅ Sim | `:226-235` — status **+** `id`, `regra_id`, `regra_versao == 3`, `elegivel is True`, `len(criterios) == 1`, `operando`, `atende is True`, `justificativa.startswith(...)` |
| `GET .../elegibilidade/{id}` 404 **de linha semeada real** | ✅ Sim | `:266-267` — status **+** `codigo`, com o conjunto demonstrativo **realmente semeado**; regressão do blocker comprovada por **S7** |
| `GET .../elegibilidade/{id}` 404 de outra execução | ⚠️ Parcial | `:284` — só o status (nota B); mitigado pelo teste irmão, que exercita o mesmo ramo com `codigo` |
| `GET .../elegibilidade/{id}` 422 | ✅ Sim | `:294-295` — status + `codigo == "identificador_invalido"` |
| `RepositorioElegibilidades.salvar` | ✅ Sim | `test_repositorio_elegibilidade.py:165-174` — id devolvido **e** releitura real do banco com 7 asserções de valor |
| `RepositorioElegibilidades.salvar` (dedup) | ✅ Sim | `:207-209` — `primeiro is not None` **e** `segundo is None` **e** estado persistido relido |
| `RepositorioElegibilidades.salvar` (duas apólices) | ✅ Sim | `:409-412` — `len(registros) == 2` **e** `{apolice_id}` **de identidade**, não só contagem |
| **Snapshot imutável (nome, área e canal)** | ✅ **Sim (fechado nesta rodada)** | `:356-372` — **três** `UPDATE` reais nas tabelas fonte (`nome`, `canal_preferido`, `codigo_ibge_area`) **e** releitura por `obter_por_id` asserindo os três valores originais. **M4a, M4b e M4c mortos** |
| `contar_por_execucao` | ⚠️ Parcial | `test_repositorio_elegibilidade.py:260-261` — valores reais, mas ainda simétricos (`1`/`1`); a assimetria vive no teste HTTP e agora também no teste de componente |
| `listar_candidatos` (área da apólice) | ✅ Sim | `:427-429` — `len == 1` **+** `apolice_id` **+** `codigo_ibge_area == AREA`, com a área do segurado **diferente** |
| Migração `0007` (backfill) | ✅ Sim | `test_migracoes.py:246-255` — os 5 valores da linha semeada relidos do banco |
| Migração `0007` (`UNIQUE`) | ✅ Sim | `:296` e `:321` — contagens reais após inserções concorrentes |
| `ServicoAvaliacaoElegibilidade` — efeito | ✅ Sim | `test_avaliacao_elegibilidade.py:169-177` — a **tupla inteira** passada a `salvar`; `:145` — `chamadas == []` prova **ausência** de escrita |
| Cliente HTTP frontend | ✅ Sim | `elegibilidade.test.ts:52,74,137-139,90,99,166` |
| Superfície — tabela | ✅ Sim | `SuperficieEventoDecisao.test.tsx:280-285` — 6 valores de célula reais |
| Superfície — distinção | ✅ Sim | `:298-303` — classe modificadora **de cada estado** **e** ícone **de cada estado** **e** o texto |
| Superfície — explicação (5 campos) | ✅ Sim | `:325,334-341` — `regra v3` **+** operando **+** valor observado **+** `Atende` **+** justificativa completa **+** os dois argumentos da chamada |
| **Superfície — quantidades** | ✅ **Sim (fechado nesta rodada)** | `:253,258-261` — fixture assimétrica `2`/`1` **+** o texto completo do parágrafo (`'2 incluídos — 1 excluído'`), que liga número, rótulo e pluralização. **F4 morto** |
| **Superfície — colunas da explicação** | ✅ **Sim (fechado nesta rodada)** | `:326-333` — `getAllByRole('columnheader')` com `toEqual([...])` **exato e ordenado**, na tabela de critérios. **F5 morto** |

---

## Code Quality

| Princípio | Status |
| --- | --- |
| Minimum code | ✅ — a correção acrescenta **uma constante** e troca um índice por uma busca; o resto é asserção |
| Surgical changes | ✅ — 6 arquivos em `c7c202e..49bf647`, todos rastreáveis a um Fix nomeado; nenhuma rota, nenhuma migração, `openapi.json` inalterado |
| No scope creep | ✅ — nenhuma transição de estado, nenhuma geração de mensagem, nenhuma rota extra (`test_saude.py:46-47` fixa o conjunto exato de caminhos) |
| Matches patterns | ✅ — `OPERANDO_AREA_AFETADA` segue a convenção dos `MOTIVO_*` do mesmo módulo (`:9-14`); a asserção de cabeçalhos reusa literalmente o padrão de `SuperficieRegras.test.tsx:118-130` |
| Spec-anchored outcome check | ✅ — **10/10** ACs com asserção casando o resultado da spec |
| Per-layer Coverage Expectation | ✅ — domínio 1:1; rota cobre feliz + vazio + 404 (×3 causas, incluindo linha semeada real) + 422 (×2); componente cobre carregando/vazio/erro/tabela/quantidades/teclado/explicação/colunas |
| Every test maps to a spec requirement | ✅ — nenhum teste órfão; as edições desta rodada fortalecem testes que já existiam |
| Documented guidelines followed | ✅ — o `README.md` de persistência promete que `canal` "nunca [é] referência viva a `segurados.canal_preferido`" (`:155`); a promessa agora é **executável** (S1 morre) |
| Docstring/contrato correspondem ao comportamento | ✅ — o docstring de `_codigo_ibge_area_de` (`:198-208`) deixou de afirmar um acoplamento posicional e passou a descrever a busca por nome, que é o que o código faz; o docstring da constante (`:17-19`) explicita por que ela é compartilhada |

---

## Edge Cases

- [x] **Segurado com mais de uma apólice na área afetada, uma elegível e outra não → um resultado distinto por combinação** — listagem `test_repositorio_elegibilidade.py:142-144`; persistência `:375-412` (duas linhas e as duas identidades de apólice). **M3 morto**
- [x] **Área do evento cobre parcialmente a área de risco da apólice → mesmo critério objetivo, sem inferência probabilística** — igualdade exata de código IBGE (`avaliador_elegibilidade.py:49`); `test_avaliador_elegibilidade.py:70-78`; determinismo asserido em `:157-161`
- [x] **Retomada após reinicialização do backend no meio do processamento → continua do progresso persistido, sem recriar resultados já gravados** — `test_repositorio_elegibilidade.py:207-209` e `test_avaliacao_elegibilidade.py:186-190`; M10 confirma que a garantia é da `UNIQUE` do banco
- [x] **Conjunto vazio válido** — `test_avaliacao_elegibilidade.py:143-145`, `test_elegibilidade_api.py:131-135`, `SuperficieEventoDecisao.test.tsx:269-270` (nota A)
- [x] **Linha semeada consultada pelo detalhe HTTP** — defeito de produção da Round 1 corrigido e guardado: `test_elegibilidade_api.py:248-267` + `test_repositorio_elegibilidade.py:300-327`; regressão recomprovada por **S7**
- [x] **Canal preferencial alterado depois da execução concluída** (Success Criterion #3) — **fechado nesta rodada**: `test_repositorio_elegibilidade.py:356-372`; **S1 morto**

---

## Gate Check

- **Gate command (Build)**: `uv run pytest -q && uv run ruff check . && uv run pyright` (em `src/backend`) + `npx vitest run && npm run lint && npm run build` (em `src/frontend`)
- **Executado nesta rodada pelo próprio Verificador** (não herdado do orquestrador), na árvore real em `49bf647`:
  - `pytest`: **378 passed**, 0 failed, 0 skipped (exit 0, 21.05s)
  - `ruff check .`: **All checks passed!** (exit 0)
  - `pyright`: **0 errors, 0 warnings, 0 informations** (exit 0)
  - `vitest run`: **202 passed** em 23 arquivos, 0 failed (exit 0, 7.30s)
  - `npm run lint` (`oxlint`): exit 0 — **11 warnings**, todas pré-existentes de `react(set-state-in-effect)` / `react(only-export-components)`; nenhuma nova
  - `npm run build`: **✓ built in 230ms** (exit 0)
- **Test count antes da feature** (fim de 2.4, `621d4ab`): 340 backend / 189 frontend
- **Test count na Round 1** (`36aafd6`): 373 backend / 202 frontend
- **Test count na Round 2** (`c7c202e`): 378 backend / 202 frontend
- **Test count na Round 3** (`49bf647`): **378 backend / 202 frontend**
- **Delta da rodada de correção**: **+0 / +0** — coerente e esperado: os quatro Fixes **fortalecem testes que já existiam** (Fix 9 e 11 dentro de um teste cada; Fix 12 dentro do teste de teclado; Fix 10 é produção). Contagem idêntica **não** significa ausência de trabalho: o poder discriminante subiu, medido por 3 mutantes que sobreviviam na Round 2 e agora morrem
- **Delta total da história**: **+38 backend / +13 frontend**
- **Test Integrity**: ✅ nenhum teste removido no diff `c7c202e..49bf647` (`grep -E "^\-.*def test_|^\-.*it\("` → vazio); **nenhuma asserção enfraquecida**. As duas substituições merecem registro explícito: (1) em `SuperficieEventoDecisao.test.tsx:258-261`, `getAllByText('1')).toHaveLength(2)` + dois `getByText(/incluído|excluído/)` foram trocados por **uma** asserção sobre o texto completo do parágrafo — **estritamente mais forte** (a antiga sobrevivia à troca dos contadores, a nova não, como S4 prova); (2) em `test_repositorio_elegibilidade.py:356-360`, o `UPDATE` de `nome` ganhou `canal_preferido` na mesma sentença e **duas** asserções novas. Todo o resto é adição
- **Skipped**: nenhum
- **Failures**: nenhuma

---

## Fix Plans

**Nenhum fix bloqueante.** Itens Minor abertos, todos opcionais e não bloqueantes:

- **Nota A** — ELEG-10: teste de serviço com candidatos que **existem** e nenhum satisfaz (`incluidos == 0`, `excluidos == N`).
- **Nota B** — acrescentar `codigo == "resultado_elegibilidade_inexistente"` a `test_elegibilidade_api.py:284` (o teste irmão já cobre o ramo).
- **Nota C** — recuperar a asserção de `role="status"` em `SuperficieEventoDecisao.test.tsx:127` com `getAllByRole('status')` + `toHaveTextContent`.
- **Nota D** — trocar o `JOIN segurados` de `0007:51` por `LEFT JOIN` + `COALESCE(s.nome, '')`, para que a migração nunca descarte linha órfã em silêncio.
- **Nota E** — asserir, num teste do semeador, que `elegibilidades_historicas.nome_segurado` casa com `segurados.nome` para a mesma linha semeada.
- **Nota F** — fechar o resíduo de `_codigo_ibge_area_de` com ~5 linhas: salvar um `ResultadoElegibilidade` cujos `criterios` tenham o operando `"área afetada"` **fora da primeira posição** (a fixture é construída à mão, como `RESULTADO_INCLUIDO` em `test_repositorio_elegibilidade.py:86-99`) e asserir, na releitura, `registro.codigo_ibge_area == AREA`. Isso mata **S2** e **S3** de uma vez. Alternativa equivalente: persistir a saída do avaliador real (5 critérios), como a fix task da R2 sugeria.
- **Nota G (nova)** — `test_repositorio_elegibilidade.py:260-261` ainda usa contagens simétricas `1`/`1` em `contar_por_execucao`; a assimetria vive apenas nas camadas HTTP e de componente.
- **Integração** — montar `SuperficieEventoDecisao` em rota no `App.tsx` (lacuna declarada, compartilhada com 2.1/2.2/2.3/2.4; deve virar item próprio, não pendência desta história).

---

## Lições candidatas (grounding para `.specs/lessons.json`)

| Origem fundamentada | Lição proposta |
| --- | --- |
| Fix 9 e Fix 11 fecharam itens que a R1 já havia pedido e a R2 encontrou pela metade | **Reforça a lição da 2.4**: uma fix task que enumera N asserções precisa ser reverificada **item a item contra o texto original da task**. Confirmado nas duas direções — quando o verificador cita o item perdido **nominalmente** ("o `UPDATE … canal_preferido` e o `assert registro.canal`"), a rodada seguinte o entrega; quando o resume ("congelar os campos"), ele some |
| Fix 10 mudou produção; o mutante literal da R2 (`criterios[0]`) virou **equivalente** | **Quando a correção elimina a classe de defeito por construção, o mutante da rodada anterior deixa de ser o instrumento certo de medição.** Reinjetá-lo produz um mutante equivalente e um falso "Survived". O instrumento correto é o **contrafactual**: variar a condição que o defeito exigia (aqui, a ordem dos critérios) e comparar o comportamento das duas implementações. E1 mostra `'residencial'` vs. `'9990001'` — evidência que nenhuma contagem de mutantes teria produzido |
| `OPERANDO_AREA_AFETADA` compartilhada entre `dominio` e `adaptadores` | **Um acoplamento implícito entre camadas ("o critério X é sempre o primeiro") fecha-se melhor com um símbolo compartilhado do que com um teste.** O teste guarda uma instância do defeito; a constante remove a possibilidade de divergência entre produtor e consumidor. O teste continua valendo como rede secundária — mas a ordem de preferência é: eliminar > guardar |
| Substituição de `getAllByText('1')).toHaveLength(2)` por `toContain('2 incluídos — 1 excluído')` | **Contar ocorrências de um literal não é asserir um valor.** Uma asserção por contagem de dígito é indistinguível da troca dos valores que ela deveria proteger; ancorar no **texto do parágrafo** liga número, rótulo e pluralização num único sinal, e o custo é o mesmo |
| Fix 12; **L-024 reincide pela quinta superfície e agora fecha** | **Reforçar L-024**: quando a AC enumera N colunas da interface, asserir **célula e cabeçalho separadamente** — são sinais independentes. `expect(getAllByRole('columnheader').map(c => c.textContent)).toEqual([...])` é o padrão barato, e o `getByRole('table')` intermediário é necessário quando há mais de uma tabela na mesma `region` |
| Rodada com **+0 testes** e 3 mutantes a menos | **Delta de contagem de testes não mede progresso de verificação.** Esta rodada não criou nenhum teste e ainda assim fechou três ACs; o indicador que se moveu foi o de mutantes mortos. Contagem de testes deve ser reportada como controle de integridade (nada foi removido), nunca como métrica de cobertura |

---

## Requirement Traceability Update

| Requirement | Previous Status (Round 2) | New Status (Round 3, final) |
| --- | --- | --- |
| ELEG-01 | ✅ Verified | ✅ Verified |
| ELEG-02 | ✅ Verified | ✅ Verified |
| ELEG-03 | ✅ Verified | ✅ Verified |
| ELEG-04 | ✅ Verified | ✅ Verified |
| ELEG-05 | ✅ Verified | ✅ Verified |
| ELEG-06 | ❌ Needs Fix (Fix 9, Fix 10) | ✅ **Verified** — nome, área **e canal** congelados, com M4a/M4b/M4c mortos; acoplamento posicional eliminado e comprovado por E1 (nota F, Minor) |
| ELEG-07 | ✅ Verified | ✅ Verified |
| ELEG-08 | ⚠️ Parcial — Needs Fix (Fix 11) | ✅ **Verified** — quantidades distinguíveis **na interface** (F4 morto) |
| ELEG-09 | ⚠️ Parcial — Needs Fix (Fix 12) | ✅ **Verified** — colunas estáveis asseridas por conjunto exato (F5 morto) |
| ELEG-10 | ✅ Verified (nota A) | ✅ Verified (nota A) |

**10/10 Verified.**

---

## Summary

**Overall**: ✅ **PASS** — história 2.5 verificada; nenhum item bloqueante aberto

**Spec-anchored check**: **10/10 ACs** com asserção casando o resultado definido pela spec (R1: 4/10; R2: 7/10). **Zero spec-precision gaps**
**Sensor**: **5/7 mutantes mortos** nesta rodada — os **3 itens acionáveis da Round 2 (M4c, F4, F5) estão mortos**; os 2 sobreviventes são a mesma função, um deles **provadamente equivalente**, e a classe de defeito que ambos representavam foi eliminada por construção e comprovada pela experiência contrafactual **E1**. Acumulado da história: **22/35**
**Gate**: 378 backend + 202 frontend passed, 0 failed, 0 skipped; `ruff`/`pyright`/`lint`/`build` verdes — todos re-executados pelo Verificador na árvore real

**O que funciona**: os três Fixes de asserção fecharam **exatamente** o que a Round 2 pediu, e isso foi medido, não aceito — reintroduzir a leitura viva de `segurados.canal_preferido` agora falha em `assert 'sms' == 'whatsapp'` (o **Success Criterion #3 literal** da spec, que sobreviveu a duas rodadas e finalmente tem guarda), trocar os contadores na tela falha com `expected '1 incluído — 2 excluídos' to contain '2 incluídos — 1 excluído'`, e apagar dois `<th>` da tabela de critérios falha na igualdade exata do conjunto de cabeçalhos. As duas substituições de asserção foram conferidas uma a uma e são **estritamente mais fortes** que as anteriores, não reescritas laterais. O Fix 10, único com mudança de produção, é o mais interessante: em vez de acrescentar um teste que guarda uma instância do defeito, ele **remove a possibilidade** — produtor e consumidor passam a compartilhar o símbolo `OPERANDO_AREA_AFETADA`, e a experiência E1 confirma o contrafactual (com os critérios reordenados, o código antigo exibiria `'residencial'` na coluna Localização; o novo continua exibindo `'9990001'`). A correção do blocker da Round 1 foi reconferida e **remorta por mutação** (reverter o semeador reproduz o `TypeError` original), assim como a guarda de imutabilidade da área.

**Problemas encontrados**: nenhum bloqueante. Um resíduo novo, Minor e bem localizado (**nota F**): a fix task da Round 2 pedia, além da troca por busca nominal, um teste de round-trip com um snapshot de **5 critérios**; esse teste não foi escrito, então uma reescrita errada de `_codigo_ibge_area_de` (`criterios[-1]`) ainda passa nos 378 testes. Não é o mesmo defeito de antes — o acoplamento **entre camadas** acabou, e nenhum reordenamento futuro do avaliador pode reintroduzi-lo — mas a correção da função em si segue apoiada em fixtures de um único critério. Custo de fechamento: ~5 linhas, listadas na nota F. Persistem também seis itens Minor já registrados e aceitos (notas A–E, G) e a lacuna de integração — `SuperficieEventoDecisao` não montada em rota no `App.tsx` — **declarada pelo autor** e compartilhada com as quatro superfícies anteriores.

**Next steps**: encerrar a história 2.5 como **Verified** (10/10 ELEG-NN) e atualizar o `Status` da tabela de rastreabilidade na `spec.md` de `Pending` para `Verified`. Promover à camada de lições o achado metodológico desta rodada — **quando a correção elimina a classe de defeito por construção, reinjetar o mutante antigo produz um equivalente e um falso "Survived"; o instrumento certo passa a ser o contrafactual** — e reforçar L-024 com o `getByRole('table')` intermediário para superfícies com mais de uma tabela por `region`. Os itens das notas A–G são opcionais e podem ser agrupados numa varredura de qualidade posterior; a lacuna de integração das superfícies deve virar item próprio antes da demonstração. Esta foi a **iteração 3 de no máximo 3** e a história fecha dentro do orçamento.
