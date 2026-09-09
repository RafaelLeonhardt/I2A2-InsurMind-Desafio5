# História 6.6: Consultar resultados da simulação e a linha do tempo — Specification

## Problem Statement

O protótipo fecha o ciclo do administrador com a tela de resultados (`Results`/imagem `05-resultado-simulacao`): estatísticas de geradas/processadas/entregues/falhas, tabela filtrável, detalhe de falha e exportação de relatório. `SuperficieResultados`, `SuperficieDetalheResultado` e `SuperficieLinhaDoTempo` já existem no frontend real, testadas isoladamente, mas nenhuma é montada em `App.tsx` — o mesmo padrão de órfã já documentado em `.specs/STATE.md`. Sem esta história, o resultado de uma simulação de envio (Épico 4 inteiro, já implementado no backend) não tem nenhuma superfície administrativa que o exiba.

## Goals

- [ ] Ao final do fluxo de envio simulado (História 6.5), o administrador vê o resultado consolidado da execução: estatísticas agregadas e a lista de itens por status/canal
- [ ] O administrador consegue inspecionar o detalhe de um item específico, incluindo o motivo de uma falha quando houver
- [ ] O administrador consegue consultar a linha do tempo ponta a ponta da execução (evento → decisão → geração → crítica → aprovação → simulação)

## Out of Scope

| Feature | Reason |
| --- | --- |
| "Corrigir dado e simular novamente" (ação vista no protótipo `Results`) | Equivale a uma nova execução por retentativa (AD-009), já coberta pelo mecanismo de retentativa do backend; esta história consulta o resultado, não reabre o fluxo de geração |
| Paginação real de 248 resultados como na imagem 05 | O volume de segurados do cenário sintético de demonstração é pequeno; paginação client-side simples cobre o caso real do produto sem replicar um número de exemplo do design de referência |
| Exportação de relatório para um formato específico não confirmado (PDF, CSV, etc.) | O backend de resultados (`resultados`, `detalhe_resultado`) não tem, até este levantamento, um endpoint de exportação confirmado; a P3 desta história cobre uma exportação simples (CSV client-side) e o formato definitivo fica sujeito à fase de Design |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Fonte de dado | `SuperficieResultados` (recebe `execucaoId`) e `SuperficieDetalheResultado` já implementadas consomem os endpoints `resultados`/`detalhe_resultado`/`consolidacao_resultados` existentes — nenhum endpoint novo necessário para P1/P2 | Verificado nas assinaturas de props já existentes no código-fonte | y — grounded no código-fonte |
| `SuperficieLinhaDoTempo` sem `execucaoId` explícito nas props | O componente resolve a execução/seleção internamente (ex.: por segurado ativo ou seleção própria) — a integração exata com o `execucaoId` desta tela é uma decisão de Design, não uma mudança de requisito | A assinatura atual (`export function SuperficieLinhaDoTempo()`) não recebe parâmetros; e como ela é montada a partir desta tela (query própria vs. prop) é uma decisão de composição, não uma exigência de produto nova | y — decisão de integração adiada para Design, consistente com o padrão já usado em 6.1 |
| Exportação de relatório (P3) | Uma exportação simples do resultado exibido (CSV gerado no cliente a partir dos dados já carregados) até que o produto confirme um formato/endpoint definitivo | Evita bloquear a história inteira por causa de uma funcionalidade cujo contrato de backend não está confirmado nesta auditoria | n — depende de confirmação de produto sobre o formato definitivo; tratado como P3 justamente por essa incerteza |

**Open questions:** none — todas resolvidas ou registradas acima (a incerteza de formato de exportação foi registrada como assumption de P3, não deixada em aberto).

---

## User Stories

### P1: Consultar o resultado consolidado da simulação ⭐ MVP

**User Story**: Como administrador, quero ver as estatísticas consolidadas de uma simulação de envio (geradas, processadas, entregues, falhas) para avaliar o sucesso do ciclo preventivo sem precisar consultar a API diretamente.

**Why P1**: É o fechamento visível do ciclo administrativo — sem ele, o resultado de todo o trabalho das Histórias 6.1–6.5 permanece invisível.

**Acceptance Criteria**:

1. WHEN uma execução atingir o estado de resultado consolidado THEN a interface SHALL exibir as estatísticas agregadas (quantidade gerada, processada, entregue e com falha) a partir dos dados persistidos.
2. WHEN o administrador filtrar a tabela de itens por status ou canal THEN a lista exibida SHALL refletir apenas os itens que atendem ao filtro selecionado.
3. The soma dos itens exibidos após qualquer filtro SHALL nunca exceder o total de itens da execução consolidada.

**Independent Test**: Abrir o resultado de uma execução concluída no cenário sintético e confirmar que a soma de entregues + falhas corresponde ao total processado exibido nas estatísticas.

---

### P1: Inspecionar o detalhe de um item, incluindo falhas ⭐ MVP

**User Story**: Como administrador, quero abrir o detalhe de um item específico do resultado, incluindo o motivo de uma falha, para entender e comunicar o que aconteceu com aquele envio simulado.

**Why P1**: É o nível de detalhe que dá utilidade prática ao resultado consolidado — sem ele, a tabela é só um contador sem explicação.

**Acceptance Criteria**:

1. WHEN o administrador selecionar um item da tabela de resultados THEN a interface SHALL exibir `SuperficieDetalheResultado` com os dados completos daquele item.
2. IF o item selecionado estiver em estado de falha THEN o detalhe SHALL exibir o motivo da falha tal como persistido pela API, sem inferir ou completar informação ausente.

**Independent Test**: Selecionar um item com falha simulada no cenário sintético e confirmar que o motivo exibido corresponde exatamente ao persistido pela API para aquele item.

---

### P2: Consultar a linha do tempo ponta a ponta

**User Story**: Como administrador, quero ver a linha do tempo completa de uma execução (do evento à simulação) para auditar a sequência de decisões automáticas e humanas de ponta a ponta.

**Why P2**: Complementa o detalhe da P1 com uma visão cronológica, mas o resultado já é útil sem essa visão consolidada.

**Acceptance Criteria**:

1. WHEN o administrador abrir a linha do tempo de uma execução THEN a interface SHALL exibir os marcos em ordem cronológica, do evento identificado até a simulação de envio.

**Independent Test**: Abrir a linha do tempo de uma execução concluída e confirmar que a ordem dos marcos exibidos corresponde à ordem cronológica real dos timestamps persistidos.

---

### P3: Exportar o resultado exibido

**User Story**: Como administrador, quero exportar os dados do resultado exibido para compartilhar ou arquivar fora da aplicação.

**Why P3**: Conveniência adicional — a consulta já é completa na interface sem essa exportação.

**Acceptance Criteria**:

1. WHEN o administrador acionar "Exportar" THEN o sistema SHALL gerar um arquivo com os dados atualmente filtrados/exibidos na tabela, sem incluir itens ocultos pelo filtro ativo.

**Independent Test**: Aplicar um filtro por status, exportar, e confirmar que o arquivo gerado contém apenas os itens daquele status.

---

## Edge Cases

- IF a execução ainda não tiver atingido um estado de resultado consolidado THEN a interface SHALL indicar que o resultado ainda não está disponível, sem mostrar uma tabela vazia como se fosse o resultado final.
- WHEN dois itens tiverem o mesmo status e canal (caso comum) THEN a ordenação da tabela SHALL ser estável (não reordenar itens iguais a cada nova renderização).

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| PAINELRES-01 | P1: Consultar o resultado consolidado da simulação | - | Pending |
| PAINELRES-02 | P1: Consultar o resultado consolidado da simulação | - | Pending |
| PAINELRES-03 | P1: Consultar o resultado consolidado da simulação | - | Pending |
| PAINELRES-04 | P1: Inspecionar o detalhe de um item, incluindo falhas | - | Pending |
| PAINELRES-05 | P1: Inspecionar o detalhe de um item, incluindo falhas | - | Pending |
| PAINELRES-06 | P2: Consultar a linha do tempo ponta a ponta | - | Pending |
| PAINELRES-07 | P3: Exportar o resultado exibido | - | Pending |

**ID format:** `PAINELRES-NN`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 7 total, 0 mapped to tasks, 7 unmapped ⚠️ — fase Specify apenas; Design/Tasks pendentes.

---

## Success Criteria

- [ ] Toda estatística exibida bate com a soma real dos itens persistidos
- [ ] Todo motivo de falha exibido vem do dado persistido, nunca de inferência
- [ ] A linha do tempo nunca mistura a proveniência de uma execução de origem com a de sua retentativa
