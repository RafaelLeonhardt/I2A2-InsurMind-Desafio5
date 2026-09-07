# E2E-11 e E2E-12 — tokens do sistema visual e ausência de controle inerte ou dado fixo.

**Arquivo de teste**: `testes-e2e/responsividade/sistema-visual.spec.ts`
**Requisitos**: E2E-11, E2E-12
**Status**: PASSOU

## Casos de teste (evidência `file:line`)

| Caso | Local | Resultado |
| --- | --- | --- |
| navegacao lateral usa a cor, a largura e o contraste canonicos | `testes-e2e/responsividade/sistema-visual.spec.ts:106` | ✅ passou |
| faixa de demonstracao usa o fundo secundario, persiste e nao pode ser fechada | `testes-e2e/responsividade/sistema-visual.spec.ts:113` | ✅ passou |
| barra de contexto separa o conteudo com a cor de borda canonica | `testes-e2e/responsividade/sistema-visual.spec.ts:124` | ✅ passou |
| controles respeitam a altura minima e o raio pequeno | `testes-e2e/responsividade/sistema-visual.spec.ts:129` | ✅ passou |
| tipografia usa Inter no corpo e Roboto Condensed nos titulos | `testes-e2e/responsividade/sistema-visual.spec.ts:138` | ✅ passou |
| todo controle recebe foco visivel com a espessura canonica | `testes-e2e/responsividade/sistema-visual.spec.ts:147` | ✅ passou |
| a re-verificacao de prontidao reflete a dependencia real, nao um estado fixo | `testes-e2e/responsividade/sistema-visual.spec.ts:161` | ✅ passou |
| restaurar dados sinteticos confirma, executa e informa a conclusao | `testes-e2e/responsividade/sistema-visual.spec.ts:181` | ✅ passou |
| a documentacao da API reflete a verificacao real do backend | `testes-e2e/responsividade/sistema-visual.spec.ts:198` | ✅ passou |
| trocar o segurado troca os dados exibidos, que nao sao fixos | `testes-e2e/responsividade/sistema-visual.spec.ts:210` | ✅ passou |
| as preferencias do segurado sao gravadas, nao apenas exibidas | `testes-e2e/responsividade/sistema-visual.spec.ts:223` | ✅ passou |

## Contexto do cenário

Cópia do comentário de cabeçalho do arquivo de teste — inclui desvios conhecidos, tabelas de rastreabilidade e o que a IA não pode inventar sem editar o teste.

A primeira metade confere, no navegador real, que os componentes globais usam os tokens
canônicos de `DESIGN.md` (cores, famílias tipográficas, raios e dimensões). A segunda metade
exercita cada controle das superfícies montadas e confirma que ele produz efeito real: um
botão que não muda nada e um dado que não acompanha a fonte são exatamente o que o AC
proíbe.

Escopo das superfícies: só o que a navegação real alcança hoje — Prontidão, Restaurar dados
sintéticos e Documentação da API no perfil Administrador, e o painel do Segurado. As
superfícies de Administrador dos Épicos 2–4 continuam fora de `App.tsx` (item aberto em
`.specs/STATE.md`), e o que não está montado não pode ser verificado aqui.

## Desvios de token medidos, registrados e não silenciados

O Edge Case de `spec.md` exige que todo critério não atendido seja registrado explicitamente
na evidência. Estes valores foram medidos no navegador real e divergem de `DESIGN.md`; a
correção é trabalho das histórias de interface correspondentes, não desta (ver "Out of
Scope" em `spec.md`):

| Token de `DESIGN.md` | Valor esperado | Valor medido |
| --- | --- | --- |
| `components.barra-de-contexto.minHeight` | 96px | 76px |
| `components.faixa-de-demonstracao.radius` (`rounded.sm`) | 5px | 0px |
| `typography.titulo-pagina.fontSize` | 32px | 51.84px em 1440px (`clamp`) |
| `components.botao.radius` (`rounded.sm`) | 5px | 8px em `.botao-reverificar` |
| `components.tabela-operacional.border` (`colors.borda`) | #D5E0E5 | #061D45 |
| `colors.texto-principal` | #172B4D | #061D45 (`colors.fundo-navegacao`) |
| `components.foco.color` (`colors.acao-primaria`) | #082B67 | #E9A914 (`colors.atencao`) |
| `typography.rotulo.fontSize` | 12px | 11.52px |
| `spacing` (escala 4/8/12/16/24/32/48) | múltiplos da escala | `rem` fracionários em `App.css` |

Os tokens afirmados abaixo são os que a implementação de fato honra; os divergentes acima
não são afirmados com o valor implementado, porque isso transformaria o desvio em contrato.
