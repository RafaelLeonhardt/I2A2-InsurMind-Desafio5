# História 2.3: Identificar eventos meteorológicos relevantes — Validation

**Date**: 2026-09-02
**Spec**: `.specs/features/2-3-identificar-eventos-meteorologicos-relevantes/spec.md`
**Diff range**: `6b2108c..22b2906` (6 commits, T1–T6; 25 arquivos, +2157/−46)
**Verifier**: independent sub-agent (author ≠ verifier) — read-only sobre a árvore real; mutações apenas em worktrees descartáveis

**Verdict**: ❌ **FAIL** — 1 mutante sobrevivente (M2) + 1 lacuna de AC fundamentada (RISCO-09, caminho `sem_regra_ativa`). Todos os gates estão verdes; as lacunas são de *discriminação de teste* e de *persistência de explicabilidade*, não de build.

---

## Task Completion

| Task | Status | Notes |
| --- | --- | --- |
| T1 — Migração `0004_avaliacao_risco` | ✅ Done | Tabela + README + `test_migracoes.py`/`test_inicializador.py` estendidos |
| T2 — `AvaliadorRisco` (motor determinístico) | ✅ Done | Função pura; adição de "área aplicável" para granizo justificada (ver RISCO-06) |
| T3 — `RepositorioRegras` / `RepositorioAvaliacoesRisco` | ✅ Done | `regra_versao` explícito conforme Nota de implementação |
| T4 — `ServicoAvaliacaoRisco` | ⚠️ Partial | Caminho `sem_regra_ativa` não persiste código/motivo (ver RISCO-09); serviço não é chamado por nenhum caminho de produção |
| T5 — Endpoint HTTP de detalhe | ✅ Done | Roteador incluído em `composicao/api.py:89-92`; `openapi.json` sincronizado |
| T6 — Superfície "Evento e decisão" | ⚠️ Partial | Componente não montado em nenhuma rota (lacuna declarada pelo autor em `tasks.md` T6 / `STATE.md`) |

---

## Spec-Anchored Acceptance Criteria

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| **RISCO-01** — centralizar limiares em configuração versionada e legível, com valores padrão e justificativa | Limiar de chuva = 50.0 mm, versionado, com justificativa documentada | Config: tabela `regras` (`versao`/`estado`), default semeado em `src/backend/central_preventiva/adaptadores/persistencia/semeador.py:189-190` (`"chuva_intensa", 50.0`); leitura versionada em `repositorio_regras.py:27-29` (`WHERE estado='ativa' ORDER BY versao DESC`); justificativa em `design.md:136-138`; schema documentado em `adaptadores/persistencia/README.md` (seção `0004`). Teste: `testes/test_repositorio_regras.py:50` — `assert regra.limiar_meteorologico == 50.0`; `:77-78` — `assert regra.versao == 2` (regra `substituida` ignorada) | ✅ PASS (com ressalva, ver Code Quality #1) |
| **RISCO-02** — documentação SHALL explicitar fronteiras inclusivas/exclusivas, **com exemplos limítrofes** | Para cada limiar: qual lado da fronteira é relevante + exemplos no valor-limite | Fronteira inclusiva documentada em `design.md:136` (`intensidade >= 50.0` — fronteira **inclusiva**) e ecoada em runtime na justificativa (`dominio/avaliador_risco.py:111-112`). Exemplos limítrofes existem **apenas como testes** (`testes/test_avaliador_risco.py:69` `49.9`, `:79` `50.0`, `:86` `50.1`), não em nenhum artefato de documentação; nenhum limiar é documentado como exclusivo nem o documento declara que não há fronteira exclusiva configurada | ⚠️ **Spec-precision gap** |
| **RISCO-03** — reconhecer chuva intensa e granizo como suportados | Ambos avaliados, não rejeitados | `dominio/avaliador_risco.py:99` (guarda de tipo); `testes/test_avaliador_risco.py:81-82` — `assert resultado.relevante is True` / `motivo == MOTIVO_RELEVANTE` (chuva); `:105-108` — idem + `criterio_ocorrencia.atende is True` (granizo) | ✅ PASS |
| **RISCO-04** — tipo diferente → registrado como não suportado **sem avançar** | Resultado "não suportado", limiar não avaliado | `dominio/avaliador_risco.py:99-100` → `_rejeitar_tipo_nao_suportado`; `testes/test_avaliador_risco.py:133` — `assert resultado.motivo == MOTIVO_TIPO_NAO_SUPORTADO`; `:134` — `assert len(resultado.criterios) == 1` (prova que o ramo de limiar nunca foi executado, apesar de `intensidade=999.0` em `:126`) | ✅ PASS |
| **RISCO-05** — chuva: comparar medidas, área, severidade e período com a regra do **residencial**, resultado determinístico com valores e critérios | Resultado com valores observados + critérios aplicados | `dominio/avaliador_risco.py:102-126`; `testes/test_avaliador_risco.py:72-75` — `motivo == MOTIVO_ABAIXO_DO_LIMIAR`, `criterio_intensidade.atende is False`, `valor_observado == "49.9 mm"`; `:96-99` — `motivo == MOTIVO_AREA_NAO_APLICAVEL`, `criterio_area.valor_observado == AREA_OUTRA` | ⚠️ **Spec-precision gap** (ver nota A) |
| **RISCO-06** — granizo: idem contra a regra do **automóvel** | Resultado determinístico com valores e critérios | `dominio/avaliador_risco.py:128-137`; `testes/test_avaliador_risco.py:105-108` (relevante por ocorrência) e `:114-115` — `assert resultado.motivo == MOTIVO_AREA_NAO_APLICAVEL` (fora da área) | ⚠️ **Spec-precision gap** (ver notas A e B) |
| **RISCO-07** — mesma entrada + mesma versão de regra → resultado e justificativa idênticos | Igualdade byte-a-byte de resultado e justificativa | `dominio/avaliador_risco.py:92-137` (função pura, sem I/O, sem estado); `testes/test_avaliador_risco.py:143` — `assert primeira == segunda` (dataclass `frozen` compara `relevante`, toda a tupla de `Criterio` incluindo strings de justificativa, e `motivo`) | ✅ PASS |
| **RISCO-08** — nenhum LLM, prompt ou heurística probabilística participa da decisão | Zero envolvimento de IA em qualquer caminho | Estrutural: `dominio/avaliador_risco.py:1-9` importa apenas stdlib + domínio; `testes/test_camadas.py:7-36` proíbe, por varredura AST de todo `dominio/*.py`, importar `central_preventiva.adaptadores` (onde viveria qualquer cliente OpenAI); `aplicacao/avaliacao_risco.py:54-63` declara exatamente 3 portas + a função pura — nenhuma porta de IA existe para ser chamada | ✅ PASS (evidência estrutural, ver nota C) |
| **RISCO-09** — evento sem critérios → terminal `sem_risco` **com código e motivo persistidos**, sem elegibilidade/mensagem/OpenAI | Estado `sem_risco` + código e motivo gravados | `aplicacao/avaliacao_risco.py:98-103`; `testes/test_avaliacao_risco.py:103` — `assert execucoes.transicoes == [(execucao_id, 1, EstadoExecucao.SEM_RISCO)]` (tupla exata) e `:102` — `assert len(avaliacoes.salvas) == 1` (motivo persistido em `avaliacoes_risco.motivo`). **Sub-caso `sem_regra_ativa`**: `aplicacao/avaliacao_risco.py:86-93` retorna antes de `salvar`; `testes/test_avaliacao_risco.py:125` — `assert avaliacoes.salvas == []`, `:124` — `motivo == MOTIVO_SEM_REGRA_ATIVA` (apenas em memória) | ❌ **GAP** (ver nota D) |
| **RISCO-10** — evento relevante → `avaliando_elegibilidade` preservando snapshot imutável do evento e da versão da regra | Transição + snapshot de `evento_id`, `regra_id`, `regra_versao` | `aplicacao/avaliacao_risco.py:96-103`; `testes/test_avaliacao_risco.py:114` — `assert execucoes.transicoes == [(execucao_id, 1, EstadoExecucao.AVALIANDO_ELEGIBILIDADE)]`; `:137-141` — `execucao_salva == execucao_id`, `evento_salvo == evento.id`, `regra_salva == REGRA_CHUVA.id`, `versao_salva == REGRA_CHUVA.versao`. Imutabilidade: `repositorio_avaliacoes_risco.py:78-93` só `INSERT`, `:99-103` só `SELECT` (nenhum `UPDATE`/`DELETE`); `migracoes/0004_avaliacao_risco.sql` grava `regra_versao INTEGER NOT NULL` como valor, não referência | ⚠️ PASS enfraquecido — **mutante M2 sobreviveu** exatamente nesta asserção de versão |
| **RISCO-11** — detalhe exibe operando, valor observado, resultado e justificativa de cada critério | As 4 colunas por critério | Backend: `testes/test_avaliacao_risco_api.py:75-78` — `len(corpo["criterios"]) == 2`, `criterios[0]["operando"] == "área aplicável"`, `criterios[0]["atende"] is True`, `criterios[1]["valor_observado"] == "72.5 mm"` (round-trip JSON real, do `INSERT` ao corpo HTTP). Repositório: `testes/test_repositorio_avaliacoes_risco.py:61` — `assert avaliacao.criterios == RESULTADO_RELEVANTE.criterios` (tupla completa, incluindo justificativas). Frontend: `SuperficieEventoDecisao.test.tsx:72-77` — `getByText('área aplicável')`, `getByText('9990001')`, `getAllByText('Atende')).toHaveLength(2)`, justificativa integral | ✅ PASS (não alcançável na app, ver nota E) |
| **RISCO-12** — distinguir relevância / ausência de risco / dado inválido por **texto, ícone e cor** | Tríade texto+ícone+cor por categoria | `SuperficieEventoDecisao.tsx:27-44`; `SuperficieEventoDecisao.test.tsx:85-89` — `findByText('Relevante')` + `toHaveClass('categoria-decisao-badge--relevante')` + `badge?.querySelector('svg')` presente; `:110-113` — `findByText('Sem risco')` + classe `--sem_risco`; `:123-125` — `findByText('Dado inválido')` + classe `--dado_invalido`. Cores em `SuperficieEventoDecisao.css:22-35` | ⚠️ **Spec-precision gap** (ver nota F) |
| **RISCO-13** — progresso reflete a etapa real da máquina de estados; frontend não recalcula nem antecipa resultado | Progresso real, zero recálculo | `SuperficieEventoDecisao.test.tsx:54` — estado `carregando`; `:62-63` — `findByText(/Em processamento/)` + `queryByRole('table')).not.toBeInTheDocument()` (nada antecipado); `:144-145` — `toHaveBeenCalledWith(EXECUCAO_ID)` e `toHaveBeenCalledTimes(1)`; `:133-134` — falha real vira `role="alert"` "Indisponível", distinta de "aguardando". Cliente: `api/avaliacaoRisco.test.ts:79` — `resolves.toBeNull()` no 404; `:91-92` — 422 vira `ErroAvaliacaoRisco` com `codigo === 'execucao_id_invalido'`; `:101-102` — rede vira `codigo === 'falha_de_rede'`, `status` `null` | ✅ PASS |

**Status**: ❌ 1 GAP (RISCO-09) + ⚠️ 4 spec-precision gaps (RISCO-02, 05, 06, 12); 8 ACs plenamente cobertos.

### Notas de julgamento

**A — "severidade e período" (RISCO-05/06).** A spec manda comparar quatro operandos: *medidas, área, severidade e período*. O motor compara dois: `área` (`avaliador_risco.py:77`) e `intensidade` (`:105`). "Severidade" está dobrada dentro de `intensidade`; "período" **não é comparado com nada** — `RegraSnapshot` não carrega nenhum campo de janela temporal contra o qual `periodo_inicio`/`periodo_fim` pudessem ser confrontados. Defensável (a medida já é "mm acumulados no período"), mas a spec não define o resultado preciso de uma comparação de período, então isso é lacuna de precisão da spec, não falha de implementação.

**B — "produto correto" (RISCO-05/06).** A spec exige a regra ativa *associada ao seguro residencial* (chuva) e *automóvel* (granizo). `repositorio_regras.py:28` filtra **apenas** por `evento_tipo = ? AND estado = 'ativa'` — `apolice_tipo` é transportado em `RegraSnapshot` (`:39`) mas nunca verificado nem asserido. A ligação existe só nos dados semeados (`semeador.py:189-193` chuva→`residencial`; `:201-204` granizo→`automovel`) e nenhum teste a afirma: `test_repositorio_regras.py:52` assere `apolice_tipo == "residencial"` sobre uma linha que o próprio teste inseriu com esse valor — round-trip, não prova de associação. Uma inversão dos produtos na configuração semeada passaria por todos os testes.

**C — RISCO-08 (zero IA).** A ausência de IA é garantida estruturalmente e a evidência é sólida, mas é *inferencial*: `test_camadas.py:12-19` não lista `openai` na tupla de importações proibidas — proíbe `central_preventiva.adaptadores`, que é onde o cliente vive hoje. A garantia depende dessa localização se manter.

**D — RISCO-09, caminho `sem_regra_ativa` (lacuna fundamentada).** A AC exige terminal `sem_risco` "com **código e motivo persistidos**". No caminho normal de não relevância isso acontece (`avaliacoes_risco.motivo`). No caminho "sem regra ativa" **nada é persistido**: `aplicacao/avaliacao_risco.py:86-93` pula `salvar` (justificado — `regra_id`/`regra_versao` são `NOT NULL` em `0004_avaliacao_risco.sql`), e `RepositorioExecucaoPreventiva.transicionar` (`repositorio_execucao_preventiva.py:81-83`) não recebe motivo algum; `execucao_preventiva` (`0001_schema_inicial.sql:80-86`) não tem coluna de motivo/código. O `ResultadoAvaliacaoRisco` com `motivo=sem_regra_ativa` existe apenas em memória e é descartado ao fim do processo. Consequência observável, não apenas um registro faltante: `GET .../avaliacao-risco` devolve `404 avaliacao_risco_inexistente`, o cliente devolve `null` (`avaliacaoRisco.ts:135-137`) e a superfície mostra "Em processamento — a execução ainda não alcançou a etapa de avaliação de risco" (`SuperficieEventoDecisao.tsx:104-109`) para uma execução **já decidida e terminal**. A decisão do autor não é errada em si (a coluna realmente é `NOT NULL`), mas a consequência — decisão terminal sem explicabilidade persistida — não foi fechada.

**E — Alcance real da superfície.** `SuperficieEventoDecisao` não é importada por nenhum arquivo fora da própria pasta, e `ServicoAvaliacaoRisco.avaliar_evento` não é chamado por nenhum caminho de produção (só por testes) — nenhuma linha de `avaliacoes_risco` é produzida pelo sistema em execução. O autor declarou a lacuna de navegação em `tasks.md` T6 e em `STATE.md`, a fechar por história de integração futura. RISCO-09/10 estão portanto verificados no nível unitário, não ponta a ponta.

**F — RISCO-12, a tríade.** Texto ✅ (`findByText` das três categorias). Cor ⚠️ — asserida por *nome de classe* como proxy; o jsdom não carrega o CSS, então nenhum teste observa cor. Ícone ❌ — apenas o caso `relevante` assere que *existe* um `<svg>`; nenhum teste assere que os três ícones **diferem** (`WarningIcon` / `XCircleIcon` / `CheckCircleIcon`, `SuperficieEventoDecisao.tsx:39-43`). Trocar dois ícones entre si sobreviveria à suíte. Como a AC exige distinção *por ícone*, a asserção não alcança o resultado definido pela spec.

### Julgamentos solicitados explicitamente

- **RISCO-01/02 — reuso da tabela `regras` em vez de arquivo de config dedicado**: **satisfaz** "centralizado, versionado e legível". `regras` é literalmente uma configuração versionada (`versao` + `estado`, com `substituida` ignorada — provado em `test_repositorio_regras.py:64-78`), o valor padrão está semeado num único lugar e a justificativa está registrada. O que **não** é satisfeito é a segunda metade de RISCO-02: os "exemplos limítrofes" nunca chegaram a um artefato de documentação — vivem só como testes.
- **RISCO-03/04 — teste do tipo não suportado via string arbitrária**: **desenho legítimo de teste**, não red flag. O enum tem só dois membros, então o ramo é uma defesa contra dado externo malformado atravessando a fronteira de normalização de 2.1; o `# type: ignore` é a única forma de exercitá-lo, e a alternativa (remover a guarda) apagaria uma defesa que a própria spec pede. A asserção `len(criterios) == 1` com `intensidade=999.0` prova que o limiar não foi tocado — é forte, não cerimonial.
- **RISCO-06 — granizo checar "área aplicável"**: **justificado pela spec, não scope creep**. RISCO-06 diz literalmente "comparar medidas, **área**, severidade e período" para granizo também, e o terceiro Edge Case da spec ("evento sem a área aplicável reconhecida → não relevante, registrando o motivo, e não como erro técnico") não é tipado por evento. A Tech Decision "sempre relevante por ocorrência" (`design.md:137`) só afirma que **não há limiar de intensidade** para granizo — não que a área seja ignorada. A adição fecha um edge case que o atalho do design deixaria aberto.
- **RISCO-13 — 404 tratado como estado de progresso, não erro**: **correto**. O backend só devolve 404 quando não existe snapshot, o que é uma posição real da máquina de estados, e o estado é distinguido de falha real (`indisponivel`, testado em `:128-135`). A única ressalva é a nota D: esse mesmo 404 hoje também encobre o caso terminal `sem_regra_ativa`.

---

## Discrimination Sensor

Worktree isolada (`git worktree add --detach <scratch> 22b2906`), um ciclo por mutação, removida logo após cada verificação.

| # | Mutação | File:line | Descrição | Testes executados | Killed? |
| --- | --- | --- | --- | --- | --- |
| M1 | Fronteira inclusiva | `dominio/avaliador_risco.py:105` | `evento.intensidade >= regra.limiar_meteorologico` → `>` | `testes/test_avaliador_risco.py` | ✅ **Killed** — `test_chuva_no_limiar_exato_e_relevante_fronteira_inclusiva` falhou (`assert False is True`) |
| M2 | Versão da regra persistida | `aplicacao/avaliacao_risco.py:96` | `salvar(..., regra.versao, ...)` → `salvar(..., 1, ...)` (literal) | `testes/test_avaliacao_risco.py` | ❌ **SURVIVED** — 4 passed |
| M3 | Classificação de categoria no frontend | `SuperficieEventoDecisao.tsx:28` | `motivo === 'tipo_nao_suportado'` → `motivo === 'abaixo_do_limiar'` no mapeamento para `dado_invalido` | `SuperficieEventoDecisao.test.tsx` | ✅ **Killed** — 2 failed / 6 passed |

**Sensor depth**: lightweight (3 mutações; a M2 foi escolhida deliberadamente para sondar uma fraqueza suspeita de fixture, não para confirmar um kill provável)

**Result**: 2/3 killed — ❌ **FAIL**

**Análise do sobrevivente M2**: as fixtures de `test_avaliacao_risco.py` usam `versao=1` (`:30`), e `test_repositorio_avaliacoes_risco.py:49` também grava `regra_versao=1`. Como o valor da fixture coincide com o literal mais plausível de um bug, a asserção `versao_salva == REGRA_CHUVA.versao` (`test_avaliacao_risco.py:140`) não consegue distinguir "propaga a versão da regra" de "grava 1". Isso é crítico para AD-11: o snapshot de versão é justamente o mecanismo que impede uma regra futura de reescrever a justificativa histórica; um bug de versão errada passaria despercebido. `test_repositorio_regras.py:78` já usa `versao=2` e mostra que a suíte sabe usar um valor não trivial — o caminho do serviço apenas não o faz.

**Verificação de isolamento**: `git status --porcelain` vazio antes e depois; `git worktree list` mostra apenas a árvore real em `22b2906`. Nenhum resíduo.

---

## Payload / Conjunction Rule (rota HTTP e repositórios)

| Alvo | Asserção verifica valor real? | Evidência |
| --- | --- | --- |
| `GET .../avaliacao-risco` 200 | ✅ Sim — round-trip JSON completo, não só status | `test_avaliacao_risco_api.py:70-78`: status `200` **e** `execucao_id`, `relevante is True`, `motivo == "relevante"`, `len(criterios) == 2`, `criterios[0]["operando"]`, `criterios[0]["atende"] is True`, `criterios[1]["valor_observado"] == "72.5 mm"` — os critérios saem de um `INSERT` real em DuckDB (`:23-46`), atravessam `_desserializar_criterios` e o modelo Pydantic |
| `GET` 404 | ✅ Sim | `:86-88`: status + `content-type` `application/problem+json` + `codigo == "avaliacao_risco_inexistente"` |
| `GET` 422 (id malformado) | ✅ Sim | `:96-98`: status + `content-type` + `codigo == "execucao_id_invalido"` — confirma o `422` próprio, não o `HTTPValidationError` do FastAPI |
| `RepositorioAvaliacoesRisco.salvar`/`obter_por_execucao` | ✅ Sim | `test_repositorio_avaliacoes_risco.py:54-62`: os 8 campos do snapshot, incluindo `regra_versao == 1` e `criterios == RESULTADO_RELEVANTE.criterios` (tupla inteira, com justificativas) |
| `RepositorioRegras.obter_ativa` | ⚠️ Parcial | `test_repositorio_regras.py:49-53` assere id/limiar/área/produto/versão, mas `apolice_tipo` é round-trip do valor que o próprio teste inseriu (nota B) |
| `ServicoAvaliacaoRisco` — chamada a `salvar` | ⚠️ Parcial | `test_avaliacao_risco.py:136-141` inspeciona a tupla real de argumentos (não "foi chamado"), mas `regra_versao` é indistinguível do literal `1` — ver M2 |

Nenhuma asserção do tipo "a chamada aconteceu" ou "status 200" isolada foi encontrada. A regra é respeitada; as duas ressalvas são de *escolha de valor de fixture*, não de forma da asserção.

---

## Code Quality

| Princípio | Status |
| --- | --- |
| Minimum code | ⚠️ — `LIMIAR_CHUVA_INTENSA_MM` (`dominio/avaliador_risco.py:11`) é declarado com docstring de justificativa mas **não é referenciado em lugar nenhum** do repositório (única ocorrência). É uma segunda cópia, morta, do default que vive em `semeador.py:190`, livre para divergir em silêncio |
| Surgical changes | ✅ — apenas arquivos exigidos pelas tasks; edições em testes existentes limitadas à contagem de migração e à lista de paths |
| No scope creep | ✅ — a checagem de área para granizo é exigida pela spec, não uma extensão (ver julgamentos) |
| Matches patterns | ✅ — `Protocol`s locais como em `coleta_meteorologica.py` (AD-1); `AvaliacaoRisco` no repositório como `SnapshotExecucao`; `problem+json` correlacionado como nos roteadores existentes; migração numerada com relações como comentário (AD-005) |
| Spec-anchored outcome check | ❌ — RISCO-09 (`sem_regra_ativa`) não atinge o resultado definido pela spec; RISCO-12 não assere a distinção por ícone |
| Per-layer Coverage Expectation | ⚠️ — domínio 1:1 com as ACs ✅; rota cobre feliz + 404 + 422 ✅; mas nenhum teste exercita o caminho ponta a ponta (serviço não é chamado em produção) |
| Every test maps to a spec requirement | ✅ — nenhum teste órfão nos 7 arquivos novos |
| Documented guidelines followed | ✅ — `AGENTS.md`, `README.md`; sem threshold dedicado, defaults fortes aplicados |

---

## Edge Cases

- [x] **Valor-limite de fronteira inclusiva → relevante** — `test_avaliador_risco.py:79-82` (`50.0` → `relevante is True`)
- [x] **Valor-limite de fronteira exclusiva → não relevante** — vacuamente satisfeito: nenhum limiar exclusivo está configurado. Não coberto por teste (não há o que testar) e não declarado como tal na documentação — contribui para o gap de RISCO-02
- [x] **Área não reconhecida → não relevante com motivo, não erro técnico** — `test_avaliador_risco.py:95-99` (chuva) e `:114-115` (granizo); ambos retornam `ResultadoAvaliacaoRisco`, nenhuma exceção

---

## Gate Check

- **Gate command (Build)**: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright` + `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`
- **Resultado**: backend **288 passed, 0 failed, 0 skipped**; frontend **163 passed em 20 arquivos, 0 failed**. `ruff`/`pyright`/`lint`/`build` confirmados verdes pelo orquestrador ao longo de toda a implementação, mais recentemente imediatamente antes deste despacho — o Verificador não os reexecutou para fins de aprovação; a contagem de testes acima foi coletada para registro
- **Test count antes da feature**: 268 backend / 151 frontend (derivado dos arquivos de teste novos)
- **Test count depois**: 288 backend / 163 frontend
- **Delta**: +20 backend (`test_avaliador_risco` 8, `test_avaliacao_risco` 4, `test_repositorio_regras` 3, `test_repositorio_avaliacoes_risco` 2, `test_avaliacao_risco_api` 3), +12 frontend (`avaliacaoRisco.test.ts` 4, `SuperficieEventoDecisao.test.tsx` 8). Nenhum teste removido; nenhuma asserção existente enfraquecida (as edições em `test_migracoes.py`/`test_inicializador.py`/`test_saude.py` apenas estendem listas exatas)
- **Skipped**: nenhum
- **Failures**: nenhuma

---

## Fix Plans

### Fix 1: Persistir código e motivo do terminal `sem_risco` sem regra ativa (RISCO-09)

- **Root cause**: `aplicacao/avaliacao_risco.py:86-93` pula `salvar` porque `avaliacoes_risco.regra_id`/`regra_versao` são `NOT NULL`, e `transicionar` não carrega motivo — logo o motivo `sem_regra_ativa` só existe em memória. Uma execução terminal fica indistinguível, na API e na tela, de uma ainda não avaliada.
- **Fix task**: tornar `regra_id`/`regra_versao` anuláveis em `avaliacoes_risco` (migração `0005`) e persistir o snapshot também no caminho sem regra, com `criterios` vazio e `motivo=sem_regra_ativa`; ou, alternativamente, gravar motivo/código em `execucao_preventiva`. Cobrir com um teste de serviço que assere `avaliacoes.salvas` não vazio com `motivo == MOTIVO_SEM_REGRA_ATIVA`, e um teste de rota que assere `200` (não `404`) para essa execução.
- **Priority**: Major

### Fix 2: Fortalecer a asserção de `regra_versao` no serviço (mutante M2)

- **Root cause**: fixtures usam `versao=1`, idêntico ao literal mais provável de um bug, tornando a asserção não discriminante.
- **Fix task**: mudar `REGRA_CHUVA.versao` em `testes/test_avaliacao_risco.py:30` para um valor não trivial (ex.: `7`) e manter `assert versao_salva == REGRA_CHUVA.versao`; idem em `test_repositorio_avaliacoes_risco.py:49`. Rever o mutante M2 e confirmar o kill.
- **Priority**: Major

### Fix 3: Asserir a distinção por ícone entre as três categorias (RISCO-12)

- **Root cause**: `SuperficieEventoDecisao.test.tsx` assere presença de `<svg>` apenas no caso `relevante` e nunca compara os ícones entre categorias; a AC exige distinção por ícone.
- **Fix task**: adicionar `data-testid`/`aria-label` distinto por ícone em `SuperficieEventoDecisao.tsx:38-44` e asserir, nos três testes de categoria, que o identificador do ícone difere.
- **Priority**: Minor

### Fix 4: Levar os exemplos limítrofes para a documentação (RISCO-02)

- **Root cause**: `49.9 / 50.0 / 50.1` existe só como teste; nenhum artefato de documentação traz exemplos limítrofes, e não há declaração de que nenhuma fronteira exclusiva está configurada.
- **Fix task**: acrescentar em `adaptadores/persistencia/README.md` (ou no docstring do módulo) uma tabela de fronteira por limiar com os três exemplos e a nota "nenhum limiar exclusivo configurado nesta demonstração".
- **Priority**: Minor

### Fix 5: Remover a constante morta `LIMIAR_CHUVA_INTENSA_MM`

- **Root cause**: cópia não referenciada do default que vive em `semeador.py:190`; risco de divergência silenciosa.
- **Fix task**: remover `dominio/avaliador_risco.py:11-16`, movendo a justificativa para o README junto do Fix 4.
- **Priority**: Minor

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
| --- | --- | --- |
| RISCO-01 | Implementing | ✅ Verified |
| RISCO-02 | Implementing | ⚠️ Spec-precision gap |
| RISCO-03 | Implementing | ✅ Verified |
| RISCO-04 | Implementing | ✅ Verified |
| RISCO-05 | Implementing | ⚠️ Spec-precision gap |
| RISCO-06 | Implementing | ⚠️ Spec-precision gap |
| RISCO-07 | Implementing | ✅ Verified |
| RISCO-08 | Implementing | ✅ Verified |
| RISCO-09 | Implementing | ❌ Needs Fix |
| RISCO-10 | Implementing | ⚠️ Verified com teste fraco (M2) |
| RISCO-11 | Implementing | ✅ Verified |
| RISCO-12 | Implementing | ⚠️ Spec-precision gap |
| RISCO-13 | Implementing | ✅ Verified |

---

## Summary

**Overall**: ⚠️ Issues — não pronto para marcar concluído

**Spec-anchored check**: 8/13 ACs plenamente casados com o resultado definido pela spec; 4 spec-precision gaps; 1 GAP fundamentado (RISCO-09)
**Sensor**: 2/3 mutantes mortos (M2 sobreviveu)
**Gate**: 288 backend + 163 frontend passed, 0 failed, 0 skipped

**O que funciona**: o motor determinístico é genuinamente puro e a fronteira inclusiva de 50.0 mm está exercitada nos três pontos (49.9/50.0/50.1) e provada discriminante por M1. AD-5 é honrado de forma estrutural, não por convenção. O snapshot é imutável por construção (só `INSERT`/`SELECT`, `regra_versao` como valor). A rota HTTP faz round-trip real dos critérios do DuckDB até o corpo JSON. O caminho "sem regra ativa" pula a persistência de forma **deliberada e asserida** (`avaliacoes.salvas == []`), não por acidente. A adição de "área aplicável" ao granizo é exigida pela spec, não scope creep, e o teste de tipo não suportado é desenho legítimo.

**Problemas encontrados**: (1) o terminal `sem_risco` por falta de regra ativa não persiste código nem motivo, deixando uma execução decidida indistinguível de uma não avaliada na API e na tela — Fix 1; (2) a asserção de `regra_versao` no serviço não é discriminante porque a fixture vale `1` — Fix 2; (3) a distinção por ícone exigida por RISCO-12 não é asserida — Fix 3; (4) os exemplos limítrofes de RISCO-02 nunca chegaram à documentação — Fix 4; (5) constante de limiar morta e duplicada — Fix 5. Contexto adicional (não bloqueante, já declarado pelo autor): nem `ServicoAvaliacaoRisco` nem `SuperficieEventoDecisao` são alcançáveis em produção ainda.

**Next steps**: rotear Fix 1 e Fix 2 (Major) para um implementador; Fix 3–5 (Minor) podem acompanhar. Reverificar com foco em M2 e no caminho `sem_regra_ativa` após as correções.
