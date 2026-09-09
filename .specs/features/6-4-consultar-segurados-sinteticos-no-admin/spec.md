# História 6.4: Consultar segurados sintéticos no admin — Specification

## Problem Statement

O protótipo (`PeopleTable`, rota `insureds` do `adminNav`, tela "Segurados") e a imagem `02-analise-evento-regra-publico` mostram o administrador consultando a base de segurados sintéticos — nome, bairro, apólice, canal — tanto isoladamente quanto como prévia de elegibilidade. O backend já expõe essa listagem (`lista_segurados`, `src/backend/central_preventiva/adaptadores/http/lista_segurados.py`, com teste de API em `test_lista_segurados_api.py`), mas não existe, nem órfão, nenhum componente de frontend que a exiba para o Administrador — a única listagem de pessoas hoje é o `SeletorSegurado`, que pertence ao perfil Segurado e serve para "visualizar como" outro segurado, não para o admin auditar a base. Esta é a única superfície de negócio do admin que precisa ser construída do zero, não apenas religada.

## Goals

- [ ] O administrador acessa "Segurados" pela navegação (História 6.1) e vê a lista completa de segurados sintéticos com nome, bairro, apólice e canal de comunicação preferido
- [ ] A lista é filtrável/pesquisável por nome ou bairro para os cenários sintéticos com mais de uma dezena de segurados
- [ ] A partir de um segurado da lista, é possível abrir seu contexto (apólice, alertas, comunicados) na mesma perspectiva usada na História 6.2 quando ele aparece como elegível

## Out of Scope

| Feature | Reason |
| --- | --- |
| Edição/cadastro de segurados pela interface | O domínio é inteiramente sintético e semeado por restauração (Épico 1); não existe caso de uso de cadastro manual no produto |
| Exclusão de segurados | Mesmo motivo acima |
| Paginação server-side | O volume de segurados sintéticos do cenário de demonstração é pequeno (dezenas, não milhares); paginação client-side simples é suficiente e paginação server-side adicionaria complexidade sem benefício demonstrável |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Fonte de dado | `GET` de `lista_segurados` (já implementado e testado no backend) — nenhum endpoint novo | O backend já entrega exatamente os campos que o protótipo (`PeopleTable`) exibe | y — verificado em `test_lista_segurados_api.py` |
| Padrão visual/estrutural do componente novo | Segue o padrão já estabelecido pelas demais superfícies de listagem do projeto (ex.: tabela com busca simples, como a lista de destinatários de `SuperficieGeracaoMensagens`) em vez de inventar um padrão de UI novo | Consistência de UX e menor risco de divergir dos tokens visuais já usados no projeto (AD conhecido: 9 divergências de tokens já registradas em E2E-11 — não adicionar mais um padrão à parte) | y — decisão de manter consistência com o sistema visual existente |
| "Abrir o contexto do segurado" a partir da lista (Goal 3) | Reusa a mesma perspectiva de leitura já usada pela prévia de elegíveis (História 6.2) — não abre o `PainelSegurado` do perfil Segurado (que é sobre "eu, o segurado logado", não sobre "auditar um segurado qualquer" como admin) | Evita confundir a visão de autoatendimento (Épico 5) com a visão de auditoria administrativa; são propósitos e audiências diferentes mesmo reusando componentes de exibição | y — mantém a separação de perfis já estabelecida no projeto |

**Open questions:** none — todas resolvidas ou registradas acima.

---

## User Stories

### P1: Listar segurados sintéticos ⭐ MVP

**User Story**: Como administrador, quero ver a lista de segurados sintéticos com seus dados básicos (nome, bairro, apólice, canal) para ter uma visão geral da base sobre a qual as regras preventivas operam.

**Why P1**: É a capacidade central da história — sem ela, não existe tela de "Segurados" no admin.

**Acceptance Criteria**:

1. WHEN o administrador abrir "Segurados" pela navegação THEN a interface SHALL exibir uma tabela com nome, bairro, apólice e canal de comunicação preferido de cada segurado sintético retornado pela API.
2. WHILE a lista estiver vazia (nenhum segurado no cenário sintético ativo) the interface SHALL mostrar um estado vazio explícito.
3. IF a chamada à API falhar THEN a interface SHALL mostrar um erro explícito com ação de tentar novamente, nunca uma lista vazia indistinguível de "nenhum segurado".

**Independent Test**: Com o cenário sintético padrão restaurado, abrir "Segurados" e confirmar que a contagem de linhas da tabela corresponde à contagem retornada por `GET` de `lista_segurados`.

---

### P2: Buscar por nome ou bairro

**User Story**: Como administrador, quero filtrar a lista de segurados por nome ou bairro para encontrar rapidamente um segurado específico num cenário com muitos registros.

**Why P2**: Melhora usabilidade da P1, mas a lista já é útil sem busca em cenários pequenos.

**Acceptance Criteria**:

1. WHEN o administrador digitar um termo no campo de busca THEN a tabela SHALL exibir apenas os segurados cujo nome ou bairro contenham o termo, sem diferenciar maiúsculas/minúsculas.
2. WHEN o termo de busca não corresponder a nenhum segurado THEN a interface SHALL mostrar um estado "nenhum resultado" distinto do estado vazio da lista completa.

**Independent Test**: Buscar por um bairro presente no cenário sintético e confirmar que só os segurados desse bairro aparecem; buscar um termo inexistente e confirmar a mensagem de "nenhum resultado".

---

### P3: Abrir o contexto de um segurado a partir da lista

**User Story**: Como administrador, quero abrir o contexto de um segurado específico (apólice, alertas, comunicados) a partir da lista para investigar um caso pontual sem precisar trocar de perfil.

**Why P3**: Valor incremental de investigação — a lista já cumpre seu propósito de auditoria geral sem esta ação.

**Acceptance Criteria**:

1. WHEN o administrador selecionar um segurado na lista THEN a interface SHALL exibir sua apólice, alertas e comunicados em modo somente leitura, na perspectiva administrativa (não a do `PainelSegurado`).

**Independent Test**: Selecionar um segurado com ao menos um alerta e confirmar que seus dados de apólice e alertas aparecem corretamente, sem nenhuma ação de edição disponível.

---

## Edge Cases

- IF dois segurados tiverem o mesmo nome (dado sintético) THEN a lista SHALL diferenciá-los por um identificador estável (id ou apólice), nunca colapsar as duas linhas.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| LISTASEG-01 | P1: Listar segurados sintéticos | - | Pending |
| LISTASEG-02 | P1: Listar segurados sintéticos | - | Pending |
| LISTASEG-03 | P1: Listar segurados sintéticos | - | Pending |
| LISTASEG-04 | P2: Buscar por nome ou bairro | - | Pending |
| LISTASEG-05 | P2: Buscar por nome ou bairro | - | Pending |
| LISTASEG-06 | P3: Abrir o contexto de um segurado a partir da lista | - | Pending |

**ID format:** `LISTASEG-NN`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 6 total, 0 mapped to tasks, 6 unmapped ⚠️ — fase Specify apenas; Design/Tasks pendentes.

---

## Success Criteria

- [ ] Todo segurado sintético do cenário ativo aparece na lista com dados corretos
- [ ] A busca nunca omite um segurado que de fato corresponde ao termo
- [ ] O contexto aberto pelo admin nunca oferece uma ação de edição
