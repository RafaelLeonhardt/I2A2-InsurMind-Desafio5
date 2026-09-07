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
