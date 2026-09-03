# História 3.1: Preparar a produção agêntica com dados mínimos — Validation

**Date**: 2026-09-03
**Spec**: `.specs/features/3-1-preparar-a-producao-agentica-com-dados-minimos/spec.md`
**Diff range**: `7666b0a..f2d9308` (11 commits: T1–T9 em `39493d3..0f7890d`, doc da rodada 1 em `d4b9d8d`, correção em `f2d9308`)
**Verifier**: sub-agente independente (autor ≠ verificador) — **rodada 2** (fresh; nada da rodada 1 foi tomado como fato)

> **Contexto de rodada.** A rodada 1 (`7666b0a..0f7890d`) reprovou com 3 achados: **Gap 1 (Bloqueador)** — `Idempotency-Key` não escopada pela execução alvo; **Gap 2 (Maior)** — fidelidade do snapshot copiado (AD-012) sem asserção, mutante M5 sobrevivente; **Gap 3 (Menor, não bloqueante)** — `SuperficiePreparacaoIA` fora do `App.tsx`. Esta rodada reverifica tudo do zero e checa especificamente o commit de correção `f2d9308`. O relatório da rodada 1 foi substituído por este; seus achados estão preservados na seção **Achados da rodada 1 e seu desfecho**.

---

## Task Completion

| Task | Status | Notes |
| --- | --- | --- |
| T1: dependências `langchain`/`langchain-openai`/`langgraph` | ✅ Done | `39493d3`. Versões fixadas no `pyproject.toml`; `uv.lock` regenerado. Nenhum módulo de produção as importa ainda (3.2 cobra a dívida) — coerente com o próprio texto do T1. |
| T2: migração de schema | ✅ Done | `2e8a2c2`. Entrou como `0009_preflight_ia.sql`; `0007`/`0008` já pertenciam a 2.5/2.6. Renumeração verificada correta, sem colisão. |
| T3: `RetryComBackoff[T]` | ✅ Done | `4187898`. `testes/test_coletor_com_retry.py` e `testes/test_coleta_meteorologica.py` seguem com **zero** linhas no diff da história — nenhuma regressão observável em 2.2. |
| T4: `VerificadorDisponibilidadeOpenAI` | ✅ Done | `fd28924`. Estendeu também `Configuracao` (exigido por PREFL-05/06, que não tinham task própria). |
| T5: `MontadorContextoAgente` | ✅ Done | `f78ffed`. Acrescentou `OPERANDO_COBERTURA_EXIGIDA` ao avaliador de elegibilidade, no mesmo padrão de `OPERANDO_AREA_AFETADA` (2.5). |
| T6: `RepositorioContextosAgente` | ✅ Done | `d9f51c3`. |
| T7: `ServicoPreflightIA` | ✅ Done | `4f29100` + `f2d9308`. A idempotência agora é resolvida sobre um hash escopado pelo alvo — Gap 1 fechado. |
| T8: roteador HTTP | ✅ Done | `01b66b9` + `f2d9308`. Três rotas (uma a mais que o T8 pedia, ancorada em PREFL-14). Escopo de idempotência corrigido nos dois POSTs. |
| T9: superfície de bloqueio | ✅ Done | `0f7890d`. `npm run verificar-tipos-api` foi executado na rodada 1 contra o backend real (verde); `f2d9308` não toca o frontend, e a suíte de 229 testes segue idêntica. Componente ainda fora do `switch` de `App.tsx` (risco (9) pré-existente do Handoff, comum às superfícies 2.3–2.6). |

---

## Spec-Anchored Acceptance Criteria

### P1: Preflight de disponibilidade antes de qualquer geração

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| PREFL-01 — WHEN execução exclusivamente em `aguardando_geracao` tiver a etapa agêntica preparada THEN verificar configuração e disponibilidade antes de gerar qualquer mensagem | Nenhuma verificação nem geração fora de `aguardando_geracao`; verificação real antes de tudo | `src/backend/testes/test_preflight_ia.py:526` — `assert cenario.verificador.chamadas == 0` e `:527` `assert cenario.execucoes.transicoes == []` para `coletando`/`sem_risco`/`falhou_preparacao_ia`/`concluida`; `src/backend/testes/test_preflight_ia_api.py:297` — `409 estado_nao_preparavel` | ✅ PASS (confirmado pelo mutante **M7**, morto nesta rodada) |
| PREFL-02 — WHEN o preflight for bem-sucedido THEN transicionar automática e idempotentemente para `processando_mensagens` | Estado final exatamente `processando_mensagens`; repetir não reverifica nem retransiciona | `src/backend/testes/test_preflight_ia.py:365` — `assert cenario.execucoes.transicoes == [(EXECUCAO_ID, 1, EstadoExecucao.PROCESSANDO_MENSAGENS)]`; `:501` — `assert cenario.verificador.chamadas == 0` / `:502` `transicoes == []` no no-op idempotente; `src/backend/testes/test_preflight_ia_api.py:177` — `assert corpo["estado"] == "processando_mensagens"` | ✅ PASS |
| PREFL-03 — IF chave ausente/inválida ou OpenAI indisponível THEN terminal `falhou_preparacao_ia` ao esgotarem as tentativas, sem nenhuma chamada de geração | Estado exatamente `falhou_preparacao_ia`, após 3 tentativas, zero contextos, zero geração | `src/backend/testes/test_preflight_ia.py:418` — `assert cenario.verificador.chamadas == 3`; `:420` — `transicoes == [(EXECUCAO_ID, 1, EstadoExecucao.FALHOU_PREPARACAO_IA)]`; `:429` — `assert cenario.contextos.salvos == []`; `src/backend/testes/test_verificador_disponibilidade_openai.py:77` — `assert espiao.requisicoes == []` (chave ausente, sem rede) | ✅ PASS — **lacuna da rodada 1 fechada**: uma execução distinta nunca mais herda o desfecho de outra (`test_preflight_ia_api.py:279`) |
| PREFL-04 — WHEN alcançar `falhou_preparacao_ia` THEN exceção sanitizada, resultados determinísticos preservados, sem valor/fragmento/cabeçalho/detalhe da credencial | `Exceção` própria com causa sanitizada; nenhuma ocorrência da chave em resultado, exceção ou resposta HTTP | `src/backend/testes/test_preflight_ia.py:423` — `assert cenario.excecoes.registradas == [(EXECUCAO_ID, INDISPONIVEL.causa, 3, IMPACTO_PREPARACAO_IA)]` (a `Exceção` é chaveada pela própria execução); `src/backend/testes/test_verificador_disponibilidade_openai.py:158-160` — `assert CHAVE_SINTETICA not in resultado.causa`, `not in repr(resultado)`, `assert "Bearer" not in resultado.causa`; `src/backend/testes/test_preflight_ia_api.py:199` — a chave sintética não aparece na resposta | ✅ PASS — **lacuna da rodada 1 fechada** (a execução alvo errada agora recebe 409, nunca o registro alheio) |
| PREFL-05 — SHALL manter modelo, temperatura, **demais parâmetros suportados**, versão de prompt e limites operacionais configuráveis e documentados; chave real só de `OPENAI_API_KEY` | Spec **não enumera** quais são os "demais parâmetros suportados" | `src/backend/testes/test_configuracao.py:207-210` — `assert configuracao.modelo_openai == "gpt-4o-mini"`, `temperatura_openai == 0.2`, `versao_prompt == "v1"`, `timeout_openai_segundos == 15.0`; `:278` — `.env.example` documenta as 4 chaves + `OPENAI_API_KEY`; `src/backend/central_preventiva/composicao/configuracao.py:45` — `SecretStr` com `validation_alias="OPENAI_API_KEY"` | ⚠️ Spec-precision gap (inalterado desde a rodada 1: a cláusula "demais parâmetros suportados" não tem valor definido na spec; modelo/temperatura/versão de prompt/limite operacional estão cobertos e validados) |

### P1: Inicialização segura e nova tentativa correlacionada

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| PREFL-06 — IF configuração estrutural ausente/malformada/incompatível THEN bloquear a própria inicialização com erro sanitizado, antes de qualquer execução | Falha de inicialização (não de execução), mensagem sem o valor recebido | `src/backend/testes/test_configuracao.py:246` — `pytest.raises(ValidationError)` para modelo/temperatura/versão/timeout malformados; `:260` — `assert valor_sensivel not in str(captura.value)` | ✅ PASS |
| PREFL-07 — WHEN Marina solicitar nova tentativa a partir de `falhou_preparacao_ia` THEN validar que todas as referências versionadas dos snapshots existem, estão completas, íntegras e em versões suportadas **antes de criar qualquer registro** | Recusa antes de qualquer `INSERT` | `src/backend/testes/test_preflight_ia.py:669` — 5 classes de corrupção parametrizadas, `motivo_esperado in excecao.value.motivo` e `cenario.execucoes.criadas == []`; `:685` — regra versionada irresolvível | ✅ PASS |
| PREFL-08 — IF a validação falhar THEN comando rejeitado sem criar execução nova | Nenhuma execução criada | `src/backend/testes/test_preflight_ia.py:647` — `assert cenario.execucoes.criadas == []` e `elegibilidades.copias == []`; `src/backend/testes/test_preflight_ia_api.py:465` — `assert resposta.json()["codigo"] == "snapshot_invalido"` e `:466` `retentativas == []` | ✅ PASS |
| PREFL-09 — IF a validação passar THEN nova `ExecucaoPreventiva` em `aguardando_geracao`, novo `execucao_id`, `execucao_origem_id` e **chave idempotente própria**; origem permanece terminal; replay não duplica | Estado exatamente `aguardando_geracao`, origem intacta em `falhou_preparacao_ia`, replay devolve o mesmo id, **chave de outra origem não é reaproveitada** | `src/backend/testes/test_preflight_ia.py:573-577` — `nova_id != EXECUCAO_ID`, `nova.execucao_origem_id == EXECUCAO_ID`, `snapshots[EXECUCAO_ID].estado == FALHOU_PREPARACAO_IA`; `:599` — replay devolve o mesmo id sem criar segunda execução; `src/backend/testes/test_preflight_ia_api.py:428-430` — `assert resposta.status_code == 409`, `codigo == "conflito_idempotencia"`, `retentativas == []` para a origem alheia; conteúdo da cópia AD-012 em `src/backend/testes/test_preflight_ia.py:799-806` | ✅ PASS — **Gap 1 e Gap 2 da rodada 1 fechados** (mutantes **M-A** e **M5** mortos) |
| PREFL-10 — WHEN consultar origem ↔ retentativas THEN navegar nas duas direções, preservando IDs, estados e marcos sem mesclar históricos | Ambas as direções; marcos não mesclados | `src/backend/testes/test_preflight_ia_api.py:358` — `nova["execucao_origem_id"] == str(origem_id)`; `:364` — `origem["retentativas"] == [nova_id]`; `:367` — `[m["marco"] for m in origem["marcos"]] == ["falhou_preparacao_ia"]`; `:369` — `nova["marcos"] == []`; `src/frontend/src/funcionalidades/preparacao-ia/SuperficiePreparacaoIA.test.tsx:193` e `:208` — `expect(aoNavegar).toHaveBeenCalledWith(NOVA_ID)` / `(ORIGEM_ID)` | ✅ PASS |

### P1: Contexto mínimo do agente redator

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| PREFL-11 — WHEN o contexto for montado THEN conter somente evento, localização aproximada, contexto/coberturas relevantes, canal e orientações de segurança | Exatamente 5 campos, nem um a mais | `src/backend/testes/test_montador_contexto_agente.py:88` — `assert {campo.name for campo in dataclasses.fields(ContextoAgente)} == {"evento", "localizacao_aproximada", "coberturas_relevantes", "canal", "orientacoes_seguranca"}`; `:115` — igualdade de valor com o `ContextoAgente` esperado | ✅ PASS (mutante M3 da rodada 1, morto) |
| PREFL-12 — SHALL excluir documentos, informações financeiras, dados de pagamento, credenciais e qualquer dado não necessário | Nenhum valor nem nome de campo sensível alcança o objeto produzido | `src/backend/testes/test_montador_contexto_agente.py:127` — `for sensivel in sensiveis: assert sensivel.valor_observado not in serializado` e `assert sensivel.operando not in serializado`; `:100` — `assert not hasattr(contexto, "__dict__")` + `pytest.raises(FrozenInstanceError)` | ✅ PASS (mutante M3 da rodada 1, morto; reforçado por **M6** nesta rodada — item excluído do público não gera contexto) |
| PREFL-13 — WHEN a proveniência for registrada THEN armazenar categorias usadas e não usadas, sem copiar conteúdo sensível para logs | Duas listas de **nomes de categoria**; nada de conteúdo em log | `src/backend/testes/test_repositorio_contextos_agente.py:43` — persiste conteúdo + as duas listas; `:112` — `test_persistencia_nao_registra_o_conteudo_do_contexto_em_log`; `src/backend/testes/test_preflight_ia.py:375` — categorias usadas/não usadas conferidas contra as constantes | ✅ PASS |
| PREFL-14 — WHEN Marina consultar a proveniência antes ou depois da geração THEN exibir essas categorias | As duas listas de categorias, sem conteúdo | `src/backend/testes/test_preflight_ia_api.py:329` — `assert registros[0]["categorias_usadas"] == list(CATEGORIAS_UTILIZADAS)`; `:331` — `assert "sms" not in resposta.text`; `:332` — `assert AREA not in resposta.text` | ✅ PASS (⚠️ "exibir" satisfeito na camada de API; nenhuma superfície de UI consome a rota — coerente com o mapeamento T6/T8 da própria spec) |
| PREFL-15 — IF campo obrigatório ausente/inconsistente na montagem de um item THEN só esse item alcança terminal de exceção, sem enviar solicitação parcial à OpenAI | Um item em exceção, os demais montados, zero chamadas por item | `src/backend/testes/test_preflight_ia.py:463` — `assert cenario.verificador.chamadas == 1`; `:464` — `excecoes.registradas == [(EXECUCAO_ID, f"contexto_invalido:{invalido.id}:coberturas_relevantes", 1, IMPACTO_ITEM_SEM_CONTEXTO)]`; `src/backend/testes/test_montador_contexto_agente.py:221` — falha de um item não impede o seguinte | ✅ PASS |

### P2: Explicação de indisponibilidade sem substituto artificial

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| PREFL-16 — IF a OpenAI não estiver disponível THEN não substituir a resposta por texto fixo, simulador de modelo ou outro provedor | Nenhum conteúdo de mensagem exibido; afirmação explícita de que nada foi gerado | `src/frontend/src/funcionalidades/preparacao-ia/SuperficiePreparacaoIA.test.tsx:119` — `'Nenhuma mensagem foi gerada e nada foi escrito no lugar dela'`; `:134` — `expect(screen.queryByText(/Prezado\|Comunicado preventivo\|Olá,/)).not.toBeInTheDocument()`. Backend: nenhum caminho de geração existe nesta história (`verificador.chamadas` é a única saída externa) | ✅ PASS |
| PREFL-17 — WHEN o bloqueio ocorrer THEN a interface explica a causa e a próxima ação segura | Causa sanitizada real (não inventada) + ação de nova tentativa | `src/frontend/src/funcionalidades/preparacao-ia/SuperficiePreparacaoIA.test.tsx:104` — `expect(bloqueio).toHaveTextContent(CAUSA)`; `:105` — `'Nenhuma mensagem preventiva é gerada nesta execução.'`; `:106` — `'solicite uma nova tentativa'`; causa persistida no marco: `src/backend/testes/test_preflight_ia_api.py:368` — `assert origem["marcos"][0]["causa"] == "A credencial da OpenAI foi recusada."` | ✅ PASS (⚠️ componente ainda não roteado em `App.tsx` — risco (9) pré-existente, comum às superfícies 2.3–2.6) |

**Status**: ✅ 16/17 ACs com o desfecho da spec asserido; 1 ⚠️ Spec-precision gap (PREFL-05, inalterado e já registrado como lição L-029). **Nenhum AC sem evidência.** Os 3 Edge Cases estão tratados.

---

## Edge Cases

- [x] **EC1 — IF o preflight for repetido com a mesma condição de indisponibilidade em execuções diferentes THEN cada execução SHALL registrar sua própria exceção, sem compartilhar ou reutilizar o registro de outra** — ✅ **tratado nesta rodada**.
  - *Cláusula "sem compartilhar ou reutilizar"*: `src/backend/testes/test_preflight_ia_api.py:279-283` — mesma `Idempotency-Key` numa execução diferente devolve `409 conflito_idempotencia` e a execução alvo permanece em `aguardando_geracao`, sem herdar o desfecho da primeira; `:428-430` — o mesmo para `nova-tentativa-ia`, com `retentativas == []` na origem alheia.
  - *Cláusula "cada execução registra sua própria exceção"*: a `Exceção` e o marco são gravados chaveados pelo `execucao_id` (`aplicacao/preflight_ia.py:433` e `:436`), asserido em `src/backend/testes/test_preflight_ia.py:423` e `:427`. **Sonda descartável deste Verifier** (worktree isolado, removida): duas execuções distintas, mesma indisponibilidade, chaves distintas → cada uma termina em `falhou_preparacao_ia` com `execucao_id`, marco e instante próprios, nada compartilhado. Ver *Sondas adicionais*.
- [x] EC2 — chave válida mas modelo configurado fora do catálogo → falha de preparação com causa sanitizada: `src/backend/testes/test_verificador_disponibilidade_openai.py:111` — `test_modelo_ausente_do_catalogo_resulta_em_falha_de_preparacao_nao_em_sucesso`, `resultado.disponivel is False` e causa citando apenas o nome do modelo configurado (mutante M1 da rodada 1, morto).
- [x] EC3 — segurado sem coberturas relevantes ao evento → tratado como campo obrigatório ausente para esse item: `src/backend/testes/test_montador_contexto_agente.py:170` — `assert erro.campo == CATEGORIA_COBERTURAS` e `assert erro.elegibilidade_id == ELEGIBILIDADE_ID`.

---

## Discrimination Sensor

**Isolamento**: `git worktree add <scratch> HEAD` (nunca `git stash`). Baseline `git status --porcelain` do worktree real: **vazio antes e depois** das 4 mutações e das 2 sondas; `git worktree list` voltou a listar apenas o repositório principal. Verificado explicitamente ao fim de cada bloco.

| Mutation | File:line | Description | Killed? |
| --- | --- | --- | --- |
| **M-A** (sensor de regressão do Gap 1) | `src/backend/central_preventiva/adaptadores/http/preflight_ia.py:256` e `:331` | Reverteu a própria correção: `_hash_requisicao_escopado(execucao_id, corpo)` → `sha256(corpo).hexdigest()` nos dois POSTs | ✅ **Killed** — exatamente 2 falhas: `test_reusar_a_chave_em_outra_execucao_devolve_conflito_sem_reaproveitar_a_resposta` (`assert 202 == 409`) e `test_reusar_a_chave_de_nova_tentativa_em_outra_origem_devolve_conflito`. Nenhum outro teste falha, o que prova que o **replay legítimo** (mesma chave, mesma execução) continua passando nos dois mundos e não foi quebrado pela correção. |
| **M5** (reinjeção do sobrevivente da rodada 1) | `src/backend/central_preventiva/adaptadores/persistencia/repositorio_elegibilidade.py:192` | Quebrou a fidelidade do snapshot copiado: `SELECT ... nome_segurado, justificativa` → `SELECT ... 'ANONIMO', ''` | ✅ **Killed** — `test_retentativa_de_origem_com_contextos_monta_os_da_copia_sem_violar_a_unique` falha em `test_preflight_ia.py:799` com `assert 'ANONIMO' == 'Pessoa Teste'`. Na rodada 1 os 524 testes ficavam verdes com a cópia adulterada. |
| **M6** (nova, escolha deste Verifier) | `src/backend/central_preventiva/aplicacao/preflight_ia.py:499` | Removeu o filtro de público: `if not registro.elegivel: continue` → `if False: continue`, montando e persistindo contexto também para os **excluídos** do público elegível (vazamento de minimização de dados no nível da população) | ✅ **Killed** — 5 falhas, incl. `test_item_excluido_do_publico_nao_recebe_contexto`, `test_proveniencia_expoe_as_categorias_usadas_e_nao_usadas` e o cenário integrado contra DuckDB real |
| **M7** (nova, escolha deste Verifier) | `src/backend/central_preventiva/aplicacao/preflight_ia.py:425` | Removeu a guarda de estado do PREFL-01: `if snapshot.estado != AGUARDANDO_GERACAO: raise EstadoNaoPreparavel(...)` → `if False:`, permitindo preflight a partir de qualquer estado | ✅ **Killed** — 5 falhas: os 4 estados parametrizados de `test_execucao_fora_de_aguardando_geracao_nao_e_preparavel` (`coletando`, `sem_risco`, `falhou_preparacao_ia`, `concluida`) e `test_preflight_de_execucao_fora_de_aguardando_geracao_devolve_409` |

**Sensor depth**: lightweight (4 mutações: 2 de regressão dirigidas aos gaps da rodada 1, 2 novas sobre o código de maior risco remanescente — minimização de dados no nível da população e a guarda de estado do preflight)
**Result**: **4/4 killed** — ✅ PASS

### Sondas adicionais (não-mutação, worktree isolado, descartadas)

1. **EC1, cláusula positiva** — duas execuções distintas, mesma indisponibilidade (`401 invalid_api_key`), `Idempotency-Key` distintas: cada resposta traz o seu próprio `execucao_id`, ambas terminam em `falhou_preparacao_ia` e cada uma tem **exatamente um** marco `falhou_preparacao_ia`, com causa sanitizada e instante próprios. Nada compartilhado ou reutilizado.
2. **Replay com o UUID escrito em maiúsculas** — `POST /execucoes/{uuid-minúsculo}/preflight` seguido de `POST /execucoes/{UUID-MAIÚSCULO}/preflight` com a mesma chave devolve `202` e depois `409 conflito_idempotencia`, em vez de replay. Ver *Observações*: comportamento **fail-closed**, sem violação de AC.

---

## Code Quality

| Principle | Status |
| --- | --- |
| Minimum code | ⚠️ `langchain`/`langchain-openai`/`langgraph` seguem como dependências de runtime sem import de produção nesta história (T1 pediu explicitamente; cash-in em 3.2). A correção `f2d9308` acrescenta 1 helper de 2 linhas úteis — mínimo possível. |
| Surgical changes | ✅ `f2d9308` toca 3 arquivos, 93 inserções e **2** deleções (as duas linhas de hash substituídas). Nenhum outro comportamento alterado. |
| No scope creep | ✅ 3 adições fora do texto das tasks (`GET /execucoes/{id}/contextos`, marcos de preflight, extensão de `Configuracao`) — todas ancoradas em ACs que nenhuma task cobria (PREFL-14, PREFL-16/17, PREFL-05/06); julgadas legítimas na rodada 1 e reconferidas aqui. |
| Matches patterns | ✅ Idempotência AD-002, `problem+json` AD-011, concorrência otimista AD-008, execução correlacionada AD-009, cópia de snapshot AD-012, migração numerada AD-001/AD-015 |
| Spec-anchored outcome check | ⚠️ 16/17 asseridos contra o valor da spec; PREFL-05 tem cláusula sem valor definido (lição L-029) |
| Per-layer Coverage Expectation met | ✅ Domínio 1:1 com PREFL-11..15; rotas cobrem feliz + borda + erro, **incluindo agora o caminho "mesma chave, execução diferente"** nos dois POSTs, e a fidelidade de conteúdo da cópia AD-012 |
| Every test maps to a spec requirement | ✅ Os 2 testes novos citam AD-002 no docstring e ancoram o Edge Case 1; nenhum teste órfão |
| Documented guidelines followed | ✅ `AGENTS.md`, `README.md`, `adaptadores/persistencia/README.md` |
| No abstractions for single-use code | ✅ `RetryComBackoff[T]` tem 2 consumidores reais (2.2 e 3.1); `_hash_requisicao_escopado` tem 2 chamadores |
| Didn't "improve" unrelated code | ✅ Suíte de 2.2 intacta (0 linhas de diff em `test_coletor_com_retry.py` / `test_coleta_meteorologica.py`) |
| Test integrity | ✅ `f2d9308` não remove **nenhuma** linha de teste (`git show f2d9308 -- src/backend/testes` tem 0 deleções) e não enfraquece nenhuma asserção — o teste do AD-012 foi **fortalecido**, não relaxado |
| Would senior engineer approve? | ✅ Sim |

---

## Gate Check

- **Gate command (Build, fim de fase — `tasks.md` §Gate Check Commands)**: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright` + `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`
- **Result** (executado por este Verifier sobre a árvore real em `f2d9308`):
  - Backend: **526 passed**, 0 failed, 0 skipped (exit 0)
  - `ruff check .`: *All checks passed!* (exit 0)
  - `pyright`: 0 errors, 0 warnings, 0 informations (exit 0)
  - Frontend: **229 passed** (26 arquivos), 0 failed, 0 skipped (exit 0)
  - `oxlint`: exit 0 (apenas warnings pré-existentes de `set-state-in-effect`/`only-export-components`, o mesmo padrão já presente nas 4 superfícies anteriores)
  - `vite build`: ✓ built (exit 0)
- **Test count before feature**: 414 backend / 219 frontend
- **Test count after round 1**: 524 backend / 229 frontend
- **Test count after round 2**: **526 backend / 229 frontend**
- **Delta**: +112 backend, +10 frontend em relação ao pré-história; **+2 backend** na correção (os dois testes de reuso de chave entre execuções)
- **Skipped tests**: nenhum
- **Failures**: nenhuma
- **Test integrity**: nenhum teste removido em nenhuma das duas rodadas; nenhuma asserção enfraquecida; uma asserção **fortalecida** (`test_retentativa_de_origem_com_contextos_monta_os_da_copia_sem_violar_a_unique`, +8 comparações de conteúdo)

---

## Achados da rodada 1 e seu desfecho

| Rodada 1 | Severidade | Desfecho na rodada 2 | Evidência |
| --- | --- | --- | --- |
| **Gap 1** — `Idempotency-Key` não escopada pela execução alvo: os dois POSTs têm corpo sempre vazio, então `sha256(corpo)` produzia o mesmo hash para qualquer execução, e a mesma chave reaproveitada devolvia silenciosamente a resposta gravada por outra execução (Edge Case 1 violado; PREFL-03/04/09 afetados) | Bloqueador | ✅ **Fechado** | `f2d9308` acrescenta `_hash_requisicao_escopado(identificador_alvo, corpo)` = `sha256(alvo.encode() + b":" + corpo)` (`adaptadores/http/preflight_ia.py:127-137`), usado nos dois POSTs (`:256`, `:331`) com o id do caminho. Verificado de três formas independentes: (a) leitura do código e do fluxo de `ConflitoIdempotencia` → `409` (`:269`, `:353`); (b) os 2 testes novos com asserções reais de status, `codigo` e estado intocado da execução alvo; (c) **mutante M-A** — revertida a correção, exatamente esses 2 testes falham |
| **Gap 2** — fidelidade do snapshot copiado (AD-012) sem nenhuma asserção de conteúdo; mutante M5 sobrevivia aos 524 testes | Maior | ✅ **Fechado** | `test_preflight_ia.py:795-806` compara `nome_segurado`, `justificativa`, `canal`, `criterios`, `evento_id`, `regra_id`, `segurado_id`, `apolice_id` de cada linha copiada contra a original (casadas por `elegivel`). **M5 reinjetado nesta rodada morre** com `assert 'ANONIMO' == 'Pessoa Teste'` |
| **Gap 3** — `SuperficiePreparacaoIA` fora do `switch` de `App.tsx` | Menor (não bloqueante) | ⏭️ **Inalterado, como esperado** | Risco (9) pré-existente do Handoff, comum a `SuperficieEventoDecisao`, `SuperficieExecucao`, `SuperficieRegras` e `SuperficieFonteMeteorologica`. Pertence à história de integração de UI ainda não agendada; explicitamente fora do escopo desta correção e **não** bloqueia a 3.1 |

### Julgamentos da rodada 1 reconferidos por amostragem

Os 4 marcadores `SPEC_DEVIATION` e as adições não declaradas (migração `0009`, rota `GET /execucoes/{id}/contextos`, marcos `falhou_preparacao_ia`/`preparacao_ia_concluida`, regeneração de `tipos-gerados.ts`, extração de `RetryComBackoff[T]`) foram julgados aceitáveis na rodada 1, com raciocínio registrado. Este Verifier reconferiu por amostragem os dois de maior risco e mantém os veredictos:

- **`preparar(..., chave_idempotencia, hash_requisicao)`** — na rodada 1 era "aceitável na forma, incompleta na execução" (era a origem do Gap 1). Reconferido: a decisão de resolver a idempotência onde o efeito acontece continua correta pelo AD-002, e **agora a chave de escopo também está correta**. Veredicto elevado a ✅ aceitável.
- **Marcos `falhou_preparacao_ia` / `preparacao_ia_concluida`** — reconferido que a causa gravada no marco é a mesma já sanitizada na origem pelo `VerificadorDisponibilidadeOpenAI` e que nenhum dos 4 marcos de `GerenciadorExecucoes` (2.6) colide. ✅ aceitável.

---

## Observações (não são gaps; nenhum AC violado)

1. **Replay com o UUID em forma textual diferente devolve 409, não a resposta gravada.** O hash usa a string crua do caminho (`execucao_id`), não a forma canônica de `str(execucao_uuid)`. Sonda deste Verifier: repetir a mesma chave com o mesmo UUID em **maiúsculas** devolve `409 conflito_idempotencia` em vez do replay. É **fail-closed** — nada é duplicado e nenhum registro alheio é devolvido, então PREFL-09 ("o replay do comando SHALL não duplicar execução nem efeito") continua satisfeito. Registrado apenas como nota de robustez: canonizar com `str(execucao_uuid)` deixaria o replay tolerante à forma textual, se algum dia interessar.
2. **A cláusula positiva do EC1 é verificada, mas por sonda, não por teste versionado.** "Cada execução registra sua própria exceção" está garantida estruturalmente (a escrita é chaveada por `execucao_id`) e foi confirmada empiricamente pela sonda 1; a cláusula que efetivamente falhou na rodada 1 ("sem compartilhar ou reutilizar") está asserida em `test_preflight_ia_api.py:279` e `:428`. Um teste com duas execuções fechando explicitamente a cláusula positiva seria um reforço barato numa história futura.
3. **Risco de mesmo padrão fora do escopo desta história.** `adaptadores/http/meteorologia.py:331`, `:395` e `:466` ainda calculam `sha256(await requisicao.body()).hexdigest()` com o alvo vindo só do caminho (2.2). É a mesma construção que produziu o Gap 1. **Fora do escopo da 3.1** — mantido como risco a revisitar, exatamente como registrado na rodada 1. A lição L-027 já cobre a regra geral.

---

## Requirement Traceability Update

| Requirement | Previous Status (rodada 1) | New Status (rodada 2) |
| --- | --- | --- |
| PREFL-01 | ✅ Verified | ✅ Verified |
| PREFL-02 | ✅ Verified | ✅ Verified |
| PREFL-03 | ⚠️ Verified with gap (Fix 1) | ✅ Verified |
| PREFL-04 | ⚠️ Verified with gap (Fix 1) | ✅ Verified |
| PREFL-05 | ⚠️ Spec-precision gap | ⚠️ Spec-precision gap (inalterado; lição L-029) |
| PREFL-06 | ✅ Verified | ✅ Verified |
| PREFL-07 | ✅ Verified | ✅ Verified |
| PREFL-08 | ✅ Verified | ✅ Verified |
| PREFL-09 | ❌ Needs Fix (Fix 1, Fix 2) | ✅ Verified |
| PREFL-10 | ✅ Verified | ✅ Verified |
| PREFL-11 | ✅ Verified | ✅ Verified |
| PREFL-12 | ✅ Verified | ✅ Verified |
| PREFL-13 | ✅ Verified | ✅ Verified |
| PREFL-14 | ✅ Verified | ✅ Verified |
| PREFL-15 | ✅ Verified | ✅ Verified |
| PREFL-16 | ✅ Verified | ✅ Verified |
| PREFL-17 | ✅ Verified | ✅ Verified |

---

## Summary

**Overall**: ✅ Ready

**Verdict**: **PASS**

**Spec-anchored check**: 16/17 ACs asseridos contra o desfecho definido pela spec; 1 ⚠️ spec-precision gap (PREFL-05, cláusula "demais parâmetros suportados" — defeito da spec, não da implementação, já registrado como lição L-029). Nenhum AC sem evidência. **Os 3 Edge Cases estão tratados**, incluindo o EC1 que reprovou a rodada 1.
**Sensor**: 4 mutações injetadas, **4 mortas, 0 sobreviventes**.
**Gate**: 526 backend + 229 frontend passed, 0 failed, 0 skipped; ruff, pyright, oxlint e vite build todos exit 0.

**What works**:

- **Gap 1 fechado com prova de regressão.** A `Idempotency-Key` agora é escopada pelo alvo: a mesma chave usada numa execução diferente devolve `409 conflito_idempotencia` e a execução alvo permanece intocada, sem herdar o desfecho da primeira. O mutante M-A (reversão da correção) mata exatamente os 2 testes novos e nenhum outro — prova simultânea de que o defeito é detectado e de que o **replay legítimo** (mesma chave, mesma execução) continua devolvendo a resposta gravada sem refazer o preflight.
- **Gap 2 fechado com prova de regressão.** A fidelidade do snapshot copiado (AD-012) é agora asserida campo a campo; o mutante M5, que sobreviveu à rodada 1 inteira, morre.
- Preflight real (`GET /v1/models`) com política única de 3 tentativas e backoff 1s/2s, transicionando corretamente para `processando_mensagens` ou `falhou_preparacao_ia`, sem nenhuma chamada de geração — guarda de estado do PREFL-01 confirmada pelo mutante M7.
- Minimização de dados em dois níveis: **estrutural** (`ContextoAgente` é `frozen`+`slots` com exatamente 5 campos) e **populacional** (só itens elegíveis recebem contexto — mutante M6).
- Credencial nunca aparece em resultado, causa, exceção, log ou corpo HTTP, sanitizada na origem.
- Navegação origem ↔ retentativa nos dois sentidos, sem mesclar marcos; a superfície explica o bloqueio com a causa real persistida e afirma explicitamente que nada foi substituído.

**Issues found**: nenhum bloqueador e nenhum maior. Restam 1 spec-precision gap conhecido (PREFL-05), 1 pendência menor pré-existente e já rastreada (`SuperficiePreparacaoIA` fora do `App.tsx`, comum às superfícies 2.3–2.6) e 3 observações de robustez sem violação de AC (ver *Observações*).

**Next steps**: história 3.1 pronta. Levar adiante, fora desta história: (a) o roteamento das 5 superfícies no `App.tsx`; (b) o mesmo escopo de idempotência nas 3 rotas de `adaptadores/http/meteorologia.py` (lição L-027); (c) 3.2 deve confirmar o consumo efetivo de `langchain`/`langchain-openai`/`langgraph`.
