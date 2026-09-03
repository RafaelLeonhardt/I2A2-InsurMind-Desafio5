# História 3.2: Gerar mensagens automaticamente para cada canal — Validation

**Date**: 2026-09-03
**Spec**: `.specs/features/3-2-gerar-mensagens-automaticamente-para-cada-canal/spec.md`
**Diff range**: `9d64242..c46ef26` (10 commits: `801bf9a`..`c46ef26`, T1 + fix de migração + T2–T9)
**Verifier**: independent sub-agent (author ≠ verifier) — nenhuma linha de implementação ou teste desta história foi escrita por este agente

---

## Task Completion

| Task | Status | Notes |
| --- | --- | --- |
| T1 | ✅ Done | `0010_mensagens.sql` (renumeração `0008`→`0010` marcada como `SPEC_DEVIATION` no próprio arquivo; `0008`/`0009` já consumidos por 2.6/3.1) |
| — | ✅ Done | Commit de correção `3121471` — expectativa de migrações do inicializador `[1..9]`→`[1..10]`; atualização legítima (a migração `0010` existe de fato), não afrouxamento |
| T2 | ✅ Done | `EstadoMensagem` com os 9 valores do AD-4 e 5 terminais; matriz pedia `Tests: none`, autor adicionou 3 casos — evidência a mais, não a menos |
| T3 | ✅ Done | `ValidadorSaidaCanal` + 4 limites em `Configuracao` + `.env.example` |
| T4 | ✅ Done | `AgenteRedator`; `SPEC_DEVIATION` do tipo de retorno (`RespostaRedator` em vez de `SaidaCanal`) verificada e justificada — ver GERAR-09/GERAR-10 |
| T5 | ✅ Done | `StateGraph` de um nó compilado; 3 desfechos; nenhum teste toca rede |
| T6 | ✅ Done | `RepositorioMensagens` com `MensagemJaExiste`, `ConflitoVersaoMensagem`, `TransicaoMensagemInvalida` |
| T7 | ✅ Done | `ServicoGeracaoMensagens.gerar_lote` + gatilho automático via porta `acionar_geracao` (`SPEC_DEVIATION` registrada) |
| T8 | ✅ Done | `GET /api/v1/execucoes/{execucao_id}/mensagens`; inventário de rotas de `test_saude.py` atualizado (rota nova real, não assertion enfraquecida) |
| T9 | ✅ Done | `SuperficieGeracaoMensagens` — leitura apenas |

---

## Spec-Anchored Acceptance Criteria

### P1: Limites de canal configuráveis e validados nas fronteiras

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| GERAR-01: limites exatos e configuráveis, unidade = caractere Unicode | WhatsApp 1024, SMS 160, assunto e-mail 78, corpo e-mail 2000; contagem em caracteres Unicode, não bytes | `src/backend/testes/test_validador_saida_canal.py:56-59` - `assert configuracao.limite_caracteres_whatsapp == 1024` (+ sms/assunto/corpo); `:214-216` - `assert len(corpo.encode("utf-8")) > 160` e `validar(Canal.SMS, SaidaCanal(corpo="á"*160)).valida is True`; `:224-227` - limites injetados substituem os defaults | ✅ PASS |
| GERAR-02: validadores aplicam os limites **antes e depois** da geração | "depois" é preciso (recusa da saída acima do limite); "antes" não é definido pela spec — não existe artefato a validar antes da geração | depois: `test_validador_saida_canal.py:111-112` - `assert resultado.motivo == f"limite_excedido:corpo:{limite+1}:{limite}"`; antes (interpretação do autor): `test_validador_saida_canal.py:243-244` - `assert validador().limite_corpo(canal) == limite_corpo` e `src/backend/testes/test_agente_redator.py:170-172` - o mesmo número entra no prompt | ⚠️ Spec-precision gap |
| GERAR-03: fronteiras exatas (abaixo / no limite / acima) de **cada** limite | 4 campos × 3 posições | corpo (whatsapp/sms/email, parametrizado): `test_validador_saida_canal.py:73`, `:90`, `:109-112`; assunto de e-mail: `:118-124`, `:130-136`, `:142-150` - `assert resultado.motivo == "limite_excedido:assunto:79:78"` | ✅ PASS (4/4 campos) |

### P1: Geração automática por combinação segurado+canal

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| GERAR-04: execução em `processando_mensagens` aciona automaticamente o redator para cada combinação elegível, sem ação manual **por mensagem** | Todas as combinações elegíveis geradas a partir de um único comando; nenhuma ação humana por item | `src/backend/testes/test_geracao_mensagens.py:602-610` - `preflight.preparar(...)` → `assert resultado.estado == PROCESSANDO_MENSAGENS` e `{(elegibilidade_id, canal)} == {(primeiro.id, SMS), (segundo.id, EMAIL)}`, `{estado} == {CRITICANDO}`; `:284-293` - lote único gera 2 mensagens, `redator.canais_chamados == [SMS, EMAIL]`; `:316-326` - item excluído não gera; negativo: `:641-645` - preflight bloqueado não aciona nada | ✅ PASS |
| GERAR-05: mensagem permanece associada a execução, elegibilidade, evento, regra, segurado, apólice e canal | Vínculo direto (execução/elegibilidade/canal) + vínculo por elegibilidade (evento/regra/segurado/apólice) | `test_geracao_mensagens.py:305-313` - `assert mensagem.execucao_id == EXECUCAO_ID`, `mensagem.elegibilidade_id == incluido.id`, `mensagem.canal is Canal.WHATSAPP`, `origem.evento_id == EVENTO_ID`, `origem.regra_id == REGRA_ID`, `origem.segurado_id`/`origem.apolice_id`; schema: `migracoes/0010_mensagens.sql` colunas `execucao_id`/`elegibilidade_id`/`canal` | ✅ PASS |
| GERAR-06: `UNIQUE` impede segunda mensagem para a mesma elegibilidade+canal | Segunda criação recusada pelo banco, não por checagem em Python | `src/backend/testes/test_migracoes.py:603-616` - `pytest.raises(duckdb.ConstraintException)` no par repetido e `assert total == (3,)` (mesmo item em outro canal e outro item no mesmo canal permitidos); `src/backend/testes/test_repositorio_mensagens.py:58` - `pytest.raises(MensagemJaExiste)`; `test_geracao_mensagens.py:483-484` - reinvocação mantém os mesmos 2 ids | ✅ PASS |

### P1: Saída estruturada por tipo de canal, validada deterministicamente

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| GERAR-07: WhatsApp/SMS devolvem corpo adaptado, campos obrigatórios e limite validados | Schema com `corpo`; corpo é o único obrigatório; limite cobrado | `test_agente_redator.py:122-125` - `assert modelo.invocacoes[0].schema is SaidaWhatsApp`/`SaidaSMS` e `resposta.saida.corpo == estruturada.model_dump()["corpo"]`; `test_validador_saida_canal.py:189-192` - WhatsApp/SMS válidos só com corpo | ✅ PASS |
| GERAR-08: e-mail devolve assunto **e** corpo, mesmos validadores | Schema com `assunto`+`corpo`; ambos obrigatórios; limites separados | `test_agente_redator.py:122-125` (`schema is SaidaEmail`, `saida.assunto` preenchido); `test_validador_saida_canal.py:172-173` - `assert resultado.motivo == "campo_obrigatorio_ausente:assunto"`; `:181-182` - assunto nulo idem; `test_grafo_geracao_mensagem.py:172-173` idem no grafo | ✅ PASS |
| GERAR-09: saída ausente/malformada/acima do limite → versão inválida, **impedida** de seguir à crítica, com motivo persistido | `valida = false` + motivo persistido; estado permanece `gerando`, nunca `criticando`; nenhuma exceção não tratada | `test_geracao_mensagens.py:391-396` - `assert mensagem.estado is EstadoMensagem.GERANDO`, `versao.valida is False`, `versao.motivo_invalidez == "limite_excedido:corpo:161:160"`; `:411-416` - corpo em branco → `"campo_obrigatorio_ausente:corpo"`, ainda `GERANDO`; `test_grafo_geracao_mensagem.py:161-162` - saída ausente → `"saida_ausente"`; `test_agente_redator.py:180-182` - `parsed: None` devolve `RespostaRedator(saida=None, ...)` sem levantar exceção | ✅ PASS |
| GERAR-10: mensagem válida persiste versão inicial, duração, modelo, prompt e métricas de uso; avança `gerando` → `criticando` | Todos os 5 campos persistidos + transição de estado | `test_geracao_mensagens.py:363-374` - `assert mensagem.estado is EstadoMensagem.CRITICANDO`, `versao.numero_tentativa == 1`, `versao.conteudo == SaidaCanal(corpo=CORPO_VALIDO)`, `versao.modelo == "gpt-4o-mini"`, `versao.versao_prompt == "v1"`, `versao.tokens_entrada == 210`, `versao.tokens_saida == 64`, `versao.duracao_ms > 0`; repositório: `test_repositorio_mensagens.py:99-108` | ✅ PASS |

### P2: Reidratação sem duplicar geração

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| GERAR-11: atualizar a página reconstrói etapa e progresso **a partir dos dados persistidos** | Progresso derivado só da API, sem estado inventado | `src/frontend/src/funcionalidades/geracao-mensagens/SuperficieGeracaoMensagens.test.tsx:55-60` - `findByText('1 de 2 mensagens geradas')`, `expect(getMensagens).toHaveBeenCalledWith(EXECUCAO_ID)`; `:160-162` - após `unmount` + remontagem, `'2 de 2 mensagens geradas'` e `getAllByRole('listitem')` com 2 itens; `:126-127` - sem mensagens, `'0 de 0 mensagens geradas'`; backend: `src/backend/testes/test_mensagens_api.py:57-58` (lista vazia), `:145-147` (`versao_atual is None`, nunca inventada) | ✅ PASS |
| GERAR-12: o frontend não reenvia geração nem duplica mensagem ao reidratar | Nenhuma chamada de escrita a partir da superfície; contagem de mensagens não aumenta | `SuperficieGeracaoMensagens.test.tsx:137-145` - após clicar "Atualizar progresso", `getMensagens` chamado 2× e o módulo `api/mensagens` não expõe nenhum símbolo `gerar`/`Gerar`/`post`; `test_mensagens_api.py:165-167` - duas consultas idênticas, `len(repo.listar_por_execucao(...)) == 2`; backend: `test_geracao_mensagens.py:483-486` - segunda invocação de `gerar_lote` mantém os mesmos ids e `redator.canais_chamados` inalterado (nenhuma regeração) | ✅ PASS |

**Status**: ⚠️ 11/12 ACs casaram com o desfecho definido pela spec; 1 spec-precision gap (GERAR-02, "antes da geração" não tem desfecho preciso na spec).

---

## Edge Cases

- [x] **Saída estruturalmente válida mas vazia → campo obrigatório ausente, não sucesso** — `test_validador_saida_canal.py:155-161` (parametrizado em `""`, `"   "`, `"\n\t "` × 3 canais) - `assert resultado.motivo == "campo_obrigatorio_ausente:corpo"`; fim a fim: `test_geracao_mensagens.py:411-416`.
- [x] **Dois elegíveis no mesmo canal e evento → cada combinação gera sua própria mensagem, sem reaproveitar conteúdo** — `test_geracao_mensagens.py:462-468` - `{elegibilidade_id} == {primeiro.id, segundo.id}` e `assert len(conteudos) == 2`.
- [x] **Contexto mínimo ausente → falha isolada, sem tentar gerar com contexto incompleto** — `test_geracao_mensagens.py:342-347` - só o item com contexto gera, `redator.canais_chamados == [Canal.SMS]` (nenhuma chamada para o item sem contexto) e a exceção operacional registrada é exatamente `("contexto_ausente:{id}", 1, IMPACTO_ITEM_SEM_MENSAGEM)`.

---

## Discrimination Sensor

Escopo isolado: `git worktree add <scratch> HEAD` (nunca `git stash`). Baseline `git status --porcelain` vazio antes e depois; worktree removida com `--force` ao fim.

| # | File:line | Description | Killed? |
| --- | --- | --- | --- |
| 1 | `src/backend/central_preventiva/aplicacao/geracao_mensagens.py:152-153` | Removido o filtro `if not registro.elegivel: continue` — excluídos do público passariam a receber mensagem (vazamento de governança de dados) | ✅ Killed — `test_item_excluido_do_publico_nao_gera_mensagem` |
| 2 | `src/backend/central_preventiva/aplicacao/geracao_mensagens.py:170-171` | Quebrado o no-op idempotente: em `MensagemJaExiste`, roda o grafo mesmo assim (regeração de mensagem já persistida) | ✅ Killed — `test_reinvocar_o_lote_nao_duplica_mensagem_nem_regera` (`canais_chamados` com 2 itens extras) |
| 3 | `src/backend/central_preventiva/dominio/validador_saida_canal.py:131` | Off-by-one no limite de corpo: `len(corpo) > limite` → `>= limite` | ✅ Killed — 5 testes, incluindo `test_corpo_exatamente_no_limite_e_valido[whatsapp-1024\|sms-160\|email-2000]` e `test_contagem_e_de_caracteres_unicode_e_nao_de_bytes` |
| 4 | `src/backend/central_preventiva/dominio/validador_saida_canal.py:119` | Off-by-one no limite de assunto: `len(assunto) > limite` → `>= limite` | ✅ Killed — `test_assunto_de_email_exatamente_no_limite_e_valido` (`motivo='limite_excedido:assunto:78:78'`) |
| 5 | `src/backend/central_preventiva/aplicacao/preflight_ia.py:465-466` | Removida a chamada a `acionar_geracao` — o acionamento automático deixaria de existir | ✅ Killed — `test_preflight_bem_sucedido_aciona_a_geracao_do_lote_automaticamente` |

**Não mutado, registrado como lacuna** (a mutação exigiria remover código ausente): não existe nenhum tratamento de exceção na task desacoplada de geração — ver Fix 1.

**Sensor depth**: lightweight-plus (5 mutações; viés para integração LLM, mensageria e o invariante de minimização de dados do AD-9)
**Result**: 5/5 killed — PASS ✅

---

## Code Quality

| Principle | Status |
| --- | --- |
| Minimum code | ✅ |
| Surgical changes | ✅ — 3 arquivos pré-existentes tocados (`preflight_ia.py` aplicação/HTTP, `api.py`), todos exigidos pelo acionamento e pelo registro da rota |
| No scope creep | ✅ — texto gerado deliberadamente fora do `GET`; regeneração/crítica deixadas para 3.3/3.4 |
| Matches patterns | ⚠️ — o padrão de task desacoplada é seguido (`create_task` + set de referências fortes + `add_done_callback`), mas sem o `try/except Exception` + registro de falha técnica que `GerenciadorExecucoes._processar_coleta_e_continuar` usa (RUNNER-11). Ver Fix 1 |
| Spec-anchored outcome check | ✅ (1 spec-precision gap declarado em GERAR-02) |
| Per-layer Coverage Expectation met | ✅ — domínio 1:1 com GERAR-01..03/07..09; rota nova com happy + vazio + 404 + 422 + escopo por execução |
| Every test maps to a spec requirement | ✅ — nenhum teste órfão nos 9 arquivos de teste novos/alterados |
| Documented guidelines followed | ✅ — `AGENTS.md`/`README.md`; matriz de cobertura de `tasks.md`; dublê obrigatório do `ChatOpenAI` respeitado (nenhum teste toca a rede) |

**Atualizações de testes pré-existentes conferidas uma a uma**: `test_inicializador.py:73,99` (`[1..9]`→`[1..10]`) e `test_migracoes.py:86-99,110-121` acompanham a migração `0010` real; `test_saude.py:53` acrescenta a rota nova ao inventário. Nenhuma assertion foi enfraquecida, nenhum teste foi removido.

---

## Gate Check

- **Gate command** (Build, `tasks.md`): backend `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright` + frontend `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`
- **Result**: backend 630 passed, 0 failed, 0 skipped (exit 0); ruff `All checks passed!`; pyright `0 errors, 0 warnings, 0 informations`; frontend 237 passed / 27 arquivos (exit 0); oxlint exit 0 (apenas warnings pré-existentes, nenhum em arquivo desta história); `vite build` ✓
- **Test count before feature**: 528 backend / 229 frontend
- **Test count after feature**: 630 backend / 237 frontend
- **Delta**: +102 backend, +8 frontend
- **Skipped tests**: nenhum
- **Failures**: nenhuma

---

## Fix Plans

### Fix 1: falha do lote de geração desaparece silenciosamente na task desacoplada

- **Root cause**: `adaptadores/http/preflight_ia.py:244-246` agenda `gerar_lote` com `asyncio.create_task(...)` e um `add_done_callback(_tarefas_de_geracao.discard)` que apenas descarta a referência — nunca chama `tarefa.exception()`. E `aplicacao/geracao_mensagens.py:151-154` não envolve `_gerar_item` em nenhum `try/except` amplo: `_gerar_item` só captura `MensagemJaExiste`. Logo, qualquer erro de infraestrutura fora do caminho do grafo (`salvar_versao`, `transicionar` levantando `ConflitoVersaoMensagem`, `listar_por_execucao`) aborta o lote inteiro no primeiro item afetado, sem registrar `Exceção` operacional, sem transicionar a execução e sem nada visível na superfície — a execução fica em `processando_mensagens` indefinidamente. Isso contradiz o próprio docstring de `gerar_lote` ("Uma falha isolada de um item nunca interrompe os demais") e diverge do padrão RUNNER-11 já estabelecido em `GerenciadorExecucoes._processar_coleta_e_continuar`, que envolve o corpo da task em `except Exception` e registra a falha técnica.
- **Fix task**: envolver o corpo de `_gerar_item` (ou o laço de `gerar_lote`) em `except Exception` registrando a `Exceção` operacional com o mesmo `IMPACTO_ITEM_SEM_MENSAGEM`, e/ou surfacear a exceção da task em `acionar_geracao` (`tarefa.add_done_callback` que leia `tarefa.exception()` e registre a falha técnica), espelhando `_registrar_falha_processamento`. Teste: um repositório dublê cujo `salvar_versao` levanta erro no primeiro item deve deixar o segundo item gerado e uma exceção operacional registrada.
- **Priority**: Major (robustez operacional; nenhum AC GERAR-* falha por causa disso — o único caso de isolamento que a spec nomeia, contexto mínimo ausente, está coberto e passa)

### Fix 2: execução interrompida em `processando_mensagens` não é retomada no boot

- **Root cause**: `GerenciadorExecucoes.retomar_pendentes` (`aplicacao/gerenciador_execucoes.py:376-385`) chama `continuar`, que em `_continuar` retorna sem ação para qualquer estado diferente de `coletando`/`avaliando_elegibilidade`. Uma execução em `processando_mensagens` cuja task de geração morreu com o processo (restart do backend no meio do lote) nunca retoma: mensagens já criadas ficam em `gerando` para sempre.
- **Fix task**: decidir explicitamente (registro no STATE.md, ou retomada real em 3.4 junto da política de nova tentativa) se `processando_mensagens` é retomável no boot; hoje não é, e nada documenta isso.
- **Priority**: Minor (fora do escopo literal desta história — GERAR-11/12 tratam de recarregar a página, não de reiniciar o backend — mas é o mesmo buraco que a 2.6 fechou para `coletando`)

### Fix 3: `test_prompt_leva_os_cinco_campos_do_contexto_minimo_e_nada_mais` não testa o "e nada mais"

- **Root cause**: `src/backend/testes/test_agente_redator.py:130-143` afirma apenas que os 5 campos do `ContextoAgente` **estão** no prompt; não há nenhuma assertion negativa (`elegibilidade_id`, `segurado_id`, `apolice_id`, `nome_segurado` ausentes). O código está correto — `montar_prompt` só recebe `ContextoAgente` e não há caminho para outro dado —, mas o teste não é discriminante para o invariante AD-9 que seu nome promete.
- **Fix task**: acrescentar assertions negativas sobre identificadores no texto enviado ao modelo.
- **Priority**: Minor (invariante hoje garantido pela estrutura do código, não pelo teste)

---

## Observações verificadas (não são lacunas)

- **`RespostaRedator` em vez de `SaidaCanal` (SPEC_DEVIATION, T4)**: justificada e necessária. GERAR-10 exige persistir métricas de uso — `SaidaCanal` não as carrega; GERAR-09 exige que saída ausente seja *marcada inválida*, não que levante exceção — daí `saida: SaidaCanal | None`. O caminho `saida=None` é tratado corretamente a jusante: `ValidadorSaidaCanal.validar` aceita `SaidaCanal | None` (`validador_saida_canal.py:101,109-110`) e o grafo classifica o resultado como `INVALIDA` sem nunca desreferenciar `None` (`geracao_mensagem.py:157-167`); `_gerar_item` persiste `SaidaCanal(corpo="")` nesse caso (`geracao_mensagens.py:187`). Coberto por `test_agente_redator.py:180-182`, `test_grafo_geracao_mensagem.py:161-162`.
- **`ChatOpenAI` construído na primeira geração, não na composição**: verificado como correção real, não conveniência. `montar_portas_preflight` instancia `AgenteRedator` no boot da aplicação (`adaptadores/http/preflight_ia.py:240`, chamado por `criar_aplicacao`); construir `ChatOpenAI` ali levantaria `OpenAIError` sem `OPENAI_API_KEY`, quebrando a subida do backend com chave vazia — exatamente o cenário que os testes de API usam (`Configuracao` sem chave) e que o AD-9 trata como estado de preflight, não falha de inicialização. A construção tardia está em `agente_redator.py:181-200`. Os testes que "pegaram isso" são os testes de API pré-existentes, que constroem a aplicação real sem chave — regressão legítima, não teste inventado para a ocasião.
- **`GET .../mensagens` não devolve o texto gerado**: nenhum AC GERAR-01..12 exige expor conteúdo por esse endpoint (GERAR-11/12 falam de etapa e progresso). Fronteira de escopo válida, remetida a 3.5.
- **Mensagem em `falhou_integracao_ia` não ganha linha em `versoes_mensagem`**: consistente — `versoes_mensagem.conteudo`/`duracao_ms`/`modelo` são `NOT NULL` e nenhum conteúdo foi produzido. `falhou_integracao_ia` é terminal (`estados_mensagem.py`), então nada a jusante precisa agir sobre ele; a causa fica na `Exceção` operacional (`test_geracao_mensagens.py:448-450` verifica ambos: versão atual `None` e a causa registrada).
- **`SuperficieGeracaoMensagens` não está montada no `App.tsx`**: idêntico a `SuperficieExecucao` (2.6), `SuperficiePreparacaoIA` (3.1) e `SuperficieEventoDecisao` — convenção pré-existente do projeto, não regressão desta história.
- **AD-010 (insert-or-noop)**: `RepositorioMensagens.criar` usa `INSERT` + tradução de `duckdb.ConstraintException` em `MensagemJaExiste`, tratado como no-op pelo caso de uso. É "ou equivalente" no sentido do AD-010 — a garantia continua sendo do banco, sem checagem "consulta e depois insere" em Python.

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
| --- | --- | --- |
| GERAR-01 | Implementing | ✅ Verified |
| GERAR-02 | Implementing | ✅ Verified (⚠️ spec-precision gap: "antes da geração") |
| GERAR-03 | Implementing | ✅ Verified |
| GERAR-04 | Implementing | ✅ Verified |
| GERAR-05 | Implementing | ✅ Verified |
| GERAR-06 | Implementing | ✅ Verified |
| GERAR-07 | Implementing | ✅ Verified |
| GERAR-08 | Implementing | ✅ Verified |
| GERAR-09 | Implementing | ✅ Verified |
| GERAR-10 | Implementing | ✅ Verified |
| GERAR-11 | Implementing | ✅ Verified |
| GERAR-12 | Implementing | ✅ Verified |

---

## Summary

**Overall**: ✅ Ready (com 3 fix tasks de robustez/precisão de teste, nenhuma bloqueante de AC)

**Verdict**: PASS ✅
**Spec-anchored check**: 12/12 ACs cobertos com evidência `file:line`; 11/12 casaram com um desfecho preciso da spec; 1 spec-precision gap (GERAR-02)
**Sensor**: 5/5 mutantes mortos
**Gate**: 630 backend + 237 frontend passed, 0 failed, 0 skipped; ruff, pyright (strict), oxlint e vite build limpos

**What works**:

- Limites por canal configuráveis com contagem em caracteres Unicode comprovada contra bytes, e fronteiras exatas (abaixo/no limite/acima) nos 4 campos limitados — não só nos corpos.
- Acionamento automático real: um único `POST /execucoes/{id}/preflight` deixa todo o lote elegível gerado; nenhuma ação de Marina por mensagem, e nenhum segundo comando HTTP inventado. O `SPEC_DEVIATION` que redireciona o gatilho de `GerenciadorExecucoes` (que de fato para em `aguardando_geracao`) para `ServicoPreflightIA._preparar_agora` foi verificado contra o código real e está correto.
- Saída ausente, em branco ou acima do limite nunca chega a `criticando`; o motivo é um código estável persistido, sem vazar o texto recusado.
- Reinvocar `gerar_lote` é no-op garantido pelo banco (`UNIQUE (elegibilidade_id, canal)`), sem regeração — comprovado pelo mutante 2.
- Nenhum teste toca a OpenAI; o prompt recebe apenas os 5 campos do `ContextoAgente` (AD-9), por construção do `montar_prompt`.

**Issues found**:

1. Fix 1 (Major): falha de infraestrutura no lote desaparece silenciosamente na task desacoplada e interrompe o restante do lote — contradiz o docstring do próprio `gerar_lote` e o padrão RUNNER-11.
2. Fix 2 (Minor): execução presa em `processando_mensagens` não é retomada no boot.
3. Fix 3 (Minor): a assertion do teste de minimização de dados não cobre o "e nada mais" que seu nome promete.

**Next steps**: rotear os 3 fixes ao implementador (Fix 1 primeiro). Nenhum deles invalida um AC desta história; os três são endurecimento e podem ser feitos junto de 3.3/3.4 se o orquestrador preferir.
