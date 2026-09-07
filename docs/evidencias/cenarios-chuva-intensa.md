# Cenário E2E-01 — chuva intensa residencial, da entrada meteorológica ao comunicado.

**Arquivo de teste**: `testes-e2e/cenarios/chuva-intensa.spec.ts`
**Requisitos**: E2E-01
**Status**: PASSOU

## Casos de teste (evidência `file:line`)

| Caso | Local | Resultado |
| --- | --- | --- |
| avanca da entrada meteorologica ate o comunicado do segurado elegivel | `testes-e2e/cenarios/chuva-intensa.spec.ts:42` | ✅ passou |

## Contexto do cenário

Cópia do comentário de cabeçalho do arquivo de teste — inclui desvios conhecidos, tabelas de rastreabilidade e o que a IA não pode inventar sem editar o teste.

Percorre o fluxo inteiro contra o backend real: coleta no INMET (dublado) → normalização →
relevância → elegibilidade → preflight de IA → geração e crítica (OpenAI dublada) → revisão
humana → simulação, e termina na interface real, com o comunicado aberto pelo segurado
elegível num navegador Chromium.

As etapas administrativas são dirigidas pela API REST porque as superfícies de
Administrador dos Épicos 2–4 ainda não estão montadas em `App.tsx` (item aberto registrado
em `.specs/STATE.md`). A visualização final — que é o que o AC exige ver na interface —
acontece na tela real do perfil Segurado.
