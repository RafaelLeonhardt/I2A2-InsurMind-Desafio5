# História 4.4: Consultar a linha do tempo ponta a ponta — Specification

## Problem Statement

As Histórias 4.1–4.3 entregam totais, detalhe individual e visualização pelo segurado, mas nenhuma reconstrói a cronologia completa de uma execução — do evento meteorológico até a visualização do comunicado. Sem essa história, Marina não tem como auditar o "porquê" de ponta a ponta de nenhuma execução específica, nem correlacionar todos os marcos já persistidos pelos Épicos 2 e 3 numa única narrativa temporal.

## Goals

- [ ] Abrir a linha do tempo de uma execução mostra, em ordem cronológica, coleta, normalização, regra, elegibilidade, gerações, críticas, exceções, decisões humanas, simulação e visualização existentes, cada marco com data/hora, ator, ação, resultado e correlação
- [ ] Execução que origina ou foi criada por retentativa navega entre origem e todas as correlacionadas, em ambas as direções, com IDs/estados/marcos separados e auditáveis
- [ ] Execução encerrada sem risco ou sem elegíveis termina no motivo determinístico correspondente, sem etapa de IA/aprovação/simulação inexistente
- [ ] Mensagem com várias tentativas expande cada versão/avaliação/motivo de reprovação na ordem correta, com proveniência ligada à mensagem e à execução
- [ ] Pesquisa/filtro por segurado sintético, canal ou estado disponível no MVP mostra só resultados correspondentes sem alterar dados; resultado vazio é explicado, sem paginação/filtro avançado fora do escopo
- [ ] Comunicado reaberto várias vezes mantém um único marco de primeira visualização, sem duplicar eventos nem alterar a cronologia
- [ ] Horários persistidos em UTC são localizados de forma consistente para a demonstração, com o valor canônico continuando disponível para auditoria técnica
- [ ] Linha do tempo com muitos marcos é navegável por teclado/leitor de tela, com ordem/agrupamentos/estado expandido anunciados, e rolagem interna com nome acessível quando necessária

## Out of Scope

| Feature | Reason |
| --- | --- |
| Consolidação de totais/resultados | História 4.1 |
| Detalhe individual de uma mensagem | História 4.2 (a linha do tempo referencia, mas não substitui, o detalhe já entregue) |
| Registro da própria visualização pelo segurado | História 4.3 — esta história só exibe o marco já registrado |
| Filtros/paginação avançados (múltiplos critérios combinados, exportação) | Explicitamente fora do MVP pelo próprio AC |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Fonte única dos marcos | Uma consulta agregadora que une, por `execucao_id`, `marcos_execucao` (2.6), `sincronizacoes_meteorologicas`+tentativas (2.1/2.2), `avaliacoes_risco` (2.3), `elegibilidades_historicas` (2.5), `versoes_mensagem`+`avaliacoes_criticas`+`decisoes_humanas` (3.2/3.3/3.5), `excecoes_operacionais` (2.2/3.4), `entregas_simuladas`+`visualizacoes_comunicado` (3.6/4.3) — nenhuma tabela nova de "linha do tempo" duplicando o que já existe | Toda a informação já está persistida por histórias anteriores com timestamp; duplicá-la numa tabela de linha do tempo criaria uma segunda fonte de verdade a manter sincronizada | y — decorre diretamente do princípio de fonte única já aplicado pelo projeto inteiro (nenhuma história anterior duplicou dado já persistido) |
| Filtros do MVP | Segurado sintético (por nome/id), canal (`whatsapp`/`email`/`sms`), estado (`EstadoExecucao`/`EstadoMensagem` disponíveis) — aplicados sobre a lista de execuções antes de abrir uma linha do tempo específica, não dentro da própria linha do tempo já aberta | Cumpre literalmente "informa um segurado sintético, canal ou estado disponível"; a lista de execuções é o ponto natural de busca antes de entrar no detalhe cronológico de uma execução específica | y — decorre diretamente do próprio AC |

**Open questions:** none — todas resolvidas ou registradas acima.

---

## User Stories

### P1: Cronologia completa com marcos correlacionados ⭐ MVP

**User Story**: Como Marina, quero abrir a linha do tempo de uma execução e ver, em ordem, tudo que aconteceu desde a coleta até a visualização, para reconstruir como o evento virou comunicação.

**Why P1**: É o núcleo da história — sem a cronologia completa, não há auditoria ponta a ponta possível.

**Acceptance Criteria**:

1. WHEN Marina abrir a linha do tempo de uma execução com marcos persistidos THEN a interface SHALL exibir, em ordem cronológica, coleta, normalização, regra, elegibilidade, gerações, críticas, exceções, decisões humanas, simulação e visualização existentes.
2. Each timeline entry SHALL apresentar data/hora, ator, ação, resultado e correlação.
3. IF uma execução for encerrada sem risco ou sem elegíveis THEN sua linha do tempo SHALL terminar no motivo determinístico correspondente, sem conter etapas de IA, aprovação ou simulação inexistentes.
4. WHEN a linha do tempo de uma mensagem com várias tentativas for expandida THEN cada versão, avaliação e motivo de reprovação SHALL aparecer na ordem correta, com a proveniência permanecendo ligada à mensagem e à execução.

**Independent Test**: Abrir a linha do tempo de uma execução completa (coleta→simulação→visualização) e confirmar todos os marcos na ordem certa; abrir a de uma execução `sem_risco` e confirmar que ela termina ali, sem nenhuma etapa de geração/crítica/simulação listada.

---

### P1: Navegação entre execuções correlacionadas ⭐ MVP

**User Story**: Como Marina, quero navegar de uma execução para sua origem ou suas retentativas, para entender a história completa mesmo quando uma falha gerou uma nova tentativa.

**Why P1**: Fecha a auditoria entre execuções correlacionadas já criadas pelas Histórias 2.2/3.1/3.6.

**Acceptance Criteria**:

1. WHEN Marina consultar a linha do tempo de uma execução que origina ou foi criada por retentativa THEN ela SHALL poder navegar da origem para todas as execuções correlacionadas e de cada correlacionada de volta à origem, com IDs, estados e marcos permanecendo separados e auditáveis em ambas as direções.

**Independent Test**: A partir de uma execução em `falhou_coleta` com uma retentativa correlacionada já criada (2.2), navegar para a retentativa e depois de volta à origem, confirmando que os marcos de cada uma nunca se misturam.

---

### P1: Marco único de visualização e ausência de duplicação ⭐ MVP

**User Story**: Como Marina, quero confiar que reabrir um comunicado nunca duplica nada na linha do tempo, para que a cronologia sempre reflita exatamente o que aconteceu uma vez.

**Why P1**: É a garantia de integridade da cronologia sobre o marco entregue por 4.3.

**Acceptance Criteria**:

1. IF um comunicado tiver sido reaberto várias vezes THEN a linha do tempo SHALL conter somente um marco de primeira visualização.
2. Reaberturas SHALL não duplicar eventos nem alterar a cronologia.

**Independent Test**: Reabrir o mesmo comunicado 3 vezes (via 4.3) e confirmar, na linha do tempo, exatamente um marco de visualização com a data da primeira abertura.

---

### P2: Pesquisa, localização temporal e acessibilidade

**User Story**: Como Marina, quero pesquisar execuções por segurado/canal/estado, ver horários localizados de forma consistente, e navegar a linha do tempo por teclado/leitor de tela, para auditar com eficiência e sem barreira de acesso.

**Why P2**: Reforça usabilidade sobre a cronologia já garantida pelas P1; não bloqueia a primeira demonstração de uma linha do tempo correta.

**Acceptance Criteria**:

1. WHEN Marina informar um segurado sintético, canal ou estado disponível e aplicar a pesquisa/filtro previsto no MVP THEN a lista SHALL mostrar somente os resultados correspondentes, sem alterar nenhum dado.
2. IF um resultado vazio ocorrer THEN ele SHALL ser explicado, sem oferecer filtros ou paginação avançados fora do escopo.
3. WHEN horários persistidos em UTC forem exibidos THEN eles SHALL ser localizados de forma consistente para o contexto da demonstração, com o valor canônico permanecendo disponível para auditoria técnica.
4. WHEN a linha do tempo for navegada por teclado ou leitor de tela THEN ordem, agrupamentos e estado expandido SHALL ser anunciados, e a rolagem interna, se necessária, SHALL possuir nome acessível e indicação visível.

**Independent Test**: Filtrar a lista de execuções por um canal específico e confirmar que só execuções com mensagens desse canal aparecem; navegar a linha do tempo inteira por teclado e confirmar anúncio de cada marco expandido.

---

## Edge Cases

- IF uma execução tiver múltiplas mensagens, cada uma com seu próprio ciclo de tentativas THEN a linha do tempo SHALL agrupar os marcos por mensagem dentro da cronologia geral da execução, sem intercalar de forma confusa marcos de mensagens diferentes.
- IF nenhuma execução corresponder ao filtro informado THEN a lista SHALL mostrar uma explicação de resultado vazio, nunca um erro técnico.
- WHEN uma execução tiver exceções técnicas (falha de integração, falha local de simulação) intercaladas com marcos de sucesso THEN a linha do tempo SHALL apresentar ambos na ordem cronológica real, sem esconder a exceção nem reordenar para parecer um fluxo mais limpo do que o real.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| TIMELINE-01 | P1: Cronologia completa com marcos correlacionados | Design | Pending |
| TIMELINE-02 | P1: Cronologia completa com marcos correlacionados | Design | Pending |
| TIMELINE-03 | P1: Cronologia completa com marcos correlacionados | Design | Pending |
| TIMELINE-04 | P1: Cronologia completa com marcos correlacionados | Design | Pending |
| TIMELINE-05 | P1: Navegação entre execuções correlacionadas | Design | Pending |
| TIMELINE-06 | P1: Marco único de visualização e ausência de duplicação | Design | Pending |
| TIMELINE-07 | P1: Marco único de visualização e ausência de duplicação | Design | Pending |
| TIMELINE-08 | P2: Pesquisa, localização temporal e acessibilidade | Design | Pending |
| TIMELINE-09 | P2: Pesquisa, localização temporal e acessibilidade | Design | Pending |
| TIMELINE-10 | P2: Pesquisa, localização temporal e acessibilidade | Design | Pending |
| TIMELINE-11 | P2: Pesquisa, localização temporal e acessibilidade | Design | Pending |

**ID format:** `TIMELINE-NN`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 11 total, 0 mapped to tasks, 11 unmapped ⚠️ (mapeamento ocorre na fase Tasks)

---

## Success Criteria

- [ ] Linha do tempo de uma execução completa mostra todos os marcos reais na ordem cronológica correta, com data/hora, ator, ação, resultado, correlação
- [ ] Execução `sem_risco`/`sem_elegiveis` termina no motivo, sem etapa inexistente
- [ ] Navegação origem↔retentativa nunca mistura marcos de execuções diferentes
- [ ] Reabrir um comunicado várias vezes nunca duplica o marco de visualização
- [ ] Filtro por segurado/canal/estado nunca altera dado, e resultado vazio é sempre explicado
