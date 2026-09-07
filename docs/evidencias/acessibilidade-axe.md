# E2E-13 (parte automatizada) — auditoria WCAG 2.2 AA com `@axe-core/playwright`.

**Arquivo de teste**: `testes-e2e/acessibilidade/axe.spec.ts`
**Requisitos**: E2E-13
**Status**: PASSOU

## Casos de teste (evidência `file:line`)

| Caso | Local | Resultado |
| --- | --- | --- |
| fluxo de Prontidao, no estado normal e com dependencia indisponivel | `testes-e2e/acessibilidade/axe.spec.ts:111` | ✅ passou |
| fluxo de Restaurar dados sinteticos, com o modal de confirmacao aberto | `testes-e2e/acessibilidade/axe.spec.ts:126` | ✅ passou |
| fluxo de Documentacao da API | `testes-e2e/acessibilidade/axe.spec.ts:139` | ✅ passou |
| painel do Segurado com dado real, do resumo ao detalhe do comunicado | `testes-e2e/acessibilidade/axe.spec.ts:146` | ✅ passou |
| painel do Segurado no estado vazio, sem nenhum comunicado | `testes-e2e/acessibilidade/axe.spec.ts:176` | ✅ passou |

## Contexto do cenário

Cópia do comentário de cabeçalho do arquivo de teste — inclui desvios conhecidos, tabelas de rastreabilidade e o que a IA não pode inventar sem editar o teste.

Cada fluxo principal alcançável pela navegação real é analisado no Chromium, com as regras
de WCAG 2.0/2.1/2.2 nos níveis A e AA. O AC exige zero violação crítica ou séria; violações
de impacto moderado ou menor são relatadas na mensagem de falha e listadas no cabeçalho de
`checklist-manual.spec.ts`, nunca silenciadas.

Fluxos auditados: Prontidão (estado normal e com dependência indisponível), Restaurar dados
sintéticos (superfície e modal de confirmação), Documentação da API, e o painel do Segurado
com dado real produzido por um cenário concluído — visão geral, alertas, apólice,
comunicados e meus dados, mais o detalhe do alerta e o detalhe do comunicado.

Fluxos não auditáveis aqui: Monitoramento, Evento e decisão, Regras, Supervisão, Resultados
e Linha do tempo da execução. As superfícies existem e têm suíte `vitest` própria, mas não
estão montadas em `App.tsx` (item aberto registrado em `.specs/STATE.md`) — o `axe-core`
roda contra uma página real, e não há navegação que as alcance. Isso está registrado aqui
como lacuna conhecida da auditoria, não como aprovação.
