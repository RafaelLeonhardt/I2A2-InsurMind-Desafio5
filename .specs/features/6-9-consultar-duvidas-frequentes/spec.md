# História 6.9: Consultar dúvidas frequentes — Specification

## Problem Statement

O protótipo (`SimplePage(faq)`, item "Dúvidas frequentes" do `insuredNav`) mostra quatro perguntas educacionais sobre a simulação — o que é este ambiente, por que os dados são sintéticos, o que significa "comunicação simulada", etc. Na aplicação real, não existe nenhum componente, rota ou conteúdo de FAQ (`grep` por "dúvidas"/"duvidas"/"faq" no frontend não retorna nada). É a lacuna de menor esforço de todo o levantamento: conteúdo estático, sem dependência de backend, mas ausente por completo.

## Goals

- [ ] O segurado acessa "Dúvidas frequentes" pela navegação do seu perfil e lê as respostas às perguntas educacionais sobre o ambiente de simulação
- [ ] O conteúdo deixa claro, de forma consistente com o resto do produto, que nenhuma comunicação real é enviada e que os dados são sintéticos

## Out of Scope

| Feature | Reason |
| --- | --- |
| Busca/filtro dentro do FAQ | Volume de conteúdo é pequeno (poucas perguntas); busca adicionaria complexidade sem benefício demonstrável |
| Conteúdo administrável (CMS) para editar as perguntas | Fora de escopo do PoC — conteúdo estático versionado no próprio frontend, como o restante do produto |
| FAQ equivalente para o perfil Administrador | O protótipo só tem "Dúvidas frequentes" no `insuredNav`; não há pedido equivalente para o admin em nenhum artefato levantado |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Conteúdo das perguntas | Adaptar as quatro perguntas do protótipo (`SimplePage(faq)`, `docs/design/prototype/src/App.jsx`) ao vocabulário e às garantias já usadas no restante da aplicação real (ex.: "ambiente educacional", "dados sintéticos", "nenhum envio real de mensagens é realizado" — frase já usada em `Sidebar`/`sidebar-note` do protótipo e replicável aqui) | Mantém consistência de mensagem com o aviso já presente em toda a aplicação (`FaixaDemonstracao`, já implementada), em vez de inventar um texto novo desalinhado | y — decisão de conteúdo de baixo risco, sem ambiguidade de produto |
| Local de exibição | Renderizada como mais uma seção de `PainelSegurado` (mesmo padrão de composição das cinco superfícies de 5.1–5.6, `comoSecao`) — não como item de navegação lateral próprio, já que o perfil Segurado hoje usa uma página única com seções empilhadas (5.7), não abas | Mantém a decisão de composição já registrada em 5.7 (`PainelSegurado.tsx`) em vez de reabrir a discussão de navegação em abas vs. página única, que é uma divergência de UX já deliberada e aceita, não um defeito | y — consistente com o padrão de composição já estabelecido e aceito no projeto |

**Open questions:** none — todas resolvidas ou registradas acima.

---

## User Stories

### P1: Consultar as perguntas e respostas do FAQ ⭐ MVP

**User Story**: Como segurado, quero ler as dúvidas frequentes sobre o ambiente de simulação para entender que os alertas e comunicações que recebo são educacionais, não reais.

**Why P1**: É a única capacidade desta história — conteúdo estático sem camadas adicionais.

**Acceptance Criteria**:

1. WHEN o segurado acessar a seção "Dúvidas frequentes" THEN a interface SHALL exibir a lista de perguntas com suas respectivas respostas.
2. The conteúdo exibido SHALL declarar explicitamente que o ambiente é educacional, os dados são sintéticos e nenhuma comunicação real é enviada.

**Independent Test**: Abrir a seção e confirmar que as quatro perguntas do protótipo (ou seu equivalente adaptado) aparecem com resposta visível, sem depender de nenhuma chamada de API.

---

### P2: Expandir/recolher cada pergunta individualmente

**User Story**: Como segurado, quero expandir só a pergunta que me interessa, para não precisar rolar por todas as respostas de uma vez.

**Why P2**: Melhora usabilidade da P1; o conteúdo já é consultável com todas as respostas sempre visíveis, sem essa interação.

**Acceptance Criteria**:

1. WHEN o segurado selecionar uma pergunta fechada THEN a interface SHALL expandir sua resposta sem afetar o estado das demais perguntas.
2. WHEN o segurado selecionar uma pergunta já expandida THEN a interface SHALL recolhê-la novamente.

**Independent Test**: Expandir uma pergunta, confirmar que as demais permanecem no estado anterior, depois recolher a mesma pergunta e confirmar que ela volta ao estado fechado.

---

## Edge Cases

- The lista de perguntas SHALL nunca ficar vazia — se o conteúdo não puder ser carregado (caso venha a depender de um arquivo externo no futuro), a interface SHALL mostrar um conjunto mínimo de conteúdo embutido em vez de uma seção em branco.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| FAQ-01 | P1: Consultar as perguntas e respostas do FAQ | Implementing | `SuperficieFAQ.tsx` (novo) + `SuperficieFAQ.test.tsx` |
| FAQ-02 | P1: Consultar as perguntas e respostas do FAQ | Implementing | `SuperficieFAQ.tsx` (novo) + `SuperficieFAQ.test.tsx` |
| FAQ-03 | P2: Expandir/recolher cada pergunta individualmente | Implementing | `SuperficieFAQ.tsx` (`<details>` nativo) + `SuperficieFAQ.test.tsx` |
| FAQ-04 | P2: Expandir/recolher cada pergunta individualmente | Implementing | `SuperficieFAQ.tsx` (`<details>` nativo) + `SuperficieFAQ.test.tsx` |

**ID format:** `FAQ-NN`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 4 total, 4 mapped, 0 unmapped — Design inline (Medium, sem decisão de arquitetura nova); Execute completo, aguardando Verifier.

---

## Success Criteria

- [ ] A seção de FAQ está sempre acessível ao segurado sem depender de rede
- [ ] O texto nunca contradiz a mensagem de simulação já usada no restante do produto
