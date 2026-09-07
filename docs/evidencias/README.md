# Evidências da suíte completa — História 5.8

Gerado em 2026-09-07 13:22:56 UTC por `python3 scripts/gerar_evidencias.py`.

## Suítes de unidade e integração

| Suíte | Comando | Resultado |
| --- | --- | --- |
| Backend (pytest) | `uv run --directory src/backend pytest` | ✅ passou |
| Frontend (vitest) | `npm test --prefix src/frontend -- --run` | ✅ passou |
| E2E (Playwright, todos os projetos) | `npx playwright test` (em `testes-e2e/`) | ✅ passou |

Resumo da última linha de cada suíte:

```
[backend]
........................................................................ [ 98%]
...............                                                          [100%]
1095 passed in 121.86s (0:02:01)
Uninstalled 1 package in 1ms
Installed 1 package in 4ms

[frontend]
 RUN  v4.1.11 /Users/rafael/Documents/git/I2A2/insur-minds/Desafio5/src/frontend
 Test Files  46 passed (46)
      Tests  444 passed (444)
   Start at  10:20:36
   Duration  16.25s (transform 2.44s, setup 6.24s, import 52.26s, tests 17.09s, environment 30.00s)

[e2e]
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Shutting down
INFO:     Waiting for application shutdown.
INFO:     Application shutdown complete.
INFO:     Finished server process [22137]
```

## Cenários ponta a ponta

| Relatório | Requisitos | Status |
| --- | --- | --- |
| [E2E-13 (parte automatizada) — auditoria WCAG 2.2 AA com `@axe-core/playwright`.](acessibilidade-axe.md) | E2E-13 | ✅ passou |
| [E2E-13 (parte assistida) — checklist de acessibilidade que o `axe-core` não cobre sozinho.](acessibilidade-checklist-manual.md) | E2E-13 | ✅ passou |
| [Cenário E2E-01 — chuva intensa residencial, da entrada meteorológica ao comunicado.](cenarios-chuva-intensa.md) | E2E-01 | ✅ passou |
| [Cenário E2E-05 — contingência do INMET: indisponibilidade controlada e cenário sintético.](cenarios-contingencia-inmet.md) | E2E-05 | ✅ passou |
| [Cenário E2E-08 — toda evidência de um cenário executado é localizável, e o contrato bate.](cenarios-evidencias-localizaveis.md) | E2E-08 | ✅ passou |
| [Cenário E2E-02 — granizo automóvel, da entrada sintética rotulada ao comunicado.](cenarios-granizo.md) | E2E-02 | ✅ passou |
| [Cenário E2E-06 — produção agêntica alcançada com a OpenAI indisponível ou mal configurada.](cenarios-indisponibilidade-openai.md) | E2E-06 | ✅ passou |
| [Cenário E2E-04 — regeneração automática e esgotamento das três tentativas.](cenarios-regeneracao.md) | E2E-04 | ✅ passou |
| [Cenário E2E-07 — retentativa correlacionada a partir de uma falha terminal, sem duplicação.](cenarios-retentativa.md) | E2E-07 | ✅ passou |
| [Cenário E2E-03 (metade "sem público elegível") — evento relevante, ninguém elegível.](cenarios-sem-elegivel.md) | E2E-03 | ✅ passou |
| [Cenário E2E-03 (metade "sem risco") — evento que não atinge nenhuma regra.](cenarios-sem-risco.md) | E2E-03 | ✅ passou |
| [E2E-11 e E2E-12 — tokens do sistema visual e ausência de controle inerte ou dado fixo.](responsividade-sistema-visual.md) | E2E-11, E2E-12 | ✅ passou |
| [E2E-10 — larguras desktop suportadas e aviso abaixo de 1024 px.](responsividade-viewports.md) | E2E-10 | ✅ passou |
