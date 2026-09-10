# História 6.6: Consultar resultados da simulação e a linha do tempo — Specification

## Problem Statement

O protótipo fecha o ciclo do administrador com a tela de resultados (`Results`/imagem `05-resultado-simulacao`): estatísticas de geradas/processadas/entregues/falhas, tabela filtrável, detalhe de falha e exportação de relatório. `SuperficieResultados`, `SuperficieDetalheResultado` e `SuperficieLinhaDoTempo` já existem no frontend real, testadas isoladamente, mas nenhuma é montada em `App.tsx` — o mesmo padrão de órfã já documentado em `.specs/STATE.md`. Sem esta história, o resultado de uma simulação de envio (Épico 4 inteiro, já implementado no backend) não tem nenhuma superfície administrativa que o exiba.

## Goals

- [ ] Ao final do fluxo de envio simulado (História 6.5), o administrador vê o resultado consolidado da execução: estatísticas agregadas e a lista de itens por status/canal
- [ ] O administrador consegue inspecionar o detalhe de um item específico, incluindo o motivo de uma falha quando houver
- [ ] O administrador consegue consultar a linha do tempo ponta a ponta da execução (evento → decisão → geração → crítica → aprovação → simulação)

## Out of Scope

| Feature | Reason |
| --- | --- |
| "Corrigir dado e simular novamente" (ação vista no protótipo `Results`) | Equivale a uma nova execução por retentativa (AD-009), já coberta pelo mecanismo de retentativa do backend; esta história consulta o resultado, não reabre o fluxo de geração |
| Paginação real de 248 resultados como na imagem 05 | O volume de segurados do cenário sintético de demonstração é pequeno; paginação client-side simples cobre o caso real do produto sem replicar um número de exemplo do design de referência |
| Exportação de relatório para um formato específico não confirmado (PDF, CSV, etc.) | O backend de resultados (`resultados`, `detalhe_resultado`) não tem, até este levantamento, um endpoint de exportação confirmado; a P3 desta história cobre uma exportação simples (CSV client-side) e o formato definitivo fica sujeito à fase de Design |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Fonte de dado | `SuperficieResultados` (recebe `execucaoId`) e `SuperficieDetalheResultado` já implementadas consomem os endpoints `resultados`/`detalhe_resultado` existentes — nenhum endpoint novo necessário para P1/P2 | Verificado nas assinaturas de props já existentes no código-fonte | y — grounded no código-fonte |
| **[CORRIGIDA]** "Quantidade gerada, processada, entregue e com falha" (PAINELRES-01) | O backend não persiste "gerada" e "processada" como contadores distintos — só `totaisPorEstado` (uma linha por estado de mensagem: `aprovada`, `rejeitada`, `excluida`, `falhou_conteudo`, `falhou_integracao_ia`, `simulada_entregue`). "Total processado" = soma de todos os `totaisPorEstado`; "entregue" = total de `simulada_entregue`; "com falha" = soma de `falhou_conteudo` + `falhou_integracao_ia`. Uma seção de estatísticas rápidas nova (derivada, não um dado novo da API) exibe esses três números antes das tabelas já existentes | `ResultadosConsolidados.totaisPorEstado: TotalPorChave[]` (`api/resultados.ts:26-34`) não tem campos "gerada"/"processada" — confirmado por leitura completa do tipo e do componente | y — grounded no código-fonte; consistente com o Independent Test do P1 ("soma de entregues + falhas corresponde ao total processado"), que não menciona "gerada" separadamente |
| **[CORRIGIDA]** "Tabela de itens filtrável por status ou canal" (PAINELRES-02/03) | `SuperficieResultados` **não tem** uma tabela de itens individuais cobrindo todo o lote — tem duas tabelas agregadas (`totaisPorCanal`, `totaisPorEstado`, cada uma só `{chave, total}`, sem granularidade de item) e uma terceira tabela, `TabelaNaoSimulaveis`, que é a única com um item por linha (`mensagemId`, `canal`, `estado`, `motivo`). PAINELRES-02/03 se aplicam a essa tabela: filtro client-side por canal/estado sobre `resultados.naoSimulaveis`, não sobre o lote inteiro (que não existe como lista de itens no frontend nem no backend hoje) | Lida integralmente em `SuperficieResultados.tsx` (372 linhas) — `TabelaTotais` (usada duas vezes, para canal e para estado) não recebe `onSelecionar` nem filtro, só ordenação de colunas; `TabelaNaoSimulaveis` é a única tabela com `item.mensagemId` por linha | y — grounded no código-fonte; escopo restrito é consistente com o Independent Test do P1 (soma de itens simulados/falhos bate com o total agregado, não exige listar cada item individual do lote inteiro) |
| **[CORRIGIDA]** "Selecionar um item da tabela de resultados" (PAINELRES-04/05) | O único ponto de seleção possível hoje é uma linha de `TabelaNaoSimulaveis` (a única tabela por item) — abre `SuperficieDetalheResultado` (já existe, drawer controlado por `aberto`/`mensagemId`/`onFechar`, já testado isoladamente) | `SuperficieDetalheResultado` já expõe exatamente essas props (`aberto`, `execucaoId`, `mensagemId`, `onFechar`) prontas para controle externo por estado local, mesmo padrão de `mensagemAberta` já usado em `SuperficieRevisaoLote` (6.5) | y — grounded no código-fonte |
| `SuperficieLinhaDoTempo` sem `execucaoId` explícito nas props | O componente é autossuficiente: tem sua própria busca de execuções (por segurado/canal/estado, `buscarExecucoes`) e sua própria seleção — não precisa de composição com `SuperficieExecucao`; alcançável como destino de topo próprio, não como drill-down (AD-016 continua reservado para detalhe parametrizado por id) | A assinatura atual (`export function SuperficieLinhaDoTempo()`) não recebe parâmetros; o componente já renderiza seu próprio `<main id="conteudo-principal">`, igual a `SuperficieRegras`/`SuperficieFonteMeteorologica` — o mesmo padrão de integração "só montar no App.tsx" usado em 6.3/6.7 | y — grounded no código-fonte |
| **[NOVA]** Slot de navegação para `SuperficieLinhaDoTempo` | Reusa o item de topo `'comunicacoes'` já existente em `SUPERFICIES_TOPO_POR_PERFIL`/`NavegacaoLateral` (rotulado "Comunicações"), hoje um placeholder `EmConstrucao` em `App.tsx:65-66` — fecha uma lacuna aberta desde o Design da 6.1 (`.specs/features/6-1-.../design.md:63`, comentário `// NOVO — 6.5 (design próprio)`) que nem a spec.md da 6.5 nem a da 6.6 haviam reclamado explicitamente | A busca própria da `SuperficieLinhaDoTempo` (por segurado/canal/estado, cruzando execuções) é conceitualmente "consultar comunicações", o encaixe mais natural para o rótulo já existente — evita deixar um item de navegação permanentemente "Em construção" e evita criar um `SuperficieTopo` novo desnecessário | y — decisão de composição, sem mudança de requisito de produto |
| Exportação de relatório (P3) | Uma exportação simples do resultado exibido (CSV gerado no cliente a partir dos dados já carregados) até que o produto confirme um formato/endpoint definitivo | Evita bloquear a história inteira por causa de uma funcionalidade cujo contrato de backend não está confirmado nesta auditoria | n — depende de confirmação de produto sobre o formato definitivo; tratado como P3 justamente por essa incerteza |

**Open questions:** none — todas resolvidas ou registradas acima (a incerteza de formato de exportação foi registrada como assumption de P3, não deixada em aberto). Duas assumptions originais foram corrigidas durante o Design (marcadas `[CORRIGIDA]`) e uma nova foi adicionada (`[NOVA]`), seguindo o mesmo padrão de autocorreção já usado nas Histórias 6.3/6.4.

---

## User Stories

### P1: Consultar o resultado consolidado da simulação ⭐ MVP

**User Story**: Como administrador, quero ver as estatísticas consolidadas de uma simulação de envio (geradas, processadas, entregues, falhas) para avaliar o sucesso do ciclo preventivo sem precisar consultar a API diretamente.

**Why P1**: É o fechamento visível do ciclo administrativo — sem ele, o resultado de todo o trabalho das Histórias 6.1–6.5 permanece invisível.

**Acceptance Criteria**:

1. WHEN uma execução atingir o estado de resultado consolidado THEN a interface SHALL exibir as estatísticas agregadas (quantidade gerada, processada, entregue e com falha) a partir dos dados persistidos.
2. WHEN o administrador filtrar a tabela de itens por status ou canal THEN a lista exibida SHALL refletir apenas os itens que atendem ao filtro selecionado.
3. The soma dos itens exibidos após qualquer filtro SHALL nunca exceder o total de itens da execução consolidada.

**Independent Test**: Abrir o resultado de uma execução concluída no cenário sintético e confirmar que a soma de entregues + falhas corresponde ao total processado exibido nas estatísticas.

---

### P1: Inspecionar o detalhe de um item, incluindo falhas ⭐ MVP

**User Story**: Como administrador, quero abrir o detalhe de um item específico do resultado, incluindo o motivo de uma falha, para entender e comunicar o que aconteceu com aquele envio simulado.

**Why P1**: É o nível de detalhe que dá utilidade prática ao resultado consolidado — sem ele, a tabela é só um contador sem explicação.

**Acceptance Criteria**:

1. WHEN o administrador selecionar um item da tabela de resultados THEN a interface SHALL exibir `SuperficieDetalheResultado` com os dados completos daquele item.
2. IF o item selecionado estiver em estado de falha THEN o detalhe SHALL exibir o motivo da falha tal como persistido pela API, sem inferir ou completar informação ausente.

**Independent Test**: Selecionar um item com falha simulada no cenário sintético e confirmar que o motivo exibido corresponde exatamente ao persistido pela API para aquele item.

---

### P2: Consultar a linha do tempo ponta a ponta

**User Story**: Como administrador, quero ver a linha do tempo completa de uma execução (do evento à simulação) para auditar a sequência de decisões automáticas e humanas de ponta a ponta.

**Why P2**: Complementa o detalhe da P1 com uma visão cronológica, mas o resultado já é útil sem essa visão consolidada.

**Acceptance Criteria**:

1. WHEN o administrador abrir a linha do tempo de uma execução THEN a interface SHALL exibir os marcos em ordem cronológica, do evento identificado até a simulação de envio.

**Independent Test**: Abrir a linha do tempo de uma execução concluída e confirmar que a ordem dos marcos exibidos corresponde à ordem cronológica real dos timestamps persistidos.

---

### P3: Exportar o resultado exibido

**User Story**: Como administrador, quero exportar os dados do resultado exibido para compartilhar ou arquivar fora da aplicação.

**Why P3**: Conveniência adicional — a consulta já é completa na interface sem essa exportação.

**Acceptance Criteria**:

1. WHEN o administrador acionar "Exportar" THEN o sistema SHALL gerar um arquivo com os dados atualmente filtrados/exibidos na tabela, sem incluir itens ocultos pelo filtro ativo.

**Independent Test**: Aplicar um filtro por status, exportar, e confirmar que o arquivo gerado contém apenas os itens daquele status.

---

## Edge Cases

- IF a execução ainda não tiver atingido um estado de resultado consolidado THEN a interface SHALL indicar que o resultado ainda não está disponível, sem mostrar uma tabela vazia como se fosse o resultado final.
- WHEN dois itens tiverem o mesmo status e canal (caso comum) THEN a ordenação da tabela SHALL ser estável (não reordenar itens iguais a cada nova renderização).

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| PAINELRES-01 | P1: Consultar o resultado consolidado da simulação | T2, T3, T4 | ✅ Verified |
| PAINELRES-02 | P1: Consultar o resultado consolidado da simulação | T5 | ✅ Verified |
| PAINELRES-03 | P1: Consultar o resultado consolidado da simulação | T5 | ✅ Verified |
| PAINELRES-04 | P1: Inspecionar o detalhe de um item, incluindo falhas | T6 | ✅ Verified |
| PAINELRES-05 | P1: Inspecionar o detalhe de um item, incluindo falhas | T6 | Implementing (Fix 1 aplicado, aguardando re-verificação) |
| PAINELRES-06 | P2: Consultar a linha do tempo ponta a ponta | T3 | ✅ Verified |
| PAINELRES-07 | P3: Exportar o resultado exibido | T7 | ✅ Verified |

**ID format:** `PAINELRES-NN`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 7 total, 7 mapped to tasks, 0 unmapped — todas as 7 tasks (T1-T7) implementadas, gate completo passando (frontend 520 testes + lint + build). Rodada 1 do Verifier: FAIL (PAINELRES-05 sem cobertura de teste para o ramo `excecao`) → Fix 1 aplicado (teste de composição novo em `SuperficieResultados.test.tsx` com `excecao` não-nula) → aguardando rodada 2.

---

## Success Criteria

- [ ] Toda estatística exibida bate com a soma real dos itens persistidos
- [ ] Todo motivo de falha exibido vem do dado persistido, nunca de inferência
- [ ] A linha do tempo nunca mistura a proveniência de uma execução de origem com a de sua retentativa
