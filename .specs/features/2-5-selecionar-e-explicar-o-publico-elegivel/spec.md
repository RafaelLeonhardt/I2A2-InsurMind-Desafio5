# História 2.5: Selecionar e explicar o público elegível — Specification

## Problem Statement

A História 2.3 decide que um evento é relevante e avança a execução para `avaliando_elegibilidade`, mas nada ainda decide quais segurados e apólices específicos devem receber uma comunicação preventiva. Sem essa história, não há público formado, nem explicação de por que alguém foi incluído ou excluído — pré-requisito direto para a História 2.6 (checkpoint `aguardando_geracao`) e para todo o Épico 3.

## Goals

- [ ] A elegibilidade considera apenas segurados e apólices sintéticos do conjunto demonstrativo, avaliando área afetada, tipo e situação da apólice, coberturas e participação em alertas
- [ ] O canal preferencial do segurado é preservado para a comunicação futura sem alterar o resultado dos demais critérios
- [ ] Segurado e apólice que atendem integralmente a regra geram resultado `incluido` com todos os critérios satisfeitos registrados
- [ ] Ao menos um critério não atendido gera resultado `excluido` com o resultado de cada critério e explicação objetiva das condições que impediram a inclusão
- [ ] Toda execução concluída conserva snapshots imutáveis do segurado, apólice, evento e regra usados, mesmo que os dados originais mudem depois
- [ ] A mesma combinação de execução, evento, versão de regra, segurado e apólice nunca produz mais de um resultado de elegibilidade
- [ ] Marina consulta quantidades de incluídos/excluídos e abre a explicação completa de qualquer registro sem depender de hover
- [ ] Um público vazio é um resultado válido, não uma falha técnica, e nunca aciona a OpenAI ou cria mensagem

## Out of Scope

| Feature | Reason |
| --- | --- |
| Cálculo de relevância do evento em si | História 2.3 — esta história parte de um evento já considerado relevante |
| Gestão de regras (edição, teste, versionamento) | História 2.4 — esta história apenas consome a versão de regra já ativa/snapshotada |
| Geração de mensagens para o público elegível | Épico 3 — esta história só forma e explica o público, não produz comunicação |
| Alteração de preferências de canal pelo próprio segurado | Épico 5 (perfil Segurado); aqui o canal é apenas lido, não editado |
| Uso de modelo de linguagem na seleção do público | Proibido pelo AD-5; a seleção é 100% determinística |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Origem dos dados de segurado/apólice avaliados | Reutiliza exclusivamente `segurados` e `apolices` já semeados pelo conjunto demonstrativo do Épico 1, sem nenhuma fonte adicional | AC explícito: "considerar somente segurados e apólices sintéticos existentes no conjunto demonstrativo"; o schema dessas tabelas já existe (Épico 1) | y — já decidido no schema do Épico 1, apenas confirmado aqui |
| Estrutura do registro de elegibilidade `incluido`/`excluido` | Estende a tabela `elegibilidades_historicas` já existente (`evento_id`, `regra_id`, `segurado_id`, `apolice_id`, `elegivel`, `justificativa`) com os campos adicionais necessários para o snapshot de critérios avaliados, definidos no Design | O schema (`README.md` de persistência) já tem `elegibilidades_historicas` com exatamente esse propósito; a história só formaliza o preenchimento pela execução real, além do dado pré-calculado de demonstração já existente | y — já decidido no schema do Épico 1, apenas confirmado aqui |
| Mecanismo de "nenhuma futura mensagem duplicada" | Uma restrição de unicidade (por execução, evento, versão de regra, segurado, apólice) impede mais de um resultado de elegibilidade para a mesma combinação, definida no Design junto à extensão da tabela | Consistente com AD-7 ("unicidades impedem uma segunda mensagem por elegibilidade") e com o AC de "no máximo um resultado de elegibilidade" | n — decisão de schema, revisável no Design |

**Open questions:** none — todas resolvidas ou registradas acima.

---

## User Stories

### P1: Cálculo de elegibilidade por critérios objetivos ⭐ MVP

**User Story**: Como Marina, quero que o sistema calcule automaticamente quem é elegível para um evento relevante, avaliando área, apólice, coberturas e participação em alertas, para saber objetivamente quem deve receber uma ação preventiva.

**Why P1**: É o cálculo central da história, do qual dependem os resultados `incluido`/`excluido` e todo o restante do fluxo.

**Acceptance Criteria**:

1. WHEN a elegibilidade de um evento relevante com snapshot de uma regra ativa for avaliada THEN o sistema SHALL considerar somente segurados e apólices sintéticos existentes no conjunto demonstrativo.
2. The system SHALL avaliar área afetada, tipo e situação da apólice, coberturas e participação em alertas como critérios de elegibilidade.
3. WHEN a elegibilidade de um segurado com canal preferencial definido for calculada THEN o sistema SHALL preservar esse canal para a futura preparação da comunicação, sem que ele altere o resultado dos demais critérios de elegibilidade.

**Independent Test**: Avaliar um segurado com `participa_de_alertas = false` e confirmar que essa condição por si só o exclui, independentemente do canal preferencial configurado.

---

### P1: Resultados `incluido`/`excluido` com snapshot imutável ⭐ MVP

**User Story**: Como Marina, quero que cada avaliação produza um resultado registrado e imutável, incluído ou excluído, para auditar depois exatamente por que cada decisão foi tomada, mesmo que os dados originais mudem.

**Why P1**: É a garantia de auditabilidade e integridade histórica exigida pelo AD-11.

**Acceptance Criteria**:

1. WHEN um segurado e uma apólice atenderem integralmente à regra THEN o sistema SHALL criar um resultado `incluido` associado à execução, ao evento, à versão da regra, ao segurado e à apólice, com todos os critérios registrados como satisfeitos.
2. IF ao menos um critério não for atendido THEN o sistema SHALL criar um resultado `excluido` com o resultado de cada critério, identificando objetivamente quais condições impediram a inclusão.
3. WHEN os dados originais de segurado, apólice, evento ou regra forem alterados após uma execução de elegibilidade concluída THEN a execução SHALL conservar snapshots imutáveis desse contexto, sem que sua explicação histórica seja reescrita.
4. WHILE a mesma combinação de execução, evento, versão de regra, segurado e apólice for reprocessada ou retomada THEN SHALL existir no máximo um resultado de elegibilidade, sem originar futura mensagem duplicada.

**Independent Test**: Reprocessar a mesma execução de elegibilidade duas vezes (simulando retomada) e confirmar, por contagem no banco, que existe exatamente um resultado por combinação.

---

### P2: Consulta, explicação e conjunto vazio válido

**User Story**: Como Marina, quero abrir o público avaliado de um evento, ver quantidades e critérios de cada registro, e confiar que um conjunto vazio é um resultado normal, para validar a decisão sem tratar ausência de elegíveis como erro.

**Why P2**: Reforça transparência e usabilidade sobre o cálculo já garantido pelas stories P1; não bloqueia a formação do público em si.

**Acceptance Criteria**:

1. WHEN Marina abrir Evento e decisão THEN a interface SHALL exibir as quantidades de incluídos e excluídos e uma tabela com segurado sintético, apólice, localização, canal e resultado, permitindo abrir os critérios e a justificativa de cada linha sem depender de hover.
2. WHEN Marina abrir a explicação de um registro THEN a interface SHALL exibir regra e versão, operando, valor observado, resultado e justificativa em colunas estáveis, distinguindo inclusões e exclusões por texto, ícone e cor.
3. IF nenhum registro satisfizer a regra THEN o resultado SHALL ser um conjunto vazio válido, não uma falha técnica, e o sistema SHALL não realizar nenhuma chamada à OpenAI nem criar mensagem.

**Independent Test**: Avaliar um evento cujo público potencial não atende a nenhum critério e confirmar que a execução termina com conjunto vazio válido, sem erro e sem chamada de IA registrada.

---

## Edge Cases

- IF um segurado tiver mais de uma apólice ativa na área afetada, uma elegível e outra não THEN o sistema SHALL avaliar cada combinação segurado+apólice separadamente, gerando um resultado distinto para cada uma.
- IF a área do evento cobrir parcialmente a área de risco de uma apólice THEN o sistema SHALL aplicar o mesmo critério objetivo de área definido pela regra, sem inferência probabilística.
- WHEN a avaliação de elegibilidade for retomada após uma reinicialização do backend no meio do processamento THEN o sistema SHALL continuar a partir do progresso persistido sem recriar resultados já gravados.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| ELEG-01 | P1: Cálculo de elegibilidade por critérios objetivos | Design | Verified |
| ELEG-02 | P1: Cálculo de elegibilidade por critérios objetivos | Design | Verified |
| ELEG-03 | P1: Cálculo de elegibilidade por critérios objetivos | Design | Verified |
| ELEG-04 | P1: Resultados incluído/excluído com snapshot imutável | Design | Verified |
| ELEG-05 | P1: Resultados incluído/excluído com snapshot imutável | Design | Verified |
| ELEG-06 | P1: Resultados incluído/excluído com snapshot imutável | Design | Verified |
| ELEG-07 | P1: Resultados incluído/excluído com snapshot imutável | Design | Verified |
| ELEG-08 | P2: Consulta, explicação e conjunto vazio válido | Design | Verified |
| ELEG-09 | P2: Consulta, explicação e conjunto vazio válido | Design | Verified |
| ELEG-10 | P2: Consulta, explicação e conjunto vazio válido | Design | Verified |

**ID format:** `ELEG-NN`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 10 total, 0 mapped to tasks, 10 unmapped ⚠️ (mapeamento ocorre na fase Tasks)

---

## Success Criteria

- [ ] Reprocessar a mesma combinação evento+regra+segurado+apólice nunca cria um segundo resultado de elegibilidade
- [ ] Um resultado `excluido` sempre lista objetivamente qual critério falhou
- [ ] Alterar o canal preferencial de um segurado depois de uma execução concluída não altera o resultado histórico dessa execução
- [ ] Um evento sem nenhum elegível termina com conjunto vazio válido, sem chamada à OpenAI
- [ ] A tabela de público elegível é navegável e explicável sem nenhuma interação por hover
