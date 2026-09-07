# E2E-10 — larguras desktop suportadas e aviso abaixo de 1024 px.

**Arquivo de teste**: `testes-e2e/responsividade/viewports.spec.ts`
**Requisitos**: E2E-10
**Status**: PASSOU

## Casos de teste (evidência `file:line`)

| Caso | Local | Resultado |
| --- | --- | --- |
| perfil Administrador funciona na referencia 1440x1024 | `testes-e2e/responsividade/viewports.spec.ts:92` | ✅ passou |
| perfil Segurado funciona na referencia 1440x1024 | `testes-e2e/responsividade/viewports.spec.ts:115` | ✅ passou |
| perfil Administrador mantem as funcoes em 1024px | `testes-e2e/responsividade/viewports.spec.ts:128` | ✅ passou |
| perfil Segurado mantem as funcoes em 1024px | `testes-e2e/responsividade/viewports.spec.ts:142` | ✅ passou |
| perfil Administrador mantem as funcoes em 1280px | `testes-e2e/responsividade/viewports.spec.ts:128` | ✅ passou |
| perfil Segurado mantem as funcoes em 1280px | `testes-e2e/responsividade/viewports.spec.ts:142` | ✅ passou |
| perfil Administrador mantem as funcoes em 1920px | `testes-e2e/responsividade/viewports.spec.ts:128` | ✅ passou |
| perfil Segurado mantem as funcoes em 1920px | `testes-e2e/responsividade/viewports.spec.ts:142` | ✅ passou |
| abaixo de 1024px o aviso de resolucao aparece sem esconder funcoes | `testes-e2e/responsividade/viewports.spec.ts:153` | ✅ passou |
| o aviso de resolucao desaparece ao voltar para uma largura suportada | `testes-e2e/responsividade/viewports.spec.ts:171` | ✅ passou |

## Contexto do cenário

Cópia do comentário de cabeçalho do arquivo de teste — inclui desvios conhecidos, tabelas de rastreabilidade e o que a IA não pode inventar sem editar o teste.

`DESIGN.md` fixa 1440 × 1024 como referência canônica e define "responsivo para desktop"
como 1024 px até monitores amplos: entre 1024 e 1279 px a navegação recolhe e os painéis
laterais descem depois do conteúdo; abaixo de 1024 px o MVP informa explicitamente que a
resolução não é suportada, sem ocultar função nenhuma.

Os dois perfis navegáveis são verificados em cada largura, porque a composição do perfil
Segurado (`PainelSegurado`, 5.7) e a do Administrador ocupam a grade de formas diferentes.
