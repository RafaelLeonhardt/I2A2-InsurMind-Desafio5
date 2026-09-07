# E2E-13 (parte assistida) — checklist de acessibilidade que o `axe-core` não cobre sozinho.

**Arquivo de teste**: `testes-e2e/acessibilidade/checklist-manual.spec.ts`
**Requisitos**: E2E-13
**Status**: PASSOU

## Casos de teste (evidência `file:line`)

| Caso | Local | Resultado |
| --- | --- | --- |
| teclado: o primeiro tab alcanca o atalho que leva ao conteudo principal | `testes-e2e/acessibilidade/checklist-manual.spec.ts:88` | ✅ passou |
| teclado: a navegacao lateral inteira e alcancavel e acionavel sem mouse | `testes-e2e/acessibilidade/checklist-manual.spec.ts:103` | ✅ passou |
| foco: o modal recebe o foco, fecha com Esc e devolve o foco a origem | `testes-e2e/acessibilidade/checklist-manual.spec.ts:121` | ✅ passou |
| foco: sair do detalhe do alerta devolve o foco ao item que o abriu | `testes-e2e/acessibilidade/checklist-manual.spec.ts:144` | ✅ passou |
| zoom 200%: o conteudo reflui sem rolagem horizontal e sem perder funcao | `testes-e2e/acessibilidade/checklist-manual.spec.ts:159` | ✅ passou |
| movimento reduzido: nenhuma transicao ou animacao permanece ativa | `testes-e2e/acessibilidade/checklist-manual.spec.ts:189` | ✅ passou |
