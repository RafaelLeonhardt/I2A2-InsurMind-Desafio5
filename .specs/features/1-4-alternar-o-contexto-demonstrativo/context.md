# Alternar o Contexto Demonstrativo Context

**Gathered:** 2026-08-29
**Spec:** `.specs/features/1-4-alternar-o-contexto-demonstrativo/spec.md`
**Status:** Ready for design

---

## Feature Boundary

Um seletor "Visualizar como" na barra de contexto alterna a navegação e o conteúdo entre a perspectiva de Administrador (Prontidão, Restaurar dados sintéticos) e a de Segurado (Visão geral, com o segurado sintético padrão), sem nunca representar login, autenticação ou permissão real. O perfil persiste em `localStorage` entre reloads; nenhuma decisão de backend depende dele.

---

## Implementation Decisions

### Composição da navegação do Administrador

- Dois itens de navegação lateral reais: "Prontidão" e "Restaurar dados sintéticos" — nenhuma superfície "Administração" nova é criada.
- Justificativa: os únicos dois itens administrativos já implementados hoje; evita inventar uma superfície fora do escopo da História 1.4.

### Perfil padrão sem preferência salva

- "Administrador" é o perfil exibido quando não há valor válido em `localStorage` (primeira visita, ou valor corrompido/desconhecido).

### Estado transitório ao trocar de perfil

- O modal "Restaurar dados sintéticos", se aberto, fecha automaticamente como parte da alternância de perfil — não há dado de formulário a perder nesse modal.
- Esse mesmo mecanismo de "limpeza de estado transitório" é o que a spec chama de "limpar seleção administrativa incompatível" (não existe hoje nenhuma seleção de linha/tabela administrativa persistente para limpar; o modal é o único estado transitório real).

### Origem do nome do segurado padrão

- O frontend busca o nome via chamada de rede real a um endpoint do backend (a definir na fase de Design), nunca via string fixa no bundle — segue o precedente de AD-003 (fetch real mesmo antes do cliente OpenAPI da História 1.5).
- O segurado padrão é o primeiro semeado em `semeador.py` (`identificador_demonstracao("segurado/chuva-elegivel")`, nome "Pessoa Segurada Sintética DEMO-001") — já elegível, já sintético, sem exigir escolha.

### Agent's Discretion

- Mecanismo técnico de navegação entre superfícies (biblioteca de rotas vs. estado local em memória) — decisão de arquitetura, resolvida na fase de Design.
- Forma exata do endpoint que expõe o segurado padrão (rota, verbo, formato de resposta) — decisão de Design, seguindo as convenções REST/JSON já estabelecidas (`/api/v1`, `snake_case`, IDs opacos).
- Texto exato de rótulos, ícones e mensagens de indisponibilidade — desde que sigam o tom e os componentes já especificados em `DESIGN.md`/`EXPERIENCE.md` (`{components.seletor-demonstrativo}`, `{components.barra-de-contexto}`, `{components.faixa-de-demonstracao}`).

### Declined / Undiscussed Gray Areas → Assumptions

- Nenhuma área foi recusada; as três áreas de produto identificadas (composição da navegação do Administrador, perfil padrão, estado transitório no modal) foram discutidas e decididas com o usuário e já estão registradas na tabela de Assumptions & Open Questions do `spec.md`.

---

## Specific References

- `_bmad-output/planning-artifacts/epics.md` (linhas 544–597): texto canônico dos critérios de aceitação da História 1.4, usado como base direta para as ACs do `spec.md`.
- `_bmad-output/implementation-artifacts/epic-1-context.md`: restrição de não antecipar entidades/comportamentos de épicos posteriores — motivou a decisão de não criar uma superfície "Administração" nem itens de nav para Monitoramento/Regras/Alertas/Comunicados/Meus Dados.
- `.specs/STATE.md` (AD-003): precedente de usar `fetch` direto contra a API real antes do cliente OpenAPI da História 1.5 — motivou a decisão de buscar o segurado padrão via rede, não hardcoded.
- `src/backend/central_preventiva/adaptadores/persistencia/semeador.py`: origem do segurado padrão escolhido ("Pessoa Segurada Sintética DEMO-001").
- `src/frontend/src/App.tsx`: shell estática atual (perfil Segurado fixo, "Marina Costa" hardcoded) que esta história substitui por navegação e contexto reais.

---

## Deferred Ideas

- Seletor de múltiplos segurados sintéticos — fica para uma história futura, quando mais de um segurado precisar ser navegável.
- Superfície "Administração" como landing page com cards — cogitada e recusada nesta rodada em favor de dois itens de navegação diretos; pode ressurgir quando Monitoramento (Épico 2) precisar de uma home administrativa real.
