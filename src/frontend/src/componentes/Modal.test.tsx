import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { Modal } from './Modal'

const TITULO = 'Restaurar demonstração'
const OBJETO = 'Dados sintéticos da demonstração'
const IMPACTO = 'As alterações locais serão perdidas.'

function renderizarModal(sobrescritas: Partial<Parameters<typeof Modal>[0]> = {}) {
  const onConfirmar = vi.fn()
  const onFechar = vi.fn()
  render(
    <Modal
      aberto
      impacto={IMPACTO}
      objeto={OBJETO}
      onConfirmar={onConfirmar}
      onFechar={onFechar}
      titulo={TITULO}
      {...sobrescritas}
    />,
  )
  return { onConfirmar, onFechar }
}

/** Abre e fecha o modal a partir de um botão, para observar o retorno do foco. */
function Acionador({ podeFechar = true }: { podeFechar?: boolean }) {
  const [aberto, definirAberto] = useState(false)
  return (
    <>
      <button onClick={() => definirAberto(true)} type="button">
        Abrir
      </button>
      <Modal
        aberto={aberto}
        impacto={IMPACTO}
        objeto={OBJETO}
        onConfirmar={() => definirAberto(false)}
        onFechar={() => definirAberto(false)}
        podeFechar={podeFechar}
        titulo={TITULO}
      />
    </>
  )
}

describe('modal de confirmação', () => {
  it('apresenta título, objeto e impacto da ação', () => {
    renderizarModal()

    expect(screen.getByRole('dialog', { name: TITULO })).toBeInTheDocument()
    expect(screen.getByText(OBJETO)).toBeInTheDocument()
    expect(screen.getByText(IMPACTO)).toBeInTheDocument()
  })

  it('prende o foco no modal ao navegar com Tab e Shift+Tab', async () => {
    const usuario = userEvent.setup()
    renderizarModal()
    const cancelar = screen.getByRole('button', { name: 'Cancelar' })
    const confirmar = screen.getByRole('button', { name: 'Confirmar' })

    expect(cancelar).toHaveFocus()
    await usuario.tab()
    expect(confirmar).toHaveFocus()
    await usuario.tab()
    expect(cancelar).toHaveFocus()
    await usuario.tab({ shift: true })
    expect(confirmar).toHaveFocus()
  })

  it('fecha com Esc quando o fechamento é permitido', async () => {
    const usuario = userEvent.setup()
    const { onFechar } = renderizarModal()

    await usuario.keyboard('{Escape}')

    expect(onFechar).toHaveBeenCalledTimes(1)
  })

  it('ignora Esc enquanto o fechamento não é permitido', async () => {
    const usuario = userEvent.setup()
    const { onFechar } = renderizarModal({ podeFechar: false })

    await usuario.keyboard('{Escape}')

    expect(onFechar).not.toHaveBeenCalled()
  })

  it('devolve o foco ao controle de origem ao fechar', async () => {
    const usuario = userEvent.setup()
    render(<Acionador />)
    const abrir = screen.getByRole('button', { name: 'Abrir' })

    await usuario.click(abrir)
    expect(screen.getByRole('dialog', { name: TITULO })).toBeInTheDocument()
    await usuario.keyboard('{Escape}')

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(abrir).toHaveFocus()
  })

  it('confirma exatamente uma vez por clique', async () => {
    const usuario = userEvent.setup()
    const { onConfirmar } = renderizarModal()

    await usuario.click(screen.getByRole('button', { name: 'Confirmar' }))

    expect(onConfirmar).toHaveBeenCalledTimes(1)
  })

  it('confirma exatamente uma vez por Enter no botão de confirmação', async () => {
    const usuario = userEvent.setup()
    const { onConfirmar } = renderizarModal()
    screen.getByRole('button', { name: 'Confirmar' }).focus()

    await usuario.keyboard('{Enter}')

    expect(onConfirmar).toHaveBeenCalledTimes(1)
  })

  it('desabilita a confirmação enquanto a ação está em andamento', async () => {
    const usuario = userEvent.setup()
    const { onConfirmar } = renderizarModal({ confirmacaoDesabilitada: true })
    const confirmar = screen.getByRole('button', { name: 'Confirmar' })

    expect(confirmar).toBeDisabled()
    await usuario.click(confirmar)

    expect(onConfirmar).not.toHaveBeenCalled()
  })

  it('não renderiza nada enquanto estiver fechado', () => {
    renderizarModal({ aberto: false })

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })
})
