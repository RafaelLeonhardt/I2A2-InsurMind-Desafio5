# História 6.5: Gerar, revisar e confirmar o envio simulado das comunicações — Specification

## Problem Statement

O protótipo mostra o fluxo completo de produção agêntica pelo lado do administrador: preparar o contexto mínimo, gerar mensagens por IA (`MessagePage`/imagem `03-geracao-revisao-mensagens`), revisar em lote e confirmar o envio simulado (`SimModal`/imagem `04-confirmacao-envio-simulado`). No frontend real, `SuperficiePreparacaoIA`, `SuperficieGeracaoMensagens`, `SuperficieAvaliacaoCritica`, `SuperficieRevisaoLote` e `SuperficieSimulacao` já existem — cada uma testada isoladamente — mas nenhuma é alcançável a partir de `App.tsx`. Sem esta história, o administrador não tem como ver a IA gerando mensagens, avaliar as verificações de segurança, aprovar ou rejeitar o lote, nem confirmar a simulação de envio — apesar de o backend de ponta a ponta (Épico 3 inteiro) já existir e ser exercitado hoje só por testes E2E que contornam a UI chamando a API REST diretamente.

## Goals

- [ ] A partir de uma execução em andamento (História 6.2), o administrador acompanha a preparação do contexto mínimo, a geração de mensagens por canal e a avaliação crítica de segurança de cada mensagem
- [ ] O administrador revisa o lote de comunicações geradas, decide aprovar, regenerar ou rejeitar cada item com a justificativa exigida quando aplicável, e confirma o envio simulado
- [ ] Toda decisão humana registrada nesta tela fica disponível para a explicação que o segurado eventualmente vê (História 6.9 / 5.4), sem duplicar ou divergir do que foi de fato decidido

## Out of Scope

| Feature | Reason |
| --- | --- |
| Envio real de mensagens | Nunca existe no produto — toda "confirmação de envio" é uma simulação (AD do projeto, reforçado em todo o domínio) |
| Consulta de resultados após a simulação (estatísticas, falhas, exportação) | História 6.6 — esta história termina na confirmação do envio, não no resultado consolidado |
| Edição manual do texto de uma mensagem gerada | Fora do domínio atual — a única ação sobre uma mensagem individual é aprovar, regenerar (nova geração por IA) ou rejeitar, nunca editar texto livre |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Composição das cinco superfícies existentes | `SuperficiePreparacaoIA` (recebe `execucaoId`), `SuperficieGeracaoMensagens` (recebe `execucaoId`), `SuperficieAvaliacaoCritica` (recebe `mensagemId`+`versaoId`), `SuperficieRevisaoLote` (recebe `execucaoId`) e `SuperficieSimulacao` são sequenciadas como etapas da mesma execução, na ordem em que o backend as produz (`preparando_ia` → `gerando` → `criticando` → `revisao_lote` → `simulando`) — a orquestração exata de transição entre etapas fica para a fase de Design | As cinco superfícies já existem prontas com esses props; a única peça em aberto é como a navegação entre etapas se encadeia, uma decisão de composição de UI, não de requisito de produto | y — grounded no código-fonte (`Propriedades` de cada superfície) |
| Estado "em revisão" por mensagem individual + contador (visto na imagem 03: "247 prontas, 1 em revisão") | Exibido se e somente se o backend de geração/revisão já expuser esse estado por mensagem; não inventado no frontend caso a API só devolva um estado agregado | Item D.3-#21 do levantamento de gaps: não confirmado se o backend persiste estado por mensagem individual — assumir sem verificar violaria o princípio já em vigor de nunca inferir dado ausente | y — mesma regra aplicada em EXPLICACAO-05/PAINELEXEC |
| Justificativa obrigatória para certas decisões | Mantida exatamente como já implementado em `SuperficieRevisaoLote` ("Decisões que só são aceitas com justificativa", REVISAO-06) — esta história não altera essa regra, só a torna alcançável | Regra já definida e testada na história de origem (3.5); reabri-la aqui seria escopo fora desta integração | y — decorre do código já existente |

**Open questions:** none — todas resolvidas ou registradas acima.

---

## User Stories

### P1: Acompanhar a preparação e a geração de mensagens ⭐ MVP

**User Story**: Como administrador, quero acompanhar a IA preparando o contexto mínimo e gerando uma mensagem por canal para cada segurado elegível, para confirmar que a produção agêntica está ocorrendo corretamente antes de qualquer revisão.

**Why P1**: É o primeiro elo visível da produção agêntica — sem ele, a revisão em lote (segunda história desta feature) não tem conteúdo de onde partir.

**Acceptance Criteria**:

1. WHEN uma execução entrar na etapa de preparação do contexto mínimo THEN a interface SHALL exibir o progresso dessa preparação a partir dos marcos já persistidos pela API.
2. WHEN a execução avançar para a geração de mensagens THEN a interface SHALL exibir a lista de destinatários com o estado de geração de cada mensagem (pronta, em processamento, ou falha).
3. IF a geração de uma mensagem falhar (`falhou_integracao_ia`) THEN a interface SHALL mostrar essa falha explicitamente para o item afetado, sem bloquear a exibição das demais mensagens já geradas.

**Independent Test**: Abrir uma execução em `gerando` e confirmar que a lista de destinatários exibida corresponde às mensagens já persistidas pela API para essa execução, com o estado real de cada uma.

---

### P1: Revisar a avaliação crítica de segurança de cada mensagem ⭐ MVP

**User Story**: Como administrador, quero ver a avaliação crítica de segurança de cada mensagem gerada, para confirmar que nenhuma comunicação inadequada seguiria para o envio simulado.

**Why P1**: É a garantia de segurança que o produto promete — sem essa visibilidade, aprovar o lote na próxima história seria um ato de confiança cega na IA.

**Acceptance Criteria**:

1. WHEN uma mensagem tiver sido avaliada pelo agente crítico THEN a interface SHALL exibir os critérios avaliados e a origem da decisão (agente ou humana), distinguindo visualmente as duas.
2. IF uma mensagem tiver sido regenerada (automaticamente pelo ciclo crítico ou por decisão humana) THEN a interface SHALL indicar quantas tentativas ocorreram e qual delas foi a aprovada.

**Independent Test**: Abrir a avaliação crítica de uma mensagem que passou por 2 tentativas antes da aprovação e confirmar que as tentativas e a origem da aprovação final aparecem corretamente.

---

### P1: Revisar o lote e confirmar o envio simulado ⭐ MVP

**User Story**: Como administrador, quero revisar o lote de mensagens geradas, decidir sobre cada item (aprovar, regenerar ou rejeitar) e confirmar o envio simulado, para concluir o ciclo de comunicação preventiva sem enviar nada real.

**Why P1**: É a ação que fecha o ciclo desta história — sem ela, a produção agêntica fica sem destino.

**Acceptance Criteria**:

1. WHEN o administrador abrir a revisão em lote de uma execução THEN a interface SHALL exibir cada item do lote com sua decisão pendente e um sinal de atenção quando o item estiver em exceção.
2. IF a decisão selecionada exigir justificativa (REVISAO-06 já implementado) THEN o sistema SHALL bloquear a confirmação até que a justificativa seja preenchida.
3. WHEN o administrador confirmar o envio simulado do lote revisado THEN o sistema SHALL registrar a simulação e avançar a execução para o estado de resultado consolidado (História 6.6), deixando claro que nenhum envio real ocorreu.

**Independent Test**: Revisar um lote com um item exigindo justificativa, confirmar que a confirmação é bloqueada sem ela, preencher a justificativa, confirmar o envio simulado e verificar que a execução avança de estado.

---

## Edge Cases

- IF todos os itens do lote forem rejeitados THEN o sistema SHALL permitir a confirmação de "nenhum envio", sem forçar ao menos uma aprovação artificial.
- WHEN o administrador tentar confirmar o envio simulado duas vezes seguidas (duplo clique) THEN o sistema SHALL tratar a segunda confirmação como idempotente (AD-002), nunca gerando uma segunda simulação.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| FLUXOMSG-01 | P1: Acompanhar a preparação e a geração de mensagens | T1 | ✅ Verified |
| FLUXOMSG-02 | P1: Acompanhar a preparação e a geração de mensagens | T2 | ✅ Verified |
| FLUXOMSG-03 | P1: Acompanhar a preparação e a geração de mensagens | T2 | ✅ Verified |
| FLUXOMSG-04 | P1: Revisar a avaliação crítica de segurança de cada mensagem | T5 | ✅ Verified |
| FLUXOMSG-05 | P1: Revisar a avaliação crítica de segurança de cada mensagem | T5 | ✅ Verified |
| FLUXOMSG-06 | P1: Revisar o lote e confirmar o envio simulado | T3 | ✅ Verified |
| FLUXOMSG-07 | P1: Revisar o lote e confirmar o envio simulado | T3 | ✅ Verified |
| FLUXOMSG-08 | P1: Revisar o lote e confirmar o envio simulado | T4, T6 | ✅ Verified |

**ID format:** `FLUXOMSG-NN`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 8 total, 8 mapped to tasks, 0 unmapped — todas as 6 tasks (T1-T6) implementadas, gate completo passando (frontend 502 testes + lint + build). Verificação independente **PASS** — 8/8 ACs casadas com o desfecho da spec, 2/2 Edge Cases cobertos, 4/4 mutações do sensor mortas: `validation.md`.

---

## Success Criteria

- [ ] Todo estado de geração/crítica exibido corresponde exatamente ao persistido pela API, nunca recalculado no frontend
- [ ] Nenhuma confirmação de envio simulado é possível sem que decisões que exigem justificativa a tenham
- [ ] Uma confirmação repetida nunca produz uma segunda simulação
