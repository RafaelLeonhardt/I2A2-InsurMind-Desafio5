# História 3.1: Preparar a produção agêntica com dados mínimos — Validation

**Date**: 2026-09-03
**Spec**: `.specs/features/3-1-preparar-a-producao-agentica-com-dados-minimos/spec.md`
**Diff range**: `7666b0a..0f7890d` (9 commits, T1–T9)
**Verifier**: independent sub-agent (author ≠ verifier) — rodada 1

---

## Task Completion

| Task | Status | Notes |
| --- | --- | --- |
| T1: dependências `langchain`/`langchain-openai`/`langgraph` | ✅ Done | `39493d3`. Versões fixadas no `pyproject.toml`; `uv.lock` regenerado. Nenhum módulo de produção as importa ainda (só 3.2 vai) — declarado por antecipação, coerente com o próprio texto do T1. |
| T2: migração de schema | ✅ Done | `2e8a2c2`. Entrou como `0009_preflight_ia.sql` (não `0007`): `0007`/`0008` já pertencem a 2.5/2.6. Renumeração **verificada correta** — nenhuma colisão, `schema_migracoes` registra `1..9` (`testes/test_migracoes.py`, `testes/test_inicializador.py`). |
| T3: `RetryComBackoff[T]` | ✅ Done | `4187898`. `testes/test_coletor_com_retry.py` e `testes/test_coleta_meteorologica.py` (2.2) **não têm uma linha alterada no diff** — nenhuma regressão de comportamento observável em 2.2. |
| T4: `VerificadorDisponibilidadeOpenAI` | ✅ Done | `fd28924`. Também estendeu `Configuracao` (não reivindicado por nenhuma task, mas exigido por PREFL-05/06). |
| T5: `MontadorContextoAgente` | ✅ Done | `f78ffed`. Também acrescentou `OPERANDO_COBERTURA_EXIGIDA` ao avaliador de elegibilidade (mesmo padrão de `OPERANDO_AREA_AFETADA`, 2.5). |
| T6: `RepositorioContextosAgente` | ✅ Done | `d9f51c3`. |
| T7: `ServicoPreflightIA` | ⚠️ Partial | `4f29100`. Funcionalmente completo, mas a resolução de idempotência não é escopada por execução — ver Gap 1. |
| T8: roteador HTTP | ⚠️ Partial | `01b66b9`. Três rotas (uma a mais que o T8 pedia). Mesmo defeito de escopo de idempotência — ver Gap 1. |
| T9: superfície de bloqueio | ✅ Done | `0f7890d`. `npm run verificar-tipos-api` **executado por este Verifier contra o backend real em `127.0.0.1:8000`: verde** (o `tipos-gerados.ts` regenerado é fiel ao contrato, não um contorno). Componente ainda fora do `switch` de `App.tsx` (risco (9) pré-existente do Handoff). |

---

## Spec-Anchored Acceptance Criteria

### P1: Preflight de disponibilidade antes de qualquer geração

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| PREFL-01 — WHEN execução exclusivamente em `aguardando_geracao` tiver a etapa agêntica preparada THEN verificar configuração e disponibilidade antes de gerar qualquer mensagem | Nenhuma verificação nem geração fora de `aguardando_geracao`; verificação real antes de tudo | `src/backend/testes/test_preflight_ia.py:515` — `assert cenario.verificador.chamadas == 0` e `assert cenario.execucoes.transicoes == []` para `coletando`/`sem_risco`/`falhou_preparacao_ia`/`concluida`; `src/backend/testes/test_preflight_ia.py:432` — `assert cenario.verificador.chamadas == 3` | ✅ PASS |
| PREFL-02 — WHEN o preflight for bem-sucedido THEN transicionar automática e idempotentemente para `processando_mensagens` | Estado final exatamente `processando_mensagens`; repetir não reverifica nem retransiciona | `src/backend/testes/test_preflight_ia.py:353` — `assert resultado.estado == EstadoExecucao.PROCESSANDO_MENSAGENS` e `assert cenario.execucoes.transicoes == [(EXECUCAO_ID, 1, EstadoExecucao.PROCESSANDO_MENSAGENS)]`; `src/backend/testes/test_preflight_ia.py:493` — `assert cenario.verificador.chamadas == 0` / `transicoes == []`; `src/backend/testes/test_preflight_ia_api.py:177` — `assert corpo["estado"] == "processando_mensagens"` | ✅ PASS |
| PREFL-03 — IF chave ausente/inválida ou OpenAI indisponível THEN terminal `falhou_preparacao_ia` ao esgotarem as tentativas, sem nenhuma chamada de geração | Estado exatamente `falhou_preparacao_ia`, após 3 tentativas, zero contextos, zero geração | `src/backend/testes/test_preflight_ia.py:408` — `assert resultado.estado == EstadoExecucao.FALHOU_PREPARACAO_IA`, `assert cenario.verificador.chamadas == 3`, `assert cenario.espera.esperas == [1.0, 2.0]`, `assert cenario.contextos.salvos == []`; `src/backend/testes/test_verificador_disponibilidade_openai.py:70` — `assert espiao.requisicoes == []` (chave ausente, sem rede) | ✅ PASS |
| PREFL-04 — WHEN alcançar `falhou_preparacao_ia` THEN exceção sanitizada, resultados determinísticos preservados, sem valor/fragmento/cabeçalho/detalhe da credencial | `Exceção` própria com causa sanitizada; nenhuma ocorrência da chave em resultado, exceção ou resposta HTTP | `src/backend/testes/test_preflight_ia.py:408` — `assert cenario.excecoes.registradas == [(EXECUCAO_ID, INDISPONIVEL.causa, 3, IMPACTO_PREPARACAO_IA)]`; `src/backend/testes/test_verificador_disponibilidade_openai.py:149` — `assert CHAVE_SINTETICA not in repr(resultado)`, `assert "Bearer" not in resultado.causa`; `src/backend/testes/test_preflight_ia_api.py:199` — `assert CHAVE_SINTETICA not in resposta.text` | ✅ PASS (confirmado pelo mutante M2, morto) |
| PREFL-05 — SHALL manter modelo, temperatura, **demais parâmetros suportados**, versão de prompt e limites operacionais configuráveis e documentados; chave real só de `OPENAI_API_KEY` | Spec não enumera quais são os "demais parâmetros suportados" | `src/backend/testes/test_configuracao.py:197` — `assert configuracao.modelo_openai == "gpt-4o-mini"` … `timeout_openai_segundos == 15.0`; `:213` valores configurados; `:278` — `.env.example` documenta as 4 chaves + `OPENAI_API_KEY`; `src/backend/central_preventiva/composicao/configuracao.py:46` — `validation_alias="OPENAI_API_KEY"` sobre um `SecretStr` | ⚠️ Spec-precision gap (cláusula "demais parâmetros suportados" sem valor definido; modelo/temperatura/versão de prompt/limite estão cobertos) |

### P1: Inicialização segura e nova tentativa correlacionada

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| PREFL-06 — IF configuração estrutural ausente/malformada/incompatível THEN bloquear a própria inicialização com erro sanitizado, antes de qualquer execução | Falha de inicialização (não de execução), mensagem sem o valor recebido | `src/backend/testes/test_configuracao.py:246` — `with pytest.raises(ValidationError)` para modelo/temperatura/versão/timeout malformados; `:260` — `assert valor_sensivel not in str(captura.value)` | ✅ PASS |
| PREFL-07 — WHEN Marina solicitar nova tentativa a partir de `falhou_preparacao_ia` THEN validar que todas as referências versionadas dos snapshots existem, estão completas, íntegras e em versões suportadas **antes de criar qualquer registro** | Recusa antes de qualquer `INSERT` | `src/backend/testes/test_preflight_ia.py:669` — 5 classes de corrupção parametrizadas, `assert motivo_esperado in excecao.value.motivo` e `assert cenario.execucoes.criadas == []`; `:685` — regra versionada irresolvível | ✅ PASS |
| PREFL-08 — IF a validação falhar THEN comando rejeitado sem criar execução nova | Nenhuma execução criada | `src/backend/testes/test_preflight_ia.py:647` — `assert cenario.execucoes.criadas == []` e `elegibilidades.copias == []`; `src/backend/testes/test_preflight_ia_api.py:385` — `assert resposta.status_code == 422`, `codigo == "snapshot_invalido"`, `retentativas == []` | ✅ PASS |
| PREFL-09 — IF a validação passar THEN nova `ExecucaoPreventiva` em `aguardando_geracao`, novo `execucao_id`, `execucao_origem_id` e chave idempotente própria; origem permanece terminal; replay não duplica | Estado exatamente `aguardando_geracao`, origem intacta em `falhou_preparacao_ia`, replay devolve o mesmo id | `src/backend/testes/test_preflight_ia.py:563` — `assert nova.estado == EstadoExecucao.AGUARDANDO_GERACAO`, `assert nova.execucao_origem_id == EXECUCAO_ID`, `assert cenario.execucoes.snapshots[EXECUCAO_ID].estado == EstadoExecucao.FALHOU_PREPARACAO_IA`; `:599` — `assert segunda == primeira` e `assert len(cenario.execucoes.criadas) == 1`; `src/backend/testes/test_preflight_ia_api.py:305` | ✅ PASS (mas ver Gap 1: a mesma chave usada em **origens diferentes** vaza o registro de uma para a outra) |
| PREFL-10 — WHEN consultar origem ↔ retentativas THEN navegar nas duas direções, preservando IDs, estados e marcos sem mesclar históricos | Ambas as direções; marcos não mesclados | `src/backend/testes/test_preflight_ia_api.py:305` — `assert nova["execucao_origem_id"] == str(origem_id)`, `assert origem["retentativas"] == [nova_id]`, `assert [m["marco"] for m in origem["marcos"]] == ["falhou_preparacao_ia"]`, `assert nova["marcos"] == []`; `src/frontend/src/funcionalidades/preparacao-ia/SuperficiePreparacaoIA.test.tsx:186` e `:199` — `expect(aoNavegar).toHaveBeenCalledWith(NOVA_ID)` / `(ORIGEM_ID)` | ✅ PASS |

### P1: Contexto mínimo do agente redator

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| PREFL-11 — WHEN o contexto for montado THEN conter somente evento, localização aproximada, contexto/coberturas relevantes, canal e orientações de segurança | Exatamente 5 campos, nem um a mais | `src/backend/testes/test_montador_contexto_agente.py:88` — `assert {campo.name for campo in dataclasses.fields(ContextoAgente)} == {"evento", "localizacao_aproximada", "coberturas_relevantes", "canal", "orientacoes_seguranca"}`; `:115` — igualdade de valor com o `ContextoAgente` esperado | ✅ PASS (confirmado pelo mutante M3, morto) |
| PREFL-12 — SHALL excluir documentos, informações financeiras, dados de pagamento, credenciais e qualquer dado não necessário | Nenhum valor nem nome de campo sensível alcança o objeto produzido | `src/backend/testes/test_montador_contexto_agente.py:127` — `for sensivel in sensiveis: assert sensivel.valor_observado not in serializado; assert sensivel.operando not in serializado`; `:100` — `assert not hasattr(contexto, "__dict__")` + `pytest.raises(FrozenInstanceError)` | ✅ PASS (confirmado pelo mutante M3, morto) |
| PREFL-13 — WHEN a proveniência for registrada THEN armazenar categorias usadas e não usadas, sem copiar conteúdo sensível para logs | Duas listas de **nomes de categoria**; nada de conteúdo em log | `src/backend/testes/test_repositorio_contextos_agente.py:43` — persiste conteúdo + as duas listas; `:112` — `test_persistencia_nao_registra_o_conteudo_do_contexto_em_log`; `src/backend/testes/test_preflight_ia.py:375` — `assert usadas == CATEGORIAS_UTILIZADAS` e `assert nao_usadas == CATEGORIAS_NAO_UTILIZADAS` | ✅ PASS |
| PREFL-14 — WHEN Marina consultar a proveniência antes ou depois da geração THEN exibir essas categorias | As duas listas de categorias, sem conteúdo | `src/backend/testes/test_preflight_ia_api.py:283` — `GET /api/v1/execucoes/{id}/contextos`: `assert registros[0]["categorias_usadas"] == list(CATEGORIAS_UTILIZADAS)`, `assert "sms" not in resposta.text`, `assert AREA not in resposta.text`; `src/backend/testes/test_repositorio_contextos_agente.py:66` | ✅ PASS (⚠️ "exibir" satisfeito na camada de API; nenhuma superfície de UI consome a rota — coerente com o mapeamento T6/T8 da própria spec) |
| PREFL-15 — IF campo obrigatório ausente/inconsistente na montagem de um item THEN só esse item alcança terminal de exceção, sem enviar solicitação parcial à OpenAI | Um item em exceção, os demais montados, zero chamadas por item | `src/backend/testes/test_preflight_ia.py:447` — `assert resultado.contextos_montados == 2`, `assert resultado.itens_em_excecao == (invalido.id,)`, `assert cenario.verificador.chamadas == 1`, `assert cenario.excecoes.registradas == [(EXECUCAO_ID, f"contexto_invalido:{invalido.id}:coberturas_relevantes", 1, IMPACTO_ITEM_SEM_CONTEXTO)]`; `src/backend/testes/test_montador_contexto_agente.py:221` | ✅ PASS |

### P2: Explicação de indisponibilidade sem substituto artificial

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| PREFL-16 — IF a OpenAI não estiver disponível THEN não substituir a resposta por texto fixo, simulador de modelo ou outro provedor | Nenhum conteúdo de mensagem exibido; afirmação explícita de que nada foi gerado | `src/frontend/src/funcionalidades/preparacao-ia/SuperficiePreparacaoIA.test.tsx:112` — `expect(bloqueio).toHaveTextContent('Nenhuma mensagem foi gerada e nada foi escrito no lugar dela')`; `:126` — `expect(screen.queryByText(/Prezado\|Comunicado preventivo\|Olá,/)).not.toBeInTheDocument()`. Backend: nenhum caminho de geração existe nesta história (`verificador.chamadas` é a única saída externa) | ✅ PASS |
| PREFL-17 — WHEN o bloqueio ocorrer THEN a interface explica a causa e a próxima ação segura | Causa sanitizada real (não inventada) + ação de nova tentativa | `src/frontend/src/funcionalidades/preparacao-ia/SuperficiePreparacaoIA.test.tsx:96` — `expect(bloqueio).toHaveTextContent(CAUSA)`, `toHaveTextContent('Nenhuma mensagem preventiva é gerada nesta execução.')`, `toHaveTextContent('solicite uma nova tentativa')`; `:142` — causa vinda do preflight; causa persistida no marco `falhou_preparacao_ia` (`src/backend/testes/test_preflight_ia_api.py:305`, `assert origem["marcos"][0]["causa"] == "A credencial da OpenAI foi recusada."`) | ✅ PASS (⚠️ componente ainda não roteado em `App.tsx` — risco (9) pré-existente, comum às superfícies 2.3–2.6) |

**Status**: ⚠️ 16/17 ACs com o desfecho da spec asserido; 1 ⚠️ Spec-precision gap (PREFL-05). Nenhum AC sem evidência. **Mas** o Edge Case 1 falha (abaixo), e o defeito que ele expõe atravessa PREFL-03/04/09.

---

## Edge Cases

- [ ] **EC1 — IF o preflight for repetido com a mesma condição de indisponibilidade em execuções diferentes THEN cada execução SHALL registrar sua própria exceção, sem compartilhar ou reutilizar o registro de outra** — ❌ **NÃO tratado, e sem nenhum teste**. Reproduzido por este Verifier em worktree isolado (ver Fix 1).
- [x] EC2 — chave válida mas modelo configurado fora do catálogo → falha de preparação com causa sanitizada: `src/backend/testes/test_verificador_disponibilidade_openai.py:111` — `assert resultado.disponivel is False` e `assert resultado.causa == f"O modelo configurado ('{MODELO}') não está no catálogo da OpenAI."`
- [x] EC3 — segurado sem coberturas relevantes ao evento → tratado como campo obrigatório ausente para esse item: `src/backend/testes/test_montador_contexto_agente.py:170` — `assert erro.campo == CATEGORIA_COBERTURAS` e `assert erro.elegibilidade_id == ELEGIBILIDADE_ID`

---

## Discrimination Sensor

**Isolamento**: `git worktree add <scratch> HEAD` (nunca `git stash`). `git status --porcelain` do worktree real: **vazio antes e depois** dos 5 mutantes e das 2 sondas; `git worktree list` volta a listar apenas o repositório principal.

| Mutation | File:line | Description | Killed? |
| --- | --- | --- | --- |
| M1 | `src/backend/central_preventiva/adaptadores/ia/verificador_disponibilidade_openai.py:130` | Inverteu a classificação de catálogo: `if self._modelo not in catalogo` → `if self._modelo in catalogo` | ✅ Killed (6 falhas, incl. `test_modelo_ausente_do_catalogo_resulta_em_falha_de_preparacao_nao_em_sucesso`) |
| M2 | `src/backend/central_preventiva/adaptadores/ia/verificador_disponibilidade_openai.py:121` | Vazou a credencial na causa: `causa=f"{CAUSA_CREDENCIAL_INVALIDA} (chave: {self._chave})"` | ✅ Killed (4 falhas, incl. `test_preflight_ia_api.py::test_preflight_com_openai_indisponivel_falha_a_preparacao_sem_expor_a_credencial` — o vazamento é pego ponta a ponta, não só na unidade) |
| M3 | `src/backend/central_preventiva/dominio/montador_contexto_agente.py:95` e `:193` | Deixou passar um 6º campo: acrescentou `documento_do_segurado` a `ContextoAgente` e o preencheu a partir de um critério sensível do snapshot | ✅ Killed (4 falhas, incl. o teste de vazamento `test_nenhum_dado_fora_da_lista_permitida_atravessa_a_montagem`) |
| M4 | `src/backend/central_preventiva/aplicacao/preflight_ia.py:398` | Rompeu a ligação da cópia AD-012: `criar_correlacionada(..., copiar_elegibilidades)` → `criar_correlacionada(..., None)` | ✅ Killed (4 falhas, incl. o cenário integrado contra DuckDB real) |
| M5 | `src/backend/central_preventiva/adaptadores/persistencia/repositorio_elegibilidade.py:189` | Quebrou a fidelidade do snapshot copiado: `SELECT ... nome_segurado, justificativa` → `SELECT ... 'ANONIMO', ''` | ❌ **Survived** — **524/524 testes de backend continuam verdes** com a cópia adulterada |

**Sensor depth**: lightweight (5 mutações, enviesadas para minimização de dados, credencial e AD-012, conforme a orientação de risco proporcional)
**Result**: 4/5 killed — ❌ FAIL (1 mutante sobrevivente → fix task)

### Sondas adicionais (não-mutação, worktree isolado)

Duas sondas confirmaram o defeito do EC1 sem tocar o worktree real (ver Fix 1). Ambas as sondas foram descartadas com o worktree.

---

## Code Quality

| Principle | Status |
| --- | --- |
| Minimum code | ⚠️ `langchain`/`langchain-openai`/`langgraph` entram como dependências de runtime sem nenhum import de produção nesta história (T1 pediu explicitamente; cash-in só em 3.2) |
| Surgical changes | ✅ Extensões aditivas; nenhum teste pré-existente reescrito |
| No scope creep | ⚠️ 3 adições fora do texto das tasks (`GET /execucoes/{id}/contextos`, marcos de preflight, extensão de `Configuracao`) — **todas ancoradas em ACs que nenhuma task cobria** (PREFL-14, PREFL-16/17, PREFL-05/06); julgadas legítimas |
| Matches patterns | ✅ Idempotência AD-002, `problem+json` AD-011, concorrência otimista AD-008, execução correlacionada AD-009, cópia de snapshot AD-012, migração numerada AD-001/AD-015 |
| Spec-anchored outcome check | ⚠️ 16/17 asseridos contra o valor da spec; PREFL-05 tem cláusula sem valor definido |
| Per-layer Coverage Expectation met | ⚠️ Domínio 1:1 com PREFL-11..15 ✅; rotas cobrem feliz+borda+erro ✅; **falta o caminho de erro "mesma chave, execução diferente"** (Gap 1) e a asserção de fidelidade da cópia (Gap 2) |
| Every test maps to a spec requirement | ✅ Nenhum teste órfão encontrado nos 6 arquivos novos |
| Documented guidelines followed | ✅ `AGENTS.md`, `README.md`, `adaptadores/persistencia/README.md` (atualizado com a coluna e a tabela novas) |
| No abstractions for single-use code | ✅ `RetryComBackoff[T]` tem 2 consumidores reais (2.2 e 3.1) |
| Didn't "improve" unrelated code | ✅ `coleta_meteorologica.py` mudou só para delegar ao wrapper; suíte de 2.2 intacta (0 linhas de diff em `test_coletor_com_retry.py` / `test_coleta_meteorologica.py`) |
| Would senior engineer approve? | ⚠️ Sim, condicionado aos 2 fixes abaixo |

---

## Gate Check

- **Gate command (Build, fim de fase)**: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright` + `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`
- **Result**:
  - Backend: **524 passed**, 0 failed, 0 skipped
  - `ruff check .`: All checks passed!
  - `pyright`: 0 errors, 0 warnings, 0 informations
  - Frontend: **229 passed** (26 arquivos), 0 failed, 0 skipped
  - `oxlint`: exit 0 (só warnings pré-existentes de `set-state-in-effect`/`only-export-components`, o mesmo padrão já presente em 4 superfícies anteriores)
  - `vite build`: ✓ built
- **Extra (verificado por este Verifier, não pelo autor)**: `npm run verificar-tipos-api` contra o backend real em `127.0.0.1:8000` (banco temporário migrado à versão 9) → *"src/api/tipos-gerados.ts está sincronizado com o contrato OpenAPI do backend em execução."* A regeneração de 990+/664- linhas **não** encobre contrato divergente.
- **Test count before feature**: 414 backend / 219 frontend
- **Test count after feature**: 524 backend / 229 frontend
- **Delta**: +110 backend, +10 frontend
- **Skipped tests**: nenhum
- **Failures**: nenhuma
- **Test integrity**: nenhum teste removido; nenhuma asserção pré-existente enfraquecida (os 2 arquivos de teste de 2.2 tocados pelo refactor do T3 têm **zero** linhas de diff).

---

## Fix Plans

### Fix 1 (Blocker) — a mesma `Idempotency-Key` em execuções diferentes devolve o registro de outra execução

- **Root cause**: `ServicoPreflightIA.preparar` e `.solicitar_nova_tentativa` resolvem a idempotência por `(chave, operacao)` apenas (`src/backend/central_preventiva/aplicacao/preflight_ia.py:345` e `:374`), e o roteador calcula `hash_requisicao = sha256(await requisicao.body()).hexdigest()` (`src/backend/central_preventiva/adaptadores/http/preflight_ia.py:242` e `:317`). Como **as duas rotas têm corpo vazio** e o `execucao_id` viaja só no path, duas execuções distintas produzem chave e hash idênticos: a segunda não dispara `ConflitoIdempotencia` — ela recebe a resposta gravada pela primeira.
- **Evidência reproduzida** (worktree isolado, descartado):
  - `POST /execucoes/A/preflight` e `POST /execucoes/B/preflight` com `Idempotency-Key: mesma-chave` e a OpenAI indisponível → **B responde `202` com o `execucao_id` de A, o estado de A e a causa de A**; a execução B permanece em `aguardando_geracao`, com `marcos: []` e **nenhuma `Exceção` própria**.
  - `POST /execucoes/A/nova-tentativa-ia` e `POST /execucoes/B/nova-tentativa-ia` com a mesma chave → **B responde `202` com o `execucao_id` da retentativa de A e `execucao_origem_id` de B** (uma correlação que não existe); `GET /execucoes/B` devolve `retentativas: []`.
- **AC violado**: Edge Case 1 da spec ("cada execução SHALL registrar sua própria exceção, sem compartilhar ou reutilizar o registro de outra"), com efeito colateral sobre PREFL-03/PREFL-04 (a execução B nunca alcança o terminal nem registra exceção) e sobre PREFL-09 (resposta descreve uma correlação inexistente).
- **Fix task**:
  - **What**: escopar a idempotência das duas operações pela execução alvo — incluir o `execucao_id`/`execucao_origem_id` do path no `hash_requisicao` (ex.: `sha256(str(uuid).encode() + await requisicao.body())`) ou no nome da operação, de modo que a mesma chave em execuções diferentes produza `409 conflito_idempotencia` em vez de devolver o registro alheio.
  - **Where**: `src/backend/central_preventiva/adaptadores/http/preflight_ia.py:242`, `:317` (e/ou `aplicacao/preflight_ia.py:345`, `:374`).
  - **Verify**: teste novo em `testes/test_preflight_ia_api.py` — duas execuções, mesma `Idempotency-Key`, OpenAI indisponível: a segunda **não** devolve o `execucao_id` da primeira; ambas terminam em `falhou_preparacao_ia` com `Exceção` e marco próprios. Idem para `nova-tentativa-ia`.
  - **Done when**: o Edge Case 1 tem citação `file:line`; o replay legítimo (mesma chave, **mesma** execução) continua devolvendo a resposta registrada sem novo preflight.
- **Priority**: **Blocker**
- **Nota de escopo**: a mesma construção aparece em `adaptadores/http/meteorologia.py:395` (2.2, `sincronizacao_id` no path com corpo vazio). Fora do escopo desta história — registrar como risco a revisitar, não corrigir aqui.

### Fix 2 (Major) — a fidelidade do snapshot copiado (AD-012) não é asserida por nenhum teste

- **Root cause**: `RepositorioElegibilidades.copiar_para_execucao` não tem teste dedicado (`grep copiar_para_execucao testes/` só encontra o dublê em `test_preflight_ia.py:222`). O único exercício da implementação real é `test_preflight_ia.py:737`, que assere quantidade (`len(copiadas) == 2`), o conjunto `{True, False}` de `elegivel` e ids novos — **nunca a igualdade de conteúdo**. O mutante M5 troca `nome_segurado` por `'ANONIMO'` e `justificativa` por `''` e os 524 testes continuam verdes.
- **AC/decisão violada**: AD-012 ("conteúdo de snapshot idêntico"), que sustenta PREFL-09 e a auditabilidade autocontida de cada execução.
- **Fix task**:
  - **What**: asserir a identidade linha a linha entre origem e cópia — todas as colunas de snapshot (`evento_id`, `regra_id`, `regra_versao`, `segurado_id`, `apolice_id`, `elegivel`, `criterios`, `canal`, `nome_segurado`, `justificativa`), com apenas `id` e `execucao_id` diferentes.
  - **Where**: `src/backend/testes/test_repositorio_elegibilidade.py` (teste de integração dedicado ao novo método) ou reforço de `test_preflight_ia.py:737`.
  - **Verify**: reinjetar M5 (`'ANONIMO'`/`''` no `SELECT` de `_copiar`) e confirmar que o teste falha.
  - **Done when**: M5 morre.
- **Priority**: **Major**

### Fix 3 (Minor, opcional) — `SuperficiePreparacaoIA` não é alcançável pelo `App.tsx`

- **Root cause**: mesma pendência já registrada como risco (9) do Handoff para `SuperficieEventoDecisao`, `SuperficieExecucao`, `SuperficieRegras` e `SuperficieFonteMeteorologica`.
- **Impacto**: PREFL-17 é verificável no componente, não na navegação real.
- **Fix task**: pertence à história/tarefa de integração de UI ainda não agendada; **não** deve ser corrigido dentro da 3.1.
- **Priority**: Minor (não bloqueia esta história — consistente com o tratamento dado às quatro superfícies anteriores)

---

## Julgamento independente sobre as 4 `SPEC_DEVIATION` e as adições não declaradas

| Item | Veredito | Razão |
| --- | --- | --- |
| `GET /v1/models` em vez de `ChatOpenAI` (`verificador_disponibilidade_openai.py:7`) | ✅ Aceitável — na verdade **mais** conforme à spec que o design | O design admite "ou chamada HTTP equivalente de baixo custo" no mesmo item, e a tabela *Assumptions* da própria `spec.md` já escolhe `GET /v1/models` (padrão da `SondaOpenAI`). Uma invocação de `ChatOpenAI` seria uma chamada de geração antes do terminal — o que PREFL-03 proíbe — e só o catálogo permite implementar o Edge Case 2. Verificado: nenhuma chamada de geração existe no código desta história. |
| `montar(elegibilidade_id, ...)` (`montador_contexto_agente.py:11`) | ✅ Aceitável, sem vazamento | O AC real é a fronteira de 5 campos de `ContextoAgente`, não a assinatura. Inspecionado diretamente: `ContextoAgente` declara exatamente os 5 campos (`:91–95`), é `frozen`+`slots`, e o `elegibilidade_id` só aparece em `ErroContexto`. Confirmado pelo mutante M3. |
| `obter_por_elegibilidade -> RegistroContextoAgente` (`repositorio_contextos_agente.py:7`) | ✅ Aceitável e necessário | O tipo do design (`ContextoAgente \| None`) não expõe proveniência, e PREFL-14 exige exatamente isso. A rota `GET /execucoes/{id}/contextos` devolve **só nomes de categoria** (`RespostaProvenienciaContexto` carrega `elegibilidade_id` + as 2 listas, nada mais) — verificado no código e por `test_preflight_ia_api.py:283` (`"sms" not in resposta.text`, `AREA not in resposta.text`). |
| `preparar(..., chave_idempotencia, hash_requisicao)` (`preflight_ia.py:8`) | ⚠️ Aceitável na forma, **incompleta na execução** | O AD-002 realmente exige decidir a idempotência onde o efeito acontece. Mas o escopo escolhido — `(chave, operacao)` sem o alvo — é o que produz o Gap 1. A decisão está certa; a chave de escopo está errada. |
| Migração `0009` em vez de `0007` | ✅ Aceitável e correta | `0007_elegibilidade_correcoes.sql` (2.5) e `0008_marcos_execucao.sql` (2.6) já ocupavam os números. Verificado: nenhuma colisão de arquivo, `schema_migracoes` registra `1..9`, `test_migracoes.py` e `test_inicializador.py` asseriram a sequência, e a coluna nula sem backfill dispensa corretamente o recreate-and-copy do AD-015 (justificado no cabeçalho do `.sql`). |
| Rota `GET /execucoes/{id}/contextos` a mais | ✅ Aceitável | PREFL-14 é um AC voltado a Marina que nenhuma task expunha fora do repositório. Um método de repositório não é algo que Marina consulta. Não vaza canal nem área. |
| Marcos `falhou_preparacao_ia` / `preparacao_ia_concluida` | ✅ Aceitável, sem conflito com 2.6 | Reusa `RepositorioExecucaoPreventiva.registrar_marco`/`listar_marcos` (2.6) sem alterá-los. Nomes verificados contra os 4 marcos de `GerenciadorExecucoes` (`coleta_concluida`, `avaliacao_risco_concluida`, `avaliacao_elegibilidade_concluida`, `publico_elegivel_formado`): **nenhuma colisão**. A causa gravada é a `causa` já sanitizada pelo `VerificadorDisponibilidadeOpenAI` — sanitizada **na origem**, não só no ponto de exibição; o mutante M2 provou que um vazamento aí é pego até na resposta HTTP. |
| Extensão de `Configuracao` dentro do T4 | ✅ Aceitável | PREFL-05/PREFL-06 não tinham task própria e T4 é o primeiro consumidor de `modelo_openai`. `chave_openai` continua `SecretStr` e `obter_configuracao` sanitiza. |
| Refactor `RetryComBackoff[T]` (T3) | ✅ Aceitável, **sem regressão em 2.2** | Exigido pela Tech Decision do design. `testes/test_coletor_com_retry.py` e `testes/test_coleta_meteorologica.py` têm **zero** linhas no diff `7666b0a..0f7890d`, e a suíte completa passa. |
| `tipos-gerados.ts` regenerado (990+/664-) | ✅ Aceitável, verificado empiricamente | `npm run verificar-tipos-api` executado por este Verifier contra o backend real: verde. A reordenação é de ordem de registro de rotas, não drift de contrato (`test_openapi_sincronizado.py` compara dicionários, portanto é insensível à ordem). |
| `langchain`/`langchain-openai`/`langgraph` declarados sem uso | ⚠️ Observação, não gap | Nenhum módulo de produção os importa nesta história. T1 pediu explicitamente e 3.2 cobra a dívida; anotado apenas para que 3.2 confirme o consumo. |

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
| --- | --- | --- |
| PREFL-01 | Implementing | ✅ Verified |
| PREFL-02 | Implementing | ✅ Verified |
| PREFL-03 | Implementing | ⚠️ Verified with gap (Fix 1) |
| PREFL-04 | Implementing | ⚠️ Verified with gap (Fix 1) |
| PREFL-05 | Implementing | ⚠️ Spec-precision gap |
| PREFL-06 | Implementing | ✅ Verified |
| PREFL-07 | Implementing | ✅ Verified |
| PREFL-08 | Implementing | ✅ Verified |
| PREFL-09 | Implementing | ❌ Needs Fix (Fix 1, Fix 2) |
| PREFL-10 | Implementing | ✅ Verified |
| PREFL-11 | Implementing | ✅ Verified |
| PREFL-12 | Implementing | ✅ Verified |
| PREFL-13 | Implementing | ✅ Verified |
| PREFL-14 | Implementing | ✅ Verified |
| PREFL-15 | Implementing | ✅ Verified |
| PREFL-16 | Implementing | ✅ Verified |
| PREFL-17 | Implementing | ✅ Verified |

---

## Summary

**Overall**: ❌ Not Ready

**Verdict**: **FAIL**

**Spec-anchored check**: 16/17 ACs asseridos contra o desfecho definido pela spec; 1 ⚠️ spec-precision gap (PREFL-05, cláusula "demais parâmetros suportados"); **1 de 3 Edge Cases não tratado** (EC1).
**Sensor**: 5 mutações injetadas, 4 mortas, **1 sobrevivente** (M5).
**Gate**: 524 backend + 229 frontend passed, 0 failed, 0 skipped; ruff/pyright/oxlint/vite build limpos; `verificar-tipos-api` verde contra o backend real.

**What works**:

- Preflight real (`GET /v1/models`) com política única de 3 tentativas e backoff 1s/2s, transicionando corretamente para `processando_mensagens` ou `falhou_preparacao_ia`, sem nenhuma chamada de geração.
- Minimização de dados **estrutural**: `ContextoAgente` é `frozen`+`slots` com exatamente 5 campos; o teste de vazamento discrimina de verdade (M3 morto).
- Credencial nunca aparece em resultado, causa, exceção, log ou corpo HTTP — inclusive ponta a ponta (M2 morto). Nenhum `logging`/`print` no código novo.
- AD-012 atômico: a cópia das elegibilidades roda na transação de `criar_correlacionada`, e a falha da cópia não deixa execução órfã (teste dedicado + M4 morto).
- Navegação origem↔retentativa nos dois sentidos, sem mesclar marcos; superfície explica bloqueio com causa real persistida, impacto, próxima ação e afirmação explícita de que nada foi substituído.
- Migração `0009` correta, sem colisão; refactor do retry sem regressão em 2.2.

**Issues found**:

1. **Blocker** — Idempotência não escopada por execução: a mesma `Idempotency-Key` em execuções diferentes devolve o registro da primeira, deixando a segunda sem preflight, sem exceção e sem marco (Edge Case 1 violado, PREFL-03/04/09 afetados). Fix 1.
2. **Major** — Fidelidade do snapshot copiado (AD-012) sem nenhuma asserção: o mutante M5 (`nome_segurado`→`'ANONIMO'`, `justificativa`→`''`) sobrevive aos 524 testes. Fix 2.
3. **Minor** — `SuperficiePreparacaoIA` fora do `switch` de `App.tsx` (risco (9) pré-existente); não bloqueia esta história.

**Next steps**: rotear Fix 1 e Fix 2 a um implementador e re-despachar o Verifier (iteração 2 de no máximo 3). Fix 3 permanece na pendência de integração de UI já registrada no Handoff.
