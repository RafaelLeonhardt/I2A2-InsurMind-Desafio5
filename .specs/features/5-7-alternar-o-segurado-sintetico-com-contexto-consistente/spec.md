# História 5.7: Alternar o segurado sintético com contexto consistente — Specification

## Problem Statement

As Histórias 5.1–5.6 assumem "o segurado ativo" (`SEGURADO_PADRAO`, Épico 1) como identidade fixa, mas o conjunto sintético já semeia múltiplos segurados (elegível/não elegível para chuva e para granizo). Sem essa história, a pessoa demonstradora não consegue mostrar cenários diferentes no perfil Segurado sem editar dado manualmente, e não há garantia de que uma troca de segurado nunca mistura dado de um com outro nas cinco superfícies já entregues.

## Goals

- [ ] O seletor demonstrativo no perfil Segurado mostra só os segurados inequivocamente sintéticos do seed, descrito como `Visualizar como`, nunca como autenticação/login
- [ ] Trocar de segurado atualiza Visão geral, Alertas, Apólice, Comunicados e Meus Dados em conjunto para o mesmo segurado, sem alterar nenhum dado persistido de domínio
- [ ] Durante o carregamento do novo contexto, o estado `Contexto trocando` impede combinação de dado entre segurados; nenhuma superfície mantém conteúdo do segurado anterior sob o novo nome
- [ ] Falha ao carregar parte do novo contexto bloqueia ou reverte para o último contexto íntegro, com causa/impacto/próxima ação visíveis
- [ ] Nenhuma superfície do perfil Segurado expõe comando administrativo (editar regra, gerar mensagem, aprovar lote, iniciar simulação); endereço administrativo acessado diretamente retorna ao contexto correto sem representar permissão produtiva
- [ ] Voltar ao perfil Administrador reconstrói as superfícies administrativas; o segurado selecionado pode permanecer só como contexto demonstrativo, sem conceder/retirar autoridade no backend
- [ ] O seletor é operável por teclado: rótulo, opção ativa, foco e mudança anunciados; alvo mínimo de 44×44px; motivo textual quando desabilitado

## Out of Scope

| Feature | Reason |
| --- | --- |
| Conteúdo das cinco superfícies em si | Histórias 5.1–5.6 — esta história só troca qual segurado elas consultam |
| Autenticação/autorização real | Explicitamente proibido — o seletor nunca é login (ADR-0009) |
| Alternância de perfil Administrador↔Segurado | História 1.4 (Épico 1) já entrega esse mecanismo; esta história só adiciona a dimensão "qual segurado" dentro do perfil Segurado |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Onde vive o "segurado ativo" selecionado | Estado de contexto React (mesmo padrão de `PerfilContexto.tsx`, Épico 1), persistido em `localStorage` sob uma chave própria — nenhuma sessão de servidor, nenhuma tabela nova | Mesmo mecanismo já usado por `PerfilContexto` para persistir a escolha de perfil entre recarregamentos; consistente com "não é autenticação" — é preferência de demonstração local | y — decorre diretamente do padrão já estabelecido em 1.4 |
| Fonte da lista de segurados sintéticos disponíveis | Os segurados já semeados pelo conjunto sintético do Épico 1 (`semeador.py`) — endpoint novo que lista `segurados` (agora com nome/identificador, sem nenhum dado sensível), não um cadastro novo | O seed já define exatamente quais segurados existem; nenhuma criação de segurado nova é necessária ou permitida no MVP | y — decorre diretamente do conjunto sintético já existente |

**Open questions:** none — todas resolvidas ou registradas acima.

---

## User Stories

### P1: Seletor "Visualizar como" sem ambiguidade de autenticação ⭐ MVP

**User Story**: Como pessoa demonstradora, quero escolher qual segurado sintético visualizar, deixando claro que isso não é um login, para apresentar cenários diferentes com segurança e sem confundir a audiência.

**Why P1**: É o núcleo da história — sem o seletor claramente rotulado, a troca de segurado não existe ou pode ser mal interpretada como autenticação real.

**Acceptance Criteria**:

1. WHEN a pessoa abrir o seletor demonstrativo no perfil Segurado ativo THEN a interface SHALL exibir somente os segurados inequivocamente sintéticos disponíveis no seed, com a troca descrita como `Visualizar como`, nunca como autenticação ou login.

**Independent Test**: Abrir o seletor e confirmar que a lista mostra só segurados do seed (nomes claramente sintéticos) e que nenhum texto ou rótulo sugere "entrar"/"login"/"senha".

---

### P1: Troca consistente entre as cinco superfícies ⭐ MVP

**User Story**: Como pessoa demonstradora, quero que trocar de segurado atualize todas as superfícies do perfil Segurado de forma consistente, para nunca misturar dado de dois segurados na mesma tela.

**Why P1**: É a garantia central de integridade — sem ela, a troca poderia produzir uma combinação inválida e confusa de dados.

**Acceptance Criteria**:

1. WHEN outro segurado for selecionado e a transição de contexto terminar THEN Visão geral, Alertas, Apólice, Comunicados e Meus Dados SHALL refletir o mesmo segurado em conjunto, sem nenhum dado persistido de domínio ser alterado pela troca.
2. WHILE o novo contexto ainda estiver carregando THEN o estado `Contexto trocando` SHALL impedir combinações de dado entre segurados, e a interface SHALL não manter conteúdo anterior sob o novo nome.
3. IF uma falha ocorrer ao carregar parte do novo contexto e a transição não puder ser concluída consistentemente THEN a troca SHALL ser bloqueada ou revertida para o último contexto íntegro, com causa, impacto e próxima ação permanecendo visíveis.

**Independent Test**: Trocar de segurado e, durante o carregamento, confirmar que nenhuma superfície mostra dado do segurado anterior rotulado com o nome do novo; forçar falha parcial (dublê) e confirmar reversão ao contexto anterior íntegro.

---

### P1: Ausência de ações administrativas e retorno seguro ao Administrador ⭐ MVP

**User Story**: Como pessoa demonstradora, quero ter certeza de que o perfil Segurado nunca expõe uma ação administrativa, e que voltar ao Administrador funciona normalmente, para nunca confundir a audiência sobre quem pode fazer o quê.

**Why P1**: É a garantia de separação de autoridade entre os dois perfis — princípio central do produto (AD-9/ADR-0009).

**Acceptance Criteria**:

1. WHEN qualquer superfície do perfil Segurado tiver suas ações inspecionadas THEN não SHALL existir comandos para editar regras, gerar mensagens, aprovar lotes ou iniciar simulação, e endereços administrativos acessados diretamente SHALL retornar ao contexto correto sem representar permissão produtiva.
2. WHEN a pessoa voltar ao perfil Administrador THEN as superfícies administrativas SHALL reaparecer, com o segurado selecionado podendo permanecer apenas como contexto demonstrativo, e a alternância SHALL não conceder ou retirar autoridade no backend.

**Independent Test**: Inspecionar cada uma das cinco superfícies do perfil Segurado e confirmar ausência de qualquer ação administrativa; acessar diretamente um endereço administrativo estando no perfil Segurado e confirmar retorno seguro ao contexto correto.

---

### P2: Acessibilidade do seletor

**User Story**: Como pessoa demonstradora, quero operar o seletor inteiramente por teclado, com anúncios claros, para apresentar a demonstração com confiança em qualquer contexto de acessibilidade.

**Why P2**: Reforça acessibilidade sobre a mecânica já correta da P1; não bloqueia a primeira demonstração de troca bem-sucedida.

**Acceptance Criteria**:

1. WHEN o seletor for operado por teclado, navegando, escolhendo ou cancelando THEN rótulo, opção ativa, foco e mudança SHALL ser anunciados.
2. The control SHALL possuir alvo mínimo de 44×44 px e motivo textual quando desabilitado.

**Independent Test**: Navegar o seletor inteiramente por teclado (abrir, mover entre opções, confirmar e cancelar) e confirmar anúncios em cada etapa.

---

## Edge Cases

- IF a pessoa tentar selecionar o mesmo segurado já ativo THEN a troca SHALL ser tratada como uma operação válida sem efeito (sem re-disparar `Contexto trocando` desnecessariamente).
- IF o seletor for aberto sem nenhum segurado disponível (seed ausente/corrompido) THEN a interface SHALL explicar isso claramente, sem lista vazia sem explicação.
- WHEN a troca de segurado ocorrer enquanto uma ação de leitura (ex.: uma requisição de Alertas) ainda está em andamento para o segurado anterior THEN essa resposta tardia SHALL ser descartada, nunca aplicada ao novo contexto.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| SELETOR-01 | P1: Seletor "Visualizar como" sem ambiguidade de autenticação | Design | Pending |
| SELETOR-02 | P1: Troca consistente entre as cinco superfícies | Design | Pending |
| SELETOR-03 | P1: Troca consistente entre as cinco superfícies | Design | Pending |
| SELETOR-04 | P1: Troca consistente entre as cinco superfícies | Design | Pending |
| SELETOR-05 | P1: Ausência de ações administrativas e retorno seguro ao Administrador | Design | Pending |
| SELETOR-06 | P1: Ausência de ações administrativas e retorno seguro ao Administrador | Design | Pending |
| SELETOR-07 | P2: Acessibilidade do seletor | Design | Pending |
| SELETOR-08 | P2: Acessibilidade do seletor | Design | Pending |

**ID format:** `SELETOR-NN`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 8 total, 0 mapped to tasks, 8 unmapped ⚠️ (mapeamento ocorre na fase Tasks)

---

## Success Criteria

- [ ] Seletor sempre rotulado `Visualizar como`, nunca sugere login/autenticação
- [ ] Troca de segurado nunca mistura dado de dois segurados em nenhuma das cinco superfícies
- [ ] Falha parcial de carregamento sempre bloqueia ou reverte, nunca deixa contexto inconsistente
- [ ] Nenhuma ação administrativa acessível a partir do perfil Segurado, em nenhuma circunstância
- [ ] Seletor inteiramente operável por teclado, com alvo mínimo de 44×44px
