# E2E-13 (parte assistida) — checklist de acessibilidade que o `axe-core` não cobre sozinho.

**Arquivo de teste**: `testes-e2e/acessibilidade/checklist-manual.spec.ts`
**Requisitos**: E2E-13
**Status**: PASSOU

## Casos de teste (evidência `file:line`)

| Caso | Local | Resultado |
| --- | --- | --- |
| teclado: o primeiro tab alcanca o atalho que leva ao conteudo principal | `testes-e2e/acessibilidade/checklist-manual.spec.ts:83` | ✅ passou |
| teclado: a navegacao lateral inteira e alcancavel e acionavel sem mouse | `testes-e2e/acessibilidade/checklist-manual.spec.ts:98` | ✅ passou |
| foco: o modal recebe o foco, fecha com Esc e devolve o foco a origem | `testes-e2e/acessibilidade/checklist-manual.spec.ts:116` | ✅ passou |
| foco: sair do detalhe do alerta devolve o foco ao item que o abriu | `testes-e2e/acessibilidade/checklist-manual.spec.ts:139` | ✅ passou |
| zoom 200%: o conteudo reflui sem rolagem horizontal e sem perder funcao | `testes-e2e/acessibilidade/checklist-manual.spec.ts:154` | ✅ passou |
| movimento reduzido: nenhuma transicao ou animacao permanece ativa | `testes-e2e/acessibilidade/checklist-manual.spec.ts:184` | ✅ passou |

## Contexto do cenário

Cópia do comentário de cabeçalho do arquivo de teste — inclui desvios conhecidos, tabelas de rastreabilidade e o que a IA não pode inventar sem editar o teste.

O AC exige teclado, foco, contraste, zoom 200%, nomes acessíveis e movimento reduzido. Três
desses seis são decididos por análise estática do DOM e já ficam cobertos, com zero violação
em todos os nove estados auditados, pelas regras do `axe-core` em `axe.spec.ts`:

| Critério do AC | Onde é verificado |
| --- | --- |
| Contraste | regra `color-contrast` (WCAG 1.4.3) — `axe.spec.ts` |
| Nomes acessíveis | regras `button-name`, `link-name`, `select-name`, `label`, `image-alt` — `axe.spec.ts` |
| Estrutura e marcos | regras `landmark-*`, `heading-order`, `list`, `aria-*` — `axe.spec.ts` |
| Teclado | este arquivo: ordem, alcance, `Esc` e devolução de foco |
| Foco | este arquivo: foco visível e devolvido ao elemento de origem |
| Zoom 200% | este arquivo: refluxo sem rolagem horizontal, funções preservadas |
| Movimento reduzido | este arquivo: nenhuma duração de transição/animação sob `reduce` |

Os três últimos dependem de comportamento em tempo de execução (foco real, refluxo real,
media query real), que é exatamente o que uma ferramenta de análise de DOM não decide.

## Desvios conhecidos, registrados e não silenciados

- Os fluxos de Administrador dos Épicos 2–4 (Monitoramento, Evento e decisão, Regras,
Supervisão, Resultados, Linha do tempo) não estão montados em `App.tsx` e por isso não
entram nesta auditoria; item aberto registrado em `.specs/STATE.md`.
- Os desvios de token visual medidos estão na tabela do cabeçalho de
`testes-e2e/responsividade/sistema-visual.spec.ts`; nenhum deles produz violação WCAG
crítica ou séria.
- Refluxo da tabela de Prontidão sob o texto mais longo (INMET indisponível), no piso de
1024 px CSS declarado em `DESIGN.md`: a tabela de 6 colunas rolava horizontalmente a
página inteira em vez de rolar apenas dentro da própria região, contra a "rolagem nomeada"
que `EXPERIENCE.md` prevê para tabela operacional. Corrigido em `36523bf` (fix(api):
permitir PUT no CORS e conter a rolagem da tabela de prontidao); o teste de zoom abaixo
mede exatamente esse estado de maior densidade textual e passa.
