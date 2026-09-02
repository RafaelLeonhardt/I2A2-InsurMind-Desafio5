# História 2.3: Identificar eventos meteorológicos relevantes — Specification

## Problem Statement

As Histórias 2.1 e 2.2 entregam eventos meteorológicos normalizados e resilientes, mas nada ainda decide se um evento justifica ação preventiva. Sem uma classificação objetiva e determinística de relevância, qualquer evento normalizado poderia (ou não) avançar para elegibilidade sem critério auditável — e o AD-5 exige explicitamente que essa decisão nunca pertença a um modelo de linguagem.

## Goals

- [ ] Limiares e janelas de chuva intensa e granizo estão centralizados em configuração versionada e legível, com valores padrão e justificativa, e exemplos de fronteira inclusiva/exclusiva
- [ ] O domínio reconhece chuva intensa e granizo como eventos suportados; outros tipos são registrados como não suportados sem avançar
- [ ] A relevância é calculada comparando medidas, área, severidade e período com a regra ativa associada ao produto correto (residencial para chuva, automóvel para granizo), produzindo resultado determinístico com valores e critérios
- [ ] A mesma entrada e a mesma versão de regra sempre produzem o mesmo resultado; nenhum LLM participa da decisão
- [ ] Evento sem risco termina em `sem_risco` com código e motivo, sem criar elegibilidade, mensagem ou chamada à OpenAI
- [ ] Evento relevante avança para `avaliando_elegibilidade` preservando snapshot imutável do evento e da versão da regra usada
- [ ] Marina consulta o detalhe da decisão de risco por critério, com relevância/ausência de risco/dado inválido distinguíveis por texto, ícone e cor

## Out of Scope

| Feature | Reason |
| --- | --- |
| Coleta e normalização do evento meteorológico | História 2.1 — aqui o evento já normalizado é o ponto de partida |
| Cálculo de elegibilidade de segurados/apólices | História 2.5 — esta história só decide se o evento em si é relevante |
| Edição, teste e versionamento de regras pela interface | História 2.4 — aqui a regra ativa é apenas consumida, não gerenciada |
| Suporte a tipos de evento além de chuva intensa e granizo | Fora do MVP; eventos de outros tipos são registrados como não suportados, não avaliados |
| Qualquer uso de modelo de linguagem na decisão de risco | Proibido pelo AD-5; decisão é 100% determinística |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Valores padrão dos limiares de chuva intensa e granizo | A confirmar no Design com valores meteorologicamente plausíveis e documentados (ex.: chuva intensa por acumulado/período; granizo por ocorrência/severidade), com justificativa e exemplos de fronteira | A história exige "valores padrão da demonstração e justificativa" mas não fixa os números; fixá-los é uma decisão técnica de configuração, não uma decisão de produto nova | n — assunção técnica, revisável no Design |
| Onde vive a configuração de regras consumida por esta história | Reutiliza a tabela `regras` já existente no schema (`evento_tipo`, `limiar_meteorologico`, `area_aplicavel`, `apolice_tipo`, `versao`, `estado`), sem criar uma fonte de configuração paralela | O schema (`adaptadores/persistencia/README.md`) já define `regras` com exatamente esses campos e semântica de versionamento por substituição | y — já decidido no schema do Épico 1, apenas confirmado aqui |
| Estrutura do snapshot imutável de evento + versão de regra | Um registro específico da avaliação de risco (nova tabela ou coluna estruturada em `execucao_preventiva`/tabela filha, definida no Design) armazena o `evento_id`, `regra_id` e os valores/critérios observados no momento da avaliação | AD-11 exige que mutações futuras na regra não reescrevam a justificativa histórica; a tabela `regras` já versiona por substituição, então o snapshot só precisa referenciar a versão correta | n — decisão de schema, revisável no Design |

**Open questions:** none — todas resolvidas ou registradas acima.

---

## User Stories

### P1: Regras de relevância centralizadas e eventos suportados ⭐ MVP

**User Story**: Como Marina, quero que os limiares de chuva intensa e granizo estejam centralizados e documentados, e que o sistema reconheça apenas os tipos de evento suportados, para confiar que a triagem inicial de risco é objetiva e transparente.

**Why P1**: É a base de dados/configuração da qual todo o cálculo de relevância depende.

**Acceptance Criteria**:

1. The system SHALL centralizar os limiares e janelas de chuva intensa e granizo em configuração versionada e legível, com valores padrão da demonstração e justificativa.
2. The configuration documentation SHALL explicitar, para cada limiar, quais fronteiras são inclusivas e quais são exclusivas, com exemplos limítrofes.
3. WHEN o tipo de um evento meteorológico normalizado for avaliado THEN o domínio SHALL reconhecer chuva intensa e granizo como eventos suportados.
4. IF um evento normalizado for de um tipo diferente de chuva intensa ou granizo THEN o sistema SHALL registrá-lo como não suportado sem avançar no fluxo.

**Independent Test**: Inspecionar a configuração de regras e confirmar, para um valor imediatamente abaixo, sobre e acima de cada limiar, qual lado da fronteira é considerado relevante.

---

### P1: Cálculo determinístico de relevância por produto ⭐ MVP

**User Story**: Como Marina, quero que a relevância de um evento de chuva intensa ou granizo seja calculada de forma determinística contra a regra ativa do produto correspondente, para saber exatamente por que um evento foi ou não considerado relevante.

**Why P1**: É a decisão central da história — sem ela não há triagem objetiva de risco.

**Acceptance Criteria**:

1. WHEN a relevância de um evento de chuva intensa for calculada THEN o sistema SHALL comparar medidas, área, severidade e período com a regra ativa associada ao seguro residencial, produzindo um resultado determinístico com os valores observados e critérios aplicados.
2. WHEN a relevância de um evento de granizo for calculada THEN o sistema SHALL comparar medidas, área, severidade e período com a regra ativa associada ao seguro automóvel, produzindo um resultado determinístico com os valores observados e critérios aplicados.
3. WHILE a mesma entrada meteorológica e a mesma versão de regra forem usadas THEN uma avaliação repetida SHALL produzir exatamente o mesmo resultado e justificativa.
4. The system SHALL não permitir que nenhum modelo de linguagem, prompt ou heurística probabilística participe da decisão de relevância.

**Independent Test**: Avaliar duas vezes o mesmo evento de chuva intensa contra a mesma versão de regra e confirmar resultado e justificativa byte-a-byte idênticos.

---

### P1: Transições de estado a partir do resultado da relevância ⭐ MVP

**User Story**: Como Marina, quero que a execução avance ou termine automaticamente conforme a relevância calculada, para não precisar decidir manualmente se um evento sem risco deve seguir adiante.

**Why P1**: Fecha o ciclo determinístico da história ao estado real da máquina de estados (`ExecucaoPreventiva`).

**Acceptance Criteria**:

1. IF um evento não atingir os critérios da regra ativa THEN a execução SHALL alcançar o estado terminal `sem_risco` com código e motivo persistidos, sem criar avaliação de elegibilidade, mensagem ou chamada à OpenAI.
2. WHEN um evento atingir integralmente os critérios da regra ativa THEN a execução SHALL avançar para `avaliando_elegibilidade`, preservando um snapshot imutável do evento e da versão da regra utilizada.

**Independent Test**: Avaliar um evento abaixo do limiar e confirmar terminal `sem_risco` sem nenhuma linha criada em elegibilidade; avaliar um evento acima do limiar e confirmar transição para `avaliando_elegibilidade` com snapshot gravado.

---

### P2: Explicabilidade da decisão e progresso em tempo real

**User Story**: Como Marina, quero abrir o detalhe de qualquer decisão de risco e acompanhar seu progresso real, para explicar a qualquer momento por que um evento foi classificado como relevante, sem risco ou inválido.

**Why P2**: Reforça a auditabilidade e a transparência da decisão já tomada pelas stories P1; não bloqueia o cálculo de relevância em si.

**Acceptance Criteria**:

1. WHEN Marina abrir o detalhe do evento THEN a interface SHALL exibir o operando, o valor observado, o resultado e a justificativa de cada critério da decisão de risco.
2. The interface SHALL distinguir relevância, ausência de risco e dados inválidos por texto, ícone e cor.
3. WHILE a avaliação estiver em processamento THEN o progresso exibido SHALL refletir a etapa real da máquina de estados, e o frontend SHALL não recalcular relevância nem antecipar um resultado.

**Independent Test**: Abrir o detalhe de um evento avaliado como não relevante e confirmar que cada critério mostra operando, valor observado e justificativa, sem nenhum cálculo replicado no frontend.

---

## Edge Cases

- IF um evento estiver exatamente no valor-limite de um limiar marcado como fronteira inclusiva THEN o sistema SHALL classificá-lo como relevante.
- IF um evento estiver exatamente no valor-limite de um limiar marcado como fronteira exclusiva THEN o sistema SHALL classificá-lo como não relevante.
- WHEN um evento chegar sem a área aplicável reconhecida pela regra ativa THEN o sistema SHALL tratá-lo como não relevante, registrando o motivo, e não como erro técnico.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| RISCO-01 | P1: Regras de relevância centralizadas e eventos suportados | Design | Implementing |
| RISCO-02 | P1: Regras de relevância centralizadas e eventos suportados | Design | Implementing |
| RISCO-03 | P1: Regras de relevância centralizadas e eventos suportados | Design | Implementing |
| RISCO-04 | P1: Regras de relevância centralizadas e eventos suportados | Design | Implementing |
| RISCO-05 | P1: Cálculo determinístico de relevância por produto | Design | Implementing |
| RISCO-06 | P1: Cálculo determinístico de relevância por produto | Design | Implementing |
| RISCO-07 | P1: Cálculo determinístico de relevância por produto | Design | Implementing |
| RISCO-08 | P1: Cálculo determinístico de relevância por produto | Design | Implementing |
| RISCO-09 | P1: Transições de estado a partir do resultado da relevância | Design | Implementing |
| RISCO-10 | P1: Transições de estado a partir do resultado da relevância | Design | Implementing |
| RISCO-11 | P2: Explicabilidade da decisão e progresso em tempo real | Design | Implementing |
| RISCO-12 | P2: Explicabilidade da decisão e progresso em tempo real | Design | Implementing |
| RISCO-13 | P2: Explicabilidade da decisão e progresso em tempo real | Design | Implementing |

**ID format:** `RISCO-NN`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 13 total, 0 mapped to tasks, 13 unmapped ⚠️ (mapeamento ocorre na fase Tasks)

---

## Success Criteria

- [ ] Dois eventos idênticos avaliados contra a mesma versão de regra produzem resultado e justificativa idênticos
- [ ] Nenhum caminho de decisão de risco chama a OpenAI ou qualquer modelo de linguagem
- [ ] Evento sem risco termina em `sem_risco` sem criar elegibilidade, mensagem ou chamada de IA
- [ ] Evento relevante avança para `avaliando_elegibilidade` com snapshot imutável do evento e da regra
- [ ] Testes automatizados cobrem exatamente as fronteiras inclusivas e exclusivas configuradas
