import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { ContextoInconsistente } from './ContextoInconsistente'

describe('ContextoInconsistente', () => {
  it('exibe uma mensagem explicando o bloqueio, sem mostrar dado de superfície', () => {
    render(<ContextoInconsistente aoVoltar={vi.fn()} perfil="segurado" />)

    expect(
      screen.getByText(/contexto solicitado está ausente ou não é compatível/i),
    ).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })

  it('chama aoVoltar ao ativar o botão por clique', async () => {
    const aoVoltar = vi.fn()
    const usuario = userEvent.setup()
    render(<ContextoInconsistente aoVoltar={aoVoltar} perfil="administrador" />)

    await usuario.click(screen.getByRole('button', { name: 'Voltar para a Visão geral' }))

    expect(aoVoltar).toHaveBeenCalledTimes(1)
  })

  it('chama aoVoltar ao ativar o botão por Enter, com foco por Tab', async () => {
    const aoVoltar = vi.fn()
    const usuario = userEvent.setup()
    render(<ContextoInconsistente aoVoltar={aoVoltar} perfil="administrador" />)

    await usuario.tab()
    expect(screen.getByRole('button', { name: 'Voltar para a Visão geral' })).toHaveFocus()
    await usuario.keyboard('{Enter}')

    expect(aoVoltar).toHaveBeenCalledTimes(1)
  })
})
