# História 5.5: Consultar o histórico de comunicados — Specification

## Problem Statement

A História 4.3 entrega o registro de primeira visualização de um comunicado individual, e a 5.4 entrega sua explicação, mas Carlos ainda não tem uma lista central de todos os seus comunicados. Sem essa história, Carlos não consegue enxergar seu histórico completo de comunicações simuladas, nem reabrir uma consulta anterior a partir de uma listagem própria.

## Goals

- [ ] Abrir Comunicados mostra canal, assunto ou resumo, data e estado de cada registro do segurado ativo, e só desse segurado
- [ ] Selecionar um comunicado abre conteúdo, prévia do canal e linha do tempo correspondente; a primeira abertura segue o registro idempotente de `Visualizada no portal` (Épico 4)
- [ ] Reabrir um comunicado já visualizado mantém estado e data inalterados, sem criar novo comunicado/entrega/marco
- [ ] Ausência de comunicados mostra estado vazio explicativo, com caminhos para Alertas, Apólice e Meus Dados
- [ ] Falha ao carregar lista/detalhe mantém a falha visível com impacto e próxima ação, sem mostrar conteúdo fixo como se fosse persistido
- [ ] A lista é operável por teclado/leitor de tela: seleção, canal, data e estado anunciados; ações não dependem de hover; cada linha preserva relações semânticas

## Out of Scope

| Feature | Reason |
| --- | --- |
| Explicação de como a mensagem foi criada | História 5.4 — referenciada pelo detalhe, não reimplementada aqui |
| Registro da primeira visualização em si | História 4.3 — esta história consome o mecanismo já existente |
| Preferências de canal/participação | História 5.6 |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Fonte da lista | `entregas_simuladas` (3.6) + `visualizacoes_comunicado` (4.3), filtradas por segurado via `mensagens`→`elegibilidades_historicas.segurado_id` — nenhuma tabela nova | Toda a informação de "o que foi entregue e visualizado" já existe; a lista é uma projeção filtrada, não um novo conceito de dado | y — decorre diretamente do dado já produzido pelos Épicos 3/4 |
| "Assunto ou resumo" para canais sem assunto (WhatsApp/SMS) | Um resumo derivado das primeiras palavras do `corpo` da apresentação simulada, truncado a um comprimento fixo, quando o canal for `whatsapp`/`sms`; para `email`, usa o `assunto` real | Cumpre "assunto ou resumo" sem inventar um campo de assunto para canais que não têm um | n — decisão técnica, revisável no Design |

**Open questions:** none — todas resolvidas ou registradas acima.

---

## User Stories

### P1: Lista de comunicados isolada por segurado ⭐ MVP

**User Story**: Como Carlos, quero ver todos os meus comunicados simulados numa lista, para consultar o que já recebi sem me preocupar em ver dado de outra pessoa.

**Why P1**: É o ponto de entrada da história.

**Acceptance Criteria**:

1. WHEN existirem comunicados associados a Carlos e ele abrir Comunicados THEN a interface SHALL exibir canal, assunto ou resumo, data e estado de cada registro, retornando somente comunicados do segurado sintético ativo.
2. IF Carlos não possuir comunicados THEN a lista SHALL apresentar estado vazio explicativo, mantendo caminhos válidos para Alertas, Apólice e Meus Dados.

**Independent Test**: Com dois segurados sintéticos tendo comunicados distintos, abrir a lista de cada um e confirmar que nenhum vê o comunicado do outro.

---

### P1: Detalhe com visualização idempotente e sem regressão de estado ⭐ MVP

**User Story**: Como Carlos, quero abrir o detalhe de um comunicado e confiar que reabri-lo nunca cria nada novo nem muda o registro da minha primeira leitura, para ter certeza de que a evidência de visualização é confiável.

**Why P1**: É a integração correta com o marco de visualização já entregue por 4.3.

**Acceptance Criteria**:

1. WHEN Carlos selecionar um comunicado e abrir o detalhe THEN a interface SHALL exibir o conteúdo, a prévia do canal e a linha do tempo correspondente, e a primeira abertura SHALL seguir o registro idempotente de `Visualizada no portal` definido no Épico 4.
2. WHEN um comunicado já em `Visualizada no portal` for reaberto THEN o estado e a data da primeira visualização SHALL permanecer inalterados, sem criar novo comunicado, entrega ou marco.

**Independent Test**: Abrir um comunicado pela primeira vez, anotar a data de visualização, reabri-lo, e confirmar que a data exibida é idêntica e nenhum novo registro foi criado no banco.

---

### P2: Erro visível sem conteúdo fixo e navegação acessível

**User Story**: Como Carlos, quero que uma falha ao carregar a lista ou um comunicado seja honesta, e que eu consiga navegar tudo por teclado/leitor de tela, para confiar na ferramenta em qualquer situação.

**Why P2**: Reforça honestidade e acessibilidade sobre o conteúdo já correto da P1; não bloqueia a primeira demonstração da lista funcionando.

**Acceptance Criteria**:

1. IF a API responder com erro ao carregar a lista ou o detalhe THEN a falha SHALL permanecer visível com impacto e próxima ação, e a interface SHALL nunca mostrar conteúdo fixo como se fosse persistido.
2. WHEN a lista for operada por teclado ou leitor de tela THEN seleção, canal, data e estado SHALL ser anunciados, com ações nunca dependendo de hover e cada linha preservando relações semânticas.

**Independent Test**: Forçar uma falha na API de lista (dublê) e confirmar que a tela mostra erro com impacto/próxima ação, nunca uma lista de exemplo; navegar a lista inteira por teclado e confirmar anúncio de cada campo por linha.

---

## Edge Cases

- IF um comunicado ainda não tiver sido visualizado (entrega existe, mas nenhuma linha em `visualizacoes_comunicado`) THEN a lista SHALL mostrar o estado correto ("Enviada — simulação", ainda não "Visualizada no portal"), sem antecipar a visualização.
- WHEN dois comunicados tiverem a mesma data (improvável, mas possível em dado sintético) THEN a ordenação SHALL ser determinística por um critério secundário estável (ex.: id), sem posição instável entre carregamentos.
- IF um comunicado pertencer a uma execução ainda não concluída (mensagem não `simulada_entregue`) THEN ele SHALL não aparecer na lista de Comunicados — só entregas de fato simuladas contam como comunicado (consistente com 4.3, que já recusa registrar visualização de mensagem não elegível).

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| COMUNICADOS-01 | P1: Lista de comunicados isolada por segurado | Design | Pending |
| COMUNICADOS-02 | P1: Lista de comunicados isolada por segurado | Design | Pending |
| COMUNICADOS-03 | P1: Detalhe com visualização idempotente e sem regressão de estado | Design | Pending |
| COMUNICADOS-04 | P1: Detalhe com visualização idempotente e sem regressão de estado | Design | Pending |
| COMUNICADOS-05 | P2: Erro visível sem conteúdo fixo e navegação acessível | Design | Pending |
| COMUNICADOS-06 | P2: Erro visível sem conteúdo fixo e navegação acessível | Design | Pending |

**ID format:** `COMUNICADOS-NN`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 6 total, 0 mapped to tasks, 6 unmapped ⚠️ (mapeamento ocorre na fase Tasks)

---

## Success Criteria

- [ ] Lista de comunicados nunca mostra dado de outro segurado
- [ ] Reabrir um comunicado nunca muda a data de primeira visualização nem cria novo registro
- [ ] Estado vazio mantém navegação para as demais superfícies
- [ ] Erro de carregamento nunca aparece como conteúdo fixo persistido
- [ ] Lista inteiramente navegável por teclado/leitor de tela
