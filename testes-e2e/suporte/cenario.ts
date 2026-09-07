/** Preparo comum a todo cenário E2E e navegação até o painel do perfil Segurado (5.8). */

import { expect, type Page } from '@playwright/test'
import { restaurarDadosSinteticos } from './api.ts'
import { resetarDubles } from './dubles-cliente.ts'

/**
 * Devolve o ambiente ao estado inicial determinístico antes de um cenário.
 *
 * A restauração usa o endpoint REST ao vivo, nunca o CLI `composicao.inicializador`: o
 * servidor está no ar durante toda a suíte e o DuckDB aceita um único escritor. Ela repõe o
 * estado inicial completo, apagando também as tabelas produzidas por execuções anteriores
 * (AD-014) — é o que garante que rodar a suíte duas vezes dê o mesmo resultado.
 */
export async function prepararCenario(): Promise<void> {
  await restaurarDadosSinteticos()
  await resetarDubles()
}

/**
 * Abre a interface real na superfície de Prontidão do perfil Administrador.
 *
 * O shell inicia no perfil Administrador com Prontidão como primeira superfície; a navegação
 * lateral é o caminho real até ela, e clicá-la explicitamente mantém o teste correto mesmo se
 * a ordem das superfícies mudar.
 */
export async function abrirProntidao(page: Page): Promise<void> {
  await page.goto('/')

  // O perfil ativo é persistido em `localStorage`, então um cenário que já visitou o painel
  // do Segurado recarrega nele. A volta é pelo mesmo botão real da barra de contexto.
  const alternarPerfil = page.getByRole('button', { name: /^Visualizar como / })
  await expect(alternarPerfil).toBeVisible()
  if ((await alternarPerfil.textContent())?.includes('Administrador')) {
    await alternarPerfil.click()
  }

  await page.getByRole('button', { name: 'Prontidão' }).click()
  await expect(page.getByRole('heading', { name: 'Prontidão das dependências' })).toBeVisible()
}

/**
 * Abre a interface real, troca para o perfil Segurado e seleciona o segurado sintético.
 *
 * O shell inicia no perfil Administrador; o botão "Visualizar como Segurado" da barra de
 * contexto é o caminho real de troca, e o `select` "Visualizar como" do painel escolhe qual
 * segurado sintético as cinco superfícies exibem (5.7).
 */
export async function abrirPainelSegurado(page: Page, nomeSegurado: string): Promise<void> {
  await page.goto('/')
  await page.getByRole('button', { name: 'Visualizar como Segurado' }).click()

  const seletor = page.getByLabel('Visualizar como')
  await expect(seletor).toBeEnabled()
  await seletor.selectOption({ label: nomeSegurado })

  // Confirma que a troca foi validada antes de qualquer asserção do cenário: o seletor só
  // exibe o novo nome depois que `SeguradoContexto` conclui a troca. Sem isso, uma troca que
  // não se aplicasse apareceria adiante como um erro obscuro de elemento, não como a falha
  // que de fato é.
  await expect(seletor.locator('option:checked')).toHaveText(nomeSegurado)
}
