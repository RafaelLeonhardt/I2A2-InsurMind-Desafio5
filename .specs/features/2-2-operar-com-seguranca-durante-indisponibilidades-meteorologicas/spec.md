# História 2.2: Operar com segurança durante indisponibilidades meteorológicas — Specification

## Problem Statement

A História 2.1 entrega a coleta feliz do INMET, mas nada garante hoje o que acontece quando o INMET falha, demora ou fica fora do ar durante a demonstração. Sem tratamento explícito de indisponibilidade, uma falha temporária poderia travar a operação, criar um alerta a partir de dado obsoleto, ou deixar Marina sem um caminho de contingência para continuar demonstrando o fluxo.

## Goals

- [ ] Toda coleta aplica timeout e no máximo três tentativas totais, com espera configurável, cada uma registrada individualmente
- [ ] Os valores de intervalo, timeout, tentativas e backoff são exatos, configuráveis, documentados e justificados
- [ ] Um snapshot antigo válido continua consultável (com origem, horário e idade) mas nunca inicia nova avaliação de risco enquanto a coleta corrente falha
- [ ] Esgotadas as três tentativas, a execução termina como `falhou_coleta` com uma `Exceção` registrada, sem travar em estado intermediário
- [ ] Marina pode ativar um cenário sintético de contingência, rotulado `sintetico` e nunca combinado silenciosamente com `real_inmet`
- [ ] Uma nova tentativa após indisponibilidade cria execução correlacionada própria, sem reabrir a execução terminal anterior
- [ ] A recuperação do INMET retoma o agendamento automático sem duplicar eventos já persistidos
- [ ] A interface distingue `Operacional`, `Em tentativa`, `Degradada`, `Indisponível`, `Sintética` e `Recuperada` por texto, ícone e cor, cada uma só com ações seguras

## Out of Scope

| Feature | Reason |
| --- | --- |
| Coleta feliz, normalização e formato do evento | História 2.1 — esta história trata apenas do caminho de falha e contingência |
| Avaliação de relevância ou elegibilidade a partir do snapshot antigo | Explicitamente proibido pelos ACs: snapshot desatualizado nunca inicia nova avaliação |
| Retentativa automática ilimitada ou circuit breaker adaptativo | Fora do MVP; o limite fixo de três tentativas totais já é o mecanismo de contenção aprovado (AD-8) |
| Múltiplos cenários sintéticos simultâneos ou customização ad hoc do cenário | O conjunto demonstrativo já define os cenários sintéticos disponíveis (Épico 1); esta história só ativa um cenário existente |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Valores exatos de timeout, número de tentativas e backoff da coleta de produção | Timeout de 5 segundos por tentativa, 3 tentativas totais, backoff exponencial com jitter (1s, 2s, 4s), todos configuráveis por variável de ambiente com os mesmos valores como padrão documentado | Consistente com AD-8 ("timeout e no máximo três tentativas") e com o padrão já usado na sonda de prontidão (`TIMEOUT_SEGUNDOS`), mas com timeout de produção distinto do timeout de sonda (3s), pois a coleta real processa payload maior que o ping de saúde | n — assunção técnica, revisável no Design |
| Onde persistir tentativas individuais e o marco de exceção | Reutiliza a tabela de sincronizações criada no Design da História 2.1 para as tentativas; uma nova tabela ou coluna de `Exceção` correlacionada por `execucao_id` é adicionada no Design desta história | Consistente com AD-10 (correlação sem conteúdo sensível) e com `execucao_preventiva` sendo "casca mínima" que os Épicos 2/3 estendem | n — decisão de schema, revisável no Design |
| Cenários sintéticos de contingência disponíveis | Reutiliza os cenários sintéticos já definidos no conjunto demonstrativo do Épico 1 (`adaptadores/persistencia/semeador.py` e dados de restauração), sem criar novos cenários nesta história | A história pede para "ativar" um cenário existente, não para defini-lo; a fonte de verdade dos dados sintéticos já é o seed versionado do Épico 1 | y — decisão do usuário refletida no PRD (Épico 1 é pré-requisito explícito) |

**Open questions:** none — todas resolvidas ou registradas acima.

---

## User Stories

### P1: Retentativa limitada e configuração de resiliência documentada ⭐ MVP

**User Story**: Como Marina, quero que a coleta tente algumas vezes com tempo limitado antes de desistir, para que uma falha momentânea do INMET não trave a demonstração nem seja tratada como sucesso.

**Why P1**: É o mecanismo base de resiliência do qual dependem snapshot, terminal de falha e recuperação.

**Acceptance Criteria**:

1. WHEN a coleta ao INMET falhar por falha temporária, timeout ou resposta inválida THEN o adaptador SHALL aplicar timeout e realizar no máximo três tentativas totais, com espera configurável entre elas.
2. WHEN cada tentativa individual ocorrer THEN o sistema SHALL registrar seu número, início, término, código do resultado e correlação.
3. The system SHALL definir intervalo de coleta, timeout, número de tentativas e backoff como valores exatos, configuráveis e documentados.
4. The documentation SHALL justificar os valores padrão e descrever o comportamento observável de cada tipo de falha.
5. WHILE ainda existirem tentativas disponíveis THEN a interface de Fonte meteorológica SHALL exibir a tentativa atual e o limite de três, atualizando o progresso sem bloquear a navegação nem aparentar processamento infinito.

**Independent Test**: Configurar o adaptador dublê para falhar nas duas primeiras tentativas e responder na terceira; confirmar três tentativas registradas com seus resultados individuais e sucesso final.

---

### P1: Snapshot preservado sem novo alerta e terminal explícito de falha ⭐ MVP

**User Story**: Como Marina, quero que um snapshot antigo continue visível mas nunca dispare uma nova avaliação, e que a coleta esgotada termine de forma explícita, para nunca confundir dado desatualizado com dado atual.

**Why P1**: É a garantia central de segurança da história — impedir que dado obsoleto vire alerta.

**Acceptance Criteria**:

1. WHILE existir um último snapshot válido e uma nova coleta falhar THEN o sistema SHALL manter esse snapshot disponível apenas para consulta, acompanhado de origem, horário e idade calculada.
2. IF o snapshot antigo for consultado durante uma falha de coleta THEN o sistema SHALL não iniciar nenhuma nova avaliação de risco, alerta ou mensagem a partir dele.
3. IF as três tentativas de uma coleta esgotarem THEN a execução SHALL encerrar como `falhou_coleta` e SHALL criar uma `Exceção` com causa, tentativas e impacto operacional.
4. WHEN a execução alcançar `falhou_coleta` THEN a interface SHALL apresentar o estado `Indisponível`, mantendo o snapshot antigo claramente identificado como desatualizado.

**Independent Test**: Forçar as três tentativas a falharem, confirmar que a execução termina em `falhou_coleta` com uma `Exceção` consultável e que o snapshot anterior aparece marcado como desatualizado, sem novo evento avaliado.

---

### P1: Contingência sintética rotulada e recuperação sem duplicação ⭐ MVP

**User Story**: Como Marina, quero ativar um cenário sintético durante uma indisponibilidade real e ver o sistema se recuperar sem duplicar dados quando o INMET voltar, para continuar a demonstração com segurança e integridade.

**Why P1**: Cobre os dois lados do ciclo de contingência: entrada segura no modo sintético e saída segura de volta ao modo real.

**Acceptance Criteria**:

1. WHILE o INMET permanecer indisponível THEN Marina SHALL poder solicitar uma nova tentativa explícita, que SHALL criar uma nova execução correlacionada em `coletando`, com identificação e chave idempotente próprias, sem reabrir a execução terminal anterior nem reutilizar elegibilidade inexistente.
2. IF o comando de nova tentativa explícita for repetido acidentalmente com a mesma `Idempotency-Key` THEN o sistema SHALL não duplicar a nova operação de coleta nem seus efeitos.
3. WHEN Marina confirmar a ativação de um cenário sintético disponível no conjunto demonstrativo THEN o sistema SHALL criar uma coleta separada com proveniência `sintetico`, sem combinar silenciosamente seus registros com dados `real_inmet`.
4. WHILE um cenário sintético estiver ativo THEN qualquer evento ou superfície derivada SHALL manter sua origem sintética visível por texto e indicador acessível, explicando que o cenário serve à contingência e à reprodução da demonstração.
5. WHEN o INMET voltar a fornecer dados válidos e uma coleta real for concluída THEN o sistema SHALL registrar a recuperação e retomar o agendamento automático, sem duplicar eventos já persistidos com a mesma identidade externa ou chave determinística de conteúdo.

**Independent Test**: Com o adaptador dublê indisponível, ativar o cenário sintético e confirmar proveniência `sintetico` isolada; em seguida, fazer o dublê responder com sucesso e confirmar recuperação sem eventos duplicados.

---

### P2: Estados visíveis da fonte e cobertura de valores-limite

**User Story**: Como Marina, quero distinguir claramente cada estado da fonte meteorológica na interface, para saber que ações são seguras em cada momento.

**Why P2**: Reforça clareza operacional sobre o comportamento já garantido pelas stories P1; não bloqueia a demonstração do caminho de contingência em si.

**Acceptance Criteria**:

1. WHEN Marina abrir Monitoramento, Prontidão ou Fonte meteorológica THEN a interface SHALL distinguir `Operacional`, `Em tentativa`, `Degradada`, `Indisponível`, `Sintética` e `Recuperada` por texto, ícone e cor.
2. The interface SHALL apresentar, para cada estado da fonte, somente ações seguras e aplicáveis a esse estado.
3. The test suite SHALL cobrir recuperação antes do limite, esgotamento das três tentativas, snapshot informativo, nova tentativa, ativação sintética e recuperação real sem duplicação.
4. The test suite SHALL cobrir os valores-limite de timeout, tentativas e backoff usando dublês de tempo, sem aguardar tempo real nem chamar o INMET real.

**Independent Test**: Percorrer os seis estados com dados de teste e confirmar visualmente/programaticamente que cada um expõe um conjunto de ações distinto e seguro.

---

## Edge Cases

- IF a segunda tentativa de uma coleta ocorrer exatamente no limite do timeout configurado THEN o sistema SHALL classificá-la como falha de timeout, não como sucesso tardio.
- IF Marina tentar ativar um cenário sintético enquanto uma coleta real está em `coletando` THEN o sistema SHALL tratar a ativação como uma operação correlacionada distinta, sem interromper silenciosamente a coleta real em andamento.
- WHEN o backend reiniciar com uma execução em `coletando` de uma tentativa anterior à reinicialização THEN o sistema SHALL retomar a partir do último marco durável, sem perder a contagem de tentativas já registradas.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| RESIL-01 | P1: Retentativa limitada e configuração de resiliência documentada | Design | Verified |
| RESIL-02 | P1: Retentativa limitada e configuração de resiliência documentada | Design | Verified |
| RESIL-03 | P1: Retentativa limitada e configuração de resiliência documentada | Design | Verified |
| RESIL-04 | P1: Retentativa limitada e configuração de resiliência documentada | Design | Verified |
| RESIL-05 | P1: Retentativa limitada e configuração de resiliência documentada | Design | Verified |
| RESIL-06 | P1: Snapshot preservado sem novo alerta e terminal explícito de falha | Design | Verified |
| RESIL-07 | P1: Snapshot preservado sem novo alerta e terminal explícito de falha | Design | Verified |
| RESIL-08 | P1: Snapshot preservado sem novo alerta e terminal explícito de falha | Design | Verified |
| RESIL-09 | P1: Snapshot preservado sem novo alerta e terminal explícito de falha | Design | Verified |
| RESIL-10 | P1: Contingência sintética rotulada e recuperação sem duplicação | Design | Verified |
| RESIL-11 | P1: Contingência sintética rotulada e recuperação sem duplicação | Design | Verified |
| RESIL-12 | P1: Contingência sintética rotulada e recuperação sem duplicação | Design | Verified |
| RESIL-13 | P1: Contingência sintética rotulada e recuperação sem duplicação | Design | Verified |
| RESIL-14 | P1: Contingência sintética rotulada e recuperação sem duplicação | Design | Verified |
| RESIL-15 | P2: Estados visíveis da fonte e cobertura de valores-limite | Design | Verified |
| RESIL-16 | P2: Estados visíveis da fonte e cobertura de valores-limite | Design | Verified |
| RESIL-17 | P2: Estados visíveis da fonte e cobertura de valores-limite | Design | Verified |
| RESIL-18 | P2: Estados visíveis da fonte e cobertura de valores-limite | Design | Verified |

**ID format:** `RESIL-NN`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 18 total, 18 verified (Verifier PASS, `validation.md`, rodada 3 de 2026-09-02)

---

## Success Criteria

- [ ] Três falhas consecutivas do adaptador dublê levam a execução a `falhou_coleta` com `Exceção` consultável, sem travar em `Coletando`
- [ ] Um snapshot antigo nunca dispara avaliação de risco durante uma falha de coleta corrente
- [ ] Ativar um cenário sintético produz eventos `sintetico` nunca combinados com eventos `real_inmet`
- [ ] Após recuperação real, nenhum evento é duplicado em `eventos_meteorologicos`
- [ ] Todos os seis estados da fonte (`Operacional`, `Em tentativa`, `Degradada`, `Indisponível`, `Sintética`, `Recuperada`) são distinguíveis na interface
