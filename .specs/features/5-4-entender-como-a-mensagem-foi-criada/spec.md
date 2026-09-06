# História 5.4: Entender como a mensagem foi criada — Specification

## Problem Statement

Toda a proveniência agêntica (3.4) e a explicação de risco/elegibilidade (2.3/2.5) já existem no backend, mas nada ainda as traduz numa explicação acessível ao próprio Carlos. Sem essa história, o "Como esta mensagem foi criada" — a peça central de confiança e transparência do produto para o segurado — não existe, e Carlos não tem como distinguir o que foi decidido por regra determinística do que foi produzido por IA.

## Goals

- [ ] Abrir "Como esta mensagem foi criada" mostra fonte meteorológica, dados do evento e versão da regra preventiva aplicada, distinguindo claramente critérios determinísticos de atividades de IA
- [ ] A explicação agêntica descreve em linguagem acessível os papéis do agente redator e do agente crítico, mostrando decisão crítica, tentativas e aprovação humana correspondentes
- [ ] O contexto minimizado mostra categorias de dados utilizadas e não utilizadas, sem documentos, dados financeiros, pagamentos, credenciais ou prompt completo
- [ ] A prévia da mensagem final simulada corresponde exatamente à versão aprovada e simulada, informando que a comunicação é privada, simulada e não constitui alerta oficial
- [ ] Proveniência parcialmente indisponível ou com exceção histórica mostra `Procedência parcial`/`Exceção` com o que está e não está disponível, sem preencher lacunas com inferência ou dado fixo
- [ ] O drawer explicativo prende o foco, `Esc` fecha e devolve o foco à origem, com título sempre visível e sem segunda camada modal

## Out of Scope

| Feature | Reason |
| --- | --- |
| Lista/histórico de comunicados | História 5.5 — esta história é a explicação de um comunicado já aberto, não a lista |
| Consulta de alertas/apólice em si | Histórias 5.1–5.3 — referenciadas pela explicação, não reimplementadas aqui |
| Edição de qualquer conteúdo | Nunca existe — a explicação é só leitura |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Fonte de toda a explicação | Reusa integralmente `ServicoDetalheResultado` (4.2) como base, com uma camada de tradução para linguagem acessível ao segurado — nenhuma consulta nova ao banco além das já existentes de 2.3/2.5/3.2/3.3/3.4/3.5 | 4.2 já junta exatamente os mesmos dados (evento, regra, versões, críticas, decisão humana) que esta história precisa exibir; a diferença é só a audiência (Carlos vs. Marina) e a linguagem, não a fonte de dado | y — decorre diretamente do dado já agregado por 4.2 |

**Open questions:** none — todas resolvidas ou registradas acima.

---

## User Stories

### P1: Explicação completa com separação determinístico/IA ⭐ MVP

**User Story**: Como Carlos, quero entender de onde veio minha mensagem — o evento, a regra, os agentes envolvidos e a aprovação humana — para confiar no processo sem confundir decisão automática com IA.

**Why P1**: É o núcleo da história — sem ela, a transparência prometida pelo produto não chega ao segurado.

**Acceptance Criteria**:

1. WHEN Carlos abrir "Como esta mensagem foi criada" para um comunicado pertencente a ele THEN a interface SHALL exibir fonte meteorológica, dados do evento e versão da regra preventiva aplicada, distinguindo claramente critérios determinísticos de atividades realizadas por IA.
2. WHEN a mensagem tiver sido gerada e criticada THEN a explicação agêntica SHALL descrever em linguagem acessível os papéis do agente redator e do agente crítico, mostrando a decisão crítica, as tentativas e a aprovação humana correspondentes.

**Independent Test**: Abrir a explicação de um comunicado que passou por 2 tentativas antes da aprovação, e confirmar que evento/regra (determinístico) e redator/crítico/tentativas/aprovação humana (agêntico) aparecem claramente separados.

---

### P1: Contexto minimizado e prévia fiel sem promessa oficial ⭐ MVP

**User Story**: Como Carlos, quero ver exatamente quais categorias de dado foram usadas na minha mensagem, e que a prévia mostrada seja idêntica à que foi de fato simulada, para confiar que nada indevido foi compartilhado nem inventado.

**Why P1**: É a garantia de minimização de dados (AD-9) e de fidelidade de conteúdo chegando à ponta final da experiência.

**Acceptance Criteria**:

1. WHEN Carlos consultar os dados envolvidos no contexto minimizado usado pela IA THEN a interface SHALL exibir as categorias utilizadas e não utilizadas, sem documentos, informações financeiras, pagamentos, credenciais ou prompt completo aparecendo em nenhum momento.
2. WHEN a prévia da mensagem final simulada for apresentada THEN ela SHALL corresponder à versão efetivamente aprovada e simulada, informando que a comunicação é privada, simulada e não constitui alerta oficial.

**Independent Test**: Abrir o contexto minimizado de um comunicado e confirmar que só as categorias permitidas (evento, localização aproximada, coberturas relevantes, canal, orientações) aparecem, nunca um campo fora dessa lista; comparar a prévia exibida com o `conteudo` da versão aprovada persistida e confirmar identidade.

---

### P1: Procedência parcial/exceção sem inferência preenchida ⭐ MVP

**User Story**: Como Carlos, quero que, se parte da explicação estiver indisponível, isso seja dito claramente em vez de preenchido com um palpite, para nunca confiar em algo que não é real.

**Why P1**: É a garantia de honestidade sobre lacunas de dado — um princípio já aplicado em todo o projeto (nunca dado fixo mascarando indisponibilidade).

**Acceptance Criteria**:

1. IF parte da proveniência estiver indisponível ou existir uma exceção histórica associada THEN a explicação SHALL apresentar `Procedência parcial` ou `Exceção` com o que está e o que não está disponível, sem preencher lacunas com inferências ou dados fixos.

**Independent Test**: Abrir a explicação de um comunicado cuja avaliação crítica de uma tentativa intermediária não foi persistida (dado de teste simulando lacuna) e confirmar que a seção correspondente mostra `Procedência parcial` explicitamente, sem inventar o dado ausente.

---

### P2: Navegação acessível do drawer explicativo

**User Story**: Como Carlos, quero navegar a explicação inteiramente por teclado, com foco preso e `Esc` previsível, para usar a ferramenta com a tecnologia assistiva que eu precisar.

**Why P2**: Reforça acessibilidade sobre o conteúdo já correto da P1; não bloqueia a primeira demonstração da explicação em si.

**Acceptance Criteria**:

1. WHEN o drawer explicativo for aberto e Carlos navegar por teclado THEN o foco SHALL permanecer preso, `Esc` SHALL fechar a camada e o foco SHALL voltar à origem.
2. The title SHALL permanecer visível durante toda a navegação, e nenhuma segunda camada modal SHALL poder ser aberta.

**Independent Test**: Abrir o drawer por teclado, confirmar que `Tab` não sai dele, e que `Esc` fecha e devolve o foco ao controle que o abriu.

---

## Edge Cases

- IF uma mensagem nunca chegou a `criticando` (falhou na primeira geração, `falhou_integracao_ia`) THEN a explicação agêntica SHALL mostrar isso como exceção, sem seção de crítica vazia parecendo incompleta por engano.
- IF a mensagem tiver sido regenerada por decisão humana (3.5), não só pelo ciclo automático (3.4) THEN a explicação SHALL distinguir claramente qual regeneração foi automática e qual foi solicitada por decisão humana.
- WHEN o comunicado consultado pertencer a uma execução correlacionada (retentativa) THEN a explicação SHALL indicar isso, sem misturar proveniência da execução de origem com a da retentativa.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| EXPLICACAO-01 | P1: Explicação completa com separação determinístico/IA | T1/T2/T3 | ✅ Verified |
| EXPLICACAO-02 | P1: Explicação completa com separação determinístico/IA | T1/T2/T3 | ✅ Verified |
| EXPLICACAO-03 | P1: Contexto minimizado e prévia fiel sem promessa oficial | T1/T2/T3 | ✅ Verified |
| EXPLICACAO-04 | P1: Contexto minimizado e prévia fiel sem promessa oficial | T1/T2/T3 | ✅ Verified |
| EXPLICACAO-05 | P1: Procedência parcial/exceção sem inferência preenchida | T1/T2/T3 | ✅ Verified |
| EXPLICACAO-06 | P2: Navegação acessível do drawer explicativo | T3 | ✅ Verified |
| EXPLICACAO-07 | P2: Navegação acessível do drawer explicativo | T3 | ✅ Verified |

**ID format:** `EXPLICACAO-NN`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 7 total, 7 mapped to tasks, 0 unmapped — verified by `.specs/features/5-4-entender-como-a-mensagem-foi-criada/validation.md` (2026-09-06)

---

## Success Criteria

- [ ] Explicação sempre separa visualmente critério determinístico de atividade de IA
- [ ] Contexto minimizado nunca mostra campo fora da lista permitida
- [ ] Prévia da mensagem final é idêntica ao conteúdo realmente aprovado e simulado
- [ ] Lacuna de proveniência sempre mostra `Procedência parcial`/`Exceção`, nunca inferência
- [ ] Drawer com foco preso, `Esc` funcional, nunca mais de uma camada modal
