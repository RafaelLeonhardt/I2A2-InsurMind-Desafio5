# História 3.2: Gerar mensagens automaticamente para cada canal — Specification

## Problem Statement

A História 3.1 deixa a execução em `processando_mensagens` com o contexto mínimo já montado por item elegível, mas nenhuma mensagem é de fato gerada ainda. Sem esta história, não existe o agente redator que produz conteúdo adaptado a WhatsApp, e-mail e SMS — o núcleo da proposta de valor do produto (comunicação preventiva personalizada) simplesmente não existe.

## Goals

- [ ] Cada canal (WhatsApp, e-mail, SMS) tem limites exatos e configuráveis, com unidade de contagem inequívoca, validados antes e depois da geração, com casos de teste nas fronteiras
- [ ] A execução em `processando_mensagens` aciona automaticamente o agente redator para cada combinação elegível de segurado+canal, sem ação manual por mensagem
- [ ] Toda mensagem gerada permanece associada a execução, elegibilidade, evento, regra, segurado, apólice e canal de origem, com unicidade por elegibilidade+canal
- [ ] WhatsApp/SMS produzem corpo adaptado ao canal e às orientações preventivas, com campos obrigatórios e limite validados deterministicamente
- [ ] E-mail produz assunto e corpo adaptados, com os mesmos validadores determinísticos
- [ ] Saída ausente, malformada ou acima do limite é marcada inválida e impedida de seguir à crítica/simulação, com motivo persistido
- [ ] Mensagem válida persiste versão inicial, duração, modelo, prompt e métricas de uso, avançando de `gerando` para `criticando`
- [ ] Reidratar a página durante a geração reconstrói etapa e progresso dos dados persistidos, sem reenviar geração nem duplicar mensagem

## Out of Scope

| Feature | Reason |
| --- | --- |
| Avaliação crítica da mensagem gerada | História 3.3 — aqui a mensagem só é gerada e validada deterministicamente, nunca criticada por IA |
| Regeneração após reprovação e limite de 3 tentativas | História 3.4 — esta história cobre a primeira tentativa de geração de cada mensagem |
| Revisão humana e decisão de lote | História 3.5 |
| Edição manual do texto gerado | Nunca existe no MVP (AD-5/AD-6) — Marina decide, não edita |
| Suporte a canais além de WhatsApp, e-mail e SMS | Fora do escopo aprovado do MVP |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Limites exatos por canal (demonstração) | WhatsApp: 1024 caracteres; SMS: 160 caracteres (1 segmento GSM-7); E-mail: assunto 78 caracteres, corpo 2000 caracteres | Valores de referência amplamente usados por essas plataformas na prática (limite de segmento SMS GSM-7, linha de assunto recomendada por RFC 2822/convenção de e-mail, limite de mensagem de template do WhatsApp Business); documentados como default de demonstração, revisável | n — assunção técnica de valor, revisável no Design |
| Unidade de contagem | Caracteres Unicode (não bytes, não "tokens") para todos os canais, contados sobre o texto final já formatado | Unidade inequívoca e testável sem depender de codificação de transporte real (SMS-real varia por concatenação de segmentos, fora do escopo desta simulação) | y — decisão do usuário refletida no PRD (contagem "inequívoca" é o requisito explícito) |
| Onde vive a orquestração de geração (LangGraph) | Um `StateGraph` do LangGraph com um nó `gerar` por mensagem, mapeado 1:1 ao estado de mensagem já diagramado no AD-4 (`gerando`→`criticando`→...) — esta história implementa só o nó `gerar` e a validação determinística pós-geração; os demais nós (`criticar`, revisão) chegam nas histórias seguintes, que estendem o mesmo grafo | ADR-0012 já decide LangGraph para o grafo de agentes; AD-4 já publica o diagrama de estados exato que o grafo deve implementar | y — já decidido no ADR-0012/AD-4, apenas confirmado aqui |
| Formato da saída estruturada do redator | `with_structured_output` (LangChain) com um schema Pydantic por tipo de canal (`SaidaWhatsApp`/`SaidaSMS` com `corpo`; `SaidaEmail` com `assunto`+`corpo`) | Padrão atual documentado do LangChain para saída estruturada validável; evita parsing manual de texto livre do modelo | n — decisão técnica, revisável no Design |

**Open questions:** none — todas resolvidas ou registradas acima.

---

## User Stories

### P1: Limites de canal configuráveis e validados nas fronteiras ⭐ MVP

**User Story**: Como Marina, quero que cada canal tenha um limite exato e testado, para confiar que nenhuma mensagem gerada estoura o que o canal realmente suporta.

**Why P1**: É o contrato determinístico do qual toda validação de saída depende — sem ele, "válido" não tem definição objetiva.

**Acceptance Criteria**:

1. The system SHALL definir, para WhatsApp, e-mail e SMS, limites exatos e configuráveis com unidade de contagem inequívoca (caracteres Unicode do texto final).
2. The validators SHALL aplicar esses limites antes e depois da geração.
3. The test suite SHALL cobrir casos exatamente nas fronteiras de cada limite (um caractere abaixo, exatamente no limite, um caractere acima).

**Independent Test**: Validar um corpo de SMS com exatamente 160 caracteres (válido) e 161 caracteres (inválido), confirmando o resultado determinístico em ambos os casos.

---

### P1: Geração automática por combinação segurado+canal ⭐ MVP

**User Story**: Como Marina, quero que o agente redator gere automaticamente uma mensagem para cada segurado elegível em seu canal, para não precisar disparar cada geração manualmente.

**Why P1**: É o comportamento automático central da história — sem ele, a "automação" do produto não existe de fato.

**Acceptance Criteria**:

1. WHEN uma execução em `processando_mensagens` retomar o marco `publico_elegivel_formado` THEN o sistema SHALL acionar automaticamente o agente redator para cada combinação elegível de segurado e canal, sem exigir ação manual de Marina por mensagem.
2. WHEN uma geração for iniciada e sua mensagem persistida THEN a mensagem SHALL permanecer associada à execução, elegibilidade, evento, regra, segurado, apólice e canal de origem.
3. The system SHALL impedir, por restrição de unicidade, uma segunda mensagem para a mesma elegibilidade e canal.

**Independent Test**: Com dois segurados elegíveis (canais diferentes) e um contexto mínimo já montado (3.1), disparar a geração e confirmar duas mensagens criadas, cada uma associada à sua própria elegibilidade e canal, sem clique manual por item.

---

### P1: Saída estruturada por tipo de canal, validada deterministicamente ⭐ MVP

**User Story**: Como Marina, quero que cada canal produza exatamente os campos que ele precisa, validados sem depender do juízo do modelo, para nunca ver uma mensagem tecnicamente inválida avançar.

**Why P1**: É a garantia de qualidade estrutural mínima antes de qualquer avaliação de conteúdo (que só chega em 3.3).

**Acceptance Criteria**:

1. WHEN o agente redator devolver conteúdo estruturado para um canal WhatsApp ou SMS THEN a saída SHALL conter um corpo adaptado ao canal e às orientações preventivas, com campos obrigatórios e limite configurado validados deterministicamente.
2. WHEN o agente redator devolver conteúdo estruturado para o canal e-mail THEN a saída SHALL conter assunto e corpo adaptados ao contexto, com campos obrigatórios e limites configurados validados deterministicamente.
3. IF a saída for ausente, malformada ou exceder o limite configurado THEN os validadores determinísticos SHALL marcar essa versão como inválida, impedida de seguir à crítica ou simulação, com o motivo persistido para a próxima tentativa controlada.
4. WHEN uma mensagem for validada com sucesso THEN sua versão inicial, duração, modelo, prompt e métricas de uso SHALL ser persistidos, e o estado SHALL avançar de `gerando` para `criticando`.

**Independent Test**: Com um dublê do modelo configurado para devolver uma saída acima do limite de SMS, confirmar que a versão é marcada inválida com motivo persistido, sem avançar para `criticando`.

---

### P2: Reidratação sem duplicar geração

**User Story**: Como Marina, quero atualizar a página durante a geração sem que isso duplique nenhuma mensagem, para confiar na ferramenta mesmo sob uso instável de rede.

**Why P2**: Reforça robustez operacional sobre o fluxo já garantido pela P1/P2 anteriores; não bloqueia a primeira demonstração de geração bem-sucedida.

**Acceptance Criteria**:

1. WHEN a página for atualizada durante a geração THEN o frontend SHALL reconstruir etapa e progresso a partir dos dados persistidos.
2. The frontend SHALL não reenviar a geração nem duplicar mensagens ao reidratar.

**Independent Test**: Iniciar a geração, simular um recarregamento da página no meio do processo, e confirmar que o número de mensagens geradas não aumenta e o progresso exibido reflete o estado real persistido.

---

## Edge Cases

- IF o modelo devolver uma saída estruturalmente válida mas vazia (corpo em branco) THEN os validadores determinísticos SHALL tratá-la como campo obrigatório ausente, não como sucesso.
- IF dois segurados elegíveis compartilharem o mesmo canal e evento THEN cada combinação segurado+apólice+canal SHALL gerar sua própria mensagem, sem reaproveitamento de conteúdo entre elas.
- WHEN o contexto mínimo de um item (3.1) não existir por algum motivo THEN a geração desse item SHALL falhar de forma isolada, sem tentar gerar com contexto incompleto.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| GERAR-01 | P1: Limites de canal configuráveis e validados nas fronteiras | Design | Pending |
| GERAR-02 | P1: Limites de canal configuráveis e validados nas fronteiras | Design | Pending |
| GERAR-03 | P1: Limites de canal configuráveis e validados nas fronteiras | Design | Pending |
| GERAR-04 | P1: Geração automática por combinação segurado+canal | Design | Pending |
| GERAR-05 | P1: Geração automática por combinação segurado+canal | Design | Pending |
| GERAR-06 | P1: Geração automática por combinação segurado+canal | Design | Implementing |
| GERAR-07 | P1: Saída estruturada por tipo de canal, validada deterministicamente | Design | Pending |
| GERAR-08 | P1: Saída estruturada por tipo de canal, validada deterministicamente | Design | Pending |
| GERAR-09 | P1: Saída estruturada por tipo de canal, validada deterministicamente | Design | Pending |
| GERAR-10 | P1: Saída estruturada por tipo de canal, validada deterministicamente | Design | Pending |
| GERAR-11 | P2: Reidratação sem duplicar geração | Design | Pending |
| GERAR-12 | P2: Reidratação sem duplicar geração | Design | Pending |

**ID format:** `GERAR-NN`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 12 total, 0 mapped to tasks, 12 unmapped ⚠️ (mapeamento ocorre na fase Tasks)

---

## Success Criteria

- [ ] Cada canal tem limite testado exatamente nas fronteiras (abaixo/no limite/acima)
- [ ] Todos os itens elegíveis de uma execução geram mensagem automaticamente, sem clique manual por item
- [ ] Toda mensagem gerada é rastreável até execução, elegibilidade, evento, regra, segurado, apólice, canal
- [ ] Saída inválida nunca avança para `criticando`
- [ ] Recarregar a página durante a geração nunca duplica mensagem
