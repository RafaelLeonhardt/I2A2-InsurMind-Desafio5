# História 3.1: Preparar a produção agêntica com dados mínimos — Specification

## Problem Statement

O Épico 2 entrega execuções paradas em `aguardando_geracao` com um público elegível preservado, mas nada ainda verifica se a OpenAI está disponível nem monta o contexto mínimo que os agentes do Épico 3 vão consumir. Sem essa história, a geração de mensagens (3.2+) poderia tentar rodar sem credencial válida, expor dados além do necessário ao modelo, ou travar indefinidamente numa integração indisponível — violando diretamente o AD-9 (minimização de dados) e o AD-8 (falha explícita de integração externa).

## Goals

- [ ] A execução verifica configuração e disponibilidade da OpenAI antes de gerar qualquer mensagem, e transiciona idempotentemente para `processando_mensagens` só após preflight bem-sucedido
- [ ] Falha de credencial ausente/inválida ou indisponibilidade global da OpenAI transiciona a execução para `falhou_preparacao_ia`, com exceção sanitizada e sem revelar a credencial
- [ ] Modelo, temperatura, demais parâmetros, versão de prompt e limites operacionais são configuráveis e documentados; a chave real só é lida de `OPENAI_API_KEY`
- [ ] Configuração estrutural ausente/malformada bloqueia a inicialização do serviço (não a criação de uma execução) com erro sanitizado
- [ ] Nova tentativa após `falhou_preparacao_ia` valida integridade dos snapshots antes de criar uma nova `ExecucaoPreventiva` correlacionada; a origem permanece terminal e o replay não duplica
- [ ] A interface navega de uma execução correlacionada para sua origem e vice-versa, sem mesclar históricos
- [ ] O contexto do agente redator contém somente evento, localização aproximada, contexto e coberturas relevantes, canal e orientações de segurança — nunca documentos, dados financeiros, credenciais ou dado desnecessário
- [ ] A proveniência do contexto minimizado (categorias usadas/não usadas) é registrada e consultável por Marina, sem copiar conteúdo sensível a log
- [ ] Falha na montagem/validação do contexto de um item afeta só esse item, sem enviar requisição parcial à OpenAI
- [ ] Indisponibilidade da OpenAI nunca é mascarada por texto fixo, simulador de modelo ou outro provedor

## Out of Scope

| Feature | Reason |
| --- | --- |
| Geração de conteúdo pelo agente redator | História 3.2 — esta história só prepara e valida o terreno antes da primeira chamada de geração |
| Crítica, revisão humana e simulação | Histórias 3.3–3.6 |
| Modo offline/simulado de LLM para demonstração sem internet | ADR-0012/AD-9 exigem modo conectado obrigatório no MVP; explicitamente proibido pelos ACs desta história |
| Autenticação/autorização de múltiplos usuários para a chave OpenAI | Fora do MVP (ADR-0009/0013); só há um ambiente local |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Biblioteca de integração com o modelo | `langchain-openai` (`ChatOpenAI`) para a chamada ao modelo; LangGraph só entra a partir da orquestração de geração/crítica (História 3.2+) — o preflight desta história é uma chamada HTTP simples, sem grafo | ADR-0012 já decide LangChain/LangGraph para o fluxo de agentes; o preflight em si não tem estado, nó ou transição condicional, então não precisa de LangGraph ainda | y — decisão já tomada no ADR-0012, apenas delimitada ao escopo desta história |
| Forma da verificação de preflight | Reusa o mesmo padrão de `SondaOpenAI` (Épico 1: `GET /v1/models` com a chave) para uma checagem de disponibilidade real, mas como parte do fluxo de produção (com o resultado persistido na execução), não como sonda de prontidão isolada | `SondaOpenAI` já existe e já resolve exatamente "checar disponibilidade sem expor a credencial"; reusar evita duas implementações divergentes do mesmo conceito | n — decisão técnica, revisável no Design |
| Onde `falhou_preparacao_ia` vs. bloqueio de inicialização se separam | "Configuração estrutural ausente/malformada" (ex.: modelo inválido no `.env`) bloqueia a inicialização do serviço, igual à validação de `Configuracao` já existente (`configuracao.py`); "chave ausente/inválida" ou "OpenAI indisponível" são sempre casos de preflight em tempo de execução, nunca impedem o backend de subir | Já é o comportamento literal exigido pelo AC ("ausência/invalidade da chave ou indisponibilidade da OpenAI deverão permanecer casos do preflight, não falhas estruturais de inicialização") | y — decisão já resolvida pelo próprio AC |

**Open questions:** none — todas resolvidas ou registradas acima.

---

## User Stories

### P1: Preflight de disponibilidade antes de qualquer geração ⭐ MVP

**User Story**: Como Marina, quero que o sistema verifique a integração com a OpenAI antes de começar a gerar mensagens, para nunca iniciar uma produção que vai falhar no meio do caminho.

**Why P1**: É o gate que protege toda a produção agêntica subsequente — sem ele, 3.2+ poderiam tentar gerar sem credencial válida.

**Acceptance Criteria**:

1. WHEN uma execução exclusivamente em `aguardando_geracao` tiver sua etapa agêntica preparada THEN o sistema SHALL verificar a presença da configuração e a disponibilidade da OpenAI antes de gerar qualquer mensagem.
2. WHEN o preflight for bem-sucedido THEN a execução SHALL transicionar automática e idempotentemente para `processando_mensagens`.
3. IF `OPENAI_API_KEY` estiver ausente ou inválida, ou a OpenAI permanecer globalmente indisponível antes da criação de qualquer mensagem THEN a execução SHALL transicionar para o terminal `falhou_preparacao_ia` ao esgotarem as tentativas de preflight, sem iniciar nenhuma chamada de geração.
4. WHEN a execução alcançar `falhou_preparacao_ia` THEN o sistema SHALL registrar uma exceção sanitizada e preservar todos os resultados determinísticos já produzidos (2.1–2.6), sem revelar valor, fragmento, cabeçalho ou detalhe da credencial.
5. The system SHALL manter modelo, temperatura, demais parâmetros suportados, versão de prompt e limites operacionais como valores configuráveis e documentados, lendo a chave real somente de `OPENAI_API_KEY`.

**Independent Test**: Com um dublê de integração configurado para indisponível, iniciar o preflight de uma execução em `aguardando_geracao` e confirmar que ela termina em `falhou_preparacao_ia` sem nenhuma chamada de geração registrada; repetir com o dublê disponível e confirmar transição para `processando_mensagens`.

---

### P1: Inicialização segura e nova tentativa correlacionada ⭐ MVP

**User Story**: Como Marina, quero que uma configuração estrutural inválida impeça o backend de subir, e que eu possa tentar de novo depois de uma falha de preparação sem perder o histórico, para operar com segurança e continuidade.

**Why P1**: Separa corretamente dois tipos de falha (estrutural vs. operacional) e garante que a demonstração pode continuar após uma falha temporária da OpenAI.

**Acceptance Criteria**:

1. IF a configuração estrutural da integração OpenAI estiver ausente, malformada ou incompatível THEN o serviço SHALL bloquear sua própria inicialização com erro sanitizado, antes de qualquer execução ser criada.
2. WHEN Marina solicitar nova tentativa a partir de uma execução em `falhou_preparacao_ia` THEN o sistema SHALL validar que todas as referências versionadas dos snapshots existem e estão completas, íntegras e com versões suportadas antes de criar qualquer registro.
3. IF essa validação falhar THEN o comando SHALL ser rejeitado sem criar execução nova.
4. IF a validação passar THEN uma nova `ExecucaoPreventiva` SHALL ser criada em `aguardando_geracao`, com novo `execucao_id`, `execucao_origem_id` e chave idempotente própria; a execução de origem SHALL permanecer terminal e o replay do comando SHALL não duplicar execução nem efeito.
5. WHEN Marina consultar a origem de uma execução correlacionada, ou estiver na execução original consultando suas retentativas THEN a interface SHALL permitir navegar em ambas as direções, preservando IDs, estados e marcos sem mesclar históricos.

**Independent Test**: Forçar uma execução a `falhou_preparacao_ia`, solicitar nova tentativa, e confirmar que a execução original permanece terminal enquanto a nova existe em `aguardando_geracao` com `execucao_origem_id` apontando para a original.

---

### P1: Contexto mínimo do agente redator ⭐ MVP

**User Story**: Como Marina, quero que só os dados estritamente necessários cheguem ao agente redator, para nunca expor informação securitária ou pessoal além do preciso.

**Why P1**: É a garantia de minimização de dados exigida pelo AD-9 — sem ela, qualquer geração futura arriscaria vazar dado indevido ao provedor externo.

**Acceptance Criteria**:

1. WHEN o contexto do agente redator for montado para um integrante do público elegível THEN o contexto SHALL conter somente evento, localização aproximada, contexto e coberturas relevantes da apólice, canal e orientações de segurança.
2. The context assembly SHALL excluir documentos, informações financeiras, dados de pagamento, credenciais e qualquer dado não necessário à geração.
3. WHEN a proveniência do contexto minimizado for registrada THEN o sistema SHALL armazenar as categorias de dados utilizadas e não utilizadas, sem copiar conteúdo sensível para logs.
4. WHEN Marina consultar a proveniência antes ou depois da geração THEN o sistema SHALL exibir essas categorias.
5. IF um campo obrigatório estiver ausente ou inconsistente durante a montagem/validação do contexto de um item THEN somente esse item SHALL alcançar um estado terminal de exceção, sem enviar nenhuma solicitação parcial à OpenAI.

**Independent Test**: Montar o contexto de um item elegível e confirmar, por inspeção do objeto produzido, que nenhum campo fora da lista permitida está presente; montar o contexto de um item com dado obrigatório ausente e confirmar que só esse item falha, sem afetar os demais.

---

### P2: Explicação de indisponibilidade sem substituto artificial

**User Story**: Como Marina, quero que a interface explique claramente um bloqueio por indisponibilidade da OpenAI, para saber a próxima ação segura sem confundir com uma falha silenciosa.

**Why P2**: Reforça a transparência operacional já garantida pela P1; não bloqueia a demonstração do preflight em si.

**Acceptance Criteria**:

1. IF a OpenAI não estiver disponível no modo conectado obrigatório do MVP THEN o sistema SHALL não substituir a resposta por texto fixo, simulador de modelo ou outro provedor.
2. WHEN esse bloqueio ocorrer THEN a interface SHALL explicar a causa e a próxima ação segura disponível a Marina.

**Independent Test**: Com a OpenAI indisponível, confirmar visualmente que a interface explica o bloqueio e oferece a ação de nova tentativa, sem nenhum conteúdo gerado artificialmente aparecendo como se fosse real.

---

## Edge Cases

- IF o preflight for repetido com a mesma condição de indisponibilidade em execuções diferentes THEN cada execução SHALL registrar sua própria exceção, sem compartilhar ou reutilizar o registro de outra.
- IF a chave `OPENAI_API_KEY` for válida mas o modelo configurado não existir mais no catálogo da OpenAI THEN o preflight SHALL tratar isso como falha de preparação (não como sucesso), com causa sanitizada.
- WHEN o contexto mínimo for montado para um segurado sem coberturas relevantes ao evento THEN o sistema SHALL tratar isso como campo obrigatório ausente/inconsistente para esse item, sem afetar os demais.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| PREFL-01 | P1: Preflight de disponibilidade antes de qualquer geração | Design | Pending |
| PREFL-02 | P1: Preflight de disponibilidade antes de qualquer geração | Design | Pending |
| PREFL-03 | P1: Preflight de disponibilidade antes de qualquer geração | Design | Pending |
| PREFL-04 | P1: Preflight de disponibilidade antes de qualquer geração | Design | Pending |
| PREFL-05 | P1: Preflight de disponibilidade antes de qualquer geração | T1 | Implementing |
| PREFL-06 | P1: Inicialização segura e nova tentativa correlacionada | Design | Pending |
| PREFL-07 | P1: Inicialização segura e nova tentativa correlacionada | T2 | Implementing |
| PREFL-08 | P1: Inicialização segura e nova tentativa correlacionada | Design | Pending |
| PREFL-09 | P1: Inicialização segura e nova tentativa correlacionada | Design | Pending |
| PREFL-10 | P1: Inicialização segura e nova tentativa correlacionada | Design | Pending |
| PREFL-11 | P1: Contexto mínimo do agente redator | Design | Pending |
| PREFL-12 | P1: Contexto mínimo do agente redator | T2 | Implementing |
| PREFL-13 | P1: Contexto mínimo do agente redator | Design | Pending |
| PREFL-14 | P1: Contexto mínimo do agente redator | Design | Pending |
| PREFL-15 | P1: Contexto mínimo do agente redator | Design | Pending |
| PREFL-16 | P2: Explicação de indisponibilidade sem substituto artificial | Design | Pending |
| PREFL-17 | P2: Explicação de indisponibilidade sem substituto artificial | Design | Pending |

**ID format:** `PREFL-NN`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 17 total, 0 mapped to tasks, 17 unmapped ⚠️ (mapeamento ocorre na fase Tasks)

---

## Success Criteria

- [ ] Preflight bem-sucedido transiciona `aguardando_geracao` → `processando_mensagens` de forma idempotente
- [ ] Preflight malsucedido transiciona para `falhou_preparacao_ia` sem nenhuma chamada de geração e sem expor a credencial em nenhum log/erro
- [ ] Contexto do agente redator nunca contém campo fora da lista permitida (evento, localização aproximada, contexto/coberturas relevantes, canal, orientações de segurança)
- [ ] Nova tentativa após `falhou_preparacao_ia` cria execução correlacionada nova sem reabrir a original
- [ ] Nenhum texto fixo ou simulador de modelo aparece como substituto de uma resposta real da OpenAI
