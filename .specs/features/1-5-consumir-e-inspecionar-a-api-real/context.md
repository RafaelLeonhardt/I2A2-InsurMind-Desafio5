# História 1.5 — Context (decisões do usuário)

## Decisão 1: forma da "interface técnica" de disponibilidade da documentação

**Pergunta**: o AC de EARS "a interface técnica deverá exibir estado de carregamento, disponibilidade ou indisponibilidade com causa e endereço local" — tela nova ou indicador em superfície existente?

**Resposta do usuário**: tela nova dedicada.

**Consequência no spec**: nova `Superficie` `'documentacao-api'`, visível só no perfil Administrador, com link para a Swagger UI.

## Decisão 2: escopo do cliente HTTP central / tipos gerados

**Pergunta**: migrar `contexto.ts`, `prontidao.ts` e `dadosSinteticos.ts` para o cliente central com tipos gerados, ou criar o cliente central só para o que esta história adiciona?

**Resposta do usuário**: só o cliente central, sem migrar as 3 chamadas existentes.

**Consequência no spec**: `Out of Scope` registra a não-migração como dívida já prevista em AD-003 (`.specs/STATE.md`); o cliente HTTP central e os tipos gerados por `openapi-typescript` são usados apenas pela nova superfície "Documentação da API".
