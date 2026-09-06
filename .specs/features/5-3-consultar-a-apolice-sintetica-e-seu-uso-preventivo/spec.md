# História 5.3: Consultar a apólice sintética e seu uso preventivo — Specification

## Problem Statement

As Histórias 5.1/5.2 mostram alertas, mas Carlos não tem como consultar sua apólice em si nem entender como seus dados participaram das regras que geraram um alerta. Sem essa história, a apólice permanece invisível para o segurado, e a explicação de "por que fui incluído" (2.5) nunca chega até ele de forma acessível.

## Goals

- [ ] Abrir Apólice mostra número, situação, vigência, endereço sintético do risco, coberturas relevantes, canal preferencial e participação em alertas, obtidos da API e do registro persistido do segurado ativo
- [ ] Consultar a explicação de uma cobertura/localização que participou de uma execução mostra como a categoria foi comparada pela regra determinística, sem afirmação de cobertura/indenização/decisão de sinistro
- [ ] Apólice inativa ou sem cobertura relacionada ao evento explica o estado de forma objetiva, sem transformar a condição em falha técnica
- [ ] Apólice inexistente ou de outro segurado é impedida pela API (problema identificável) e mostrada como `Não encontrada` sem expor outro registro
- [ ] Consultar uma comunicação histórica usa o snapshot preservado daquela execução mesmo que os dados atuais divirjam; a superfície da apólice atual indica que alterações afetam só decisões futuras

## Out of Scope

| Feature | Reason |
| --- | --- |
| Edição da apólice pelo segurado | Nunca existe no MVP — apólice é dado sintético fixo, só as preferências (canal/participação) são editáveis (História 5.6) |
| Detalhe do alerta em si | História 5.2 — esta história é sobre a apólice, referenciada pelo alerta, não o inverso |
| Explicação agêntica de como a mensagem foi criada | História 5.4 |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Fonte da "explicação de como a categoria foi comparada" | Reusa os critérios já persistidos em `elegibilidades_historicas.criterios` (2.5) — mesmo dado que a superfície "Evento e decisão" de Marina já exibe (2.5), mas filtrado às categorias relevantes à apólice (área, tipo/situação, coberturas), sem os campos internos de auditoria administrativa | Evita duplicar a lógica de explicação de critério; reusa a mesma fonte imutável já produzida pela avaliação de elegibilidade | y — decorre diretamente do dado já produzido pelo Épico 2 |

**Open questions:** none — todas resolvidas ou registradas acima.

---

## User Stories

### P1: Dados da apólice e explicação de critérios sem promessa de cobertura ⭐ MVP

**User Story**: Como Carlos, quero consultar minha apólice e entender como ela participou de uma decisão preventiva, sem que isso pareça uma confirmação de cobertura, para me situar sem falsas expectativas.

**Why P1**: É o núcleo da história — sem ela, a apólice é invisível e a explicação de elegibilidade nunca chega ao segurado.

**Acceptance Criteria**:

1. WHEN Carlos abrir Apólice com uma apólice sintética associada a ele THEN a interface SHALL exibir número, situação, vigência, endereço sintético do risco, coberturas relevantes, canal preferencial e participação em alertas, obtidos da API e do registro persistido do segurado ativo.
2. WHEN Carlos consultar a explicação de uma cobertura ou localização que participou de uma execução THEN a interface SHALL exibir como a categoria foi comparada pela regra determinística, sem nenhuma afirmação de cobertura, indenização ou decisão de sinistro.

**Independent Test**: Abrir a apólice de um segurado com um alerta ativo e confirmar todos os campos do AC exibidos; abrir a explicação de uma cobertura envolvida e confirmar que o texto compara critério, sem nenhuma frase que prometa cobertura.

---

### P1: Estados de apólice sem falha técnica e isolamento por segurado ⭐ MVP

**User Story**: Como Carlos, quero que uma apólice inativa ou sem cobertura relacionada seja explicada com clareza, e que eu nunca consiga ver a apólice de outra pessoa, para confiar na integridade e na honestidade da informação.

**Why P1**: É a garantia de tratamento objetivo de estados normais e de isolamento de dados.

**Acceptance Criteria**:

1. IF a apólice estiver inativa ou sem cobertura relacionada ao evento THEN a superfície SHALL explicar o estado correspondente de forma objetiva, sem transformar a condição em falha técnica.
2. IF a apólice não existir ou não pertencer ao segurado ativo e for solicitada THEN a API SHALL impedir o acesso cruzado e responder com problema identificável, e a interface SHALL apresentar `Não encontrada` sem expor outro registro.

**Independent Test**: Abrir a apólice de um segurado com apólice `cancelada` e confirmar explicação objetiva, sem indicador de erro técnico; tentar acessar a apólice de outro segurado diretamente pelo endereço e confirmar `Não encontrada`.

---

### P2: Snapshot histórico preservado apesar de mudança atual

**User Story**: Como Carlos, quero que uma comunicação passada continue explicada com os dados de quando ela aconteceu, mesmo que minha apólice tenha mudado desde então, para entender corretamente o histórico sem confusão com o presente.

**Why P2**: Reforça a integridade histórica (AD-11) sobre o conteúdo já correto da P1; não bloqueia a primeira demonstração da apólice atual.

**Acceptance Criteria**:

1. WHEN dados atuais diferirem do snapshot usado numa execução anterior e Carlos consultar uma comunicação histórica THEN a explicação SHALL usar o snapshot preservado daquela execução.
2. The current-policy surface SHALL indicar que alterações afetam somente decisões futuras.

**Independent Test**: Alterar (via dado de teste) um campo da apólice após uma execução já concluída, e confirmar que a explicação da comunicação histórica ainda mostra o valor antigo, enquanto a superfície de Apólice atual mostra o valor novo com o aviso de "afeta só o futuro".

---

## Edge Cases

- IF a apólice tiver múltiplas coberturas mas só uma foi relevante à regra aplicada THEN a explicação SHALL destacar especificamente a cobertura avaliada, sem listar as demais como se também tivessem participado.
- IF Carlos não tiver nenhuma execução histórica para consultar (apólice nunca usada em nenhuma avaliação) THEN a superfície de Apólice SHALL mostrar os dados cadastrais normalmente, sem seção de "uso preventivo" vazia parecendo erro.
- WHEN a apólice estiver vigente mas fora do período de vigência atual (`vigencia_fim` passado) THEN o estado SHALL ser explicado como apólice expirada, distinto de "cancelada" ou "suspensa".

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| APOLICE-01 | P1: Dados da apólice e explicação de critérios sem promessa de cobertura | Execute (T1) | Verified (validation.md rodada 2) |
| APOLICE-02 | P1: Dados da apólice e explicação de critérios sem promessa de cobertura | Execute (T2) | Verified (validation.md rodada 2) |
| APOLICE-03 | P1: Estados de apólice sem falha técnica e isolamento por segurado | Execute (T2) | Verified (validation.md rodada 2) |
| APOLICE-04 | P1: Estados de apólice sem falha técnica e isolamento por segurado | Execute (T2) | Verified (validation.md rodada 2) |
| APOLICE-05 | P2: Snapshot histórico preservado apesar de mudança atual | Execute (T2) | Verified (validation.md rodada 2) |
| APOLICE-06 | P2: Snapshot histórico preservado apesar de mudança atual | Execute (T4) | Verified (validation.md rodada 2) |

**ID format:** `APOLICE-NN`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 6 total, 0 mapped to tasks, 6 unmapped ⚠️ (mapeamento ocorre na fase Tasks)

---

## Success Criteria

- [ ] Apólice exibe todos os campos do AC a partir de dado real, nunca fixo
- [ ] Nenhuma explicação de critério contém promessa de cobertura, indenização ou decisão de sinistro
- [ ] Apólice inativa/sem cobertura explica objetivamente, sem aparência de falha técnica
- [ ] Nenhuma apólice de outro segurado é acessível, direta ou indiretamente
- [ ] Comunicação histórica sempre usa o snapshot da execução, nunca o dado atual divergente
