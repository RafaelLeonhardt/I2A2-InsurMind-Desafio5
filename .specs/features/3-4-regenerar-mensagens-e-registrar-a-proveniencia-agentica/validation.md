# História 3.4: Regenerar mensagens e registrar a proveniência agêntica — Validation

## Validation Verdict: FAIL ❌

**Date**: 2026-09-04
**Spec**: `.specs/features/3-4-regenerar-mensagens-e-registrar-a-proveniencia-agentica/spec.md`
**Diff range**: `ce964f8..70ce8af` (6 commits, um por task)
**Verifier**: sub-agente independente (author ≠ verifier), re-derivado da `spec.md` e do diff, sem confiar no relato do autor

**Por que FAIL**: 12/12 ACs e 3/3 Edge Cases cobertos com evidência `file:line` e desfecho batendo com a spec; gate verde (735 backend + 253 frontend, ruff/pyright limpos). O único bloqueio é o **sensor de discriminação**: 1 de 7 mutantes sobreviveu, exatamente sobre a afirmação de maior risco da história (a numeração de tentativa reconstruída na retomada). Não há defeito de produção — o código está correto; falta a asserção que o prova. Regra do skill: mutante sobrevivente vira fix task antes de a história fechar.

---

## Task Completion

| Task | Status | Notes |
| --- | --- | --- |
| T1 — Migração `mensagem_id` em `excecoes_operacionais` | ✅ Done | `e303d42`. Renumerada para `0012` (`0009`/`0010`/`0011` consumidas por 3.1/3.2/3.3) — SPEC_DEVIATION declarada no próprio `.sql`. Contabilidade de `schema_migracoes` conferida: `testes/test_migracoes.py:87` — `assert resultado.versoes_aplicadas == (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12)` e o registro `(12, "excecoes mensagem")`; `testes/test_inicializador.py:73` — `assert versoes_registradas(caminho) == [1, ..., 12]`. |
| T2 — `RepositorioMensagens.incrementar_tentativa` | ✅ Done | `95a59c0`. Limite cobrado no próprio `UPDATE` (`tentativa_atual < 3` no `WHERE`), não só na leitura anterior. |
| T3 — Ciclo automático no `GrafoGeracaoMensagem` | ✅ Done | `13af722`. Nós `regenerar`/`esgotar` + 3 arestas condicionais (`START`, pós-`gerar`, pós-`criticar`). |
| T4 — `retomar_pendentes` estendido | ✅ Done | `c57d10a`. Ligado de verdade no boot (ver item 12(b) abaixo). |
| T5 — `GET /mensagens/{id}/proveniencia` | ✅ Done | `e886218`. `openapi.json` regenerado, `test_openapi_sincronizado.py` verde. |
| T6 — Superfície de acompanhamento do ciclo | ✅ Done | `70ce8af`. 6 categorias distintas, foco preservado, `aria-live`. |

---

## Spec-Anchored Acceptance Criteria

### P1: Regeneração automática limitada a três tentativas

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| REGEN-01: WHEN reprovada (crítico ou validação determinística recuperável) e há tentativa disponível THEN o redator recebe os motivos e gera nova versão, histórico anterior imutável e consultável | redator rechamado com os motivos categorizados; versão anterior preservada | `testes/test_grafo_geracao_mensagem.py:472` — `assert redator.motivos_recebidos == [(), (MotivoCritica(CategoriaCritica.TOM, "O texto usa tom alarmista."),)]`; `testes/test_geracao_mensagens.py:941` — `assert cenario.redator.motivos_recebidos == [(), (motivo,)]`; `testes/test_geracao_mensagens.py:906` — `assert versoes[0][1] == f'{{"corpo": "{CORPO_VALIDO} versao um"}}'` (versão 1 intacta ao lado da 2); ramo determinístico em `testes/test_grafo_geracao_mensagem.py:493` — `assert redator.motivos_recebidos[1] == (MotivoCritica(CategoriaCritica.ADEQUACAO_CANAL, "limite_excedido:corpo:161:160"),)`; consulta do histórico em `testes/test_proveniencia_api.py:171` — `assert corpo["tentativas"][0]["avaliacao"]["aprovada"] is False` | ✅ PASS |
| REGEN-02: The system SHALL permitir no máximo três tentativas totais por mensagem | 4ª tentativa nunca reservada; limite = 3 | `testes/test_repositorio_mensagens.py:258` — `with pytest.raises(LimiteTentativasExcedido)` + `assert registro.tentativa_atual == 3` e `assert registro.versao == 3` (linha não mutada); `testes/test_grafo_geracao_mensagem.py:564` — `assert redator.chamadas == MAXIMO_TENTATIVAS_MENSAGEM` e `assert critico.chamadas == MAXIMO_TENTATIVAS_MENSAGEM`; `CicloFalso.preparar_regeneracao` (`testes/test_grafo_geracao_mensagem.py:159`) aborta em uma 4ª reserva | ✅ PASS |
| REGEN-03: WHEN uma tentativa produzir aprovação válida THEN o ciclo encerra imediatamente, sem consumir tentativas adicionais | parada na tentativa 1, 2 **e** 3 | tentativa 1: `testes/test_grafo_geracao_mensagem.py:515` — `assert redator.chamadas == 1` + `assert ciclo.tentativa_atual == 1`; tentativa 2: `:530` — `assert redator.chamadas == 2` + `assert ciclo.estado is EstadoMensagem.AGUARDANDO_REVISAO`; tentativa 3: `:546` — `assert [tentativa for tentativa, _ in ciclo.versoes] == [1, 2, 3]` + `assert ciclo.excecoes == []` | ✅ PASS |
| REGEN-04: IF a terceira tentativa também for reprovada THEN `falhou_conteudo` + `Exceção`, fora do lote simulável | estado `falhou_conteudo`, exceção com causa/tentativas/impacto correlacionada por `mensagem_id` | `testes/test_geracao_mensagens.py:960` — `assert mensagem.estado is EstadoMensagem.FALHOU_CONTEUDO` + `assert cenario.excecoes.registradas == [(EXECUCAO_ID, f"falhou_conteudo:{incluido.id}:seguranca", 3, IMPACTO_ITEM_FORA_DO_LOTE)]` + `assert cenario.excecoes.mensagens_correlacionadas == [mensagem.id]`; `testes/test_grafo_geracao_mensagem.py:564` — `assert ciclo.excecoes == [("falhou_conteudo", 3, (MotivoCritica(CategoriaCritica.TOM, "Promete indenização integral."),))]`; distinção execução↔mensagem em SQL: `testes/test_migracoes.py:890` — `assert [causa for (causa,) in da_execucao] == ["falhou_coleta"]` sob `WHERE execucao_id = ? AND mensagem_id IS NULL` | ✅ PASS |

**Nota**: "não poder integrar o lote simulável" é observável nesta história pelo terminal `falhou_conteudo` + o impacto `IMPACTO_ITEM_FORA_DO_LOTE`; o portão de composição do lote simulável em si é da História 3.6. Não é lacuna: a spec não define outro observável nesta história.

### P1: Isolamento de falha de integração por mensagem

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| REGEN-05: IF falha não recuperada da OpenAI em geração **ou** crítica com transporte esgotado THEN somente a mensagem afetada alcança `falhou_integracao_ia` | `falhou_integracao_ia`, distinto de `falhou_conteudo`, nos **dois** nós | nó `gerar` (grafo): `testes/test_grafo_geracao_mensagem.py:630` — `assert ciclo.estado is EstadoMensagem.FALHOU_INTEGRACAO_IA` + `assert ciclo.estado is not EstadoMensagem.FALHOU_CONTEUDO` + `assert ciclo.tentativa_atual == 1`; nó `gerar` (persistência real): `testes/test_geracao_mensagens.py:487` — `assert por_item[com_falha.id].estado is EstadoMensagem.FALHOU_INTEGRACAO_IA`; nó `criticar` (grafo, na 3ª tentativa): `testes/test_grafo_geracao_mensagem.py:646` — `assert ciclo.tentativa_atual == 3` + `assert ciclo.estado is EstadoMensagem.FALHOU_INTEGRACAO_IA`; nó `criticar` (persistência real): `testes/test_geracao_mensagens.py:806` e `:987` — `assert cenario.excecoes.mensagens_correlacionadas == [mensagem.id]` | ✅ PASS |
| REGEN-06: WHILE uma mensagem estiver em `falhou_integracao_ia` THEN as demais alcançam seus próprios terminais, sem bloqueio cruzado | outros itens chegam a `aguardando_revisao`/`falhou_conteudo` | `testes/test_geracao_mensagens.py:487` — `assert por_item[seguinte.id].estado is EstadoMensagem.AGUARDANDO_REVISAO`; terminais mistos: `testes/test_geracao_mensagens.py:873` — `assert por_item[reprovado.id].estado is EstadoMensagem.FALHOU_CONTEUDO` + `assert por_item[aprovado.id].estado is EstadoMensagem.AGUARDANDO_REVISAO` + `assert por_item[aprovado.id].tentativa_atual == 1`; falha técnica fora do grafo: `testes/test_geracao_mensagens.py:1005` — `assert mensagens[0].estado is EstadoMensagem.AGUARDANDO_REVISAO` depois de o item anterior levantar `RuntimeError`; retomada: `testes/test_geracao_mensagens.py:1232` | ✅ PASS |

### P1: Proveniência completa e retomada sem repetição

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| REGEN-07: WHEN a proveniência de qualquer versão/avaliação for consultada THEN apresenta agente, modelo, versão do prompt, categorias de entrada, saída, avaliação, tentativa, duração e métricas de uso | os 9 nomes do AC, por tentativa | `testes/test_proveniencia_api.py:127` — `assert primeira["agente"] == "redator"`, `assert primeira["modelo"] == "gpt-4o-mini"`, `assert primeira["versao_prompt"] == "v1"`, `assert corpo["categorias_entrada"]["usadas"] == list(CATEGORIAS_USADAS)`, `assert primeira["saida"] == {"assunto": None, "corpo": "Alerta enfático demais."}`, `assert primeira["avaliacao"]["aprovada"] is False`, `assert primeira["numero_tentativa"] == 1`, `assert primeira["duracao_ms"] == 742.5`, `assert primeira["tokens_entrada"] == 210` e `assert primeira["tokens_saida"] == 64` | ✅ PASS |
| REGEN-08: The provenance record SHALL não conter chave, contato, prompt completo em log ou informação sensível | ausência literal de chave/nome/telefone/instrução de sistema | `testes/test_proveniencia_api.py:189` — `assert CHAVE_OPENAI not in bruto`, `assert NOME_SEGURADO not in bruto`, `assert TELEFONE_SEGURADO not in bruto`, `assert INSTRUCAO_SISTEMA not in bruto`, `assert "prompt" not in bruto.lower().replace("versao_prompt", "")` | ✅ PASS |
| REGEN-09: WHEN o runner retomar após reinício THEN continua do último marco durável sem repetir tentativa já concluída | tentativa 2 reprovada → prossegue na 3, sem refazer 1 nem 2 | `testes/test_geracao_mensagens.py:1075` (DuckDB real + serviço reinstanciado) — `assert reiniciado.redator.canais_chamados == [Canal.SMS]` (uma única chamada), `assert [numero for numero, _, _ in versoes] == [1, 2, 3]`, `assert versoes[0][1] == f'{{"corpo": "{CORPO_VALIDO} tentativa 1"}}'` e `assert versoes[1][1] == ... tentativa 2`, `assert mensagem.tentativa_atual == 3`; 3ª já reprovada: `:1100` — `assert reiniciado.redator.canais_chamados == []` + `assert mensagem.estado is EstadoMensagem.FALHOU_CONTEUDO`; sem versão: `:1121`; em `criticando` sem avaliação: `:1141` — `assert reiniciado.critico.chamadas == 1` + `assert reiniciado.redator.canais_chamados == []`; delegação no boot: `testes/test_gerenciador_execucoes.py:549` — `assert geracao.retomadas == [execucao_id]` e escopo em `:566` — `assert geracao.retomadas == []` | ⚠️ PASS com lacuna de sensor (mutante M7, ver abaixo) |
| REGEN-10: The system SHALL nunca reabrir um estado terminal de mensagem já alcançado | 5 terminais, linha não mutada, nenhuma versão nova, nenhuma chamada à OpenAI | `testes/test_geracao_mensagens.py:1185` (parametrizado em `falhou_conteudo`, `falhou_integracao_ia`, `simulada_entregue`, `excluida`, `rejeitada`) — `assert depois.versao == antes.versao`, `assert depois.tentativa_atual == antes.tentativa_atual`, `assert _versoes_persistidas(tmp_path, mensagem_id) == []`, `assert reiniciado.redator.canais_chamados == []`; `aguardando_revisao` (não terminal, mas humano) em `:1211`; no repositório: `testes/test_repositorio_mensagens.py:298` — `with pytest.raises(TransicaoMensagemInvalida)` + `assert registro.tentativa_atual == 1` | ✅ PASS |

### P2: Acompanhamento acessível do ciclo por item

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| REGEN-11: WHEN tentativas e mensagens mudarem de estado THEN a interface mostra etapa, tentativa atual, limite, aprovações e exceções por item | "Tentativa N de 3" por item + etapa + contagem de aprovações/exceções | `SuperficieGeracaoMensagens.test.tsx:192` — `expect(await screen.findByText('Tentativa 2 de 3')).toBeInTheDocument()` e `expect(screen.getByText('Tentativa 3 de 3'))`; etapa por item: `:210` — `expect(aprovada).toHaveAttribute('data-categoria', 'aprovada')` / `reprovada` / `excecao`; agregados: `:235` — `expect(await screen.findByText('1 aprovadas pelo crítico, 2 em exceção'))`. O limite vem do backend (`RespostaMensagem.limite_tentativas`, `adaptadores/http/mensagens.py:71`), não de constante da UI | ✅ PASS |
| REGEN-12: The interface SHALL não mover o foco inesperadamente nem depender somente de cor | `document.activeElement` igual antes e depois; texto+ícone+cor distintos | foco no botão: `SuperficieGeracaoMensagens.test.tsx:249` — `expect(document.activeElement).toBe(focadoAntes)` e `expect(document.activeElement).toBe(botao)`; foco fora da lista: `:270` — `expect(document.activeElement).toBe(principal)`; região viva: `:290` — `expect(lista).toHaveAttribute('aria-live', 'polite')`; três sinais (L-024): `:210` — rótulos distintos + `[data-icone-nome="thumbs-up"]`/`"prohibit"`/`"warning"` + `expect(new Set([corDe(aprovada), corDe(reprovada), corDe(integracao)]).size).toBe(3)` | ✅ PASS |

**Status**: ✅ 12/12 ACs cobertos com evidência `file:line` e desfecho batendo com o texto da spec; 0 spec-precision gaps; 1 lacuna de discriminação de teste sobre REGEN-09 (não é lacuna de cobertura de AC — é o mutante M7).

---

## Edge Cases

- [x] **EC1** — Reprovação na tentativa 3 por falha determinística leva ao mesmo `falhou_conteudo`: `testes/test_grafo_geracao_mensagem.py:588` — `assert critico.chamadas == 0` + `assert ciclo.estado is EstadoMensagem.FALHOU_CONTEUDO` + exceção com `MotivoCritica(CategoriaCritica.ADEQUACAO_CANAL, "campo_obrigatorio_ausente:corpo")`; com persistência real em `testes/test_geracao_mensagens.py:439` (`assert mensagem.estado is not EstadoMensagem.CRITICANDO` + `tentativa_atual == 3`) e `:465`.
- [x] **EC2** — Falha de integração durante a própria tentativa 3 leva a `falhou_integracao_ia`, não `falhou_conteudo`: `testes/test_grafo_geracao_mensagem.py:646` — `assert ciclo.tentativa_atual == 3`, `assert ciclo.estado is EstadoMensagem.FALHOU_INTEGRACAO_IA`, `assert ciclo.estado is not EstadoMensagem.FALHOU_CONTEUDO`, `assert [causa for causa, _, _ in ciclo.excecoes] == ["falha_integracao_ia_critica"]`.
- [x] **EC3** — Execução com mensagens em terminais diferentes: o estado de cada mensagem está correto ao final desta história e o agregado da execução **não** é movido (o portão é da 3.5): `testes/test_geracao_mensagens.py:873` (`falhou_conteudo` + `aguardando_revisao` na mesma execução) e `:487` (`falhou_integracao_ia` + `aguardando_revisao`); execução intocada em `testes/test_gerenciador_execucoes.py:549` — `assert snapshot.estado == EstadoExecucao.PROCESSANDO_MENSAGENS` + `assert execucoes.listar_marcos(execucao_id) == []`. Observação menor (não bloqueante): nenhum teste único reúne os **três** terminais simultaneamente; a spec só exige o estado correto por mensagem, o que está coberto.

---

## Discrimination Sensor

Scratch isolado: `git worktree add <scratch> HEAD` (nunca `git stash`). Baseline `git status --porcelain` vazio antes e depois; worktree removido com `git worktree remove --force` e `git worktree prune`; `HEAD` conferido em `70ce8af` ao final.

| # | Mutation | File | Description | Killed? |
| --- | --- | --- | --- | --- |
| M1 | Off-by-one do limite de tentativas | `aplicacao/grafos/geracao_mensagem.py:77` | `MAXIMO_TENTATIVAS_MENSAGEM = 3` → `4` | ✅ Killed — `test_terceira_reprovacao_do_critico_leva_a_falhou_conteudo_sem_quarta_tentativa`, `test_terceira_reprovacao_deterministica_leva_ao_mesmo_falhou_conteudo`, `test_terceira_reprovacao_registra_excecao_correlacionada_pela_mensagem`, `test_retomada_na_terceira_tentativa_ja_reprovada_esgota_sem_gerar_de_novo` (entre outros) |
| M2 | Retomada sempre reinicia em `gerar` | `aplicacao/geracao_mensagens.py:461` | removida a guarda `if versao is None or versao.numero_tentativa < registro.tentativa_atual`, forçando entrada em `NO_GERAR` | ✅ Killed — `test_retomada_continua_na_terceira_tentativa_sem_repetir_a_primeira_nem_a_segunda`, `test_retomada_na_terceira_tentativa_ja_reprovada_esgota_sem_gerar_de_novo`, `test_retomada_de_mensagem_em_criticando_sem_avaliacao_critica_a_versao_persistida` |
| M3 | Remoção da guarda de estado terminal na retomada | `aplicacao/geracao_mensagens.py:436` | removido `if registro.estado not in ESTADOS_RETOMAVEIS: continue` | ✅ Killed — `test_retomada_nunca_reabre_uma_mensagem_em_estado_terminal` nos 5 terminais + `test_retomada_nao_toca_mensagem_que_ja_aguarda_revisao_humana` |
| M4 | Troca de terminal por causa (geração) | `aplicacao/geracao_mensagens.py:290` | transporte esgotado em `gerar` → `FALHOU_CONTEUDO` em vez de `FALHOU_INTEGRACAO_IA` | ✅ Killed — `test_falha_de_transporte_isola_o_item_e_o_lote_continua` |
| M5 | Troca de terminal por causa (crítica) | `aplicacao/geracao_mensagens.py:330` | transporte esgotado em `criticar` → `FALHOU_CONTEUDO` | ✅ Killed — `test_falha_de_transporte_do_critico_leva_a_falhou_integracao_ia_sem_terminal_novo`, `test_falha_de_integracao_tambem_correlaciona_a_excecao_pela_mensagem` (prova que os dois caminhos têm teste próprio, não um só assumido simétrico) |
| M6 | Remoção do `except Exception` amplo por item (risco 12a) | `aplicacao/geracao_mensagens.py:525` | `_gerar_item_isolado` passa a chamar `_gerar_item` sem `try/except` | ✅ Killed — `test_item_com_falha_tecnica_nao_interrompe_o_restante_do_lote` (e o teste prova continuação real do lote: `assert mensagens[0].estado is EstadoMensagem.AGUARDANDO_REVISAO` para o item seguinte, não só ausência de propagação) |
| M7 | Número de tentativa errado na reconstrução da retomada | `aplicacao/geracao_mensagens.py:514` | `"tentativa": registro.tentativa_atual` → `"tentativa": 1` no estado reconstruído por `_retomar_grafo` | ❌ **Survived** — suíte inteira verde (735 passed) com a mutação aplicada |

**Sensor depth**: expandido (7 mutações; P1 com invariantes de integridade de dados — limite de tentativas e retomada).
**Result**: 6/7 mortos, 1 sobrevivente — FAIL ❌

### M7 — o que exatamente ficou sem asserção

`state["tentativa"]` reconstruído na retomada alimenta três coisas: (a) o `numero_tentativa` da versão que `registrar_geracao` grava, (b) o campo `tentativas` da `Exceção` que `esgotar_tentativas` registra, (c) a decisão `regenerar` vs `esgotar` dentro do grafo. Os testes atuais só exercitam a retomada com `tentativa_atual == 1` no caminho que chega a `gerar`, e os caminhos com tentativa 2/3 sempre passam por `preparar_regeneracao`, que relê o número do banco — então o valor errado fica invisível.

Sonda executada no scratch (arquivo temporário, removido depois): mensagem semeada com as tentativas 1 e 2 concluídas e reprovadas, tentativa 3 reservada e sem versão gravada, retomada disparada.

| Código | `numero_tentativa` das versões persistidas |
| --- | --- |
| Sem mutação (produção atual) | `[1, 2, 3]` — correto |
| Com M7 | `[1, 1, 2]` — **linha duplicada de tentativa 1** |

Ou seja: o código de produção está certo, mas nenhuma asserção da suíte distingue "retomou na tentativa certa" de "regravou por cima de uma tentativa já concluída" — que é literalmente o desfecho que o REGEN-09 proíbe e a proveniência por tentativa do REGEN-07 depende. É uma lacuna de discriminação, não um bug entregue.

---

## Code Quality

| Principle | Status |
| --- | --- |
| Minimum code | ✅ — nenhuma tabela nova; `excecoes_operacionais` reusada com uma coluna nula, como o design decidiu |
| Surgical changes | ✅ — o grafo ganhou 2 nós e 3 arestas; nenhum nó de 3.2/3.3 foi reescrito |
| No scope creep | ✅ — o estado da execução não é mexido (portão de saída de `processando_mensagens` fica para 3.5, como a spec manda) |
| Matches patterns | ✅ — `incrementar_tentativa` repete o padrão otimista de `RepositorioExecucaoPreventiva`; o `except Exception` por item espelha `GerenciadorExecucoes._processar_coleta_e_continuar` (RUNNER-11) |
| Spec-anchored outcome check (valores afirmados batem com a spec) | ✅ — 12/12 |
| Per-layer Coverage Expectation (domínio 1:1 com ACs; rotas com happy + edge + erro) | ✅ — `test_proveniencia_api.py` cobre 200 completo, 200 sem tentativa, 200 sem avaliação, 404 e 422 |
| Todo teste em escopo mapeia para AC/edge case/Done-when | ✅ — nenhum teste órfão no diff |
| Documented guidelines followed | ✅ — `AGENTS.md`, `README.md`; documentação de persistência atualizada e verificada por `testes/test_migracoes.py:900` |
| Integridade de teste (contagem/nomes) | ✅ — ver abaixo |

### Os 6 testes reescritos de 3.2/3.3 — veredito independente: **legítimos, não escondem regressão**

Comparei nome a nome as versões antiga e nova de cada arquivo de teste (`git show ce964f8:<path>` vs `70ce8af`). **Nenhum teste foi removido** em nenhum arquivo; o único delta é adição e 4 renomeações.

| Teste (nome antigo → novo) | Asserção antiga | Asserção nova | Mais fraca? |
| --- | --- | --- | --- |
| `..._permanece_em_gerando_com_motivo_persistido` → `..._nunca_avanca_para_criticando_e_registra_o_motivo` (`test_geracao_mensagens.py:439`) | `estado is GERANDO` | `estado is FALHOU_CONTEUDO` **e** `estado is not CRITICANDO` **e** `tentativa_atual == 3` (mais as 3 asserções de versão preservadas) | Não — 3 asserções onde havia 1 |
| `test_saida_vazia_permanece_em_gerando...` → `..._e_campo_obrigatorio_ausente_e_consome_a_tentativa` (`:465`) | `estado is GERANDO` | `estado is FALHOU_CONTEUDO` **e** `tentativa_atual == 3` | Não |
| `..._e_mensagem_permanece_em_criticando` → `test_reprovacao_do_critico_persiste_motivos_da_versao_avaliada` (`:759`) | `estado is CRITICANDO` | `estado is FALHOU_CONTEUDO` **e** `tentativa_atual == 3` (asserções de motivos/origem intactas) | Não |
| `..._nem_avanca` → `test_saida_invalida_do_critico_nao_persiste_avaliacao_nem_aprova` (`:790`) | `estado is CRITICANDO` + `is not AGUARDANDO_REVISAO` + avaliação `None` | `estado is FALHOU_CONTEUDO` + `is not AGUARDANDO_REVISAO` + avaliação `None` | Não — mesma força, desfecho mais completo |
| `test_mensagem_reprovada_deterministicamente_nunca_recebe_avaliacao_critica` (`:832`, nome mantido) | `estado is GERANDO` + `critico.chamadas == 0` | `estado is FALHOU_CONTEUDO` + `is not AGUARDANDO_REVISAO` + `critico.chamadas == 0` (agora ao longo das 3 tentativas) | Não — ganhou uma asserção e um ciclo inteiro de superfície |
| `test_reprovacao_de_um_item_nao_impede_a_aprovacao_do_seguinte` (`:873`, nome mantido) | `reprovado is CRITICANDO` + `aprovado is AGUARDANDO_REVISAO` | `reprovado is FALHOU_CONTEUDO` + `tentativa_atual == 3` + `aprovado is AGUARDANDO_REVISAO` + `tentativa_atual == 1` | Não — 4 asserções onde havia 2 |

**Eram comportamento realmente deferido?** Sim, e conferi na fonte, não no relato do autor:

- `.specs/features/3-2-gerar-mensagens-automaticamente-para-cada-canal/spec.md:23` — "Regeneração após reprovação e limite de 3 tentativas | História 3.4 — esta história cobre a primeira tentativa de geração de cada mensagem".
- `.specs/features/3-3-avaliar-a-qualidade-e-a-seguranca-das-mensagens/spec.md:21` — "Contagem de tentativas e regeneração automática após reprovação | História 3.4 — aqui a mensagem só é avaliada uma vez por versão; o ciclo de regeneração é orquestrado depois".

A "parada em `gerando`/`criticando`" que aqueles testes afirmavam era o estado *transitório* que sobrava justamente porque o ciclo não existia; nenhuma AC de 3.2/3.3 exige que a mensagem termine ali. As reescritas trocam um estado intermediário por um terminal, sempre com asserção adicional. Nenhuma foi enfraquecida, nenhuma foi apagada.

### Item 12(a) do `STATE.md` — veredito independente: **parcialmente fechado** (como o autor declarou)

O que foi realmente feito (`aplicacao/geracao_mensagens.py:525`): `gerar_lote` agora chama `_gerar_item_isolado`, que envolve `_gerar_item` em `except Exception` e registra `falha_tecnica_item:{elegibilidade_id}:{tipo}: {erro}` como `Exceção` operacional; idem na retomada (`_retomar_item_isolado`, `:429`). O mecanismo é o certo:

- Ele **não** engole desfecho de conteúdo: reprovação, saída inválida e transporte esgotado nunca chegam ali como exceção — cada um tem seu ramo explícito dentro do grafo e do `CicloPersistenteMensagem`. O `except` só vê falha de infraestrutura de verdade (conflito de versão, banco fora).
- Ele **realmente** deixa o lote seguir: provado por `test_item_com_falha_tecnica_nao_interrompe_o_restante_do_lote` (`testes/test_geracao_mensagens.py:1005`), que quebra o **primeiro** item com `RuntimeError("banco indisponível")` e afirma que o segundo item existe (`assert [item.elegibilidade_id for item in mensagens] == [seguinte.id]`) e chega ao terminal (`assert mensagens[0].estado is EstadoMensagem.AGUARDANDO_REVISAO`). Não é "nenhuma exceção propagou": é continuação comprovada. Mutação M6 confirma que a asserção mata a remoção do handler.

**O que continua aberto** (por isso "parcial", e é honesto assim): a `asyncio.Task` desacoplada em si segue sem rede de proteção — `montar_portas_preflight.acionar_geracao` (`adaptadores/http/preflight_ia.py:259`) faz `add_done_callback(_tarefas_de_geracao.discard)`, que nunca chama `.exception()`; e o que está fora do laço em `gerar_lote` (a própria chamada a `elegibilidades.listar_por_execucao`) continua sem `try`. Uma falha nesses dois pontos ainda morre em silêncio. O impacto ficou bem menor porque o item 12(b) agora recupera a execução no boot, mas o risco não desapareceu — recomendo manter 12(a) registrado como parcial no `STATE.md`, não riscá-lo.

### Item 12(b) do `STATE.md` — veredito independente: **genuinamente fechado**

Tracei a ligação inteira, sem assumir:

1. `composicao/api.py:69` — o lifespan chama `await gerenciador.retomar_pendentes()` no boot, antes do agendador.
2. `GerenciadorExecucoes` é construído com `montar_portas_execucao(configuracao_ativa)`.
3. `adaptadores/http/execucao_preventiva.py:180` — `montar_portas_execucao` passa `geracao=montar_servico_geracao(configuracao)`, que é o `ServicoGeracaoMensagens` **real** (repositórios DuckDB reais, `construir_grafo` com `AgenteRedator`/`AgenteCritico` reais) — `adaptadores/http/preflight_ia.py:201`.
4. `aplicacao/gerenciador_execucoes.py:396` — `retomar_pendentes` deixou de ignorar `PROCESSANDO_MENSAGENS` e chama `await self._portas.geracao.retomar_mensagens_pendentes(execucao_id)`.
5. `listar_nao_terminais` (`repositorio_execucao_preventiva.py:183`) filtra por `eh_terminal`, e `processando_mensagens` não é terminal — logo a execução chega mesmo à varredura.

Coberto por `testes/test_gerenciador_execucoes.py:549` (delega e não mexe no estado/marcos da execução) e `:566` (não delega para `aguardando_geracao`/`coletando`), com o comportamento real do serviço provado nos testes de retomada com DuckDB real (`test_geracao_mensagens.py:1075..1252`). É um fechamento de verdade, não uma remoção de `return` antecipado.

### Fronteira de minimização do `ContextoAgente` — intacta

`dominio/montador_contexto_agente.py:83` continua `@dataclass(frozen=True, slots=True)` com exatamente os 5 campos de 3.1 (`evento`, `localizacao_aproximada`, `coberturas_relevantes`, `canal`, `orientacoes_seguranca`). `git diff ce964f8..70ce8af -- central_preventiva/dominio/` é **vazio**. Os motivos da reprovação entram como terceiro parâmetro separado de `AgenteRedator.gerar()` (`adaptadores/ia/agente_redator.py:233`) e como bloco de texto do pedido em `montar_prompt` (`:142`) — nunca guardados no contexto. Provado por `testes/test_agente_redator.py:209` (bloco presente com categoria+justificativa) e `testes/test_agente_redator.py:227` (`assert CABECALHO_CORRECAO not in str(modelo.invocacoes[0].entrada)` na primeira tentativa).

### `excecoes_operacionais.mensagem_id` — discriminação conferida

A coluna é nula e sem backfill (`migracoes/0012_excecoes_mensagem.sql`), e a discriminação está testada nos dois sentidos em SQL: `testes/test_migracoes.py:890` afirma `WHERE mensagem_id = ?` → só `falhou_conteudo` e `WHERE execucao_id = ? AND mensagem_id IS NULL` → só `falhou_coleta`. Nenhum caminho de **leitura** de exceções existe ainda em produção (o único uso é o `INSERT` em `repositorio_execucao_preventiva.py:273`), então não há query que possa vazar exceção de execução em consulta de mensagem — nada a corrigir, mas vale a nota para 3.5/4.x: quem criar a primeira leitura precisa aplicar esse filtro. Observação menor: `_registrar_excecao` de `ServicoGeracaoMensagens` (`:590`) registra sem `mensagem_id` também na retomada (`_retomar_item_isolado`), mesmo quando a mensagem já existe — coerente com "exceção do item que não chegou a ter mensagem" no lote, um pouco menos preciso na retomada; não viola nenhuma AC.

### SPEC_DEVIATIONs declaradas (3) — todas justificadas

1. `aplicacao/grafos/geracao_mensagem.py:27` — porta `CicloMensagem` no lugar da dependência direta de `RepositorioMensagens` no grafo, e duas funções de aresta em vez de uma `decidir_apos_critica`. Aceita: a dependência direta colocaria DuckDB dentro do grafo e criaria ciclo de composição; e a decisão precisa mesmo existir depois de `gerar` (reprovação determinística nunca chega a `criticar` mas consome tentativa, REGEN-01).
2. `aplicacao/grafos/geracao_mensagem.py:38` — `tuple[MotivoCritica, ...]` em vez de `list[MotivoCritica] | None`. Aceita: coerente com os valores de domínio imutáveis do projeto.
3. `adaptadores/ia/agente_redator.py:15` — terceiro parâmetro em `gerar()` em vez de "sem alteração de assinatura, motivos pelo contexto". Aceita e, na verdade, **obrigatória**: as duas metades da frase do design se contradiziam, porque o próprio design exige que `ContextoAgente` continue com 5 campos.
4. `migracoes/0012_excecoes_mensagem.sql:3` — renumeração `0010`→`0012`. Aceita, já é a L-034 confirmada do projeto.

---

## Gate Check

- **Gate command (Build)**: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright` + `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`
- **Backend**: 735 passed, 0 failed, 0 skipped (`53.46s`); `ruff` — "All checks passed!"; `pyright` — "0 errors, 0 warnings, 0 informations"
- **Frontend**: 253 passed em 28 arquivos, 0 failed, 0 skipped; `lint` — só os 12 avisos pré-existentes (`set-state-in-effect`/`only-export-components`), nenhum na superfície tocada; `build` — "✓ built in 235ms"
- **Test count before feature**: 689 backend (medido de forma independente com `pytest --collect-only -q` em um worktree em `ce964f8`, não copiado do relato do autor) + 247 frontend
- **Test count after feature**: 735 backend + 253 frontend
- **Delta**: +46 backend, +6 frontend
- **Test integrity**: nenhum teste apagado. Diff nome a nome dos 6 arquivos de teste tocados: `test_grafo_geracao_mensagem.py` +11, `test_geracao_mensagens.py` +12 e 4 renomeados, `test_gerenciador_execucoes.py` +2, `test_repositorio_mensagens.py` +4, `test_migracoes.py` +3, `test_agente_redator.py` +2. Nenhuma asserção enfraquecida (tabela dos 6 reescritos acima).
- **Skipped tests**: nenhum
- **Failures**: nenhuma

---

## Fix Plans

### Fix 1: Fechar o mutante M7 — a retomada não prova o número da tentativa que grava

- **Root cause**: `_retomar_grafo` (`src/backend/central_preventiva/aplicacao/geracao_mensagens.py:514`) reconstrói `state["tentativa"]` a partir de `registro.tentativa_atual`, e esse valor vira o `numero_tentativa` da versão gravada e o campo `tentativas` da `Exceção` de esgotamento. A suíte só exercita a retomada que chega a `gerar` com `tentativa_atual == 1`, e os demais caminhos releem o número do banco em `preparar_regeneracao` — então trocar o valor por `1` mantém 735 testes verdes enquanto o banco passa a receber uma segunda versão numerada `1`.
- **Fix task** (somente teste — **nenhuma mudança de produção**, o código está correto): em `src/backend/testes/test_geracao_mensagens.py`, (a) acrescentar um teste de retomada que semeia as tentativas 1 e 2 concluídas/reprovadas, reserva a tentativa 3 e a transiciona para `gerando` **sem** gravar versão, roda `retomar_mensagens_pendentes` e afirma `[numero for numero, _, _ in _versoes_persistidas(...)] == [1, 2, 3]` (hoje o desfecho mutado seria `[1, 1, 2]`); (b) estender `test_retomada_na_terceira_tentativa_ja_reprovada_esgota_sem_gerar_de_novo` (`:1100`) com a asserção do campo `tentativas` da `Exceção` registrada (`== 3`) e do `IMPACTO_ITEM_FORA_DO_LOTE`, espelhando o que `:960` já faz no caminho sem retomada.
- **Verify**: reaplicar M7 (`"tentativa": registro.tentativa_atual` → `1`) num worktree descartável e confirmar que a suíte agora falha.
- **Done when**: M7 morre; 735+2 testes verdes; nenhum arquivo de produção alterado.
- **Priority**: Major

### Fix 2 (opcional, Minor): ramo de retomada com avaliação já aprovada sem teste

- **Root cause**: em `_retomar_item` (`src/backend/central_preventiva/aplicacao/geracao_mensagens.py:480`), o ramo `critica.desfecho is DesfechoCritica.APROVADA` (mensagem interrompida entre gravar a avaliação aprovada e transicionar) não tem teste. Sondei o comportamento no scratch: funciona corretamente (mensagem chega a `aguardando_revisao`, zero chamadas ao redator e ao crítico, nenhuma versão nova, nenhuma avaliação duplicada — `RepositorioAvaliacoesCriticas.salvar` é `ON CONFLICT DO NOTHING`). É lacuna de cobertura, não defeito.
- **Fix task**: um teste de retomada com versão válida + avaliação aprovada já persistida, afirmando `estado is AGUARDANDO_REVISAO`, `redator.canais_chamados == []`, `critico.chamadas == 0` e uma única linha em `avaliacoes_criticas`.
- **Priority**: Minor

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
| --- | --- | --- |
| REGEN-01 | Implementing | ✅ Verified |
| REGEN-02 | Implementing | ✅ Verified |
| REGEN-03 | Implementing | ✅ Verified |
| REGEN-04 | Implementing | ✅ Verified |
| REGEN-05 | Implementing | ✅ Verified |
| REGEN-06 | Implementing | ✅ Verified |
| REGEN-07 | Implementing | ✅ Verified |
| REGEN-08 | Implementing | ✅ Verified |
| REGEN-09 | Implementing | ⚠️ Needs Test Fix (AC coberto; mutante M7 sobrevivente — Fix 1) |
| REGEN-10 | Implementing | ✅ Verified |
| REGEN-11 | Implementing | ✅ Verified |
| REGEN-12 | Implementing | ✅ Verified |

---

## Summary

**Overall**: ❌ Not Ready — 1 fix de teste antes de fechar

**Spec-anchored check**: 12/12 ACs com desfecho batendo com a spec, 0 spec-precision gaps, 3/3 Edge Cases
**Sensor**: 6/7 mutantes mortos, 1 sobrevivente (M7)
**Gate**: 735 backend + 253 frontend, 0 falhas; ruff/pyright/build limpos

**What works**: o ciclo de três tentativas está fechado no próprio grafo, com a fronteira exata provada nos dois sentidos (aprovação encerra na 1ª, 2ª e 3ª; 3ª reprovação vai a `falhou_conteudo` sem 4ª chamada, e o limite é cobrado também no `UPDATE` do repositório). As duas causas terminais permanecem distintas e cada nó tem seu próprio teste de transporte esgotado — não há simetria assumida. A retomada roda contra DuckDB real com serviço reinstanciado, continua do marco durável certo e nunca reabre nenhum dos 5 terminais (parametrizado, com `versao` e `tentativa_atual` conferidas). A proveniência expõe os 9 nomes do AC e é provada negativa quanto a chave, contato e prompt. O item 12(b) do `STATE.md` está genuinamente fechado, com a fiação de boot traçada ponta a ponta. Os 6 testes reescritos de 3.2/3.3 são legítimos e mais fortes, não mais fracos.

**Issues found**: Fix 1 (Major) — nenhuma asserção distingue "retomou na tentativa certa" de "regravou por cima de uma tentativa concluída"; o mutante M7 sobrevive e a sonda mostra `[1, 1, 2]` de versões persistidas sob a mutação. Fix 2 (Minor) — um ramo de retomada sem teste. Item 12(a) do `STATE.md` está parcialmente fechado: o laço por item ficou protegido e provado, mas a `asyncio.Task` desacoplada e o trecho fora do laço em `gerar_lote` continuam sem rede.

**Next steps**: rotear o Fix 1 (e, se conveniente, o Fix 2) a um implementador; re-verificar; então marcar REGEN-09 como Verified e fechar a história. Nenhuma mudança de produção é necessária.
