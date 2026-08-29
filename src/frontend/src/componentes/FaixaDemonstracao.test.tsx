import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { FaixaDemonstracao } from './FaixaDemonstracao'

describe('FaixaDemonstracao', () => {
  it('exibe os três textos fixos da faixa demonstrativa', () => {
    render(<FaixaDemonstracao />)

    expect(screen.getByText('Dados sintéticos')).toBeInTheDocument()
    expect(screen.getByText(/Ambiente educacional/)).toBeInTheDocument()
    expect(screen.getByText('Sem envio real')).toBeInTheDocument()
  })

  it('não contém nenhum elemento interativo de fechamento', () => {
    render(<FaixaDemonstracao />)

    expect(screen.queryByRole('button')).not.toBeInTheDocument()
    expect(screen.queryByRole('link')).not.toBeInTheDocument()
  })
})
