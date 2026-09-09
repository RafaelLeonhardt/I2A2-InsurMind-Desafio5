# História 6.3: Editar e testar regras de negócio — Specification

## Problem Statement

`SuperficieRegras` (`src/frontend/src/funcionalidades/regras/SuperficieRegras.tsx`) já implementa a edição de regras preventivas — equivalente à tela `RulePage`/imagem `10-edicao-regra-negocio` do protótipo — testada isoladamente, mas nunca montada em `App.tsx`. Sem esta história, mudar ou consultar uma regra de negócio preventiva só é possível via chamada direta à API (`regras`/`gestao_regras`), nunca pela interface.

## Goals

- [ ] O administrador acessa "Regras de negócio" pela navegação (História 6.1) e vê a(s) regra(s) ativa(s), com evento, público elegível e comunicação configurados
- [ ] Uma alteração de regra é salva com o versionamento já existente no backend (AD-008, optimistic concurrency) refletido na interface
- [ ] A estimativa de elegíveis é recalculada e exibida antes de salvar, sem exigir uma execução real para ser vista

## Out of Scope

| Feature | Reason |
| --- | --- |
| Duplicar regra / testar com evento atual (vistos só na imagem 10, ausentes do protótipo interativo `App.jsx` e de `SuperficieRegras`) | Aparecem apenas nessa imagem isolada, sem confirmação de que fazem parte do escopo atual do produto nem suporte de backend conhecido — ficam fora até confirmação explícita |
| Rajadas de vento como condição separada (idem, só na imagem 10) | Mesmo motivo acima — não presente no domínio (`AvaliadorRisco`, 2.3) hoje |
| Gestão de usuários e perfis, Configurações (nav da imagem 10) | Não fazem parte desta história nem de nenhuma especificada — telas isoladas na imagem, sem contraparte de produto confirmada |
| Criação de uma segunda regra ativa simultânea para o mesmo tipo de evento | Fora do domínio atual (`RepositorioRegras`, 2.4); esta história edita a regra existente, não introduz múltiplas regras concorrentes |
| REGRASADM-04 (estimativa de elegíveis antes de salvar) | **Decisão do usuário em 2026-09-09**: adiada como follow-up — exige uma capacidade nova de backend (contar segurados por área/tipo de apólice/cobertura) que não existe hoje e é materialmente maior que "integrar navegação" (escopo das demais histórias do Épico 6). P2, não bloqueia REGRASADM-01/02/03 (a própria spec já registrava isso). Retomar como história própria se o produto priorizar |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Fonte de dado e regras de negócio da edição | **Corrigido durante o Design de 6.3**: `SuperficieRegras` (2.4) não tem seções "Evento/Público elegível/Comunicação" nem "resumo em linguagem natural" — é uma tabela versionada (tipo de evento, severidade, limiar, área, apólice, cobertura, antecedência, canal, versão, estado) + formulário de edição com "Testar"/"Ativar nova versão". Os mesmos dados de evento/elegibilidade/comunicação estão presentes, só não organizados nessas 3 seções nomeadas como o protótipo (`RulePage`) sugeria — reusado sem reescrita, só integrado à navegação | Verificado por leitura direta de `SuperficieRegras.tsx`; a Assumption original presumia uma estrutura visual que nunca existiu no componente real de 2.4 | y — corrigido com evidência de código, ver Out of Scope para o desdobramento em REGRASADM-04 |
| "Testar" valida contra eventos, não conta elegíveis | O botão "Testar" (`testarRegra`) avalia a regra contra cenários sintéticos de **eventos meteorológicos** (relevância de risco, mesmo mecanismo de 2.4/2.3) — não existe, hoje, nenhum endpoint que conte quantos segurados/apólices bateriam com área+tipo de apólice+cobertura de uma regra proposta. `GET /segurados` (6.4) só devolve id+nome, sem apólice/área/cobertura | Verificado em `api/regras.ts` (`CasoTeste` é por evento, não por segurado) e `lista_segurados.py` (`RespostaSeguradoListado` só tem `id`/`nome`) | y — corrigido com evidência de código |
| Concorrência otimista na UI | Um conflito de versão (`versao_esperada` desatualizado) é mostrado como erro explícito pedindo para recarregar, nunca sobrescrito silenciosamente | Seguindo AD-008, já aplicado a toda tabela mutável do projeto; backend já responde `409 conflito_versao` (`adaptadores/http/regras.py:456-459`) e o frontend já trata qualquer falha de `ativarRegra` como erro explícito (`ErroRegras`) — só faltava um teste próprio para esse cenário específico | y — decorre de AD-008, comportamento já existente, cobertura de teste adicionada nesta história |

**Open questions:** none — todas resolvidas ou registradas acima.

---

## User Stories

### P1: Consultar e editar a regra preventiva ativa ⭐ MVP

**User Story**: Como administrador, quero abrir a regra de negócio preventiva ativa, editar suas condições e salvar, para ajustar o critério de elegibilidade sem depender de uma chamada direta à API.

**Why P1**: É a capacidade central da história — sem ela, `SuperficieRegras` permanece inalcançável mesmo estando pronta.

**Acceptance Criteria**:

1. WHEN o administrador abrir "Regras de negócio" pela navegação THEN a interface SHALL exibir a regra preventiva ativa com suas seções de Evento, Público elegível e Comunicação preenchidas com os valores persistidos.
2. WHEN o administrador alterar um campo e confirmar "Salvar e testar regra" THEN o sistema SHALL persistir a nova versão da regra e atualizar a versão exibida na interface.
3. IF a versão da regra mudou no backend desde que a tela foi carregada (conflito de concorrência otimista) THEN o sistema SHALL rejeitar a gravação com um erro explícito, sem sobrescrever a versão mais recente.

**Independent Test**: Abrir "Regras de negócio", alterar um valor de condição, salvar, e confirmar que a versão da regra incrementou e o valor persistiu ao recarregar a tela.

---

### P2: Ver a estimativa de elegíveis antes de salvar

**User Story**: Como administrador, quero ver quantos segurados seriam elegíveis com as novas condições antes de salvar, para avaliar o impacto da mudança.

**Why P2**: Reforça confiança na edição da P1, mas a regra já pode ser editada e salva sem essa prévia.

**Acceptance Criteria**:

1. WHEN o administrador alterar uma condição da regra THEN a interface SHALL recalcular e exibir a estimativa de elegíveis correspondente antes de qualquer gravação.

**Independent Test**: Alterar o limiar de uma condição e confirmar que a contagem de elegíveis exibida muda de acordo, sem precisar salvar.

---

## Edge Cases

- IF nenhuma regra preventiva ativa existir para o tipo de evento monitorado THEN a interface SHALL mostrar esse estado explicitamente, nunca um formulário vazio sem explicação.
- WHEN o administrador tentar salvar uma condição inválida (ex.: limiar negativo) THEN o sistema SHALL rejeitar com uma mensagem de validação específica, sem persistir a alteração.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| REGRASADM-01 | P1: Consultar e editar a regra preventiva ativa | Execute | Implementing — `App.tsx` monta `SuperficieRegras` (2.4) no case `'regras'`; aguardando Verifier |
| REGRASADM-02 | P1: Consultar e editar a regra preventiva ativa | Execute | Implementing — `ativarRegra(id, versao, dados)` já existente (2.4); aguardando Verifier |
| REGRASADM-03 | P1: Consultar e editar a regra preventiva ativa | Execute | Implementing — backend já responde `409 conflito_versao`; teste novo cobrindo o cenário em `SuperficieRegras.test.tsx`; aguardando Verifier |
| REGRASADM-04 | P2: Ver a estimativa de elegíveis antes de salvar | - | Deferred — ver Out of Scope (decisão do usuário, exige capacidade nova de backend) |

**ID format:** `REGRASADM-NN`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified → Deferred

**Coverage:** 4 total, 3 mapped (P1, Execute concluído), 1 deferred (P2, REGRASADM-04) — Design feito inline (Medium, reusa `SuperficieRegras` 2.4 já existente, sem decisão de arquitetura nova); aguardando Verifier.

---

## Success Criteria

- [ ] A regra ativa é editável e salva pela interface, refletindo o versionamento real do backend
- [ ] Nenhuma gravação sobrescreve silenciosamente uma versão mais recente
- [ ] A estimativa de elegíveis exibida nunca diverge do que a regra salva de fato produziria
