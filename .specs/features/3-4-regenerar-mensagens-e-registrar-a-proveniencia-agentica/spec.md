# História 3.4: Regenerar mensagens e registrar a proveniência agêntica — Specification

## Problem Statement

As Histórias 3.2 e 3.3 entregam geração e crítica de uma única tentativa cada, mas nada ainda fecha o ciclo automático de "reprovou, tenta de novo até um limite" nem consolida a proveniência completa de cada versão. Sem essa história, uma reprovação automática pararia o fluxo sem tentar se corrigir sozinho, e Marina não teria como auditar de onde veio cada mensagem — o AD-6 exige explicitamente esse ciclo automático limitado a três tentativas antes de qualquer intervenção humana.

## Goals

- [ ] Mensagem reprovada (crítico ou validação determinística recuperável) com tentativa disponível é regenerada automaticamente pelo redator com os motivos da reprovação, preservando o histórico anterior imutável
- [ ] No máximo três tentativas totais por mensagem; aprovação válida encerra o ciclo imediatamente
- [ ] Terceira tentativa também reprovada leva a mensagem a `falhou_conteudo` com uma `Exceção`, fora do lote simulável
- [ ] Falha não recuperada da OpenAI (geração ou crítica) após tentativas de integração esgotadas leva somente a mensagem afetada a `falhou_integracao_ia`, sem bloquear as demais
- [ ] Toda versão/avaliação expõe proveniência completa (agente, modelo, versão do prompt, categorias de entrada, saída, avaliação, tentativa, duração, métricas de uso), sem segredo nem conteúdo sensível em log
- [ ] Reinicialização do backend durante o ciclo retoma do último marco durável sem repetir tentativa concluída; estados terminais de mensagem nunca reabrem
- [ ] Marina acompanha etapa, tentativa atual, limite, aprovações e exceções por item, com atualizações acessíveis que não movem o foco inesperadamente

## Out of Scope

| Feature | Reason |
| --- | --- |
| Decisão humana de regenerar | História 3.5 — esta história cobre só o ciclo automático (redator↔crítico); a regeneração solicitada por Marina é tratada em 3.5, compartilhando o mesmo limite de tentativas |
| Revisão e decisão de lote | História 3.5 |
| Geração/crítica da primeira tentativa | Histórias 3.2/3.3 — esta história estende o ciclo, não o reimplementa |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Onde o laço automático de regeneração vive | Dentro do mesmo `StateGraph` por mensagem (3.2/3.3): uma aresta condicional de `criticar` de volta a `gerar` quando reprovada e `tentativa < 3`, incrementando a tentativa atomicamente antes de reentrar em `gerar` — em vez de o caso de uso relançar o grafo externamente | AD-4 já descreve exatamente esse ciclo (`criticando --> gerando: reprovada e tentativa menor que 3`) como parte do mesmo grafo por mensagem; LangGraph suporta arestas condicionais de volta a um nó anterior nativamente | y — decorre diretamente do AD-4, já aprovado |
| Contagem compartilhada entre tentativa automática e humana | O contador `mensagens.tentativa_atual` (3.2) é único e compartilhado; a História 3.5 vai incrementá-lo pelo mesmo mecanismo desta história, nunca por um contador paralelo | AD-6 exige explicitamente "tentativas automáticas e humanas compartilham o máximo de três" | y — já decidido no AD-6, apenas confirmado aqui |

**Open questions:** none — todas resolvidas ou registradas acima.

---

## User Stories

### P1: Regeneração automática limitada a três tentativas ⭐ MVP

**User Story**: Como Marina, quero que mensagens reprovadas sejam regeneradas automaticamente até três vezes, para só precisar prestar atenção nos casos que a automação não resolveu.

**Why P1**: É o comportamento central da história — sem ele, toda reprovação vira uma parada manual desnecessária.

**Acceptance Criteria**:

1. WHEN uma mensagem for reprovada pelo agente crítico ou por validação determinística recuperável, e ainda houver tentativa disponível THEN o agente redator SHALL receber os motivos da reprovação e gerar uma nova versão automaticamente, preservando o histórico anterior imutável e consultável.
2. The system SHALL permitir no máximo três tentativas totais por mensagem.
3. WHEN uma tentativa produzir uma aprovação válida THEN o ciclo daquele item SHALL encerrar imediatamente, sem consumir tentativas adicionais.
4. IF a terceira tentativa também for reprovada THEN a mensagem SHALL alcançar `falhou_conteudo`, gerar uma `Exceção`, e SHALL não poder integrar o lote simulável.

**Independent Test**: Com um dublê que reprova nas duas primeiras tentativas e aprova na terceira, confirmar 3 versões persistidas, a mensagem em `aguardando_revisao`, e nenhuma quarta tentativa disparada.

---

### P1: Isolamento de falha de integração por mensagem ⭐ MVP

**User Story**: Como Marina, quero que uma falha de conexão com a OpenAI afete só a mensagem envolvida, para que uma falha pontual não pare a produção inteira do lote.

**Why P1**: É a garantia de resiliência por item exigida pelo AD-8 — sem ela, uma falha transitória bloquearia todo o lote.

**Acceptance Criteria**:

1. IF uma falha não recuperada da OpenAI ocorrer durante geração ou crítica e as tentativas de integração (transporte) forem esgotadas THEN somente a mensagem afetada SHALL alcançar `falhou_integracao_ia`.
2. WHILE uma mensagem estiver em `falhou_integracao_ia` THEN as demais mensagens da execução SHALL continuar até seus próprios estados terminais, sem bloqueio cruzado.

**Independent Test**: Com um dublê que falha de transporte de forma esgotada para uma mensagem e funciona normalmente para as demais, confirmar que só a mensagem afetada termina em `falhou_integracao_ia` e as outras alcançam `aguardando_revisao`/`falhou_conteudo` normalmente.

---

### P1: Proveniência completa e retomada sem repetição ⭐ MVP

**User Story**: Como Marina, quero consultar a proveniência completa de qualquer versão ou avaliação, e confiar que uma reinicialização não repete trabalho já feito, para auditar e operar com segurança.

**Why P1**: É a garantia de auditabilidade (AD-10) e de continuidade (AD-7) sobre o ciclo já implementado pelas outras P1.

**Acceptance Criteria**:

1. WHEN a proveniência de qualquer versão ou avaliação produzida for consultada THEN o sistema SHALL apresentar agente, modelo, versão do prompt, categorias de entrada, saída, avaliação, tentativa, duração e métricas de uso.
2. The provenance record SHALL não conter chave, contato, prompt completo em log ou qualquer outra informação sensível.
3. WHEN o runner retomar a execução após uma reinicialização do backend durante o ciclo THEN ele SHALL continuar do último marco durável sem repetir uma tentativa já concluída.
4. The system SHALL nunca reabrir um estado terminal de mensagem já alcançado.

**Independent Test**: Persistir uma mensagem com tentativa 2 concluída e o backend reiniciado; confirmar que a retomada não repete a tentativa 1 nem a 2, e prossegue a partir do estado real persistido.

---

### P2: Acompanhamento acessível do ciclo por item

**User Story**: Como Marina, quero acompanhar etapa, tentativa e exceções de cada mensagem sem perder o foco da tela, para monitorar o lote com conforto.

**Why P2**: Reforça usabilidade sobre o ciclo já garantido pelas P1; não bloqueia a execução automática em si.

**Acceptance Criteria**:

1. WHEN tentativas e mensagens mudarem de estado THEN a interface SHALL mostrar etapa, tentativa atual, limite, aprovações e exceções por item.
2. The interface SHALL não mover o foco inesperadamente nem depender somente de cor para comunicar mudança de estado.

**Independent Test**: Observar a superfície durante um ciclo de 3 tentativas e confirmar que o foco do teclado permanece onde Marina o deixou, com cada mudança de estado também comunicada por texto/ícone.

---

## Edge Cases

- IF uma mensagem for reprovada na tentativa 3 por falha determinística (não crítica) THEN o mesmo terminal `falhou_conteudo` SHALL se aplicar, sem distinção de fonte da reprovação no estado final.
- IF a falha de integração ocorrer durante a própria tentativa 3 (não uma reprovação de conteúdo) THEN a mensagem SHALL alcançar `falhou_integracao_ia`, não `falhou_conteudo` — os dois terminais permanecem distintos por causa.
- WHEN uma execução tiver mensagens em terminais diferentes (`aguardando_revisao`, `falhou_conteudo`, `falhou_integracao_ia`) simultaneamente THEN o agregado da execução SHALL só avançar de `processando_mensagens` quando todas as mensagens alcançarem um terminal de conteúdo (isso é formalizado como o gate da História 3.5, mas o estado de cada mensagem já deve estar correto ao final desta história).

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| REGEN-01 | P1: Regeneração automática limitada a três tentativas | Execute (T3) | ✅ Verified |
| REGEN-02 | P1: Regeneração automática limitada a três tentativas | Execute (T2, T3) | ✅ Verified |
| REGEN-03 | P1: Regeneração automática limitada a três tentativas | Execute (T3) | ✅ Verified |
| REGEN-04 | P1: Regeneração automática limitada a três tentativas | Execute (T1, T2, T3) | ✅ Verified |
| REGEN-05 | P1: Isolamento de falha de integração por mensagem | Execute (T3) | ✅ Verified |
| REGEN-06 | P1: Isolamento de falha de integração por mensagem | Execute (T3) | ✅ Verified |
| REGEN-07 | P1: Proveniência completa e retomada sem repetição | Execute (T5) | ✅ Verified |
| REGEN-08 | P1: Proveniência completa e retomada sem repetição | Execute (T5) | ✅ Verified |
| REGEN-09 | P1: Proveniência completa e retomada sem repetição | Execute (T4) | ✅ Verified |
| REGEN-10 | P1: Proveniência completa e retomada sem repetição | Execute (T2, T4) | ✅ Verified |
| REGEN-11 | P2: Acompanhamento acessível do ciclo por item | Execute (T6) | ✅ Verified |
| REGEN-12 | P2: Acompanhamento acessível do ciclo por item | Execute (T6) | ✅ Verified |

**ID format:** `REGEN-NN`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 12 total, 12 mapped to tasks, 0 unmapped. Verificação independente em dois rounds (`validation.md`, `ce964f8..e72bbdb`): 12/12 ACs com evidência `file:line` e desfecho batendo com a spec, 3/3 Edge Cases, gate verde (737 backend + 253 frontend). O round 1 (`..70ce8af`) apontou duas lacunas **de teste**, sem defeito de produção: o mutante M7 (número de tentativa reconstruído na retomada) e um ramo de `_retomar_item` sem cobertura. As correções `c355fec` e `e72bbdb` são somente de teste (+78 linhas, 0 de produção) e o round 2 confirmou por reinjeção que M7 e M8 agora morrem — **REGEN-09 verificado**, 8/8 mutantes mortos.

---

## Success Criteria

- [ ] Ciclo reprova→regenera funciona automaticamente até 3 tentativas, sem intervenção manual
- [ ] Terceira reprovação sempre termina em `falhou_conteudo` com `Exceção`
- [ ] Falha de integração afeta só a mensagem envolvida, nunca o lote inteiro
- [ ] Proveniência completa consultável para toda versão/avaliação, sem segredo exposto
- [ ] Retomada após reinício nunca repete tentativa concluída nem reabre terminal
