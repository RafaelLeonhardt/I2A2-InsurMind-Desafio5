# História 2.5: Selecionar e explicar o público elegível — Validation

**Date**: 2026-09-02
**Rodada**: **ROUND 1**
**Spec**: `.specs/features/2-5-selecionar-e-explicar-o-publico-elegivel/spec.md`
**Diff range**: `621d4ab..36aafd6` (6 commits — T1 `18a3547`, T2 `9853eee`, T3 `e6b4e5b`, T4 `7df1876`, T5 `e0338a6`, T6 `36aafd6`)
**Verifier**: sub-agente independente (author ≠ verifier) — read-only sobre a árvore real; mutações apenas em worktree descartável

**Verdict**: ❌ **FAIL**

**Resumo em uma frase**: o código de produção está correto e os gates estão todos verdes (373 backend / 202 frontend, `ruff`/`pyright`/`lint`/`build` limpos), mas **7 de 10 mutantes sobreviveram** — as asserções não guardam vários dos comportamentos que a própria spec define como resultado esperado (canal congelado, `apolice_id` na `UNIQUE`, coluna de área da apólice, contagem incluídos/excluídos, e três dos cinco itens exigidos pela ELEG-09). Há também **um defeito real de produção**: `obter_por_id` levanta `TypeError` (→ HTTP 500) ao ler qualquer linha semeada do conjunto demonstrativo.

---

## Task Completion

| Task | Status | Notes |
| --- | --- | --- |
| T1 — Migração `0006_elegibilidade.sql` | ✅ Done | Recreate-and-copy aplicado; backfill comprovado em `testes/test_migracoes.py:213-250` (`execucao_id IS NULL`, `criterios == '{"origem": "seed_demonstrativo"}'`, `canal == "sms"` vindo do JOIN, `justificativa` preservada). Renumeração `0005`→`0006` **verificada e correta**: `test_migracoes.py:81-92` assere a sequência exata `(1,2,3,4,5,6)` e os 6 rótulos registrados — nenhum número pulado nem duplicado. `README.md` de persistência atualizado com as 3 colunas novas, a `UNIQUE` e a estratégia de recreate |
| T2 — `AvaliadorElegibilidade` | ⚠️ **Partial** | Motor puro correto e determinístico; cada critério de exclusão testado isoladamente. **Mas** a ELEG-05 ("resultado de **cada** critério") não tem asserção: M9 (resultado excluído devolvendo só os critérios que falharam) **sobreviveu** |
| T3 — Repositórios de elegibilidade | ⚠️ **Partial** | Dedup por `UNIQUE` comprovado por round-trip real de banco (M10 morto). **Mas** três comportamentos ficaram sem guarda: coluna de área (M2), `apolice_id` na `UNIQUE` (M3) e `canal` congelado (M4) |
| T4 — `ServicoAvaliacaoElegibilidade` | ✅ Done | Orquestração correta; conjunto vazio válido; nenhuma porta de IA existe para ser chamada. Nota: a transição de estado da execução fica para 2.6 — **fora de escopo, não contado como lacuna** |
| T5 — Endpoint HTTP | ⚠️ **Partial** | Rotas corretas, `openapi.json` sincronizado, guarda de 404 por execução **real** (M5 morto). **Mas** existe um caminho de 500 não tratado (ver Fix 1) e a contagem incluídos/excluídos pode ser trocada sem teste vermelho (M7) |
| T6 — Superfície "Evento e decisão" | ⚠️ **Partial** | Quantidades, tabela, botão por teclado e distinção texto+ícone+cor implementados e (parcialmente) asseridos. **Mas** três dos cinco itens que a ELEG-09 enumera não têm asserção: regra+versão (M6), valor observado e resultado (M8) |

**Lacuna de integração declarada (não é defeito desta história)**: `SuperficieEventoDecisao` continua não montada em rota no `App.tsx` (`grep -rn "SuperficieEventoDecisao" src/frontend/src/App.tsx` → zero ocorrências). Mesmo padrão já aceito para as superfícies de 2.1/2.2/2.3/2.4, declarado pelo autor. Registrado, **não contado como lacuna**.

**Desvios documentados nas "Notas de implementação", avaliados um a um:**

| Desvio | Avaliação independente |
| --- | --- |
| Migração renumerada `0005` → `0006` | ✅ **Razoável e verificado**. `0005_avaliacao_risco_sem_regra.sql` já existia em `621d4ab` (commit anterior a esta história). A sequência final `(1,2,3,4,5,6)` está asserida em `test_migracoes.py:81,90` e `test_inicializador.py:73,99`; nenhum número pulado ou duplicado |
| `semeador.py` ganhou `criterios`/`canal` | ✅ **Necessário**. As colunas são `NOT NULL` e o semeador roda depois da migração. Contagens do semeador inalteradas (`test_inicializador.py:74-80`) |
| `RegraSnapshot` ganhou `cobertura_exigida` | ✅ **Razoável, sem quebra silenciosa**. Os 5 pontos de construção foram atualizados: `repositorio_regras.py:78,90`, `aplicacao/gestao_regras.py:161`, `testes/test_avaliador_risco.py`, `testes/test_avaliacao_risco.py`, `testes/test_avaliador_elegibilidade.py`. Todas as construções usam argumentos nomeados, então a inserção do campo **antes** de `versao` não desloca nenhum posicional; `pyright` (0 erros) confirma. `avaliar()` de 2.3 não lê o campo novo — o significado dos testes de 2.3/2.4 não mudou (os 373 testes passam, incluindo os 292 pré-2.4) |
| `CandidatoElegibilidade` plano em vez de `Segurado` + `ApoliceSnapshot` | ✅ **Razoável**. Confirmado que `dominio/segurado.py::Segurado` (id, nome) é consumido por `aplicacao/contexto.py` para o seletor de perfil — propósito não relacionado. Estendê-lo acoplaria dois consumidores distintos; a spec trata "segurado+apólice" como combinação inseparável |
| `salvar` recebe `segurado_id`/`apolice_id` fora do `resultado` | ✅ **Razoável**. Mesmo padrão de `RepositorioAvaliacoesRisco.salvar` (2.3) |
| `serializacao_criterios.py` extraída e compartilhada com 2.3 | ✅ **Refactor sem mudança de comportamento**. Código movido literalmente (`git diff` mostra remoção + import, corpo idêntico); os testes de 2.3 (`test_repositorio_avaliacoes_risco.py`) continuam verdes |
| `nome_segurado`/`codigo_ibge_area`/`regra_versao` por `JOIN` na leitura | ⚠️ **Parcialmente problemático** — ver ELEG-06 abaixo. `regra_versao` é seguro (linhas de `regras` são imutáveis por versão), mas `s.nome` e `a.codigo_ibge_area` são **dados vivos** exibidos dentro de uma explicação que a spec exige imutável |

---

## Spec-Anchored Acceptance Criteria

Mapeamento ID→AC pela ordem da `spec.md` (o `design.md` não referencia nenhum `ELEG-NN`): ELEG-01..03 = as 3 ACs da 1ª story P1; ELEG-04..07 = as 4 ACs da 2ª story P1; ELEG-08..10 = as 3 ACs da story P2.

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + asserção | Result |
| --- | --- | --- | --- |
| **ELEG-01** — avaliar considerando **somente** segurados e apólices sintéticos do conjunto demonstrativo | Candidatos vêm exclusivamente de `segurados`/`apolices` semeados; nenhuma outra fonte | `repositorio_elegibilidade.py:66-73` — único `SELECT`, sobre `apolices JOIN segurados`, sem nenhuma fonte externa. Testes: `test_repositorio_elegibilidade.py:109-117` — `len(candidatos) == 1`, `str(candidato.segurado_id) == id_segurado`, `apolice_tipo == "residencial"`, `apolice_situacao == "ativa"`, `coberturas == ("alagamento",)`; `:127` — `candidatos == []` para apólice de outra área | ⚠️ **Partial** — a **coluna** de área não está pinada: **M2 sobreviveu** (trocar `a.codigo_ibge_area` por `s.codigo_ibge_area` no `WHERE` deixa 373 testes verdes). "Somente sintéticos" é garantia estrutural (as tabelas só recebem seed), sem teste próprio |
| **ELEG-02** — avaliar área, tipo e situação da apólice, coberturas e participação em alertas | Exatamente esses 5 critérios, cada um capaz de excluir sozinho | `avaliador_elegibilidade.py:149-155` — a tupla dos 5. Testes: `test_avaliador_elegibilidade.py:66` — `len(resultado.criterios) == 5`; exclusão isolada de cada um: `:75` (`MOTIVO_AREA_NAO_APLICAVEL`), `:86` (`MOTIVO_APOLICE_INCOERENTE`), `:95`/`:105` (`MOTIVO_APOLICE_INATIVA`, cancelada e suspensa), `:114` (`MOTIVO_COBERTURA_AUSENTE`), `:128` (`MOTIVO_NAO_PARTICIPA_DE_ALERTAS`). **M1 morto** | ✅ **PASS** |
| **ELEG-03** — canal preferencial preservado para a comunicação futura, **sem alterar** o resultado dos demais critérios | Mesma decisão com canais diferentes; `canal` do resultado igual ao do candidato | `test_avaliador_elegibilidade.py:139` — `resultado_whatsapp.elegivel == resultado_email.elegivel == True`; `:140-141` — `canal == "whatsapp"` / `== "email"`; `:149` — `canal == "sms"`. **Independent Test da spec** literal em `:117-129`: `participa_de_alertas=False` + `canal_preferido="sms"` → `elegivel is False`, `motivo == MOTIVO_NAO_PARTICIPA_DE_ALERTAS`, `canal == "sms"`. Código: `avaliador_elegibilidade.py:168` — `canal` só é copiado, nunca comparado | ✅ **PASS** (no domínio; o congelamento na persistência é ELEG-06, e lá há lacuna) |
| **ELEG-04** — segurado+apólice que atendem integralmente → resultado `incluido` **associado à execução, evento, versão da regra, segurado e apólice**, com **todos** os critérios satisfeitos | Linha `elegivel = true` ligada às 5 chaves, com os 5 critérios `atende = true` | Domínio: `test_avaliador_elegibilidade.py:63-66` — `elegivel is True`, `motivo == MOTIVO_INCLUIDO`, `all(c.atende ...)`, `len(criterios) == 5`. Serviço: `test_avaliacao_elegibilidade.py:162-167` — `execucao_salva == execucao_id`, `evento_salvo == EVENTO_CHUVA.id`, `regra_salva == REGRA_CHUVA.id`, `segurado_salvo`/`apolice_salva` do candidato, `resultado.elegivel is True`. Persistência (round-trip real de DuckDB): `test_repositorio_elegibilidade.py:162-168` — `registro.execucao_id == execucao_id`, `elegivel is True`, `canal == "whatsapp"`, `criterios == RESULTADO_INCLUIDO.criterios`, `nome_segurado == "Pessoa Teste"`, `codigo_ibge_area == AREA`, **`regra_versao == 1`**. HTTP: `test_elegibilidade_api.py:203-208` — `regra_id`, **`regra_versao == 3`**, `elegivel is True` | ✅ **PASS** |
| **ELEG-05** — ao menos um critério não atendido → resultado `excluido` **com o resultado de cada critério**, identificando objetivamente o que impediu | Resultado excluído carrega **os 5** critérios (satisfeitos e não satisfeitos) + motivo/justificativa específicos | Motivo e justificativa: `test_avaliador_elegibilidade.py:74-77` (`elegivel is False`, `MOTIVO_AREA_NAO_APLICAVEL`, `criterio_area.atende is False`), `:96` (`"cancelada" in resultado.justificativa`), `:114`, `:128`. **Nenhum teste assere que um resultado excluído conserva os critérios satisfeitos** — `len(criterios) == 5` só existe no caso incluído (`:66`) | ❌ **GAP** — **M9 sobreviveu**: fazer o resultado excluído devolver apenas os critérios que falharam deixa os 373 testes verdes. A metade "com o resultado de **cada** critério" da AC não tem evidência |
| **ELEG-06** — dados originais alterados **depois** de uma execução concluída → snapshots imutáveis conservados, **sem que a explicação histórica seja reescrita** | Reler o registro após `UPDATE` em `segurados`/`apolices`/`regras` devolve exatamente os valores do momento da avaliação | **Sem evidência.** `grep -rn "UPDATE segurados\|UPDATE apolices" src/backend/testes/` não encontra nenhum teste desta história que altere o dado original e releia o registro (só `test_semeador.py:139` e `test_dados_sinteticos_api.py:51`, de outras histórias). A migração congela `criterios` e `canal` em colunas próprias (`0006_elegibilidade.sql:23-24`), e o `README.md` de persistência promete "nunca referência viva a `segurados.canal_preferido`" — promessa **não guardada por teste** | ❌ **GAP (duplo)** — (a) **teste**: **M4 sobreviveu** (ler `s.canal_preferido` no lugar de `e.canal` deixa tudo verde); o Success Criterion da spec "alterar o canal preferencial depois da execução não altera o resultado histórico" não tem nenhum teste. (b) **produção**: `_SELECT_REGISTRO_ENRIQUECIDO` (`repositorio_elegibilidade.py:175-183`) lê `s.nome` e `a.codigo_ibge_area` **vivos**; editar o nome do segurado ou a área da apólice **reescreve** a explicação histórica exibida, e `codigo_ibge_area` pode passar a contradizer o `valor_observado` congelado do critério "área afetada" no mesmo payload |
| **ELEG-07** — mesma combinação (execução, evento, versão de regra, segurado, apólice) reprocessada/retomada → **no máximo um** resultado, sem originar mensagem duplicada | Exatamente 1 linha por combinação; 2ª tentativa é no-op, não erro | **Round-trip real de banco** (não mock): `test_repositorio_elegibilidade.py:182-191` — `primeiro is not None`, **`segundo is None`**, `len(repo.listar_por_execucao(execucao_id)) == 1`. Nível SQL: `test_migracoes.py:290-311` — dois `INSERT ... ON CONFLICT DO NOTHING` da mesma combinação → `total_reais[0] == 1`; e `:280-286` — duas linhas semeadas `execucao_id IS NULL` idênticas coexistem (`total_nulas[0] == 2`). Serviço: `test_avaliacao_elegibilidade.py:178-180` — reprocessar a mesma execução gera 2 chamadas mas **`len(combinacoes) == 1`**. **M10 morto** (remover `ON CONFLICT DO NOTHING` → `ConstraintException` real do DuckDB, provando que a `UNIQUE` existe e é exercitada de verdade) | ⚠️ **Partial** — a garantia principal está comprovada, mas o componente `apolice_id` da `UNIQUE` **não está guardado**: **M3 sobreviveu** (remover `apolice_id` da restrição deixa tudo verde), e com ele o Edge Case da spec "dois resultados distintos para duas apólices do mesmo segurado" passaria a **perder silenciosamente** a segunda linha |
| **ELEG-08** — a interface exibe quantidades de incluídos/excluídos e tabela com segurado, apólice, localização, canal e resultado, permitindo abrir critérios e justificativa **sem depender de hover** | As duas quantidades corretas e distinguíveis; as 5 colunas; abertura por teclado | Backend: `test_elegibilidade_api.py:166-172` — `incluidos == 1`, `excluidos == 1`, `len(registros) == 2`, `nomes == {"Maria Sintética","João Sintético"}`, `canais == {"whatsapp","sms"}`. Frontend: `SuperficieEventoDecisao.test.tsx:280-285` — `Maria Sintética`, `João Sintético`, `whatsapp`, `sms`, `Incluído`, `Excluído` dentro da `table` nomeada; `:316-327` — `botaoVerCriterios.focus()` + `toHaveFocus()` + `keyboard('{Enter}')` abre a explicação e `getDetalheElegibilidade` é chamado com `(EXECUCAO_ID, '4444…')` (sem hover em nenhum ponto) | ⚠️ **Partial** — a asserção de **quantidades** (`:258` — `getAllByText('1')).toHaveLength(2)`) não distingue incluídos de excluídos, e as duas fixtures backend usam `1`/`1`: **M7 sobreviveu** (trocar os dois `count(*) FILTER` entre si deixa tudo verde). O conjunto de cabeçalhos da tabela também não é asserido (2.4 usava `toEqual([...])` para isso, lição já estabelecida) |
| **ELEG-09** — a explicação exibe **regra e versão, operando, valor observado, resultado e justificativa** em colunas estáveis, distinguindo inclusões e exclusões por **texto, ícone e cor** | Os 5 campos visíveis em colunas fixas + os 3 sinais de distinção | **Texto+ícone+cor** ✅: `SuperficieEventoDecisao.test.tsx:298-303` — `toHaveClass('resultado-elegibilidade-badge--incluido')` / `'--excluido'` **e** `svg[data-icone-nome="check-circle"]` / `"x-circle"` **e** o texto `Incluído`/`Excluído` (`:284-285`). **Operando** ✅: `:322` — `getByText('área afetada')`. **Justificativa** ✅: `:323-325`. **Regra e versão** ❌: renderizado em `SuperficieEventoDecisao.tsx:330` mas a asserção `:321` usa `/Explicação — Maria Sintética/`, que **não** cobre `(regra v3)`. **Valor observado** e **Resultado** ❌: renderizados em `:349-350`, sem nenhuma asserção. **Colunas estáveis** ❌: os cabeçalhos `:339-342` não são asseridos | ❌ **GAP** — **M6 sobreviveu** (remover `(regra v{regraVersao})` do título) e **M8 sobreviveu** (apagar as colunas `Valor observado` e `Resultado` inteiras). 3 dos 5 itens enumerados pela AC não têm evidência de teste na superfície (o backend cobre `regra_versao` em `test_elegibilidade_api.py:204` e o cliente HTTP em `elegibilidade.test.ts:137,139` — mas a AC é sobre a **interface**) |
| **ELEG-10** — nenhum registro satisfaz a regra → conjunto vazio **válido**, não falha técnica, **sem chamada à OpenAI e sem criar mensagem** | `200`/contagem zero/lista vazia; zero chamadas de IA; nenhuma mensagem | Serviço: `test_avaliacao_elegibilidade.py:132-134` — `contagem.incluidos == 0`, `contagem.excluidos == 0`, `elegibilidades.chamadas == []`. HTTP: `test_elegibilidade_api.py:131-135` — `status_code == 200`, `incluidos == 0`, `excluidos == 0`, `registros == []`. Repositório: `test_repositorio_elegibilidade.py:233` — `listar_por_execucao(uuid4()) == []`. Frontend: `SuperficieEventoDecisao.test.tsx:269-270` — `'Nenhum segurado avaliado até o momento.'` **e** `queryByRole('alert')` ausente (vazio ≠ erro). Sem IA: garantia **estrutural** — `PortasAvaliacaoElegibilidade` (`avaliacao_elegibilidade.py:54-62`) não tem porta de IA, e `grep -rn "openai" ` nos 4 módulos desta história devolve zero | ✅ **PASS** (nota A — o caso literal da AC, "candidatos existem mas **nenhum** satisfaz a regra", não é testado: o teste de conjunto vazio usa **zero candidatos**) |

**Status**: ❌ **Gaps presentes** — **4 PASS**, **3 Partial**, **3 GAP** de 10 ACs.

**Spec-precision gaps**: nenhum. A `spec.md` 2.5 define resultado preciso para as 10 ACs; todas as lacunas são de **evidência de teste** (e uma de produção), não de imprecisão da spec.

---

## Discrimination Sensor

Duas worktrees isoladas e descartáveis (`git worktree add --detach <scratch> 36aafd6`), revertidas com `git checkout -- .` entre mutações e removidas com `git worktree remove --force` + `git worktree prune`. O `node_modules` do frontend foi apenas **symlinkado** para dentro da worktree e o link removido antes da remoção. Nenhum `git stash` usado. **Baseline nas worktrees antes de mutar**: 373 testes backend verdes; 15/15 em `SuperficieEventoDecisao.test.tsx`.

| # | Mutação | File:line | Descrição | Testes executados | Killed? |
| --- | --- | --- | --- | --- | --- |
| **M1** | Critério de alertas sempre atende | `dominio/avaliador_elegibilidade.py:110` | `atende = candidato.participa_de_alertas` → `atende = True` | `testes/` (373) | ✅ **Killed** — `test_sem_nenhuma_participacao_de_alertas_exclui_independente_do_canal` falha em `:127` |
| **M2** | Área lida do segurado, não da apólice | `adaptadores/persistencia/repositorio_elegibilidade.py:71` | `WHERE a.codigo_ibge_area = ?` → `WHERE s.codigo_ibge_area = ?` | `testes/` (373) | ❌ **Survived** — 373 passed. Todas as fixtures dão o mesmo código IBGE ao segurado e à apólice, então a semântica "área **da apólice**" (ELEG-01/02) não é medida |
| **M3** | `apolice_id` fora da `UNIQUE` | `migracoes/0006_elegibilidade.sql:27` | `UNIQUE (execucao_id, evento_id, regra_id, segurado_id, apolice_id)` → `UNIQUE (execucao_id, evento_id, regra_id, segurado_id)` | `testes/` (373) | ❌ **Survived** — 373 passed. Com esta mutação, o Edge Case "duas apólices do mesmo segurado, uma elegível e outra não" perderia a 2ª linha silenciosamente (`ON CONFLICT DO NOTHING`), sem nenhum teste vermelho |
| **M4** | Canal lido vivo em vez de congelado | `repositorio_elegibilidade.py:177` | `e.canal` → `s.canal_preferido` no `_SELECT_REGISTRO_ENRIQUECIDO` | `testes/` (373) | ❌ **Survived** — 373 passed. O snapshot de canal (AD-11, ELEG-03/06, Success Criterion #3) não tem nenhuma guarda |
| **M5** | Guarda de execução no detalhe HTTP | `adaptadores/http/elegibilidade.py:237` | `if registro is None or registro.execucao_id != execucao_uuid:` → `if registro is None:` | `testes/` (373) | ✅ **Killed** — `test_get_registro_elegibilidade_de_outra_execucao_retorna_404` falha em `:238`. **A checagem de 404 por execução é real, não decorativa** |
| **M6** | Regra+versão fora da explicação | `SuperficieEventoDecisao.tsx:330` | `Explicação — {nomeSegurado} (regra v{regraVersao})` → `Explicação — {nomeSegurado}` | `SuperficieEventoDecisao.test.tsx` (15) | ❌ **Survived** — 15 passed. A asserção `:321` usa um regex que para antes da versão |
| **M7** | Contagens trocadas | `repositorio_elegibilidade.py:144` | `count(*) FILTER (WHERE elegivel), count(*) FILTER (WHERE NOT elegivel)` → os dois invertidos | `testes/` (373) | ❌ **Survived** — 373 passed. Todas as fixtures usam `1` incluído e `1` excluído, tornando a troca invisível |
| **M8** | Duas colunas da explicação apagadas | `SuperficieEventoDecisao.tsx:349-350` | remoção de `<td>{criterio.valorObservado}</td>` e `<td>{criterio.atende ? 'Atende' : 'Não atende'}</td>` | `SuperficieEventoDecisao.test.tsx` (15) | ❌ **Survived** — 15 passed. Dois dos cinco itens exigidos pela ELEG-09 podem sumir da tela sem teste vermelho |
| **M9** | Resultado excluído perde os critérios satisfeitos | `dominio/avaliador_elegibilidade.py:167` | `criterios=criterios` → `criterios=criterios if elegivel else tuple(c for c in criterios if not c.atende)` | `testes/` (373) | ❌ **Survived** — 373 passed. A ELEG-05 exige "o resultado de **cada** critério" |
| **M10** | Dedup removida do `INSERT` | `repositorio_elegibilidade.py:121` | `"ON CONFLICT DO NOTHING RETURNING id"` → `"RETURNING id"` | `testes/` (373) | ✅ **Killed** — `test_salvar_chamado_duas_vezes_para_a_mesma_combinacao_nao_duplica` falha com `_duckdb.ConstraintException: Duplicate key "execucao_id: …, apolice_id: …" violates unique constraint`. **Prova que a dedup da ELEG-04/07 passa por um round-trip real de banco, não por mock** |

**Sensor depth**: **P0-full** (integridade de dados — 10 mutações manuais, ≥5 exigidas pelo protocolo)
**Result**: **3/10 killed, 7 survived** — ❌ **FAIL**

**Verificação de isolamento**: `git status --porcelain` vazio **antes** (`BASELINE:[]`) e **depois** (`POST-SENSOR STATUS:[]`) do ciclo; `git worktree list` mostra apenas a árvore real em `36aafd6`; os dois diretórios de scratch não existem mais; `src/frontend/node_modules` da árvore real continua diretório real (não symlink). Nenhum arquivo do projeto foi modificado por esta rodada exceto este `validation.md`.

---

## Payload / Conjunction Rule

Regra aplicada: a asserção precisa olhar **valor devolvido e/ou estado persistido**, não "a chamada aconteceu" nem um status isolado.

| Alvo | Asserção verifica valor real? | Evidência |
| --- | --- | --- |
| `GET .../elegibilidade` 200 vazio | ✅ Sim | `test_elegibilidade_api.py:131-135` — status **+** `incluidos == 0`, `excluidos == 0`, `registros == []` (lista vazia explícita, não erro) |
| `GET .../elegibilidade` 200 preenchido | ⚠️ **Parcial** | `:164-172` — status **+** `len == 2` **+** `nomes` **+** `canais` asseridos. Mas `incluidos == 1` / `excluidos == 1` são **simétricos**: M7 prova que a asserção não distingue os dois contadores |
| `GET .../elegibilidade` 422 | ✅ Sim | `:180-182` — status **+** `content-type: application/problem+json` **+** `codigo == "execucao_id_invalido"` |
| `GET .../elegibilidade/{id}` 200 | ✅ Sim | `:200-209` — status **+** `id`, `regra_id`, `regra_versao == 3`, `elegivel is True`, `len(criterios) == 1`, `criterios[0].operando`, `criterios[0].atende is True`, `justificativa.startswith(...)` |
| `GET .../elegibilidade/{id}` 404 inexistente | ✅ Sim | `:220-221` — status **+** `codigo == "resultado_elegibilidade_inexistente"` |
| `GET .../elegibilidade/{id}` 404 de outra execução | ⚠️ **Parcial** | `:238` — **só** `status_code == 404`, sem `codigo`. A guarda é comprovadamente viva (M5 morto), mas a asserção é mais fraca que a irmã de `:221` |
| `GET .../elegibilidade/{id}` 422 | ✅ Sim | `:248-249` — status **+** `codigo == "identificador_invalido"` |
| `RepositorioElegibilidades.salvar` | ✅ Sim | `test_repositorio_elegibilidade.py:159-168` — id devolvido **e releitura real do banco** com 7 asserções de valor, incluindo a tupla de critérios |
| `RepositorioElegibilidades.salvar` (dedup) | ✅ Sim | `:189-191` — `primeiro is not None` **e** `segundo is None` **e** o estado persistido relido (`len(listar_por_execucao) == 1`) |
| `contar_por_execucao` | ⚠️ **Parcial** | `:226-227` — valores reais (`1`/`1`), mas simétricos (M7) |
| `listar_candidatos` | ✅ Sim | `:109-117` — identidade dos ids **e** 5 campos de valor, não só contagem |
| Migração `0006` (backfill) | ✅ Sim | `test_migracoes.py:247-250` — os 4 valores da linha semeada relidos do banco |
| Migração `0006` (`UNIQUE`) | ✅ Sim | `:286` e `:311` — contagens reais após inserções concorrentes (`2` nulas coexistem, `1` real após duas tentativas) |
| `ServicoAvaliacaoElegibilidade` — efeito | ✅ Sim | `test_avaliacao_elegibilidade.py:162-167` — a **tupla inteira** passada a `salvar` (execução, evento, regra, segurado, apólice) e `resultado.elegivel`, não só a contagem de chamadas; `:134` — `chamadas == []` prova **ausência** de escrita |
| Cliente HTTP frontend | ✅ Sim | `elegibilidade.test.ts:52,74` — `toEqual` do objeto inteiro; `:137-139` — `regraVersao === 3` **e** `criterios` completos; `:90,99,166` — `codigo` específico por causa |
| Superfície — tabela | ✅ Sim | `SuperficieEventoDecisao.test.tsx:280-285` — 6 valores de célula reais |
| Superfície — distinção | ✅ Sim | `:298-303` — classe modificadora **de cada estado** **e** ícone **de cada estado** **e** o texto (os 3 sinais, conforme a lição L-024 de 2.4) |
| Superfície — quantidades | ❌ **Não** | `:258` — `getAllByText('1')).toHaveLength(2)`: conta ocorrências do dígito, não liga cada quantidade ao seu rótulo. Nem `incluidos` nem `excluidos` é asserido individualmente |
| Superfície — explicação | ⚠️ **Parcial** | `:321-327` — nome do segurado, operando, justificativa e o argumento da chamada. **Faltam** versão da regra, valor observado e resultado (M6, M8) |

---

## Code Quality

| Princípio | Status |
| --- | --- |
| Minimum code | ✅ — nenhuma abstração especulativa; `serializacao_criterios.py` só foi extraída porque há **dois** consumidores reais |
| Surgical changes | ✅ — 31 arquivos, todos rastreáveis a T1–T6; as edições em código de 2.3/2.4 são o mínimo exigido pelo campo novo de `RegraSnapshot` |
| No scope creep | ✅ — nenhuma transição de estado de execução (corretamente deixada para 2.6), nenhuma geração de mensagem, nenhuma rota extra (`test_saude.py:46-47` fixa o conjunto **exato** de caminhos sob `/api/v1`) |
| Matches patterns | ✅ — roteador, `problem+json` correlacionado, `422` explícito em vez do `HTTPValidationError` genérico, `data-icone-nome`, cliente `openapi-fetch` tipado: tudo igual a 2.3/2.4 |
| Spec-anchored outcome check | ❌ — **6/10** ACs com asserção casando o resultado da spec; ELEG-05, ELEG-06 e ELEG-09 sem evidência para parte do resultado definido |
| Per-layer Coverage Expectation | ⚠️ — domínio quase 1:1 (falta a ELEG-05 "cada critério"); rota cobre feliz + vazio + 404 (×2 causas) + 422 (×2 causas) ✅; componente cobre carregando/vazio/erro/tabela/teclado ✅, mas não os 5 campos da ELEG-09 |
| Every test maps to a spec requirement | ✅ — nenhum teste órfão; os 33 testes backend e 13 frontend novos mapeiam a ACs, Edge Cases ou "Done when" |
| Documented guidelines followed | ✅ — `AGENTS.md` e o `README.md` de persistência atualizado com colunas, `UNIQUE` e estratégia de recreate (fecha a lição **L-022** de 2.4, que 2.4 deixou aberta) |
| Docstring/contrato correspondem ao comportamento | ⚠️ — o `README.md` de persistência afirma que `canal` é "nunca referência viva a `segurados.canal_preferido`": **verdade hoje**, mas M4 mostra que nenhum teste sustenta a promessa. E o docstring de `RegistroElegibilidade` (`repositorio_elegibilidade.py:30-33`) justifica o JOIN vivo "para evitar duas fontes de verdade" — o efeito colateral é que a explicação histórica **pode** ser reescrita (ELEG-06) |

---

## Edge Cases

- [ ] **Segurado com mais de uma apólice na área afetada, uma elegível e outra não → um resultado distinto por combinação** — parcialmente coberto e **não guardado**. A listagem devolve as duas combinações (`test_repositorio_elegibilidade.py:142-144` — `len(candidatos) == 2`, `situacoes == {"ativa","cancelada"}`) e o domínio decide cada uma corretamente, mas **nenhum teste persiste as duas linhas e conta 2**: **M3 sobreviveu**, então remover `apolice_id` da `UNIQUE` (que faria a 2ª linha desaparecer) não produz nenhum teste vermelho
- [x] **Área do evento cobre parcialmente a área de risco da apólice → mesmo critério objetivo, sem inferência probabilística** — o critério é igualdade exata de código IBGE (`avaliador_elegibilidade.py:49`), sem faixa, sem probabilidade; `test_avaliador_elegibilidade.py:70-77` cobre o não-casamento. Determinismo asserido em `:152-156` (`primeira == segunda`)
- [x] **Retomada após reinicialização do backend no meio do processamento → continua do progresso persistido, sem recriar resultados já gravados** — **comprovado com banco real**: `test_repositorio_elegibilidade.py:182-191` (2º `salvar` da mesma combinação devolve `None`, 1 linha ao final, **sem exceção**) e `test_avaliacao_elegibilidade.py:175-180` (chamar `avaliar_publico` duas vezes na mesma execução → `len(combinacoes) == 1`). M10 confirma que a garantia é da `UNIQUE` do banco, não de lógica em memória. Re-executar é idempotente e não levanta erro
- [x] **Conjunto vazio válido** — `test_avaliacao_elegibilidade.py:132-134`, `test_elegibilidade_api.py:131-135`, `SuperficieEventoDecisao.test.tsx:269-270` (nota A: o caso "candidatos existem, nenhum satisfaz" não é testado isoladamente)
- [ ] **Linha semeada consultada pelo detalhe HTTP** — **não tratado, defeito de produção** (ver Fix 1)

---

## Gate Check

- **Gate command (Build)**: `uv run pytest -q && uv run ruff check . && uv run pyright` (em `src/backend`) + `npx vitest run && npm run lint && npm run build` (em `src/frontend`)
- **Executado nesta rodada pelo próprio Verificador** (não herdado do orquestrador), na árvore real em `36aafd6`:
  - `pytest`: **373 passed**, 0 failed, 0 skipped (exit 0, 20.35s)
  - `ruff check .`: **All checks passed!** (exit 0)
  - `pyright`: **0 errors, 0 warnings, 0 informations** (exit 0)
  - `vitest run`: **202 passed** em 23 arquivos, 0 failed (exit 0, 7.13s)
  - `npm run lint` (`oxlint`): exit 0 — **11 warnings**, todas pré-existentes de `react(set-state-in-effect)` / `react(only-export-components)`; a nova (`SuperficieEventoDecisao.tsx:129`, o `useEffect` de elegibilidade) segue exatamente o padrão já aceito em `:107`, `SuperficieRegras.tsx:89`, `SuperficieProntidao.tsx:84` e `SuperficieFonteMeteorologica.tsx:149`
  - `npm run build`: **✓ built in 228ms** (exit 0)
- **Test count antes da feature** (fim de 2.4, `621d4ab`): 340 backend / 189 frontend
- **Test count depois da feature** (`36aafd6`): **373 backend / 202 frontend**
- **Delta**: **+33 backend / +13 frontend** (+46 no total)
- **Test Integrity**: ✅ nenhum teste removido; nenhuma asserção enfraquecida. Duas edições em testes pré-existentes, ambas justificadas: `test_migracoes.py`/`test_inicializador.py` passaram de `(1,2,3,4,5)` para `(1,2,3,4,5,6)` (a migração nova), e `SuperficieEventoDecisao.test.tsx:127` trocou `getByRole('status')` por `getByText('Carregando decisão de risco…')` — **necessária**, porque a seção nova acrescentou um segundo `role="status"` na tela ("Carregando público elegível…") e `getByRole` passaria a falhar por ambiguidade. A asserção continua verificando o mesmo texto, mas **perdeu** a garantia do papel ARIA (item Minor, nota C)
- **Skipped**: nenhum
- **Failures**: nenhuma

---

## Fix Plans

### Fix 1 (**Blocker**) — `obter_por_id` quebra em qualquer linha semeada do conjunto demonstrativo

- **Root cause**: a migração `0006` faz backfill de `criterios` com o **objeto** `'{"origem": "seed_demonstrativo"}'` (`0006_elegibilidade.sql:39`; idem `semeador.py:269,280,291,302`), mas `desserializar_criterios` (`serializacao_criterios.py:31-39`) espera uma **lista** de objetos. Ler uma dessas linhas itera sobre as chaves do dicionário e levanta `TypeError: string indices must be integers, not 'str'`.
- **Reprodução independente** (executada nesta rodada, em worktree descartável, contra o banco real semeado por `SemeadorDadosSinteticos`): `linhas semeadas: 4` → `criterios: {"origem": "seed_demonstrativo"}` → `obter_por_id RAISED: TypeError string indices must be integers, not 'str'`.
- **Impacto**: `GET /api/v1/execucoes/{qualquer-uuid}/elegibilidade/{id-de-linha-semeada}` devolve **500** em vez do **404** que a rota pretende (a comparação `registro.execucao_id != execucao_uuid` em `http/elegibilidade.py:237` nunca é alcançada, porque a exceção acontece antes, dentro do repositório). Nenhum dos 373 testes cobre o caminho, porque nenhum teste combina o semeador com este repositório.
- **Fix task** — *What*: fazer as linhas semeadas usarem o mesmo formato de lista, **ou** tornar `desserializar_criterios` tolerante a um payload que não seja lista de critérios (devolvendo `()`); preferir a primeira opção (um único formato). *Where*: `migracoes/0006_elegibilidade.sql:39` e `semeador.py:269,280,291,302` (p.ex. `'[]'`, como o próprio teste `test_repositorio_elegibilidade.py:259` já usa), ou `serializacao_criterios.py:28-39`. *Verify*: um teste que semeia o conjunto demonstrativo e chama `obter_por_id` (e a rota de detalhe) sobre uma linha semeada, asserindo **404** com `codigo == "resultado_elegibilidade_inexistente"` — nunca 500. *Done when*: o teste novo passa e a mutação "voltar o backfill para o objeto" o mata.
- **Priority**: **Blocker** (500 não tratado em caminho alcançável, sobre dados que o próprio sistema semeia)

### Fix 2 (**Major**) — ELEG-06: canal congelado e snapshot imutável sem nenhuma guarda (M4)

- **Root cause**: nenhum teste altera o dado original depois da execução e relê o registro. A promessa do `README.md` ("nunca referência viva a `segurados.canal_preferido`") não é executável.
- **Fix task** — *What*: teste de integração que (1) salva um resultado com `canal = 'whatsapp'`, (2) `UPDATE segurados SET canal_preferido = 'sms'` e `UPDATE apolices SET codigo_ibge_area = ...`, (3) relê por `obter_por_id`/`listar_por_execucao` e assere `registro.canal == 'whatsapp'` **e** que `criterios` continua idêntico. *Where*: `testes/test_repositorio_elegibilidade.py`. *Verify*: reinjetar M4 (`e.canal` → `s.canal_preferido`) e confirmar que o teste novo fica vermelho. *Done when*: M4 morto.
- **Priority**: **Major** (é o Success Criterion #3 literal da spec)

### Fix 3 (**Major**) — ELEG-06: `nome_segurado` e `codigo_ibge_area` são lidos vivos dentro de uma explicação que a spec exige imutável

- **Root cause**: `_SELECT_REGISTRO_ENRIQUECIDO` (`repositorio_elegibilidade.py:175-183`) faz `JOIN` em `segurados`/`apolices` na leitura. `regra_versao` é seguro (versões de regra são imutáveis, cada versão é uma linha nova — 2.4). `s.nome` e `a.codigo_ibge_area` **não** são: editar o segurado ou a apólice depois reescreve a explicação histórica exibida, e o `codigo_ibge_area` devolvido pode passar a **contradizer** o `valor_observado` congelado do critério "área afetada" dentro do mesmo payload.
- **Fix task** — *What*: decidir e registrar (STATE.md) entre (a) congelar `nome_segurado`/`codigo_ibge_area` em colunas próprias na próxima migração e (b) derivar `codigo_ibge_area` do critério já congelado, mantendo o JOIN só para `nome_segurado` (dado de exibição, não de decisão) e documentando isso na spec. *Where*: `repositorio_elegibilidade.py:175-183` (+ migração, se (a)). *Verify*: teste que altera `apolices.codigo_ibge_area` após a execução e assere que o detalhe devolvido continua coerente com `criterios[área].valor_observado`. *Done when*: nenhum campo de decisão do payload histórico muda após edição do dado original.
- **Priority**: **Major** (AD-11 / ELEG-06 é a garantia de auditabilidade da história)

### Fix 4 (**Major**) — Edge Case das duas apólices: `apolice_id` na `UNIQUE` sem guarda (M3)

- **Root cause**: nenhum teste persiste duas combinações que diferem **apenas** por `apolice_id`.
- **Fix task** — *What*: teste de integração que salva dois resultados na mesma execução/evento/regra/segurado com `apolice_id` diferentes (um `elegivel=True`, outro `False`) e assere `len(listar_por_execucao(...)) == 2` e `contar_por_execucao(...) == (1, 1)` com os dois `apolice_id` distintos presentes. *Where*: `testes/test_repositorio_elegibilidade.py`. *Verify*: reinjetar M3 e confirmar vermelho. *Done when*: M3 morto.
- **Priority**: **Major** (Edge Case explícito da spec; a falha seria perda silenciosa de dados)

### Fix 5 (**Major**) — ELEG-09: regra+versão, valor observado e resultado sem asserção na superfície (M6, M8)

- **Root cause**: a asserção `:321` usa um regex que para antes da versão; as colunas `Valor observado` e `Resultado` da tabela de critérios não são tocadas por nenhuma asserção.
- **Fix task** — *What*: no teste `abre a explicação de uma linha por teclado…` (ou num teste irmão), asserir o conjunto **exato** de cabeçalhos da tabela de critérios (`toEqual(['Operando','Valor observado','Resultado','Justificativa'])`, padrão de `SuperficieRegras.test.tsx:118-130`), o texto `regra v3` no título e as células `9990001` e `Atende`. *Where*: `src/frontend/src/funcionalidades/evento-decisao/SuperficieEventoDecisao.test.tsx`. *Verify*: reinjetar M6 e M8. *Done when*: M6 e M8 mortos.
- **Priority**: **Major** (a lição **L-024** de 2.4 — "quando a AC enumera N itens, asserir os N" — reincidiu aqui)

### Fix 6 (**Major**) — ELEG-05: resultado excluído não prova que carrega **cada** critério (M9)

- **Fix task** — *What*: acrescentar `assert len(resultado.criterios) == 5` e `assert [c.atende for c in resultado.criterios] == [True, True, False, True, True]` (ou equivalente) a pelo menos um teste de exclusão. *Where*: `testes/test_avaliador_elegibilidade.py:89-96` (apólice cancelada é o caso mais legível: 4 satisfeitos + 1 falho). *Verify*: reinjetar M9. *Done when*: M9 morto.
- **Priority**: **Major**

### Fix 7 (**Minor**) — Contagens incluídos/excluídos intercambiáveis (M7)

- **Root cause**: toda fixture usa `1` incluído e `1` excluído — a simetria torna a troca invisível, no backend e no frontend.
- **Fix task** — *What*: usar quantidades **assimétricas** (p.ex. 2 incluídos e 1 excluído) em `test_repositorio_elegibilidade.py:194-227`, `test_elegibilidade_api.py:138-172` e na fixture `elegibilidade()` do frontend; no frontend, asserir cada quantidade junto do seu rótulo (`getByText('2 incluídos')` ou um `data-*` por contador) em vez de `getAllByText('1')`. *Verify*: reinjetar M7. *Done when*: M7 morto.
- **Priority**: **Minor**

### Fix 8 (**Minor**) — ELEG-01: coluna de área não pinada (M2)

- **Fix task** — *What*: em `test_repositorio_elegibilidade.py`, inserir um segurado com `codigo_ibge_area` **diferente** da área da sua apólice e asserir que `listar_candidatos` usa a **da apólice** (candidato aparece para a área da apólice, não para a do segurado). *Verify*: reinjetar M2. *Done when*: M2 morto.
- **Priority**: **Minor**

### Itens Minor adicionais, opcionais

- **Nota A** — ELEG-10: acrescentar um teste de serviço com candidatos que **existem** mas nenhum satisfaz a regra (`incluidos == 0`, `excluidos == N`), que é o caso literal da AC; hoje só o caso "zero candidatos" é coberto.
- **Nota B** — `test_get_registro_elegibilidade_de_outra_execucao_retorna_404` (`test_elegibilidade_api.py:238`) assere só o status; acrescentar `codigo == "resultado_elegibilidade_inexistente"` e o `content-type`, como a irmã em `:221`.
- **Nota C** — `SuperficieEventoDecisao.test.tsx:127` perdeu a asserção de `role="status"` ao contornar a ambiguidade dos dois indicadores de carregamento; recuperar com `getAllByRole('status')` + `toHaveTextContent`, ou nomeando os dois indicadores.
- **Integração** — montar `SuperficieEventoDecisao` em rota no `App.tsx` (lacuna declarada pelo autor, compartilhada com 2.1/2.2/2.3/2.4; item próprio, não pendência desta história).

---

## Lições candidatas (grounding para `.specs/lessons.json`)

| Origem fundamentada | Lição proposta |
| --- | --- |
| M6 e M8 sobreviveram; **L-024 reincide pela quarta superfície consecutiva** | **Promover/reforçar L-024**: quando uma AC enumera N campos que a interface deve exibir ("regra e versão, operando, valor observado, resultado e justificativa"), o teste precisa asserir os N — o padrão barato e comprovado é `expect(cabecalhos).toEqual([...])` sobre o conjunto exato de colunas, como em `SuperficieRegras.test.tsx:118-130`. Um regex de título que para antes do último campo (`/Explicação — Maria Sintética/`) deixa esse campo livre para desaparecer |
| M7 sobreviveu | **Fixtures simétricas escondem trocas de campo.** Quando dois contadores/campos irmãos aparecem no mesmo payload (incluídos/excluídos, sucesso/falha), a fixture precisa dar-lhes valores **diferentes** — com `1` e `1` a inversão dos dois é indistinguível em todas as camadas ao mesmo tempo |
| M4 sobreviveu; o `README.md` promete "nunca referência viva" | **Toda coluna criada explicitamente para congelar um valor precisa de um teste que altere a fonte viva depois e releia.** Sem esse teste, a coluna congelada e um `JOIN` vivo são indistinguíveis, e a promessa de imutabilidade fica só na documentação |
| M3 sobreviveu | **Uma restrição `UNIQUE` de N colunas precisa de um teste por coluna que a "abre".** Testar apenas que a repetição exata deduplica prova N−(N−1) da restrição; falta o caso que difere em **uma** coluna e **deve** gerar linha nova |
| M2 sobreviveu | **Quando duas tabelas têm uma coluna homônima (`segurados.codigo_ibge_area` / `apolices.codigo_ibge_area`), as fixtures precisam dar-lhes valores diferentes**, senão o `JOIN`/`WHERE` pode apontar para a tabela errada sem nenhum teste vermelho |
| Fix 1 (linha semeada quebra a leitura) | **Um backfill de migração cria uma segunda forma do mesmo dado.** Se o valor de backfill não passa pelo mesmo desserializador do dado real, existe um caminho de leitura que só explode em produção — o teste de migração deve reler as linhas migradas **pelo repositório**, não só por `SELECT` cru |
| Renumeração `0005`→`0006` | Quando o design é escrito em lote antes da numeração real, a task deve **verificar o próximo número livre** e asserir a sequência completa no teste de migrações — o que foi feito aqui corretamente (`(1,2,3,4,5,6)`) e serve de padrão |

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status (Round 1) |
| --- | --- | --- |
| ELEG-01 | Implementing | ⚠️ **Parcial — Needs Fix** (Fix 8) |
| ELEG-02 | Implementing | ✅ **Verified** |
| ELEG-03 | Implementing | ✅ **Verified** |
| ELEG-04 | Implementing | ✅ **Verified** |
| ELEG-05 | Implementing | ❌ **Needs Fix** (Fix 6) |
| ELEG-06 | Implementing | ❌ **Needs Fix** (Fix 2, Fix 3) |
| ELEG-07 | Implementing | ⚠️ **Parcial — Needs Fix** (Fix 4) |
| ELEG-08 | Implementing | ⚠️ **Parcial — Needs Fix** (Fix 7) |
| ELEG-09 | Implementing | ❌ **Needs Fix** (Fix 5) |
| ELEG-10 | Implementing | ✅ **Verified** (nota A) |

**4/10 Verified, 3 Parciais, 3 Needs Fix.**

---

## Summary

**Overall**: ❌ **Not Ready** — a história não fecha nesta rodada

**Spec-anchored check**: **4/10 ACs** com asserção casando integralmente o resultado definido pela spec; 3 parciais e 3 com lacuna. **Zero spec-precision gaps** — a spec 2.5 é precisa; o que falta é evidência
**Sensor**: **3/10 mutantes mortos, 7 sobreviveram** (P0-full, 10 mutações)
**Gate**: 373 backend + 202 frontend passed, 0 failed, 0 skipped; `ruff`/`pyright`/`lint`/`build` verdes — todos re-executados pelo Verificador na árvore real

**O que funciona**: o motor determinístico está correto e é genuinamente puro — os 5 critérios da ELEG-02 existem, cada um exclui sozinho, e o canal é copiado sem nunca ser comparado (M1 morto). A garantia central da história — "no máximo um resultado por combinação" — está comprovada por **round-trip real de DuckDB**, não por mock: remover o `ON CONFLICT DO NOTHING` faz o DuckDB levantar `ConstraintException` num teste existente (M10 morto), e o Edge Case de retomada após reinicialização é idempotente e silencioso, como a spec pede. A guarda de 404 para um registro de **outra** execução é real, não decorativa (M5 morto). A migração `0006` está bem feita: renumeração verificada sem pular nem duplicar números, recreate-and-copy com backfill asserido valor a valor, `UNIQUE` que não colide entre linhas semeadas, e o `README.md` de persistência atualizado (fechando de passagem a lição L-022 que 2.4 deixou aberta). Os desvios documentados nas "Notas de implementação" foram todos verificados independentemente e são razoáveis — em especial o campo novo de `RegraSnapshot`, cujos 5 pontos de construção foram atualizados sem mudar o significado de nenhum teste de 2.3/2.4.

**Problemas encontrados**: (1) um **defeito de produção** — `obter_por_id` levanta `TypeError` em qualquer linha semeada do conjunto demonstrativo, porque o backfill da migração grava `criterios` como objeto e o desserializador espera lista; a rota de detalhe devolve **500** onde pretendia 404 (reproduzido nesta rodada contra o banco real semeado). (2) **Sete mutantes sobreviveram**, e não são cosméticos: o canal "congelado" pode virar leitura viva (M4), `apolice_id` pode sair da `UNIQUE` fazendo a segunda apólice do mesmo segurado desaparecer (M3), o filtro pode ler a área do segurado em vez da apólice (M2), os contadores de incluídos e excluídos podem ser trocados (M7), um resultado excluído pode perder os critérios satisfeitos (M9) e a explicação da interface pode perder a versão da regra (M6) e duas colunas inteiras (M8) — tudo isso com 373+202 testes verdes. (3) A **ELEG-06 tem também uma lacuna de produção**, não só de teste: `nome_segurado` e `codigo_ibge_area` vêm de `JOIN` vivo, então editar o segurado ou a apólice depois **reescreve** a explicação histórica e pode contradizer o `valor_observado` congelado no mesmo payload.

**Next steps**: rotear os **Fix 1–8** de volta ao implementador (Fix 1 Blocker; 2–6 Major; 7–8 Minor), com prioridade para o Fix 1 (defeito real) e para os Fix 2/3 (ELEG-06, a garantia de auditabilidade da história). Nenhuma reescrita de produção é necessária para os Fix 4–8: são asserções e fixtures. Depois da correção, **reverificar reinjetando literalmente M2, M3, M4, M6, M7, M8 e M9** e confirmando que cada um morre. Esta foi a **iteração 1 de no máximo 3**.
