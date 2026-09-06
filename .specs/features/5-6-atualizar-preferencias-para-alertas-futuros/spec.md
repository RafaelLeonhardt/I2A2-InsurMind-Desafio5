# História 5.6: Atualizar preferências para alertas futuros — Specification

## Problem Statement

Carlos hoje não tem nenhuma forma de alterar seu canal preferencial ou sua participação em alertas — `segurados.canal_preferido`/`participa_de_alertas` (Épico 1) só são lidos, nunca escritos por nenhuma história até aqui. Sem essa história, Carlos não tem nenhum controle sobre como comunicações futuras serão preparadas, e a única mutação que o perfil Segurado pode legitimamente fazer no MVP continua inexistente.

## Goals

- [ ] Meus Dados mostra o canal preferencial atual (WhatsApp/e-mail/SMS) e a participação em alertas, sem oferecer nenhum outro cadastro completo no MVP
- [ ] Alteração válida é persistida localmente pela API com `Idempotency-Key` e `versao_esperada`; a interface mostra `Salvando` e depois `Salvo`
- [ ] Alteração persistida orienta a preparação de comunicação futura e integra a elegibilidade futura, sem alterar execuções/snapshots/mensagens/comunicados anteriores
- [ ] Falha/conflito ao salvar preserva os valores editados para correção/nova tentativa, sem indicar sucesso antecipado
- [ ] Comando repetido com conteúdo idêntico devolve a resposta registrada sem nova versão; conteúdo diferente com a mesma chave ou versão desatualizada retorna `409`
- [ ] Desativar participação explica que o efeito vale só para alertas futuros; comunicados e alertas históricos continuam consultáveis
- [ ] O formulário é operável por teclado: campos, ajuda, estado pendente, erro e confirmação com nomes e foco visíveis; nenhum resultado depende só de toast ou cor

## Out of Scope

| Feature | Reason |
| --- | --- |
| Qualquer outro campo de cadastro (endereço, dados pessoais, etc.) | Explicitamente fora do MVP pelo próprio AC — só canal e participação são editáveis |
| Recalcular execuções/elegibilidades passadas | Proibido pelo AC — mudança afeta só o futuro |
| Autenticação para autorizar a mudança | Fora do MVP (ADR-0009) — o segurado ativo do contexto demonstrativo já é a identidade usada |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Mecanismo de concorrência | `versao_esperada` sobre `segurados.id`, mesmo padrão de concorrência otimista já usado em `RepositorioExecucaoPreventiva`/`RepositorioMensagens`/`RepositorioRegras` — requer adicionar `versao INTEGER NOT NULL DEFAULT 1` a `segurados` (ausente hoje, pois nenhuma história anterior escreveu nessa tabela) | Consistente com o padrão já estabelecido em todo o projeto para toda mutação sujeita a concorrência; nenhum mecanismo novo | y — decorre diretamente do padrão já estabelecido (2.2/2.4/3.2) |

**Open questions:** none — todas resolvidas ou registradas acima.

---

## User Stories

### P1: Editar canal e participação com concorrência e idempotência ⭐ MVP

**User Story**: Como Carlos, quero alterar meu canal preferencial e minha participação em alertas com segurança, para controlar futuras comunicações sem risco de perder minha edição por um conflito ou repetição acidental.

**Why P1**: É o núcleo da história — a única mutação legítima do perfil Segurado no MVP.

**Acceptance Criteria**:

1. WHEN Carlos abrir Meus Dados THEN a superfície SHALL exibir o canal preferencial atual entre WhatsApp, e-mail e SMS e a participação em alertas, sem oferecer nenhum outro cadastro completo no MVP.
2. WHEN Carlos salvar uma alteração válida de canal ou participação THEN a mudança SHALL ser persistida localmente pela API com `Idempotency-Key` e `versao_esperada`, e a interface SHALL apresentar `Salvando` e, ao concluir, `Salvo`.
3. WHEN o mesmo comando for repetido com conteúdo idêntico THEN a API SHALL devolver a resposta registrada sem criar nova versão; conteúdo diferente com a mesma chave ou uma `versao_esperada` desatualizada SHALL retornar `409`.

**Independent Test**: Salvar uma alteração de canal, confirmar `Salvo`; repetir o mesmo comando com a mesma `Idempotency-Key` e conteúdo idêntico, e confirmar que nenhuma nova versão é criada.

---

### P1: Efeito só futuro e preservação de histórico ⭐ MVP

**User Story**: Como Carlos, quero que minha nova preferência valha só para o futuro, sem reescrever nada que já aconteceu, para confiar que o histórico permanece um registro fiel do que de fato ocorreu.

**Why P1**: É a garantia de integridade histórica (AD-11) aplicada à única mutação de domínio que o segurado pode fazer.

**Acceptance Criteria**:

1. WHEN uma alteração persistida existir e uma nova execução preventiva for iniciada THEN o canal SHALL orientar a preparação da comunicação e a participação SHALL integrar a elegibilidade futura, com execuções, snapshots, mensagens e comunicados anteriores permanecendo inalterados.
2. WHEN a participação for desativada THEN o resultado exibido SHALL explicar que o efeito vale somente para alertas futuros, com comunicados e alertas históricos continuando consultáveis.

**Independent Test**: Alterar o canal preferencial de Carlos e, em seguida, consultar uma execução/elegibilidade já concluída antes da mudança — confirmar que o canal registrado nessa elegibilidade (snapshot, 2.5) permanece o antigo.

---

### P2: Falha honesta e formulário acessível

**User Story**: Como Carlos, quero que uma falha ao salvar preserve o que eu digitei e explique o erro claramente, e que eu consiga usar o formulário inteiro por teclado, para nunca perder minha edição nem ficar sem saber o que aconteceu.

**Why P2**: Reforça honestidade e acessibilidade sobre a mutação já garantida pela P1; não bloqueia a primeira demonstração de salvar com sucesso.

**Acceptance Criteria**:

1. IF a API não confirmar a mutação por falha ou conflito THEN os valores editados SHALL ser preservados para correção ou nova tentativa, e a interface SHALL explicar o erro sem indicar sucesso antecipado.
2. WHEN o formulário for usado por teclado THEN campos, ajuda, estado pendente, erro e confirmação SHALL possuir nomes e foco visíveis, com nenhum resultado dependendo somente de toast ou cor.

**Independent Test**: Forçar um `409` de versão desatualizada (dublê) ao salvar, e confirmar que os valores editados continuam no formulário, com o erro explicado, sem "Salvo" aparecer antes da confirmação real.

---

## Edge Cases

- IF Carlos alterar o canal para o mesmo valor já vigente (nenhuma mudança real) THEN o sistema SHALL tratar como uma alteração válida idempotente normal, sem erro nem efeito colateral extra.
- IF duas edições concorrentes (duas abas, por exemplo) tentarem salvar com a mesma `versao_esperada` THEN só a primeira SHALL confirmar; a segunda SHALL receber `409`, mesmo padrão de concorrência já usado em 2.4/3.2.
- WHEN a participação for reativada após ter sido desativada THEN o efeito SHALL valer só a partir desse momento, sem retroagir a nenhuma execução no meio-tempo.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| PREFS-01 | P1: Editar canal e participação com concorrência e idempotência | T4/T5 | Pending |
| PREFS-02 | P1: Editar canal e participação com concorrência e idempotência | T1/T2/T3/T5 | Implementing |
| PREFS-03 | P1: Editar canal e participação com concorrência e idempotência | T3/T4 | Pending |
| PREFS-04 | P1: Efeito só futuro e preservação de histórico | T2 | Pending |
| PREFS-05 | P1: Efeito só futuro e preservação de histórico | T5 | Pending |
| PREFS-06 | P2: Falha honesta e formulário acessível | T3/T5 | Pending |
| PREFS-07 | P2: Falha honesta e formulário acessível | T5 | Pending |

**ID format:** `PREFS-NN`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 7 total, 7 mapped to tasks, 0 unmapped

---

## Success Criteria

- [ ] Meus Dados mostra e permite editar só canal e participação, nada além disso
- [ ] Concorrência (`versao_esperada`) e idempotência (`Idempotency-Key`) funcionam exatamente como em toda mutação anterior do projeto
- [ ] Nenhuma execução/elegibilidade/mensagem/comunicado anterior é alterada por uma mudança de preferência
- [ ] Falha ao salvar nunca perde o valor editado nem indica sucesso antecipado
- [ ] Formulário inteiramente operável por teclado, sem depender só de toast/cor
