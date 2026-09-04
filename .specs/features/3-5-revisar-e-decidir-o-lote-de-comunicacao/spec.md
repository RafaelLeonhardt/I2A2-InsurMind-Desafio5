# História 3.5: Revisar e decidir o lote de comunicação — Specification

## Problem Statement

As Histórias 3.2–3.4 entregam mensagens que chegam a `aguardando_revisao` (aprovadas pelo crítico) ou a um terminal de conteúdo (`falhou_conteudo`/`falhou_integracao_ia`), mas nenhuma decisão humana ainda existe. Sem essa história, a aprovação agêntica seria a última palavra — violando diretamente o AD-6 ("Revisão humana interrompe o fluxo antes da simulação"), o requisito central de controle humano do produto.

## Goals

- [ ] Quando todas as mensagens alcançarem um estado terminal de conteúdo, a execução entra em `aguardando_revisao` e apresenta um lote com evento, regra, público, distribuição por canal, aprovações agênticas e exceções, com itens que exigem atenção primeiro
- [ ] O revisor de uma mensagem individual mostra destinatário sintético, conteúdo, versões, verificações determinísticas, avaliações críticas, dados de origem e proveniência, separados visualmente por categoria
- [ ] Marina decide cada mensagem aguardando revisão: aprovar, rejeitar, excluir do lote, ou solicitar nova geração com justificativa — nunca editar o texto
- [ ] Regeneração humana (`tentativas < 3`) transiciona atomicamente a mensagem para `gerando` e o agregado para `processando_mensagens`, compartilhando o mesmo máximo de 3 tentativas do ciclo automático (3.4), sem dupla contagem em reenvio idempotente
- [ ] Mensagem que já consumiu 3 tentativas não pode regenerar (ação indisponível com explicação); aprovação (quando elegível), rejeição e exclusão continuam disponíveis
- [ ] O agregado só retorna a `aguardando_revisao` quando nenhuma regeneração humana permanecer ativa, e só avança quando toda mensagem revisável tiver decisão terminal
- [ ] Rejeitar/excluir/regenerar sem justificativa é bloqueado com validação inline; o rascunho da justificativa é preservado até conclusão ou cancelamento consciente
- [ ] Toda decisão humana persiste perfil sintético responsável, data, resultado, justificativa (quando aplicável) e versão da mensagem, distinta da aprovação do agente crítico
- [ ] Decisão em lote (múltiplas mensagens) aplica todas as decisões válidas na mesma transação ou nenhuma; conflito de `versao_esperada` retorna `409` sem efeito parcial
- [ ] Execução sem nenhuma aprovada termina `concluida` sem simulação; execução com ao menos uma aprovada e todas decididas transiciona para `aguardando_confirmacao`

## Out of Scope

| Feature | Reason |
| --- | --- |
| Execução da simulação em si | História 3.6 — esta história só forma o gate `aguardando_confirmacao`, não simula |
| Edição do conteúdo da mensagem | Nunca existe no MVP (AD-5/AD-6) |
| Geração/crítica automática (ciclo redator↔crítico) | Histórias 3.2–3.4 — esta história só consome os terminais que esse ciclo produz e adiciona a decisão humana |
| Múltiplos perfis de revisor com permissões distintas | Fora do MVP (ADR-0009); há um único perfil operacional (Marina/Administrador) |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Quem é o "perfil sintético responsável" registrado na decisão | O perfil de demonstração ativo no momento (Administrador/Marina), já existente no contexto demonstrativo do Épico 1 — não um novo sistema de usuários | O projeto não tem múltiplos usuários reais (ADR-0009); o contexto demonstrativo já identifica "qual perfil está agindo" | y — decorre do escopo já fixado pelo Épico 1, apenas confirmado aqui |
| Mecanismo de decisão em lote atômica | Uma única transação DuckDB que aplica todas as decisões válidas do lote enviado; qualquer conflito de `versao_esperada` em qualquer item aborta a transação inteira e retorna `409` com o(s) item(ns) conflitante(s) identificado(s) | Cumpre literalmente "todas as decisões válidas deverão ser aplicadas na mesma transação ou nenhuma deverá ser aplicada"; é o mesmo padrão de transação única já usado pela restauração de dados sintéticos (Épico 1, AD-005) | y — decisão do usuário refletida no PRD, mecanismo já usado no projeto |
| Regeneração humana no grafo do LangGraph | Reentra no mesmo `StateGraph` por mensagem (3.2–3.4), no nó `gerar`, pelo mesmo mecanismo de `incrementar_tentativa` de 3.4 — a única diferença é que o gatilho é uma decisão humana explícita (com justificativa), não uma reprovação automática do crítico | Compartilha o mesmo contador e a mesma infraestrutura de grafo já aprovados; evita um segundo caminho de código para "regenerar" | y — decorre diretamente do AD-6, já aprovado |

**Open questions:** none — todas resolvidas ou registradas acima.

---

## User Stories

### P1: Lote de revisão priorizado por atenção ⭐ MVP

**User Story**: Como Marina, quero ver o lote inteiro de mensagens assim que todas alcançarem um estado terminal de conteúdo, com os itens que precisam de atenção primeiro, para revisar com eficiência.

**Why P1**: É o ponto de entrada de toda a revisão humana — sem ele não há onde decidir nada.

**Acceptance Criteria**:

1. WHEN todas as mensagens de uma execução alcançarem um estado terminal de conteúdo THEN a execução SHALL entrar em `aguardando_revisao` e apresentar um lote com evento, regra, público, distribuição por canal, aprovações agênticas e exceções.
2. The batch view SHALL ordenar itens que exigem atenção antes dos itens sem ressalvas.

**Independent Test**: Com um lote de 4 mensagens (2 aprovadas pelo crítico, 1 em `falhou_conteudo`, 1 em `falhou_integracao_ia`), confirmar que os dois itens com exceção aparecem antes dos dois aprovados na listagem.

---

### P1: Detalhe do revisor com contexto separado ⭐ MVP

**User Story**: Como Marina, quero abrir uma mensagem e ver claramente destinatário, conteúdo/versionamento e contexto de IA em seções separadas, para decidir com informação completa sem confusão visual.

**Why P1**: É o pré-requisito de informação para qualquer decisão de revisão consciente.

**Acceptance Criteria**:

1. WHEN Marina selecionar uma mensagem e abrir o revisor THEN a interface SHALL exibir destinatário sintético, conteúdo, versões, verificações determinísticas, avaliações críticas, dados de origem e proveniência.
2. The revisor SHALL separar visualmente destinatário, conteúdo/versionamento e contexto de IA.

**Independent Test**: Abrir o revisor de uma mensagem com 2 versões (uma reprovada, uma aprovada) e confirmar que ambas aparecem, com o destinatário sintético claramente separado do conteúdo gerado.

---

### P1: Decisão individual sem edição de texto ⭐ MVP

**User Story**: Como Marina, quero aprovar, rejeitar, excluir ou pedir nova geração para cada mensagem, sem poder editar o texto, para manter o controle humano sem abrir mão da rastreabilidade do conteúdo gerado.

**Why P1**: É o núcleo do controle humano exigido pelo AD-6.

**Acceptance Criteria**:

1. WHEN Marina decidir sobre uma mensagem em `aguardando_revisao` THEN ela SHALL poder aprovar, rejeitar, excluir do lote ou solicitar nova geração, e o sistema SHALL não permitir nenhuma edição manual do texto.
2. IF Marina tentar confirmar rejeição, exclusão ou regeneração sem justificativa THEN a ação SHALL permanecer bloqueada com validação inline, e o rascunho da justificativa SHALL ser preservado até concluir ou cancelar conscientemente.
3. WHEN uma decisão humana for persistida THEN o sistema SHALL registrar perfil sintético responsável, data, resultado, justificativa quando aplicável e versão da mensagem, permanecendo distinta da aprovação do agente crítico.

**Independent Test**: Tentar rejeitar uma mensagem sem preencher justificativa e confirmar bloqueio inline; preencher a justificativa, confirmar, e verificar o registro persistido com perfil, data, resultado e justificativa.

---

### P1: Regeneração humana compartilhando o limite de tentativas ⭐ MVP

**User Story**: Como Marina, quero pedir uma nova geração quando ainda houver tentativa disponível, e ver claramente quando essa opção não existe mais, para agir dentro do limite estabelecido sem surpresas.

**Why P1**: Fecha a integração entre o ciclo automático (3.4) e a decisão humana no mesmo contador de tentativas (AD-6).

**Acceptance Criteria**:

1. WHEN uma mensagem em `aguardando_revisao` com `tentativas < 3` tiver nova geração solicitada com justificativa THEN ela SHALL transicionar atomicamente para `gerando`, a tentativa SHALL ser incrementada uma única vez, e o agregado SHALL voltar a `processando_mensagens`, sem dupla contagem em reenvio idempotente.
2. IF uma mensagem já tiver consumido três tentativas THEN a ação de regenerar SHALL permanecer indisponível com uma explicação acessível, enquanto aprovação (quando elegível), rejeição e exclusão SHALL continuar disponíveis.
3. WHEN uma ou mais regenerações humanas estiverem ativas THEN o agregado SHALL retornar a `aguardando_revisao` somente quando nenhuma regeneração permanecer ativa, e nenhuma conclusão ou simulação SHALL ser permitida antes de decisão terminal para todas as mensagens revisáveis (itens já terminais de conteúdo não bloqueiam a guarda).
4. WHEN Marina solicitar regeneração para uma mensagem em `aguardando_revisao` e uma nova versão for criada THEN a versão anterior e a solicitação humana SHALL permanecer auditáveis, sem criar aprovação humana para nenhuma delas, e a nova versão SHALL exigir uma decisão humana própria ao voltar à supervisão.

**Independent Test**: Solicitar regeneração de uma mensagem com 2 tentativas já usadas e confirmar que a ação fica indisponível; solicitar de uma com 1 tentativa usada e confirmar transição atômica para `gerando`/`processando_mensagens`, com reenvio idempotente da mesma solicitação não incrementando a tentativa duas vezes.

---

### P1: Decisão em lote atômica e conclusão do agregado ⭐ MVP

**User Story**: Como Marina, quero decidir várias mensagens de uma vez e confiar que a execução conclui corretamente conforme o resultado agregado, para operar com eficiência sem perder a integridade transacional.

**Why P1**: É o fechamento do fluxo desta história — sem ele, o lote nunca converge para `concluida` ou `aguardando_confirmacao`.

**Acceptance Criteria**:

1. WHEN Marina enviar uma decisão em lote para uma seleção de várias mensagens THEN todas as decisões válidas SHALL ser aplicadas na mesma transação ou nenhuma SHALL ser aplicada, e qualquer conflito de `versao_esperada` SHALL retornar `409` sem efeito parcial.
2. WHEN todas as mensagens revisáveis tiverem sido decididas e nenhuma estiver aprovada THEN a execução SHALL terminar como `concluida` sem simulação, com os motivos de rejeição, exclusão e exceção permanecendo consultáveis.
3. WHEN ao menos uma mensagem tiver sido aprovada e todas tiverem sido decididas THEN o lote SHALL ser consolidado e a execução SHALL transicionar para o estado agregado `aguardando_confirmacao`, contendo apenas mensagens aprovadas pelo crítico e por Marina.

**Independent Test**: Enviar uma decisão em lote de 3 mensagens onde uma tem `versao_esperada` desatualizada; confirmar `409` e que nenhuma das 3 decisões foi aplicada.

---

## Edge Cases

- IF todas as mensagens de um lote estiverem em `falhou_conteudo`/`falhou_integracao_ia` (nenhuma chegou a `aguardando_revisao`) THEN a execução SHALL ainda assim alcançar `aguardando_revisao` e, sem nenhuma aprovável, terminar `concluida` sem simulação assim que Marina reconhecer o lote.
- IF Marina solicitar decisão em lote incluindo uma mensagem já decidida anteriormente (terminal) THEN essa mensagem específica SHALL ser rejeitada da operação em lote com motivo, sem impedir as demais válidas do mesmo envio (a atomicidade se aplica às decisões válidas enviadas, não força re-decidir itens já terminais).
- WHEN uma regeneração humana estiver ativa para pelo menos uma mensagem THEN uma tentativa de confirmar a simulação (3.6) SHALL ser bloqueada até a guarda de decisão terminal ser satisfeita.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| REVISAO-01 | P1: Lote de revisão priorizado por atenção | Execute (T3) | Implementing |
| REVISAO-02 | P1: Lote de revisão priorizado por atenção | Execute (T3) | Implementing |
| REVISAO-03 | P1: Detalhe do revisor com contexto separado | Execute (T3) | Implementing |
| REVISAO-04 | P1: Detalhe do revisor com contexto separado | Execute (T3) | Implementing |
| REVISAO-05 | P1: Decisão individual sem edição de texto | Execute (T2, T4) | Implementing |
| REVISAO-06 | P1: Decisão individual sem edição de texto | Execute (T1, T2, T4) | Implementing |
| REVISAO-07 | P1: Decisão individual sem edição de texto | Execute (T1, T2, T4) | Implementing |
| REVISAO-08 | P1: Regeneração humana compartilhando o limite de tentativas | Execute (T4) | Implementing |
| REVISAO-09 | P1: Regeneração humana compartilhando o limite de tentativas | Execute (T4) | Implementing |
| REVISAO-10 | P1: Regeneração humana compartilhando o limite de tentativas | Execute (T4) | Implementing |
| REVISAO-11 | P1: Regeneração humana compartilhando o limite de tentativas | Execute (T2, T4) | Implementing |
| REVISAO-12 | P1: Decisão em lote atômica e conclusão do agregado | Execute (T4) | Implementing |
| REVISAO-13 | P1: Decisão em lote atômica e conclusão do agregado | Execute (T4) | Implementing |
| REVISAO-14 | P1: Decisão em lote atômica e conclusão do agregado | Execute (T4) | Implementing |

**ID format:** `REVISAO-NN`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 14 total, 0 mapped to tasks, 14 unmapped ⚠️ (mapeamento ocorre na fase Tasks)

---

## Success Criteria

- [ ] Lote entra em `aguardando_revisao` só quando toda mensagem alcançar terminal de conteúdo, com itens de atenção primeiro
- [ ] Nenhuma decisão de rejeição/exclusão/regeneração passa sem justificativa
- [ ] Decisão em lote é atômica: tudo ou nada, `409` sem efeito parcial em conflito
- [ ] Regeneração humana e automática compartilham o mesmo limite de 3 tentativas, sem dupla contagem
- [ ] Execução sem nenhuma aprovada termina `concluida`; com ao menos uma, vai a `aguardando_confirmacao`
