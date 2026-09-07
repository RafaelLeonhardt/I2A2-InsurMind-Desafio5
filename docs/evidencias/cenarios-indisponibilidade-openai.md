# Cenário E2E-06 — produção agêntica alcançada com a OpenAI indisponível ou mal configurada.

**Arquivo de teste**: `testes-e2e/cenarios/indisponibilidade-openai.spec.ts`
**Requisitos**: E2E-06
**Status**: PASSOU

## Casos de teste (evidência `file:line`)

| Caso | Local | Resultado |
| --- | --- | --- |
| termina em falhou_preparacao_ia sem texto fixo e preserva o trabalho deterministico | `testes-e2e/cenarios/indisponibilidade-openai.spec.ts:68` | ✅ passou |
| termina em falhou_preparacao_ia quando o modelo configurado nao esta no catalogo | `testes-e2e/cenarios/indisponibilidade-openai.spec.ts:150` | ✅ passou |
