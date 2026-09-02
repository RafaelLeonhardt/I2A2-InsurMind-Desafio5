import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { AvaliacaoRisco } from '../../api/avaliacaoRisco'
import { SuperficieEventoDecisao } from './SuperficieEventoDecisao'

const { getAvaliacaoRisco } = vi.hoisted(() => ({
  getAvaliacaoRisco: vi.fn(),
}))

vi.mock('../../api/avaliacaoRisco', async (importarOriginal) => ({
  ...(await importarOriginal<typeof import('../../api/avaliacaoRisco')>()),
  getAvaliacaoRisco,
}))

const EXECUCAO_ID = '11111111-1111-1111-1111-111111111111'

function avaliacao(sobrescritas: Partial<AvaliacaoRisco> = {}): AvaliacaoRisco {
  return {
    execucaoId: EXECUCAO_ID,
    eventoId: '22222222-2222-2222-2222-222222222222',
    regraId: '33333333-3333-3333-3333-333333333333',
    regraVersao: 1,
    relevante: true,
    criterios: [
      {
        operando: 'área aplicável',
        valorObservado: '9990001',
        atende: true,
        justificativa: 'Área do evento corresponde à área aplicável da regra (9990001).',
      },
      {
        operando: 'intensidade (mm acumulados no período)',
        valorObservado: '72.5 mm',
        atende: true,
        justificativa: 'Intensidade observada atinge o limiar de 50.0 mm.',
      },
    ],
    motivo: 'relevante',
    criadoEm: '2026-08-30T12:00:00+00:00',
    ...sobrescritas,
  }
}

beforeEach(() => {
  getAvaliacaoRisco.mockReset()
})

describe('superfície de evento e decisão', () => {
  it('mostra o estado de carregamento até a primeira resposta real', () => {
    getAvaliacaoRisco.mockReturnValue(new Promise(() => {}))

    render(<SuperficieEventoDecisao execucaoId={EXECUCAO_ID} />)

    expect(screen.getByRole('status')).toHaveTextContent('Carregando decisão de risco…')
  })

  it('mostra o progresso real quando a avaliação ainda não existe (aguardando)', async () => {
    getAvaliacaoRisco.mockResolvedValue(null)

    render(<SuperficieEventoDecisao execucaoId={EXECUCAO_ID} />)

    expect(await screen.findByText(/Em processamento/)).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })

  it('exibe cada critério em colunas estáveis: operando, valor, resultado, justificativa', async () => {
    getAvaliacaoRisco.mockResolvedValue(avaliacao())

    render(<SuperficieEventoDecisao execucaoId={EXECUCAO_ID} />)

    await screen.findByRole('table')
    expect(screen.getByText('área aplicável')).toBeInTheDocument()
    expect(screen.getByText('9990001')).toBeInTheDocument()
    expect(screen.getAllByText('Atende')).toHaveLength(2)
    expect(
      screen.getByText('Área do evento corresponde à área aplicável da regra (9990001).'),
    ).toBeInTheDocument()
  })

  it('mostra a categoria Relevante com texto, ícone e cor quando o evento é relevante', async () => {
    getAvaliacaoRisco.mockResolvedValue(avaliacao({ relevante: true, motivo: 'relevante' }))

    const { container } = render(<SuperficieEventoDecisao execucaoId={EXECUCAO_ID} />)

    await screen.findByText('Relevante')
    const badge = container.querySelector('[data-icone="relevante"]')
    expect(badge).toBeInTheDocument()
    expect(badge).toHaveClass('categoria-decisao-badge--relevante')
    expect(badge?.querySelector('svg[data-icone-nome="warning"]')).toBeInTheDocument()
  })

  it('mostra a categoria Sem risco quando o evento não atinge os critérios', async () => {
    getAvaliacaoRisco.mockResolvedValue(
      avaliacao({
        relevante: false,
        motivo: 'abaixo_do_limiar',
        criterios: [
          {
            operando: 'intensidade (mm acumulados no período)',
            valorObservado: '10.0 mm',
            atende: false,
            justificativa: 'Intensidade observada fica abaixo do limiar de 50.0 mm.',
          },
        ],
      }),
    )

    const { container } = render(<SuperficieEventoDecisao execucaoId={EXECUCAO_ID} />)

    await screen.findByText('Sem risco')
    expect(screen.getByText('Não atende')).toBeInTheDocument()
    const badge = container.querySelector('[data-icone="sem_risco"]')
    expect(badge).toHaveClass('categoria-decisao-badge--sem_risco')
    expect(badge?.querySelector('svg[data-icone-nome="check-circle"]')).toBeInTheDocument()
  })

  it('mostra a categoria Dado inválido quando o tipo de evento não é suportado', async () => {
    getAvaliacaoRisco.mockResolvedValue(
      avaliacao({ relevante: false, motivo: 'tipo_nao_suportado' }),
    )

    const { container } = render(<SuperficieEventoDecisao execucaoId={EXECUCAO_ID} />)

    await screen.findByText('Dado inválido')
    const badge = container.querySelector('[data-icone="dado_invalido"]')
    expect(badge).toHaveClass('categoria-decisao-badge--dado_invalido')
    expect(badge?.querySelector('svg[data-icone-nome="x-circle"]')).toBeInTheDocument()
  })

  it('usa um ícone diferente para cada uma das três categorias (RISCO-12)', async () => {
    getAvaliacaoRisco
      .mockResolvedValueOnce(avaliacao({ relevante: true, motivo: 'relevante' }))
      .mockResolvedValueOnce(avaliacao({ relevante: false, motivo: 'abaixo_do_limiar' }))
      .mockResolvedValueOnce(avaliacao({ relevante: false, motivo: 'tipo_nao_suportado' }))

    const relevanteRender = render(<SuperficieEventoDecisao execucaoId={EXECUCAO_ID} />)
    await screen.findByText('Relevante')
    const iconeRelevante = relevanteRender.container.querySelector('[data-icone-nome]')
    relevanteRender.unmount()

    const semRiscoRender = render(<SuperficieEventoDecisao execucaoId={EXECUCAO_ID} />)
    await screen.findByText('Sem risco')
    const iconeSemRisco = semRiscoRender.container.querySelector('[data-icone-nome]')
    semRiscoRender.unmount()

    const dadoInvalidoRender = render(<SuperficieEventoDecisao execucaoId={EXECUCAO_ID} />)
    await screen.findByText('Dado inválido')
    const iconeDadoInvalido = dadoInvalidoRender.container.querySelector('[data-icone-nome]')

    const nomes = [iconeRelevante, iconeSemRisco, iconeDadoInvalido].map((icone) =>
      icone?.getAttribute('data-icone-nome'),
    )
    expect(new Set(nomes).size).toBe(3)
  })

  it('mostra Indisponível com ocorrência, impacto e próxima ação quando a consulta falha', async () => {
    getAvaliacaoRisco.mockRejectedValue(new TypeError('Failed to fetch'))

    render(<SuperficieEventoDecisao execucaoId={EXECUCAO_ID} />)

    expect(await screen.findByRole('alert')).toHaveTextContent('Indisponível')
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })

  it('nao recalcula relevancia: usa somente os valores ja recebidos do backend', async () => {
    const resolvida = avaliacao({ relevante: true, motivo: 'relevante' })
    getAvaliacaoRisco.mockResolvedValue(resolvida)

    render(<SuperficieEventoDecisao execucaoId={EXECUCAO_ID} />)

    await screen.findByText('Relevante')
    expect(getAvaliacaoRisco).toHaveBeenCalledWith(EXECUCAO_ID)
    expect(getAvaliacaoRisco).toHaveBeenCalledTimes(1)
  })
})
