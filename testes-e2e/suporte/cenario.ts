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
  await expect(seletor).toHaveValue(/.+/)
}
