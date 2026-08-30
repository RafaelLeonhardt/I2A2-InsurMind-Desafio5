# História 2.1: Coletar e normalizar dados do INMET — Specification

## Problem Statement

A Central Preventiva ainda não consulta o INMET de verdade: hoje só existe a sonda de prontidão (`SondaInmet`), que faz um único `GET` de saúde sem retries nem normalização, e o schema já reserva `eventos_meteorologicos` com `proveniencia` `real_inmet`/`sintetico`, mas nenhum adaptador o preenche. Sem essa história, não há `Evento meteorológico` real para as histórias seguintes (2.2–2.6) avaliarem — todo o Épico 2 depende de uma fonte meteorológica verificável, com origem e estado explícitos, em vez de dado fixo.

## Goals

- [ ] Uma prova limitada contra o endpoint oficial escolhido do INMET está registrada (campos consumidos, unidades, normalizações, mapeamento) e testes determinísticos de parsing usam amostras congeladas, sem rede
- [ ] O backend coleta automaticamente na inicialização e no intervalo configurado, além de aceitar coleta manual pela API
- [ ] Toda solicitação de coleta é persistida antes de responder e a interface acompanha `Coletando`/`Normalizando`/`Concluído`/`Falha`
- [ ] Respostas válidas viram `Evento meteorológico` interno com proveniência `real_inmet`; respostas inválidas não criam evento e terminam com código/motivo inspecionáveis
- [ ] Toda sincronização persiste início, término, resultado, contagem de válidos e correlação, sem logar cabeçalhos/credenciais/corpo externo
- [ ] Marina consulta o evento normalizado e o histórico de sincronizações (última tentativa, última válida, próxima consulta) em até 1s p95, só com dados persistidos
- [ ] Atualização manual repetida com a mesma `Idempotency-Key` não inicia nova coleta

## Out of Scope

| Feature | Reason |
| --- | --- |
| Tratamento de indisponibilidade, cenário sintético de contingência e recuperação | História 2.2 — esta história cobre o caminho feliz de coleta e normalização |
| Avaliação de relevância (chuva intensa/granizo) e elegibilidade | Histórias 2.3 e 2.5 — aqui o evento só é normalizado e persistido |
| Orquestração ponta a ponta da execução preventiva | História 2.6 — esta história entrega o adaptador e o endpoint de coleta isolados |
| UI de mapa completa com camadas geográficas | Fora do MVP; exige-se apenas uma alternativa em lista operável por teclado/leitor de tela equivalente à seleção do mapa |
| Múltiplas fontes meteorológicas além do INMET | Fora do escopo aprovado (ADR-0013 autoriza apenas INMET e OpenAI como saídas externas) |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Endpoint oficial do INMET a integrar | A confirmar no Design, via pesquisa na documentação pública do INMET (ex.: API de estações automáticas `apitempo.inmet.gov.br`); a URL efetiva é lida de `CENTRAL_PREVENTIVA_URL_BASE_INMET` (já existente na configuração) | Não fabricar contrato de API sem verificação; a variável de ambiente para a URL base já existe desde a sonda de prontidão (`configuracao.py`) | n — pesquisa técnica, revisável no Design |
| Intervalo de coleta automática padrão | A confirmar no Design; valor exato, configurável e documentado, coerente com o ritmo de demonstração (ordem de minutos, não segundos) | AC da história exige "valores exatos, configuráveis e documentados"; a história 2.2 detalha timeout/tentativas/backoff, então o intervalo de coleta fica definido junto no Design para não duplicar decisão | n — revisável no Design |
| Novas tabelas para histórico de sincronização e marcos de execução | `eventos_meteorologicos` (já existe) recebe as linhas normalizadas; uma nova tabela de execuções de sincronização (ex. `sincronizacoes_meteorologicas`) é adicionada em migração própria no Design, correlacionada por `execucao_id`/`requisicao_id` | O schema atual (`README.md` de persistência) não tem tabela de tentativas/histórico de coleta; `execucao_preventiva` é descrita como "casca mínima" que os Épicos 2/3 estendem | n — decisão de schema, revisável no Design |
| Forma da alternativa em lista ao mapa | Uma tabela/lista operável por teclado com os mesmos eventos exibidos no mapa (tipo, local, período, intensidade, origem, horário), sincronizada com a mesma seleção | Cumpre literalmente o AC de acessibilidade sem introduzir um mapa como dependência bloqueante do MVP | y — decisão do usuário, refletida no PRD (`epics.md`) |

**Open questions:** none — todas resolvidas ou registradas acima.

---

## User Stories

### P1: Coleta automática e sob demanda com contrato registrado ⭐ MVP

**User Story**: Como Marina, supervisora da operação, quero que a Central Preventiva consulte o INMET automaticamente na inicialização e em intervalo configurado, e que eu possa forçar uma atualização, para acompanhar eventos meteorológicos com origem verificável.

**Why P1**: Sem coleta real não há evento meteorológico algum para o restante do Épico 2 avaliar.

**Acceptance Criteria**:

1. The system SHALL registrar, para o endpoint oficial escolhido do INMET, os campos consumidos, as unidades, as normalizações aplicadas e o mapeamento para o modelo interno `Evento meteorológico`.
2. The test suite SHALL usar amostras sintéticas ou anonimizadas congeladas do contrato do INMET para testes determinísticos de parsing, sem depender de rede.
3. WHEN o backend for iniciado com a integração configurada THEN o sistema SHALL solicitar uma coleta ao INMET na inicialização e repetir a coleta no intervalo configurado.
4. WHEN Marina solicitar uma atualização manual pela API THEN o sistema SHALL aceitar o pedido independentemente do agendamento automático em curso.
5. WHEN uma solicitação de coleta (automática ou manual) for aceita THEN o backend SHALL persistir o trabalho antes de responder `202 Accepted`.
6. WHILE uma coleta estiver em processamento THEN a interface SHALL exibir um dos estados `Coletando`, `Normalizando`, `Concluído` ou `Falha`, refletindo o estado real persistido.

**Independent Test**: Com um adaptador HTTP dublê configurado com uma resposta válida do INMET, iniciar o backend e observar uma linha de coleta concluída em `eventos_meteorologicos`/histórico sem chamar a rede real; repetir via chamada manual à API e observar o mesmo comportamento.

---

### P1: Normalização com proveniência e rejeição de dados inválidos ⭐ MVP

**User Story**: Como Marina, quero que respostas válidas do INMET virem eventos internos rastreáveis e que respostas inválidas nunca avancem, para confiar que todo evento avaliado tem dado real por trás.

**Why P1**: É o núcleo da história — sem essa garantia, um dado inválido poderia disparar uma avaliação de risco incorreta.

**Acceptance Criteria**:

1. WHEN o adaptador meteorológico processar uma resposta válida do INMET THEN o sistema SHALL convertê-la em um `Evento meteorológico` interno com tipo, área, período, intensidade, medidas normalizadas e instante observado.
2. The system SHALL registrar a proveniência `real_inmet` no evento criado, sem expor o formato externo do INMET ao domínio.
3. IF a resposta do INMET não tiver campos obrigatórios, tiver medidas inválidas ou geografia não reconhecida THEN o sistema SHALL não criar nenhum `Evento meteorológico`.
4. IF a normalização rejeitar uma resposta THEN a tentativa SHALL terminar com um código e um motivo inspecionáveis, sem avançar para avaliação de risco.

**Independent Test**: Alimentar o adaptador com uma amostra congelada inválida (campo obrigatório ausente) e confirmar que nenhum evento é criado e que o motivo da rejeição fica consultável.

---

### P2: Observabilidade, histórico e idempotência da sincronização

**User Story**: Como Marina, quero consultar o histórico de sincronizações e repetir uma atualização manual com segurança, para auditar a fonte meteorológica sem duplicar coletas.

**Why P2**: Reforça auditabilidade e segurança operacional sobre o caminho feliz já coberto pelas duas stories P1; não bloqueia a primeira demonstração de coleta bem-sucedida.

**Acceptance Criteria**:

1. WHEN qualquer tentativa de sincronização iniciar e terminar THEN o sistema SHALL persistir início, término, resultado, quantidade de registros válidos e um `execucao_id` ou `requisicao_id` de correlação.
2. The system SHALL não registrar em log cabeçalhos, credenciais ou o corpo externo integral da resposta do INMET.
3. WHEN Marina abrir Monitoramento ou Fonte meteorológica THEN a interface SHALL exibir tipo, local, período, intensidade, origem e horário de cada evento normalizado.
4. The interface SHALL oferecer, para a seleção de eventos exibida no mapa, uma alternativa equivalente em lista operável por teclado e leitor de tela.
5. WHEN Marina consultar a fonte meteorológica THEN o sistema SHALL exibir última tentativa, última atualização válida, próxima consulta e resultados anteriores usando somente dados persistidos, respondendo em até 1 segundo no percentil 95.
6. IF uma atualização manual for repetida com a mesma `Idempotency-Key` THEN o sistema SHALL não iniciar outra coleta e SHALL devolver a resposta previamente registrada.

**Independent Test**: Repetir uma chamada de atualização manual com a mesma `Idempotency-Key` e confirmar, pela contagem de chamadas ao adaptador dublê, que nenhuma segunda coleta foi disparada.

---

## Edge Cases

- IF o INMET retornar uma resposta tecnicamente válida (200) mas com um campo de medida fora de faixa fisicamente plausível THEN o sistema SHALL tratá-la como resposta inválida e não criar evento.
- IF duas coletas (automática e manual) forem aceitas quase simultaneamente THEN o sistema SHALL persistir ambas como tentativas correlacionadas distintas, sem perder nenhuma.
- WHEN a amostra congelada usada nos testes de parsing for atualizada THEN os testes determinísticos SHALL continuar passando sem depender de rede.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| INMET-01 | P1: Coleta automática e sob demanda com contrato registrado | Design | Pending |
| INMET-02 | P1: Coleta automática e sob demanda com contrato registrado | Design | Pending |
| INMET-03 | P1: Coleta automática e sob demanda com contrato registrado | Design | Pending |
| INMET-04 | P1: Coleta automática e sob demanda com contrato registrado | Design | Pending |
| INMET-05 | P1: Coleta automática e sob demanda com contrato registrado | Design | Pending |
| INMET-06 | P1: Coleta automática e sob demanda com contrato registrado | Design | Pending |
| INMET-07 | P1: Normalização com proveniência e rejeição de dados inválidos | Design | Pending |
| INMET-08 | P1: Normalização com proveniência e rejeição de dados inválidos | Design | Pending |
| INMET-09 | P1: Normalização com proveniência e rejeição de dados inválidos | Design | Pending |
| INMET-10 | P1: Normalização com proveniência e rejeição de dados inválidos | Design | Pending |
| INMET-11 | P2: Observabilidade, histórico e idempotência da sincronização | Design | Pending |
| INMET-12 | P2: Observabilidade, histórico e idempotência da sincronização | Design | Pending |
| INMET-13 | P2: Observabilidade, histórico e idempotência da sincronização | Design | Pending |
| INMET-14 | P2: Observabilidade, histórico e idempotência da sincronização | Design | Pending |
| INMET-15 | P2: Observabilidade, histórico e idempotência da sincronização | Design | Pending |
| INMET-16 | P2: Observabilidade, histórico e idempotência da sincronização | Design | Pending |

**ID format:** `INMET-NN`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 16 total, 0 mapped to tasks, 16 unmapped ⚠️ (mapeamento ocorre na fase Tasks)

---

## Success Criteria

- [ ] Backend iniciado com adaptador dublê produz um evento normalizado com proveniência `real_inmet` sem chamar rede real nos testes
- [ ] Coleta manual repetida com a mesma `Idempotency-Key` não duplica registros em `eventos_meteorologicos` nem no histórico de sincronização
- [ ] Amostra inválida congelada nunca produz um `Evento meteorológico`
- [ ] Consulta de histórico e evento responde em até 1s p95 usando apenas dados persistidos
- [ ] Nenhum log de sincronização contém cabeçalhos, credenciais ou corpo externo integral
