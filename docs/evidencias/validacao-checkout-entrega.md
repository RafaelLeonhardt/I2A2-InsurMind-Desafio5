# Validação de checkout limpo e ZIP — História 5.9 (T4)

Cobre `ENTREGA-04` de `spec.md`: instalação e execução, a partir de
um checkout limpo e separadamente do ZIP final, usando só os comandos já
documentados em `README.md`, sem etapa manual oculta e sem depender de nenhum
artefato operacional local preexistente (`var/central_preventiva.duckdb`
incluso).

Executado em 2026-09-07. Dois ambientes isolados, nenhum reaproveitando estado
do repositório de trabalho:

- **Checkout limpo**: `git clone` local do repositório nesta revisão, num
  diretório totalmente novo (sem `var/`, sem `.venv/`, sem `node_modules/`).
- **ZIP extraído**: `docs/entrega/entrega.zip` (gerado por
  `scripts/empacotar_entrega.py`, T2) extraído num segundo diretório novo,
  também sem `var/`.

Em ambos, antes de qualquer comando, só `cp -n .env.example .env` (o próprio
passo documentado no README) — nenhuma outra preparação manual.

## Resultado

| Comando (README) | Checkout limpo | ZIP extraído |
| --- | --- | --- |
| `uv sync --project src/backend --locked` | ✅ instalou | ✅ instalou |
| `uv run --directory src/backend pytest` | ✅ 1095 passed in 155.97s | ✅ 1095 passed in 145.08s |
| `uv run --directory src/backend ruff check .` | ✅ All checks passed! | ver nota¹ |
| `uv run --directory src/backend pyright` | ✅ 0 errors, 0 warnings, 0 informations | ver nota¹ |
| `npm ci --prefix src/frontend` | ✅ instalou | ✅ instalou |
| `npm test --prefix src/frontend -- --run` | ✅ 46 test files, 444 tests passed | ver nota¹ |
| `npm run lint --prefix src/frontend` | ✅ passou (só avisos pré-existentes do `oxlint`, sem erro) | ver nota¹ |
| `npm run build --prefix src/frontend` | ✅ built in 1.16s | ✅ built in 1.06s |
| `uv run --directory src/backend python -m central_preventiva.composicao.inicializador` | ✅ 16 migrações aplicadas, conjunto sintético semeado, `var/central_preventiva.duckdb` criado do zero | ✅ idêntico, `var/` criado do zero |

¹ O ZIP contém exatamente o mesmo código-fonte do checkout limpo (`git
ls-files`, ver `scripts/empacotar_entrega.py`), já verificado linha a linha
pela suíte `pytest`/`ruff`/`pyright`/`vitest`/`oxlint` completa no checkout
limpo acima. Para o ZIP, a validação focou em instalação e execução
(`pytest` do backend completo + `npm ci`/`build` do frontend) para confirmar
que o empacotamento em si não corrompe nem omite nada necessário à execução —
repetir byte-a-byte a mesma suíte de qualidade já provada no checkout limpo
não agregaria evidência nova.

## Confirmações específicas do AC

- **Nenhuma etapa manual oculta**: todo comando executado veio literalmente de
  `README.md` (seção "Execução local"); nenhum comando, variável de ambiente
  ou arquivo adicional foi criado além de `cp -n .env.example .env`, que já é
  o próprio passo documentado.
- **Nenhuma dependência de artefato operacional local**: nenhum dos dois
  diretórios continha `var/` antes da inicialização; o comando de
  inicialização criou `var/central_preventiva.duckdb` do zero em ambos,
  aplicando as 16 migrações e semeando os dados sintéticos com sucesso.
- **ZIP funciona independentemente do checkout via Git**: o diretório extraído
  do ZIP não é um repositório Git (sem `.git/`); toda a instalação e execução
  acima ocorreu normalmente mesmo assim.
