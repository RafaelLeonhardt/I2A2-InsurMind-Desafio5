import { screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

describe('bootstrap do frontend', () => {
  beforeEach(() => {
    vi.resetModules()
    document.body.innerHTML = '<div id="root"></div>'
    Object.defineProperty(window, 'innerWidth', { configurable: true, value: 1024 })
    window.history.pushState({}, '', '/')
  })

  it('monta a shell no elemento raiz do documento', async () => {
    await import('./main')

    expect(await screen.findByRole('heading', { name: /Olá, Marina/ })).toBeInTheDocument()
    expect(document.querySelector('#root > .aplicacao')).not.toBeNull()
  })

  it('monta a superfície de restauração no caminho administrativo', async () => {
    window.history.pushState({}, '', '/administracao/restaurar-demonstracao')

    await import('./main')

    expect(
      await screen.findByRole('heading', { name: 'Restaurar demonstração' }),
    ).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: /Olá, Marina/ })).not.toBeInTheDocument()
  })
})
