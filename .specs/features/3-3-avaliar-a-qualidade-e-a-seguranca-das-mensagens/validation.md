# História 3.3: Avaliar a qualidade e a segurança das mensagens — Validation

**Date**: 2026-09-04
**Spec**: `.specs/features/3-3-avaliar-a-qualidade-e-a-seguranca-das-mensagens/spec.md`
**Diff range**: `2484f3c..edadc86` (6 commits, um por task T1–T6)
**Verifier**: independent sub-agent (author ≠ verifier) — nenhum arquivo de implementação ou de teste foi tocado nesta verificação

---

## Task Completion

| Task | Status | Notes |
| --- | --- | --- |
| T1 — Migração `avaliacoes_criticas` | ✅ Done (`58d1488`) | Arquivo real é `0011_avaliacoes_criticas.sql`, não `0009` como o `design.md` escreve. Renumeração correta e verificada: `0009_preflight_ia.sql` (3.1) e `0010_mensagens.sql` (3.2) já ocupam os números. `SPEC_DEVIATION` registrada no `.sql`. `schema_migracoes` consistente: `test_migracoes.py` afirma `versoes_aplicadas == (1..11)` e `versao_final == 11`, e `test_inicializador.py` foi atualizado para a mesma contagem. |
| T2 — `AgenteCritico` | ✅ Done (`fb0074e`) | `avaliar(...) -> AvaliacaoCritica \| None`. `SPEC_DEVIATION` registrada no módulo (o design declarava retorno não anulável). A escolha é exigida por CRIT-07 e está verificada abaixo. |
| T3 — Nó `criticar` no `GrafoGeracaoMensagem` | ✅ Done (`9e998b8`) | Aresta condicional após `gerar` encaminha somente `DesfechoGeracao.VALIDA`. Não-invocação provada por espião, não só por inspeção. |
| T4 — `RepositorioAvaliacoesCriticas` + transição | ✅ Done (`38c7c09`) | Cinco asserções de 3.2 atualizadas de `criticando` para `aguardando_revisao`; a mudança é exigida por CRIT-05, e nenhuma asserção foi removida ou enfraquecida (conferido linha a linha no diff). |
| T5 — `GET .../avaliacao-critica` | ✅ Done (`31f6129`) | Método aditivo `RepositorioMensagens.obter_versao`; `transicionar` intocado. `openapi.json` regenerado, `test_openapi_sincronizado.py` verde. |
| T6 — `SuperficieAvaliacaoCritica` | ✅ Done (`edadc86`) | Commit finalizado pelo orquestrador após interrupção; código verificado normalmente aqui. Uma imprecisão no registro da task — ver Fix Plan 1. |

---

## Spec-Anchored Acceptance Criteria

### P1: Avaliação crítica estruturada com contexto mínimo ⭐ MVP

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| CRIT-01 — WHEN `criticando` começar para uma versão estruturalmente válida THEN o crítico SHALL receber a mensagem e o contexto mínimo | O crítico recebe exatamente o texto validado + o mesmo `ContextoAgente` de 5 campos de 3.1, sem nova montagem de contexto | `src/backend/testes/test_grafo_geracao_mensagem.py:361` — `assert critico.conteudos == [SaidaCanal(corpo=CORPO_VALIDO)]`; `:362` — `assert critico.contextos == [CONTEXTO]` (identidade do mesmo objeto que o redator recebeu); `src/backend/testes/test_agente_critico.py:204-213` — corpo, assunto, canal e os 5 campos do contexto presentes no prompt | ✅ PASS |
| CRIT-02 — The critic SHALL não poder decidir risco, elegibilidade, cobertura ou limite de canal | Nenhuma dessas quatro decisões é expressável nem alcançável pela saída do crítico | `src/backend/testes/test_agente_critico.py:242-250` — `assert parametros == {"self","modelo","temperatura","timeout_segundos","chave","modelo_de_chat"}` (sem `ValidadorSaidaCanal`, sem limite); `:258-259` — `for limite in LIMITES_CONFIGURADOS: assert limite not in enviado` (os 4 limites de 3.2 ausentes do prompt); `:180-190` — enum fechado nos 7 critérios e `assert all(proibido not in categoria.value ...)` para `risco`/`elegibilidade`/`cobertura`/`limite`; `:272` — instrução de sistema nomeia as 4 decisões que não são do crítico. Confirmado por leitura de `adaptadores/ia/agente_critico.py:94-117` (`montar_prompt`): entram apenas canal, assunto, corpo e os 5 campos do contexto | ✅ PASS |
| CRIT-03 — WHEN a saída estruturada for validada THEN ela SHALL conter decisão + motivos específicos sobre os 7 critérios | `aprovada: bool` + motivos categorizados nos 7 critérios do AC | `src/backend/testes/test_agente_critico.py:103` — `assert avaliacao == AvaliacaoCritica(aprovada=True, motivos=())`; `:120-140` — parametrizado nas 7 categorias, `assert avaliacao == AvaliacaoCritica(aprovada=False, motivos=(MotivoCritica(categoria, justificativa),))`; `:180` — as 7 categorias fechadas são exatamente os 7 critérios; `:226-235` — os 7 critérios enumerados no prompt | ✅ PASS |
| CRIT-04 — WHEN a avaliação for orquestrada sobre mensagem que viola campos/limites determinísticos THEN a reprovação determinística SHALL permanecer separada e o modelo SHALL não poder sobrepô-la | O crítico não é chamado; a mensagem não avança; nenhuma avaliação persistida | `src/backend/testes/test_grafo_geracao_mensagem.py:336-338` — `assert final["resultado"].desfecho is DesfechoGeracao.INVALIDA`; `assert critico.chamadas == 0`; `assert "resultado_critica" not in final` (espião real, não inspeção de código); `:349-351` — mesma prova para falha de transporte da geração; `src/backend/testes/test_geracao_mensagens.py:808-810` — com crítico configurado para aprovar tudo: `assert mensagem.estado is EstadoMensagem.GERANDO`, `assert cenario.critico.chamadas == 0`, `assert ...obter_por_versao(...) is None` | ✅ PASS |

### P1: Transições de estado a partir da decisão do crítico ⭐ MVP

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| CRIT-05 — WHEN aprovada pelo crítico e pelos validadores THEN o estado SHALL avançar para `aguardando_revisao`, com a aprovação agêntica visualmente distinta da futura decisão humana | Estado final `aguardando_revisao`; distinção visual da decisão humana | `src/backend/testes/test_geracao_mensagens.py:711` — `assert mensagem.estado is EstadoMensagem.AGUARDANDO_REVISAO`; `:715-717` — `agente == "critico"`, `modelo == "gpt-4o-mini"`, `duracao_ms > 0`; `src/backend/testes/test_grafo_geracao_mensagem.py:245-246` — `assert resultado.desfecho is DesfechoCritica.APROVADA` / `motivos == ()`; distinção visual: `src/frontend/src/funcionalidades/avaliacao-critica/SuperficieAvaliacaoCritica.test.tsx:138-147` — texto, `data-icone-nome` e `--cor-origem` diferentes entre `agente_ia` e `decisao_humana` | ✅ PASS |
| CRIT-06 — WHEN reprovada pelo crítico THEN os motivos SHALL ser estruturados e associados à versão avaliada, e o item SHALL ficar disponível para a próxima tentativa dentro do limite | Motivos categorizados persistidos contra a versão; item não avança | `src/backend/testes/test_geracao_mensagens.py:738-745` — `assert mensagem.estado is EstadoMensagem.CRITICANDO`; `assert avaliacao.avaliacao == AvaliacaoCritica(aprovada=False, motivos=motivos)`; `:742` — `motivos[0].categoria is CategoriaCritica.TOM`; `src/backend/testes/test_repositorio_avaliacoes_criticas.py:79-86` — ida e volta pelo banco preserva categoria e justificativa; `:106-107` — as 7 categorias percorrem o banco; migração: `src/backend/testes/test_migracoes.py:735` — `assert total == (2,)` para versões distintas | ⚠️ Spec-precision gap (parcial) |
| CRIT-07 — IF a saída for inválida/não interpretável THEN SHALL ser falha da tentativa, nunca aprovação, e a mensagem SHALL não alcançar supervisão/simulação como válida | Nunca `aprovada`; nada persistido; não avança para `aguardando_revisao` | `src/backend/testes/test_agente_critico.py:281` (`parsed` nulo), `:289` (resposta fora do envelope), `:300` (reprovação sem motivo), `:316` (motivo sem justificativa) — todas `assert avaliar(modelo) is None`; `src/backend/testes/test_grafo_geracao_mensagem.py:286-289` — `assert resultado.desfecho is DesfechoCritica.SAIDA_INVALIDA`, `is not DesfechoCritica.APROVADA`, `causa == CAUSA_SAIDA_CRITICA_INVALIDA`; `src/backend/testes/test_geracao_mensagens.py:759-761` — `estado is CRITICANDO`, `estado is not AGUARDANDO_REVISAO`, `obter_por_versao(...) is None` | ✅ PASS |

**Nota sobre a forma do retorno (CRIT-07)**: o autor resolveu a questão com `AvaliacaoCritica \| None` em vez de um embrulho `RespostaCritico` espelhando `RespostaRedator` (3.2). A escolha foi re-derivada e confirmada aqui: `avaliacoes_criticas` não persiste métrica de uso, então um embrulho de campo único seria indireção sem função; levantar exceção seria lido pelo `RetryComBackoff` como transporte (levando a `falhou_integracao_ia`, terminal que o Edge Case reserva ao transporte); e `aprovada=False` seria exatamente a reprovação estruturada de que CRIT-07 distingue a falha. As duas formas semanticamente vazias que o código recusa (`aprovada=False` sem motivos; motivo com justificativa em branco) estão testadas, e o mutante M2 confirma que a recusa é detectável.

### P2: Detalhe da avaliação acessível a Marina

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| CRIT-08 — WHEN Marina abrir o detalhe THEN a interface SHALL exibir versão, critérios, decisão, motivos, agente, modelo e duração | Os 7 itens exibidos | `src/frontend/src/funcionalidades/avaliacao-critica/SuperficieAvaliacaoCritica.test.tsx:72-77` — versão, `'2ª tentativa'`, `'critico'`, `'gpt-4o-mini'`, `'743 ms'`; `:87` — `expect(itens.map(...)).toEqual(CRITERIOS)` (os 7 critérios, na ordem); `:113` — decisão (`'Reprovada pelo agente de IA'`); `:117-124` — cada motivo com categoria e justificativa. Contrato: `src/backend/testes/test_avaliacoes_criticas_api.py:106-126` — `mensagem_id`, `versao_mensagem_id`, `numero_tentativa`, `criterios`, `aprovada`, `motivos`, `agente`, `modelo`, `duracao_ms`, `criado_em` | ✅ PASS (com ressalva de alcançabilidade — ver Fix Plan 2) |
| CRIT-09 — The interface SHALL usar linguagem acessível sem ocultar a separação IA/regras determinísticas | Separação IA × regras visível | `src/backend/testes/test_avaliacoes_criticas_api.py:147-153` — `assert corpo["origem"] == "agente_ia"`, `assert corpo["validacao_deterministica"] == {"origem": "regras_deterministicas", ...}`, `assert corpo["origem"] != corpo["validacao_deterministica"]["origem"]`; `:176-181` — aprovação do agente não apaga o motivo da recusa determinística; `SuperficieAvaliacaoCritica.test.tsx:165-167` — `expect(new Set(textos).size).toBe(3)`, `new Set(icones).size === 3`, `new Set(cores).size === 3` para as três origens; `:186-189` — validação determinística exibida com rótulo, veredito, motivo e ícone próprios | ⚠️ Spec-precision gap (parcial: "linguagem acessível" não tem outcome preciso) |

**Status**: ✅ Todos os 9 ACs cobertos com evidência `file:line` e outcome batendo com a spec; 2 spec-precision gaps flagrados nas metades vagas de CRIT-06 e CRIT-09 (nenhuma delas é uma lacuna de implementação).

**Detalhe dos spec-precision gaps:**

- **CRIT-06** — a primeira metade ("motivos estruturados associados à versão avaliada") tem outcome preciso e está verificada. A segunda metade ("o item SHALL ficar disponível para a próxima tentativa automática dentro do limite") não tem outcome observável definido nesta spec: o limite e o ciclo de regeneração são declarados Out of Scope (História 3.4). O melhor que a implementação pode provar é o estado deixado para trás (`criticando`, com a avaliação reprovada persistida), e é isso que o teste afirma. Não há defeito a corrigir; registrado para que a 3.4 defina o que "disponível dentro do limite" significa de forma asserível.
- **CRIT-09** — "linguagem acessível" não define um outcome verificável. O teste afirma o que é asserível (rótulos em português para os 7 critérios, texto explícito de que a aprovação é do agente e não de uma pessoa) e a metade precisa do critério — a separação IA × regras — está totalmente coberta, inclusive no contrato HTTP.

---

## Discrimination Sensor

Scratch isolado: `git worktree add` em dois worktrees temporários fora do repo (`.../scratchpad/wt-mut` em `edadc86`, `.../scratchpad/wt-base` em `2484f3c`). Nenhum `git stash`. Baseline `git status --porcelain` do worktree real: vazio, antes e depois; ambos os worktrees removidos com `--force` e `git worktree list` volta a listar só o repo real.

| Mutation | File:line | Description | Killed? |
| --- | --- | --- | --- |
| M1 | `src/backend/central_preventiva/aplicacao/grafos/geracao_mensagem.py:280` | Trocou os ramos aprovada/reprovada: `if avaliacao.aprovada:` → `if not avaliacao.aprovada:` | ✅ Killed (6 testes falham, incl. `test_aprovacao_do_critico_persiste_a_avaliacao_e_avanca_para_aguardando_revisao` e `test_reprovacao_do_critico_persiste_motivos_e_mensagem_permanece_em_criticando`) |
| M2 | `src/backend/central_preventiva/adaptadores/ia/agente_critico.py:133-136` | Removeu a guarda "saída inválida ≠ aprovação": ambos os `return None` viraram `return AvaliacaoCritica(aprovada=True, motivos=())` | ✅ Killed (`test_reprovacao_sem_nenhum_motivo_volta_nula`, `test_motivo_sem_justificativa_volta_nulo`) |
| M3 | `src/backend/central_preventiva/aplicacao/grafos/geracao_mensagem.py:289` | Quebrou o roteamento para que `criticar` rode mesmo com saída determinísticamente inválida: `desfecho is VALIDA` → `gerado.saida is not None` | ✅ Killed (`test_grafo_nao_invoca_o_critico_para_saida_invalida_do_redator`, `test_mensagem_reprovada_deterministicamente_nunca_recebe_avaliacao_critica`) |
| M4 | `src/frontend/src/funcionalidades/avaliacao-critica/SuperficieAvaliacaoCritica.tsx:42` | Colapsou um dos três sinais de uma origem: `decisao_humana` passou a usar a mesma cor de `agente_ia` | ✅ Killed (`distingue a aprovação agêntica da decisão humana por rótulo, ícone e cor`; `mantém as três origens de decisão distintas em texto, ícone e cor`) |
| M5 | `src/backend/central_preventiva/aplicacao/geracao_mensagens.py:268-269` | Removeu o retorno antecipado de `SAIDA_INVALIDA` em `_concluir_critica`, fazendo uma saída não interpretável persistir uma avaliação | ✅ Killed (`test_saida_invalida_do_critico_nao_persiste_avaliacao_nem_avanca`) |

**Sensor depth**: lightweight expandido (5 mutações — 4 backend, 1 frontend), concentrado no código novo de maior risco: interpretação da decisão do crítico, guarda de saída inválida, roteamento determinístico e distinção de origem na interface.
**Result**: 5/5 killed — PASS ✅

---

## Code Quality

| Principle | Status |
| --- | --- |
| Minimum code | ✅ Nenhum componente além dos 6 que as tasks pedem. Único acréscimo não listado: `RepositorioMensagens.obter_versao`, aditivo, exigido por AD-011 para escopar a versão à mensagem e por CRIT-09 para trazer o veredito determinístico. |
| Surgical changes | ✅ `transicionar` intocado; `_SELECT_VERSAO`/`_versao_de_linha` reusados; `preflight_ia.py` e `api.py` só ganham a fiação do crítico e do roteador novo. |
| No scope creep | ✅ Nenhuma configuração especulativa (crítico reusa `modelo_openai`/`temperatura_openai`, conforme a Tech Decision do design); nenhuma tentativa de implementar o ciclo de regeneração da 3.4. |
| Matches patterns | ✅ `AgenteCritico` espelha `AgenteRedator` (protocolo mínimo de chat, construção tardia do `ChatOpenAI` por causa do AD-9, exceção de transporte propagada); repositório espelha `RepositorioContextosAgente`; roteador espelha o padrão `problem+json` correlacionado; superfície espelha `SuperficieEventoDecisao`/`SuperficieExecucao` (incl. a prop `embutido`). |
| No abstractions for single-use code | ✅ Nenhum embrulho `RespostaCritico` inventado só para simetria com 3.2 — a justificativa está registrada e é correta. |
| Spec-anchored outcome check (asserted values match spec) | ✅ 9/9, 2 metades vagas explicitamente flagradas em vez de passadas em silêncio |
| Per-layer Coverage Expectation met (domain 1:1 ACs; routes happy+edge+error) | ✅ Rota nova: 200 (aprovada e reprovada), 404 × 3 códigos distintos (`mensagem_inexistente`, `versao_inexistente`, `avaliacao_inexistente`), 422, e o caso adversarial de versão de outra mensagem |
| Every test maps to a spec requirement — no unclaimed tests | ✅ Os 59 testes novos de backend e os 10 de frontend rastreiam a CRIT-01..09, aos 3 Edge Cases ou a um "Done when" de task |
| Documented guidelines followed | ✅ `AGENTS.md`, `README.md`; piso de teste em `test_agente_redator.py`/`test_grafo_geracao_mensagem.py` (3.2) respeitado — mesmo padrão de dublê, nenhuma chamada real à OpenAI em nenhum teste |
| Would senior engineer approve? | ✅ Sim. As três `SPEC_DEVIATION` são justificadas no próprio código e cada uma é exigida por um AC. |

---

## Edge Cases

- [x] **Crítico aprova mensagem que excede o limite de canal → validação determinística prevalece.** Prova mais forte que a hipótese: com o crítico configurado para aprovar tudo, uma saída de 161 caracteres em SMS nunca alcança o nó `criticar` — `test_geracao_mensagens.py:808-810` (`estado is GERANDO`, `chamadas == 0`, avaliação `None`) e `test_grafo_geracao_mensagem.py:336-338`. No contrato HTTP, uma aprovação agêntica não apaga a recusa determinística: `test_avaliacoes_criticas_api.py:176-181`.
- [x] **Falha de transporte do crítico → mesmo padrão `falhou_integracao_ia` de 3.2, sem terminal novo.** `test_grafo_geracao_mensagem.py:301-303` (`FALHOU_INTEGRACAO_IA`, `motivos == ()`, causa `"TimeoutError: conexão expirou"`, `chamadas == MAXIMO_TENTATIVAS`) e `test_geracao_mensagens.py:778-787` (estado terminal + `Exceção` operacional `falha_integracao_ia_critica:...` com o mesmo impacto isolado de 3.2). Falha intermitente ainda produz avaliação: `test_grafo_geracao_mensagem.py:323-324`.
- [x] **Replay idempotente da mesma versão → resultado persistido reaproveitado, sem nova chamada à OpenAI.** `test_geracao_mensagens.py:825-827` — depois de dois `gerar_lote()` completos: `assert cenario.critico.chamadas == 1` (contador do dublê: uma segunda chamada faria o teste falhar), `assert ...obter_por_versao(versao_id) == primeira`, `assert len(...listar_por_execucao(...)) == 1`. Reforçado no repositório (`test_repositorio_avaliacoes_criticas.py:139-144`: o segundo `salvar` devolve o mesmo id e não sobrescreve), na migração (`test_migracoes.py:738`: reavaliar a mesma versão é no-op na `UNIQUE`) e na rota (`test_avaliacoes_criticas_api.py:274-277`: consultas repetidas devolvem o mesmo detalhe, `duracao_ms` inalterada). O mecanismo real que corta a segunda chamada é a `UNIQUE (elegibilidade_id, canal)` de 3.2 (`MensagemJaExiste` faz o item retornar antes do grafo); a `UNIQUE (versao_mensagem_id)` desta migração é a segunda barreira. O comentário do `.sql` e o docstring do repositório descrevem só a segunda como se fosse o caminho principal — impreciso, mas sem efeito em comportamento.

---

## Gate Check

- **Gate command** (Build, fim de fase — backend + frontend): `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright` e `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`
- **Result**:
  - Backend: **689 passed**, 0 failed, 0 skipped (47.5s)
  - `ruff check .`: `All checks passed!` (exit 0)
  - `pyright`: `0 errors, 0 warnings, 0 informations` (exit 0)
  - Frontend: **247 passed** em 28 arquivos, 0 failed, 0 skipped
  - `npm run lint`: exit 0 (apenas os warnings `react(set-state-in-effect)`/`only-export-components` pré-existentes; `SuperficieAvaliacaoCritica.tsx:120` produz o mesmo warning que as quatro superfícies anteriores já produzem — padrão do projeto, não regressão)
  - `npm run build`: `✓ built in 243ms` (exit 0)
- **Test count before feature** (re-derivado por este Verifier, não copiado de relatório): **630 backend / 237 frontend**, medido em worktree limpo em `2484f3c` (`pytest --collect-only` → `630 tests collected`; `vitest --run` → `237 passed`). Bate com o número registrado no fechamento de 3.2.
- **Test count after feature**: 689 backend / 247 frontend
- **Delta**: **+59 backend, +10 frontend**
- **Test Integrity Check**: nenhuma contagem diminuiu; nenhum teste deletado. Cinco asserções de `test_geracao_mensagens.py` (3.2) mudaram de `CRITICANDO` para `AGUARDANDO_REVISAO` — conferido no diff: é troca de valor esperado exigida por CRIT-05, não enfraquecimento (a asserção continua sendo igualdade sobre estado exato, e um teste foi renomeado para descrever o que agora prova). Nenhuma asserção ficou menos específica.
- **Skipped tests**: nenhum.
- **Failures**: nenhuma.

---

## Fix Plans

Nenhum defeito de implementação encontrado. Os três itens abaixo são achados não-bloqueantes, registrados para o orquestrador decidir o roteamento.

### Fix 1 (Minor, documentação): o registro da T6 relata uma contagem de testes falsa

- **Root cause**: o bloco `**Status**` da T6 em `tasks.md` diz "Gate: 630 backend (inalterado) + 247 frontend testes". A contagem real ao fim da história é **689 backend** (+59). O número 630 é o baseline de 3.2 carregado adiante — provável resíduo da sessão interrompida no meio da T6. O frontend (247) está correto.
- **Impacto**: nenhum em código; a história adiciona migração, agente, repositório, rota e ~59 testes, e o registro afirma o contrário. O risco é de auditoria: um leitor futuro concluiria que a história não acrescentou cobertura de backend.
- **Fix task**: corrigir a linha de status da T6 em `tasks.md` para `689 backend + 247 frontend`.
- **Priority**: Minor.

### Fix 2 (Minor, alcançabilidade — risco carregado do projeto): `SuperficieAvaliacaoCritica` não está na navegação real

- **Root cause**: `App.tsx` só conhece `prontidao`/`restaurar-dados-sinteticos`/`documentacao-api`/`visao-geral`. A superfície nova não é importada em lugar nenhum fora da própria pasta — é a sétima superfície nessa condição, junto com `SuperficieEventoDecisao`, `SuperficieExecucao`, `SuperficieRegras`, `SuperficieFonteMeteorologica`, `SuperficiePreparacaoIA` e `SuperficieGeracaoMensagens`.
- **Impacto**: literalmente, CRIT-08 diz "WHEN Marina abrir o detalhe"; hoje ela não tem por onde abrir no app rodando. O componente existe, está completo e totalmente testado — o que falta é o roteamento.
- **Fix task**: nenhuma nesta história. É exatamente o risco (9) já registrado em `.specs/STATE.md`, aceito no fechamento de 3.1 e 3.2 pelo mesmo motivo, e pendente de uma história/task própria de integração de UI. Registrado aqui para que a contagem suba de 6 para 7 e o débito não desapareça.
- **Priority**: Minor (consistente com o tratamento dado em 3.1/3.2; não bloqueia esta história).

### Fix 3 (observação, robustez): aprovação com motivos não vazios não é recusada

- **Root cause**: `_avaliacao_de` (`adaptadores/ia/agente_critico.py:120-137`) recusa `aprovada=False` sem motivos e motivo sem justificativa, mas aceita `aprovada=True` **com** motivos. O docstring de `AvaliacaoCritica` afirma que "uma aprovação vem com `motivos` vazio", e a interface renderizaria "Aprovada pelo agente de IA" acompanhada de motivos com ícone de reprovação.
- **Impacto**: nenhum AC violado (CRIT-03 só exige decisão + motivos específicos; CRIT-07 trata do que não pode virar aprovação, e essa forma é uma aprovação legítima). Inconsistência de exibição em um caso que o modelo pode produzir.
- **Fix task**: opcional — ou normalizar (descartar motivos em aprovação), ou tratar como não interpretável, ou apenas remover a afirmação do docstring. Requer decisão, não é um bug.
- **Priority**: Cosmetic.

---

## Achado carregado adiante: fragilidade pré-existente do lote (item 12a de `.specs/STATE.md`)

Caracterização pedida explicitamente, **não** corrigida aqui (fora do escopo desta história).

`ServicoGeracaoMensagens.gerar_lote` (`aplicacao/geracao_mensagens.py:188-191`) chama `await self._gerar_item(...)` **sem nenhum `try/except`**, apesar do docstring prometer "uma falha isolada de um item nunca interrompe os demais". As únicas exceções tratadas são as esperadas por contrato (`MensagemJaExiste`, `ValueError` de canal). A task desacoplada (`adaptadores/http/preflight_ia.py:254-259`) segue sem `except` amplo e sem callback que chame `.exception()` — inalterada por esta história.

**Veredito sobre o efeito da T4**: **mesma fragilidade estrutural, com mais superfície.** A T4 não introduziu nenhum caminho desprotegido *novo* e não removeu nenhuma proteção existente — o código do crítico (`AgenteCritico` via `RetryComBackoff`, `RepositorioAvaliacoesCriticas.salvar`, a transição para `aguardando_revisao`) roda exatamente dentro do mesmo `_gerar_item` que já não tinha isolamento por item. O que mudou é a contagem de pontos de chamada de infraestrutura capazes de levantar exceção dentro desse caminho desprotegido: de **6 antes de 3.3 para 10 depois** — `avaliacoes.salvar` (`:271`), `mensagens.transicionar(..., AGUARDANDO_REVISAO)` (`:280`), `mensagens.transicionar(..., FALHOU_INTEGRACAO_IA)` (`:263`) e `_registrar_excecao` da crítica (`:260`).

Dois desses quatro são `transicionar`, que levanta `ConflitoVersaoMensagem`/`TransicaoMensagemInvalida` — a classe de erro que o item 12a nomeia como capaz de abortar o lote em silêncio. As duas chamadas novas usam a versão esperada codificada em constante (`VERSAO_APOS_CRITICANDO = 2`); a aritmética está **correta** para todos os caminhos desta história (o nó `criticar` só é alcançado depois da transição para `criticando`, que leva a versão de 1 para 2, e nenhum caminho chega a `_concluir_critica` sem passar por ela), mas é aritmética hardcoded no mesmo estilo que 3.2 já usava.

Resumindo para o registro: **nem "irrelevante" nem "estritamente pior em natureza" — é a mesma falha de isolamento, agora com ~67% mais pontos de disparo, dois deles do tipo exato que o item 12a cita.** Continua correto tratá-la como decisão de design pendente (não há terminal de execução no AD-4 para "falha técnica geral da geração de lote"), não como patch.

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
| --- | --- | --- |
| CRIT-01 | Implementing (T2) | ✅ Verified |
| CRIT-02 | Implementing (T2) | ✅ Verified |
| CRIT-03 | Implementing (T2) | ✅ Verified |
| CRIT-04 | Implementing (T3) | ✅ Verified |
| CRIT-05 | Implementing (T4) | ✅ Verified |
| CRIT-06 | Implementing (T1, T4, T6) | ✅ Verified (⚠️ spec-precision: "disponível dentro do limite" sem outcome definido — 3.4) |
| CRIT-07 | Implementing (T3) | ✅ Verified |
| CRIT-08 | Implementing (T5, T6) | ✅ Verified (⚠️ superfície ainda não roteada em `App.tsx` — risco (9) do projeto) |
| CRIT-09 | Implementing (T5, T6) | ✅ Verified (⚠️ spec-precision: "linguagem acessível" sem outcome definido) |

---

## Summary

**Overall**: ✅ Ready

**Spec-anchored check**: 9/9 ACs com evidência `file:line` e outcome batendo com a spec; 2 spec-precision gaps flagrados (metades vagas de CRIT-06 e CRIT-09, nenhuma delas lacuna de implementação)
**Sensor**: 5/5 mutantes mortos
**Gate**: 689 backend + 247 frontend passando, 0 falhas, 0 skips; ruff, pyright, oxlint e vite build limpos
**Edge Cases**: 3/3 cobertos

**What works**:

- O crítico recebe exatamente o texto validado e o mesmo objeto `ContextoAgente` de 5 campos que o redator recebeu — nenhum caminho de montagem de contexto novo foi introduzido (CRIT-01 confirmado por leitura de `montar_prompt` e por asserção de identidade, não por docstring).
- CRIT-02 é garantido por construção em três camadas independentes, todas asseridas: a assinatura de `AgenteCritico` não admite validador nem limite; nenhum dos quatro limites de 3.2 aparece no prompt; e o enum fechado não tem categoria para risco, elegibilidade, cobertura ou limite.
- CRIT-04 é provado por espião real (`critico.chamadas == 0` em dois testes de grafo e um de serviço, com o crítico configurado para aprovar tudo), não só por inspeção de código — e o mutante M3, que faz `criticar` rodar sobre saída inválida, é morto por esses testes.
- CRIT-07 tem quatro formas de saída não interpretável testadas no agente, mais o desfecho no grafo e a ausência de persistência/transição no serviço; o mutante M2 confirma que a guarda é detectável.
- O terceiro Edge Case é provado por contador de chamadas do dublê (`chamadas == 1` após dois `gerar_lote()` completos), com três barreiras independentes verificadas: `UNIQUE` de 3.2, `UNIQUE` desta migração e igualdade do registro recuperado.
- A distinção das três origens (agente de IA / regras determinísticas / decisão humana) é asserida nos três sinais simultaneamente — texto, ícone e cor, via `new Set(...).size === 3` para cada um — aplicando L-024 proativamente; a cor foi exposta como propriedade CSS no próprio elemento para ser observável, e M4 confirma que colapsar um único sinal quebra o teste.
- Migração numerada corretamente como `0011` (não `0009` como o design escreve), com `schema_migracoes` consistente em `test_migracoes.py` e `test_inicializador.py`.

**Issues found**: nenhum defeito de implementação. Três achados não-bloqueantes (Fix 1: contagem de testes falsa no registro da T6; Fix 2: superfície não roteada em `App.tsx`, risco (9) do projeto; Fix 3: aprovação com motivos não recusada, cosmético) e a caracterização do item 12a acima.

**Next steps**: fechar a História 3.3. Rotear o Fix 1 (uma linha em `tasks.md`) e considerar Fix 2 na história de integração de UI ainda não agendada.
