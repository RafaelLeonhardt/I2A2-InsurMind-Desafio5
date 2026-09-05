# História 5.1: Compreender o alerta mais relevante na visão geral — Specification

## Problem Statement

`VisaoGeralSegurado.tsx` (Épico 1) hoje é um mockup estático — título, alerta, ações preventivas e painel contextual são todos texto fixo hardcoded ("Há chuva forte prevista para sua região.", "AUTO-DEMO-001"), sem nenhuma chamada à API real. Sem esta história, a experiência central do perfil Segurado (entender o alerta mais relevante) não existe de verdade — é apenas uma casca visual sem dado real por trás, violando diretamente a proibição de dado fixo mascarando processamento real que já vale para todo o projeto.

## Goals

- [ ] Abrir a Visão geral com um alerta ativo relacionado à localização/apólice de Carlos mostra tipo do evento, severidade, período, localização, impactos esperados e recomendações preventivas curtas, práticas e coerentes com o evento
- [ ] A origem do alerta (real INMET ou cenário sintético) e o horário dos dados ficam visíveis; origem sintética nunca é confundida com observação real
- [ ] Recomendações preventivas usam linguagem objetiva, não alarmista, esclarecendo que a comunicação é privada, não substitui autoridades, e não confirma cobertura/indenização
- [ ] Ausência de alerta relevante mostra estado vazio explicativo, sem inventar risco/recomendação; Apólice, Comunicados e Meus Dados continuam acessíveis
- [ ] Fonte degradada mostra o último snapshot com idade e caráter só informativo, sem sugerir que um novo alerta foi produzido a partir dele
- [ ] A superfície distingue `Carregando`, `Alerta`, `Sem alerta`, `Contexto trocando` e `Erro`; falha informa impacto e próxima ação sem apagar o último contexto válido
- [ ] Navegação por teclado, zoom 200% e larguras suportadas preservam ordem, foco, nomes e alvos mínimos; nenhuma informação essencial depende só de cor/ícone/mapa/hover

## Out of Scope

| Feature | Reason |
| --- | --- |
| Lista completa de alertas ativos/anteriores | História 5.2 — a Visão geral mostra só o mais relevante |
| Detalhe da apólice | História 5.3 |
| Explicação de como a mensagem foi criada | História 5.4 |
| Alternância entre segurados sintéticos | História 5.7 — esta história consome o segurado ativo, não o gerencia |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Definição de "alerta mais relevante" | O evento meteorológico relevante (2.3) mais recente cujo público elegível (2.5) inclui o segurado ativo, entre os que já avançaram além de `sem_risco`/`sem_elegiveis` | É a única noção de "alerta relacionado a Carlos" que o backend já produz (Épico 2); nenhum conceito de "alerta" novo é necessário — é a mesma elegibilidade já calculada, vista do lado do segurado | y — decorre diretamente do dado já produzido pelo Épico 2 |
| Fonte de "recomendações preventivas" | As mesmas orientações de segurança já incluídas no `ContextoAgente` (3.1) e refletidas na mensagem gerada (3.2), não um texto gerado à parte para a Visão geral | Evita uma segunda fonte de "recomendação" divergente da que a mensagem gerada realmente contém; reusa o dado já minimizado e já aprovado no fluxo agêntico | n — decisão técnica, revisável no Design |

**Open questions:** none — todas resolvidas ou registradas acima.

---

## User Stories

### P1: Alerta mais relevante com origem e horário visíveis ⭐ MVP

**User Story**: Como Carlos, quero ver rapidamente o alerta mais relevante para mim, com sua origem e horário, para entender o risco sem confundir dado real com cenário demonstrativo.

**Why P1**: É o núcleo da história — sem ele, a Visão geral continua sendo um mockup.

**Acceptance Criteria**:

1. WHEN Carlos abrir a Visão geral com um alerta ativo relacionado à sua localização e apólice sintética THEN a interface SHALL exibir tipo do evento, severidade, período, localização, impactos esperados e recomendações preventivas curtas, práticas e coerentes com o evento.
2. WHEN a origem do alerta for apresentada THEN a procedência e o horário dos dados SHALL estar visíveis, e uma origem sintética SHALL nunca ser confundida com observação real.
3. WHEN recomendações preventivas forem exibidas THEN a linguagem SHALL ser objetiva, não alarmista e orientada à segurança, esclarecendo que a comunicação é privada, não substitui autoridades e não confirma cobertura ou indenização.

**Independent Test**: Com um segurado ativo elegível para um evento real (`real_inmet`), abrir a Visão geral e confirmar tipo/severidade/período/localização/impactos/recomendações reais, com a origem `real_inmet` visível e nunca rotulada como sintética.

---

### P1: Estados vazio, degradado e de transição sem dado inventado ⭐ MVP

**User Story**: Como Carlos, quero que a Visão geral seja honesta quando não há alerta, quando a fonte está degradada, ou quando algo falha, para nunca ser enganado por uma tela que parece normal mas não é.

**Why P1**: É a garantia central de honestidade da superfície — sem ela, um estado degradado poderia parecer um alerta válido.

**Acceptance Criteria**:

1. IF não existir alerta relevante para Carlos THEN a Visão geral SHALL apresentar um estado vazio explicativo, sem inventar risco ou recomendação, mantendo Apólice, Comunicados e Meus Dados acessíveis.
2. IF a fonte do alerta estiver degradada THEN o último snapshot SHALL aparecer com sua idade e caráter apenas informativo, sem a interface sugerir que um novo alerta foi produzido a partir dele.
3. WHEN o carregamento, uma troca de contexto ou um erro ocorrer THEN a superfície SHALL distinguir `Carregando`, `Alerta`, `Sem alerta`, `Contexto trocando` e `Erro`, e uma falha SHALL informar impacto e próxima ação sem apagar o último contexto válido.

**Independent Test**: Com um segurado sem nenhum evento elegível, abrir a Visão geral e confirmar o estado vazio explicativo, com navegação para as demais superfícies ainda funcional.

---

### P2: Acessibilidade em teclado, zoom e largura suportada

**User Story**: Como Carlos, quero navegar a Visão geral por teclado ou com zoom ampliado sem perder nenhuma informação essencial, para usar a ferramenta com a tecnologia assistiva que eu precisar.

**Why P2**: Reforça acessibilidade sobre o conteúdo já correto da P1; não bloqueia a primeira demonstração do alerta real.

**Acceptance Criteria**:

1. WHEN a Visão geral for usada por teclado, com zoom de 200% ou em largura suportada THEN a ordem, o foco, os nomes e os alvos mínimos SHALL permanecer acessíveis.
2. The interface SHALL nunca depender somente de cor, ícone, mapa ou hover para transmitir informação essencial.

**Independent Test**: Navegar a Visão geral inteira só por teclado com zoom de 200% e confirmar que toda informação essencial (tipo, severidade, origem, recomendações) permanece legível e alcançável.

---

## Edge Cases

- IF Carlos for elegível para mais de um evento simultaneamente THEN a Visão geral SHALL mostrar o mais relevante por um critério objetivo (mais recente entre os ainda ativos), sem ambiguidade de qual é "o" alerta exibido.
- IF o snapshot degradado estiver disponível mas sem nenhuma avaliação de elegibilidade associada a Carlos THEN o estado SHALL ser tratado como "sem alerta", não como "alerta degradado", já que nenhum alerta de fato existe para ele.
- WHEN a troca de contexto (5.7) estiver em andamento THEN a Visão geral SHALL permanecer em `Contexto trocando` até que todo o dado do novo segurado esteja pronto, nunca misturando dado do segurado anterior com o novo.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| VISAO-01 | P1: Alerta mais relevante com origem e horário visíveis | Execute (T1) | Implementing |
| VISAO-02 | P1: Alerta mais relevante com origem e horário visíveis | Execute (T2) | Implementing |
| VISAO-03 | P1: Alerta mais relevante com origem e horário visíveis | Execute (T2) | Implementing |
| VISAO-04 | P1: Estados vazio, degradado e de transição sem dado inventado | Execute (T1, T2) | Implementing |
| VISAO-05 | P1: Estados vazio, degradado e de transição sem dado inventado | Execute (T2) | Implementing |
| VISAO-06 | P1: Estados vazio, degradado e de transição sem dado inventado | Design | Pending |
| VISAO-07 | P2: Acessibilidade em teclado, zoom e largura suportada | Execute (T4) | Implementing |
| VISAO-08 | P2: Acessibilidade em teclado, zoom e largura suportada | Execute (T4) | Implementing |

**ID format:** `VISAO-NN`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 8 total, 0 mapped to tasks, 8 unmapped ⚠️ (mapeamento ocorre na fase Tasks)

---

## Success Criteria

- [ ] `VisaoGeralSegurado.tsx` não contém mais nenhum texto fixo de alerta/apólice/recomendação — tudo vem da API real
- [ ] Origem sintética nunca aparece rotulada como observação real, e vice-versa
- [ ] Ausência de alerta mostra estado vazio explicativo, nunca um risco inventado
- [ ] Fonte degradada mostra snapshot com idade, nunca como se fosse alerta novo
- [ ] Navegação inteira por teclado/zoom 200% preserva toda informação essencial
