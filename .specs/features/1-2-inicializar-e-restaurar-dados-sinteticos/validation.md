# Inicializar e Restaurar Dados Sintéticos Validation

**Date**: 2026-08-29
**Spec**: `.specs/features/1-2-inicializar-e-restaurar-dados-sinteticos/spec.md`
**Diff range**: `7633552..bf8732c` (21 commits: 16 task commits + router consolidation `f0a033d`/`f7718b4` + docs `acb26d7` + fix `bf8732c`)
**Verifier**: independent sub-agent (author ≠ verifier), read-only over the real tree
**Pass**: second verification pass (fix→re-verify iteration 2 of 3)

**Verdict: PASS ✅.** The single gap from the first pass is closed and independently re-derived
below. All 15 ACs and all 4 spec-listed edge cases are covered by spec-anchored assertions, the
full Build gate is green on backend and frontend, and 12 injected mutants produced 11 kills plus
1 proven-equivalent mutant (no genuine survivor). Two spec-precision gaps remain flagged — both are
spec-wording gaps, not test weaknesses, and neither blocks the verdict.

---

## Task Completion

| Task | Status | Notes |
| --- | --- | --- |
| T1–T16 | ✅ Done | All 16 marked `✅ Complete` in `tasks.md`; each has its own atomic Conventional Commit inside the diff range. |
| T3 | ✅ Done (deviation recorded) | `caminho_banco` shipped with a validated default rather than a bare-required field. Independently re-checked: validation still rejects empty/extension-less/`.txt` paths (`src/backend/testes/test_configuracao.py:92`) and the default resolves under the git-ignored `var/` (`src/backend/testes/test_configuracao.py:63`). |
| T5/T8 | ✅ Done (SPEC_DEVIATION recorded) | Logical foreign keys instead of `REFERENCES`, forced by DuckDB's non-deferrable FK checks. Documented in `tasks.md` T8 and in `adaptadores/persistencia/README.md`. |
| T12 | ✅ Done (out-of-`Where` edit recorded) | `test_saude.py` touched. Re-checked: `src/backend/testes/test_saude.py:28-31` is still an exact set equality, now enumerating the one legitimately added path — additive, not weakened. |
| post-hoc | ✅ Done | `adaptadores/api/` → `adaptadores/http/` (`f0a033d`, `f7718b4`). No code, config, or test references the old path; only `.specs/` planning docs do (`tasks.md:26`, `tasks.md:424`, `design.md:144`) — harmless historical drift. |
| F1 (post-Verifier fix) | ✅ Done | Verified independently below. `restaurar_dados_sinteticos` now checks `esta_semeado()` before `idempotencia.buscar()`; five call-order assertions updated; one new e2e test added. |

---

## Fix Verification (F1 — first pass's single gap)

**Spec-defined expected outcome, re-derived from `spec.md` without consulting the prior report:**
`spec.md:92` — *"IF a restauração for solicitada antes de qualquer inicialização bem-sucedida THEN
o sistema SHALL responder com um erro explícito orientando a executar a inicialização primeiro."*
`spec.md:39` (Assumptions) reinforces it: respond with an explicit error directing the operator to
run initialization first, never silently initialize. `"antes de qualquer inicialização bem-sucedida"`
admits **two** database states — no migrations at all, and migrations applied but not yet seeded —
and the spec draws no distinction between them, so both must produce the same explicit error.
The spec fixes no status code (see spec-precision gap 2); the implemented contract is
`409` + `codigo="nao_inicializado"` + a `proxima_acao` naming initialization.

| State | Evidence (`file:line` + assertion) | Result |
| --- | --- | --- |
| Zero migrations applied (the gap) | `src/backend/testes/test_dados_sinteticos_api.py:161` — `assert resposta.status_code == 409`; `:163` — `assert resposta.json()["codigo"] == "nao_inicializado"`; `:164` — `assert "inicialização" in resposta.json()["proxima_acao"]`; `:162` — `content-type` starts with `application/problem+json` | ✅ Closed |
| Schema migrated, not yet seeded (pre-existing case, re-checked for reorder damage) | `src/backend/testes/test_dados_sinteticos_api.py:150` — `assert resposta.status_code == 409`; `:152` — `assert resposta.json()["codigo"] == "nao_inicializado"`; `:153` — `assert "inicialização" in resposta.json()["proxima_acao"]` | ✅ Still correct |
| Use-case level: guard runs before anything else, no idempotency lookup | `src/backend/testes/test_restauracao.py:199` — `assert diario == ["esta_semeado"]`; `:200` — `assert "buscar" not in diario`; `:201-202` — guard and `restaurar` never called | ✅ Closed |

**Why the fix actually works** (not merely why a test now passes): `SemeadorDadosSinteticos.esta_semeado()`
(`src/backend/central_preventiva/adaptadores/persistencia/semeador.py:309-322`) queries
`information_schema.tables` *before* touching any reference table and returns `False` on a missing
table, so it is catalog-safe on a database with zero migrations — which is exactly what
`PortaIdempotencia.buscar()` was not. Moving it to the top of
`src/backend/central_preventiva/aplicacao/restauracao.py:59-60` therefore converts the previously
unhandled DuckDB catalog error into the domain's `NaoInicializado`, which the router translates at
`src/backend/central_preventiva/adaptadores/http/dados_sinteticos.py:146-153`. Directly confirmed by
mutation M2 below: making `esta_semeado()` tolerate a missing table re-breaks exactly this test.

**Regression scan of the reorder** (the fix changed shared call-order logic in a core use case):

- Happy path — order is now `esta_semeado → buscar → existe_execucao_nao_terminal → restaurar → registrar`, asserted exactly at `src/backend/testes/test_restauracao.py:120-126`. Guard-before-mutation ordering (SEED-10) is preserved.
- Idempotent replay (SEED-11) — `src/backend/testes/test_restauracao.py:150` (`["esta_semeado", "buscar"]`, no `restaurar`/`registrar`) and e2e `src/backend/testes/test_dados_sinteticos_api.py:104-105` (identical response, local edit survives). Unaffected.
- Idempotency conflict (SEED-12) — `src/backend/testes/test_restauracao.py:169` and e2e `:121-124`. Unaffected.
- Active-execution guard (SEED-10) — `src/backend/testes/test_restauracao.py:184` and e2e `:137-141`. Unaffected.
- **Observation (not a gap):** a replay of a previously registered key would now answer `nao_inicializado` instead of the stored response if the reference tables had been emptied after that restore. That state cannot arise from any spec'd operation (a successful restore leaves every reference table populated), and in it the restore precondition genuinely does not hold, so the answer is still the correct one. No AC is weakened.
- **Observation (not a gap):** answering a restore-before-init request opens a DuckDB connection and therefore materialises an empty database file. This is pre-existing behaviour (the old `buscar()` path did the same), and "sem aplicar nenhuma mutação" in `spec.md` is scoped to the reference dataset, which is untouched.

---

## Spec-Anchored Acceptance Criteria

### P1: Inicializar esquema versionado e dados sintéticos reproduzíveis

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| SEED-01 — banco ausente/vazio ⇒ aplica todas as migrações pendentes em ordem, cada uma em sua transação, e semeia o conjunto sintético | 8 tabelas + ledger criados; ordem migrar→semear; casos elegíveis e não elegíveis para chuva intensa e granizo; identificadores fictícios | `src/backend/testes/test_migracoes.py:77` — `assert tabelas(caminho) == TABELAS_ESPERADAS`; `src/backend/testes/test_inicializacao.py:92` — `assert diario == ["aplicar_pendentes", "esta_semeado", "semear"]`; `src/backend/testes/test_semeador.py:95-98` — `("chuva_intensa", True)`, `("chuva_intensa", False)`, `("granizo", True)`, `("granizo", False)` todos presentes; `src/backend/testes/test_inicializador.py:74-80` — contagens exatas por tabela | ✅ PASS |
| SEED-02 — reexecução na mesma versão de seed ⇒ não duplica registros e relata "já preparado" | Contagens inalteradas + mensagem "já preparado" | `src/backend/testes/test_inicializador.py:97` — `assert capsys.readouterr().out.startswith("Dados já preparados")`; `:98` — `assert contagens(caminho) == contagens_iniciais`; `src/backend/testes/test_inicializacao.py:107` — `assert resultado.estado == "ja_preparado"`; `:105` — `assert "semear" not in diario` | ✅ PASS |
| SEED-03 — versão registrada > versão conhecida ⇒ recusa sem qualquer mutação, erro explícito em PT-BR | `VersaoSchemaFutura`, zero mutação no arquivo, mensagem PT-BR | `src/backend/testes/test_migracoes.py:102-105` — `assert captura.value.versao_registrada == 99`, `assert "extra" not in tabelas(caminho)`, `assert registros(caminho) == [(1, "base"), (99, "futura")]`; `src/backend/testes/test_servidor.py:107` — `assert "mais nova que a versão" in str(captura.value)`; `:108-109` — `assert chamada == {}`, `assert estado_do_banco(caminho) == estado_anterior` | ✅ PASS |
| SEED-04 — migração pendente falha ⇒ preserva as anteriores commitadas, não registra a falha, erro identifica a migração | Migração 1 commitada, 2 ausente do ledger, `MigracaoFalhou(versao=2)` | `src/backend/testes/test_migracoes.py:115` — `assert captura.value.versao == 2`; `:116-118` — `assert "base" in tabelas(...)`, `assert "extra" not in tabelas(...)`, `assert registros(caminho) == [(1, "base")]` | ✅ PASS |
| SEED-05 — arquivo operacional fora do controle de versão e integralmente recriável | `.duckdb` git-ignorado; recriação completa a partir de migrações + seed | `.gitignore:18-20` (`*.duckdb`, `*.duckdb.wal`, `var/central_preventiva.duckdb`); `src/backend/testes/test_configuracao.py:63` — `assert configuracao.caminho_banco == RAIZ_PROJETO / "var" / "central_preventiva.duckdb"`; `src/backend/testes/test_conexao.py:23` — cria o diretório ausente; `src/backend/testes/test_inicializador.py:69` — `assert not caminho.exists()` antes da recriação completa | ✅ PASS |
| SEED-06 — documentar colunas, PK/FK, restrições, timestamps e estratégia de migração em doc versionado | Doc versionada cobrindo as 8 tabelas e os 5 termos exigidos | `src/backend/testes/test_migracoes.py:170` — `assert tabela in documento` para as 8 tabelas; `:172` — `assert termo in documento` para `chave primária`, `chave estrangeira`, `restriç`, `timestamp`, `migraç` (doc: `src/backend/central_preventiva/adaptadores/persistencia/README.md`) | ✅ PASS |
| SEED-07 — todo dado semeado é sintético/anonimizado, sem PII, credencial ou contato utilizável | Nenhum e-mail/telefone/CPF-CNPJ/URL em qualquer texto do dataset | `src/backend/testes/test_semeador.py:125-128` — `assert PADRAO_EMAIL.search(texto) is None` (+ telefone, CPF/CNPJ, URL) sobre todo texto do conjunto; `:115-117` — marcador `DEMO-` em números/nomes e UUIDs derivados do namespace fictício `central-preventiva.invalid` | ✅ PASS |

### P1: Restaurar a demonstração com segurança transacional e idempotente

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| SEED-08 — modal identifica objeto e impacto e bloqueia até confirmação explícita | Objeto + impacto visíveis; nenhuma chamada de API antes da confirmação | `src/frontend/src/funcionalidades/dados-sinteticos/RestaurarDemonstracao.test.tsx:41` — objeto no diálogo; `:42-46` — impacto (perda das alterações locais) no diálogo; `:48` — `expect(restaurar).not.toHaveBeenCalled()`; `src/frontend/src/componentes/Modal.test.tsx:53-55` | ✅ PASS |
| SEED-09 — confirmada e sem execução não terminal ⇒ repõe exatamente o conjunto versionado em uma única transação DuckDB | `201`, alteração local revertida, tudo-ou-nada | `src/backend/testes/test_dados_sinteticos_api.py:74` — `assert resposta.status_code == 201`; `:77` — `assert nomes_alterados(caminho) == 0`; `src/backend/testes/test_semeador.py:187` — falha injetada no meio ⇒ `assert contagens(caminho) == contagens_originais`; `:192` — `assert preservados == nomes_originais`; `src/backend/testes/test_semeador.py:157` — restaurar duas vezes não duplica | ✅ PASS |
| SEED-10 — existe execução em estado não terminal ⇒ recusa sem mutação e informa a execução ativa | `409`, `codigo="execucao_ativa_impede_restauracao"`, zero mutação | `src/backend/testes/test_dados_sinteticos_api.py:137` — `assert resposta.status_code == 409`; `:139` — `assert resposta.json()["codigo"] == "execucao_ativa_impede_restauracao"`; `:140` — `assert "execução preventiva ativa" in resposta.json()["ocorrencia"]`; `:141` — `assert nomes_alterados(caminho) == 1`; `src/backend/testes/test_repositorio_execucoes.py:41` — parametrizado sobre todos os estados não terminais | ✅ PASS |
| SEED-11 — mesma `Idempotency-Key` repetida ⇒ devolve a resposta registrada sem executar nova restauração | Resposta idêntica, sem segunda restauração | `src/backend/testes/test_dados_sinteticos_api.py:104` — `assert segunda.json() == primeira.json()`; `:105` — `assert nomes_alterados(caminho) == 1` (a alteração feita entre as duas chamadas sobrevive, provando que nada foi restaurado); `src/backend/testes/test_restauracao.py:150-152` — `assert diario == ["esta_semeado", "buscar"]`, sem `restaurar`/`registrar` | ✅ PASS |
| SEED-12 — mesma chave reutilizada com conteúdo diferente ⇒ `409` sem efeito | Exatamente `409`, `conflito_idempotencia`, zero mutação | `src/backend/testes/test_dados_sinteticos_api.py:121` — `assert resposta.status_code == 409`; `:123` — `assert resposta.json()["codigo"] == "conflito_idempotencia"`; `:124` — `assert nomes_alterados(caminho) == 1`; `src/backend/testes/test_restauracao.py:167-171` — chave/operação corretas, sem mutação | ✅ PASS |
| SEED-13 — transação não concluída ⇒ conjunto anterior íntegro e consultável + estado terminal de falha com ocorrência, impacto e próxima ação segura | Dados preservados; os três campos presentes; sem vazamento da causa interna | `src/backend/testes/test_dados_sinteticos_api.py:185` — `assert corpo["ocorrencia"] and corpo["impacto"] and corpo["proxima_acao"]`; `:186` — `assert "falha simulada" not in str(corpo)`; `:187` — `assert nomes_alterados(caminho) == 1`; `src/frontend/src/funcionalidades/dados-sinteticos/RestaurarDemonstracao.test.tsx:90-92` — os três rótulos no `role="alert"` | ⚠️ Spec-precision gap (coberto) |
| SEED-14 — estados `Confirmação`/`Restaurando`/`Concluído`/`Falha`, foco preso, `Esc` quando aplicável, foco devolvido à origem | Os 4 estados observáveis + 3 comportamentos de foco | `RestaurarDemonstracao.test.tsx:41-48` (`Confirmação`), `:62-64` (`Restaurando`, ação desabilitada), `:77-80` (`Concluído`), `:89-92` (`Falha`), `:106` — `expect(acionador).toHaveFocus()`; `src/frontend/src/componentes/Modal.test.tsx:64-70` (trap `Tab`/`Shift+Tab`), `:79` (`Esc` fecha quando permitido), `:88` (`Esc` ignorado quando bloqueado), `:101` (foco devolvido) | ✅ PASS |
| SEED-15 — exposta exclusivamente por REST/JSON sob `/api/v1`, JSON `snake_case`, exigindo `Idempotency-Key` em toda requisição | Rota `/api/v1/dados-sinteticos/restauracoes`; corpo `snake_case`; ausência da chave ⇒ `422` | `src/backend/testes/test_dados_sinteticos_api.py:75` — `assert set(resposta.json()) == {"status", "restaurado_em"}`; `:86-88` — `assert resposta.status_code == 422`, `codigo == "idempotency_key_ausente"`; `:203` — propriedades `snake_case` no schema OpenAPI; `src/backend/testes/test_saude.py:28-31` — conjunto exato de `paths` do OpenAPI | ✅ PASS |

**Status**: ✅ 15/15 ACs covered with spec-anchored assertions · ⚠️ 2 spec-precision gaps flagged.

1. **SEED-13** — `spec.md:80` exige que a falha apresente "ocorrência, impacto e próxima ação segura"
   sem fixar o texto. O teste afirma presença e não-vazio dos três campos, que é o máximo ancorável
   na spec; fixar as strings seria testar a implementação. Gap na redação da spec, não no teste.
2. **Edge case "restauração antes de qualquer inicialização"** — `spec.md:92` exige "um erro
   explícito orientando a executar a inicialização primeiro" sem fixar o status HTTP. A escolha
   `409` (registrada em `tasks.md` T12) é coerente com as demais recusas sem mutação; o teste
   ancora no `codigo` e no `proxima_acao`, que a spec de fato define em substância.

---

## Discrimination Sensor

Scratch: temporary `git worktree` at `HEAD` (never `git stash`), backend resolved via `PYTHONPATH`
so the mutated copy shadowed the editable install; frontend via a symlinked `node_modules`.
Pre-sensor `git status --porcelain` baseline captured, worktrees removed with
`git worktree remove --force`, and porcelain re-diffed afterwards — **identical**.

| Mutation | File:line | Description | Killed? |
| --- | --- | --- | --- |
| M1 | `aplicacao/restauracao.py:59-66` | Reverte a ordem do fix: `buscar()` antes de `esta_semeado()` (a regressão original) | ✅ Killed — `test_restauracao.py::test_restauracao_antes_da_inicializacao_e_recusada_sem_consultar_a_guarda`, `::test_execucao_ativa_impede_a_restauracao_sem_mutacao` |
| M2 | `persistencia/semeador.py:317-318` | `esta_semeado()` ignora tabela ausente (`return False` → `continue`) | ✅ Killed — `test_dados_sinteticos_api.py::test_restauracao_em_banco_sem_nenhuma_migracao_orienta_a_inicializar`, `test_semeador.py::test_esta_semeado_e_falso_sem_schema_aplicado` |
| M3 | `persistencia/semeador.py:320-321` | `esta_semeado()` ignora tabela vazia (`count == 0` deixa de retornar `False`) | ✅ Killed — `test_inicializador.py::test_inicializacao_em_banco_ausente_cria_schema_e_semeia`, `test_semeador.py::test_esta_semeado_e_falso_antes_e_verdadeiro_depois_de_semear` |
| M4 | `http/dados_sinteticos.py:147-148` | `NaoInicializado` responde `400` em vez de `409` | ✅ Killed — ambos os testes e2e de `nao_inicializado` |
| M5 | `aplicacao/restauracao.py:64` | Inverte a checagem de conflito de idempotência (`!=` → `==`) | ✅ Killed — `test_restauracao.py::test_chave_repetida_com_mesmo_conteudo_devolve_a_resposta_registrada`, `::test_chave_repetida_com_conteudo_diferente_conflita_sem_mutacao` |
| M6 | `persistencia/migracoes.py:81` | Versão futura deixa de ser recusada (`> conhecida` → `> conhecida + 100`) | ✅ Killed — `test_migracoes.py::test_recusa_versao_registrada_futura_sem_aplicar_mutacao` |
| M7 | `persistencia/semeador.py:346` | Falha na transação executa `COMMIT` em vez de `ROLLBACK` | ⚪ Survived — **equivalent mutant** (ver nota) |
| M7b | `persistencia/semeador.py:343` | Remove a transação única (`BEGIN TRANSACTION` → `pass`) | ✅ Killed — `test_semeador.py::test_falha_no_meio_da_restauracao_preserva_o_conjunto_anterior` |
| M8 | `persistencia/repositorio_execucoes.py:12` | Guarda de execução ativa invertida (`NOT IN` → `IN`) | ✅ Killed — `test_repositorio_execucoes.py` (3 casos) |
| M9 | `aplicacao/restauracao.py:73` | Remove o efeito colateral `registrar()` da chave de idempotência | ✅ Killed — `test_restauracao.py::test_restauracao_bem_sucedida...`, `test_dados_sinteticos_api.py::test_mesma_chave_com_conteudo_diferente_conflita_sem_mutacao` |
| M10 | `frontend/componentes/Modal.tsx:68` | Remove a devolução de foco ao controle de origem | ✅ Killed — `Modal.test.tsx` + `RestaurarDemonstracao.test.tsx` (2 casos) |
| M11 | `frontend/.../RestaurarDemonstracao.tsx:36` | Falha da API passa a levar ao estado `Concluído` | ✅ Killed — `RestaurarDemonstracao.test.tsx::apresenta o estado Falha...` |

**M7 equivalence proof (not a test gap).** Executed directly against DuckDB in the scratch: after a
statement error inside a transaction, DuckDB aborts the transaction itself; a subsequent `COMMIT` is
accepted as a no-op and the pre-transaction rows remain (`linhas apos: [(1,)]`). The explicit
`ROLLBACK` is defensive, so replacing it with `COMMIT` produces no observable behavioural difference —
by definition an equivalent mutant, which cannot be killed by any test. The behaviour the spec
actually requires (single all-or-nothing transaction, SEED-09/SEED-13) is exercised by M7b, which
targets the same code and is killed. No fix task warranted.

**Sensor depth**: P0-full (data integrity path) — 12 mutations across use case, adapters, router,
and frontend, exceeding the ≥5 requirement.
**Result**: 11/12 killed, 1 proven equivalent, **0 genuine survivors** — PASS ✅

---

## Interactive UAT Results (if performed)

Not performed. The frontend surface is fully covered by RTL integration tests for all four
`SEED-14` states plus focus trap, `Esc`, and focus return; no human-judgment-only behaviour
(visual design, interaction feel) is asserted by the spec.

---

## Code Quality

| Principle | Status |
| --- | --- |
| Minimum code | ✅ The fix is a 6-line move plus assertions; no new abstraction introduced. |
| Surgical changes | ✅ `bf8732c` touches exactly the three files named in F1's `Where`, plus `tasks.md`. |
| No scope creep | ✅ No feature beyond the spec; `execucao_preventiva` stays minimal per the Out of Scope table. |
| Matches patterns | ✅ Guard-clause ordering, PT-BR docstrings, fake-port unit tests, `tmp_path` integration tests — all consistent with the pre-existing codebase. |
| Spec-anchored outcome check (asserted values match spec) | ✅ 15/15, with 2 spec-precision gaps flagged rather than silently passed. |
| Per-layer Coverage Expectation met (domain 1:1 ACs; routes happy+edge+error) | ✅ `dominio/estados_execucao.py` 1:1 (`test_estados_execucao.py`, parametrizado sobre todos os estados); a rota única cobre `201`, `409` ×3 (conflito, execução ativa, não inicializado ×2 estados), `422`, `500`, OpenAPI e CORS. |
| Every test maps to a spec requirement — no unclaimed tests | ✅ All 109 backend and 25 frontend tests trace to an AC, a listed edge case, or a `Done when` criterion (`test_conexao.py` → T4, `test_configuracao.py` → T3/SEED-05, `test_repositorio_idempotencia.py` → SEED-11/12, `test_camadas.py` pre-existing). |
| Documented guidelines followed | ✅ `AGENTS.md` (PT-BR naming/docstrings, synthetic data only, loopback-only config); `src/backend/central_preventiva/adaptadores/persistencia/README.md` for the schema contract. No numeric coverage-threshold guideline exists in the repo — strong defaults applied. |

---

## Edge Cases

- [x] **`schema_migracoes` ausente ou corrompida ⇒ recusa explícita** — `src/backend/testes/test_migracoes.py:145-148` (`RegistroMigracoesInvalido`, `assert tabelas(caminho) == {"segurados"}`) e `:156-159` (colunas erradas, sem mutação).
- [x] **Inicialização interrompida entre migrações ⇒ retoma da primeira pendente** — `src/backend/testes/test_migracoes.py:130-133` — `assert resultado.versoes_aplicadas == (2,)`, `assert registros(caminho) == [(1, "base"), (2, "extra")]`, e a linha inserida em `base` sobrevive (migração 1 não reaplicada).
- [x] **Restauração antes de qualquer inicialização ⇒ erro explícito orientando a inicializar** — ambos os estados admitidos pela frase da spec cobertos: `src/backend/testes/test_dados_sinteticos_api.py:150-153` (schema sem seed) e `:161-164` (nenhuma migração aplicada). **Gap da primeira passagem — fechado.**
- [x] **Repetir a inicialização logo após um sucesso ⇒ "já preparado" sem escrita adicional** — `src/backend/testes/test_inicializador.py:97-99` — mensagem, contagens inalteradas e ledger inalterado; `src/backend/testes/test_inicializacao.py:105` — `assert "semear" not in diario`.

---

## Gate Check

- **Gate command (Build)**: Backend `pytest && ruff check . && pyright` · Frontend `npm test -- --run && npm run lint && npm run build`
  - Note: the documented `uv run --directory src/backend …` form cannot execute as written on this machine — `pyproject.toml` pins `requires-python == "3.14.4"` while the local `uv` offers only 3.14.4/3.14.6. Run with `VIRTUAL_ENV="$(pwd)/.venv" uv run --directory . --active --no-sync <cmd>` from `src/backend`. This is an environment/pin mismatch, not a code defect, but it means the gate commands in `tasks.md` are not literally runnable as documented.
- **Result**: Backend 109 passed, 0 failed, 0 skipped · ruff "All checks passed" · pyright "0 errors, 0 warnings, 0 informations" (strict). Frontend 25 passed / 5 files, 0 failed · oxlint clean · `vite build` succeeded.
- **Test count before feature** (measured at `7633552` in a scratch worktree): backend 18, frontend 4.
- **Test count after feature**: backend 109, frontend 25.
- **Delta**: +91 backend, +21 frontend (+112 total). The fix commit itself added 1 test (108 → 109).
- **Skipped tests**: none.
- **Failures**: none.
- **Test Integrity**: no test deleted; no assertion weakened. The single pre-existing assertion modified in scope, `test_saude.py:28-31`, remains an exact set equality (same discriminating power) and only enumerates the path `SEED-15` legitimately adds. The five call-order assertions changed by `bf8732c` are equally strict — still full-list equality on the call journal, and `test_restauracao.py:200` *adds* a `"buscar" not in diario` assertion, strengthening the case.

---

## Fix Plans (if issues found)

None. The one gap from the first pass is closed and independently re-derived; no new gap and no
genuine surviving mutant was found in this pass.

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
| --- | --- | --- |
| SEED-01 | Implementing | ✅ Verified |
| SEED-02 | Implementing | ✅ Verified |
| SEED-03 | Implementing | ✅ Verified |
| SEED-04 | Implementing | ✅ Verified |
| SEED-05 | Implementing | ✅ Verified |
| SEED-06 | Implementing | ✅ Verified |
| SEED-07 | Implementing | ✅ Verified |
| SEED-08 | Design/Pending | ✅ Verified |
| SEED-09 | Implementing | ✅ Verified |
| SEED-10 | Implementing | ✅ Verified |
| SEED-11 | Implementing | ✅ Verified |
| SEED-12 | Implementing | ✅ Verified |
| SEED-13 | Implementing | ✅ Verified (⚠️ spec-precision gap on error wording) |
| SEED-14 | Design/Pending | ✅ Verified |
| SEED-15 | Design/Pending | ✅ Verified |

---

## Summary

**Overall**: ✅ Ready

**Spec-anchored check**: 15/15 ACs matched the spec-defined outcome · 2 spec-precision gaps flagged
**Sensor**: 11/12 mutations killed, 1 proven equivalent, 0 genuine survivors
**Gate**: backend 109 passed / ruff clean / pyright strict clean; frontend 25 passed / lint clean / build clean

**What works**:

- Initialization from an absent database file: versioned migrations applied in order, each in its own transaction, followed by the full synthetic seed with eligible and non-eligible cases for both chuva intensa and granizo.
- Idempotent re-initialization reporting "já preparado" with unchanged row counts and no extra write.
- Refusal of a future schema version and of a corrupted/missing migration ledger, with no mutation and PT-BR errors; server startup refuses to boot in either state.
- Mid-sequence migration failure that keeps prior migrations committed, omits the failed one from the ledger, and resumes correctly on the next run.
- Confirmed restore inside a single DuckDB transaction, guarded by the active-execution check, with `Idempotency-Key` replay and conflict handling, and full rollback preserving the previous dataset on failure.
- Accessible confirmation modal with focus trap, `Esc`, focus return, and the four `SEED-14` states.
- **Restore before any initialization now answers `409 nao_inicializado` in both database states the spec's wording admits** — the first pass's gap, verified closed.

**Issues found**: none blocking. Two spec-precision gaps (SEED-13 error wording; unspecified status
code for the restore-before-init refusal) are spec-wording gaps to tighten in a future spec revision,
not implementation or test defects. One process note: `tasks.md`'s Gate Check Commands are not
literally runnable given the `requires-python == "3.14.4"` pin versus locally available interpreters.

**Next steps**: Mark the feature done. Optionally tighten `spec.md` on the two flagged precision
gaps, and relax the `requires-python` pin (or install 3.14.4) so the documented gate commands run
as written.
