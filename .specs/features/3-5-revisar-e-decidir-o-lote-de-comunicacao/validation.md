# História 3.5: Revisar e decidir o lote de comunicação — Validation (rodada 2)

**Date**: 2026-09-04
**Spec**: `.specs/features/3-5-revisar-e-decidir-o-lote-de-comunicacao/spec.md`
**Diff range**: `7bca11d..0e6d557` (8 commits — T1–T6 em `634c8e9..50c8602`, doc da rodada 1 em `e99f4b4`, correção da rodada 2 em `0e6d557`)
**Verifier**: sub-agente independente e novo (author ≠ verifier; verificador ≠ verificador da rodada 1) — nenhuma afirmação da rodada 1 nem do commit de correção foi aceita sem reprodução própria
**Round**: 2 de no máximo 3 (rodada 1 = **FAIL**, com Gap 1 Major, Gap 2 Major e Gap 3 Minor)
**Result**: ✅ **PASS**

---

## Escopo desta rodada

A rodada 1 (`e99f4b4`) fez a derivação exaustiva dos 14 critérios REVISAO-*, dos 3 Edge Cases, das 7 mutações do sensor e das 5 alegações de maior carga. Esta rodada:

1. Re-lê o diff real de `0e6d557` e confirma que ele faz o que o commit diz;
2. Reproduz do zero o Gap 1 e prova que a correção o fecha — mais um ângulo que a rodada 1 não testou (lote com **zero** mensagens);
3. Re-injeta a mutação exata M4 e prova que o novo teste agora a mata, sem dano colateral;
4. Confere os 3 marcadores `SPEC_DEVIATION` contra o que o código realmente faz e contra o `design.md`;
5. Roda o gate Build completo (backend + frontend) na árvore real;
6. Re-deriva do zero o desfecho de spec de REVISAO-01, REVISAO-09 e REVISAO-14 — os critérios que a correção tocou. Os demais 11 são carregados da rodada 1, que os derivou exaustivamente e não achou lacuna.

Fora de escopo por decisão explícita: os vereditos já fechados da rodada 1 sobre as três alegações de maior carga (gatilho REVISAO-01 sem terceiro caminho, isolamento transacional entre conexões DuckDB, os dois modos de atomicidade) e sobre M2 (colisão de enums morta só pelo `pyright`, já registrada como L-045).

---

## Task Completion

| Task | Status | Notes |
| --- | --- | --- |
| T1 — Migração `0013_decisoes_humanas.sql` | ✅ Done | `634c8e9` |
| T2 — `RepositorioDecisoesHumanas` | ✅ Done | `0e8635b` |
| T3 — `ServicoRevisaoLote.obter_lote` | ✅ Done | `495b733` |
| T4 — `ServicoRevisaoLote.decidir_lote` | ✅ Done | `e900c6c` + `0e6d557` — a metade "aprovada pelo crítico" do REVISAO-14 passou a ter teste discriminante; M4 deixou de sobreviver |
| T5 — Roteador HTTP | ✅ Done | `fadc7c2` |
| T6 — Superfície do revisor e do lote | ✅ Done | `50c8602` |
| Fix 1–3 da rodada 1 | ✅ Done | `0e6d557` — as três correções em um commit, sem tocar em nenhum caminho de produção além da linha do Gap 1 |

---

## Verificação do commit de correção `0e6d557`

Lido integralmente (`git show 0e6d557`). 6 arquivos, +113/−9. Bate com o que o commit descreve, sem nada a mais:

| Arquivo | Mudança real observada | Gap |
| --- | --- | --- |
| `aplicacao/geracao_mensagens.py` | +1 linha de produção: `self.abrir_revisao_se_lote_completo(execucao_id)` no fim de `retomar_mensagens_pendentes` (`:477`), fora do laço, mantendo a chamada por item em `_retomar_item_isolado:488`; +6 linhas de docstring | 1 |
| `testes/test_geracao_mensagens.py` | +1 teste (`:1427`), nenhum teste alterado ou removido | 1 |
| `testes/test_revisao_lote.py` | +1 teste (`:1166`), nenhum teste alterado ou removido | 2 |
| `adaptadores/persistencia/repositorio_mensagens.py` | só docstring de módulo (`:13`) | 3 |
| `adaptadores/persistencia/repositorio_execucao_preventiva.py` | só docstring de `transicionar` (`:190`) | 3 |
| `adaptadores/persistencia/transacao.py` | só docstring de módulo (`:3`) | 3 |

**Zero mudança de comportamento fora da única linha do Gap 1.** Nenhuma linha `-def test_` / `-it(` no diff — nenhum teste apagado nem enfraquecido.

---

## Gap 1 — Execução presa em `processando_mensagens` após reinício

### Reprodução independente da falha original

Em worktree de rascunho (`git worktree add`, nunca `git stash`), removi a linha `:477` — voltando o código exatamente ao estado da rodada 1 — e rodei o novo teste:

```text
FAILED testes/test_geracao_mensagens.py::test_retomada_no_boot_com_todas_as_mensagens_ja_terminais_ainda_abre_a_revisao
AssertionError: assert <EstadoExecucao.PROCESSANDO_MENSAGENS: 'processando_mensagens'>
              is <EstadoExecucao.AGUARDANDO_REVISAO: 'aguardando_revisao'>
testes/test_geracao_mensagens.py:1466
```

É literalmente o sintoma que a rodada 1 observou na sua sonda descartável (`ESTADO APOS BOOT: processando_mensagens`). Portanto: (a) o bug era real; (b) o novo teste **discrimina** a correção — não é um teste que passaria de qualquer jeito.

### Confirmação de que a correção fecha o gap

Com a linha `:477` no lugar, o mesmo teste passa na árvore real. O caminho é o do boot de produção (`gerenciador_execucoes.py:397` → `retomar_mensagens_pendentes`), com repositórios reais sobre banco migrado; o cenário é semeado **direto pelos repositórios** (`criar` → `salvar_versao` → `transicionar CRITICANDO` → `avaliacoes.salvar` → `transicionar AGUARDANDO_REVISAO`), sem passar por `gerar_lote`, então o gatilho comprovadamente nunca dispara durante a semeadura — o teste prova a transição feita pela retomada, e só por ela. `assert reiniciado.redator.canais_chamados == []` fecha o outro lado: a retomada não regerou nada.

### Ângulo adicional desta rodada — lote com zero mensagens

A guarda de `abrir_revisao_se_lote_completo` (`geracao_mensagens.py:512-521`), lida linha a linha:

```python
registros = self._portas.mensagens.listar_por_execucao(execucao_id)
if not registros or any(em_ciclo_de_conteudo(item.estado) for item in registros):
    return
snapshot = self._portas.execucoes.buscar(execucao_id)
if snapshot is None or snapshot.estado is not EstadoExecucao.PROCESSANDO_MENSAGENS:
    return
```

O `not registros` é a primeira condição do primeiro `or`, então uma lista vazia sai **antes** de qualquer `any(...)` sobre coleção vazia — que retornaria `False` e deixaria a transição passar. A guarda está correta por construção, mas não bastava lê-la: rodei uma sonda descartável no worktree (execução em `processando_mensagens`, **nenhuma** mensagem criada, `retomar_mensagens_pendentes` chamado):

```text
assert cenario.mensagens.listar_por_execucao(EXECUCAO_ID) == []   # ok
asyncio.run(cenario.servico.retomar_mensagens_pendentes(EXECUCAO_ID))
assert cenario.estado_execucao() is EstadoExecucao.PROCESSANDO_MENSAGENS   # ok
assert cenario.excecoes.registradas == []                                   # ok
```

**Passou.** A chamada incondicional pós-laço **não** introduz falso-positivo de lote vazio: a execução sem mensagem alguma permanece em `processando_mensagens` e nenhuma exceção operacional é registrada. Sonda descartada com o worktree.

Também não há falso-positivo com regeneração humana ativa (REVISAO-10): a mensagem em `gerando`/`criticando` cai no `any(em_ciclo_de_conteudo(...))` e a guarda retorna. E a chamada é idempotente por construção: um agregado já fora de `processando_mensagens` sai pelo segundo `return`.

**Status: ✅ FECHADO.**

---

## Gap 2 — REVISAO-14 sem teste discriminante da metade "aprovada pelo crítico"

### Re-injeção da mutação M4 da rodada 1

Em worktree de rascunho, removi exatamente `and self._aprovada_pelo_critico(registro.id)` de `_mensagens_aprovadas` (`aplicacao/revisao_lote.py:645`) e rodei a **suíte backend inteira**:

```text
827 testes coletados → 826 passaram, 1 falhou
FAILED testes/test_revisao_lote.py::test_marina_aprova_mas_o_critico_nao_avaliou_a_versao_fica_de_fora
AssertionError: assert decisao.mensagens_aprovadas == (aprovada_pelos_dois,)
  Left contains one more item: UUID('29abf707-...')
testes/test_revisao_lote.py:1198
```

- **M4 agora é morto** — na rodada 1 ele sobrevivia à suíte inteira.
- **Exatamente 1 falha**: nenhum dano colateral, nenhum outro teste depende (mesmo acidentalmente) da segunda condição.
- A mutação é a mesma de M4, palavra por palavra, não uma variação mais fácil de matar.

### O cenário semeado é o inverso genuíno

`semear_mensagem(canal=Canal.SMS, tentativas=((True, None),), ...)` (`test_revisao_lote.py:325-369`): saída determinística **válida** (`valida=True`) e `aprovada=None`, que no helper significa "nenhuma avaliação crítica salva" (`if aprovada is not None:` pula o `avaliacoes.salvar`). É o complemento exato do caso que já existia (`:1155-1163`, aprovada pelo crítico e **rejeitada** por Marina): agora a suíte cobre os dois lados da conjunção. `_aprovada_pelo_critico` (`:648-655`) retorna `False` porque `obter_por_versao` devolve `None`, e a mesma linha cobre o caso `aprovada=False`.

A asserção final (`estados[sem_avaliacao_critica] is EstadoMensagem.APROVADA`) é o que dá precisão de spec ao teste: ela prova que a exclusão acontece no **conjunto agregado** — a decisão individual de Marina foi aceita, e é o lote que segue para `aguardando_confirmacao` que "contém apenas mensagens aprovadas pelo crítico e por Marina", exatamente como o REVISAO-14 escreve.

O implementador escolheu `((True, None),)` (crítico nunca avaliou) onde o plano da rodada 1 sugeria `((True, False),)` (crítico reprovou). Ambos passam pelo mesmo `return avaliacao is not None and avaliacao.avaliacao.aprovada`, e o kill de M4 prova a cláusula inteira; a escolha é equivalente ou melhor (exercita também o ramo `avaliacao is None`).

**Status: ✅ FECHADO.**

---

## Gap 3 — Desvios de `design.md` sem marcador `SPEC_DEVIATION`

Os três marcadores existem, seguem a convenção do projeto (25 ocorrências de `SPEC_DEVIATION` no backend, o mesmo formato de `geracao_mensagens.py:33`, `preflight_ia.py:8`, `grafos/geracao_mensagem.py:27`), e cada afirmação foi conferida contra o código e contra o `design.md`:

| Marcador | Afirma | Confere? |
| --- | --- | --- |
| `repositorio_mensagens.py:13` | `design.md` lista o repositório como reusado "sem alteração"; `obter`, `listar_por_execucao`, `transicionar` e `incrementar_tentativa` ganharam `conexao` opcional; chamadores de 2.2/3.2/3.4 inalterados | ✅ `design.md:44` diz literalmente "Reusado sem alteração"; os 4 métodos citados são exatamente os 4 que têm `conexao: duckdb.DuckDBPyConnection \| None = None` (`:245`, `:276`, `:318`, `:329`) e `listar_versoes`/`obter_versao_atual`/`criar`/`salvar_versao` não têm — a lista está correta, sem sobra nem falta |
| `repositorio_execucao_preventiva.py:190` | `design.md` lista o método como reusado; `transicionar` ganhou `conexao` opcional para participar da transação de `decidir_lote`; 2.2/2.6 inalterados | ✅ `design.md:45` lista `RepositorioExecucaoPreventiva` (`transicionar`) em "Existing Components to Leverage"; a assinatura tem `conexao` e o corpo usa `self._conexao(conexao)`. Nota de precisão: a linha 45 não escreve a expressão "sem alteração" (quem escreve é a 44, para o outro repositório) — a substância do desvio está certa, a citação é uma paráfrase |
| `transacao.py:3` | componente ausente da seção Components do `design.md`, que só descreve `RepositorioDecisoesHumanas` e `ServicoRevisaoLote`; necessário para tornar implementável "uma transação DuckDB por chamada de `decidir_lote`" | ✅ a seção **Components** (`design.md:58`) tem exatamente os dois `###` citados; `grep -c "Transacao\|transacao.py" design.md` → **0**; `design.md:124` contém literalmente "Uma transação DuckDB por chamada de `decidir_lote`" |

**Status: ✅ FECHADO.** A imprecisão de paráfrase da linha 190 é cosmética e não vira fix task (§ Observações).

---

## Spec-Anchored Acceptance Criteria — critérios re-derivados nesta rodada

### P1: Lote de revisão priorizado por atenção

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| REVISAO-01 — WHEN todas as mensagens de uma execução alcançarem um estado terminal de conteúdo THEN a execução SHALL entrar em `aguardando_revisao` e apresentar um lote com evento, regra, público, distribuição por canal, aprovações agênticas e exceções | `EstadoExecucao.AGUARDANDO_REVISAO` a partir de **qualquer** caminho que leve a última mensagem ao terminal, e cabeçalho com os 6 campos | Fechamento pela geração: `testes/test_geracao_mensagens.py:1364` — `assert cenario.estado_execucao() is EstadoExecucao.AGUARDANDO_REVISAO`. Fechamento pelo boot com a última mensagem terminando na retomada: `testes/test_geracao_mensagens.py:1424` (teste da 3.4). **Fechamento pelo boot com todas já terminais (novo)**: `testes/test_geracao_mensagens.py:1466` — `assert reiniciado.estado_execucao() is EstadoExecucao.AGUARDANDO_REVISAO` + `assert reiniciado.redator.canais_chamados == []`. Não-abertura com item ainda no ciclo: `testes/test_geracao_mensagens.py:1383`. Lote vazio não abre: sonda do Verificador (descartada). Cabeçalho: `testes/test_revisao_lote.py:480-487` — `lote.evento == EVENTO`, `lote.regra_id == REGRA_ID`, `lote.total_publico_incluido == 4`, `lote.distribuicao_por_canal == (("email",1),("sms",2),("whatsapp",1))`, `lote.aprovacoes_agenticas == 3`, `lote.itens_em_excecao == 1` | ✅ **PASS** (era ⚠️ na rodada 1) |

### P1: Regeneração humana compartilhando o limite de tentativas

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| REVISAO-09 — IF uma mensagem já tiver consumido três tentativas THEN regenerar SHALL permanecer indisponível com explicação acessível, enquanto aprovar (quando elegível), rejeitar e excluir SHALL continuar disponíveis | recusa com motivo próprio, sem efeito; as outras 3 ações seguem ativas | `testes/test_revisao_lote.py:884-891` — `recusadas == (DecisaoRecusada(esgotada, MOTIVO_LIMITE_DE_TENTATIVAS),)`, `aplicadas == (com_folga,)`, `decisoes.obter_por_mensagem(esgotada) == []`; `:916-918` — a mesma mensagem é rejeitada com sucesso; `:607-611` — `pode_regenerar is False` / `True`; `SuperficieRevisaoLote.test.tsx:365` — rádio `disabled` + explicação via `aria-describedby`, outros 3 `toBeEnabled()` | ✅ PASS — **re-confirmado**: a linha `:477` é a única mudança de produção da correção e não toca nenhum caminho de recusa por limite de tentativas; os 4 pontos de evidência seguem verdes na suíte da árvore real |
| REVISAO-10 (verificado por tabela, por ser o critério que a chamada incondicional poderia regredir) | agregado só volta a `aguardando_revisao` quando nenhuma regeneração permanece ativa | `testes/test_geracao_mensagens.py:1383` — item em `gerando` impede a abertura, inclusive vindo do novo caminho pós-laço; `testes/test_revisao_lote.py:1272-1275`, `:1216` | ✅ PASS — sem regressão |

### P1: Decisão em lote atômica e conclusão do agregado

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| REVISAO-14 — WHEN ao menos uma mensagem tiver sido aprovada e todas tiverem sido decididas THEN o lote SHALL ser consolidado e a execução SHALL transicionar para `aguardando_confirmacao`, contendo apenas mensagens aprovadas pelo crítico **e** por Marina | `EstadoExecucao.AGUARDANDO_CONFIRMACAO` e `mensagens_aprovadas` = **interseção** das duas aprovações | Metade "Marina" (crítico aprovou, Marina rejeitou): `testes/test_revisao_lote.py:1155-1163` — `estado is AGUARDANDO_CONFIRMACAO`, `mensagens_aprovadas == (aprovada,)`, `em_excecao not in mensagens_aprovadas`. **Metade "crítico" (novo)**: `testes/test_revisao_lote.py:1197-1203` — `decisao.estado is AGUARDANDO_CONFIRMACAO`, `decisao.mensagens_aprovadas == (aprovada_pelos_dois,)`, `sem_avaliacao_critica not in decisao.mensagens_aprovadas`, `estados[sem_avaliacao_critica] is EstadoMensagem.APROVADA`. Contrato HTTP: `testes/test_revisao_lote_api.py:266` | ✅ **PASS** (era ⚠️ GAP parcial na rodada 1) |

### Critérios carregados da rodada 1 (derivados exaustivamente lá, sem lacuna e sem alteração no diff desta rodada)

REVISAO-02, 03, 04, 05, 06, 07, 08, 11, 12, 13 — todos ✅ PASS, evidência `file:line` na seção "Spec-Anchored Acceptance Criteria" do relatório da rodada 1 (`e99f4b4`, mesmo arquivo). Nenhum dos arquivos que os sustentam foi tocado por `0e6d557`, e a suíte inteira segue verde.

**Status**: ✅ **14/14 ACs com outcome de spec batido e evidência `file:line`.** 0 spec-precision gaps.

---

## Edge Cases

- [x] **Edge Case 1** — lote inteiro em `falhou_conteudo`/`falhou_integracao_ia` ainda alcança `aguardando_revisao` e conclui sem simulação ao reconhecimento de Marina: `testes/test_geracao_mensagens.py:1404` + `testes/test_revisao_lote.py:1121-1123`. **Reforçado nesta rodada**: o caso agora também vale quando o reconhecimento chega depois de um reinício (o caminho do Gap 1).
- [x] **Edge Case 2** — item já decidido é recusado com motivo sem impedir as demais válidas do mesmo envio: `testes/test_revisao_lote.py:1012-1015`; `testes/test_revisao_lote_api.py:487`.
- [x] **Edge Case 3** — regeneração ativa bloqueia decisão/confirmação até a guarda ser satisfeita: `testes/test_revisao_lote.py:1044`; `testes/test_revisao_lote_api.py:457`.

---

## Discrimination Sensor (rodada 2)

Scratch: `git worktree add` em diretório temporário; nunca `git stash`. Baseline `git status --porcelain` **vazio** antes; worktree revertido (`git checkout -- .`, porcelain vazio) e removido (`git worktree remove --force`); `git worktree list` de volta a uma única árvore; porcelain da árvore real **vazio** depois; `HEAD` inalterado em `0e6d557`.

| # | File:line | Description | Killed? |
| --- | --- | --- | --- |
| M4′ (re-injeção da mutação sobrevivente da rodada 1) | `aplicacao/revisao_lote.py:645` | Removido `and self._aprovada_pelo_critico(registro.id)` — a aprovação dupla do REVISAO-14 vira só a decisão de Marina | ✅ **Killed** — `test_marina_aprova_mas_o_critico_nao_avaliou_a_versao_fica_de_fora` (1 falha na suíte inteira, 826 outros verdes: sem dano colateral) |
| M8 (regressão dirigida à correção) | `aplicacao/geracao_mensagens.py:477` | Removida a chamada pós-laço `self.abrir_revisao_se_lote_completo(execucao_id)` — volta ao código exato da rodada 1 | ✅ **Killed** — `test_retomada_no_boot_com_todas_as_mensagens_ja_terminais_ainda_abre_a_revisao` |

Sonda adicional (não é mutação — é prova de ausência de falso-positivo): retomada de execução com **zero** mensagens permanece em `processando_mensagens`, sem exceção registrada. Ver Gap 1.

Mutações M1, M2, M3, M5, M6, M7 da rodada 1 não foram re-injetadas: nenhum dos arquivos ou linhas que elas atacam foi alterado por `0e6d557` (o diff de produção é uma única linha adicionada), e o veredito da rodada 1 sobre elas (5 mortas pela suíte, M2 morta só pelo `pyright` do gate — L-045) permanece válido.

**Sensor depth**: P0-full na rodada 1 (7 mutações); rodada 2 dirigida às duas correções de comportamento (2 mutações + 1 sonda).
**Result**: **7/7 mortos** no acumulado da história — 6 pela suíte, 1 (M2) pelo `pyright` do gate obrigatório — ✅ **PASS**.

---

## Code Quality

| Principle | Status |
| --- | --- |
| Minimum code | ✅ — a correção do Gap 1 é **uma linha** de produção; nada mais foi adicionado |
| Surgical changes | ✅ — os outros 5 arquivos do commit só ganharam docstring |
| No scope creep | ✅ — nenhuma refatoração de oportunidade no commit de correção |
| Matches patterns | ✅ — `SPEC_DEVIATION (História N.N): ...` no mesmo formato das 22 ocorrências anteriores; o gatilho pós-laço espelha o `abrir_revisao_se_lote_completo` que `gerar_lote` (`:616`) já chamava fora do laço |
| Spec-anchored outcome check | ✅ — resolvido; REVISAO-14 agora tem asserção nos dois lados da conjunção |
| Per-layer Coverage Expectation met | ✅ domínio 1:1 com ACs; rotas com feliz + `404`/`409`/`422` |
| Every test maps to a spec requirement — no unclaimed tests | ✅ — as duas docstrings novas citam `REVISAO-01` e `REVISAO-14` explicitamente |
| Documented guidelines followed | ✅ — `AGENTS.md`/`README.md`; repositórios reais sobre banco migrado nos dois testes novos, sem dublê de persistência |
| Deviations marked per project convention | ✅ — resolvido (Gap 3) |

---

## Gate Check

- **Gate command (Build)**: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright` + `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`
- **Result**: backend **827 passed, 0 failed, 0 skipped** (exit 0); `ruff` "All checks passed!"; `pyright` "0 errors, 0 warnings, 0 informations". Frontend **268 passed / 29 arquivos, 0 failed** (exit 0); `oxlint` exit 0 (só os 5 avisos `set-state-in-effect` pré-existentes, padrão acumulado do projeto); `tsc -b && vite build` OK.
- **Test count antes da história** (`7bca11d`): 737 backend / 253 frontend
- **Test count na rodada 1** (`50c8602`): 825 backend / 268 frontend
- **Test count nesta rodada** (`0e6d557`): **827 backend / 268 frontend** — contagem conferida por `pytest --collect-only` na árvore real, não presumida
- **Delta desta rodada**: +2 backend (os dois testes das correções), frontend inalterado — coerente com um commit sem mudança de superfície
- **Delta da história**: +90 backend, +15 frontend
- **Skipped tests**: nenhum
- **Test integrity**: nenhuma linha `-def test_` / `-it(` no diff `50c8602..0e6d557` — nenhum teste removido nem asserção enfraquecida

---

## Fix Plans

Nenhum. Os três gaps da rodada 1 estão fechados e nenhum gap novo foi encontrado.

### Observações não-bloqueantes

- **Precisão de citação em `repositorio_execucao_preventiva.py:190`**: o marcador diz que o `design.md` lista o método como reusado "sem alteração"; a expressão literal aparece na linha 44 (para `RepositorioMensagens`), não na 45. O desvio descrito é real e a justificativa técnica está correta — é paráfrase, não erro material. Cosmético.
- **Retomada não recria mensagem inexistente**: se um `gerar_lote` fosse interrompido no meio da criação, `retomar_mensagens_pendentes` não criaria a mensagem faltante (o boot só chama a retomada, `gerenciador_execucoes.py:397`), e o lote poderia abrir parcial. É a fronteira de retomada já herdada da 3.4/REGEN-08 e alcançável pelo caminho por item desde antes desta história — **não é introduzida por `0e6d557`**, que apenas a estende ao caso de laço vazio. Registrada aqui para rastreabilidade; fora do escopo da 3.5.
- Permanecem as três observações não-bloqueantes da rodada 1: `asyncio.create_task` sem callback de exceção em `adaptadores/http/revisao_lote.py:576-581`; `src/frontend/src/api/revisaoLote.ts` sem teste próprio (padrão acumulado de 3.1–3.3); `SuperficieRevisaoLote` sem entrada em `App.tsx` (risco (9) do `STATE.md`).

---

## Requirement Traceability Update

| Requirement | Previous Status (rodada 1) | New Status |
| --- | --- | --- |
| REVISAO-01 | ❌ Needs Fix (Gap 1) | ✅ Verified |
| REVISAO-02 | ✅ Verified | ✅ Verified (carregado) |
| REVISAO-03 | ✅ Verified | ✅ Verified (carregado) |
| REVISAO-04 | ✅ Verified | ✅ Verified (carregado) |
| REVISAO-05 | ✅ Verified | ✅ Verified (carregado) |
| REVISAO-06 | ✅ Verified | ✅ Verified (carregado) |
| REVISAO-07 | ✅ Verified | ✅ Verified (carregado) |
| REVISAO-08 | ✅ Verified | ✅ Verified (carregado) |
| REVISAO-09 | ✅ Verified | ✅ Verified (re-confirmado) |
| REVISAO-10 | ✅ Verified | ✅ Verified (re-confirmado — sem regressão pela chamada pós-laço) |
| REVISAO-11 | ✅ Verified | ✅ Verified (carregado) |
| REVISAO-12 | ✅ Verified | ✅ Verified (carregado) |
| REVISAO-13 | ✅ Verified | ✅ Verified (carregado) |
| REVISAO-14 | ❌ Needs Fix (Gap 2) | ✅ Verified |

---

## Lessons

Sem sinal novo nesta rodada. Os três sinais que a produziram já viraram lição na rodada 1 e as correções os confirmam, não os ampliam:

- Gap 1 → **L-044** ("A state trigger placed inside a per-item loop never fires when the loop body is empty; also invoke it once after the loop so the zero-pending case still converges") — descreve exatamente a correção aplicada e é distinta da L-042 (que trata de *semear* o cenário de retomada certo, não de o gatilho precisar de uma chamada pós-laço). Nada a acrescentar.
- Gap 2 → **L-043** ("When a criterion requires two independent approvals, seed the case where only one of them holds and assert exclusion").
- Gap 3 → **L-046** ("Extending a component that design.md declares reused without change is a deviation — mark it with the project's deviation marker even when the signature change is backward compatible").

Rodada 2 é um PASS limpo — 0 mutantes sobreviventes, 0 spec-precision gaps, 0 ACs sem evidência, nenhum `SPEC_DEVIATION` novo (os três adicionados são a *correção* do sinal já registrado em L-046). Conforme `references/lessons.md`, nada novo é registrado.

---

## Summary

**Overall**: ✅ **Ready** — os três gaps da rodada 1 estão fechados e nenhum gap novo foi encontrado

**Spec-anchored check**: 14/14 ACs com outcome de spec batido e evidência `file:line`; 0 spec-precision gaps
**Sensor**: 2 mutações re-injetadas nesta rodada, 2 mortas (M4′ e M8) + 1 sonda de falso-positivo passando; acumulado da história 7/7 mortos (6 pela suíte, M2 pelo `pyright` do gate)
**Gate**: 827 backend + 268 frontend, 0 falhas; `ruff`/`pyright`/`oxlint`/`build` limpos

**O que ficou provado nesta rodada**:

- O bug do Gap 1 era real e o novo teste o discrimina: removida a linha da correção, ele falha com exatamente o sintoma da rodada 1 (`processando_mensagens` em vez de `aguardando_revisao`).
- A chamada incondicional pós-laço não abre lote indevidamente: execução com zero mensagens permanece em `processando_mensagens` (sonda própria), e item ainda no ciclo continua bloqueando (REVISAO-10 sem regressão).
- M4, que sobreviveu à suíte inteira na rodada 1, agora mata exatamente 1 teste e nenhum outro — a conjunção do REVISAO-14 está discriminada nos dois lados.
- Os três marcadores `SPEC_DEVIATION` existem, seguem a convenção e **descrevem com precisão** o que o código faz: a lista dos 4 métodos que ganharam `conexao` bate método a método, e `TransacaoDuckDB` está de fato ausente do `design.md` (`grep -c` → 0).
- Nada além de uma linha de produção mudou: o commit de correção é cirúrgico e não removeu nem enfraqueceu nenhum teste.

**Issues found**: nenhum

**Next steps**: história pronta para fechamento no `.specs/STATE.md` pelo orquestrador (o Verificador não edita `STATE.md`).
