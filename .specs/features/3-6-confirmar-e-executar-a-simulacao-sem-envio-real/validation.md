# História 3.6: Confirmar e executar a simulação sem envio real — Validation

**Date**: 2026-09-04
**Spec**: `.specs/features/3-6-confirmar-e-executar-a-simulacao-sem-envio-real/spec.md`
**Diff range**: `40d60ca..08375aa` (5 commits, um por task)
**Verifier**: independent sub-agent (author ≠ verifier) — nenhuma linha de implementação ou teste foi escrita nem alterada por esta verificação

Método: a cobertura foi re-derivada do zero a partir da `spec.md` e do diff real (evidence-or-zero); as sete
deviações auto-reportadas pelo autor foram tratadas como afirmações a verificar, não como fatos. Os
resultados abaixo vêm de leitura do código de produção, execução do gate na árvore real e seis mutações
em worktree isolado.

---

## Task Completion

| Task | Status | Notes |
| --- | --- | --- |
| T1 — Migração `entregas_simuladas` | ✅ Done | Renumerada `0012`→`0014` (`0009`–`0013` consumidas por 3.1–3.5), com `SPEC_DEVIATION` no topo do `.sql`. Aplicação de L-034. |
| T2 — `RepositorioEntregasSimuladas` | ✅ Done | `criar_lote` ganhou `conexao` (`SPEC_DEVIATION` no módulo) — sem ele a atomicidade que o próprio design exige seria impossível. |
| T3 — `ServicoSimulacao` | ✅ Done | Duas transações reais confirmadas por leitura de código (não só de docstring), ver Achados §1. |
| T4 — Roteador HTTP | ✅ Done | Resumo em `GET /execucoes/{id}/simulacao` em vez de estender `GET /execucoes/{id}` (`SPEC_DEVIATION` no módulo), ver Achados §5. |
| T5 — Modal + superfície de progresso | ✅ Done | 17 testes novos de componente. Superfície ainda não ligada ao switch de `App.tsx` (risco (9) do `STATE.md`), ver Achados §6. |

---

## Spec-Anchored Acceptance Criteria

### P1: Confirmação com gate separado e reconhecimento explícito

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| SIMUL-01 — WHEN Marina abrir a confirmação de um lote decidido com ao menos uma aprovada THEN a execução SHALL estar em `aguardando_confirmacao` e a interface SHALL exibir evento, regra, período, quantidade de destinatários e distribuição entre WhatsApp, e-mail e SMS | estado `aguardando_confirmacao`; os 5 dados presentes, com a distribuição pelos três canais nomeados | `testes/test_simulacao_api.py:211` — `corpo["estado"] == "aguardando_confirmacao"`; `:213-220` — `evento["tipo"] == "chuva_intensa"`, `regra_id`, `regra_versao == 2`, `fim - inicio == timedelta(hours=6)`; `:221-226` — `total_destinatarios == 3` e `distribuicao_por_canal == [{whatsapp,0},{email,1},{sms,2}]`; `SuperficieSimulacao.test.tsx:118-122` — `'chuva_intensa na área 9990001'`, `'2026-09-04T12:00:00 até 2026-09-04T18:00:00'`, `'WhatsApp: 1, E-mail: 2, SMS: 2'`, `Destinatários` → `'5'` | ✅ PASS |
| SIMUL-02 — The system SHALL manter aprovação de conteúdo e confirmação da simulação como gates separados | a confirmação só roda a partir de `aguardando_confirmacao`, e nunca decide conteúdo | `testes/test_simulacao.py:526-530` — parametrizado em `aguardando_revisao`/`processando_mensagens`/`concluida`: `pytest.raises(EstadoNaoConfirmavel)`, `capturado.value.estado is estado`, `listar_por_execucao(...) == []`; `testes/test_simulacao_api.py:433-434` — `409` + `codigo == "estado_nao_confirmavel"`; `SuperficieSimulacao.test.tsx:132` — `confirmarSimulacao` chamado com `(EXECUCAO_ID, 3)`, só a versão do agregado, nenhuma decisão de conteúdo | ✅ PASS |
| SIMUL-03 — WHILE o modal estiver aberto e Marina não tiver reconhecido a natureza simulada THEN a ação principal SHALL permanecer bloqueada, e o modal SHALL informar explicitamente que nenhuma comunicação real será enviada | botão desabilitado até o reconhecimento; texto explícito no modal; backend recusa como defesa em profundidade | `SuperficieSimulacao.test.tsx:95` — `expect(confirmar).toBeDisabled()`; `:99` — `toBeEnabled()` após marcar; `:106-108` — `'Esta operação é uma simulação: nenhuma comunicação real é enviada aos segurados.'`; `:109-111` — checkbox com nome acessível `/nenhuma comunicação real será enviada/`; `testes/test_simulacao.py:470-476` — `pytest.raises(ReconhecimentoObrigatorio)` + `entregas == []` + estado inalterado; `testes/test_simulacao_api.py:302-307` — `422` `reconhecimento_obrigatorio`, `entregas == []` | ✅ PASS |

### P1: Reclamação atômica e criação das entregas simuladas

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| SIMUL-04 — WHEN Marina marcar e confirmar THEN o backend SHALL reverificar versão do agregado e elegibilidade das mensagens, reclamando atomicamente somente as aprovadas; nenhuma rejeitada, excluída ou em exceção SHALL integrar a simulação | exatamente as aprovadas reclamadas; rejeitada/excluída/em exceção fora, e com seu estado preservado | `testes/test_simulacao.py:383-388` — com 3 aprovadas + 1 rejeitada + 1 excluída + 1 em exceção: `len(entregas) == 3`, `{entrega.mensagem_id} == set(aprovadas)`, e cada excluída segue em `REJEITADA`/`EXCLUIDA`/`FALHOU_CONTEUDO`; `:427-429` — aprovada por Marina sem aprovação do crítico fica de fora (`entregas == [aprovada]`, `estado_de(sem_critico) is APROVADA`); `:575-580` — `versao_esperada` desatualizada levanta `ConflitoVersao` sem reclamar nada | ✅ PASS |
| SIMUL-05 — WHEN o simulador processar um lote válido THEN SHALL criar atomicamente uma entrega por mensagem e canal, sem conectores reais, e somente após o sucesso da transação as aprovadas SHALL mudar para `simulada_entregue`, preservando a relação com lote, aprovações e execução | 1 entrega por mensagem+canal; mensagens em `simulada_entregue` só pós-commit; zero conector real | `testes/test_simulacao.py:344-356` — `estado is CONCLUIDA`, `len(entregas_criadas) == 2`, canal e conteúdo por mensagem, `estado_de(sms)/estado_de(email) is SIMULADA_ENTREGUE`; `testes/test_repositorio_entregas_simuladas.py:127-128` — falha após a inserção na transação do chamador ⇒ `contar(caminho) == 0` e `listar_por_execucao == []`; `:147` — contraprova, commit persiste; `testes/test_simulacao.py:455` — teste estrutural: nenhum de `httpx/requests/urllib/smtplib/twilio/sendgrid/boto3/graph.facebook.com/api.whatsapp` no caso de uso nem no repositório | ✅ PASS |
| SIMUL-06 — WHEN o resultado de uma entrega for exibido THEN SHALL mostrar como o conteúdo seria apresentado no canal, rotulado como simulado, sem inventar confirmação ou falha de provedor externo | apresentação = cópia do conteúdo aprovado; `rotulo == "simulada"`; nenhum campo de desfecho de provedor | `testes/test_simulacao_api.py:276-289` — `rotulo == "simulada"`, `corpo == CORPO_SMS`, `assunto is None` no SMS e `== ASSUNTO_EMAIL` no e-mail, e o conjunto **exato** de campos da entrega (`{id, mensagem_id, canal, rotulo, assunto, corpo, criado_em}`) — nenhum campo de provedor; `testes/test_migracoes.py:1175-1200` — a tabela `0014` não tem coluna de desfecho de provedor; `SuperficieSimulacao.test.tsx:241-246` — `'SMS — entrega simulada'`, `'Assunto: …'`, `/Nenhuma confirmação nem falha de provedor externo/` visível | ✅ PASS |

### P1: Idempotência, concorrência e rollback local

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| SIMUL-07 — WHEN o mesmo comando for repetido com a mesma `Idempotency-Key` THEN a API SHALL devolver a simulação já registrada sem criar segunda entrega; nova execução SHALL exigir ação explícita, nova chave e nova identificação | resposta idêntica; contagem de entregas inalterada; chave reusada em outro alvo ⇒ conflito | `testes/test_simulacao.py:547-549` — `segunda == primeira`, `len(entregas) == 1`, estado `CONCLUIDA`; `testes/test_simulacao_api.py:352-355` — `200`, `segunda.json() == primeira.json()`, `len(resumo["entregas"]) == 1`; `:391-395` — mesma chave em outra execução ⇒ `409 conflito_idempotencia` e a segunda execução intocada (`entregas == []`, `aguardando_confirmacao`); `testes/test_simulacao.py:560-563` — mesma chave com outro hash ⇒ `ConflitoIdempotencia`, `len(entregas) == 1` | ✅ PASS |
| SIMUL-08 — WHEN duas confirmações concorrentes forem processadas para a mesma versão THEN somente uma SHALL reclamar e criar as entregas, e a outra SHALL receber o resultado idempotente ou `409`, sem duplicação parcial | um único conjunto de entregas; a perdedora recebe idempotente **ou** `409` | `testes/test_simulacao.py:594-599` — segunda confirmação com chave nova: `EstadoNaoConfirmavel`, `capturado.value.estado is CONCLUIDA`, `len(listar_por_execucao(...)) == 2` (o mesmo conjunto da primeira, não 4); `testes/test_simulacao_api.py:371-374` — `409 estado_nao_confirmavel` e `len(resumo["entregas"]) == 1`; `:336-338` — versão desatualizada ⇒ `409 conflito_versao` e `entregas == []`. O ponto de serialização é o `UPDATE … WHERE versao = ?` (`aplicacao/simulacao.py:527-529`), executado fora de qualquer transação de escrita, antes de qualquer entrega | ✅ PASS (ver observação sobre concorrência sequencial em Achados §4) |
| SIMUL-09 — IF uma falha local ocorrer THEN a transação das entregas SHALL ser revertida primeiro, sem entrega parcial e preservando todas as mensagens como `aprovada`; uma segunda transação idempotente SHALL mover o agregado de `simulando` para `falhou_simulacao` e persistir a exceção sanitizada local, nunca uma falha fictícia do canal | zero entrega; toda mensagem `aprovada`; execução em `falhou_simulacao`; exceção local sanitizada; transação 2 idempotente | `testes/test_simulacao.py:620-624` — `entregas == []`, ambas as mensagens `APROVADA`, **`versao` de cada uma idêntica à de antes** (`== versoes_antes`, isto é, nunca mutada, não revertida por compensação), execução em `FALHOU_SIMULACAO`; `:640-646` — `causa == "falha_local_simulacao:RuntimeError"`, `tentativas == 1`, impacto = constante, `"Chuva forte" not in causa`, e nenhum de `whatsapp/sms/email/provedor/canal` em `causa.lower()`; `:669-671` — replay da transação 2 sobre agregado já terminal: `len(excecoes_registradas()) == 1`, estado segue `FALHOU_SIMULACAO`, um único marco; `:688-691` — reenvio público após a falha é barrado em `EstadoNaoConfirmavel`, sem segunda exceção | ✅ PASS |

### P2: Retentativa correlacionada e progresso visível

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| SIMUL-10 — WHEN Marina solicitar nova tentativa a partir de `falhou_simulacao` THEN SHALL validar que todas as referências versionadas dos snapshots existem, estão completas, íntegras e com versões suportadas antes de criar qualquer registro; SHALL rejeitar sem criar execução se falhar; SHALL criar nova `ExecucaoPreventiva` em `aguardando_geracao` com novo ID, `execucao_origem_id` e chave idempotente própria; origem permanece terminal, replay não duplica | 4 modos de invalidez rejeitados sem criar nada; sucesso ⇒ `aguardando_geracao` + `execucao_origem_id`; origem intacta; replay devolve o mesmo ID | `testes/test_simulacao.py:719-725` — `nova.estado is AGUARDANDO_GERACAO`, `nova.execucao_origem_id == EXECUCAO_ID`, `nova_id != EXECUCAO_ID`, origem segue `FALHOU_SIMULACAO`, `listar_correlacionadas == [nova_id]`; `:872-873` / `:887-889` / `:904-905` / `:921-922` — os quatro motivos de `SnapshotInvalido` (sem elegibilidade, versão de regra não suportada, regra não resolvível, evento ausente), cada um com `listar_correlacionadas == []`; `:813-815` — replay: `segunda == primeira`, 1 correlacionada, 2 elegibilidades (sem cópia dupla); `:847-848` — origem fora de `falhou_simulacao` ⇒ `OrigemNaoRetentavel` | ✅ PASS |
| SIMUL-11 — WHEN Marina consultar a origem de uma execução correlacionada, ou a origem consultando suas retentativas THEN a interface SHALL permitir navegar em ambas as direções, preservando IDs, estados e marcos sem mesclar históricos | navegação nos dois sentidos; cada execução com seu ID e estado; históricos não mesclados | `testes/test_simulacao_api.py:467-472` — `resumo_nova["execucao_origem_id"] == origem_id`, `resumo_nova["estado"] == "aguardando_geracao"`, `resumo_nova["retentativas"] == []`, `resumo_origem["retentativas"] == [nova_id]`, `resumo_origem["execucao_origem_id"] is None`, `resumo_origem["estado"] == "falhou_simulacao"`; `SuperficieSimulacao.test.tsx:293-298` — da retentativa para a origem: mostra `ORIGEM_ID` e `'Falha local'`, e **`queryByText(EXECUCAO_ID)` ausente** (não mescla), com o link inverso presente; `:301+` — o sentido oposto. Metade estrutural também já exposta por `GET /execucoes/{id}` (2.6): `adaptadores/http/execucao_preventiva.py:114,120,319-322` | ✅ PASS |
| SIMUL-12 — WHILE a simulação estiver em andamento THEN a interface SHALL exibir `Bloqueada`, `Pronta`, `Simulando`, `Concluída` ou `Falha local`, com o caráter simulado permanecendo visível durante e depois | os 5 rótulos exatos, distintos; aviso de simulação visível durante e depois | `SuperficieSimulacao.test.tsx:158-164` — `it.each` mapeia `aguardando_revisao→Bloqueada`, `aguardando_confirmacao→Pronta`, `simulando→Simulando`, `concluida→Concluída`, `falhou_simulacao→Falha local`; `:185-187` — `rotulos` na ordem exata, `new Set(icones).size === 5` e `new Set(cores).size === 5` (L-024/L-016 aplicadas); `:195-199` — em `simulando` **e** em `concluida`, o texto `'Esta operação é uma simulação: nenhuma comunicação real é enviada aos segurados.'` está presente | ✅ PASS |

**Status**: ✅ 12/12 ACs cobertas e casadas com o desfecho definido na spec. 1 spec-precision gap já declarado pelo autor na `tasks.md` (status HTTP da falha local — ver Gate/Achados §3), nenhum silencioso.

---

## Edge Cases

- [x] **Edge Case 1** — mensagem aprovada por Marina cuja `versao_esperada` muda entre a decisão (3.5) e a confirmação ⇒ excluída da simulação, não simulada com dado desatualizado.
  `testes/test_simulacao.py:406-409` — a mensagem regenerada (levada a `GERANDO`, versão `+1`) não gera entrega: `[entrega.mensagem_id for entrega in entregas] == [aprovada]`, `resultado.mensagens_simuladas == (aprovada,)`, e ela segue em `GERANDO` com `versao == versao_no_modal + 1`.
  Verificação independente do mecanismo: `aplicacao/simulacao.py:618-639` recomputa a elegibilidade do estado **persistido dentro da transação** (`_mensagens_a_simular(execucao_id, conexao)`, chamado em `:563`), e nunca de um valor enviado pelo cliente — o que é estritamente mais forte que comparar um `versao_esperada` recebido. A variante "regenerada e re-aprovada por Marina, mas a nova versão nunca avaliada pelo crítico" é fechada pela segunda metade da guarda (`:635-637`), coberta por `testes/test_simulacao.py:427-429`.
- [x] **Edge Case 2** — nenhuma mensagem aprovada no momento da confirmação ⇒ rejeição com erro claro, sem simulação vazia.
  `testes/test_simulacao.py:491-494` — `NenhumaMensagemAprovada`, `entregas == []`, execução **não sai** de `AGUARDANDO_CONFIRMACAO` (nem chega a `simulando`), mensagem preservada; `testes/test_simulacao_api.py:417-421` — `422 nenhuma_mensagem_aprovada`, `entregas == []`, estado inalterado. A guarda roda antes da reclamação (`aplicacao/simulacao.py:524-525`) e é repetida dentro da transação (`:564-565`) para a corrida.
- [x] **Edge Case 3** — duas execuções distintas com lotes simuláveis simultâneos ⇒ cada simulação tratada de forma independente.
  `testes/test_repositorio_entregas_simuladas.py:169-170` — `listar_por_execucao` de uma execução devolve só a sua entrega enquanto `contar(caminho) == 2`; `testes/test_simulacao_api.py:393-395` — depois de a primeira execução simular, a segunda continua com `entregas == []` e `aguardando_confirmacao` (nenhuma interferência ao nível do caso de uso); `testes/test_simulacao.py:793-800` — origem e retentativa mantêm exatamente 1 contexto e 1 mensagem cada, contadas separadamente.

---

## Discrimination Sensor

**Isolamento**: `git worktree add <scratch> HEAD` (nunca `git stash`). `git status --porcelain` da árvore real vazio antes e depois; `git worktree list` de volta a uma única entrada. Reversão entre mutações via `git checkout -- .` dentro do scratch.

| # | Mutação | File:line (scratch) | Descrição | Killed? |
| --- | --- | --- | --- | --- |
| 1 | Colapso das duas transações em uma | `aplicacao/simulacao.py:532-538` | A transição para `falhou_simulacao` + a `Exceção` sanitizada passam a rodar **dentro** da transação 1, na mesma `conexao`, antes do re-raise — de modo que o `ROLLBACK` que preserva as mensagens também desfaz o registro da falha | ✅ Killed — 8 falhas, entre elas `test_falha_local_desfaz_as_entregas_e_preserva_as_mensagens_como_aprovada` (execução fica presa em `simulando`) e toda a cadeia de nova tentativa (`OrigemNaoRetentavel: … está em 'simulando'`) |
| 2 | Remoção da metade "crítico" da aprovação dupla | `aplicacao/simulacao.py:635-637` | Elimina o `continue` quando a avaliação crítica da última versão não existe ou não está aprovada | ✅ Killed — `test_mensagem_aprovada_por_marina_sem_aprovacao_do_critico_fica_de_fora` (`Left contains one more item`) |
| 3 | Reverificação de elegibilidade afrouxada (Edge Case 1) | `aplicacao/simulacao.py:630-631` | Passa a aceitar também `EstadoMensagem.GERANDO`, simulando a mensagem regenerada com a versão antiga ainda aprovada pelo crítico | ✅ Killed — `test_mensagem_regenerada_entre_a_decisao_e_a_confirmacao_fica_de_fora` |
| 4 | Hash idempotente sem escopo do alvo (L-027) | `adaptadores/http/simulacao.py:242` | `sha256(corpo)` em vez de `sha256(alvo + b":" + corpo)`, permitindo reuso de chave entre execuções | ✅ Killed — `test_mesma_chave_em_outra_execucao_e_conflito_de_idempotencia` (`assert 200 == 409`: a segunda execução receberia silenciosamente a resposta da primeira) |
| 5 | `UNIQUE (mensagem_id)` sem efeito prático | `repositorio_entregas_simuladas.py:143` | `INSERT OR IGNORE`, deixando uma segunda entrega da mesma mensagem ser silenciosamente descartada em vez de recusada | ✅ Killed — `test_segunda_entrega_da_mesma_mensagem_e_recusada_sem_duplicar` (`DID NOT RAISE EntregaSimuladaJaExiste`) |
| 6 | Cópia de elegibilidades do AD-012 suprimida | `aplicacao/simulacao.py:448-450` | `copiar_elegibilidades` vira no-op: a nova execução passaria a depender das linhas da origem | ✅ Killed — 3 falhas, entre elas `test_retentativa_de_origem_que_chegou_a_simulando_gera_contexto_e_mensagem_sem_colidir` e `test_nova_tentativa_copia_incluidas_e_excluidas_com_o_mesmo_snapshot` |

**Sensor depth**: P0-full (6 mutações; justificado por ser história de integridade transacional **e** a que fecha o Épico 3)
**Result**: 6/6 killed — PASS ✅

---

## Code Quality

| Principle | Status |
| --- | --- |
| Minimum code | ✅ — nenhuma abstração nova além de `ServicoSimulacao`, `RepositorioEntregasSimuladas` e os 3 endpoints que as tasks nomeiam |
| Surgical changes | ✅ — o único arquivo de produção pré-existente tocado é `repositorio_execucao_preventiva.py`, e só para acrescentar o `conexao` opcional que o SIMUL-09 torna obrigatório (marcado `SPEC_DEVIATION`, chamadores de 2.2/3.1/3.4 inalterados) |
| No scope creep | ✅ — nenhum conector, nenhum retry automático, nenhuma reconciliação (tudo declarado Out of Scope) |
| Matches patterns | ✅ — `problema()`/`problem+json`, `_hash_requisicao_escopado`, `_conexao(conexao)`, portas `Protocol`, `TransacaoDuckDB`, execução correlacionada de 2.2/3.1, todos idênticos aos das histórias anteriores |
| Spec-anchored outcome check (asserted values match spec) | ✅ — 12/12; o único desfecho não fixado pela spec (status da falha local) está declarado como spec-precision gap na `tasks.md` T4 |
| Per-layer Coverage Expectation met | ✅ — domínio/aplicação 1:1 com SIMUL-01..10; rotas com feliz + `404`/`409`/`422`/`500` para as três rotas novas |
| Every test maps to a spec requirement — no unclaimed tests | ✅ — cada docstring de teste cita SIMUL-NN, um Edge Case, ou um AD (`AD-002`/`AD-009`/`AD-010`/`AD-011`/`AD-012`) |
| Documented guidelines followed | ✅ — `AGENTS.md`/`README.md`; piso de testes de 2.2/3.1/3.5 respeitado (repositórios reais sobre banco temporário migrado, não dublês) |

Lições do projeto aplicadas e verificadas nesta história: **L-003** (status não especificado declarado, não passado em silêncio), **L-024/L-016** (5 estados distintos em texto, ícone **e** cor), **L-027** (chave idempotente escopada pelo alvo), **L-028** (cópia de snapshot asserida coluna a coluna), **L-034** (número da migração atribuído no momento da implementação), **L-043** (dupla aprovação com o caso "só uma metade vale" semeado e excluído), **L-046** (extensão de componente reusado marcada como deviation).

---

## Gate Check

- **Gate command (Build)**: `uv run --directory src/backend pytest && ruff check . && pyright` + `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`
- **Backend**: **887 passed**, 0 failed, 0 skipped (84,55s); `ruff` — `All checks passed!`; `pyright` — `0 errors, 0 warnings, 0 informations`
- **Frontend**: **285 passed** em 30 arquivos, 0 failed, 0 skipped; `npm run lint` — exit `0` (warnings `react(set-state-in-effect)` pré-existentes, presentes igualmente em `SuperficiePreparacaoIA`/`SuperficieRevisaoLote`/`SuperficieRegras`); `npm run build` — `✓ built in 232ms`
- **Test count before feature** (verificado em worktree sobre `40d60ca`, não aceito do relato do autor): backend **827** coletados; frontend **268** (285 atuais − 17 do arquivo novo `SuperficieSimulacao.test.tsx`, medidos isoladamente)
- **Test count after feature**: backend **887**, frontend **285**
- **Delta**: **+60 backend, +17 frontend**. Nenhum teste removido, nenhuma asserção enfraquecida — o diff `40d60ca..08375aa` não contém remoção de teste.
- **Skipped tests**: nenhum
- **Failures**: nenhuma

---

## Achados da verificação independente

### 1. As duas transações da falha local são genuinamente duas (verificação do ponto mais consequente da história)

Verificado por leitura do código, não da docstring. `TransacaoDuckDB.executar`
(`adaptadores/persistencia/transacao.py:32-43`) abre a própria conexão, faz `BEGIN TRANSACTION`, e em
`except BaseException` executa `ROLLBACK` **e re-levanta** — antes, portanto, de qualquer `except` do
chamador. Em `aplicacao/simulacao.py:532-538` o `except Exception` de `_confirmar_agora` só é alcançado
depois desse `ROLLBACK`, e chama `_registrar_falha_local` (`:583-616`), que abre uma **segunda**
`self._portas.transacao.executar(falhar)` — outra `abrir_conexao` + outro `BEGIN`. São dois escopos
transacionais distintos, não um. A mutação 1 do sensor prova que a distinção é discriminada pelos testes:
colapsá-las deixa a execução presa em `simulando` e derruba 8 testes.

A idempotência da transação 2 é por leitura do estado real (`:596-598`): já terminal ⇒ retorna a causa sem
transicionar e sem gravar segunda `Exceção`. A afirmação do autor de que esse replay **não é alcançável pela
API pública** também confere: `_confirmar_agora:522-523` levanta `EstadoNaoConfirmavel` antes de qualquer
efeito quando a execução não está em `aguardando_confirmacao`, e `falhou_simulacao` não está —
comprovado em `testes/test_simulacao.py:685-691`. O teste do replay
(`:649-671`) chama `_registrar_falha_local` diretamente e declara esse motivo na própria docstring, em vez
de fingir um caminho público que não existe.

### 2. `injecao_falha_teste` é inalcançável de produção

O teste citado existe e faz o que afirma: `testes/test_simulacao_api.py:521-540` roda `ast.parse` sobre
`adaptadores/http/simulacao.py` **e** `composicao/api.py` e exige `referencias == []` para nós
`ast.Name`/`ast.keyword`/`ast.arg` com esse identificador — de fato mais forte que um `grep`, e o arquivo é
lido com `read_text` (um caminho errado quebraria com `FileNotFoundError`, não passaria em silêncio).
Verificação independente por `grep` da árvore inteira: fora de `.specs/`, o identificador aparece em
`aplicacao/simulacao.py` (definição e repasse interno), em `testes/test_simulacao*.py`, e em
`adaptadores/http/simulacao.py` **apenas nas linhas 13 e 460, ambas dentro de docstrings** — exatamente o
caso que o `grep` confundiria e a AST não. Nenhuma ocorrência em `composicao/`. Confirmado.

### 3. Status `500` para a falha local: escolha isolada, sem colisão

`500` é usado em exatamente dois módulos HTTP do projeto: `dados_sinteticos.py:107,158` (outro recurso,
outro código de problema) e `simulacao.py:446,521`. Na rota de confirmação, `500` só é emitido por
`FalhaLocalSimulacao` e carrega `codigo == "falha_local_simulacao"` mais causa sanitizada e próxima ação —
todos os outros desfechos dessa rota têm status próprio (`404`/`409`/`422`). O frontend distingue pelo
`codigo`, não pelo status. Nenhuma ambiguidade a resolver. O gap de precisão da spec está declarado na
`tasks.md` T4 conforme L-003; não é preciso abrir lição nova.

### 4. SIMUL-08: "concorrentes" é exercitado como sequencial-intercalado

Os testes de SIMUL-08 disparam a segunda confirmação depois de a primeira retornar, não em paralelo real
(sem `threading`, coerente com todo o restante da suíte do projeto — nenhum teste usa threads). Isso é
suficiente porque o ponto de serialização é um único `UPDATE … WHERE versao = ?` do DuckDB
(`aplicacao/simulacao.py:527-529`), executado **antes** de qualquer escrita de entrega: quem perde a versão
nunca chega a `_simular`. Os testes provam exatamente o invariante que a spec exige ("só um conjunto de
entregas existe" — `len(...) == 1`/`== 2` conforme o lote), e a mutação 4 do sensor mostra que o escopo da
chave é discriminado. Não é lacuna; registrado por transparência.

### 5. Resumo em `GET /execucoes/{id}/simulacao` não viola SIMUL-11 — verificado estruturalmente

A afirmação do autor confere por leitura do endpoint de 2.6, não por suposição:
`adaptadores/http/execucao_preventiva.py:114` declara `execucao_origem_id: UUID | None` e `:120`
`retentativas: list[UUID]` no modelo de resposta de `GET /execucoes/{execucao_id}` (`:51`, `:253`), e
`:319-322` os preenche a partir de `snapshot.execucao_origem_id` e
`execucoes_repo.listar_correlacionadas(execucao_uuid)`. A metade "navegação origem↔retentativa" de SIMUL-11
já estava exposta ali; a rota nova acrescenta o resumo da simulação (que `GET /execucoes/{id}` não tem) e
repete os dois campos de navegação por conveniência da superfície. Deviation declarada no módulo, decisão
correta de coesão de recurso.

### 6. Observações não bloqueantes

- **`SuperficieSimulacao` é a 9ª superfície não ligada ao switch de `App.tsx`/`PerfilContexto.tsx`.** Dívida
  de projeto já registrada como risco (9) no `STATE.md`, anterior a esta história e explicitamente declarada
  fora do escopo da T5. É a recorrência do padrão de L-030; não abre lição nova nem invalida SIMUL-01/03/11/12,
  cujo comportamento de componente está asserido.
- **AD-010 e a forma da dedução.** O AD nomeia `entregas_simuladas` (3.6) como uma das cinco aplicações e
  descreve a escrita como *insert-or-noop*. `criar_lote` usa `INSERT` simples e traduz a
  `duckdb.ConstraintException` em `EntregaSimuladaJaExiste` (`repositorio_entregas_simuladas.py:148-149`).
  A propriedade que o AD-010 realmente protege — dedução no banco por `UNIQUE`, jamais um "checa depois
  insere" da aplicação — está preservada, e **levantar é a semântica correta aqui**: um lote duplicado precisa
  derrubar a transação 1, não ser silenciosamente descartado. Divergência de mecanismo, não de invariante.
- **`obter_resumo` não consta das interfaces de `ServicoSimulacao` no `design.md`.** Método novo em componente
  novo (não é a extensão de componente reusado que L-046 endereça), e a rota que o consome está marcada como
  `SPEC_DEVIATION`. Cosmético.

---

## Fix Plans

Nenhum. Nenhum gap bloqueante, nenhuma AC descoberta, nenhum mutante sobrevivente.

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
| --- | --- | --- |
| SIMUL-01 | Implementing | ✅ Verified |
| SIMUL-02 | Implementing | ✅ Verified |
| SIMUL-03 | Implementing | ✅ Verified |
| SIMUL-04 | Implementing | ✅ Verified |
| SIMUL-05 | Implementing | ✅ Verified |
| SIMUL-06 | Implementing | ✅ Verified |
| SIMUL-07 | Implementing | ✅ Verified |
| SIMUL-08 | Implementing | ✅ Verified |
| SIMUL-09 | Implementing | ✅ Verified |
| SIMUL-10 | Implementing | ✅ Verified |
| SIMUL-11 | Implementing | ✅ Verified |
| SIMUL-12 | Implementing | ✅ Verified |

---

## Summary

**Overall**: ✅ Ready

**Spec-anchored check**: 12/12 ACs casadas com o desfecho definido na spec; 3/3 Edge Cases cobertos; 0 spec-precision gaps silenciosos (1 declarado pelo autor na `tasks.md`, conforme L-003)
**Sensor**: 6/6 mutações mortas (P0-full)
**Gate**: 887 backend + 285 frontend passed, 0 failed, 0 skipped; `ruff`/`pyright`/`oxlint`/`build` limpos

**What works**:

- A sequência de falha local é genuinamente de **duas transações**: o `ROLLBACK` da transação 1 devolve zero entrega e mensagens com a `versao` de concorrência otimista **nunca mutada**, e só então uma segunda transação independente e idempotente move o agregado a `falhou_simulacao` com exceção sanitizada — verificado no código e comprovado pela mutação 1.
- A reclamação exige **dupla aprovação real** (estado `aprovada` de Marina + avaliação crítica aprovada da última versão), sempre recomputada do estado persistido dentro da transação — o que fecha, de uma vez, SIMUL-04, o Edge Case 1 e sua variante "regenerada e re-aprovada sem nova crítica".
- Idempotência escopada pelo alvo (L-027), concorrência resolvida por `UPDATE … WHERE versao = ?` antes de qualquer escrita, e `UNIQUE (mensagem_id)` como rede final do banco — as três discriminadas pelo sensor.
- Nenhum conector real de canal em lugar nenhum: `grep` do diff inteiro só encontra os termos proibidos **dentro da lista de proibidos do próprio teste estrutural**; a fixture `autouse` de bloqueio de rede reforça isso nos testes de API.
- Retentativa correlacionada com cópia de elegibilidades (AD-012) provada no cenário que esta história torna obrigatório: origem que chegou a `simulando`, com contexto e mensagem próprios, e a nova execução criando os seus sobre as cópias — 1 de cada em cada execução, contados separadamente.

**Issues found**: nenhum bloqueante. Três observações não bloqueantes em Achados §6 (superfície ainda não navegável — risco (9) pré-existente do `STATE.md`; forma da dedução do AD-010; `obter_resumo` ausente do `design.md`).

**Next steps**: marcar SIMUL-01..12 como Verified na `spec.md`, fechar a História 3.6 e o Épico 3.
