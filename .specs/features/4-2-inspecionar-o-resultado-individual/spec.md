# História 4.2: Inspecionar o resultado individual — Specification

## Problem Statement

A História 4.1 entrega totais consolidados, mas Marina não consegue ainda abrir o resultado de um segurado sintético específico para conferir o conteúdo preparado e todas as decisões que o originaram. Sem essa história, uma anomalia num item individual (por exemplo, um texto inesperado ou uma decisão questionável) não teria como ser auditada em detalhe.

## Goals

- [ ] Abrir a ação de linha de uma mensagem mostra segurado sintético, apólice, canal, conteúdo, horários, estado atual, evento, versão da regra e aprovações agêntica e humana de origem
- [ ] Mensagem de e-mail mostra assunto e corpo na prévia do canal, rotulada como simulação
- [ ] Mensagem de WhatsApp/SMS mostra corpo e limite de canal validado, sem número de telefone real nem ação de envio
- [ ] Mensagem com versões anteriores relaciona a versão final às críticas, regenerações e decisão humana correspondentes; versões históricas permanecem imutáveis
- [ ] Identificador inexistente ou de outra simulação responde com problema identificável sem revelar outro registro; interface mostra `Não encontrado` com ação segura de retorno
- [ ] Navegação por teclado prende o foco na camada ativa (painel contextual/drawer), `Esc` fecha e devolve o foco à origem, sem empilhar camadas modais adicionais

## Out of Scope

| Feature | Reason |
| --- | --- |
| Totais consolidados e reconciliação | História 4.1 — esta história é o detalhe de um único item, não o agregado |
| Visualização pelo próprio segurado | História 4.3 — este detalhe é do perfil Administrador/Marina |
| Linha do tempo completa da execução | História 4.4 |
| Edição de qualquer campo do resultado | Nunca existe — resultado é histórico imutável (AD-5/AD-6/AD-11) |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Escopo de "identificador não pertencente à simulação selecionada" | O endpoint de detalhe exige tanto `execucao_id` quanto `mensagem_id`; se a mensagem existir mas pertencer a outra execução, a resposta é idêntica a "não encontrado" (não revela que o ID existe em outro contexto) | Cumpre literalmente "sem revelar outro registro" — mesmo padrão de não-enumeração já implícito no projeto (nenhum endpoint anterior vaza existência cruzada de recurso) | y — decorre diretamente do próprio AC |

**Open questions:** none — todas resolvidas ou registradas acima.

---

## User Stories

### P1: Detalhe completo do resultado individual ⭐ MVP

**User Story**: Como Marina, quero abrir o resultado de um segurado sintético e ver tudo que o originou, para conferir o conteúdo preparado e a cadeia de decisões por trás dele.

**Why P1**: É o núcleo da história — sem o detalhe completo, não há auditoria individual possível.

**Acceptance Criteria**:

1. WHEN Marina abrir a ação de linha de uma mensagem pertencente a uma simulação THEN a interface SHALL exibir segurado sintético, apólice, canal, conteúdo, horários e estado atual, além de evento, versão da regra e aprovações agêntica e humana de origem.
2. WHEN o resultado de uma mensagem de e-mail for aberto THEN a interface SHALL apresentar assunto e corpo na prévia do canal, rotulada como simulação, sem reproduzir uma entrega real.
3. WHEN o resultado de uma mensagem de WhatsApp ou SMS for aberto THEN a interface SHALL apresentar o corpo e o limite de canal validado, sem nenhum número de telefone real nem ação de envio.

**Independent Test**: Abrir o detalhe de uma mensagem de e-mail aprovada e simulada, e confirmar que assunto, corpo, segurado sintético, apólice, evento, versão da regra e as duas aprovações (crítico + Marina) aparecem, todos rotulados como simulação.

---

### P1: Rastreabilidade de versões e isolamento entre registros ⭐ MVP

**User Story**: Como Marina, quero relacionar a versão final de uma mensagem às críticas e regenerações que a produziram, e confiar que um ID errado nunca vaza informação de outro registro, para auditar com segurança e precisão.

**Why P1**: É a garantia de integridade histórica e de isolamento de dados sobre o detalhe já exibido pela P1.

**Acceptance Criteria**:

1. WHEN Marina consultar a origem de uma mensagem com versões anteriores THEN ela SHALL conseguir relacionar a versão final às críticas, regenerações e decisão humana correspondentes, com as versões históricas permanecendo imutáveis.
2. IF um identificador for inexistente ou não pertencer à simulação selecionada THEN a API SHALL responder com um problema identificável sem revelar outro registro, e a interface SHALL apresentar o estado `Não encontrado` com uma ação segura de retorno.

**Independent Test**: Abrir o detalhe de uma mensagem que passou por 2 reprovações antes da aprovação final, e confirmar que as 3 versões aparecem relacionadas às suas críticas/decisões, na ordem correta; tentar abrir um `mensagem_id` válido mas de outra execução e confirmar `Não encontrado`.

---

### P2: Navegação acessível sem empilhamento de camadas

**User Story**: Como Marina, quero navegar o detalhe inteiramente pelo teclado, com o foco preso e `Esc` funcionando de forma previsível, para operar com conforto e sem me perder na interface.

**Why P2**: Reforça acessibilidade sobre o conteúdo já exibido pela P1; não bloqueia a primeira demonstração do detalhe em si.

**Acceptance Criteria**:

1. WHEN Marina abrir painéis contextuais ou o drawer explicativo usando teclado THEN o foco SHALL ficar preso na camada ativa.
2. WHEN Marina pressionar `Esc` THEN a camada ativa SHALL fechar e o foco SHALL retornar à origem.
3. The interface SHALL nunca empilhar mais de uma camada modal adicional.

**Independent Test**: Abrir o drawer de detalhe por teclado, confirmar que `Tab` não sai do drawer, pressionar `Esc` e confirmar que o foco retorna exatamente ao elemento que abriu o drawer.

---

## Edge Cases

- IF uma mensagem em exceção (`falhou_conteudo`/`falhou_integracao_ia`) for aberta THEN o detalhe SHALL mostrar o conteúdo da última versão disponível (se houver) e a exceção associada, sem tentar simular um resultado inexistente.
- IF uma mensagem não tiver nenhuma versão aprovada por Marina (nunca chegou a `aguardando_revisao`) THEN a seção de decisão humana SHALL indicar explicitamente sua ausência, sem erro técnico.
- WHEN o drawer de detalhe for aberto a partir de contextos diferentes (Resultados vs. um link direto) THEN o comportamento de foco/`Esc` SHALL ser idêntico em ambos.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| DETALHE-01 | P1: Detalhe completo do resultado individual | Execute (T1, T2) | Implementing |
| DETALHE-02 | P1: Detalhe completo do resultado individual | Execute (T1, T2) | Implementing |
| DETALHE-03 | P1: Detalhe completo do resultado individual | Execute (T1, T2) | Implementing |
| DETALHE-04 | P1: Rastreabilidade de versões e isolamento entre registros | Execute (T1, T2) | Implementing |
| DETALHE-05 | P1: Rastreabilidade de versões e isolamento entre registros | Execute (T1, T2) | Implementing |
| DETALHE-06 | P2: Navegação acessível sem empilhamento de camadas | Design | Pending |
| DETALHE-07 | P2: Navegação acessível sem empilhamento de camadas | Design | Pending |
| DETALHE-08 | P2: Navegação acessível sem empilhamento de camadas | Design | Pending |

**ID format:** `DETALHE-NN`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 8 total, 5 mapped to tasks (T1), 3 unmapped (DETALHE-06..08 — T3)

---

## Success Criteria

- [ ] Detalhe de qualquer mensagem simulada mostra segurado, apólice, canal, conteúdo, horários, estado, evento, versão da regra e as duas aprovações
- [ ] E-mail mostra assunto+corpo; WhatsApp/SMS mostram corpo+limite, nunca telefone real
- [ ] Todas as versões de uma mensagem regenerada aparecem relacionadas às suas críticas/decisões, imutáveis
- [ ] ID inválido ou de outra execução sempre responde `Não encontrado`, nunca vaza outro registro
- [ ] Foco preso no drawer, `Esc` fecha e devolve foco à origem, nunca mais de uma camada modal
