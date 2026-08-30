# História 3.6: Confirmar e executar a simulação sem envio real — Specification

## Problem Statement

A História 3.5 entrega a execução em `aguardando_confirmacao` com o lote aprovado (crítico + Marina) consolidado, mas nada ainda executa a simulação em si. Sem essa história, o produto nunca demonstra o desfecho final do fluxo — como cada mensagem teria sido apresentada em seu canal — e o gate exigido pelo AD-6 entre decisão de conteúdo e execução ("`aguardando_confirmacao` é o gate agregado separado entre decisão humana e simulação") fica incompleto.

## Goals

- [ ] A confirmação exibe evento, regra, período, quantidade de destinatários e distribuição por canal, com aprovação de conteúdo e confirmação de simulação como gates separados
- [ ] O modal de confirmação bloqueia a ação principal até Marina reconhecer explicitamente a natureza simulada, informando que nenhuma comunicação real será enviada
- [ ] Ao confirmar, o backend reverifica versão do agregado e elegibilidade das mensagens, reclamando atomicamente só as aprovadas; nenhuma rejeitada/excluída/em exceção integra a simulação
- [ ] O simulador local cria atomicamente uma entrega simulada por mensagem e canal, sem usar conectores reais; só após sucesso da transação as mensagens aprovadas mudam para `simulada_entregue`
- [ ] Cada entrega simulada mostra como o conteúdo seria apresentado no canal, rotulada como simulada, sem inventar confirmação ou falha de provedor externo
- [ ] Comando repetido com a mesma `Idempotency-Key` devolve a simulação já registrada, sem criar segunda entrega; nova execução exige nova chave e identificação explícitas
- [ ] Confirmações concorrentes para a mesma versão: só uma reclama e cria entregas; a outra recebe o resultado idempotente ou `409`, sem duplicação parcial
- [ ] Falha local durante a simulação reverte a transação de entregas primeiro (preservando mensagens como `aprovada`), depois move o agregado a `falhou_simulacao` numa segunda transação idempotente, com exceção sanitizada local — nunca falha fictícia de canal
- [ ] Nova tentativa após `falhou_simulacao` valida integridade dos snapshots antes de criar execução correlacionada nova; origem permanece terminal, replay não duplica
- [ ] A interface navega entre execução correlacionada e sua origem, preservando IDs/estados/marcos sem mesclar históricos
- [ ] Progresso da simulação exibido como `Bloqueada`, `Pronta`, `Simulando`, `Concluída` ou `Falha local`, com caráter simulado sempre visível

## Out of Scope

| Feature | Reason |
| --- | --- |
| Qualquer conector real de WhatsApp/e-mail/SMS | Proibido pelo escopo do MVP (ADR-0009/0013) — a simulação é inteiramente local |
| Reconciliação e auditoria pós-simulação (linha do tempo, primeira visualização) | Épico 4 — esta história só executa e persiste a simulação em si |
| Consulta do resultado pelo segurado | Épico 5 |
| Retry automático de "falha de provedor" | Não existe — a simulação nunca inventa falha de canal; só falha local genuína é possível |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Forma da "apresentação simulada" por canal | Um objeto estruturado por canal (`ApresentacaoSimulada`: para WhatsApp/SMS, `corpo` renderizado; para e-mail, `assunto`+`corpo`) reaproveitando exatamente o `conteudo` já validado da versão aprovada da mensagem (3.2), sem nova geração nem transformação de conteúdo | A simulação mostra "como o conteúdo seria apresentado", não gera conteúdo novo; a versão aprovada (3.2/3.5) já é o conteúdo final | y — decorre diretamente do próprio conteúdo já produzido e aprovado nas histórias anteriores |
| Granularidade da "falha local" simulável para teste determinístico | Um ponto de injeção de falha controlado por teste (dublê de transação), não uma condição real do DuckDB forçada em produção | AC exige testes de "rollback local" determinísticos, sem depender de condições de infraestrutura reais e instáveis | n — decisão técnica de teste, revisável no Design |

**Open questions:** none — todas resolvidas ou registradas acima.

---

## User Stories

### P1: Confirmação com gate separado e reconhecimento explícito ⭐ MVP

**User Story**: Como Marina, quero confirmar conscientemente que estou iniciando uma simulação, sabendo que nada é enviado de verdade, para nunca confundir a demonstração com uma ação real.

**Why P1**: É a garantia de consentimento consciente exigida pelo AD-6 — sem ela, a simulação poderia ser disparada por engano.

**Acceptance Criteria**:

1. WHEN Marina abrir a confirmação da simulação de um lote com todas as mensagens decididas e ao menos uma aprovada THEN a execução SHALL estar em `aguardando_confirmacao` e a interface SHALL exibir evento, regra, período, quantidade de destinatários e distribuição entre WhatsApp, e-mail e SMS.
2. The system SHALL manter aprovação de conteúdo e confirmação da simulação como gates separados.
3. WHILE o modal de confirmação estiver aberto e Marina ainda não tiver reconhecido a natureza simulada THEN a ação principal SHALL permanecer bloqueada, e o modal SHALL informar explicitamente que nenhuma comunicação real será enviada.

**Independent Test**: Abrir o modal de confirmação sem marcar o reconhecimento e confirmar que o botão de confirmar permanece desabilitado; marcar o reconhecimento e confirmar que o botão libera.

---

### P1: Reclamação atômica e criação das entregas simuladas ⭐ MVP

**User Story**: Como Marina, quero que só as mensagens realmente aprovadas sejam simuladas, e que o resultado mostre exatamente como cada uma teria aparecido no canal, para confiar que a simulação reflete fielmente a decisão tomada.

**Why P1**: É o núcleo funcional da história — a demonstração do desfecho do fluxo.

**Acceptance Criteria**:

1. WHEN Marina marcar o reconhecimento e confirmar THEN o backend SHALL reverificar a versão do agregado e a elegibilidade das mensagens, reclamando atomicamente somente as aprovadas; nenhuma mensagem rejeitada, excluída ou em exceção SHALL integrar a simulação.
2. WHEN o simulador local processar um lote válido confirmado THEN ele SHALL criar atomicamente uma entrega simulada por mensagem e canal, sem usar conectores reais de WhatsApp, e-mail ou SMS, e somente após o sucesso da transação as mensagens aprovadas SHALL mudar para `simulada_entregue`, preservando a relação com lote, aprovações e execução.
3. WHEN o resultado de uma entrega simulada for exibido THEN ele SHALL mostrar como o conteúdo seria apresentado no canal, rotulado como simulado, sem inventar confirmação ou falha de provedor externo.

**Independent Test**: Confirmar um lote com 3 aprovadas e 1 rejeitada; confirmar que exatamente 3 entregas simuladas são criadas, todas rotuladas como simuladas, e a rejeitada não aparece entre elas.

---

### P1: Idempotência, concorrência e rollback local ⭐ MVP

**User Story**: Como Marina, quero confiar que confirmar duas vezes, ou uma falha local durante a simulação, nunca deixam o sistema em estado inconsistente, para operar com segurança mesmo sob uso instável.

**Why P1**: É a garantia transacional exigida pelo AD-7/AD-11 sobre a operação mais irreversível do fluxo (do ponto de vista da demonstração).

**Acceptance Criteria**:

1. WHEN o mesmo comando de confirmação for repetido com a mesma `Idempotency-Key` THEN a API SHALL devolver a simulação já registrada sem criar segunda entrega; uma nova execução SHALL exigir ação explícita, nova chave e nova identificação.
2. WHEN duas confirmações concorrentes forem processadas para a mesma versão THEN somente uma SHALL reclamar e criar as entregas numa transação válida, e a outra SHALL receber o resultado idempotente ou `409`, sem duplicação parcial.
3. IF uma falha local ocorrer durante a simulação e a transação não puder ser concluída THEN a transação das entregas SHALL ser revertida primeiro, sem confirmar entrega parcial e preservando todas as mensagens como `aprovada`; uma segunda transação idempotente SHALL mover o agregado de `simulando` para `falhou_simulacao` e persistir a exceção sanitizada local, nunca uma falha fictícia do canal.

**Independent Test**: Disparar duas confirmações concorrentes para a mesma execução e confirmar, por contagem, que só um conjunto de entregas simuladas existe; forçar uma falha local via dublê de transação e confirmar que nenhuma entrega parcial persiste e as mensagens permanecem `aprovada`.

---

### P2: Retentativa correlacionada e progresso visível

**User Story**: Como Marina, quero tentar de novo após uma falha local sem perder o histórico, e acompanhar o progresso da simulação com clareza, para continuar a demonstração com confiança.

**Why P2**: Reforça continuidade operacional sobre o fluxo já garantido pela P1; não bloqueia a primeira demonstração de simulação bem-sucedida.

**Acceptance Criteria**:

1. WHEN Marina solicitar nova tentativa a partir de uma execução em `falhou_simulacao` THEN o sistema SHALL validar que todas as referências versionadas dos snapshots existem e estão completas, íntegras e com versões suportadas antes de criar qualquer registro; SHALL rejeitar o comando sem criar execução se a validação falhar, e SHALL criar uma nova `ExecucaoPreventiva` em `aguardando_geracao` com novo ID, `execucao_origem_id` e chave idempotente própria se passar — a origem permanece terminal e o replay não duplica.
2. WHEN Marina consultar a origem de uma execução correlacionada, ou estiver na execução original consultando suas retentativas THEN a interface SHALL permitir navegar em ambas as direções, preservando IDs, estados e marcos sem mesclar históricos.
3. WHILE a simulação estiver em andamento THEN a interface SHALL exibir `Bloqueada`, `Pronta`, `Simulando`, `Concluída` ou `Falha local`, com o caráter simulado permanecendo visível durante e depois da operação.

**Independent Test**: Forçar `falhou_simulacao`, solicitar nova tentativa, e confirmar que a execução original permanece terminal enquanto a nova existe em `aguardando_geracao` com `execucao_origem_id` apontando para a original.

---

## Edge Cases

- IF uma mensagem for aprovada por Marina mas seu `versao_esperada` mudar entre a decisão (3.5) e a confirmação desta história (regeneração concorrente, por exemplo) THEN a reverificação de elegibilidade SHALL excluí-la da simulação em vez de simulá-la com dado desatualizado.
- IF nenhuma mensagem estiver aprovada no momento da confirmação (todas mudaram de estado entre a exibição do modal e o clique) THEN a confirmação SHALL ser rejeitada com um erro claro, sem criar simulação vazia.
- WHEN duas execuções distintas (por exemplo, uma execução e sua retentativa correlacionada) tiverem lotes simuláveis simultaneamente THEN cada simulação SHALL ser tratada de forma independente, sem nenhuma interferência entre elas.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| SIMUL-01 | P1: Confirmação com gate separado e reconhecimento explícito | Design | Pending |
| SIMUL-02 | P1: Confirmação com gate separado e reconhecimento explícito | Design | Pending |
| SIMUL-03 | P1: Confirmação com gate separado e reconhecimento explícito | Design | Pending |
| SIMUL-04 | P1: Reclamação atômica e criação das entregas simuladas | Design | Pending |
| SIMUL-05 | P1: Reclamação atômica e criação das entregas simuladas | Design | Pending |
| SIMUL-06 | P1: Reclamação atômica e criação das entregas simuladas | Design | Pending |
| SIMUL-07 | P1: Idempotência, concorrência e rollback local | Design | Pending |
| SIMUL-08 | P1: Idempotência, concorrência e rollback local | Design | Pending |
| SIMUL-09 | P1: Idempotência, concorrência e rollback local | Design | Pending |
| SIMUL-10 | P2: Retentativa correlacionada e progresso visível | Design | Pending |
| SIMUL-11 | P2: Retentativa correlacionada e progresso visível | Design | Pending |
| SIMUL-12 | P2: Retentativa correlacionada e progresso visível | Design | Pending |

**ID format:** `SIMUL-NN`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 12 total, 0 mapped to tasks, 12 unmapped ⚠️ (mapeamento ocorre na fase Tasks)

---

## Success Criteria

- [ ] Modal de confirmação nunca libera a ação principal sem reconhecimento explícito da natureza simulada
- [ ] Só mensagens aprovadas (crítico + Marina) geram entrega simulada; nenhum conector real é invocado em nenhum teste
- [ ] Repetir a confirmação com a mesma `Idempotency-Key` nunca cria uma segunda simulação
- [ ] Falha local nunca deixa entrega parcial nem confirma uma falha fictícia de canal
- [ ] Nova tentativa após `falhou_simulacao` cria execução correlacionada sem reabrir a original
