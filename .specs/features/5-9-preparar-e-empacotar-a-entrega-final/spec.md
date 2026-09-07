# História 5.9: Preparar e empacotar a entrega final — Specification

## Problem Statement

A História 5.8 produz evidências estruturadas e exemplos sanitizados de toda a validação integrada, mas nada ainda os consolida num pacote de entrega avaliável — relatório técnico em PDF, ZIP sanitizado, repositório público pronto, e um inventário verificável. Sem essa história, o trabalho de todo o projeto (Épicos 1–5) fica disperso e não tem um artefato final único e reproduzível para avaliação.

## Goals

- [ ] Relatório técnico em PDF existe com arquitetura implementada, agentes, tecnologias, fluxo, decisões, limitações, evidências e exemplos sanitizados de mensagens, verificável contra a implementação e os artefatos canônicos
- [ ] ZIP completo e sanitizado é gerado, sem `.env`, chaves, dados pessoais reais, caches ou artefatos operacionais indevidos
- [ ] Repositório público contém README reproduzível, licença MIT e toda a documentação exigida, livre de segredos conhecidos e arquivos impróprios
- [ ] Checkout limpo + ZIP final validam instalação e execução separadamente, usando só os comandos documentados, sem etapa manual oculta nem dependência de artefato operacional local
- [ ] Inventário da entrega registra nomes, tamanhos e checksums, permitindo verificar a integridade do PDF, ZIP e demais arquivos
- [ ] Publicação em serviço externo (GitHub ou outro) só ocorre com autorização explícita da pessoa usuária, como ação separada; sem essa autorização, o repositório permanece só preparado e validado localmente, e a história continua pendente
- [ ] Falha da publicação autorizada preserva PDF/ZIP/inventário/checksums/evidências íntegros e consultáveis, registra erro sanitizado, não presume publicação, e mantém a história pendente para nova tentativa autorizada

## Out of Scope

| Feature | Reason |
| --- | --- |
| Qualquer funcionalidade de produto | Esta história é só empacotamento/entrega dos Épicos 1–5, sem código de aplicação novo |
| Execução da publicação sem autorização explícita | Proibido pelo AC e pelo blast-radius do próprio processo de spec-driven — ação remota/externa sempre exige confirmação explícita e separada |
| Geração das evidências em si | História 5.8 — esta história consome as evidências já produzidas, não as gera |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Ferramenta de geração do PDF | Um script Python que monta o relatório em Markdown estruturado a partir de `docs/evidencias/` (5.8) e de `docs/adr/`, `docs/design/`, e o converte a PDF por uma ferramenta já disponível no ambiente de build (a ferramenta exata — ex.: um conversor Markdown→PDF — é escolhida e verificada no momento da implementação, não fabricada aqui) | Reusa as evidências já produzidas por 5.8 como fonte única de verdade; a ferramenta de conversão específica é uma decisão técnica de baixo risco, não uma decisão de produto | n — decisão técnica, revisável no Design |
| Escopo do "pacote ZIP completo" | Todo o código-fonte (`src/`), documentação (`docs/`, `README.md`, `LICENSE`), scripts de migração/seed, e `docs/evidencias/` (5.8) — explicitamente excluindo `.env`, `node_modules/`, `var/`, `__pycache__/`, `.venv/`, caches de build e qualquer artefato operacional local | Cumpre literalmente "sem `.env`, chaves, dados pessoais reais, caches ou artefatos operacionais indevidos"; a lista de exclusão é a mesma já implícita no `.gitignore` do projeto | y — decorre diretamente do `.gitignore` já existente e do AC |
| Licença | MIT, conforme já exigido pelo próprio AC ("licença MIT") | Já decidido explicitamente pelo AC, sem ambiguidade | y — decisão já resolvida pelo próprio AC |

**Open questions:** none — todas resolvidas ou registradas acima.

---

## User Stories

### P1: Relatório técnico verificável e ZIP sanitizado ⭐ MVP

**User Story**: Como equipe responsável pela submissão, quero gerar um relatório técnico em PDF e um ZIP sanitizado, para que a solução possa ser avaliada com segurança e sem exposição de dado indevido.

**Why P1**: São os dois artefatos centrais da entrega — sem eles, não há nada para avaliar.

**Acceptance Criteria**:

1. WHEN o relatório técnico final for gerado a partir das evidências estruturadas e exemplos sanitizados de 5.8 THEN um PDF SHALL existir com arquitetura implementada, agentes, tecnologias, fluxo, decisões, limitações, evidências e exemplos sanitizados de mensagens, com conteúdo verificável contra a implementação e os artefatos canônicos.
2. WHEN o pacote final for montado THEN um ZIP completo e sanitizado SHALL ser gerado, sem `.env`, chaves, dados pessoais reais, caches ou artefatos operacionais indevidos.

**Independent Test**: Gerar o PDF e o ZIP, extrair o ZIP num diretório limpo e confirmar por busca automatizada que nenhum arquivo contém `.env`, padrão de chave conhecido, ou caminho de cache/artefato operacional.

---

### P1: Repositório reproduzível e inventário verificável ⭐ MVP

**User Story**: Como equipe responsável pela submissão, quero um repositório público reproduzível e um inventário com checksums, para que qualquer avaliador possa instalar, executar e conferir a integridade do pacote de forma independente.

**Why P1**: É a garantia de reprodutibilidade e integridade — sem ela, a entrega não é auditável.

**Acceptance Criteria**:

1. WHEN os arquivos e o histórico do repositório de preparação para publicação forem verificados THEN eles SHALL conter README reproduzível, licença MIT e toda a documentação exigida, livres de segredos conhecidos e arquivos impróprios para publicação.
2. WHEN instalação e execução forem validadas separadamente a partir de um checkout limpo e do ZIP final THEN ambas SHALL funcionar usando somente os comandos documentados, sem etapa manual oculta nem dependência de artefato operacional local.
3. WHEN o inventário da entrega for fechado a partir dos artefatos finais validados THEN nomes, tamanhos e checksums SHALL ser registrados, permitindo verificar a integridade do PDF, ZIP e demais arquivos submetidos.

**Independent Test**: A partir de um `git clone` limpo (sem histórico de trabalho local) e separadamente do ZIP extraído, rodar só os comandos do README e confirmar que ambos instalam e executam com sucesso; recalcular os checksums do inventário e confirmar que batem.

---

### P2: Publicação só com autorização explícita, com falha preservando integridade local

**User Story**: Como equipe responsável pela submissão, quero que a publicação externa só aconteça com minha autorização explícita, e que uma falha de publicação nunca comprometa o que já está pronto localmente, para manter controle total sobre a etapa mais irreversível da entrega.

**Why P2**: É a garantia de segurança sobre a ação de maior blast radius desta história — publicar em um serviço externo.

**Acceptance Criteria**:

1. IF não houver autorização explícita da pessoa usuária para publicar THEN o repositório SHALL permanecer somente preparado e validado localmente, e esta história SHALL continuar pendente; a publicação efetiva SHALL só poder ocorrer como ação separada após autorização explícita, e a história SHALL só se concluir depois dessa publicação.
2. IF a publicação autorizada falhar (o serviço externo não confirmar a operação) THEN PDF, ZIP, inventário, checksums e demais evidências locais SHALL permanecer íntegros e consultáveis, o erro sanitizado SHALL ser registrado, nenhuma publicação SHALL ser presumida, e a história SHALL permanecer pendente para nova tentativa autorizada.

**Independent Test**: Sem fornecer autorização, confirmar que nenhuma chamada de publicação é feita e que todos os artefatos locais existem e passam a verificação de integridade; simular uma falha da API de publicação (dublê) e confirmar que os artefatos locais permanecem intactos e o erro é registrado sem sugerir sucesso.

---

## Edge Cases

- IF o PDF ou o ZIP já existirem de uma geração anterior THEN regenerá-los SHALL sobrescrever de forma limpa e determinística, sem misturar conteúdo de gerações diferentes.
- IF uma evidência referenciada pelo relatório técnico (5.8) estiver ausente no momento da geração THEN o script SHALL falhar explicitamente citando a evidência ausente, nunca gerar um PDF com lacuna silenciosa.
- WHEN o inventário for recalculado após qualquer alteração num dos artefatos finais THEN os checksums SHALL refletir o conteúdo atual, nunca um valor desatualizado.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| ENTREGA-01 | P1: Relatório técnico verificável e ZIP sanitizado | Design | Implementing |
| ENTREGA-02 | P1: Relatório técnico verificável e ZIP sanitizado | Design | Implementing |
| ENTREGA-03 | P1: Repositório reproduzível e inventário verificável | Design | Implementing |
| ENTREGA-04 | P1: Repositório reproduzível e inventário verificável | Design | Pending |
| ENTREGA-05 | P1: Repositório reproduzível e inventário verificável | Design | Pending |
| ENTREGA-06 | P2: Publicação só com autorização explícita, com falha preservando integridade local | Design | Pending |
| ENTREGA-07 | P2: Publicação só com autorização explícita, com falha preservando integridade local | Design | Pending |

**ID format:** `ENTREGA-NN`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 7 total, 0 mapped to tasks, 7 unmapped ⚠️ (mapeamento ocorre na fase Tasks)

---

## Success Criteria

- [ ] PDF técnico gerado, verificável contra a implementação e os artefatos canônicos
- [ ] ZIP extraído nunca contém `.env`, chave, dado pessoal real, cache ou artefato operacional
- [ ] Checkout limpo + ZIP final instalam e executam só com comandos documentados
- [ ] Checksums do inventário sempre batem com o conteúdo atual dos artefatos
- [ ] Publicação nunca ocorre sem autorização explícita; falha de publicação nunca corrompe os artefatos locais
