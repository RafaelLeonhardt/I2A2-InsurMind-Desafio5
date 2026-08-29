import { screen } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'

describe('bootstrap do frontend', () => {
  beforeEach(() => {
    document.body.innerHTML = '<div id="root"></div>'
    Object.defineProperty(window, 'innerWidth', { configurable: true, value: 1024 })
    window.localStorage.clear()
  })

  it('monta o shell do contexto demonstrativo no elemento raiz do documento', async () => {
    await import('./main')

    expect(await screen.findByRole('navigation', { name: 'Navegação principal' })).toBeInTheDocument()
    expect(document.querySelector('#root > .aplicacao')).not.toBeNull()
  })
})
