import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { EstadoDependencia, NomeDependencia } from '../../api/prontidao'
import { SuperficieProntidao } from './SuperficieProntidao'

const { getDependencias, solicitarNovaVerificacao } = vi.hoisted(() => ({
  getDependencias: vi.fn(),
  solicitarNovaVerificacao: vi.fn(),
}))

vi.mock('../../api/prontidao', async (importarOriginal) => ({
  ...(await importarOriginal<typeof import('../../api/prontidao')>()),
  getDependencias,
  solicitarNovaVerificacao,
}))

function linha(
  sobrescritas: Partial<EstadoDependencia> & { nome: NomeDependencia },
): EstadoDependencia {
  return {
    estado: 'disponivel',
    verificadoEm: '2026-08-29T12:00:00+00:00',
    causa: null,
    impacto: 'Nenhum.',
    acaoDisponivel: 'Nenhuma ação necessária.',
    ...sobrescritas,
  }
}

function conjuntoPadrao(): EstadoDependencia[] {
  return [
    linha({ nome: 'backend' }),
    linha({ nome: 'banco_dados' }),
    linha({ nome: 'inmet' }),
    linha({ nome: 'openai' }),
  ]
}

beforeEach(() => {
  getDependencias.mockReset()
  solicitarNovaVerificacao.mockReset()
})

describe('superfície de prontidão', () => {
  it('renderiza as 4 linhas com estado, última verificação, causa, impacto e ação', async () => {
    getDependencias.mockResolvedValue(conjuntoPadrao())
    render(<SuperficieProntidao />)

    await screen.findByRole('rowheader', { name: 'Backend' })
    expect(screen.getByRole('rowheader', { name: 'Banco de dados' })).toBeInTheDocument()
    expect(screen.getByRole('rowheader', { name: 'INMET' })).toBeInTheDocument()
    expect(screen.getByRole('rowheader', { name: 'OpenAI' })).toBeInTheDocument()
    expect(screen.getAllByText('Disponível')).toHaveLength(4)
    expect(screen.getAllByText('2026-08-29T12:00:00+00:00')).toHaveLength(4)
    expect(screen.getAllByText('Nenhum.')).toHaveLength(4)
  })

  it('marca a linha em Verificando com aria-live polite sem afetar as demais', async () => {
    getDependencias.mockResolvedValue([
      linha({ nome: 'backend' }),
      linha({ nome: 'banco_dados' }),
      linha({
        nome: 'inmet',
        estado: 'verificando',
        verificadoEm: null,
        causa: null,
        impacto: 'Verificação em andamento.',
        acaoDisponivel: 'Aguarde a conclusão ou consulte novamente em instantes.',
      }),
      linha({ nome: 'openai' }),
    ])
    render(<SuperficieProntidao />)

    const celulaVerificando = await screen.findByText('Verificando')
    expect(celulaVerificando.closest('td')).toHaveAttribute('aria-live', 'polite')
    expect(screen.getAllByText('Disponível')).toHaveLength(3)
  })

  it('diferencia Degradada de Indisponível por texto e por atributo', async () => {
    getDependencias.mockResolvedValue([
      linha({ nome: 'backend' }),
      linha({ nome: 'banco_dados' }),
      linha({ nome: 'inmet', estado: 'degradada', causa: 'Latência acima do orçamento.' }),
      linha({ nome: 'openai', estado: 'indisponivel', causa: 'Credencial ausente.' }),
    ])
    render(<SuperficieProntidao />)

    const degradada = await screen.findByText('Degradada')
    const indisponivel = await screen.findByText('Indisponível')

    expect(degradada.closest('[data-icone]')).toHaveAttribute('data-icone', 'degradada')
    expect(indisponivel.closest('[data-icone]')).toHaveAttribute('data-icone', 'indisponivel')
    expect(degradada.closest('.estado-badge')?.className).not.toBe(
      indisponivel.closest('.estado-badge')?.className,
    )
  })

  it('mostra a falha terminal na linha mesmo sem nenhum toast renderizado', async () => {
    getDependencias.mockResolvedValue([
      linha({ nome: 'backend' }),
      linha({ nome: 'banco_dados' }),
      linha({
        nome: 'inmet',
        estado: 'indisponivel',
        causa: 'Tempo limite excedido ao consultar o INMET.',
        impacto: 'Funcionalidades que dependem de dados meteorológicos do INMET ficam bloqueadas.',
        acaoDisponivel: 'Solicite uma nova verificação mais tarde ou prossiga sem esses dados.',
      }),
      linha({ nome: 'openai' }),
    ])
    render(<SuperficieProntidao />)

    expect(
      await screen.findByText('Tempo limite excedido ao consultar o INMET.'),
    ).toBeInTheDocument()
    expect(
      screen.getByText('Funcionalidades que dependem de dados meteorológicos do INMET ficam bloqueadas.'),
    ).toBeInTheDocument()
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('aciona solicitarNovaVerificacao com a dependência correta ao clicar em verificar novamente', async () => {
    getDependencias.mockResolvedValue(conjuntoPadrao())
    solicitarNovaVerificacao.mockResolvedValue({
      nome: 'inmet',
      estado: 'verificando',
      aceitoEm: '2026-08-29T12:00:05+00:00',
    })
    const usuario = userEvent.setup()
    render(<SuperficieProntidao />)

    await screen.findByRole('rowheader', { name: 'INMET' })
    await usuario.click(screen.getByRole('button', { name: 'Verificar novamente: INMET' }))

    expect(solicitarNovaVerificacao).toHaveBeenCalledWith('inmet')
  })

  it('não oferece o botão de re-verificação para backend e banco de dados', async () => {
    getDependencias.mockResolvedValue(conjuntoPadrao())
    render(<SuperficieProntidao />)

    await screen.findByRole('rowheader', { name: 'Backend' })
    expect(
      screen.queryByRole('button', { name: 'Verificar novamente: Backend' }),
    ).not.toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: 'Verificar novamente: Banco de dados' }),
    ).not.toBeInTheDocument()
  })

  it('faz polling enquanto alguma linha não é terminal e para quando todas terminam', async () => {
    vi.useFakeTimers()
    try {
      const naoTerminal = [
        linha({ nome: 'backend' }),
        linha({ nome: 'banco_dados' }),
        linha({ nome: 'inmet', estado: 'verificando', verificadoEm: null, causa: null }),
        linha({ nome: 'openai' }),
      ]
      getDependencias.mockResolvedValueOnce(naoTerminal).mockResolvedValue(conjuntoPadrao())

      render(<SuperficieProntidao />)
      await vi.waitFor(() => expect(getDependencias).toHaveBeenCalledTimes(1))

      await vi.advanceTimersByTimeAsync(2000)
      await vi.waitFor(() => expect(getDependencias).toHaveBeenCalledTimes(2))

      await vi.advanceTimersByTimeAsync(2000)
      await vi.waitFor(() => expect(getDependencias).toHaveBeenCalledTimes(2))
    } finally {
      vi.useRealTimers()
    }
  })

  it('percorre os controles por Tab na ordem de leitura, com foco visível em cada um', async () => {
    getDependencias.mockResolvedValue(conjuntoPadrao())
    const usuario = userEvent.setup()
    render(<SuperficieProntidao />)

    await screen.findByRole('rowheader', { name: 'INMET' })
    const botaoInmet = screen.getByRole('button', { name: 'Verificar novamente: INMET' })
    const botaoOpenai = screen.getByRole('button', { name: 'Verificar novamente: OpenAI' })

    await usuario.tab()
    expect(botaoInmet).toHaveFocus()
    expect(botaoInmet.className).toContain('botao-reverificar')

    await usuario.tab()
    expect(botaoOpenai).toHaveFocus()
    expect(botaoOpenai.className).toContain('botao-reverificar')
  })

  it('carrega a classe do alvo mínimo de 44×44 px em cada botão de re-verificação', async () => {
    getDependencias.mockResolvedValue(conjuntoPadrao())
    render(<SuperficieProntidao />)

    await screen.findByRole('rowheader', { name: 'INMET' })
    const botaoInmet = screen.getByRole('button', { name: 'Verificar novamente: INMET' })
    const botaoOpenai = screen.getByRole('button', { name: 'Verificar novamente: OpenAI' })

    // A classe `botao-reverificar` define min-width/min-height de 44px em
    // SuperficieProntidao.css. jsdom não layouta a página, então esta verificação
    // confirma a presença da classe que codifica o alvo mínimo, não um pixel medido.
    expect(botaoInmet).toHaveClass('botao-reverificar')
    expect(botaoOpenai).toHaveClass('botao-reverificar')
  })

  it('dispara a mesma ação do clique ao pressionar Enter no botão focado', async () => {
    getDependencias.mockResolvedValue(conjuntoPadrao())
    solicitarNovaVerificacao.mockResolvedValue({
      nome: 'inmet',
      estado: 'verificando',
      aceitoEm: '2026-08-29T12:00:05+00:00',
    })
    const usuario = userEvent.setup()
    render(<SuperficieProntidao />)

    await screen.findByRole('rowheader', { name: 'INMET' })
    screen.getByRole('button', { name: 'Verificar novamente: INMET' }).focus()

    await usuario.keyboard('{Enter}')

    expect(solicitarNovaVerificacao).toHaveBeenCalledTimes(1)
    expect(solicitarNovaVerificacao).toHaveBeenCalledWith('inmet')
  })
})
