# História 3.4: Regenerar mensagens e registrar a proveniência agêntica — Validation

## Validation Verdict: PASS ✅

**Round**: 2 de 3 (o round 1 fechou com veredito negativo; este round re-verifica as duas lacunas e o gate inteiro)
**Date**: 2026-09-04
**Spec**: `.specs/features/3-4-regenerar-mensagens-e-registrar-a-proveniencia-agentica/spec.md`
**Diff range**: `ce964f8..e72bbdb` (implementação `e303d42..70ce8af`, relatório do round 1 em `d4343dd`, correções do round 2 em `c355fec` e `e72bbdb`)
**Verifier**: sub-agente independente e novo (author ≠ verifier; verificador do round 2 ≠ verificador do round 1), re-derivado do diff e da `spec.md`, sem confiar no relato do autor nem no do round anterior

**Por que passa agora**: as duas lacunas do round 1 eram de **teste**, não de produção — nenhum arquivo de implementação foi tocado pelas correções (`git diff --name-only d4343dd..e72bbdb` retorna exatamente um caminho: `src/backend/testes/test_geracao_mensagens.py`, +78 linhas, 0 remoções). Reinjetei a mutação exata do round 1 (M7) num worktree descartável e ela agora **morre em dois testes**; neutralizei o ramo sem cobertura do round 1 (M8) e ele **morre no teste novo** — e, para provar que a cobertura é nova e não coincidência, rodei a mesma mutação M8 contra o arquivo de testes do round 1 (`d4343dd`), onde ela **sobrevive** com 735 testes verdes. Gate verde: 737 backend (735 + 2 novos) + 253 frontend, `ruff`/`pyright` limpos.

---

## Task Completion

| Task | Status | Notes |
| --- | --- | --- |
| T1 — Migração `mensagem_id` em `excecoes_operacionais` | ✅ Done | `e303d42`. Renumerada para `0012` — SPEC_DEVIATION declarada no `.sql`. `testes/test_migracoes.py:87`, `testes/test_inicializador.py:73`. |
| T2 — `RepositorioMensagens.incrementar_tentativa` | ✅ Done | `95a59c0`. Limite cobrado no próprio `UPDATE` (`tentativa_atual < 3` no `WHERE`). |
| T3 — Ciclo automático no `GrafoGeracaoMensagem` | ✅ Done | `13af722`. Nós `regenerar`/`esgotar` + 3 arestas condicionais. |
| T4 — `retomar_pendentes` estendido | ✅ Done | `c57d10a`. Ligado no boot (item 12(b) do `STATE.md`). |
| T5 — `GET /mensagens/{id}/proveniencia` | ✅ Done | `e886218`. `openapi.json` regenerado. |
| T6 — Superfície de acompanhamento do ciclo | ✅ Done | `70ce8af`. 6 categorias distintas, foco preservado, `aria-live`. |
| Fix 1 (round 1, Major) — discriminação do número de tentativa na retomada | ✅ Done | `c355fec`. Somente teste. Ver "Round 1 — Gap 1" abaixo. |
| Fix 2 (round 1, Minor) — ramo de retomada com avaliação já aprovada | ✅ Done | `e72bbdb`. Somente teste. Ver "Round 1 — Gap 2" abaixo. |

---

## Round 1 — Gap 1 (Major): fechado ✅

**A lacuna**: `_retomar_grafo` (`src/backend/central_preventiva/aplicacao/geracao_mensagens.py:514`) reconstrói `estado["tentativa"]` a partir de `registro.tentativa_atual`, e esse valor vira (a) o `numero_tentativa` da versão que a retomada grava, (b) o campo `tentativas` da `Exceção` de esgotamento e (c) a decisão `regenerar` vs `esgotar`. No round 1, trocar essa linha por `1` mantinha os 735 testes verdes: o único teste de retomada que chegava a `NO_GERAR` semeava `tentativa_atual == 1`, onde o valor errado coincidia com o certo, e todos os demais caminhos passavam por `preparar_regeneracao`, que relê o número do banco.

**O que a correção acrescentou** (`c355fec`, só teste):

1. `testes/test_geracao_mensagens.py:1125` — `test_retomada_de_mensagem_reservada_na_terceira_tentativa_gera_com_o_numero_certo`. Semeia 2 tentativas concluídas e reprovadas por `_semear_tentativas_reprovadas(..., ate_tentativa=2)`, depois chama `incrementar_tentativa` + `transicionar(..., GERANDO)` **fora** do laço do helper — reproduzindo exatamente "tentativa 3 reservada, nenhuma versão 3 gravada", que o helper sozinho nunca produz (ele só incrementa `if tentativa < ate_tentativa`). Asserção-chave em `:1150` — `assert [numero for numero, _, _ in _versoes_persistidas(tmp_path, mensagem_id)] == [1, 2, 3]`, mais `:1153` `assert mensagem.tentativa_atual == 3` e `:1154` `assert mensagem.estado is EstadoMensagem.AGUARDANDO_REVISAO`.
2. `testes/test_geracao_mensagens.py:1122` — asserção nova no teste pré-existente `test_retomada_na_terceira_tentativa_ja_reprovada_esgota_sem_gerar_de_novo`: `assert [tentativas for _, _, tentativas, _ in reiniciado.excecoes.registradas] == [3]`, que prende o campo `tentativas` da `Exceção` de esgotamento ao número real lido do registro retomado.

**Confirmação independente por mutação** (worktree descartável em `HEAD`, mutação idêntica à do round 1):

| Estado | `estado["tentativa"]` | Resultado da suíte |
| --- | --- | --- |
| Produção atual (`e72bbdb`) | `registro.tentativa_atual` | 737 passed |
| M7 reinjetada | `1` | **2 failed, 735 passed** |

As duas falhas são exatamente as duas asserções novas, e nenhuma outra:

- `test_retomada_de_mensagem_reservada_na_terceira_tentativa_gera_com_o_numero_certo` — `assert [1, 1, 2] == [1, 2, 3]` (a tentativa 1 é regravada por cima em vez de a 3 ser completada — o desfecho exato que o REGEN-09 proíbe).
- `test_retomada_na_terceira_tentativa_ja_reprovada_esgota_sem_gerar_de_novo` — `assert [1] == [3]` (a `Exceção` do REGEN-04 passaria a declarar 1 tentativa usada em vez de 3).

Zero dano colateral: os outros 735 testes seguem verdes sob a mutação, ou seja, a asserção nova é específica ao comportamento mutado.

---

## Round 1 — Gap 2 (Minor): fechado ✅

**A lacuna**: o ramo de `_retomar_item` em `geracao_mensagens.py:480-482` — versão válida + avaliação já persistida como aprovada, mas a transição para `aguardando_revisao` ainda não aplicada quando o processo caiu — não tinha nenhum teste.

**Roteamento conferido na fonte** (`geracao_mensagens.py:450-490`), não pelo desfecho visível. O estado semeado pelo teste novo percorre, na ordem:

1. `:454` `contexto is None` → falso (o cenário semeia contexto);
2. `:461` `versao is None or versao.numero_tentativa < registro.tentativa_atual` → falso (versão 1 existe, `numero_tentativa == 1`, `tentativa_atual == 1`) — **não** entra em `NO_GERAR`;
3. `:466` `not versao.valida` → falso (`valida=True` na semeadura);
4. `:473` `avaliacao is None` → falso (a linha aprovada foi persistida) — **não** entra em `NO_CRITICAR`;
5. `:480` `critica.desfecho is DesfechoCritica.APROVADA` → **verdadeiro** → `self._ciclo.registrar_critica(...)` + `return`, sem tocar no grafo.

É o ramo que o round 1 apontou, e não um caminho vizinho com desfecho parecido.

**O teste** (`e72bbdb`, só teste): `testes/test_geracao_mensagens.py:1211` — `test_retomada_de_avaliacao_aprovada_sem_transicao_aplicada_conclui_sem_duplicar`. Semeia mensagem + `salvar_versao(..., valida=True)`, `transicionar(..., CRITICANDO)` e `avaliacoes.salvar(versao_id, True, (), ...)` **sem** a transição para `aguardando_revisao`; retoma e afirma: `:1240` `assert reiniciado.redator.canais_chamados == []`, `:1241` `assert reiniciado.critico.chamadas == 0`, `:1244` `assert mensagem.estado is EstadoMensagem.AGUARDANDO_REVISAO` e `:1250` `assert total == (1,)` sobre `SELECT count(*) FROM avaliacoes_criticas WHERE versao_mensagem_id = ?` — contagem em SQL direto, não por método de repositório que pudesse esconder duplicata.

**Confirmação independente por mutação (M8)**: neutralizei o ramo no worktree (`if critica.desfecho is DesfechoCritica.APROVADA: return`, sem `registrar_critica`).

| Suíte | Resultado sob M8 |
| --- | --- |
| Testes do round 1 (`d4343dd:src/backend/testes/test_geracao_mensagens.py`) | **735 passed** — mutante sobrevive, a lacuna era real |
| Testes atuais (`e72bbdb`) | **1 failed, 736 passed** — `AssertionError: assert <EstadoMensagem.CRITICANDO> is <EstadoMensagem.AGUARDANDO_REVISAO>` |

O único teste que falha é o novo — ele é o que discrimina esse ramo, e antes de `e72bbdb` ninguém o fazia.

---

## Spec-Anchored Acceptance Criteria

REGEN-04, REGEN-07, REGEN-08 e REGEN-09 foram re-derivados neste round contra as evidências novas (são os critérios que as duas lacunas tocavam). Os demais reusam a verificação exaustiva do round 1, cujo diff de implementação não mudou desde então (`git diff --name-only d4343dd..e72bbdb` = apenas o arquivo de testes).

### P1: Regeneração automática limitada a três tentativas

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| REGEN-01: WHEN reprovada (crítico ou validação determinística recuperável) e há tentativa disponível THEN o redator recebe os motivos e gera nova versão, histórico anterior imutável e consultável | redator rechamado com os motivos categorizados; versão anterior preservada | `testes/test_grafo_geracao_mensagem.py:472` — `assert redator.motivos_recebidos == [(), (MotivoCritica(CategoriaCritica.TOM, "O texto usa tom alarmista."),)]`; `testes/test_geracao_mensagens.py:941` — `assert cenario.redator.motivos_recebidos == [(), (motivo,)]`; `testes/test_geracao_mensagens.py:906` — `assert versoes[0][1] == f'{{"corpo": "{CORPO_VALIDO} versao um"}}'`; ramo determinístico em `testes/test_grafo_geracao_mensagem.py:493`; histórico consultável em `testes/test_proveniencia_api.py:171` | ✅ PASS (round 1) |
| REGEN-02: The system SHALL permitir no máximo três tentativas totais por mensagem | 4ª tentativa nunca reservada; limite = 3 | `testes/test_repositorio_mensagens.py:258` — `with pytest.raises(LimiteTentativasExcedido)` + `assert registro.tentativa_atual == 3`; `testes/test_grafo_geracao_mensagem.py:564` — `assert redator.chamadas == MAXIMO_TENTATIVAS_MENSAGEM` | ✅ PASS (round 1) |
| REGEN-03: WHEN uma tentativa produzir aprovação válida THEN o ciclo encerra imediatamente | parada na tentativa 1, 2 **e** 3 | `testes/test_grafo_geracao_mensagem.py:515`, `:530`, `:546` — `assert [tentativa for tentativa, _ in ciclo.versoes] == [1, 2, 3]` + `assert ciclo.excecoes == []` | ✅ PASS (round 1) |
| REGEN-04: IF a terceira tentativa também for reprovada THEN `falhou_conteudo` + `Exceção`, fora do lote simulável | estado `falhou_conteudo`, exceção com causa/**tentativas**/impacto correlacionada por `mensagem_id` | **re-verificado neste round**: `testes/test_geracao_mensagens.py:960` — `assert cenario.excecoes.registradas == [(EXECUCAO_ID, f"falhou_conteudo:{incluido.id}:seguranca", 3, IMPACTO_ITEM_FORA_DO_LOTE)]` (caminho sem retomada) **e agora também no caminho de retomada**, `testes/test_geracao_mensagens.py:1117-1122` — `assert mensagem.estado is EstadoMensagem.FALHOU_CONTEUDO` + `assert mensagem.tentativa_atual == 3` + `assert [tentativas for _, _, tentativas, _ in reiniciado.excecoes.registradas] == [3]`; grafo em `testes/test_grafo_geracao_mensagem.py:564`; distinção execução↔mensagem em SQL em `testes/test_migracoes.py:890` | ✅ PASS (re-verificado) |

**Nota**: "não poder integrar o lote simulável" é observável nesta história pelo terminal `falhou_conteudo` + o impacto `IMPACTO_ITEM_FORA_DO_LOTE`; o portão de composição do lote é da História 3.6. Não é lacuna — a spec não define outro observável aqui.

### P1: Isolamento de falha de integração por mensagem

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| REGEN-05: IF falha não recuperada da OpenAI em geração **ou** crítica com transporte esgotado THEN somente a mensagem afetada alcança `falhou_integracao_ia` | `falhou_integracao_ia`, distinto de `falhou_conteudo`, nos **dois** nós | `testes/test_grafo_geracao_mensagem.py:630` e `:646`; persistência real em `testes/test_geracao_mensagens.py:487`, `:806` e `:987` | ✅ PASS (round 1) |
| REGEN-06: WHILE uma mensagem estiver em `falhou_integracao_ia` THEN as demais alcançam seus próprios terminais | outros itens chegam a `aguardando_revisao`/`falhou_conteudo` | `testes/test_geracao_mensagens.py:487`, `:873`, `:1005` (`assert mensagens[0].estado is EstadoMensagem.AGUARDANDO_REVISAO` após `RuntimeError` no item anterior) | ✅ PASS (round 1) |

### P1: Proveniência completa e retomada sem repetição

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| REGEN-07: WHEN a proveniência de qualquer versão/avaliação for consultada THEN apresenta agente, modelo, versão do prompt, categorias de entrada, saída, avaliação, **tentativa**, duração e métricas de uso | os 9 nomes do AC, por tentativa | **re-verificado neste round** (a tentativa é o campo que o Gap 1 tocava): leitura da API em `testes/test_proveniencia_api.py:127` — `assert primeira["agente"] == "redator"`, `assert primeira["modelo"] == "gpt-4o-mini"`, `assert primeira["versao_prompt"] == "v1"`, `assert corpo["categorias_entrada"]["usadas"] == list(CATEGORIAS_USADAS)`, `assert primeira["saida"] == {"assunto": None, "corpo": "Alerta enfático demais."}`, `assert primeira["avaliacao"]["aprovada"] is False`, `assert primeira["numero_tentativa"] == 1`, `assert primeira["duracao_ms"] == 742.5`, `assert primeira["tokens_entrada"] == 210`, `assert primeira["tokens_saida"] == 64`; **escrita** do `numero_tentativa` agora presa também no caminho de retomada por `testes/test_geracao_mensagens.py:1150` — `assert [numero for numero, _, _ in _versoes_persistidas(tmp_path, mensagem_id)] == [1, 2, 3]` (antes, uma versão duplicada de tentativa 1 passava despercebida e a proveniência por tentativa ficaria com uma linha errada) | ✅ PASS (re-verificado) |
| REGEN-08: The provenance record SHALL não conter chave, contato, prompt completo em log ou informação sensível | ausência literal de chave/nome/telefone/instrução de sistema | `testes/test_proveniencia_api.py:189` — `assert CHAVE_OPENAI not in bruto`, `assert NOME_SEGURADO not in bruto`, `assert TELEFONE_SEGURADO not in bruto`, `assert INSTRUCAO_SISTEMA not in bruto`, `assert "prompt" not in bruto.lower().replace("versao_prompt", "")` | ✅ PASS (round 1; nenhuma mudança de produção desde então) |
| REGEN-09: WHEN o runner retomar após reinício THEN continua do último marco durável sem repetir tentativa já concluída | continua da tentativa em curso, sem refazer as concluídas, em **cada** marco durável | **re-verificado neste round, agora com discriminação provada**: tentativa 3 já reservada e sem versão — `testes/test_geracao_mensagens.py:1149-1154` — `assert reiniciado.redator.canais_chamados == [Canal.SMS]` (uma única chamada) + `assert [...] == [1, 2, 3]` + `assert mensagem.tentativa_atual == 3` + `assert mensagem.estado is EstadoMensagem.AGUARDANDO_REVISAO`; tentativa 2 reprovada → segue na 3 — `:1089-1093`; 3ª já reprovada → esgota — `:1113-1122`; sem versão nenhuma — `:1170`; em `criticando` sem avaliação — `:1205`; **avaliação aprovada sem transição aplicada** — `:1240-1250`; terminais nunca reabrem — `:1185+`; delegação no boot — `testes/test_gerenciador_execucoes.py:549` e `:566`. Mutação M7 morta (ver acima) | ✅ PASS (re-verificado) |
| REGEN-10: The system SHALL nunca reabrir um estado terminal de mensagem já alcançado | 5 terminais, linha não mutada, nenhuma versão nova, nenhuma chamada à OpenAI | `testes/test_geracao_mensagens.py:1185` (parametrizado nos 5 terminais) — `assert depois.versao == antes.versao`, `assert _versoes_persistidas(tmp_path, mensagem_id) == []`, `assert reiniciado.redator.canais_chamados == []`; `testes/test_repositorio_mensagens.py:298` | ✅ PASS (round 1) |

### P2: Acompanhamento acessível do ciclo por item

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| REGEN-11: WHEN tentativas e mensagens mudarem de estado THEN a interface mostra etapa, tentativa atual, limite, aprovações e exceções por item | "Tentativa N de 3" por item + etapa + agregados | `SuperficieGeracaoMensagens.test.tsx:192`, `:210`, `:235`; limite vindo do backend em `adaptadores/http/mensagens.py:71` | ✅ PASS (round 1) |
| REGEN-12: The interface SHALL não mover o foco inesperadamente nem depender somente de cor | `document.activeElement` igual antes e depois; texto+ícone+cor distintos | `SuperficieGeracaoMensagens.test.tsx:249`, `:270`, `:290`, `:210` | ✅ PASS (round 1) |

**Status**: ✅ 12/12 ACs cobertos com evidência `file:line` e desfecho batendo com o texto da spec; 0 spec-precision gaps; 0 lacunas de discriminação.

---

## Edge Cases

- [x] **EC1** — Reprovação na tentativa 3 por falha determinística leva ao mesmo `falhou_conteudo`: `testes/test_grafo_geracao_mensagem.py:588` — `assert critico.chamadas == 0` + `assert ciclo.estado is EstadoMensagem.FALHOU_CONTEUDO`; com persistência real em `testes/test_geracao_mensagens.py:439` e `:465`.
- [x] **EC2** — Falha de integração durante a própria tentativa 3 leva a `falhou_integracao_ia`, não `falhou_conteudo`: `testes/test_grafo_geracao_mensagem.py:646` — `assert ciclo.tentativa_atual == 3`, `assert ciclo.estado is EstadoMensagem.FALHOU_INTEGRACAO_IA`, `assert ciclo.estado is not EstadoMensagem.FALHOU_CONTEUDO`.
- [x] **EC3** — Execução com mensagens em terminais diferentes: o estado de cada mensagem está correto ao final desta história e o agregado da execução não é movido (o portão é da 3.5): `testes/test_geracao_mensagens.py:873` e `:487`; execução intocada em `testes/test_gerenciador_execucoes.py:549`. Observação menor (não bloqueante, herdada do round 1): nenhum teste único reúne os três terminais simultaneamente; a spec só exige o estado correto por mensagem.

---

## Discrimination Sensor

Scratch isolado: `git worktree add <scratch> HEAD` (nunca `git stash`). Baseline `git status --porcelain` **vazio** antes do sensor e **vazio** depois; worktree removido com `git worktree remove --force` + `git worktree prune`; `git worktree list` de volta a uma única linha e `HEAD` conferido em `e72bbdb` ao final. Nenhum arquivo real foi modificado por este round além dos documentos de `.specs/`.

| # | Mutation | File | Description | Killed? |
| --- | --- | --- | --- | --- |
| M1 | Off-by-one do limite de tentativas | `aplicacao/grafos/geracao_mensagem.py:77` | `MAXIMO_TENTATIVAS_MENSAGEM = 3` → `4` | ✅ Killed (round 1) |
| M2 | Retomada sempre reinicia em `gerar` | `aplicacao/geracao_mensagens.py:461` | removida a guarda `if versao is None or versao.numero_tentativa < registro.tentativa_atual` | ✅ Killed (round 1) |
| M3 | Remoção da guarda de estado terminal na retomada | `aplicacao/geracao_mensagens.py:436` | removido `if registro.estado not in ESTADOS_RETOMAVEIS: continue` | ✅ Killed (round 1) |
| M4 | Troca de terminal por causa (geração) | `aplicacao/geracao_mensagens.py:290` | transporte esgotado em `gerar` → `FALHOU_CONTEUDO` | ✅ Killed (round 1) |
| M5 | Troca de terminal por causa (crítica) | `aplicacao/geracao_mensagens.py:330` | transporte esgotado em `criticar` → `FALHOU_CONTEUDO` | ✅ Killed (round 1) |
| M6 | Remoção do `except Exception` amplo por item (risco 12a) | `aplicacao/geracao_mensagens.py:525` | `_gerar_item_isolado` sem `try/except` | ✅ Killed (round 1) |
| M7 | Número de tentativa errado na reconstrução da retomada | `aplicacao/geracao_mensagens.py:514` | `"tentativa": registro.tentativa_atual` → `"tentativa": 1` | ✅ **Killed neste round** — 2 failed, 735 passed: `test_retomada_de_mensagem_reservada_na_terceira_tentativa_gera_com_o_numero_certo` (`assert [1, 1, 2] == [1, 2, 3]`) e `test_retomada_na_terceira_tentativa_ja_reprovada_esgota_sem_gerar_de_novo` (`assert [1] == [3]`). Sobrevivia no round 1 |
| M8 | Ramo de retomada com avaliação aprovada sem efeito | `aplicacao/geracao_mensagens.py:480` | `if critica.desfecho is DesfechoCritica.APROVADA: return` sem `registrar_critica` | ✅ **Killed neste round** — 1 failed, 736 passed: `test_retomada_de_avaliacao_aprovada_sem_transicao_aplicada_conclui_sem_duplicar` (`assert <EstadoMensagem.CRITICANDO> is <EstadoMensagem.AGUARDANDO_REVISAO>`). **Sobrevive** (735 passed) quando rodada contra o arquivo de testes do round 1 (`d4343dd`) — prova de que a cobertura é nova, não incidental |

**Sensor depth**: expandido (8 mutações acumuladas; P1 com invariantes de integridade de dados — limite de tentativas e retomada). Este round reinjetou M7 e M8; M1–M6 são do round 1 e nada na produção mudou desde então.
**Result**: 8/8 mortos — PASS ✅

---

## Code Quality

| Principle | Status |
| --- | --- |
| Minimum code | ✅ — as correções do round 2 não acrescentaram nenhuma linha de produção; +78 linhas em um único arquivo de teste |
| Surgical changes | ✅ — `git diff --name-only d4343dd..e72bbdb` = `src/backend/testes/test_geracao_mensagens.py`, e nada mais |
| No scope creep | ✅ — nenhum helper novo criado; `c355fec` reusa `_semear_tentativas_reprovadas` e `_versoes_persistidas`, `e72bbdb` reusa `Cenario`/`abrir_conexao` |
| Matches patterns | ✅ — o teste do Gap 2 conta linhas com SQL direto, mesmo padrão de `_versoes_persistidas` (`:716`) |
| Spec-anchored outcome check (valores afirmados batem com a spec) | ✅ — 12/12 |
| Per-layer Coverage Expectation (domínio 1:1 com ACs; rotas com happy + edge + erro) | ✅ — `test_proveniencia_api.py` cobre 200 completo, 200 sem tentativa, 200 sem avaliação, 404 e 422; a retomada agora cobre os **seis** marcos duráveis do `_retomar_item` (sem versão; versão da tentativa anterior com a próxima já reservada; versão inválida; versão válida sem avaliação; avaliação aprovada sem transição; avaliação reprovada com e sem tentativa restante) |
| Todo teste em escopo mapeia para AC/edge case/Done-when | ✅ — os 2 testes novos citam REGEN-04/07/08/09 no próprio docstring |
| Documented guidelines followed | ✅ — `AGENTS.md`, `README.md` |
| Integridade de teste (contagem/nomes) | ✅ — nenhum teste apagado nem renomeado nas correções; delta puramente aditivo (+2 testes, +1 asserção em um teste existente) |

Os itens de qualidade re-verificados exaustivamente no round 1 e não tocados pelas correções permanecem válidos e são reafirmados aqui sem re-litígio: os 6 testes reescritos de 3.2/3.3 (**legítimos, nenhum enfraquecido, nenhum apagado** — comportamento explicitamente deferido em `.specs/features/3-2-.../spec.md:23` e `.specs/features/3-3-.../spec.md:21`), a fronteira de minimização do `ContextoAgente` (`git diff ce964f8..e72bbdb -- central_preventiva/dominio/` continua vazio), a discriminação de `excecoes_operacionais.mensagem_id` nos dois sentidos em SQL (`testes/test_migracoes.py:890`) e as 4 SPEC_DEVIATIONs declaradas.

### Itens 12(a)/12(b) do `STATE.md` — veredito do round 1 mantido, sem re-litígio

- **12(b): genuinamente fechado.** A fiação de boot foi traçada ponta a ponta no round 1 (`composicao/api.py:69` → `aplicacao/gerenciador_execucoes.py:396` → `ServicoGeracaoMensagens.retomar_mensagens_pendentes` real), coberta por `testes/test_gerenciador_execucoes.py:549` e `:566`.
- **12(a): parcialmente fechado — permanece registrado no `STATE.md`.** O `except Exception` por item é real e provado (M6 morto), mas a `asyncio.Task` desacoplada em `adaptadores/http/preflight_ia.py:259` segue com `add_done_callback(_tarefas_de_geracao.discard)` sem chamar `.exception()`, e a chamada a `elegibilidades.listar_por_execucao` fora do laço de `gerar_lote` continua sem `try`. Nada mudou nesses dois pontos entre `70ce8af` e `e72bbdb`. **Não riscar 12(a)** do `STATE.md`.

---

## Gate Check

- **Gate command (Build)**: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright` + `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`
- **Backend**: **737 passed**, 0 failed, 0 skipped (`54.11s`); `ruff` — "All checks passed!"; `pyright` — "0 errors, 0 warnings, 0 informations"
- **Frontend**: 253 passed em 28 arquivos, 0 failed, 0 skipped (`9.78s`, exit 0); `lint`/`build` inalterados desde o round 1 (nenhum arquivo de frontend tocado por `c355fec`/`e72bbdb`)
- **Test count before feature**: 689 backend + 247 frontend
- **Test count after round 1**: 735 backend + 253 frontend
- **Test count after round 2**: **737 backend** + 253 frontend
- **Delta**: +48 backend (+2 neste round), +6 frontend
- **Test integrity**: nenhum teste apagado, nenhum renomeado e nenhuma asserção enfraquecida neste round — o diff `d4343dd..e72bbdb` é 78 inserções e 0 remoções em um único arquivo de teste
- **Skipped tests**: nenhum
- **Failures**: nenhuma

---

## Fix Plans

Nenhum. As duas correções do round 1 (Fix 1 Major, Fix 2 Minor) estão fechadas e verificadas por mutação. Nenhuma lacuna nova foi encontrada neste round.

Uma observação de acompanhamento, não bloqueante e já registrada no round 1: `_registrar_excecao` de `ServicoGeracaoMensagens` (`aplicacao/geracao_mensagens.py:590`) registra sem `mensagem_id` também no caminho de retomada (`_retomar_item_isolado`), mesmo quando a mensagem já existe. Não viola nenhuma AC desta história; vale a nota para quem criar a primeira **leitura** de exceções em 3.5/4.x, que precisará filtrar por `mensagem_id`/`IS NULL` como `testes/test_migracoes.py:890` demonstra.

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
| --- | --- | --- |
| REGEN-01 | ✅ Verified (round 1) | ✅ Verified |
| REGEN-02 | ✅ Verified (round 1) | ✅ Verified |
| REGEN-03 | ✅ Verified (round 1) | ✅ Verified |
| REGEN-04 | ✅ Verified (round 1) | ✅ Verified — re-derivado neste round (campo `tentativas` da `Exceção` agora discriminado no caminho de retomada) |
| REGEN-05 | ✅ Verified (round 1) | ✅ Verified |
| REGEN-06 | ✅ Verified (round 1) | ✅ Verified |
| REGEN-07 | ✅ Verified (round 1) | ✅ Verified — re-derivado neste round (o `numero_tentativa` gravado pela retomada agora tem asserção própria) |
| REGEN-08 | ✅ Verified (round 1) | ✅ Verified — re-derivado neste round |
| REGEN-09 | ⚠️ Needs Fix (teste) — mutante M7 sobrevivente | ✅ Verified — M7 morto por 2 testes; M8 morto pelo teste do Gap 2 |
| REGEN-10 | ✅ Verified (round 1) | ✅ Verified |
| REGEN-11 | ✅ Verified (round 1) | ✅ Verified |
| REGEN-12 | ✅ Verified (round 1) | ✅ Verified |

---

## Summary

**Overall**: ✅ Ready

**Spec-anchored check**: 12/12 ACs com desfecho batendo com a spec, 0 spec-precision gaps, 3/3 Edge Cases
**Sensor**: 8/8 mutantes mortos (M7 e M8 reinjetados e mortos neste round)
**Gate**: 737 backend + 253 frontend, 0 falhas; `ruff`/`pyright`/`build` limpos

**What works**: as duas lacunas do round 1 eram de discriminação de teste, e ambas foram fechadas sem tocar em uma linha de produção — o que o round 1 já havia diagnosticado corretamente e este round confirmou de forma independente. A retomada agora tem um teste por marco durável do `_retomar_item`, incluindo os dois que faltavam: "tentativa reservada sem versão gravada" (onde o número da tentativa é reconstruído do registro, e um valor errado sobrescreveria uma tentativa concluída) e "avaliação aprovada com a transição ainda não aplicada" (onde a retomada precisa completar a transição sem rechamar agente nem duplicar a linha de avaliação). O ciclo de três tentativas, os dois terminais distintos por causa, a proveniência completa sem dado sensível e a superfície acessível seguem verificados como no round 1.

**Issues found**: nenhuma nova. O item 12(a) do `STATE.md` permanece parcialmente fechado por decisão do round 1 (a `asyncio.Task` desacoplada segue sem observador de exceção) e deve continuar registrado.

**Next steps**: marcar REGEN-09 como Verified na `spec.md` e fechar a História 3.4. Nenhuma mudança de produção pendente.
