# História 2.6: Encerrar ou encaminhar a execução preventiva — Specification

## Problem Statement

As Histórias 2.1–2.5 entregam, isoladamente, coleta, resiliência, relevância e elegibilidade — mas nada ainda as encadeia automaticamente numa única `ExecucaoPreventiva` observável, do jeito que o AD-4 e o AD-7 exigem (uma execução, uma máquina de estados, persistida e retomável). Sem este *runner*, Marina precisaria disparar cada etapa manualmente e não teria um único lugar para ver se a execução terminou sem risco, sem elegíveis, ou está pronta para o Épico 3 gerar mensagens.

## Goals

- [ ] Uma coleta meteorológica válida dispara automaticamente normalização, avaliação de relevância e, quando aplicável, cálculo de elegibilidade, sem cliques intermediários, com cada transição persistida como marco correlacionado
- [ ] Evento sem risco e evento relevante sem elegíveis terminam, respectivamente, em `sem_risco` e `sem_elegiveis`, com causas e contagens consultáveis, sem criar mensagem, simulação ou chamada à OpenAI
- [ ] Evento relevante com público elegível persiste o marco `publico_elegivel_formado` e transiciona atomicamente para `aguardando_geracao`, encerrando a etapa determinística como `Pronto para geração`, sem exigir ação humana e sem criar mensagens
- [ ] Marina vê quantidade total e prévia do público (segurado, apólice, localização, canal, motivo) ao abrir a execução, com acesso à explicação completa antes de qualquer geração
- [ ] Qualquer um dos três resultados determinísticos é reconstruído do DuckDB ao atualizar a página ou reidratar a execução, sem recalcular ou duplicar
- [ ] Uma execução reidratada em `aguardando_geracao` reutiliza o público preservado sem recálculo quando o fluxo completo retomar a fase de IA, com preflight automático protegido por idempotência
- [ ] O mesmo comando de execução repetido com a mesma `Idempotency-Key` e conteúdo devolve o resultado já registrado; conteúdo diferente retorna `409`
- [ ] Falha interna não recuperável alcança um estado terminal explícito com código, causa, impacto e último marco durável, nunca permanecendo indefinidamente em processamento
- [ ] A interface distingue etapas concluídas, etapa corrente, encerramento e exceção por texto, ícone e traço, com atualizações importantes anunciadas de forma acessível

## Out of Scope

| Feature | Reason |
| --- | --- |
| Lógica interna de coleta, resiliência, relevância e elegibilidade | Histórias 2.1–2.5 — esta história apenas orquestra e persiste as transições entre elas |
| Preflight de IA, geração e crítica de mensagens | Épico 3 — `aguardando_geracao` é o checkpoint que encerra esta história; o preflight automático é apenas mencionado como retomada futura, não implementado aqui |
| Disparo manual de cada etapa isolada pela interface | Contrário ao AC "sem cliques intermediários"; o runner encadeia automaticamente |
| Novo mecanismo de idempotência específico desta história | Reutiliza o mecanismo genérico de `Idempotency-Key` já padronizado (AD-002 / AD-7) |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Onde vive o "runner único no processo" | Um componente de aplicação (`GerenciadorExecucoes`, já nomeado no AD-7) reclama o trabalho persistido e, na inicialização do backend, retoma execuções não terminais a partir do último marco durável | AD-7 já nomeia esse componente e define exatamente esse comportamento; esta história é a primeira a implementá-lo de fato | y — já decidido em ARCHITECTURE-SPINE.md, apenas confirmado aqui |
| Estrutura de marcos persistidos | Uma tabela de marcos correlacionados por `execucao_id` (nova migração, definida no Design) registra cada transição (`coletando`→`sem_risco`/`avaliando_elegibilidade`→`sem_elegiveis`/`aguardando_geracao`) com timestamp e causa | `execucao_preventiva` é descrita no schema como "casca mínima" que os Épicos 2/3 estendem; marcos e causas precisam de rastreabilidade própria (AD-10) | n — decisão de schema, revisável no Design |
| Definição de "falha interna não recuperável" nesta etapa | Qualquer exceção não tratada durante coleta, relevância ou elegibilidade que não seja já um terminal de negócio (`falhou_coleta`, `sem_risco`, `sem_elegiveis`) é capturada e persistida como um terminal técnico explícito com código/causa, distinto dos terminais de negócio | O AC pede um "estado terminal explícito" para falha não recuperável, sem reaproveitar os terminais de negócio já definidos, para não confundir "sem risco" com "erro técnico" | n — assunção técnica, revisável no Design |

**Open questions:** none — todas resolvidas ou registradas acima.

---

## User Stories

### P1: Orquestração automática ponta a ponta da etapa determinística ⭐ MVP

**User Story**: Como Marina, quero que a execução avance sozinha por coleta, relevância e elegibilidade assim que uma coleta válida existir, para não precisar disparar cada etapa manualmente.

**Why P1**: É o comportamento central que dá sentido a esta história — sem ele, as Histórias 2.1–2.5 continuam desconectadas.

**Acceptance Criteria**:

1. WHEN uma coleta meteorológica válida estiver disponível THEN o runner SHALL normalizar o evento, avaliar sua relevância e, quando aplicável, calcular a elegibilidade sem cliques intermediários.
2. WHEN cada transição de estado ocorrer THEN o sistema SHALL persistir um marco correlacionado à mesma execução.

**Independent Test**: Disparar uma coleta válida com um evento relevante e público elegível, e observar, sem nenhuma ação manual adicional, a execução avançar sozinha até `aguardando_geracao` com os marcos intermediários persistidos.

---

### P1: Três resultados determinísticos e checkpoint de geração ⭐ MVP

**User Story**: Como Marina, quero entender claramente se a execução terminou sem risco, sem elegíveis, ou está pronta para gerar mensagens, para saber exatamente o que fazer em seguida.

**Why P1**: São os três desfechos possíveis da etapa determinística — sem eles definidos, o restante do épico não tem um contrato de saída claro.

**Acceptance Criteria**:

1. IF o evento não satisfizer nenhuma regra preventiva ativa THEN a execução SHALL alcançar o estado terminal `sem_risco` com regra, critérios, valores e motivo consultáveis, sem criar elegibilidade, mensagem, simulação ou chamada à OpenAI.
2. IF um evento relevante não tiver segurados elegíveis THEN a execução SHALL alcançar o estado terminal `sem_elegiveis` com contagens e critérios de exclusão consultáveis, sem criar mensagem, simulação ou chamada à OpenAI.
3. WHEN um evento relevante tiver público elegível e a avaliação determinística terminar THEN a execução SHALL persistir o marco `publico_elegivel_formado` e transicionar atomicamente para `aguardando_geracao`, encerrando a operação determinística, indicando `Pronto para geração`, sem exigir ação humana e sem criar mensagens.
4. WHEN Marina abrir uma execução com público elegível formado THEN a interface SHALL exibir a quantidade total e uma prévia com segurado sintético, apólice, localização, canal e motivo da elegibilidade, permitindo abrir a explicação completa dos incluídos e excluídos antes de qualquer geração.

**Independent Test**: Rodar os três cenários (sem risco, sem elegíveis, com elegíveis) com dados de teste e confirmar, para cada um, o estado terminal correto e a ausência de qualquer chamada de IA nos dois primeiros.

---

### P2: Reidratação, idempotência e falha terminal explícita

**User Story**: Como Marina, quero que a execução se reconstrua corretamente ao reabrir a página ou reiniciar o backend, e que comandos repetidos ou falhas internas nunca deixem a execução travada, para confiar na ferramenta em qualquer condição operacional.

**Why P2**: Reforça a robustez do runner já funcional pelas stories P1; cobre os caminhos de recuperação e repetição, não o caminho feliz em si.

**Acceptance Criteria**:

1. WHEN a página for atualizada ou a execução for reidratada em qualquer um dos três resultados determinísticos THEN o estado, os marcos, as contagens e as explicações SHALL ser reconstruídos do DuckDB, sem que nenhum evento ou resultado de elegibilidade seja recalculado ou duplicado.
2. WHEN uma execução reidratada em `aguardando_geracao` retomar o fluxo completo na fase de IA THEN o público elegível preservado SHALL ser reutilizado sem recálculo, e o preflight SHALL iniciar automaticamente uma única vez, protegido pela idempotência do fluxo.
3. WHEN o mesmo comando de execução for repetido com a mesma `Idempotency-Key` e o mesmo conteúdo THEN o sistema SHALL devolver a identificação e o resultado já registrados.
4. IF a mesma `Idempotency-Key` for reusada com conteúdo diferente THEN o sistema SHALL retornar `409`.
5. IF ocorrer uma falha interna não recuperável na etapa determinística THEN a execução SHALL alcançar um estado terminal explícito com código, causa, impacto e último marco durável, e SHALL não permanecer indefinidamente como `Coletando`, `Avaliando` ou `Processando`.
6. WHEN o estado da execução mudar THEN a interface SHALL distinguir etapas concluídas, etapa corrente, encerramento e exceção por texto, ícone e traço, anunciando atualizações importantes e terminais de forma acessível.

**Independent Test**: Reiniciar o backend com uma execução em `avaliando_elegibilidade` persistida e confirmar que ela retoma do último marco durável sem recriar eventos nem resultados de elegibilidade já gravados.

---

## Edge Cases

- IF o backend for reiniciado exatamente entre a persistência do marco `publico_elegivel_formado` e a transição atômica para `aguardando_geracao` THEN a retomada SHALL completar a transição a partir do marco durável, sem deixar a execução presa entre os dois estados.
- IF duas coletas válidas correlacionadas gerarem, cada uma, sua própria execução preventiva THEN o runner SHALL processar cada execução de forma independente, sem que uma interfira no estado da outra.
- WHEN uma execução atingir `sem_risco` ou `sem_elegiveis` THEN uma tentativa de forçar manualmente uma transição para `aguardando_geracao` a partir desse terminal SHALL ser rejeitada, pois estados terminais são monotônicos e nunca reabrem (AD-7).

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| RUNNER-01 | P1: Orquestração automática ponta a ponta da etapa determinística | Design | Pending |
| RUNNER-02 | P1: Orquestração automática ponta a ponta da etapa determinística | Design | Pending |
| RUNNER-03 | P1: Três resultados determinísticos e checkpoint de geração | Design | Pending |
| RUNNER-04 | P1: Três resultados determinísticos e checkpoint de geração | Design | Pending |
| RUNNER-05 | P1: Três resultados determinísticos e checkpoint de geração | Design | Pending |
| RUNNER-06 | P1: Três resultados determinísticos e checkpoint de geração | Design | Pending |
| RUNNER-07 | P2: Reidratação, idempotência e falha terminal explícita | Design | Pending |
| RUNNER-08 | P2: Reidratação, idempotência e falha terminal explícita | Design | Pending |
| RUNNER-09 | P2: Reidratação, idempotência e falha terminal explícita | Design | Pending |
| RUNNER-10 | P2: Reidratação, idempotência e falha terminal explícita | Design | Pending |
| RUNNER-11 | P2: Reidratação, idempotência e falha terminal explícita | Design | Pending |
| RUNNER-12 | P2: Reidratação, idempotência e falha terminal explícita | Design | Pending |

**ID format:** `RUNNER-NN`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 12 total, 0 mapped to tasks, 12 unmapped ⚠️ (mapeamento ocorre na fase Tasks)

---

## Success Criteria

- [ ] Uma coleta válida com evento relevante e público elegível avança sozinha, sem clique intermediário, até `aguardando_geracao`
- [ ] Os três terminais (`sem_risco`, `sem_elegiveis`, `aguardando_geracao`) nunca disparam chamada à OpenAI nem criam mensagem
- [ ] Reidratar qualquer execução após reinício do backend reproduz exatamente o mesmo estado, marcos e contagens, sem duplicar nada
- [ ] Repetir o comando de execução com a mesma `Idempotency-Key` nunca cria uma segunda execução
- [ ] Uma falha interna não recuperável sempre termina em um estado terminal explícito, nunca em processamento indefinido
