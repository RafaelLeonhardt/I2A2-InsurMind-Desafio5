# História 3.3: Avaliar a qualidade e a segurança das mensagens — Specification

## Problem Statement

A História 3.2 entrega mensagens estruturalmente válidas em `criticando`, mas nada ainda avalia se o conteúdo é adequado — tom, utilidade, clareza, segurança, ausência de promessa de cobertura, distinção de alerta oficial. Sem essa avaliação, uma mensagem tecnicamente válida mas inadequada poderia chegar à supervisão humana já marcada como aprovada, esvaziando o propósito da revisão.

## Goals

- [ ] O agente crítico recebe a mensagem e o contexto mínimo necessário à avaliação, sem poder decidir risco, elegibilidade, cobertura ou limite de canal
- [ ] A avaliação estruturada contém decisão de aprovação/reprovação e motivos específicos, considerando tom preventivo, utilidade, clareza, segurança, ausência de promessa, distinção de alerta oficial e adequação ao canal
- [ ] A reprovação determinística (validadores de 3.2) permanece separada da avaliação textual do crítico; o modelo nunca sobrepõe a validação objetiva
- [ ] Mensagem aprovada pelo crítico e pelos validadores avança para `aguardando_revisao`, com a aprovação agêntica visualmente distinta da futura decisão humana
- [ ] Mensagem reprovada tem motivos estruturados associados à versão avaliada e fica disponível para a próxima tentativa automática (dentro do limite, definido na História 3.4)
- [ ] Saída inválida do crítico é tratada como falha da tentativa, nunca como aprovação; a mensagem não alcança supervisão/simulação como válida
- [ ] Marina inspeciona o detalhe de qualquer avaliação (versão, critérios, decisão, motivos, agente, modelo, duração) em linguagem acessível, sem esconder a separação IA/regras determinísticas

## Out of Scope

| Feature | Reason |
| --- | --- |
| Contagem de tentativas e regeneração automática após reprovação | História 3.4 — aqui a mensagem só é avaliada uma vez por versão; o ciclo de regeneração é orquestrado depois |
| Decisão humana sobre a mensagem | História 3.5 |
| Validação estrutural de campos obrigatórios e limite de canal | História 3.2 — já resolvida antes de a mensagem chegar a `criticando`; o crítico nunca revalida isso |
| Edição de conteúdo pelo crítico | Nunca existe — o crítico só aprova/reprova, nunca reescreve (AD-5/AD-6) |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Estrutura da saída do crítico | `with_structured_output` com um schema Pydantic `AvaliacaoCritica` (`aprovada: bool`, `motivos: list[MotivoCritica]`, cada motivo com `categoria` de um enum fechado — tom, utilidade, clareza, segurança, promessa_indevida, distincao_oficial, adequacao_canal — e `justificativa: str`) | Mesmo padrão de saída estruturada já adotado em 3.2 para o redator; um enum fechado de categorias torna os motivos consultáveis e filtráveis, em vez de texto livre não estruturado | n — decisão técnica, revisável no Design |
| Onde o crítico se encaixa no grafo do LangGraph | Novo nó `criticar` no mesmo `StateGraph` por mensagem iniciado em 3.2 (`GrafoGeracaoMensagem`, renomeado nesta história para refletir o escopo maior — ver Tech Decisions do Design) | AD-4 já define a transição `gerando`→`criticando` dentro do mesmo grafo por mensagem; adicionar o nó ao grafo existente evita duplicar a máquina de estados | y — decorre diretamente do AD-4, já aprovado |

**Open questions:** none — todas resolvidas ou registradas acima.

---

## User Stories

### P1: Avaliação crítica estruturada com contexto mínimo ⭐ MVP

**User Story**: Como Marina, quero que um agente crítico avalie cada mensagem com critérios explícitos e um contexto limitado, para impedir que conteúdo inadequado chegue à supervisão como se já estivesse aprovado.

**Why P1**: É o núcleo da história — sem ele não existe controle de qualidade agêntico algum.

**Acceptance Criteria**:

1. WHEN a etapa `criticando` começar para uma versão de mensagem estruturalmente válida THEN o agente crítico SHALL receber a mensagem e o contexto mínimo necessário à avaliação.
2. The critic agent SHALL não poder decidir risco, elegibilidade, cobertura ou limite de canal.
3. WHEN a saída estruturada do crítico for validada THEN ela SHALL conter uma decisão de aprovação ou reprovação e motivos específicos, considerando tom preventivo e não alarmista, utilidade, clareza, segurança, ausência de promessa, distinção de alerta oficial e adequação ao canal.
4. WHEN a avaliação for orquestrada sobre uma mensagem que viola campos ou limites determinísticos (3.2) THEN a reprovação determinística SHALL permanecer separada da avaliação textual do crítico, e o modelo SHALL não poder sobrepor ou flexibilizar essa validação objetiva.

**Independent Test**: Com um dublê do crítico configurado para reprovar por "tom alarmista", confirmar que a avaliação persistida contém a categoria e a justificativa específicas, sem afetar a validação determinística já resolvida em 3.2.

---

### P1: Transições de estado a partir da decisão do crítico ⭐ MVP

**User Story**: Como Marina, quero que a mensagem avance ou fique disponível para nova tentativa automaticamente conforme a decisão do crítico, para não precisar decidir manualmente cada avaliação.

**Why P1**: Fecha o ciclo determinístico de transição desta história ao estado real da mensagem.

**Acceptance Criteria**:

1. WHEN uma mensagem for aprovada pelo crítico e pelos validadores determinísticos THEN seu estado SHALL avançar para `aguardando_revisao`, com a aprovação agêntica permanecendo visualmente distinta da futura decisão humana.
2. WHEN uma mensagem for reprovada pelo crítico THEN os motivos SHALL ser estruturados e associados à versão avaliada, e o item SHALL ficar disponível para a próxima tentativa automática dentro do limite.
3. IF a saída do agente crítico for inválida e não puder ser interpretada com segurança THEN ela SHALL ser tratada como falha da tentativa, nunca como aprovação, e a mensagem SHALL não alcançar supervisão ou simulação como válida.

**Independent Test**: Avaliar uma mensagem com um dublê de crítico que devolve saída malformada e confirmar que ela não avança para `aguardando_revisao` nem é tratada como aprovada, permanecendo disponível para nova tentativa.

---

### P2: Detalhe da avaliação acessível a Marina

**User Story**: Como Marina, quero abrir o detalhe de qualquer avaliação crítica, para entender exatamente por que uma mensagem foi aprovada ou reprovada.

**Why P2**: Reforça a transparência da decisão já tomada pela P1; não bloqueia o fluxo automático de avaliação em si.

**Acceptance Criteria**:

1. WHEN Marina abrir o detalhe de uma avaliação THEN a interface SHALL exibir versão da mensagem, critérios, decisão, motivos, agente, modelo e duração.
2. The interface SHALL usar linguagem acessível sem ocultar a separação entre decisão de IA e regras determinísticas.

**Independent Test**: Abrir o detalhe de uma avaliação reprovada e confirmar que cada motivo aparece com sua categoria e justificativa, e que a origem determinística (3.2) versus agêntica (3.3) da decisão é visualmente distinguível.

---

## Edge Cases

- IF o crítico aprovar uma mensagem que na verdade excede o limite de canal (contradição hipotética de saída) THEN a validação determinística de 3.2 SHALL prevalecer e a mensagem SHALL permanecer reprovada, independentemente da aprovação textual do crítico.
- IF a chamada ao crítico falhar por transporte (não por conteúdo) THEN o tratamento SHALL seguir o mesmo padrão de `falhou_integracao_ia` já estabelecido em 3.2 para o redator, não um novo terminal.
- WHEN a mesma versão de mensagem for avaliada mais de uma vez por um replay idempotente THEN o resultado persistido SHALL ser reaproveitado, sem nova chamada à OpenAI.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| CRIT-01 | P1: Avaliação crítica estruturada com contexto mínimo | Tasks | Implementing (T2) |
| CRIT-02 | P1: Avaliação crítica estruturada com contexto mínimo | Tasks | Implementing (T2) |
| CRIT-03 | P1: Avaliação crítica estruturada com contexto mínimo | Tasks | Implementing (T2) |
| CRIT-04 | P1: Avaliação crítica estruturada com contexto mínimo | Tasks | Implementing (T3) |
| CRIT-05 | P1: Transições de estado a partir da decisão do crítico | Tasks | Implementing (T4) |
| CRIT-06 | P1: Transições de estado a partir da decisão do crítico | Tasks | Implementing (T1, T4) |
| CRIT-07 | P1: Transições de estado a partir da decisão do crítico | Tasks | Implementing (T3) |
| CRIT-08 | P2: Detalhe da avaliação acessível a Marina | Tasks | Implementing (T5) |
| CRIT-09 | P2: Detalhe da avaliação acessível a Marina | Tasks | Implementing (T5) |

**ID format:** `CRIT-NN`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 9 total, 0 mapped to tasks, 9 unmapped ⚠️ (mapeamento ocorre na fase Tasks)

---

## Success Criteria

- [ ] Mensagem aprovada pelo crítico e pelos validadores avança para `aguardando_revisao`
- [ ] Mensagem reprovada tem motivos estruturados e categorizados persistidos
- [ ] Saída inválida do crítico nunca é tratada como aprovação
- [ ] O crítico nunca sobrepõe uma reprovação determinística de 3.2
- [ ] Detalhe da avaliação exibe versão, critérios, decisão, motivos, agente, modelo, duração
