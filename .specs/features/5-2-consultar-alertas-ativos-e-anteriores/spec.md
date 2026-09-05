# História 5.2: Consultar alertas ativos e anteriores — Specification

## Problem Statement

A História 5.1 entrega só o alerta mais relevante na Visão geral, mas Carlos não tem como ver a lista completa de alertas (ativos e anteriores) nem abrir o detalhe de cada um. Sem essa história, Carlos não consegue entender o histórico completo da sua relação com a Central Preventiva, nem revisitar uma situação passada.

## Goals

- [ ] Abrir Alertas mostra lista com evento, severidade, período, localização, origem e estado; ativos e anteriores são distinguíveis por rótulo, ícone e texto
- [ ] Selecionar um alerta abre o detalhe com origem, período, localização, impactos, recomendações, contexto da apólice e linha do tempo, com seleção anunciada sem mover o foco inesperadamente
- [ ] Alerta com representação geográfica tem pinos com ícone e legenda textual, com toda seleção também disponível numa lista equivalente para teclado/leitor de tela
- [ ] Ausência de alertas mostra estado vazio com explicação e próxima ação válida, sem exibir dado de outro segurado
- [ ] Alerta inexistente ou de outro segurado responde `Não encontrado` sem revelar outro registro, com retorno à lista
- [ ] Evento relevante cuja simulação ainda não foi concluída mostra `Ainda não simulado` explícito, sem comunicado ou visualização antecipada

## Out of Scope

| Feature | Reason |
| --- | --- |
| Alerta mais relevante isolado na Visão geral | História 5.1 — esta história é a lista completa e o detalhe, não o resumo |
| Detalhe da apólice em si | História 5.3 — o detalhe do alerta referencia contexto da apólice, mas não substitui a superfície dedicada |
| Como a mensagem foi criada (explicação agêntica) | História 5.4 |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Critério "ativo" vs. "anterior" | Um alerta é "ativo" enquanto sua execução preventiva associada não alcançar `concluida`/`falhou_simulacao` nem exceder o período do evento (`avaliacoes_risco.periodo_fim`, 2.3); todo o restante é "anterior" | Critério objetivo derivado de dado já persistido (mesmo período que a Visão geral, 5.1, já usa para "mais relevante"), sem introduzir um campo novo de "status de alerta" | n — decisão técnica, revisável no Design |
| Fonte do "mapa" com pinos | Reusa a mesma localização (`codigo_ibge_area`/coordenada sintética) já usada pela superfície de Fonte meteorológica (2.1) — nenhum componente de mapa novo além do já existente no projeto | Consistente com a decisão já tomada em 2.1 de que toda seleção em mapa tem lista equivalente; reusa o mesmo padrão de componente | y — decorre diretamente do padrão já estabelecido em 2.1 |

**Open questions:** none — todas resolvidas ou registradas acima.

---

## User Stories

### P1: Lista de alertas distinguindo ativos e anteriores ⭐ MVP

**User Story**: Como Carlos, quero ver todos os meus alertas, ativos e anteriores, claramente distinguidos, para entender minha situação completa.

**Why P1**: É o ponto de entrada da história — sem a lista, não há nada para abrir em detalhe.

**Acceptance Criteria**:

1. WHEN Carlos possuir alertas ativos ou anteriores e abrir Alertas THEN a interface SHALL exibir uma lista com evento, severidade, período, localização, origem e estado, com ativos e anteriores distinguíveis por rótulo, ícone e texto.
2. IF não existirem alertas para o segurado ativo THEN a lista SHALL apresentar estado vazio com explicação e próxima ação válida, sem exibir dado de outro segurado sintético.

**Independent Test**: Com um segurado com 1 alerta ativo e 2 anteriores, abrir Alertas e confirmar os 3 itens listados com o rótulo correto de ativo/anterior em cada um.

---

### P1: Detalhe do alerta com equivalência de mapa e lista ⭐ MVP

**User Story**: Como Carlos, quero abrir o detalhe de um alerta e ver tudo sobre ele, inclusive num formato que funcione com teclado e leitor de tela, para entender a situação completamente, independente da tecnologia que eu uso.

**Why P1**: É o núcleo de acessibilidade e completude da história.

**Acceptance Criteria**:

1. WHEN Carlos selecionar um alerta e abrir seu detalhe THEN a interface SHALL exibir origem, período, localização, impactos, recomendações, contexto da apólice e linha do tempo, com a seleção anunciada sem mover o foco inesperadamente.
2. WHEN o alerta possuir representação geográfica THEN os pinos do mapa SHALL ter ícone e legenda textual, e toda seleção SHALL existir também numa lista equivalente para teclado e leitor de tela.

**Independent Test**: Abrir o detalhe de um alerta com representação geográfica e confirmar que a mesma seleção disponível no mapa está disponível e operável na lista equivalente por teclado.

---

### P1: Isolamento por segurado e estados não simulados ⭐ MVP

**User Story**: Como Carlos, quero ter certeza de que só vejo meus próprios alertas, e que um evento ainda não simulado nunca finge ter um comunicado, para confiar plenamente no que a tela mostra.

**Why P1**: É a garantia de integridade de dados e de honestidade sobre estados intermediários.

**Acceptance Criteria**:

1. IF um alerta for inexistente ou não pertencer ao segurado ativo e seu endereço for acessado diretamente THEN a interface SHALL apresentar `Não encontrado` sem revelar outro registro, com retorno à lista de alertas.
2. WHEN Carlos acessar o detalhe de um evento relevante cuja simulação ainda não foi concluída THEN o estado `Ainda não simulado` SHALL ser explícito, sem nenhum comunicado ou visualização antecipada.

**Independent Test**: Acessar diretamente o endereço de um alerta de outro segurado sintético e confirmar `Não encontrado`; abrir o detalhe de um evento relevante ainda em `processando_mensagens` e confirmar `Ainda não simulado`, sem nenhum comunicado exibido.

---

## Edge Cases

- IF um alerta anterior tiver sido simulado com sucesso mas o comunicado ainda não foi visualizado (4.3) THEN o detalhe SHALL mostrar isso corretamente, sem confundir "simulado" com "visualizado".
- WHEN dois alertas tiverem exatamente o mesmo período THEN a ordenação da lista SHALL ser determinística (por exemplo, por `criado_em` decrescente), sem posição instável entre carregamentos.
- IF o alerta selecionado deixar de existir entre a listagem e a abertura do detalhe (situação de teste apenas, já que o histórico é imutável) THEN o detalhe SHALL responder `Não encontrado`, mesmo padrão do AC.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| ALERTAS-01 | P1: Lista de alertas distinguindo ativos e anteriores | Execute (T1) | Implementing |
| ALERTAS-02 | P1: Lista de alertas distinguindo ativos e anteriores | Execute (T1) | Implementing |
| ALERTAS-03 | P1: Detalhe do alerta com equivalência de mapa e lista | Execute (T2) | Implementing |
| ALERTAS-04 | P1: Detalhe do alerta com equivalência de mapa e lista | Execute (T4) | Implementing |
| ALERTAS-05 | P1: Isolamento por segurado e estados não simulados | Execute (T2) | Implementing |
| ALERTAS-06 | P1: Isolamento por segurado e estados não simulados | Execute (T2) | Implementing |

**ID format:** `ALERTAS-NN`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 6 total, 0 mapped to tasks, 6 unmapped ⚠️ (mapeamento ocorre na fase Tasks)

---

## Success Criteria

- [ ] Lista de alertas sempre distingue ativo/anterior por rótulo+ícone+texto
- [ ] Detalhe do alerta mostra todos os campos do AC, com mapa e lista equivalentes
- [ ] Nenhum alerta de outro segurado é acessível, direta ou indiretamente
- [ ] Evento não simulado mostra `Ainda não simulado`, nunca um comunicado antecipado
- [ ] Estado vazio de alertas mantém navegação para as demais superfícies
