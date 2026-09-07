/**
 * E2E-13 (parte assistida) — checklist de acessibilidade que o `axe-core` não cobre sozinho.
 *
 * O AC exige teclado, foco, contraste, zoom 200%, nomes acessíveis e movimento reduzido. Três
 * desses seis são decididos por análise estática do DOM e já ficam cobertos, com zero violação
 * em todos os nove estados auditados, pelas regras do `axe-core` em `axe.spec.ts`:
 *
 * | Critério do AC | Onde é verificado |
 * | --- | --- |
 * | Contraste | regra `color-contrast` (WCAG 1.4.3) — `axe.spec.ts` |
 * | Nomes acessíveis | regras `button-name`, `link-name`, `select-name`, `label`, `image-alt` — `axe.spec.ts` |
 * | Estrutura e marcos | regras `landmark-*`, `heading-order`, `list`, `aria-*` — `axe.spec.ts` |
 * | Teclado | este arquivo: ordem, alcance, `Esc` e devolução de foco |
 * | Foco | este arquivo: foco visível e devolvido ao elemento de origem |
 * | Zoom 200% | este arquivo: refluxo sem rolagem horizontal, funções preservadas |
 * | Movimento reduzido | este arquivo: nenhuma duração de transição/animação sob `reduce` |
 *
 * Os três últimos dependem de comportamento em tempo de execução (foco real, refluxo real,
 * media query real), que é exatamente o que uma ferramenta de análise de DOM não decide.
 *
 * ## Desvios conhecidos, registrados e não silenciados
 *
 * - Os fluxos de Administrador dos Épicos 2–4 (Monitoramento, Evento e decisão, Regras,
 *   Supervisão, Resultados, Linha do tempo) não estão montados em `App.tsx` e por isso não
 *   entram nesta auditoria; item aberto registrado em `.specs/STATE.md`.
 * - Os desvios de token visual medidos estão na tabela do cabeçalho de
 *   `testes-e2e/responsividade/sistema-visual.spec.ts`; nenhum deles produz violação WCAG
 *   crítica ou séria.
 * - Refluxo da tabela de Prontidão (defeito aberto, o teste de zoom abaixo o reprova): a
 *   tabela de 6 colunas não cabe na coluna de conteúdo quando uma célula carrega o texto mais
 *   longo. Medido com o INMET indisponível: em 1024 px CSS (o piso declarado em `DESIGN.md`),
 *   `.tabela-prontidao` ocupa 922 px e o documento chega a `scrollWidth` 1060 contra
 *   `clientWidth` 1024, forçando rolagem horizontal na página inteira. Em 720 px o mesmo
 *   acontece já com o texto curto (877 px). Com todas as dependências disponíveis, o texto é
 *   curto o bastante e não há transbordo em 1440/1280/1024/900 px — por isso o defeito só
 *   aparece no estado de contingência. `EXPERIENCE.md` prevê "rolagem nomeada" para tabela
 *   operacional, ou seja, a rolagem deveria ficar dentro da própria região da tabela. A
 *   correção pertence à história da superfície de Prontidão, não a esta
 *   (ver "Out of Scope" em `spec.md`).
 */

import { expect, test, type Page } from '@playwright/test'
import {
  abrirPainelSegurado,
  abrirProntidao,
  conteudoComTexto,
  prepararCenario,
} from '../suporte/cenario.ts'
import { programarSondaInmet } from '../suporte/dubles-cliente.ts'
import { NOME_SEGURADO_CHUVA_ELEGIVEL } from '../suporte/identificadores.ts'

/**
 * `getComputedStyle` do navegador, tipado localmente: o `tsconfig` da suíte não carrega a lib
 * DOM, porque os arquivos de suporte rodam em Node.
 */
type JanelaComEstilo = {
  getComputedStyle: (elemento: unknown) => { getPropertyValue: (nome: string) => string }
  document: {
    documentElement: { scrollWidth: number; clientWidth: number }
    activeElement: { id: string; tagName: string } | null
    querySelectorAll: (seletor: string) => ArrayLike<unknown>
  }
}

/**
 * Viewport em pixels CSS que 200% de zoom produz no piso de resolução suportado.
 *
 * `DESIGN.md` declara suporte de 1024 px para cima, então o pior caso que o produto promete
 * atender com zoom de 200% é um monitor de 2048 px físicos: 1024 px CSS depois do zoom. Medir
 * o zoom a partir da referência de 1440 px levaria a 720 px CSS, faixa que o produto declara
 * não suportada e sinaliza com o aviso explícito de resolução.
 */
const ZOOM_200_NO_PISO = { width: 1024, height: 768 }

/** Devolve o `id` e a tag do elemento com foco no momento. */
function elementoFocado(page: Page): Promise<{ id: string; tagName: string } | null> {
  return page.evaluate(() => {
    const ativo = (globalThis as unknown as JanelaComEstilo).document.activeElement
    return ativo === null ? null : { id: ativo.id, tagName: ativo.tagName }
  })
}

test.describe('E2E-13: checklist assistida de acessibilidade', () => {
  test.beforeEach(async () => {
    await prepararCenario()
  })

  test('teclado: o primeiro tab alcanca o atalho que leva ao conteudo principal', async ({
    page,
  }) => {
    // Sem clique antes: o teste é sobre a ordem de tabulação a partir do início do documento.
    await page.goto('/')
    await expect(page.getByRole('heading', { name: 'Prontidão das dependências' })).toBeVisible()

    await page.keyboard.press('Tab')
    const atalho = page.getByRole('link', { name: 'Pular para o conteúdo principal' })
    await expect(atalho).toBeFocused()

    await atalho.press('Enter')
    expect(await elementoFocado(page)).toEqual({ id: 'conteudo-principal', tagName: 'MAIN' })
  })

  test('teclado: a navegacao lateral inteira e alcancavel e acionavel sem mouse', async ({
    page,
  }) => {
    await page.goto('/')
    await expect(page.getByRole('heading', { name: 'Prontidão das dependências' })).toBeVisible()

    // Do atalho até cada item da navegação, apenas com Tab, na ordem visual.
    await page.keyboard.press('Tab')
    for (const rotulo of ['Prontidão', 'Restaurar dados sintéticos', 'Documentação da API']) {
      await page.keyboard.press('Tab')
      await expect(page.getByRole('button', { name: rotulo })).toBeFocused()
    }

    // E o item focado responde ao teclado, não só ao clique.
    await page.keyboard.press('Enter')
    await expect(page.getByRole('heading', { name: 'Documentação da API' })).toBeVisible()
  })

  test('foco: o modal recebe o foco, fecha com Esc e devolve o foco a origem', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('button', { name: 'Restaurar dados sintéticos' }).click()

    const abrir = page.getByRole('button', { name: 'Restaurar demonstração' })
    await abrir.click()

    const modal = page.getByRole('dialog')
    await expect(modal).toBeVisible()
    await expect(modal).toHaveAttribute('aria-modal', 'true')

    // O foco entra no modal, não fica para trás na superfície.
    const dentro = await modal.evaluate((elemento) => {
      const ativo = (globalThis as unknown as JanelaComEstilo).document.activeElement
      return ativo !== null && (elemento as { contains: (no: unknown) => boolean }).contains(ativo)
    })
    expect(dentro).toBe(true)

    await page.keyboard.press('Escape')
    await expect(modal).toBeHidden()
    await expect(abrir).toBeFocused()
  })

  test('foco: sair do detalhe do alerta devolve o foco ao item que o abriu', async ({ page }) => {
    await abrirPainelSegurado(page, NOME_SEGURADO_CHUVA_ELEGIVEL)

    const alertas = conteudoComTexto(page, 'Seus alertas')
    const abrirDetalhe = alertas.getByRole('button', { name: 'Ver detalhe' }).first()
    const idOrigem = await abrirDetalhe.getAttribute('id')
    await abrirDetalhe.click()

    const detalhe = conteudoComTexto(page, 'Contexto da apólice')
    await expect(detalhe).toBeVisible()
    await detalhe.getByRole('button', { name: /Voltar/i }).click()

    expect((await elementoFocado(page))?.id).toBe(idOrigem)
  })

  test('zoom 200%: o conteudo reflui sem rolagem horizontal e sem perder funcao', async ({
    page,
  }) => {
    await page.setViewportSize(ZOOM_200_NO_PISO)
    await abrirProntidao(page)

    // A medição é feita no estado de maior densidade textual da superfície, não no mais
    // curto: "INMET indisponível" é um estado obrigatório de Prontidão (`EXPERIENCE.md`) e é
    // o que a tabela exibe durante uma contingência. Medir só o texto curto faria este teste
    // passar por sorte, conforme o estado que a suíte tivesse deixado no processo do backend.
    await programarSondaInmet([{ falha: 'conexao' }])
    const linhaInmet = page
      .getByRole('row')
      .filter({ has: page.getByRole('rowheader', { name: 'INMET' }) })
    await linhaInmet.getByRole('button', { name: 'Verificar novamente: INMET' }).click()
    await expect(linhaInmet.getByText('Indisponível', { exact: true })).toBeVisible()

    const rolagem = await page.evaluate(() => {
      const raiz = (globalThis as unknown as JanelaComEstilo).document.documentElement
      return { conteudo: raiz.scrollWidth, visivel: raiz.clientWidth }
    })
    expect(rolagem.conteudo).toBeLessThanOrEqual(rolagem.visivel)

    // Dentro da faixa suportada não há aviso de resolução, e nada de essencial some.
    await expect(page.getByRole('note')).toHaveCount(0)
    await expect(page.getByRole('table', { name: 'Prontidão das 4 dependências' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Verificar novamente: INMET' })).toBeEnabled()
    await expect(page.getByRole('button', { name: 'Documentação da API' })).toBeVisible()
  })

  test('movimento reduzido: nenhuma transicao ou animacao permanece ativa', async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' })
    await abrirPainelSegurado(page, NOME_SEGURADO_CHUVA_ELEGIVEL)

    const emMovimento = await page.evaluate(() => {
      const janela = globalThis as unknown as JanelaComEstilo
      const duracaoNaoNula = (valor: string) =>
        valor
          .split(',')
          .map((parte) => parte.trim())
          .some((parte) => parte !== '' && parte !== '0s' && parte !== '0ms')

      const encontrados: string[] = []
      const elementos = janela.document.querySelectorAll('*')
      for (let indice = 0; indice < elementos.length; indice += 1) {
        const elemento = elementos[indice]
        const estilo = janela.getComputedStyle(elemento)
        if (
          duracaoNaoNula(estilo.getPropertyValue('transition-duration')) ||
          duracaoNaoNula(estilo.getPropertyValue('animation-duration'))
        ) {
          encontrados.push((elemento as { className?: string }).className ?? '(sem classe)')
        }
      }
      return encontrados
    })
    expect(emMovimento).toEqual([])
  })
})
