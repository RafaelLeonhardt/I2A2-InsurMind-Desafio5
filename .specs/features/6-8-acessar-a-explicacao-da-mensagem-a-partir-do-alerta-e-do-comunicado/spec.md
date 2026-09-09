# História 6.8: Acessar a explicação da mensagem a partir do alerta e do comunicado — Specification

## Problem Statement

A História 5.4 já especificou e implementou o conteúdo de "Como esta mensagem foi criada" (`SuperficieExplicacaoComunicado`, `EXPLICACAO-01..07`, todas `✅ Verified`). O componente recebe `aberto`, `seguradoId` e `entregaSimuladaId`, e já é exaustivamente testado isoladamente. Mas, como o próprio `.specs/STATE.md` registra em "Known open items", ele nunca é chamado a partir de `SuperficieAlertas`, `SuperficieComunicado`/`SuperficieComunicados` ou `VisaoGeralSegurado` — não existe, hoje, nenhum botão "Ver como a mensagem foi criada" clicável na aplicação real, apesar de existir no protótipo (overlay `Explain`, imagem `08-explicacao-mensagem-ia`) em três pontos de entrada distintos (visão geral, alerta e comunicado). Esta história fecha exatamente essa lacuna de alcançabilidade — não estende nem reabre o conteúdo já verificado de 5.4.

## Goals

- [ ] A partir de um alerta ativo em `SuperficieAlertas` associado a uma entrega simulada, o segurado consegue abrir a explicação dessa mensagem
- [ ] A partir de um comunicado em `SuperficieComunicado`/`SuperficieComunicados`, o segurado consegue abrir a explicação da mesma forma
- [ ] Fechar a explicação sempre devolve o foco ao controle que a abriu, qualquer que seja a origem (alerta ou comunicado)

## Out of Scope

| Feature | Reason |
| --- | --- |
| Qualquer alteração ao conteúdo, comportamento de foco ou lógica interna de `SuperficieExplicacaoComunicado` | Já especificado e verificado em 5.4 (`EXPLICACAO-01..07`); esta história é só sobre onde o botão que a abre existe, não sobre o que ela mostra |
| Explicação a partir da "Visão geral" (`VisaoGeralSegurado`) quando não houver `entregaSimuladaId` disponível naquele contexto | Se a visão geral não tiver o id da entrega simulada associada ao alerta mais relevante prontamente disponível, essa origem específica fica para uma iteração futura — as duas origens da P1 (alerta e comunicado) já cobrem o caso principal do protótipo |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Como `entregaSimuladaId` chega a `SuperficieAlertas`/`SuperficieComunicado` | Cada alerta/comunicado já carrega ou pode carregar essa referência a partir dos dados retornados por `alerta_segurado`/`lista_comunicados` (a confirmar o nome exato do campo na fase de Design); se a API não expuser esse id para um item específico, o botão de explicação simplesmente não aparece para aquele item, em vez de abrir uma explicação vazia | Segue o mesmo princípio de "nunca inferir/inventar" já aplicado ao restante do projeto — o botão só existe onde o dado que ele precisa já existe | y — consistente com o princípio já formalizado em EXPLICACAO-05 |
| Botão em `VisaoGeralSegurado` | Fora do MVP desta história (ver Out of Scope), tratado como P3 caso o id esteja disponível | Reduz o risco de a história ficar bloqueada por uma origem cujo dado ainda não foi confirmado como disponível naquele componente específico | y — decisão de escopo, não uma ambiguidade deixada em aberto |

**Open questions:** none — todas resolvidas ou registradas acima.

---

## User Stories

### P1: Abrir a explicação a partir de um alerta ⭐ MVP

**User Story**: Como segurado, quero abrir "Como esta mensagem foi criada" a partir de um alerta ativo para entender a origem da comunicação que recebi sobre ele.

**Why P1**: É o ponto de entrada mais direto do protótipo (o alerta é a tela mais visitada do segurado) e o que mais reforça confiança no momento em que ela é mais necessária.

**Acceptance Criteria**:

1. WHEN um alerta exibido em `SuperficieAlertas` tiver uma entrega simulada associada THEN a interface SHALL exibir uma ação "Ver como esta mensagem foi criada" para aquele alerta.
2. WHEN o segurado acionar essa ação THEN a interface SHALL abrir `SuperficieExplicacaoComunicado` com `seguradoId` e `entregaSimuladaId` corretos para o alerta selecionado.
3. IF um alerta não tiver entrega simulada associada THEN a ação SHALL não aparecer para esse alerta, em vez de abrir uma explicação vazia ou com erro.

**Independent Test**: Abrir um alerta do cenário sintético que já tenha uma comunicação simulada associada, acionar "Ver como esta mensagem foi criada" e confirmar que o drawer abre com o conteúdo daquela entrega específica (não de outra).

---

### P1: Abrir a explicação a partir de um comunicado ⭐ MVP

**User Story**: Como segurado, quero abrir a mesma explicação a partir do histórico de comunicados para revisar a origem de uma mensagem já recebida anteriormente.

**Why P1**: É o segundo ponto de entrada do protótipo e cobre o caso de consulta posterior, não só no momento do alerta.

**Acceptance Criteria**:

1. WHEN um comunicado exibido em `SuperficieComunicado`/`SuperficieComunicados` tiver uma entrega simulada associada THEN a interface SHALL exibir a mesma ação "Ver como esta mensagem foi criada".
2. WHEN o segurado acionar essa ação a partir do comunicado THEN a interface SHALL abrir `SuperficieExplicacaoComunicado` com o `entregaSimuladaId` daquele comunicado específico.

**Independent Test**: Abrir o histórico de comunicados, selecionar um item, acionar a ação e confirmar que o conteúdo exibido corresponde exatamente àquele comunicado, não ao alerta mais recente.

---

### P1: Foco devolvido corretamente após fechar, qualquer que seja a origem ⭐ MVP

**User Story**: Como segurado, quero que fechar a explicação sempre devolva meu foco ao botão que abri, mesmo tendo entrado por caminhos diferentes, para navegar com teclado sem me perder.

**Why P1**: O comportamento de foco já existe dentro de `SuperficieExplicacaoComunicado` (EXPLICACAO-06/07); esta história só garante que ele funciona corretamente para as duas novas origens, não que ele seja reimplementado.

**Acceptance Criteria**:

1. WHEN o segurado fechar a explicação aberta a partir de um alerta THEN o foco SHALL retornar ao botão daquele alerta específico.
2. WHEN o segurado fechar a explicação aberta a partir de um comunicado THEN o foco SHALL retornar ao botão daquele comunicado específico.

**Independent Test**: Abrir e fechar a explicação a partir de um alerta por teclado, confirmar o foco de retorno; repetir a partir de um comunicado diferente e confirmar que o foco não vaza para o botão do alerta.

---

## Edge Cases

- IF o mesmo segurado tiver múltiplos alertas com entregas simuladas distintas THEN cada botão SHALL abrir a explicação da entrega correspondente ao seu próprio alerta, nunca a de outro alerta da lista.
- WHEN a explicação estiver aberta e o segurado trocar de segurado ativo (SeguradoContexto, 5.7) THEN a explicação aberta SHALL fechar, evitando misturar o contexto de um segurado com o de outro.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| ABRIREXP-01 | P1: Abrir a explicação a partir de um alerta | - | Pending |
| ABRIREXP-02 | P1: Abrir a explicação a partir de um alerta | - | Pending |
| ABRIREXP-03 | P1: Abrir a explicação a partir de um alerta | - | Pending |
| ABRIREXP-04 | P1: Abrir a explicação a partir de um comunicado | - | Pending |
| ABRIREXP-05 | P1: Abrir a explicação a partir de um comunicado | - | Pending |
| ABRIREXP-06 | P1: Foco devolvido corretamente após fechar, qualquer que seja a origem | - | Pending |
| ABRIREXP-07 | P1: Foco devolvido corretamente após fechar, qualquer que seja a origem | - | Pending |

**ID format:** `ABRIREXP-NN`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 7 total, 0 mapped to tasks, 7 unmapped ⚠️ — fase Specify apenas; Design/Tasks pendentes.

---

## Success Criteria

- [ ] Todo alerta/comunicado com entrega simulada associada tem um caminho clicável até sua explicação
- [ ] Nenhuma explicação aberta mistura o conteúdo de uma entrega com outra
- [ ] O foco de teclado nunca se perde ao fechar, de nenhuma das duas origens
