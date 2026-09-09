# História 6.1: Navegar o painel administrativo e monitorar eventos climáticos — Specification

## Problem Statement

O protótipo navegável (`docs/design/prototype`, tela `AdminHome`/imagem `01-monitoramento-climatico-administrador`) mostra um administrador chegando a uma visão geral com a lista de eventos climáticos detectados e o fluxo automático de tratamento. Hoje, o perfil Administrador da aplicação real só alcança três superfícies técnicas (`prontidao`, `restaurar-dados-sinteticos`, `documentacao-api` — `src/frontend/src/contexto/PerfilContexto.tsx`); não existe navegação lateral própria do admin nem qualquer tela que liste eventos meteorológicos ou execuções preventivas em andamento. O backend (`meteorologia`, `dados_sinteticos`, `execucao_preventiva`) já expõe quase todos esses dados — falta apenas um pequeno campo de vínculo evento→execução (ver Assumptions). Sem esta história, "logar como Administrador" na aplicação real não mostra nenhuma capacidade de negócio — só telas de operação/infra.

## Goals

- [ ] O perfil Administrador ganha navegação lateral própria (espelhando `adminNav` do protótipo: Eventos climáticos, Regras de negócio, Segurados, Comunicações, Fontes de dados), substituindo a lista fixa de 3 superfícies técnicas por uma que também alcança as de negócio
- [ ] A tela "Eventos climáticos" lista os eventos meteorológicos relevantes identificados e, para cada um, a execução preventiva correspondente (quando existir), permitindo abrir o acompanhamento da execução (História 6.2)
- [ ] Um evento sem execução preventiva associada (ainda não processado) é distinguível visualmente de um já em andamento ou concluído

## Out of Scope

| Feature | Reason |
| --- | --- |
| Mapa geográfico de severidade (visual de mapa da imagem 01) | O protótipo usa um mapa ilustrativo estático sem dado real por trás; a aplicação real não tem coordenadas/geometria de área monitorada persistidas (`areas_monitoradas_inmet` mapeia código de estação, não polígono) — reproduzir o mapa exigiria um dado que não existe hoje |
| Disparo manual de nova coleta a partir desta tela | Coberto por `meteorologia`/`SuperficieFonteMeteorologica` (História 6.7), não duplicado aqui |
| Detalhe da decisão do evento (evidências, condições da regra, elegíveis) | História 6.2 — esta tela só lista e navega, não explica a decisão |
| Telas "Usuários e perfis" e "Configurações" vistas na imagem `10-edicao-regra-negocio` | Aparecem só nessa imagem isolada, ausentes do protótipo interativo (`App.jsx`) e de qualquer `.specs/features` existente; não há especificação de produto por trás — ficam de fora até confirmação explícita de escopo |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Fonte de dado da lista de eventos | `GET /eventos` (`meteorologia`) já existe e será a base da lista, mas `RespostaEvento` hoje não tem um campo que ligue o evento à sua execução preventiva, e não existe um endpoint para listar execuções — não há, hoje, como montar "evento + status da execução" só com a API existente. Esta história inclui uma pequena extensão aditiva do backend: `RespostaEvento` ganha `execucao_id: UUID \| None`, preenchido por um `JOIN`/consulta adicional no repositório de eventos contra a tabela de execuções (nulo quando o evento ainda não gerou execução) | Verificado por leitura direta de `meteorologia.py` (`RespostaEvento`, sem `execucao_id`) e `execucao_preventiva.py` (só `POST /execucoes` e `GET /execucoes/{id}`, sem listagem) — corrige a Assumption original desta spec, que presumia isso já disponível. É uma extensão aditiva (um campo opcional a mais numa resposta já existente), não uma mudança de contrato quebrando consumidores atuais (`extra="forbid"` nos modelos não impede adicionar um campo novo com default) | y — corrigido durante a fase de Design com evidência de código; ver `design.md` desta história |
| Estrutura de navegação | Um componente de navegação lateral por perfil (análogo a `NavegacaoLateral` já usado, hoje genérico) ganha uma variante/seção para os itens do admin, decidida na fase de Design | Este é o ponto de maior ambiguidade arquitetural do Épico 6 inteiro (como `SUPERFICIES_POR_PERFIL` e `NavegacaoLateral` crescem sem quebrar as 3 superfícies técnicas já existentes) — fica para a fase de Design de 6.1, não travado prematuramente na Specify | y — decisão de arquitetura adiada corretamente para Design |
| Itens elegíveis para "lista de eventos" | Mostra eventos com `relevante = true` (RISCO-12/13) por padrão, com indicação separada para os `sem_risco`/`dado_invalido` já registrados, sem escondê-los completamente | O protótipo (`AdminHome`) só mostra eventos relevantes; mas o backend registra as três categorias (`SuperficieEventoDecisao`), e esconder as outras duas perderia transparência sobre por que um evento não gerou execução | y — segue o padrão de transparência já estabelecido em 2.3/2.5 |

**Open questions:** none — todas resolvidas ou registradas acima.

---

## User Stories

### P1: Painel do administrador com navegação própria ⭐ MVP

**User Story**: Como administrador, quero uma navegação lateral com as áreas de negócio do meu perfil (Eventos climáticos, Regras de negócio, Segurados, Comunicações, Fontes de dados) para acessar qualquer uma delas sem depender da URL/estado técnico.

**Why P1**: É o pré-requisito de toda a integração do Épico 6 — sem navegação própria, nenhuma das outras superfícies (6.2–6.7) fica alcançável por um usuário real.

**Acceptance Criteria**:

1. WHEN o perfil ativo for Administrador THEN a navegação lateral SHALL exibir os itens Eventos climáticos, Regras de negócio, Segurados, Comunicações e Fontes de dados, além dos itens técnicos já existentes (Prontidão, Restaurar dados sintéticos, Documentação da API).
2. WHEN o administrador selecionar "Eventos climáticos" THEN a superfície ativa SHALL trocar para a lista de eventos climáticos sem recarregar a página.
3. The navegação SHALL continuar restrita às superfícies válidas do perfil ativo — nenhum item do perfil Segurado SHALL aparecer para o Administrador, e vice-versa.

**Independent Test**: Alternar para o perfil Administrador, confirmar que a navegação lateral mostra os 5 itens de negócio + os 3 técnicos, e que clicar em "Eventos climáticos" troca o conteúdo principal sem erro.

---

### P1: Lista de eventos climáticos identificados ⭐ MVP

**User Story**: Como administrador, quero ver a lista de eventos meteorológicos identificados como relevantes, com a execução preventiva correspondente, para saber quais exigem atenção ou acompanhamento.

**Why P1**: É o ponto de entrada de todo o fluxo de negócio do admin — sem ele, as Histórias 6.2 em diante não têm como ser alcançadas a partir de um evento real.

**Acceptance Criteria**:

1. WHEN o administrador abrir "Eventos climáticos" THEN a lista SHALL exibir cada evento identificado com tipo, área, severidade derivada e status da execução preventiva associada (não iniciada, em andamento, concluída ou com falha).
2. WHEN um evento tiver uma execução preventiva associada THEN a lista SHALL oferecer uma ação para abrir o acompanhamento dessa execução (História 6.2).
3. IF um evento não tiver execução preventiva associada ainda THEN a lista SHALL indicar isso explicitamente, sem simular ou inferir uma execução inexistente.
4. WHILE a lista estiver vazia (nenhum evento identificado no cenário sintético ativo) the interface SHALL mostrar um estado vazio explícito, nunca uma tabela em branco sem explicação.

**Independent Test**: Com o cenário sintético padrão restaurado, abrir "Eventos climáticos" e confirmar que ao menos um evento relevante aparece com sua execução associada navegável, e que um evento `sem_risco`/`dado_invalido` (se presente no cenário) aparece distinguido, não escondido.

---

## Edge Cases

- IF a chamada às APIs de eventos/execuções falhar (rede/servidor) THEN a lista SHALL mostrar um erro explícito com ação de tentar novamente, nunca uma lista vazia indistinguível de "nenhum evento".
- WHEN dois eventos do mesmo tipo e área ocorrerem em instantes próximos (deduplicados por `UNIQUE`, AD-010) THEN a lista SHALL mostrar apenas o evento persistido, sem duplicata.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| ADMNAV-01 | P1: Painel do administrador com navegação própria | - | Pending |
| ADMNAV-02 | P1: Painel do administrador com navegação própria | - | Pending |
| ADMNAV-03 | P1: Painel do administrador com navegação própria | - | Pending |
| ADMNAV-04 | P1: Lista de eventos climáticos identificados | T1/T2/T7/T8 | In Tasks (T1–T3 done) |
| ADMNAV-05 | P1: Lista de eventos climáticos identificados | T6/T8 | In Tasks (backend pronto — T1–T3) |
| ADMNAV-06 | P1: Lista de eventos climáticos identificados | - | Pending |
| ADMNAV-07 | P1: Lista de eventos climáticos identificados | - | Pending |

**ID format:** `ADMNAV-NN`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 7 total, 0 mapped to tasks, 7 unmapped ⚠️ — fase Specify apenas; Design/Tasks pendentes.

---

## Success Criteria

- [ ] Um administrador consegue navegar do login até uma decisão de evento sem sair da interface (sem depender da API/Swagger)
- [ ] Todo evento identificado no cenário sintético aparece na lista, com status de execução correto
- [ ] Nenhum item de navegação do perfil errado aparece cruzado entre Administrador e Segurado
