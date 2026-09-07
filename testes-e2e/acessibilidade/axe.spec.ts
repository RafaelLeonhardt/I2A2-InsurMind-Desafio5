/**
 * E2E-13 (parte automatizada) — auditoria WCAG 2.2 AA com `@axe-core/playwright`.
 *
 * Cada fluxo principal alcançável pela navegação real é analisado no Chromium, com as regras
 * de WCAG 2.0/2.1/2.2 nos níveis A e AA. O AC exige zero violação crítica ou séria; violações
 * de impacto moderado ou menor são relatadas na mensagem de falha e listadas no cabeçalho de
 * `checklist-manual.spec.ts`, nunca silenciadas.
 *
 * Fluxos auditados: Prontidão (estado normal e com dependência indisponível), Restaurar dados
 * sintéticos (superfície e modal de confirmação), Documentação da API, e o painel do Segurado
 * com dado real produzido por um cenário concluído — visão geral, alertas, apólice,
 * comunicados e meus dados, mais o detalhe do alerta e o detalhe do comunicado.
 *
 * Fluxos não auditáveis aqui: Monitoramento, Evento e decisão, Regras, Supervisão, Resultados
 * e Linha do tempo da execução. As superfícies existem e têm suíte `vitest` própria, mas não
 * estão montadas em `App.tsx` (item aberto registrado em `.specs/STATE.md`) — o `axe-core`
 * roda contra uma página real, e não há navegação que as alcance. Isso está registrado aqui
 * como lacuna conhecida da auditoria, não como aprovação.
 */

import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page } from '@playwright/test'
import { ESTACAO_CHUVA } from '../suporte/ambiente.ts'
import {
  aguardarEstado,
  confirmarSimulacao,
  decidirLote,
  iniciarExecucao,
  obterLoteRevisao,
  obterSimulacao,
  solicitarPreflight,
} from '../suporte/api.ts'
import {
  abrirPainelSegurado,
  abrirProntidao,
  conteudoComTexto,
  prepararCenario,
} from '../suporte/cenario.ts'
import { programarInmet, programarSondaInmet } from '../suporte/dubles-cliente.ts'
import { AREA_CHUVA_ID, NOME_SEGURADO_CHUVA_ELEGIVEL } from '../suporte/identificadores.ts'

/** Conjunto de regras da auditoria: WCAG 2.0, 2.1 e 2.2, níveis A e AA. */
const ETIQUETAS_WCAG = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa']

/** Impactos que o AC proíbe por completo. */
const IMPACTOS_PROIBIDOS = new Set(['critical', 'serious'])

/** Acima do limiar de 50 mm da regra de chuva intensa semeada (`semeador.py`). */
const CHUVA_ACIMA_DO_LIMIAR_MM = 55.4

type Violacao = { id: string; impact: string | null | undefined; alvos: string[] }

/**
 * Roda o `axe-core` na página e devolve as violações encontradas, já resumidas.
 *
 * A lista completa é devolvida (não só as proibidas) para que a mensagem de falha mostre o
 * quadro inteiro: uma auditoria que só conta o que reprova esconde o resto.
 */
async function auditar(page: Page): Promise<Violacao[]> {
  const resultado = await new AxeBuilder({ page }).withTags(ETIQUETAS_WCAG).analyze()
  return resultado.violations.map((violacao) => ({
    id: violacao.id,
    impact: violacao.impact,
    alvos: violacao.nodes.map((no) => no.target.join(' ')),
  }))
}

/**
 * Falha o fluxo se houver qualquer violação crítica ou séria, citando todas as encontradas.
 *
 * O que sobra (moderado/menor) não reprova o AC, mas é anexado ao relatório do Playwright:
 * uma auditoria que só registra o que reprova esconde o resto, e o Edge Case de `spec.md`
 * exige desvio documentado, nunca silenciado.
 */
function exigirSemCriticasNemSerias(fluxo: string, violacoes: Violacao[]): void {
  test.info().annotations.push({
    type: 'axe',
    description: `${fluxo}: ${violacoes.length === 0 ? 'nenhuma violação' : JSON.stringify(violacoes)}`,
  })
  const proibidas = violacoes.filter((violacao) =>
    IMPACTOS_PROIBIDOS.has(violacao.impact ?? ''),
  )
  expect(
    proibidas,
    `Violações críticas/sérias em "${fluxo}". Quadro completo: ${JSON.stringify(violacoes)}`,
  ).toEqual([])
}

/** Executa o cenário de chuva intensa até a conclusão, dando dado real ao perfil Segurado. */
async function executarCenarioComComunicado(): Promise<void> {
  await programarInmet([{ preset: 'chuva', milimetros: CHUVA_ACIMA_DO_LIMIAR_MM }], ESTACAO_CHUVA)
  const execucaoId = await iniciarExecucao(AREA_CHUVA_ID)
  await aguardarEstado(execucaoId, ['aguardando_geracao'])
  await solicitarPreflight(execucaoId)
  await aguardarEstado(execucaoId, ['aguardando_revisao'])
  const lote = await obterLoteRevisao(execucaoId)
  const item = lote.itens[0]!
  await decidirLote(execucaoId, [
    { mensagem_id: item.mensagem_id, versao_esperada: item.versao, resultado: 'aprovar' },
  ])
  await aguardarEstado(execucaoId, ['aguardando_confirmacao'])
  const resumo = await obterSimulacao(execucaoId)
  await confirmarSimulacao(execucaoId, resumo.versao)
}

test.describe('E2E-13: auditoria automatizada WCAG 2.2 AA', () => {
  test.beforeEach(async () => {
    await prepararCenario()
  })

  test('fluxo de Prontidao, no estado normal e com dependencia indisponivel', async ({ page }) => {
    await abrirProntidao(page)
    await expect(page.getByRole('table', { name: 'Prontidão das 4 dependências' })).toBeVisible()
    exigirSemCriticasNemSerias('Prontidão (normal)', await auditar(page))

    // O estado de erro também precisa ser acessível, não só o caminho feliz.
    await programarSondaInmet([{ falha: 'conexao' }])
    const linhaInmet = page
      .getByRole('row')
      .filter({ has: page.getByRole('rowheader', { name: 'INMET' }) })
    await linhaInmet.getByRole('button', { name: 'Verificar novamente: INMET' }).click()
    await expect(linhaInmet.getByText('Indisponível', { exact: true })).toBeVisible()
    exigirSemCriticasNemSerias('Prontidão (INMET indisponível)', await auditar(page))
  })

  test('fluxo de Restaurar dados sinteticos, com o modal de confirmacao aberto', async ({
    page,
  }) => {
    await page.goto('/')
    await page.getByRole('button', { name: 'Restaurar dados sintéticos' }).click()
    await expect(page.getByRole('heading', { name: 'Restaurar demonstração' })).toBeVisible()
    exigirSemCriticasNemSerias('Restaurar dados sintéticos', await auditar(page))

    await page.getByRole('button', { name: 'Restaurar demonstração' }).click()
    await expect(page.getByRole('dialog')).toBeVisible()
    exigirSemCriticasNemSerias('Restaurar dados sintéticos (modal)', await auditar(page))
  })

  test('fluxo de Documentacao da API', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('button', { name: 'Documentação da API' }).click()
    await expect(conteudoComTexto(page, 'Documentação da API').getByRole('link')).toBeVisible()
    exigirSemCriticasNemSerias('Documentação da API', await auditar(page))
  })

  test('painel do Segurado com dado real, do resumo ao detalhe do comunicado', async ({ page }) => {
    await executarCenarioComComunicado()
    await abrirPainelSegurado(page, NOME_SEGURADO_CHUVA_ELEGIVEL)

    await expect(conteudoComTexto(page, 'Seus comunicados')).toBeVisible()
    exigirSemCriticasNemSerias('Painel do Segurado', await auditar(page))

    await conteudoComTexto(page, 'Seus alertas')
      .getByRole('button', { name: 'Ver detalhe' })
      .first()
      .click()
    await expect(
      conteudoComTexto(page, 'Contexto da apólice').getByRole('heading', {
        name: 'Contexto da apólice',
      }),
    ).toBeVisible()
    exigirSemCriticasNemSerias('Detalhe do alerta', await auditar(page))

    await conteudoComTexto(page, 'Seus comunicados')
      .getByRole('button', { name: 'Ver detalhe' })
      .first()
      .click()
    await expect(
      conteudoComTexto(page, 'Seu comunicado preventivo').getByRole('heading', {
        name: 'Seu comunicado preventivo',
      }),
    ).toBeVisible()
    exigirSemCriticasNemSerias('Detalhe do comunicado', await auditar(page))
  })

  test('painel do Segurado no estado vazio, sem nenhum comunicado', async ({ page }) => {
    await abrirPainelSegurado(page, NOME_SEGURADO_CHUVA_ELEGIVEL)
    await expect(conteudoComTexto(page, 'Nenhum comunicado no momento')).toBeVisible()
    exigirSemCriticasNemSerias('Painel do Segurado (vazio)', await auditar(page))
  })
})
