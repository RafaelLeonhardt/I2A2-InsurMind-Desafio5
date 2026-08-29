import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { FaixaDemonstracao } from './FaixaDemonstracao'

describe('FaixaDemonstracao', () => {
  it('exibe a faixa fixa "Ambiente educacional · Dados sintéticos · Sem envio real"', () => {
    render(<FaixaDemonstracao />)

    expect(
      screen.getByText('Ambiente educacional · Dados sintéticos · Sem envio real'),
    ).toBeInTheDocument()
  })

  it('não contém nenhum elemento interativo de fechamento', () => {
    render(<FaixaDemonstracao />)

    expect(screen.queryByRole('button')).not.toBeInTheDocument()
    expect(screen.queryByRole('link')).not.toBeInTheDocument()
  })
})
