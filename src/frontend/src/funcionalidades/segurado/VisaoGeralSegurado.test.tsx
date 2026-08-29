import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { VisaoGeralSegurado } from './VisaoGeralSegurado'

describe('VisaoGeralSegurado', () => {
  it('renderiza o alerta, as ações preventivas e o painel contextual sem referência a Marina Costa', () => {
    render(<VisaoGeralSegurado />)

    expect(screen.getByRole('heading', { name: 'Chuva intensa e rajadas de vento' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Como se prevenir' })).toBeInTheDocument()
    expect(
      screen.getByText('Evite estacionar o veículo próximo a árvores e estruturas frágeis.'),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('heading', { name: 'Por que este alerta é relevante?' }),
    ).toBeInTheDocument()
    expect(screen.queryByText(/Marina/)).not.toBeInTheDocument()
  })

  it('não renderiza nenhum dado de segurado (nome) - vem só da BarraContexto', () => {
    render(<VisaoGeralSegurado />)

    expect(screen.queryByText(/Pessoa Segurada Sintética/)).not.toBeInTheDocument()
    expect(screen.queryByText('Segurado ativo')).not.toBeInTheDocument()
  })
})
