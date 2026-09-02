# História 2.3: Identificar eventos meteorológicos relevantes — Validation

**Date**: 2026-09-02
**Rodada**: **ROUND 2** (re-verificação após correções)
**Spec**: `.specs/features/2-3-identificar-eventos-meteorologicos-relevantes/spec.md`
**Diff range**: `6b2108c..1122288` (7 commits — T1–T6 + o commit de correção `1122288`)
**Diff das correções em isolado**: `22b2906..1122288`
**Verifier**: sub-agente independente (author ≠ verifier), distinto do verificador da Round 1 — read-only sobre a árvore real; mutações apenas em worktrees descartáveis

**Verdict**: ✅ **PASS**

**Histórico**: Round 1 (`6b2108c..22b2906`) → ❌ FAIL (1 lacuna de AC fundamentada em RISCO-09 + mutante M2 sobrevivente + 3 lacunas menores) → Fix 1–5 implementados pelo orquestrador e commitados em `1122288` → Round 2 (este relatório) → ✅ PASS.

Todas as cinco correções foram **verificadas de forma independente na árvore real** (não aceitas do sumário): a lacuna de RISCO-09 está fechada em todas as camadas, o mutante M2 está morto, a distinção por ícone está asserida, os exemplos limítrofes chegaram à documentação e a constante morta foi removida. Uma **regressão menor e não bloqueante de documentação** foi encontrada e está registrada em Fix Plans (Fix 6).

---

## Task Completion

| Task | Status | Notes |
| --- | --- | --- |
| T1 — Migração `0004_avaliacao_risco` | ✅ Done | — |
| T2 — `AvaliadorRisco` (motor determinístico) | ✅ Done | Constante morta `LIMIAR_CHUVA_INTENSA_MM` removida (Fix 5, confirmado: zero ocorrências no repositório) |
| T3 — `RepositorioRegras` / `RepositorioAvaliacoesRisco` | ✅ Done | `regra_id`/`regra_versao` agora `UUID \| None` / `int \| None` na dataclass, no `salvar` e na desserialização (`repositorio_avaliacoes_risco.py:34-35,75-76,119-120`) |
| T4 — `ServicoAvaliacaoRisco` | ✅ Done | Era ⚠️ Partial na Round 1; o caminho `sem_regra_ativa` agora persiste snapshot (`aplicacao/avaliacao_risco.py:90`). Continua não alcançável por caminho de produção (lacuna declarada pelo autor, fora de escopo desta história) |
| T5 — Endpoint HTTP de detalhe | ✅ Done | Modelo relaxado (`adaptadores/http/avaliacao_risco.py:37-42`); `openapi.json` re-sincronizado e **guardado por teste** (ver Payload/Contrato) |
| T6 — Superfície "Evento e decisão" | ✅ Done | Ícones distintos por categoria; tipos do frontend nulos. Componente segue não montado em rota (lacuna declarada pelo autor em `tasks.md` T6 / `STATE.md`) |
| Fix 1–5 (Verifier Round 1) | ✅ Done | Verificados um a um abaixo |

---

## Verificação das correções da Round 1

| Fix | O que Round 1 pediu | Verificação independente (Round 2) | Resultado |
| --- | --- | --- | --- |
| **Fix 1** — RISCO-09 persistir código/motivo | Terminal `sem_risco` sem regra ativa deve gravar código e motivo | Migração `0005_avaliacao_risco_sem_regra.sql:10-29` recria a tabela (recreate-and-copy, precedente AD-015/migração 0003) com `regra_id UUID` e `regra_versao INTEGER` **sem** `NOT NULL`, copiando todas as linhas antes do `DROP`. Serviço: `aplicacao/avaliacao_risco.py:90` — `self._portas.avaliacoes.salvar(execucao_id, evento.id, None, None, resultado)` **antes** da transição (`:91-93`). Rota: devolve `200` porque o snapshot passa a existir — nenhuma lógica de rota precisou mudar, só o modelo (`http/avaliacao_risco.py:37-42`). Frontend: `api/avaliacaoRisco.ts:20-21` `regraId: string \| null` | ✅ **Fechado** |
| **Fix 2** — mutante M2 | Fixture de versão não trivial | `testes/test_avaliacao_risco.py:30` — `versao=7` (com comentário explicando o porquê); `testes/test_repositorio_avaliacoes_risco.py:49,58` — `regra_versao=7`. **Mutante M2 re-injetado e agora morto** (ver Sensor) | ✅ **Fechado** |
| **Fix 3** — RISCO-12 distinção por ícone | Asserir que os três ícones diferem | `SuperficieEventoDecisao.tsx:41,46,50` — `data-icone-nome` `warning` / `x-circle` / `check-circle`; `SuperficieEventoDecisao.test.tsx:153` — `expect(new Set(nomes).size).toBe(3)`, mais três asserções por categoria em `:89,:114,:127`. **Colisão de ícone re-injetada e morta** (ver Sensor) | ✅ **Fechado** |
| **Fix 4** — RISCO-02 exemplos limítrofes na documentação | Tabela de fronteira + exemplos + declaração de ausência de fronteira exclusiva | `adaptadores/persistencia/README.md:104-122` — seção "Limiares de relevância", tabela por `evento_tipo` com fronteira **Inclusiva** (`:113`), declaração "nenhuma fronteira exclusiva está configurada nesta demonstração" (`:114`) e os três exemplos `49.9`/`50.0`/`50.1` (`:120-122`). Guardado por `testes/test_migracoes.py:294-305` | ✅ **Fechado** |
| **Fix 5** — constante morta | Remover `LIMIAR_CHUVA_INTENSA_MM` | `grep -rn LIMIAR_CHUVA_INTENSA_MM src/` → zero ocorrências. A justificativa migrou para o README (`:113`, coluna "Justificativa"), como Fix 4 previu | ✅ **Fechado** |

---

## Spec-Anchored Acceptance Criteria

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + asserção | Result |
| --- | --- | --- | --- |
| **RISCO-01** — centralizar limiares em configuração versionada e legível, com valores padrão e justificativa | Limiar de chuva = `50.0` mm, versionado, com justificativa documentada | Config: tabela `regras` (`versao`/`estado`); default semeado em `adaptadores/persistencia/semeador.py:189-190` (`"chuva_intensa", 50.0`); leitura versionada em `repositorio_regras.py:27-29` (`WHERE estado='ativa' ORDER BY versao DESC`); justificativa agora em `adaptadores/persistencia/README.md:113`. Teste: `testes/test_repositorio_regras.py:50` — `assert regra.limiar_meteorologico == 50.0`; `:77-78` — `assert regra.versao == 2` (regra `substituida` ignorada). **Melhorado na Round 2**: a duplicata morta do default no domínio foi removida, então a tabela `regras` é agora literalmente a única fonte de verdade | ✅ PASS |
| **RISCO-02** — documentação SHALL explicitar fronteiras inclusivas/exclusivas, **com exemplos limítrofes** | Por limiar: qual lado da fronteira é relevante + exemplos no valor-limite | `adaptadores/persistencia/README.md:104-122`: tabela de limiares com fronteira `Inclusiva (intensidade >= limiar)` (`:113`), "nenhuma fronteira exclusiva está configurada nesta demonstração" (`:114`), tabela de exemplos `49.9` → Não relevante / `50.0` → **Relevante** / `50.1` → Relevante (`:120-122`). Guarda automatizada: `testes/test_migracoes.py:302` — `assert "nenhuma fronteira exclusiva está configurada" in documento` e `:303-304` — `for exemplo in ("49.9","50.0","50.1"): assert exemplo in documento`. Comportamento correspondente asserido em `testes/test_avaliador_risco.py:69,79,86` | ✅ **PASS** (era ⚠️ na Round 1) |
| **RISCO-03** — reconhecer chuva intensa e granizo como suportados | Ambos avaliados, não rejeitados | `dominio/avaliador_risco.py:92` (guarda de tipo); `testes/test_avaliador_risco.py:81-82` — `resultado.relevante is True` / `motivo == MOTIVO_RELEVANTE` (chuva); `:105-108` — idem + `criterio_ocorrencia.atende is True` (granizo) | ✅ PASS |
| **RISCO-04** — tipo diferente → registrado como não suportado **sem avançar** | Resultado "não suportado", limiar não avaliado | `dominio/avaliador_risco.py:92-93` → `_rejeitar_tipo_nao_suportado`; `testes/test_avaliador_risco.py:133` — `motivo == MOTIVO_TIPO_NAO_SUPORTADO`; `:134` — `len(resultado.criterios) == 1` (prova que o ramo de limiar nunca rodou, apesar de `intensidade=999.0` em `:126`) | ✅ PASS |
| **RISCO-05** — chuva: comparar medidas, área, severidade e período com a regra do **residencial**, resultado determinístico com valores e critérios | Resultado com valores observados + critérios aplicados | `dominio/avaliador_risco.py:95-119`; `testes/test_avaliador_risco.py:72-75` — `motivo == MOTIVO_ABAIXO_DO_LIMIAR`, `criterio_intensidade.atende is False`, `valor_observado == "49.9 mm"`; `:96-99` — `motivo == MOTIVO_AREA_NAO_APLICAVEL` | ⚠️ **Spec-precision gap** (nota A — inalterado desde a Round 1; fora do escopo das correções desta rodada) |
| **RISCO-06** — granizo: idem contra a regra do **automóvel** | Resultado determinístico com valores e critérios | `dominio/avaliador_risco.py:121-130`; `testes/test_avaliador_risco.py:105-108` e `:114-115` — `motivo == MOTIVO_AREA_NAO_APLICAVEL` | ⚠️ **Spec-precision gap** (notas A e B — inalterado, fora do escopo desta rodada) |
| **RISCO-07** — mesma entrada + mesma versão de regra → resultado e justificativa idênticos | Igualdade byte-a-byte | `dominio/avaliador_risco.py:85-130` (função pura, sem I/O nem estado); `testes/test_avaliador_risco.py:143` — `assert primeira == segunda` (dataclass `frozen`: compara `relevante`, toda a tupla de `Criterio` com as strings de justificativa, e `motivo`) | ✅ PASS |
| **RISCO-08** — nenhum LLM, prompt ou heurística probabilística participa da decisão | Zero envolvimento de IA em qualquer caminho | Estrutural: `dominio/avaliador_risco.py:1-9` importa só stdlib + domínio; `testes/test_camadas.py:7-36` proíbe, por varredura AST de todo `dominio/*.py`, importar `central_preventiva.adaptadores`; `aplicacao/avaliacao_risco.py:54-63` declara exatamente 3 portas + a função pura — nenhuma porta de IA existe para ser chamada. O novo caminho `sem_regra_ativa` (`:87-94`) também não introduz nenhuma chamada | ✅ PASS (evidência estrutural, nota C) |
| **RISCO-09** — evento sem critérios → terminal `sem_risco` **com código e motivo persistidos**, sem elegibilidade/mensagem/OpenAI | Estado `sem_risco` + código e motivo gravados, para **todo** caminho terminal | Caminho normal: `aplicacao/avaliacao_risco.py:96-104`; `testes/test_avaliacao_risco.py:103` — `execucoes.transicoes == [(execucao_id, 1, EstadoExecucao.SEM_RISCO)]`. **Sub-caso `sem_regra_ativa` (a lacuna da Round 1)**: `aplicacao/avaliacao_risco.py:90` grava o snapshot; `testes/test_avaliacao_risco.py:133` — `assert len(avaliacoes.salvas) == 1`, `:137-139` — `regra_salva is None`, `versao_salva is None`, `resultado_salvo.motivo == MOTIVO_SEM_REGRA_ATIVA`, `:140` — transição exata para `SEM_RISCO`. Repositório real: `testes/test_repositorio_avaliacoes_risco.py:87-92` — round-trip DuckDB com `regra_id is None`/`regra_versao is None`/`motivo == "sem_regra_ativa"`/`criterios == ()`. Rota: `testes/test_avaliacao_risco_api.py:103-109` — `status_code == 200` (**não 404**), `motivo == "sem_regra_ativa"`, `regra_id is None`, `criterios == []`. Migração: `testes/test_migracoes.py:166-208` — preserva linhas existentes **e** aceita `NULL`. Nenhuma elegibilidade/mensagem/IA: as 3 portas do serviço não incluem nenhuma delas (`aplicacao/avaliacao_risco.py:54-63`) | ✅ **PASS** (era ❌ GAP na Round 1) |
| **RISCO-10** — evento relevante → `avaliando_elegibilidade` preservando snapshot imutável do evento e da versão da regra | Transição + snapshot de `evento_id`, `regra_id`, `regra_versao` | `aplicacao/avaliacao_risco.py:96-104`; `testes/test_avaliacao_risco.py:116` — `execucoes.transicoes == [(execucao_id, 1, EstadoExecucao.AVALIANDO_ELEGIBILIDADE)]`; `:150-154` — `execucao_salva == execucao_id`, `evento_salvo == evento.id`, `regra_salva == REGRA_CHUVA.id`, `versao_salva == REGRA_CHUVA.versao` **com `versao=7`** (`:30`), agora discriminante. Imutabilidade: `repositorio_avaliacoes_risco.py:88` só `INSERT`, `:110` só `SELECT` (nenhum `UPDATE`/`DELETE` em nenhuma das duas migrações); `regra_versao` gravada como valor, não referência | ✅ **PASS** (mutante M2 agora morto — era ⚠️ enfraquecido na Round 1) |
| **RISCO-11** — detalhe exibe operando, valor observado, resultado e justificativa de cada critério | As 4 colunas por critério | Backend: `testes/test_avaliacao_risco_api.py:75-78` — `len(corpo["criterios"]) == 2`, `criterios[0]["operando"] == "área aplicável"`, `criterios[0]["atende"] is True`, `criterios[1]["valor_observado"] == "72.5 mm"` (round-trip real do `INSERT` DuckDB ao corpo HTTP). Repositório: `testes/test_repositorio_avaliacoes_risco.py:61` — `criterios == RESULTADO_RELEVANTE.criterios` (tupla completa com justificativas). Frontend: `SuperficieEventoDecisao.test.tsx:72-77` + tabela de 4 colunas em `SuperficieEventoDecisao.tsx:149-169` | ✅ PASS (não alcançável na app, nota E) |
| **RISCO-12** — distinguir relevância / ausência de risco / dado inválido por **texto, ícone e cor** | Tríade texto+ícone+cor por categoria | **Texto**: `SuperficieEventoDecisao.test.tsx:85` `findByText('Relevante')`, `:110` `'Sem risco'`, `:123` `'Dado inválido'`. **Ícone**: `:89` `svg[data-icone-nome="warning"]`, `:114` `"check-circle"`, `:127` `"x-circle"`, e sobretudo `:153` — `expect(new Set(nomes).size).toBe(3)` renderizando as três categorias e provando que os identificadores são **par a par distintos**. **Cor**: `toHaveClass('categoria-decisao-badge--{categoria}')` nas três, com as cores em `SuperficieEventoDecisao.css:22-35` (proxy por classe; o jsdom não carrega CSS) | ✅ **PASS** (era ⚠️ na Round 1) |
| **RISCO-13** — progresso reflete a etapa real da máquina de estados; frontend não recalcula nem antecipa resultado | Progresso real, zero recálculo | `SuperficieEventoDecisao.test.tsx:54` — estado `carregando`; `:62-63` — `findByText(/Em processamento/)` + `queryByRole('table')).not.toBeInTheDocument()`; `:170-171` — `toHaveBeenCalledWith(EXECUCAO_ID)` / `toHaveBeenCalledTimes(1)`; falha real vira `role="alert"` "Indisponível". Cliente: `api/avaliacaoRisco.test.ts:79` — `resolves.toBeNull()` no 404; `:91-92` — 422 → `codigo === 'execucao_id_invalido'`; `:101-102` — rede → `codigo === 'falha_de_rede'`. **Melhorado na Round 2**: o 404 deixou de encobrir o terminal `sem_regra_ativa` (ver RISCO-09), então "Em processamento" agora só aparece para execuções genuinamente não avaliadas | ✅ PASS (reforçado) |

**Status**: ✅ **13/13 ACs cobertos**; 11 plenamente casados com o resultado definido pela spec, 2 ⚠️ spec-precision gaps herdados (RISCO-05/06) que a própria Round 1 declarou fora do escopo das correções — a spec não define um resultado preciso para a comparação de "período", logo não há valor a asserir.

### Notas de julgamento (herdadas da Round 1, re-conferidas e mantidas)

**A — "severidade e período" (RISCO-05/06).** A spec enumera quatro operandos; o motor compara dois (`área`, `intensidade`). "Severidade" está dobrada em `intensidade`; "período" não é comparado com nada — `RegraSnapshot` não carrega campo de janela temporal. Re-confirmado no código atual: `dominio/avaliador_risco.py:95-130` inalterado pelo commit de correção. Continua lacuna de precisão da spec, não falha de implementação.

**B — "produto correto" (RISCO-05/06).** `repositorio_regras.py:28` filtra apenas por `evento_tipo` e `estado='ativa'`; `apolice_tipo` é transportado mas nunca verificado. A ligação residencial/automóvel existe só nos dados semeados (`semeador.py:189-193`, `:201-204`). Inalterado — fora do escopo desta rodada.

**C — RISCO-08 (zero IA).** Garantia estrutural sólida mas inferencial: `test_camadas.py:12-19` proíbe `central_preventiva.adaptadores`, não literalmente `openai`. Inalterado.

**E — Alcance real.** `ServicoAvaliacaoRisco.avaliar_evento` e `SuperficieEventoDecisao` seguem sem caminho de produção — lacuna de integração declarada pelo autor em `tasks.md` T6 e `STATE.md`. RISCO-09/10 estão verificados no nível unitário + repositório real + rota HTTP real, não ponta a ponta pela aplicação em execução.

### Julgamentos da Round 1 mantidos (re-conferidos, não re-litigados)

Reuso da tabela `regras` satisfaz "centralizado, versionado e legível" (RISCO-01); o teste de tipo não suportado por bypass de enum é desenho legítimo (RISCO-03/04); granizo checar "área aplicável" é exigido pela spec, não scope creep (RISCO-06); o 404 como estado de progresso no frontend está correto (RISCO-13) — e agora está *mais* correto, porque deixou de cobrir um caso terminal.

---

## Discrimination Sensor

Worktree isolada por mutação (`git worktree add --detach <scratch> 1122288`), removida imediatamente após cada verificação. Escopo estreito por instrução: re-injetar as duas falhas que a Round 1 mandou fechar, mais uma nova no caminho de menor confiança (a migração `0005`).

| # | Mutação | File:line | Descrição | Testes executados | Killed? |
| --- | --- | --- | --- | --- | --- |
| M2′ | **Re-injeção do sobrevivente da Round 1** | `aplicacao/avaliacao_risco.py:97` | `salvar(..., regra.versao, ...)` → `salvar(..., 1, ...)` (literal) | `testes/test_avaliacao_risco.py` | ✅ **Killed** — `test_snapshot_salvo_carrega_execucao_evento_regra_e_versao_corretos` falhou em `:154` com `AssertionError: assert 1 == 7` |
| M4 | **Re-injeção da colisão de ícone** | `SuperficieEventoDecisao.tsx:46` | `data-icone-nome="x-circle"` → `"check-circle"` (dois ícones iguais) | `SuperficieEventoDecisao.test.tsx` | ✅ **Killed** — 2 failed / 7 passed; o teste de RISCO-12 falhou em `:153` com `expected 2 to be 3`, mais o teste por categoria |
| M5 | **Nova — perda silenciosa de dados no recreate-and-copy** | `migracoes/0005_avaliacao_risco_sem_regra.sql:22-26` | Removido o `INSERT INTO avaliacoes_risco_nova SELECT ... FROM avaliacoes_risco` — a tabela é recriada vazia e as linhas existentes somem no `DROP` | `testes/test_migracoes.py`, `testes/test_inicializador.py` | ✅ **Killed** — `test_migracao_sem_regra_preserva_avaliacoes_e_aceita_regra_nula` falhou em `:189` com `assert None is not None` |

**Traçado sem mutação (mecanicamente certo, sem gastar ciclo de worktree)**: remover de volta a chamada `salvar` do caminho sem regra (`aplicacao/avaliacao_risco.py:90` — a regressão exata da Round 1) seria morto por `testes/test_avaliacao_risco.py:133` (`assert len(avaliacoes.salvas) == 1` → `0 == 1`) e por `:134` (desempacotamento de `avaliacoes.salvas[0]` → `IndexError`).

**Sensor depth**: lightweight (3 mutações — 2 re-injeções dirigidas dos achados da Round 1 + 1 nova no caminho de maior risco introduzido pela correção)

**Result**: **3/3 killed** — ✅ **PASS**

**Verificação de isolamento**: `git status --porcelain` vazio antes e depois de cada ciclo; `git worktree list` mostra apenas a árvore real em `1122288`. Nenhum resíduo.

---

## Verificação de regressão (foco: relaxamento de `NOT NULL` pela migração `0005`)

A pergunta central desta rodada: relaxar `avaliacoes_risco.regra_id`/`regra_versao` pode ter quebrado algum leitor que assumia presença.

| Verificação | Método | Resultado |
| --- | --- | --- |
| **Quem lê a tabela `avaliacoes_risco`?** | `grep -rn "avaliacoes_risco" src/backend/central_preventiva src/frontend/src` | Apenas **dois** consumidores: `repositorio_avaliacoes_risco.py` (`INSERT` em `:88`, `SELECT` em `:110`) e `adaptadores/http/avaliacao_risco.py` (que só usa o repositório). **Nenhum relatório, nenhum `JOIN`, nenhuma agregação, nenhum outro `SELECT`.** Superfície de regressão fechada |
| **A desserialização aguenta `NULL`?** | Leitura de `repositorio_avaliacoes_risco.py:119-120` | `regra_id=None if linha[3] is None else UUID(str(linha[3]))` e idem para `regra_versao` — o antigo `UUID(str(None))` teria levantado `ValueError`. Coberto por `testes/test_repositorio_avaliacoes_risco.py:83-92` (round-trip real em DuckDB) |
| **Linhas pré-existentes sobrevivem à recriação?** | Teste + mutação M5 | `testes/test_migracoes.py:172-193` insere uma linha sob o schema `0004`, aplica a `0005` e assere `id`, `regra_id` e `motivo` preservados. Mutação M5 confirma que a asserção é discriminante |
| **Contagem/ordem de migrações consistente** | `testes/test_migracoes.py:81-82,89` e `:100,:107`; `testes/test_inicializador.py:73,99` | `versoes_aplicadas == (1,2,3,4,5)`, `versao_final == 5`, registro `(5, "avaliacao risco sem regra")`, e reexecução idempotente. Verde |
| **Contrato OpenAPI sincronizado ponta a ponta** | `testes/test_openapi_sincronizado.py:29-35` | `assert documento_ao_vivo == snapshot` — **igualdade exata** do documento vivo contra `composicao/openapi.json` versionado. O snapshot commitado carrega `anyOf: [{format:uuid,type:string},{type:null}]` para `regra_id` e `anyOf: [{type:integer},{type:null}]` para `regra_versao`. Portanto o contrato publicado reflete de fato a nulidade, e não pode divergir em silêncio |
| **Tipos do frontend refletem a nulidade (não só o backend)** | `src/api/tipos-gerados.ts:421,426` + `src/api/avaliacaoRisco.ts:103-110` | `tipos-gerados.ts` regenerado: `regra_id: string \| null`, `regra_versao: number \| null`. Crucialmente, `paraAvaliacaoRisco` é **tipada a partir de** `components['schemas']['RespostaAvaliacaoRisco']` e atribui `regraId: corpo.regra_id` — se `AvaliacaoRisco.regraId` tivesse ficado `string`, o `tsc` do `npm run build` teria falhado. A propagação da nulidade é **verificada por tipo**, não editada à mão. `npm run build` verde confirma |
| **Estado novo alcançável na UI** | `SuperficieEventoDecisao.tsx:27-30,59` | `motivo === 'sem_regra_ativa'` com `relevante === false` cai em `calcularCategoria` → `'sem_risco'` (rótulo "Sem risco", ícone `check-circle`, classe `--sem_risco`) e o texto já existia em `ROTULOS_MOTIVO:59` ("Nenhuma regra ativa para este tipo de evento."). **Sem crash, sem `undefined` na tela.** Com `criterios: []` a tabela renderiza cabeçalho e corpo vazio — correto, mas não coberto por teste de frontend (ver Fix 7, Cosmético) |
| **Asserções enfraquecidas em algum lugar?** | Diff `22b2906..1122288` de todos os arquivos de teste | **Nenhuma.** Todas as edições fortalecem: `assert avaliacoes.salvas == []` → bloco de 6 asserções; `querySelector('svg')` → `svg[data-icone-nome="warning"]`; `regra_versao=1` → `7`. Nenhum teste removido; nenhum `skip`/`xfail` introduzido |

---

## Payload / Conjunction Rule (rota HTTP e repositórios)

| Alvo | Asserção verifica valor real? | Evidência |
| --- | --- | --- |
| `GET .../avaliacao-risco` 200 (com regra) | ✅ Sim | `test_avaliacao_risco_api.py:70-78` — status **e** `execucao_id`, `relevante`, `motivo`, `len(criterios) == 2`, `operando`, `atende`, `valor_observado == "72.5 mm"` |
| `GET .../avaliacao-risco` 200 (**sem regra ativa**, novo) | ✅ Sim | `test_avaliacao_risco_api.py:103-109` — status `200` **e** `relevante is False`, `motivo == "sem_regra_ativa"`, `regra_id is None`, `regra_versao is None`, `criterios == []`. Não é "status 200" isolado |
| `GET` 404 | ✅ Sim | `:118-120` — status + `content-type application/problem+json` + `codigo == "avaliacao_risco_inexistente"`. **Continua distinguindo** o caso "ainda não avaliada" do terminal já decidido |
| `GET` 422 (id malformado) | ✅ Sim | `:128-130` — status + content-type + `codigo == "execucao_id_invalido"` |
| `RepositorioAvaliacoesRisco.salvar`/`obter_por_execucao` (com regra) | ✅ Sim | `test_repositorio_avaliacoes_risco.py:54-62` — os 8 campos, incluindo `regra_versao == 7` (não trivial) e a tupla inteira de `criterios` |
| `RepositorioAvaliacoesRisco` (regra nula, novo) | ✅ Sim | `:87-92` — `regra_id is None`, `regra_versao is None`, `relevante is False`, `motivo`, `criterios == ()` |
| `ServicoAvaliacaoRisco` — chamada a `salvar` | ✅ Sim (era ⚠️ na Round 1) | `test_avaliacao_risco.py:150-154` inspeciona a tupla real de argumentos e `versao_salva == 7` é agora discriminante (provado por M2′) |
| `RepositorioRegras.obter_ativa` | ⚠️ Parcial | `test_repositorio_regras.py:49-53` — `apolice_tipo` segue round-trip do valor inserido pelo próprio teste (nota B, fora do escopo) |

Nenhuma asserção do tipo "a chamada aconteceu" ou "status isolado". A regra é respeitada.

---

## Code Quality

| Princípio | Status |
| --- | --- |
| Minimum code | ✅ — a constante morta foi removida (Fix 5); a migração `0005` faz exatamente uma coisa; a rota HTTP não ganhou nenhum ramo novo (o `200` emerge do snapshot passar a existir, não de um `if` adicional) |
| Surgical changes | ✅ — apenas os arquivos exigidos pelos Fix 1–5; nenhuma edição em código não relacionado |
| No scope creep | ✅ — nenhum campo, endpoint ou abstração além do necessário para persistir a decisão terminal |
| Matches patterns | ⚠️ — o recreate-and-copy segue o precedente da migração `0003` (AD-015) e o comentário de relação como na `0004` ✅; **porém** o README, que documenta uma seção por migração (`## Tabelas da migração 0001/0002/0003/0004`), **não ganhou seção para a `0005`**, e a tabela da `0004` (`README.md:274-275`) ainda declara `regra_id`/`regra_versao` como `NOT NULL` — hoje factualmente incorreto. Ver Fix 6 |
| Spec-anchored outcome check | ✅ — 11/13 ACs casam com o resultado definido pela spec; os 2 restantes são lacunas de precisão da própria spec, explicitamente fora do escopo desta rodada |
| Per-layer Coverage Expectation | ✅ — domínio 1:1 com as ACs; rota cobre feliz + **feliz sem regra** + 404 + 422; migração cobre preservação + nulidade. Ressalva conhecida: nenhum caminho de produção exercita o serviço (nota E, declarado pelo autor) |
| Every test maps to a spec requirement | ✅ — os 4 testes novos citam RISCO-09 (3) e RISCO-02 (1) nos docstrings; o teste novo de frontend cita RISCO-12. Nenhum teste órfão |
| Documented guidelines followed | ✅ — `AGENTS.md`, `README.md` de persistência, AD-015 (recreate-and-copy), AD-11 (versão como valor) |

---

## Edge Cases

- [x] **Valor-limite de fronteira inclusiva → relevante** — `testes/test_avaliador_risco.py:79-82` (`50.0` → `relevante is True`); agora **também documentado** em `README.md:121`
- [x] **Valor-limite de fronteira exclusiva → não relevante** — vacuamente satisfeito e **agora declarado como tal** na documentação (`README.md:114`: "nenhuma fronteira exclusiva está configurada nesta demonstração"), com guarda automatizada em `test_migracoes.py:302`. Era o ponto aberto da Round 1
- [x] **Área não reconhecida → não relevante com motivo, não erro técnico** — `testes/test_avaliador_risco.py:95-99` (chuva) e `:114-115` (granizo); ambos devolvem `ResultadoAvaliacaoRisco`, nenhuma exceção
- [x] **(novo) Sem regra ativa para o tipo → terminal `sem_risco` explicável, não um 404 indistinguível** — `test_avaliacao_risco.py:133-140`, `test_repositorio_avaliacoes_risco.py:83-92`, `test_avaliacao_risco_api.py:103-109`

---

## Gate Check

- **Gate command (Build)**: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright` + `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`
- **Executado nesta rodada pelo próprio Verificador** (não herdado do orquestrador):
  - `pytest`: **292 passed**, 0 failed, 0 skipped (exit 0)
  - `ruff check .`: **All checks passed!**
  - `pyright`: **0 errors, 0 warnings, 0 informations**
  - `vitest --run`: **164 passed** em 20 arquivos, 0 failed (exit 0)
  - `npm run lint`: exit 0 (8 warnings pré-existentes de `react-hooks`/fast-refresh, nenhuma nova nem em arquivo desta história além de `SuperficieEventoDecisao.tsx:79`, que já existia na Round 1)
  - `npm run build`: **✓ built in 228ms** (exit 0) — confirma a checagem de tipos da propagação de nulidade
- **Test count antes da feature**: 268 backend / 151 frontend
- **Test count após a Round 1**: 288 backend / 163 frontend
- **Test count após as correções (Round 2)**: **292 backend / 164 frontend**
- **Delta da rodada de correção**: **+4 backend** (`test_avaliacao_risco_api` +1 `sem_regra_ativa` 200; `test_migracoes` +2 preservação/nulidade e documentação de fronteiras; `test_repositorio_avaliacoes_risco` +1 regra nula) e **+1 frontend** (distinção de ícones, RISCO-12)
- **Delta total da feature**: +24 backend / +13 frontend
- **Test Integrity**: contagem **só cresceu**; nenhum teste removido; nenhuma asserção enfraquecida (todas as edições fortalecem — ver tabela de regressão)
- **Skipped**: nenhum
- **Failures**: nenhuma

---

## Fix Plans

Nenhum bloqueador. Dois itens registrados para acompanhamento — **não bloqueiam o PASS** e não devem consumir a terceira iteração de correção desta história.

### Fix 6: Atualizar a documentação versionada do schema para a migração `0005` (Minor)

- **Root cause**: regressão introduzida pela própria correção do Fix 1. `adaptadores/persistencia/README.md:274-275` continua declarando `regra_id` como `NOT NULL, chave estrangeira lógica para regras(id)` e `regra_versao` como `NOT NULL`, o que deixou de ser verdade em `1122288`. Além disso o README tem uma seção por migração (`## Tabelas da migração 0001…0004`) e a `0005` não ganhou nenhuma — apesar de existir o precedente exato da `0003`, que documenta sua própria alteração recreate-and-copy em `README.md:215`. O documento se descreve como "Documento versionado do schema operacional", então a divergência é um defeito factual num artefato versionado.
- **Por que passou despercebido**: `test_migracoes.py:281-291` só assere que os *nomes de tabela* e alguns termos genéricos aparecem no README — não valida nulidade nem exige uma seção por migração.
- **Fix task**: acrescentar `## Tabelas da migração 0005_avaliacao_risco_sem_regra` no mesmo formato da `0003`, explicando o relaxamento e o motivo (RISCO-09), e corrigir as duas linhas da tabela da `0004` para refletir que as colunas aceitam `NULL` quando não havia regra ativa. Verificar: o README menciona `0005` e nenhuma das duas colunas aparece mais como `NOT NULL`.
- **Priority**: Minor (documentação; nenhuma AC depende disso, nenhum comportamento afetado)

### Fix 7: Cobrir a renderização de `sem_regra_ativa` na superfície (Cosmético)

- **Root cause**: o Fix 1 tornou `motivo: 'sem_regra_ativa'` com `criterios: []` um estado **alcançável** na UI pela primeira vez (antes o 404 desviava para "Em processamento"). O componente o trata corretamente por construção — cai na categoria `sem_risco` e o rótulo já existe em `SuperficieEventoDecisao.tsx:59` — mas nenhum teste de frontend exercita esse motivo, e a tabela de critérios renderiza cabeçalho com corpo vazio.
- **Fix task**: um caso em `SuperficieEventoDecisao.test.tsx` com `motivo: 'sem_regra_ativa'`, `criterios: []`, asserindo "Sem risco" + "Nenhuma regra ativa para este tipo de evento."; opcionalmente suprimir a tabela quando `criterios.length === 0`.
- **Priority**: Cosmético

---

## Lições da Round 1 — condições subjacentes

Nenhuma lição nova distilada nesta rodada (PASS sem sinal fundamentado novo além do Fix 6, que é documentação e já está coberto conceitualmente por L-022). Estado das lições da Round 1 em `.specs/lessons.json`:

| Lição | Texto | Condição subjacente fechada nesta feature? |
| --- | --- | --- |
| **L-020** | Escolher valores de fixture diferentes de defaults plausíveis, para que um bug de valor errado não passe pela asserção | ✅ Fechada — `versao=7` em `test_avaliacao_risco.py:30` e `test_repositorio_avaliacoes_risco.py:49`; mutante M2′ morto |
| **L-021** | Quando uma coluna `NOT NULL` impede persistir um resultado exigido por uma AC, relaxar o schema em vez de pular a escrita em silêncio | ✅ Fechada — migração `0005` + `avaliacao_risco.py:90` |
| **L-022** | Levar exemplos de fronteira de limiar ao artefato de documentação nomeado pelo requisito, não só ao arquivo de teste | ✅ Fechada para RISCO-02 — `README.md:104-122`, guardado por `test_migracoes.py:294-305`. (O Fix 6 é a mesma família de risco — doc versionada divergindo do código — reincidindo em outro ponto; se recorrer numa próxima feature, vale promover L-022 de `candidate` a estabelecida) |
| **L-023** | Comparar e asserir cada operando enumerado por um requisito, ou registrar explicitamente por que um operando não é comparado | ⚠️ **Aberta por decisão** — RISCO-05/06 ("período") seguem sem comparação e sem registro explícito no código; a Round 1 declarou isso fora do escopo desta rodada de correção |
| **L-024** | Quando um requisito exige distinção por texto, ícone e cor, asserir que os três sinais diferem entre categorias | ✅ Fechada — `SuperficieEventoDecisao.test.tsx:153` (`new Set(nomes).size === 3`); colisão de ícone morta pela mutação M4. Ressalva: "cor" segue asserida por nome de classe (o jsdom não carrega CSS) — limite de ferramenta, não de asserção |

---

## Requirement Traceability Update

| Requirement | Round 1 Status | Round 2 Status |
| --- | --- | --- |
| RISCO-01 | ✅ Verified | ✅ Verified |
| RISCO-02 | ⚠️ Spec-precision gap | ✅ **Verified** |
| RISCO-03 | ✅ Verified | ✅ Verified |
| RISCO-04 | ✅ Verified | ✅ Verified |
| RISCO-05 | ⚠️ Spec-precision gap | ⚠️ Spec-precision gap (fora de escopo, nota A/B) |
| RISCO-06 | ⚠️ Spec-precision gap | ⚠️ Spec-precision gap (fora de escopo, nota A/B) |
| RISCO-07 | ✅ Verified | ✅ Verified |
| RISCO-08 | ✅ Verified | ✅ Verified |
| RISCO-09 | ❌ Needs Fix | ✅ **Verified** |
| RISCO-10 | ⚠️ Verified com teste fraco | ✅ **Verified** (M2′ morto) |
| RISCO-11 | ✅ Verified | ✅ Verified |
| RISCO-12 | ⚠️ Spec-precision gap | ✅ **Verified** |
| RISCO-13 | ✅ Verified | ✅ Verified |

---

## Summary

**Overall**: ✅ **Ready**

**Spec-anchored check**: 13/13 ACs cobertos com citação `file:line`; **11/13 casam exatamente com o resultado definido pela spec**; 2 spec-precision gaps herdados (RISCO-05/06, "período") que a Round 1 declarou fora do escopo — a spec não define o resultado preciso, então não há valor a asserir
**Sensor**: **3/3 mutantes mortos** (as 2 falhas que a Round 1 mandou fechar, re-injetadas e agora mortas; + 1 nova no recreate-and-copy da migração `0005`)
**Gate**: 292 backend + 164 frontend passed, 0 failed, 0 skipped; `ruff`/`pyright`/`lint`/`build` verdes — **todos re-executados pelo Verificador nesta rodada**

**O que funciona**: as cinco correções fazem o que prometem, verificado no código real e não pelo sumário. A lacuna de RISCO-09 está fechada em **todas as camadas** — migração, repositório, serviço, rota HTTP e tipos do frontend — e cada camada tem asserção própria sobre o valor real, não sobre "a chamada aconteceu". O relaxamento de `NOT NULL` foi feito pelo caminho seguro (recreate-and-copy com preservação provada por mutação) e **não tem nenhum outro leitor no repositório** que pudesse assumir presença: só o repositório e a rota tocam a tabela. A nulidade propaga ponta a ponta de forma **verificada por máquina**, não por revisão: o snapshot `openapi.json` é guardado por igualdade exata contra o documento vivo (`test_openapi_sincronizado.py:35`), e o mapeamento do frontend é tipado a partir do schema gerado, de modo que o `tsc` do build reprovaria uma divergência. O mutante M2 da Round 1 está morto com uma mensagem clara (`assert 1 == 7`). A distinção por ícone de RISCO-12 é agora asserida como distinção real (conjunto de três nomes), não como mera presença de `<svg>`. Os exemplos limítrofes de RISCO-02 chegaram à documentação com guarda automatizada. Nenhuma asserção foi enfraquecida em lugar nenhum e a contagem de testes só cresceu.

**Problemas encontrados**: nenhum bloqueador. Uma regressão **menor de documentação** introduzida pela própria correção — `README.md:274-275` ainda declara `regra_id`/`regra_versao` como `NOT NULL` e a migração `0005` não ganhou seção no documento versionado do schema, apesar do precedente da `0003` (Fix 6, Minor). E um estado de UI recém-alcançável (`sem_regra_ativa` com zero critérios) que o componente trata corretamente por construção mas nenhum teste de frontend exercita (Fix 7, Cosmético). Contexto conhecido e já declarado pelo autor, inalterado: nem `ServicoAvaliacaoRisco` nem `SuperficieEventoDecisao` são alcançáveis por caminho de produção — lacuna de integração a fechar em história futura.

**Next steps**: marcar a História 2.3 como concluída. Fix 6 e Fix 7 podem acompanhar a próxima história que tocar persistência ou a superfície de decisão; nenhum dos dois justifica uma terceira iteração de correção nesta história.
