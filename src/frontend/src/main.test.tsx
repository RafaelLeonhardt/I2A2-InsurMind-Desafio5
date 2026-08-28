import { screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

describe('bootstrap do frontend', () => {
  beforeEach(() => {
    vi.resetModules()
    document.body.innerHTML = '<div id="root"></div>'
    Object.defineProperty(window, 'innerWidth', { configurable: true, value: 1024 })
  })

  it('monta a shell no elemento raiz do documento', async () => {
    await import('./main')

    expect(await screen.findByRole('heading', { name: /Olá, Marina/ })).toBeInTheDocument()
    expect(document.querySelector('#root > .aplicacao')).not.toBeNull()
  })
})
