import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it } from 'vitest'
import App from './App'

function definirLargura(largura: number) {
  Object.defineProperty(window, 'innerWidth', { configurable: true, value: largura })
}

afterEach(() => {
  cleanup()
  definirLargura(1024)
})

describe('shell da Central Preventiva', () => {
  it('mantém os avisos persistentes da demonstração', () => {
    definirLargura(1440)
    render(<App />)
    expect(screen.getAllByText('Ambiente educacional').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Dados sintéticos').length).toBeGreaterThan(0)
    expect(screen.getByText(/Sem envio real/)).toBeInTheDocument()
  })

  it('oferece landmarks e navegação por teclado', async () => {
    definirLargura(1440)
    const usuario = userEvent.setup()
    render(<App />)
    expect(screen.getByRole('navigation', { name: 'Navegação principal' })).toBeInTheDocument()
    expect(screen.getByRole('main')).toBeInTheDocument()
    expect(screen.getByRole('complementary')).toBeInTheDocument()
    const atalho = screen.getByRole('link', { name: 'Pular para o conteúdo principal' })
    await usuario.tab()
    expect(atalho).toHaveFocus()
    expect(atalho).toHaveAttribute('href', '#conteudo-principal')
    await usuario.keyboard('{Enter}')
    expect(screen.getByRole('main')).toHaveFocus()
  })

  it('mantém o aviso consultivo para telas menores no documento', () => {
    definirLargura(1024)
    render(<App />)
    expect(screen.queryByRole('note')).not.toBeInTheDocument()
    definirLargura(1023)
    fireEvent(window, new Event('resize'))
    expect(screen.getByRole('note')).toHaveTextContent('Todas as funções permanecem disponíveis')
    expect(screen.getByRole('link', { name: 'Alertas' })).toHaveAttribute('href', '#titulo-alerta')
    expect(screen.getByRole('link', { name: 'Minha apólice' })).toHaveAttribute('href', '#titulo-contexto')
  })
})
