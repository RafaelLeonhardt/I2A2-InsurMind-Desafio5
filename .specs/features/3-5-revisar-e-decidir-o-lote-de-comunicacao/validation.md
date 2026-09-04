# História 3.5: Revisar e decidir o lote de comunicação — Validation

**Date**: 2026-09-04
**Spec**: `.specs/features/3-5-revisar-e-decidir-o-lote-de-comunicacao/spec.md`
**Diff range**: `7bca11d..50c8602` (6 commits, T1–T6)
**Verifier**: independent sub-agent (author ≠ verifier) — evidence re-derived from `spec.md` and the real diff, not from the author's summary

---

## Task Completion

| Task | Status | Notes |
| --- | --- | --- |
| T1 — Migração `0013_decisoes_humanas.sql` | ✅ Done | `634c8e9`; renumerada de `0011` (L-034, 4ª recorrência). Justificativa cobrada pelo `CHECK` do próprio banco |
| T2 — `RepositorioDecisoesHumanas` | ✅ Done | `0e8635b`; `salvar`/`obter_por_mensagem`, com o parâmetro `conexao` opcional (AD-012) |
| T3 — `ServicoRevisaoLote.obter_lote` | ✅ Done | `495b733`; inclui o gatilho agregado do REVISAO-01 em `ServicoGeracaoMensagens.abrir_revisao_se_lote_completo` (SPEC_DEVIATION documentado) |
| T4 — `ServicoRevisaoLote.decidir_lote` | ⚠️ Partial | `e900c6c`; funcionalmente completo, mas a metade "aprovada pelo crítico" do REVISAO-14 não tem teste discriminante (mutante M4 sobreviveu) |
| T5 — Roteador HTTP | ✅ Done | `fadc7c2`; `GET`/`POST`, hash idempotente escopado pela execução (L-027) |
| T6 — Superfície do revisor e do lote | ✅ Done | `50c8602`; colisão de schema `RespostaCriterio` → `RespostaCriterioLote` confirmada resolvida |

---

## Spec-Anchored Acceptance Criteria

### P1: Lote de revisão priorizado por atenção

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| REVISAO-01 — WHEN todas as mensagens alcançarem um terminal de conteúdo THEN a execução entra em `aguardando_revisao` e apresenta o lote com evento, regra, público, canais, aprovações agênticas e exceções | `EstadoExecucao.AGUARDANDO_REVISAO` + cabeçalho com os 6 campos | `testes/test_geracao_mensagens.py:1364` — `assert cenario.estado_execucao() is EstadoExecucao.AGUARDANDO_REVISAO`; `testes/test_revisao_lote.py:480-487` — `assert lote.evento == EVENTO` / `lote.regra_id == REGRA_ID` / `lote.total_publico_incluido == 4` / `lote.distribuicao_por_canal == (("email",1),("sms",2),("whatsapp",1))` / `lote.aprovacoes_agenticas == 3` / `lote.itens_em_excecao == 1` | ⚠️ PASS com lacuna — ver Gap 1 (janela de reinício não dispara o gatilho) |
| REVISAO-02 — The batch view SHALL ordenar itens que exigem atenção antes dos sem ressalvas | exceções → reprovação histórica → aprovação limpa → sem pendência (Tech Decision do design) | `testes/test_revisao_lote.py:414-419` — `assert [item.prioridade ...] == [PRIORIDADE_EXCECAO, PRIORIDADE_EXCECAO, PRIORIDADE_APROVACAO_LIMPA, PRIORIDADE_APROVACAO_LIMPA]`; `testes/test_revisao_lote.py:449-455` — ordem completa das 4 faixas; `testes/test_revisao_lote_api.py:226` — mesma ordem no contrato HTTP; `SuperficieRevisaoLote.test.tsx:141` — a lista renderiza na ordem recebida com o sinal de atenção por item | ✅ PASS |

### P1: Detalhe do revisor com contexto separado

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| REVISAO-03 — WHEN Marina abrir o revisor THEN exibir destinatário sintético, conteúdo, versões, verificações determinísticas, avaliações críticas, dados de origem e proveniência | os 7 blocos presentes e distintos | `testes/test_revisao_lote.py:504-535` — asserções campo a campo em `item.destinatario.*`, `item.origem.*`, `item.proveniencia.categorias_usadas/nao_usadas`, `versao.conteudo`, `versao.valida`, `versao.avaliacao.avaliacao.aprovada`; `testes/test_revisao_lote.py:583-587` — `assert primeira.valida is False and primeira.avaliacao is None` (verificação determinística ≠ crítica); `testes/test_revisao_lote.py:551-561` — as 2 versões com o veredito de cada | ✅ PASS |
| REVISAO-04 — The revisor SHALL separar visualmente destinatário, conteúdo/versionamento e contexto de IA | 3 seções visualmente distintas | `SuperficieRevisaoLote.test.tsx:181` — "separa destinatário, conteúdo/versionamento e contexto de IA em seções próprias"; `SuperficieRevisaoLote.test.tsx:205` — as duas versões da mensagem regenerada com o veredito de cada | ✅ PASS |

### P1: Decisão individual sem edição de texto

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| REVISAO-05 — WHEN Marina decidir uma mensagem em `aguardando_revisao` THEN poder aprovar/rejeitar/excluir/regenerar, e o sistema NÃO permitir edição manual do texto | 4 ações; zero campo de edição do corpo | `testes/test_revisao_lote.py:684-685` (parametrizado nos 3 terminais) — `assert cenario.estado_de(mensagem_id) is estado_esperado` **e** `assert ...listar_versoes(...)[-1].conteudo == conteudo_antes`; `testes/test_revisao_lote.py:796-799` — regenerar leva a `GERANDO`; `SuperficieRevisaoLote.test.tsx:241` — `expect(textareas).toHaveLength(1)` com `id="justificativa-decisao"` e `expect(screen.getByText(CORPO_GERADO).tagName).toBe('P')` | ✅ PASS |
| REVISAO-06 — IF confirmar rejeição/exclusão/regeneração sem justificativa THEN ação bloqueada com validação inline e rascunho preservado até concluir ou cancelar conscientemente | bloqueio antes de qualquer mutação + rascunho persistido | `testes/test_revisao_lote.py:750-756` (3 resultados × 3 formas de "vazio") — `assert cenario.decisoes.obter_por_mensagem(sem_motivo) == []` **e** `... (valida) == []` **e** `estado_execucao() is AGUARDANDO_REVISAO`; `testes/test_revisao_lote_api.py:346` — `422`; `SuperficieRevisaoLote.test.tsx:262-282` (`it.each` dos 3 rótulos) — `toHaveTextContent('Escreva a justificativa antes de confirmar esta decisão.')`, `aria-invalid="true"`, `expect(decidirLote).not.toHaveBeenCalled()`; `SuperficieRevisaoLote.test.tsx:327` — rascunho sobrevive à navegação; `:354` — só o descarte consciente limpa | ✅ PASS |
| REVISAO-07 — WHEN uma decisão humana for persistida THEN registrar perfil, data, resultado, justificativa e versão da mensagem, distinta da aprovação do crítico | 5 campos + separação de `avaliacoes_criticas` | `testes/test_revisao_lote.py:710-718` — `perfil_responsavel == PERFIL`, `resultado is REJEITAR`, `justificativa == "..."`, `versao_mensagem_id == versao_mensagem.id`, `criado_em is not None`, e `critica.agente == "critico"` na mesma versão; `testes/test_repositorio_decisoes_humanas.py:201` — as duas tabelas permanecem distintas; `testes/test_migracoes.py:928` — a migração persiste os mesmos campos | ✅ PASS |

### P1: Regeneração humana compartilhando o limite de tentativas

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| REVISAO-08 — WHEN `tentativas < 3` e regeneração pedida com justificativa THEN transição atômica para `gerando`, tentativa incrementada uma única vez, agregado volta a `processando_mensagens`, sem dupla contagem em reenvio idempotente | `EstadoMensagem.GERANDO`, `tentativa_atual == 2`, `EstadoExecucao.PROCESSANDO_MENSAGENS`, reenvio não incrementa | `testes/test_revisao_lote.py:796-799` — `estado is GERANDO`, `tentativa_atual == 2`, `decisao.estado is PROCESSANDO_MENSAGENS`; `testes/test_revisao_lote.py:821-823` — após reenvio, `tentativa_atual == 2`, `primeira == segunda`, `len(decisoes) == 1` | ✅ PASS |
| REVISAO-09 — IF a mensagem já consumiu 3 tentativas THEN regenerar indisponível com explicação acessível; aprovar/rejeitar/excluir seguem disponíveis | recusa com motivo próprio; outras 3 ações ativas | `testes/test_revisao_lote.py:884-891` — `recusadas == (DecisaoRecusada(esgotada, MOTIVO_LIMITE_DE_TENTATIVAS),)`, `aplicadas == (com_folga,)`, `decisoes.obter_por_mensagem(esgotada) == []`; `testes/test_revisao_lote.py:916-918` — a mesma mensagem é rejeitada com sucesso; `testes/test_revisao_lote.py:607-611` — `pode_regenerar is False` / `True`; `SuperficieRevisaoLote.test.tsx:365` — rádio `disabled` + explicação via `aria-describedby` e os outros 3 `toBeEnabled()` | ✅ PASS |
| REVISAO-10 — WHEN houver regeneração humana ativa THEN o agregado só volta a `aguardando_revisao` quando nenhuma permanecer ativa, e nenhuma conclusão/simulação antes de decisão terminal de toda revisável (terminais de conteúdo não bloqueiam) | `PROCESSANDO_MENSAGENS` enquanto ativa; `AGUARDANDO_REVISAO` enquanto houver revisável pendente | `testes/test_revisao_lote.py:1272-1275` — com uma aprovada e uma regenerando: `decisao.estado is PROCESSANDO_MENSAGENS`, `estado_execucao() is PROCESSANDO_MENSAGENS`; `testes/test_revisao_lote.py:1182-1183` — revisável pendente mantém `AGUARDANDO_REVISAO`; `testes/test_geracao_mensagens.py:1383` — uma mensagem em `gerando` impede a abertura; `testes/test_revisao_lote.py:1216` — o agregado volta a `AGUARDANDO_REVISAO` só quando o ciclo da versão nova termina; `testes/test_revisao_lote.py:1061` — decisão recusada com o agregado fora de revisão | ✅ PASS |
| REVISAO-11 — WHEN regeneração criar nova versão THEN a versão anterior e a solicitação humana permanecem auditáveis, sem aprovação humana para nenhuma delas, e a nova versão exige decisão própria | 2 versões + 2 decisões (regenerar → aprovar), cada uma ligada à sua versão | `testes/test_revisao_lote.py:1213-1222` — `[versao.numero_tentativa ...] == [1, 2]`, `decisoes == [REGENERAR]`, `decisoes[0].versao_mensagem_id == versoes[0].id`; `testes/test_revisao_lote.py:1240-1246` — `[REGENERAR, APROVAR]` e a última decisão aponta para `versoes[-1].id`; `testes/test_repositorio_decisoes_humanas.py:169` — o histórico preserva regeneração + decisão seguinte | ✅ PASS |

### P1: Decisão em lote atômica e conclusão do agregado

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| REVISAO-12 — WHEN decisão em lote THEN todas as válidas na mesma transação ou nenhuma, e conflito de `versao_esperada` retorna `409` sem efeito parcial | zero decisão persistida; status `409` | `testes/test_revisao_lote.py:949-953` — leitura direta do banco pelos repositórios reais: `estado_de(...) is AGUARDANDO_REVISAO` para as 3 e `decisoes.obter_por_mensagem(...) == []` para as 3; `testes/test_revisao_lote.py:982-987` — o incremento de tentativa já gravado também volta atrás (`tentativa_atual == 1`); `testes/test_revisao_lote_api.py:336-343` — `status_code == 409`, `codigo == "conflito_versao"`, `GET` seguinte com todos em `aguardando_revisao` e `decisoes == []`; `testes/test_repositorio_decisoes_humanas.py:237` — a decisão gravada na transação do chamador desaparece no `ROLLBACK` | ✅ PASS |
| REVISAO-13 — WHEN todas revisáveis decididas e nenhuma aprovada THEN `concluida` sem simulação, com motivos consultáveis | `EstadoExecucao.CONCLUIDA` + justificativas legíveis | `testes/test_revisao_lote.py:1088-1098` — `decisao.estado is CONCLUIDA`, `mensagens_aprovadas == ()`, `estado_execucao() is CONCLUIDA`, e as justificativas de rejeição/exclusão recuperadas pelo `obter_lote`; `testes/test_revisao_lote_api.py:531` — mesmo desfecho pela rota | ✅ PASS |
| REVISAO-14 — WHEN ao menos uma aprovada e todas decididas THEN `aguardando_confirmacao` contendo apenas mensagens aprovadas pelo crítico **e** por Marina | `EstadoExecucao.AGUARDANDO_CONFIRMACAO`; conjunto = interseção das duas aprovações | `testes/test_revisao_lote.py:1155-1163` — `estado is AGUARDANDO_CONFIRMACAO`, `mensagens_aprovadas == (aprovada,)` (o item aprovado pelo crítico e **rejeitado por Marina** fica de fora), `em_excecao not in mensagens_aprovadas`; `testes/test_revisao_lote_api.py:266` — mesmo desfecho pela rota | ⚠️ **GAP parcial** — só a metade "Marina" é discriminada. Nenhum teste semeia o caso inverso (aprovado por Marina, **não** aprovado pelo crítico): o mutante M4 removeu `and self._aprovada_pelo_critico(...)` de `revisao_lote.py:645` e **sobreviveu**. Ver Gap 2 |

**Status**: ⚠️ 13/14 ACs com outcome de spec batido e evidência `file:line`; REVISAO-14 coberto pela metade; REVISAO-01 com uma janela de reinício descoberta. 0 spec-precision gaps (a spec desta história define outcomes precisos em todos os 14 critérios).

---

## Edge Cases

- [x] **Edge Case 1** — lote inteiro em `falhou_conteudo`/`falhou_integracao_ia` ainda passa por `aguardando_revisao` e conclui sem simulação ao reconhecimento de Marina: `testes/test_geracao_mensagens.py:1404` (`assert cenario.estado_execucao() is EstadoExecucao.AGUARDANDO_REVISAO` com todas em `FALHOU_INTEGRACAO_IA`) + `testes/test_revisao_lote.py:1121-1123` (envio sem decisões → `CONCLUIDA`).
- [x] **Edge Case 2** — item já decidido é recusado com motivo sem impedir as demais válidas do mesmo envio: `testes/test_revisao_lote.py:1012-1015` — `recusadas == (DecisaoRecusada(ja_decidida, MOTIVO_MENSAGEM_JA_DECIDIDA),)`, `aplicadas == (pendente,)`, `estado_de(pendente) is APROVADA`; `testes/test_revisao_lote_api.py:487` no contrato HTTP.
- [x] **Edge Case 3** — regeneração ativa bloqueia decisão/confirmação até a guarda ser satisfeita: `testes/test_revisao_lote.py:1044` (`EstadoNaoRevisavel` com o agregado em `processando_mensagens`) + `testes/test_revisao_lote_api.py:457` (`409`).

---

## Discrimination Sensor

Scratch: `git worktree add` em diretório temporário (nunca `git stash`). Baseline `git status --porcelain` vazio antes e depois; `git worktree list` de volta a uma única árvore; `HEAD` inalterado em `50c8602`.

| # | File:line | Description | Killed? |
| --- | --- | --- | --- |
| M1 | `aplicacao/geracao_mensagens.py:507` | Removida a guarda `any(em_ciclo_de_conteudo(...))` — o gatilho passa a abrir a revisão com uma mensagem ainda em `gerando` | ✅ Killed — `test_execucao_permanece_processando_enquanto_uma_mensagem_segue_no_ciclo` |
| M2 | `aplicacao/geracao_mensagens.py:513` | Colisão de nomes: `EstadoExecucao.AGUARDANDO_REVISAO` → `EstadoMensagem.AGUARDANDO_REVISAO` no alvo da transição do agregado | ⚠️ **Sobreviveu à suíte** (os dois membros de `StrEnum` têm o mesmo valor `"aguardando_revisao"`, e `transicionar` grava `novo_estado.value` — nenhum teste comportamental pode distingui-los) / ✅ **Morto pelo gate Full**: `pyright` acusa `reportArgumentType` em `geracao_mensagens.py:513` |
| M3 | `adaptadores/persistencia/transacao.py:37` | `ROLLBACK` → `COMMIT` no `except` da transação única (atomicidade só aparente) | ✅ Killed — `test_conflito_de_versao_em_um_item_aborta_o_envio_inteiro`, `test_conflito_de_versao_desfaz_ate_a_regeneracao_ja_gravada_na_transacao`, `test_post_com_conflito_de_versao_devolve_409_sem_efeito_parcial` |
| M4 | `aplicacao/revisao_lote.py:645` | Removido `and self._aprovada_pelo_critico(registro.id)` — a aprovação dupla do REVISAO-14 vira só a decisão de Marina | ❌ **Survived** → fix task (Gap 2) |
| M5 | `aplicacao/geracao_mensagens.py:512` | O gatilho passa a decidir `CONCLUIDA` quando nenhuma mensagem está em `aguardando_revisao` (invade o escopo de `decidir_lote`) | ✅ Killed — `test_lote_inteiro_em_excecao_ainda_abre_a_revisao` |
| M6 | `adaptadores/http/revisao_lote.py:392` | Hash de idempotência deixa de incluir o identificador da execução | ✅ Killed — `test_post_com_a_mesma_chave_em_outra_execucao_devolve_409` |
| M7 | `aplicacao/revisao_lote.py:840` | Item em exceção perde a prioridade de atenção (`PRIORIDADE_EXCECAO` → `PRIORIDADE_SEM_PENDENCIA`) | ✅ Killed — `test_lote_ordena_itens_em_excecao_antes_dos_aprovados`, `test_lote_ordena_reprovacao_historica_entre_excecao_e_aprovacao_limpa`, `test_get_devolve_o_lote_ordenado_com_todos_os_campos_do_ac` |

**Sensor depth**: P0-full (7 mutações — atomicidade transacional e integridade de estado agregado justificam ≥5).
**Result**: 5/7 mortos pela suíte, 1/7 morto só pelo gate estático (M2), 1/7 sobrevivente (M4) — ❌ FAIL.

### Sonda adicional do Verificador (não é mutação — é uma prova de lacuna)

Teste descartável escrito no worktree de rascunho: uma execução em `processando_mensagens` cujas mensagens já estão **todas** em terminal de conteúdo, submetida a `retomar_mensagens_pendentes` (o caminho de boot de 2.6/3.4). Resultado observado: `ESTADO APOS BOOT: processando_mensagens` — o gatilho nunca roda. Ver Gap 1.

---

## Verificação empírica das três alegações de maior carga

1. **Gatilho do REVISAO-01 (nenhum terceiro caminho)** — confirmado por rastreamento completo: em produção só há dois pontos de entrada no ciclo (`gerar_lote`, disparado por `adaptadores/http/preflight_ia.py:258`, e `retomar_mensagens_pendentes`, disparado por `aplicacao/gerenciador_execucoes.py:397` e por `adaptadores/http/revisao_lote.py:579`). Ambos passam por `_gerar_item_isolado`/`_retomar_item_isolado`, e cada um chama `abrir_revisao_se_lote_completo` como última instrução, fora do `try` do item. A regeneração humana **não** cria um segundo mecanismo: `acionar_regeneracao` reentra pela retomada de 3.4. **Porém** o gatilho vive *dentro* do corpo do laço por item: quando o laço não itera nada, ele nunca roda (Gap 1).
2. **Colisão `EstadoExecucao.AGUARDANDO_REVISAO` × `EstadoMensagem.AGUARDANDO_REVISAO`** — auditados os 12 pontos de uso dos três arquivos novos/alterados: todo predicado de nível-mensagem usa `EstadoMensagem` e todo alvo/guarda de nível-execução usa `EstadoExecucao`. O código está correto. O risco é real mas estruturalmente invisível para testes (M2): `pyright` é o único discriminador, e ele já é obrigatório no gate Full/Build.
3. **Isolamento de transação entre conexões DuckDB** — verificado empiricamente pelo Verificador, não aceito da alegação (duckdb 1.5.5, duas conexões ao mesmo arquivo no mesmo processo): a segunda conexão lê `0` linhas durante a transação aberta da primeira, seu próprio `INSERT` é aceito e **sobrevive ao `ROLLBACK`** da primeira (o arquivo final contém só a linha da segunda). A alegação é tecnicamente correta e a adição do parâmetro `conexao` é necessária, não decorativa. Todas as escritas de `_aplicar`/`_aplicar_item` recebem a conexão da transação (`revisao_lote.py:592, 595, 607-631`); as únicas leituras em conexão própria acontecem **antes** de `transacao.executar` ou **depois** do `COMMIT` — nenhum caminho abre uma segunda conexão dentro da transação.
4. **Regressão nos chamadores anteriores (2.2/3.2/3.4)** — o parâmetro é opcional com `default=None` e o corpo cai no `abrir_conexao` original; suíte completa verde (825), nenhum teste apagado ou enfraquecido no diff (`git diff` não contém nenhuma linha `-def test_`), contagem por arquivo sem regressão. **Zero regressões.**
5. **Os dois modos de atomicidade são distintos e verificáveis** — sim: item já terminal sai por `_recusa_de` (`revisao_lote.py:556`) *antes* da transação, e as demais decisões são aplicadas (`test_item_ja_decidido_e_recusado_sem_impedir_as_demais_do_mesmo_envio:1012`); `versao_esperada` desatualizada só é detectada *dentro* da transação e levanta `ConflitoVersaoDecisao` após percorrer todos os itens, abortando tudo (`test_conflito_de_versao_em_um_item_aborta_o_envio_inteiro:949`, com leitura direta do banco). M3 mata os dois testes de conflito e não toca os de recusa por item — a distinção é comportamental, não apenas documental.

---

## Code Quality

| Principle | Status |
| --- | --- |
| Minimum code | ✅ |
| Surgical changes | ✅ — a extensão dos repositórios anteriores é um parâmetro opcional + um `contextmanager` de 6 linhas por repositório, sem alterar nenhum caminho existente |
| No scope creep | ✅ |
| Matches patterns | ✅ — `conexao` opcional segue `RepositorioElegibilidades.copiar_para_execucao` (AD-012); transação única segue `aplicacao/restauracao.py` (AD-005); hash idempotente segue `preflight_ia.py` (`f2d9308`, L-027) |
| Spec-anchored outcome check | ⚠️ — REVISAO-14 assertado só na metade (ver Gap 2) |
| Per-layer Coverage Expectation met | ✅ domínio 1:1 com ACs; rotas com feliz + `404`/`409`/`422` + `409` de conflito e de idempotência |
| Every test maps to a spec requirement — no unclaimed tests | ✅ — cada docstring de teste cita o `REVISAO-NN`, o Edge Case ou o AD que justifica |
| Documented guidelines followed | ✅ — `AGENTS.md`/`README.md`; piso de teste de `test_restauracao.py` (transação única) e `test_repositorio_regras.py` (concorrência otimista) respeitado, com repositórios reais sobre banco migrado |
| Deviations marked per project convention | ❌ — ver Gap 3 |

---

## Gate Check

- **Gate command (Build)**: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright` + `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`
- **Result**: backend **825 passed, 0 failed, 0 skipped**; `ruff` "All checks passed!"; `pyright` "0 errors, 0 warnings"; frontend **268 passed (29 arquivos), 0 failed**; `oxlint` exit 0 (só avisos `set-state-in-effect` pré-existentes em 5 superfícies, padrão do projeto); `tsc -b && vite build` OK.
- **Contrato**: `npm run verificar-tipos-api` executado contra o backend real (banco de rascunho migrado, `127.0.0.1:8000`) → "está sincronizado com o contrato OpenAPI do backend em execução". `RespostaCriterioLote` confirmado distinto de `RespostaCriterio` (`avaliacao_risco.py:19`), `RespostaCriterioElegibilidade` e `RespostaCriterioTeste` no `openapi.json` e em `tipos-gerados.ts` — nenhum nome qualificado por módulo.
- **Test count before feature** (`7bca11d`, medido em worktree): 737 backend / 253 frontend
- **Test count after feature** (`50c8602`): 825 backend / 268 frontend
- **Delta**: +88 backend, +15 frontend
- **Skipped tests**: nenhum
- **Test integrity**: nenhuma linha `-def test_` / `-it(` no diff — nenhum teste removido nem asserção enfraquecida

---

## Fix Plans

### Fix 1 — Execução presa em `processando_mensagens` após reinício (Gap 1)

- **Root cause**: `abrir_revisao_se_lote_completo` só é chamado *dentro* do corpo do laço de `retomar_mensagens_pendentes` (`aplicacao/geracao_mensagens.py:467-470` → `:481`). Se o processo reinicia depois que a última mensagem alcançou seu terminal de conteúdo mas antes de o gatilho rodar (ou se o gatilho falhou e foi engolido pelo `except` de `:515`), o boot encontra a execução em `processando_mensagens`, `retomar_mensagens_pendentes` não acha nenhuma mensagem em `gerando`/`criticando`, o laço não executa, e o gatilho nunca dispara. A execução fica presa para sempre e o lote nunca abre para Marina — violação literal do REVISAO-01.
- **Reproduzido**: sonda do Verificador em worktree de rascunho — `ESTADO APOS BOOT: processando_mensagens` (esperado `aguardando_revisao`).
- **Fix task**: chamar `self.abrir_revisao_se_lote_completo(execucao_id)` uma vez ao final de `retomar_mensagens_pendentes`, fora do laço (a idempotência já está garantida pela guarda `snapshot.estado is not PROCESSANDO_MENSAGENS` de `:510`). Acrescentar um teste em `testes/test_geracao_mensagens.py` que semeia uma execução em `processando_mensagens` com todas as mensagens já em terminal de conteúdo e afirma `estado_execucao() is EstadoExecucao.AGUARDANDO_REVISAO` após a retomada.
- **Priority**: Major

### Fix 2 — REVISAO-14: metade "aprovada pelo crítico" sem teste discriminante (Gap 2)

- **Root cause**: `_mensagens_aprovadas` (`aplicacao/revisao_lote.py:641-646`) exige `EstadoMensagem.APROVADA` **e** `_aprovada_pelo_critico`, mas nenhum teste semeia uma mensagem em `aguardando_revisao` cuja última versão **não** foi aprovada pelo crítico. Removida a segunda condição, toda a suíte permanece verde (M4).
- **Fix task**: em `testes/test_revisao_lote.py`, semear uma mensagem com `tentativas=((True, False),)` e `estado=EstadoMensagem.AGUARDANDO_REVISAO`, aprová-la por `decidir_lote`, e afirmar que ela **não** aparece em `resultado.mensagens_aprovadas` (e, se for a única, que o agregado não vai a `aguardando_confirmacao`). Se a equipe concluir que o estado é inalcançável pela máquina de estados e a condição é defesa em profundidade, registrar essa decisão explicitamente no docstring em vez de deixá-la sem prova.
- **Priority**: Major (mutante sobrevivente — `validate.md` §5 exige fix task antes de fechar a história)

### Fix 3 — Desvios de `design.md` sem marcação (Gap 3)

- **Root cause**: `design.md:44` declara `RepositorioMensagens` "Reusado **sem alteração**" e `:45` o mesmo para `RepositorioExecucaoPreventiva`, mas ambos tiveram assinaturas estendidas com o parâmetro `conexao`; e `TransacaoDuckDB` (`adaptadores/persistencia/transacao.py`, componente novo) não aparece na seção **Components** do `design.md`. Nenhum dos dois carrega o marcador `SPEC_DEVIATION` que o projeto aplica consistentemente a divergências bem menores (`agente_redator.py:8`, `repositorio_contextos_agente.py:7`, `montador_contexto_agente.py:11`).
- **Fix task**: acrescentar o marcador `SPEC_DEVIATION` nos dois repositórios e em `transacao.py` (a justificativa técnica já está escrita nos docstrings — falta só o marcador que a torna rastreável), ou atualizar `design.md`.
- **Priority**: Minor (documentação/rastreabilidade; a mudança em si está correta e verificada)

### Observações não-bloqueantes (não viram fix task)

- `montar_portas_revisao.acionar_regeneracao` (`adaptadores/http/revisao_lote.py:576-581`) dispara `asyncio.create_task` sem `except` amplo nem callback que leia `.exception()` — mesma forma do risco (12)(a) já registrado no `STATE.md` para 3.2. Aqui o impacto é menor (cada item da retomada já tem `try/except` próprio), mas o padrão se repete.
- `src/frontend/src/api/revisaoLote.ts` (391 linhas de tradução do contrato) não tem teste próprio; o teste de superfície mocka `getLoteRevisao`/`decidirLote`. Coerente com `avaliacaoCritica.ts`, `mensagens.ts` e `preparacaoIa.ts` (3.1–3.3) e não exigido pela Test Coverage Matrix — registrado como padrão acumulado, não como desvio desta história.
- `SuperficieRevisaoLote` é a 8ª superfície sem entrada em `App.tsx`/`PerfilContexto.tsx` — mesma pendência do risco (9) do `STATE.md`.

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
| --- | --- | --- |
| REVISAO-01 | Implementing | ❌ Needs Fix (Gap 1 — janela de reinício) |
| REVISAO-02 | Implementing | ✅ Verified |
| REVISAO-03 | Implementing | ✅ Verified |
| REVISAO-04 | Implementing | ✅ Verified |
| REVISAO-05 | Implementing | ✅ Verified |
| REVISAO-06 | Implementing | ✅ Verified |
| REVISAO-07 | Implementing | ✅ Verified |
| REVISAO-08 | Implementing | ✅ Verified |
| REVISAO-09 | Implementing | ✅ Verified |
| REVISAO-10 | Implementing | ✅ Verified |
| REVISAO-11 | Implementing | ✅ Verified |
| REVISAO-12 | Implementing | ✅ Verified |
| REVISAO-13 | Implementing | ✅ Verified |
| REVISAO-14 | Implementing | ❌ Needs Fix (Gap 2 — mutante M4 sobrevivente) |

---

## Summary

**Overall**: ❌ Not Ready — 2 fix tasks Major + 1 Minor antes de fechar a história

**Spec-anchored check**: 13/14 ACs com outcome de spec batido e evidência `file:line`; 1 coberto pela metade (REVISAO-14); 0 spec-precision gaps
**Sensor**: 7 mutações injetadas — 5 mortas pela suíte, 1 morta só pelo `pyright` do gate (M2), 1 sobrevivente (M4)
**Gate**: 825 backend + 268 frontend, 0 falhas; `ruff`/`pyright`/`oxlint`/`build`/`verificar-tipos-api` limpos

**What works**:
- A transação única é real, não aparente: verifiquei empiricamente o isolamento entre conexões do DuckDB 1.5.5 e confirmei que toda escrita de `decidir_lote` roda na conexão da transação. `ROLLBACK` → `COMMIT` (M3) mata três testes.
- Os dois modos de recusa (item já terminal vs. conflito de versão) são comportamentalmente distintos e provados por leitura direta do banco, não só pelo `GET` da própria API.
- O gatilho agregado do REVISAO-01 é genuinamente o único ponto por onde passa todo desfecho terminal de mensagem: rastreei os três disparadores de produção e nenhum caminho alternativo alcança um terminal sem passar por `_gerar_item_isolado`/`_retomar_item_isolado`. A regeneração humana reentra pelo mesmo mecanismo de 3.4, não por um segundo.
- A extensão dos repositórios de 2.2/3.2/3.4 é aditiva e não regrediu nada: 737 → 825 testes, nenhum removido, nenhum enfraquecido.
- O ciclo completo de regeneração humana (decidir → `gerando` → grafo real → nova versão → `aguardando_revisao` → segunda decisão → `aguardando_confirmacao`) é exercido ponta a ponta contra persistência real em `test_ciclo_completo_de_regeneracao_humana_devolve_o_lote_a_revisao` — não é um teste raso.
- A colisão de nomes `RespostaCriterio`/`RespostaCriterioLote` está de fato resolvida e o contrato TypeScript está sincronizado com o backend em execução.

**Issues found**:
1. Gap 1 (Major) — reinício com todas as mensagens já terminais deixa a execução presa em `processando_mensagens`; o gatilho mora dentro do laço por item e não roda com o laço vazio. Fix: uma chamada ao final de `retomar_mensagens_pendentes` + um teste.
2. Gap 2 (Major) — mutante M4 sobrevivente: a metade "aprovada pelo crítico" do REVISAO-14 nunca é discriminada por teste. Fix: um teste que semeia o caso inverso.
3. Gap 3 (Minor) — três divergências reais de `design.md` sem o marcador `SPEC_DEVIATION` que o projeto usa por convenção.

**Next steps**: rotear os Fix 1–3 a um implementador e re-despachar o Verificador (iteração 1 de no máximo 3).
