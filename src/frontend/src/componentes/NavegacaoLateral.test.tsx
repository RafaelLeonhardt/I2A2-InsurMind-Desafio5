import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it } from 'vitest'
import { CHAVE_ARMAZENAMENTO_PERFIL, PerfilProvider } from '../contexto/PerfilContexto'
import { NavegacaoLateral } from './NavegacaoLateral'

function renderizarComPerfil(perfil: 'administrador' | 'segurado') {
  window.localStorage.setItem(CHAVE_ARMAZENAMENTO_PERFIL, perfil)
  return render(
    <PerfilProvider>
      <NavegacaoLateral />
    </PerfilProvider>,
  )
}

afterEach(() => {
  window.localStorage.clear()
})

describe('NavegacaoLateral', () => {
  it('no perfil Administrador, mostra somente "Prontidão" e "Restaurar dados sintéticos"', () => {
    renderizarComPerfil('administrador')

    expect(screen.getByRole('button', { name: /Prontidão/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Restaurar dados sintéticos/ })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Visão geral/ })).not.toBeInTheDocument()
  })

  it('no perfil Segurado, mostra somente "Visão geral"', () => {
    renderizarComPerfil('segurado')

    expect(screen.getByRole('button', { name: /Visão geral/ })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Prontidão/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Restaurar dados sintéticos/ })).not.toBeInTheDocument()
  })

  it('o item correspondente à superficieAtiva recebe aria-current="page" por padrão', () => {
    renderizarComPerfil('administrador')

    expect(screen.getByRole('button', { name: /Prontidão/ })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('button', { name: /Restaurar dados sintéticos/ })).not.toHaveAttribute(
      'aria-current',
    )
  })

  it('ativar um item por clique chama selecionarSuperficie, movendo o aria-current', async () => {
    const usuario = userEvent.setup()
    renderizarComPerfil('administrador')

    await usuario.click(screen.getByRole('button', { name: /Restaurar dados sintéticos/ }))

    expect(screen.getByRole('button', { name: /Restaurar dados sintéticos/ })).toHaveAttribute(
      'aria-current',
      'page',
    )
    expect(screen.getByRole('button', { name: /Prontidão/ })).not.toHaveAttribute('aria-current')
  })

  it('ativar um item por Enter, com foco por Tab, chama selecionarSuperficie', async () => {
    const usuario = userEvent.setup()
    renderizarComPerfil('administrador')

    await usuario.tab()
    expect(screen.getByRole('button', { name: /Prontidão/ })).toHaveFocus()
    await usuario.tab()
    expect(screen.getByRole('button', { name: /Restaurar dados sintéticos/ })).toHaveFocus()
    await usuario.keyboard('{Enter}')

    expect(screen.getByRole('button', { name: /Restaurar dados sintéticos/ })).toHaveAttribute(
      'aria-current',
      'page',
    )
  })
})
