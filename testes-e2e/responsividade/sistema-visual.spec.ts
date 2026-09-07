/**
 * E2E-11 e E2E-12 — tokens do sistema visual e ausência de controle inerte ou dado fixo.
 *
 * A primeira metade confere, no navegador real, que os componentes globais usam os tokens
 * canônicos de `DESIGN.md` (cores, famílias tipográficas, raios e dimensões). A segunda metade
 * exercita cada controle das superfícies montadas e confirma que ele produz efeito real: um
 * botão que não muda nada e um dado que não acompanha a fonte são exatamente o que o AC
 * proíbe.
 *
 * Escopo das superfícies: só o que a navegação real alcança hoje — Prontidão, Restaurar dados
 * sintéticos e Documentação da API no perfil Administrador, e o painel do Segurado. As
 * superfícies de Administrador dos Épicos 2–4 continuam fora de `App.tsx` (item aberto em
 * `.specs/STATE.md`), e o que não está montado não pode ser verificado aqui.
 *
 * ## Desvios de token medidos, registrados e não silenciados
 *
 * O Edge Case de `spec.md` exige que todo critério não atendido seja registrado explicitamente
 * na evidência. Estes valores foram medidos no navegador real e divergem de `DESIGN.md`; a
 * correção é trabalho das histórias de interface correspondentes, não desta (ver "Out of
 * Scope" em `spec.md`):
 *
 * | Token de `DESIGN.md` | Valor esperado | Valor medido |
 * | --- | --- | --- |
 * | `components.barra-de-contexto.minHeight` | 96px | 76px |
 * | `components.faixa-de-demonstracao.radius` (`rounded.sm`) | 5px | 0px |
 * | `typography.titulo-pagina.fontSize` | 32px | 51.84px em 1440px (`clamp`) |
 * | `components.botao.radius` (`rounded.sm`) | 5px | 8px em `.botao-reverificar` |
 * | `components.tabela-operacional.border` (`colors.borda`) | #D5E0E5 | #061D45 |
 * | `colors.texto-principal` | #172B4D | #061D45 (`colors.fundo-navegacao`) |
 * | `components.foco.color` (`colors.acao-primaria`) | #082B67 | #E9A914 (`colors.atencao`) |
 * | `typography.rotulo.fontSize` | 12px | 11.52px |
 * | `spacing` (escala 4/8/12/16/24/32/48) | múltiplos da escala | `rem` fracionários em `App.css` |
 *
 * Os tokens afirmados abaixo são os que a implementação de fato honra; os divergentes acima
 * não são afirmados com o valor implementado, porque isso transformaria o desvio em contrato.
 */

import { expect, test, type Locator, type Page } from '@playwright/test'
import { obterPreferencias } from '../suporte/api.ts'
import {
  abrirPainelSegurado,
  abrirProntidao,
  conteudoComTexto,
  prepararCenario,
} from '../suporte/cenario.ts'
import { programarSondaInmet } from '../suporte/dubles-cliente.ts'
import {
  NOME_SEGURADO_CHUVA_ELEGIVEL,
  NOME_SEGURADO_GRANIZO_ELEGIVEL,
  SEGURADO_CHUVA_ELEGIVEL_ID,
} from '../suporte/identificadores.ts'

/** Cores canônicas de `DESIGN.md`, no formato que `getComputedStyle` devolve. */
const COR = {
  fundoNavegacao: 'rgb(6, 29, 69)',
  fundoNavegacaoSecundario: 'rgb(8, 43, 103)',
  borda: 'rgb(213, 224, 229)',
  sobreEscuro: 'rgb(255, 255, 255)',
} as const

/** `{spacing.largura-navegacao}` de `DESIGN.md`. */
const LARGURA_NAVEGACAO = '252px'

/** `{rounded.sm}` de `DESIGN.md`. */
const RAIO_PEQUENO = '5px'

/** Altura mínima de controle exigida por `DESIGN.md` (`botao`, `seletor-demonstrativo`). */
const ALTURA_MINIMA_CONTROLE = '44px'

/** `{components.foco.width}` de `DESIGN.md`. */
const ESPESSURA_FOCO = '3px'

const FAMILIA_CORPO = 'Inter, Arial, sans-serif'
const FAMILIA_TITULO = '"Roboto Condensed", sans-serif'

/**
 * `getComputedStyle` do navegador, tipado localmente: o `tsconfig` da suíte não carrega a lib
 * DOM, porque os arquivos de suporte rodam em Node.
 */
type JanelaComEstilo = {
  getComputedStyle: (elemento: unknown) => { getPropertyValue: (nome: string) => string }
}

/** Lê uma propriedade computada de um elemento real, já renderizado pelo Chromium. */
function estiloDe(alvo: Locator, propriedade: string): Promise<string> {
  return alvo.evaluate(
    (elemento, nome) =>
      (globalThis as unknown as JanelaComEstilo)
        .getComputedStyle(elemento)
        .getPropertyValue(nome as string),
    propriedade,
  )
}

/** Número da apólice exibida no painel, que precisa acompanhar o segurado selecionado. */
function apoliceExibida(page: Page): Locator {
  return conteudoComTexto(page, 'Sua apólice')
}

test.describe('E2E-11: tokens do sistema visual', () => {
  test.beforeEach(async ({ page }) => {
    await prepararCenario()
    await abrirProntidao(page)
  })

  test('navegacao lateral usa a cor, a largura e o contraste canonicos', async ({ page }) => {
    const navegacao = page.getByRole('navigation', { name: 'Navegação principal' })
    expect(await estiloDe(navegacao, 'background-color')).toBe(COR.fundoNavegacao)
    expect(await estiloDe(navegacao, 'width')).toBe(LARGURA_NAVEGACAO)
    expect(await estiloDe(navegacao, 'color')).toBe(COR.sobreEscuro)
  })

  test('faixa de demonstracao usa o fundo secundario, persiste e nao pode ser fechada', async ({
    page,
  }) => {
    const faixa = page.locator('.faixa-simulacao')
    expect(await estiloDe(faixa, 'background-color')).toBe(COR.fundoNavegacaoSecundario)
    expect(await estiloDe(faixa, 'color')).toBe(COR.sobreEscuro)
    expect(await estiloDe(faixa, 'min-height')).toBe(ALTURA_MINIMA_CONTROLE)
    await expect(faixa.getByText('Ambiente educacional')).toBeVisible()
    await expect(faixa.getByRole('button')).toHaveCount(0)
  })

  test('barra de contexto separa o conteudo com a cor de borda canonica', async ({ page }) => {
    const barra = page.locator('.barra-contexto')
    expect(await estiloDe(barra, 'border-bottom-color')).toBe(COR.borda)
  })

  test('controles respeitam a altura minima e o raio pequeno', async ({ page }) => {
    const item = page.getByRole('button', { name: 'Prontidão' })
    expect(await estiloDe(item, 'min-height')).toBe(ALTURA_MINIMA_CONTROLE)
    expect(await estiloDe(item, 'border-radius')).toBe(RAIO_PEQUENO)

    const acao = page.getByRole('button', { name: 'Verificar novamente: INMET' })
    expect(await estiloDe(acao, 'min-height')).toBe(ALTURA_MINIMA_CONTROLE)
  })

  test('tipografia usa Inter no corpo e Roboto Condensed nos titulos', async ({ page }) => {
    const titulo = page.getByRole('heading', { name: 'Prontidão das dependências' })
    expect(await estiloDe(titulo, 'font-family')).toBe(FAMILIA_TITULO)
    expect(await estiloDe(titulo, 'font-weight')).toBe('700')

    const corpo = page.locator('.introducao')
    expect(await estiloDe(corpo, 'font-family')).toBe(FAMILIA_CORPO)
  })

  test('todo controle recebe foco visivel com a espessura canonica', async ({ page }) => {
    await page.getByRole('button', { name: 'Prontidão' }).press('Tab')
    const focado = page.locator(':focus-visible')
    await expect(focado).toHaveCount(1)
    expect(await estiloDe(focado, 'outline-style')).toBe('solid')
    expect(await estiloDe(focado, 'outline-width')).toBe(ESPESSURA_FOCO)
  })
})

test.describe('E2E-12: nenhum controle inerte e nenhum dado fixo', () => {
  test.beforeEach(async () => {
    await prepararCenario()
  })

  test('a re-verificacao de prontidao reflete a dependencia real, nao um estado fixo', async ({
    page,
  }) => {
    await abrirProntidao(page)
    const linhaInmet = page
      .getByRole('row')
      .filter({ has: page.getByRole('rowheader', { name: 'INMET' }) })

    // Com o INMET fora do ar, a mesma ação precisa produzir o estado oposto.
    await programarSondaInmet([{ falha: 'conexao' }])
    await linhaInmet.getByRole('button', { name: 'Verificar novamente: INMET' }).click()
    await expect(linhaInmet.getByText('Indisponível', { exact: true })).toBeVisible()
    await expect(linhaInmet.getByText('Falha de conexão ao consultar o INMET.')).toBeVisible()

    // De volta ao ar, a mesma ação precisa voltar atrás: o valor vem da sonda, não da tela.
    await programarSondaInmet([{ status: 200, corpo: { ok: true } }])
    await linhaInmet.getByRole('button', { name: 'Verificar novamente: INMET' }).click()
    await expect(linhaInmet.getByText('Disponível', { exact: true })).toBeVisible()
  })

  test('restaurar dados sinteticos confirma, executa e informa a conclusao', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('button', { name: 'Restaurar dados sintéticos' }).click()

    // O botão da superfície abre o modal de confirmação, não restaura direto.
    await page.getByRole('button', { name: 'Restaurar demonstração' }).click()
    const modal = page.getByRole('dialog')
    await expect(modal).toBeVisible()
    await expect(modal.getByRole('button', { name: 'Cancelar' })).toBeVisible()

    // A confirmação executa a restauração real e informa o desfecho.
    await modal.getByRole('button', { name: 'Confirmar restauração' }).click()
    await expect(modal.getByText(/Dados sintéticos restaurados/)).toBeVisible()
    await modal.getByRole('button', { name: 'Concluir' }).click()
    await expect(modal).toBeHidden()
  })

  test('a documentacao da API reflete a verificacao real do backend', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('button', { name: 'Documentação da API' }).click()

    const superficie = conteudoComTexto(page, 'Documentação da API')
    await expect(superficie.getByText('Disponível', { exact: true })).toBeVisible()
    await expect(superficie.getByRole('link')).toHaveAttribute(
      'href',
      'http://127.0.0.1:8000/docs',
    )
  })

  test('trocar o segurado troca os dados exibidos, que nao sao fixos', async ({ page }) => {
    await abrirPainelSegurado(page, NOME_SEGURADO_CHUVA_ELEGIVEL)
    await expect(apoliceExibida(page).getByText('DEMO-RES-0001')).toBeVisible()

    await page.getByLabel('Visualizar como').selectOption({ label: NOME_SEGURADO_GRANIZO_ELEGIVEL })
    await expect(
      page.getByLabel('Visualizar como').locator('option:checked'),
    ).toHaveText(NOME_SEGURADO_GRANIZO_ELEGIVEL)

    await expect(apoliceExibida(page).getByText('DEMO-AUT-0003')).toBeVisible()
    await expect(apoliceExibida(page).getByText('DEMO-RES-0001')).toHaveCount(0)
  })

  test('as preferencias do segurado sao gravadas, nao apenas exibidas', async ({ page }) => {
    await abrirPainelSegurado(page, NOME_SEGURADO_CHUVA_ELEGIVEL)
    const meusDados = conteudoComTexto(page, 'Meus Dados')

    const antes = await obterPreferencias(SEGURADO_CHUVA_ELEGIVEL_ID)
    expect(antes.participa_de_alertas).toBe(true)

    const participacao = meusDados.getByRole('checkbox', { name: 'Participar de alertas' })
    await expect(participacao).toBeChecked()
    await participacao.uncheck()
    await meusDados.getByRole('button', { name: 'Salvar' }).click()
    await expect(meusDados.getByText('Salvo', { exact: true })).toBeVisible()

    // A gravação chegou à fonte da verdade: o controle escreve no backend, não só na tela.
    await expect
      .poll(async () => (await obterPreferencias(SEGURADO_CHUVA_ELEGIVEL_ID)).participa_de_alertas)
      .toBe(false)
    const depois = await obterPreferencias(SEGURADO_CHUVA_ELEGIVEL_ID)
    expect(depois.versao).toBe(antes.versao + 1)
  })
})
