/**
 * E2E-10 — larguras desktop suportadas e aviso abaixo de 1024 px.
 *
 * `DESIGN.md` fixa 1440 × 1024 como referência canônica e define "responsivo para desktop"
 * como 1024 px até monitores amplos: entre 1024 e 1279 px a navegação recolhe e os painéis
 * laterais descem depois do conteúdo; abaixo de 1024 px o MVP informa explicitamente que a
 * resolução não é suportada, sem ocultar função nenhuma.
 *
 * Os dois perfis navegáveis são verificados em cada largura, porque a composição do perfil
 * Segurado (`PainelSegurado`, 5.7) e a do Administrador ocupam a grade de formas diferentes.
 */

import { expect, test, type Page } from '@playwright/test'
import {
  abrirPainelSegurado,
  abrirProntidao,
  conteudoComTexto,
  prepararCenario,
} from '../suporte/cenario.ts'
import { NOME_SEGURADO_CHUVA_ELEGIVEL } from '../suporte/identificadores.ts'

/** `{spacing.largura-navegacao}` de `DESIGN.md`: a coluna reservada à navegação lateral. */
const LARGURA_NAVEGACAO = 252

/** Referência canônica de `DESIGN.md` e piso comprovado de `EXPERIENCE.md`. */
const REFERENCIA = { width: 1440, height: 1024 }

/** Larguras desktop suportadas: o piso de 1024 px, a faixa recolhida e um monitor amplo. */
const LARGURAS_SUPORTADAS = [
  { width: 1024, height: 768 },
  { width: 1280, height: 800 },
  { width: 1920, height: 1080 },
]

/** Abaixo do piso: a resolução não é suportada e isso precisa ser dito. */
const ABAIXO_DO_PISO = { width: 900, height: 800 }

const AVISO_RESOLUCAO =
  'Para uma visualização mais confortável, use uma tela com pelo menos 1024 px. ' +
  'Todas as funções permanecem disponíveis.'

/**
 * `getComputedStyle` do navegador, tipado localmente: o `tsconfig` da suíte não carrega a lib
 * DOM (os arquivos de suporte rodam em Node), então o retorno de `page.evaluate` precisa do
 * tipo declarado aqui.
 */
type JanelaComEstilo = {
  getComputedStyle: (elemento: unknown) => { getPropertyValue: (nome: string) => string }
}

/** Itens de navegação de cada perfil (`SUPERFICIES_POR_PERFIL`, `PerfilContexto.tsx`). */
const NAVEGACAO_ADMINISTRADOR = ['Prontidão', 'Restaurar dados sintéticos', 'Documentação da API']
const NAVEGACAO_SEGURADO = ['Visão geral']

/** Confirma o enquadramento global exigido em qualquer largura suportada. */
async function conferirMolduraGlobal(page: Page, itens: readonly string[]): Promise<void> {
  for (const item of itens) {
    await expect(page.getByRole('button', { name: item })).toBeVisible()
  }
  await expect(page.getByRole('button', { name: /^Visualizar como / })).toBeVisible()
  await expect(page.getByText('Ambiente educacional')).toBeVisible()
}

/**
 * Nenhuma superfície de conteúdo pode ser desenhada dentro da coluna de navegação.
 *
 * A busca é por `.conteudo`, não por `main`: desde o fix de composição de `PainelSegurado`
 * (5.8) só a primeira superfície do perfil Segurado é `<main>` e as outras quatro são
 * `<section>`. Olhar só para `main` deixaria de detectar exatamente a regressão que este
 * teste existe para pegar — quatro superfícies voltando a se espalhar pela grade.
 */
async function conferirConteudoForaDaNavegacao(page: Page): Promise<void> {
  const areas = page.locator('.conteudo')
  const total = await areas.count()
  expect(total).toBeGreaterThan(0)
  for (let indice = 0; indice < total; indice += 1) {
    const caixa = await areas.nth(indice).boundingBox()
    expect(caixa, `a superfície ${indice} não tem caixa`).not.toBeNull()
    expect(
      caixa!.x,
      `a superfície ${indice} começa em x=${caixa!.x} (largura ${caixa!.width}), ` +
        `dentro da coluna de navegação de ${LARGURA_NAVEGACAO}px`,
    ).toBeGreaterThanOrEqual(LARGURA_NAVEGACAO)
  }
}

test.describe('E2E-10: larguras desktop e aviso de resolução', () => {
  test.beforeEach(async () => {
    await prepararCenario()
  })

  test('perfil Administrador funciona na referencia 1440x1024', async ({ page }) => {
    await page.setViewportSize(REFERENCIA)
    await abrirProntidao(page)

    await conferirMolduraGlobal(page, NAVEGACAO_ADMINISTRADOR)
    await expect(page.getByRole('note')).toHaveCount(0)
    await conferirConteudoForaDaNavegacao(page)

    const grade = await page
      .locator('.aplicacao')
      .evaluate((elemento) =>
        (globalThis as unknown as JanelaComEstilo)
          .getComputedStyle(elemento)
          .getPropertyValue('grid-template-columns'),
      )
    expect(grade.startsWith(`${LARGURA_NAVEGACAO}px `)).toBe(true)

    // Função essencial da superfície: a re-verificação por dependência externa.
    await expect(
      page.getByRole('button', { name: 'Verificar novamente: INMET' }),
    ).toBeEnabled()
  })

  test('perfil Segurado funciona na referencia 1440x1024', async ({ page }) => {
    await page.setViewportSize(REFERENCIA)
    await abrirPainelSegurado(page, NOME_SEGURADO_CHUVA_ELEGIVEL)

    await conferirMolduraGlobal(page, NAVEGACAO_SEGURADO)
    await expect(page.getByRole('note')).toHaveCount(0)
    await conferirConteudoForaDaNavegacao(page)

    // Função essencial da superfície: trocar o segurado sintético em exibição.
    await expect(page.getByLabel('Visualizar como')).toBeEnabled()
  })

  for (const viewport of LARGURAS_SUPORTADAS) {
    test(`perfil Administrador mantem as funcoes em ${viewport.width}px`, async ({ page }) => {
      await page.setViewportSize(viewport)
      await abrirProntidao(page)

      await conferirMolduraGlobal(page, NAVEGACAO_ADMINISTRADOR)
      await expect(page.getByRole('note')).toHaveCount(0)
      await expect(
        page.getByRole('table', { name: 'Prontidão das 4 dependências' }),
      ).toBeVisible()
      await expect(
        page.getByRole('button', { name: 'Verificar novamente: OpenAI' }),
      ).toBeEnabled()
    })

    test(`perfil Segurado mantem as funcoes em ${viewport.width}px`, async ({ page }) => {
      await page.setViewportSize(viewport)
      await abrirPainelSegurado(page, NOME_SEGURADO_CHUVA_ELEGIVEL)

      await conferirMolduraGlobal(page, NAVEGACAO_SEGURADO)
      await expect(page.getByRole('note')).toHaveCount(0)
      await expect(page.getByLabel('Visualizar como')).toBeEnabled()
      await expect(conteudoComTexto(page, 'Sua apólice')).toBeVisible()
    })
  }

  test('abaixo de 1024px o aviso de resolucao aparece sem esconder funcoes', async ({ page }) => {
    await page.setViewportSize(ABAIXO_DO_PISO)
    await abrirProntidao(page)

    const aviso = page.getByRole('note')
    await expect(aviso).toBeVisible()
    await expect(aviso).toHaveText(AVISO_RESOLUCAO)

    // "não oculta funções silenciosamente": a navegação e a ação da superfície continuam lá.
    await conferirMolduraGlobal(page, NAVEGACAO_ADMINISTRADOR)
    await expect(
      page.getByRole('table', { name: 'Prontidão das 4 dependências' }),
    ).toBeVisible()
    await expect(
      page.getByRole('button', { name: 'Verificar novamente: INMET' }),
    ).toBeEnabled()
  })

  test('o aviso de resolucao desaparece ao voltar para uma largura suportada', async ({ page }) => {
    await page.setViewportSize(ABAIXO_DO_PISO)
    await abrirProntidao(page)
    await expect(page.getByRole('note')).toBeVisible()

    await page.setViewportSize(REFERENCIA)
    await expect(page.getByRole('note')).toHaveCount(0)
  })
})
