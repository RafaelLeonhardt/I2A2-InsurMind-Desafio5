import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { SuperficieFAQ } from './SuperficieFAQ'

const PERGUNTAS = [
  'Por que recebi este alerta?',
  'A mensagem foi realmente enviada?',
  'Quais dados a IA utiliza?',
  'Como trocar o segurado simulado?',
]

describe('SuperficieFAQ', () => {
  it('exibe as quatro perguntas com resposta visível ao montar, sem nenhuma chamada de API (FAQ-01)', () => {
    render(<SuperficieFAQ />)

    for (const pergunta of PERGUNTAS) {
      const detalhe = screen.getByText(pergunta).closest('details')
      expect(detalhe).not.toBeNull()
      expect(detalhe).toHaveAttribute('open')
    }
    expect(screen.getByText(/nenhuma mensagem real é enviada/i)).toBeVisible()
  })

  it('declara que o ambiente é educacional, os dados são sintéticos e não há envio real (FAQ-02)', () => {
    render(<SuperficieFAQ />)

    expect(
      screen.getByText(
        'Ambiente educacional. Dados sintéticos. Nenhum envio real de mensagens é realizado.',
      ),
    ).toBeInTheDocument()
  })

  it('cada pergunta é independentemente colapsável sem afetar as demais (FAQ-03/04)', async () => {
    const usuario = userEvent.setup()
    render(<SuperficieFAQ />)

    const primeiraPergunta = screen.getByText(PERGUNTAS[0])
    const segundaPergunta = screen.getByText(PERGUNTAS[1])
    const primeiroDetalhe = primeiraPergunta.closest('details')
    const segundoDetalhe = segundaPergunta.closest('details')
    if (!primeiroDetalhe || !segundoDetalhe) throw new Error('details não encontrado')

    expect(primeiroDetalhe.open).toBe(true)
    expect(segundoDetalhe.open).toBe(true)

    await usuario.click(primeiraPergunta)
    expect(primeiroDetalhe.open).toBe(false)
    expect(segundoDetalhe.open).toBe(true)

    await usuario.click(primeiraPergunta)
    expect(primeiroDetalhe.open).toBe(true)
    expect(segundoDetalhe.open).toBe(true)
  })

  it('renderiza como section sem id/foco próprios quando comoSecao (composição em PainelSegurado)', () => {
    const { container } = render(<SuperficieFAQ comoSecao />)

    expect(container.querySelector('main')).not.toBeInTheDocument()
    const secao = container.querySelector('section')
    expect(secao).not.toBeNull()
    expect(secao).not.toHaveAttribute('id')
  })
})
