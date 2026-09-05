# História 4.3: Registrar a primeira visualização do comunicado — Specification

## Problem Statement

As Histórias 3.6/4.1/4.2 entregam entregas simuladas consultáveis por Marina, mas nada ainda permite que Carlos (o segurado sintético) abra seu próprio comunicado nem produz evidência de que ele foi de fato visto. Sem essa história, o produto não tem a ponta final da comunicação preventiva — a experiência de quem recebe — nem a evidência auditável de visualização que o Épico 5 (perfil Segurado) vai construir em cima.

## Goals

- [ ] Carlos abrir efetivamente o comunicado de uma entrega em `Enviada — simulação` registra, no backend, uma única transição para `Visualizada no portal`, com data/hora da primeira visualização persistida em UTC
- [ ] Reabrir ou atualizar a página de um comunicado já visualizado mantém o conteúdo disponível, sem criar nova entrega, mensagem, transição ou data de primeira visualização
- [ ] Duas aberturas concorrentes do mesmo comunicado registram a primeira visualização numa única transação; ambas as respostas convergem para o mesmo estado persistido
- [ ] Tentativa de abrir como comunicado uma mensagem ainda não simulada, rejeitada, excluída ou em exceção é recusada com erro de domínio explícito, sem criar marco de visualização
- [ ] O comunicado renderizado mostra conteúdo, canal, natureza simulada e linha do tempo disponível, sem ação administrativa nem sugestão de entrega confirmada por provedor
- [ ] Falha local ao registrar a visualização preserva um estado de erro consultável, permite reabertura idempotente, e nunca antecipa visualmente `Visualizada no portal`

## Out of Scope

| Feature | Reason |
| --- | --- |
| Demais superfícies do perfil Segurado (alertas, apólice, preferências) | Épico 5 — esta história cobre só a abertura do comunicado e o marco de primeira visualização |
| Ações administrativas sobre o comunicado | Explicitamente proibido pelo AC — o perfil Segurado nunca administra |
| Linha do tempo completa da execução (visão de Marina) | História 4.4 — aqui só a "linha do tempo disponível" do próprio comunicado é exibida a Carlos, não a execução inteira |
| Autenticação real de segurados | Fora do MVP (ADR-0009); o contexto demonstrativo do Épico 1 já resolve "qual segurado está agindo" |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Identidade de "Carlos" no ambiente local | O segurado sintético selecionado no contexto demonstrativo do Épico 1 (`AlternarSeguradoSintetico`, História 1.4/5.7) — nenhum sistema de login novo | O projeto já resolve "qual perfil e qual segurado sintético está ativo" via o contexto demonstrativo; esta história só consome essa identidade já existente | y — decorre do escopo já fixado pelo Épico 1 |
| Definição de "abrir efetivamente" (não só navegar para a rota) | O evento de visualização é registrado quando o conteúdo do comunicado é de fato renderizado na tela (chamada explícita do frontend ao backend após o componente montar com sucesso), não apenas ao navegar para a URL | Evita registrar uma "visualização" por um `GET` de pré-carregamento, prefetch de rota, ou erro de renderização antes do conteúdo aparecer | n — decisão técnica, revisável no Design |
| Mecanismo de concorrência da primeira visualização | `INSERT ... ON CONFLICT DO NOTHING` (ou equivalente DuckDB) numa tabela com `UNIQUE(entrega_simulada_id)`, dentro de uma única transação — a primeira chamada que chega grava, as demais leem a linha já existente | É o mecanismo mais simples e correto para "duas aberturas concorrentes convergem para o mesmo estado", sem exigir lock explícito adicional | n — decisão técnica, revisável no Design |

**Open questions:** none — todas resolvidas ou registradas acima.

---

## User Stories

### P1: Primeira visualização registrada uma única vez ⭐ MVP

**User Story**: Como Carlos, quero abrir meu comunicado e saber que isso fica registrado como evidência, para confiar que a demonstração reflete de fato minha experiência de leitura.

**Why P1**: É o núcleo da história — sem essa marca, não há evidência de visualização alguma.

**Acceptance Criteria**:

1. WHEN Carlos abrir efetivamente o comunicado de uma entrega em `Enviada — simulação` no perfil Segurado THEN o backend SHALL registrar uma única transição para `Visualizada no portal`, persistindo data e hora da primeira visualização em UTC.
2. WHEN Carlos reabrir ou atualizar a página de um comunicado já visualizado THEN o conteúdo SHALL continuar disponível, e nenhuma nova entrega, mensagem, transição ou data de primeira visualização SHALL ser criada.
3. WHEN duas aberturas concorrentes do mesmo comunicado forem processadas THEN uma única transação SHALL registrar a primeira visualização, e ambas as respostas SHALL convergir para o mesmo estado persistido.

**Independent Test**: Abrir o mesmo comunicado duas vezes seguidas e confirmar, por consulta direta ao banco, que existe exatamente uma linha de visualização, com a mesma data/hora nas duas respostas.

---

### P1: Recusa de estados não elegíveis e apresentação sem ação administrativa ⭐ MVP

**User Story**: Como Carlos, quero abrir só comunicados que de fato me foram enviados na simulação, apresentados de forma clara e honesta, para nunca ver algo que não deveria existir ou que sugira uma ação que não é minha.

**Why P1**: É a garantia de integridade de domínio e de escopo do perfil Segurado.

**Acceptance Criteria**:

1. IF uma mensagem ainda não simulada, rejeitada, excluída ou em exceção for aberta como comunicado THEN a operação SHALL ser recusada com um erro de domínio explícito, sem criar nenhum marco de visualização.
2. WHEN o detalhe do comunicado for renderizado THEN a interface SHALL apresentar conteúdo, canal, natureza simulada e linha do tempo disponível, sem oferecer ações administrativas nem sugerir entrega confirmada por provedor.

**Independent Test**: Tentar abrir como comunicado uma mensagem em `falhou_conteudo` e confirmar erro de domínio explícito, sem nenhum registro de visualização criado.

---

### P2: Falha local sem antecipação visual do estado

**User Story**: Como Carlos, quero que uma falha técnica ao registrar minha visualização não me deixe com uma tela confusa nem finja que já foi registrada, para confiar no que a tela mostra.

**Why P2**: Reforça honestidade operacional sobre o núcleo já garantido pela P1; não bloqueia a primeira demonstração de visualização bem-sucedida.

**Acceptance Criteria**:

1. IF o registro de visualização falhar localmente e o conteúdo não puder ser marcado com segurança THEN a interface SHALL preservar um estado de erro consultável e SHALL permitir nova abertura idempotente.
2. The interface SHALL nunca antecipar visualmente o estado `Visualizada no portal` antes da confirmação real do backend.

**Independent Test**: Forçar uma falha local no registro de visualização (dublê de repositório) e confirmar que a interface mostra um estado de erro, não `Visualizada no portal`, e que reabrir a página tenta de novo com segurança.

---

## Edge Cases

- IF uma entrega simulada pertencer a um canal e-mail mas Carlos abrir pelo perfil Segurado independentemente do canal original THEN a primeira visualização SHALL ser registrada da mesma forma, já que o marco é sobre o comunicado no portal, não sobre o canal simulado original.
- WHEN Carlos alternar para outro segurado sintético (Épico 5, História 5.7) e abrir um comunicado desse outro segurado THEN a visualização SHALL ser registrada e consultada isoladamente por segurado, nunca misturada entre perfis sintéticos.
- IF duas visualizações concorrentes ocorrerem exatamente no mesmo milissegundo THEN o mecanismo de unicidade (`UNIQUE`/`ON CONFLICT`) SHALL garantir apenas uma linha persistida, sem depender de ordenação de chegada específica.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| VISU-01 | P1: Primeira visualização registrada uma única vez | Execute (T1, T2, T5) | Verified |
| VISU-02 | P1: Primeira visualização registrada uma única vez | Execute (T2, T5) | Verified |
| VISU-03 | P1: Primeira visualização registrada uma única vez | Execute (T2) | Verified |
| VISU-04 | P1: Recusa de estados não elegíveis e apresentação sem ação administrativa | Execute (T3, T4) | Verified |
| VISU-05 | P1: Recusa de estados não elegíveis e apresentação sem ação administrativa | Execute (T3, T4) | Verified |
| VISU-06 | P2: Falha local sem antecipação visual do estado | Execute (T5) | Verified |
| VISU-07 | P2: Falha local sem antecipação visual do estado | Execute (T5) | Verified |

**ID format:** `VISU-NN`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 7 total, 7 mapped to tasks (T1, T2, T3, T4, T5), 7 verified

---

## Success Criteria

- [ ] Abrir um comunicado pela primeira vez sempre cria exatamente uma visualização com data/hora UTC
- [ ] Reabrir ou concorrer duas aberturas nunca cria uma segunda visualização
- [ ] Mensagem não elegível (não simulada/rejeitada/excluída/exceção) sempre recusa com erro de domínio, sem marco criado
- [ ] Comunicado renderizado nunca mostra ação administrativa nem confirmação de provedor real
- [ ] Falha local nunca antecipa `Visualizada no portal`
