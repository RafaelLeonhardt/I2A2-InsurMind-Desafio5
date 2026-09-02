import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Execucao } from '../../api/execucao'
import { SuperficieExecucao } from './SuperficieExecucao'

const { getExecucao } = vi.hoisted(() => ({
  getExecucao: vi.fn(),
}))

const { getAvaliacaoRisco } = vi.hoisted(() => ({
  getAvaliacaoRisco: vi.fn(),
}))

const { getElegibilidade } = vi.hoisted(() => ({
  getElegibilidade: vi.fn(),
}))

vi.mock('../../api/execucao', async (importarOriginal) => ({
  ...(await importarOriginal<typeof import('../../api/execucao')>()),
  getExecucao,
}))

vi.mock('../../api/avaliacaoRisco', async (importarOriginal) => ({
  ...(await importarOriginal<typeof import('../../api/avaliacaoRisco')>()),
  getAvaliacaoRisco,
}))

vi.mock('../../api/elegibilidade', async (importarOriginal) => ({
  ...(await importarOriginal<typeof import('../../api/elegibilidade')>()),
  getElegibilidade,
}))

const EXECUCAO_ID = '11111111-1111-1111-1111-111111111111'

function execucao(sobrescritas: Partial<Execucao>): Execucao {
  return {
    id: EXECUCAO_ID,
    estado: 'coletando',
    marcos: [],
    publicoElegivelTotal: null,
    publicoElegivelPrevia: [],
    ...sobrescritas,
  }
}

beforeEach(() => {
  getExecucao.mockReset()
  getAvaliacaoRisco.mockReset()
  getElegibilidade.mockReset()
  getAvaliacaoRisco.mockResolvedValue(null)
  getElegibilidade.mockResolvedValue({ incluidos: 0, excluidos: 0, registros: [] })
})

describe('superfície de execução', () => {
  it('mostra a etapa corrente de coleta quando nenhum marco foi persistido ainda', async () => {
    getExecucao.mockResolvedValue(execucao({ estado: 'coletando', marcos: [] }))
    render(<SuperficieExecucao execucaoId={EXECUCAO_ID} />)

    const corrente = await screen.findByText('Coletando dados meteorológicos…')
    expect(corrente.closest('[data-categoria]')).toHaveAttribute('data-categoria', 'corrente')
  })

  it('mostra coleta concluída e a avaliação de risco como corrente', async () => {
    getExecucao.mockResolvedValue(
      execucao({
        estado: 'coletando',
        marcos: [{ marco: 'coleta_concluida', causa: null, criadoEm: '2026-08-30T12:00:00Z' }],
      }),
    )
    render(<SuperficieExecucao execucaoId={EXECUCAO_ID} />)

    expect(await screen.findByText('Coleta meteorológica concluída')).toBeInTheDocument()
    expect(screen.getByText('Avaliação de risco em andamento…')).toBeInTheDocument()
  })

  it('encerra em sem_risco sem chamar avaliação de elegibilidade (sem etapa corrente)', async () => {
    getExecucao.mockResolvedValue(
      execucao({
        estado: 'sem_risco',
        marcos: [
          { marco: 'coleta_concluida', causa: null, criadoEm: '2026-08-30T12:00:00Z' },
          { marco: 'sem_risco', causa: null, criadoEm: '2026-08-30T12:00:01Z' },
        ],
      }),
    )
    render(<SuperficieExecucao execucaoId={EXECUCAO_ID} />)

    const encerramento = await screen.findByText('Encerrado — evento sem risco relevante')
    expect(encerramento.closest('[data-categoria]')).toHaveAttribute(
      'data-categoria',
      'encerramento',
    )
    expect(screen.queryByText(/em andamento/)).not.toBeInTheDocument()
  })

  it('encerra em sem_elegiveis com rótulo e categoria próprios', async () => {
    getExecucao.mockResolvedValue(
      execucao({
        estado: 'sem_elegiveis',
        marcos: [
          { marco: 'coleta_concluida', causa: null, criadoEm: '2026-08-30T12:00:00Z' },
          {
            marco: 'avaliacao_risco_concluida',
            causa: null,
            criadoEm: '2026-08-30T12:00:01Z',
          },
          {
            marco: 'avaliacao_elegibilidade_concluida',
            causa: null,
            criadoEm: '2026-08-30T12:00:02Z',
          },
          { marco: 'sem_elegiveis', causa: null, criadoEm: '2026-08-30T12:00:03Z' },
        ],
      }),
    )
    render(<SuperficieExecucao execucaoId={EXECUCAO_ID} />)

    const encerramento = await screen.findByText('Encerrado — nenhum segurado elegível')
    expect(encerramento.closest('[data-categoria]')).toHaveAttribute(
      'data-categoria',
      'encerramento',
    )
  })

  it('exibe uma exceção com a causa registrada quando o estado é falhou_coleta', async () => {
    getExecucao.mockResolvedValue(
      execucao({
        estado: 'falhou_coleta',
        marcos: [
          {
            marco: 'falhou_coleta',
            causa: 'RuntimeError: erro inesperado no risco',
            criadoEm: '2026-08-30T12:00:00Z',
          },
        ],
      }),
    )
    render(<SuperficieExecucao execucaoId={EXECUCAO_ID} />)

    const excecao = await screen.findByText('Falha técnica não recuperável')
    expect(excecao.closest('[data-categoria]')).toHaveAttribute('data-categoria', 'excecao')
    expect(screen.getByText('RuntimeError: erro inesperado no risco')).toBeInTheDocument()
  })

  it('chega em aguardando_geracao com a prévia do público elegível embutida', async () => {
    getExecucao.mockResolvedValue(
      execucao({
        estado: 'aguardando_geracao',
        marcos: [
          { marco: 'coleta_concluida', causa: null, criadoEm: '2026-08-30T12:00:00Z' },
          {
            marco: 'avaliacao_risco_concluida',
            causa: null,
            criadoEm: '2026-08-30T12:00:01Z',
          },
          {
            marco: 'avaliacao_elegibilidade_concluida',
            causa: null,
            criadoEm: '2026-08-30T12:00:02Z',
          },
          { marco: 'publico_elegivel_formado', causa: null, criadoEm: '2026-08-30T12:00:03Z' },
          { marco: 'aguardando_geracao', causa: null, criadoEm: '2026-08-30T12:00:04Z' },
        ],
        publicoElegivelTotal: 1,
        publicoElegivelPrevia: [{ nomeSegurado: 'Maria Sintética', canal: 'whatsapp' }],
      }),
    )
    const { container } = render(<SuperficieExecucao execucaoId={EXECUCAO_ID} />)

    expect(await screen.findByText('Público elegível formado')).toBeInTheDocument()
    expect(screen.getByText('Aguardando geração de mensagens')).toBeInTheDocument()
    expect(container.querySelector('.secao-evento-decisao-embutida')).toBeInTheDocument()
  })

  it('anuncia a etapa final numa região aria-live quando a execução se resolve', async () => {
    getExecucao.mockResolvedValue(
      execucao({
        estado: 'sem_risco',
        marcos: [{ marco: 'sem_risco', causa: null, criadoEm: '2026-08-30T12:00:00Z' }],
      }),
    )
    render(<SuperficieExecucao execucaoId={EXECUCAO_ID} />)

    const encerramento = await screen.findByText('Encerrado — evento sem risco relevante')
    expect(encerramento.closest('[aria-live]')).toHaveAttribute('aria-live', 'polite')
  })

  it('as quatro categorias têm texto, ícone e traço (classe) todos distintos entre si', async () => {
    getExecucao.mockResolvedValue(
      execucao({
        estado: 'falhou_coleta',
        marcos: [
          { marco: 'coleta_concluida', causa: null, criadoEm: '2026-08-30T12:00:00Z' },
          {
            marco: 'falhou_coleta',
            causa: 'RuntimeError: falha sintética',
            criadoEm: '2026-08-30T12:00:01Z',
          },
        ],
      }),
    )
    const { container } = render(<SuperficieExecucao execucaoId={EXECUCAO_ID} />)

    await screen.findByText('Falha técnica não recuperável')
    const itens = Array.from(container.querySelectorAll('.etapa-execucao'))
    expect(itens).toHaveLength(2)

    const textos = itens.map((item) => item.textContent)
    const icones = itens.map((item) => item.querySelector('[data-icone-nome]')?.getAttribute('data-icone-nome'))
    const classes = itens.map((item) => item.className)

    expect(new Set(textos).size).toBe(itens.length)
    expect(new Set(icones).size).toBe(itens.length)
    expect(new Set(classes).size).toBe(itens.length)
  })

  it('faz polling enquanto em andamento e para ao chegar em um resultado', async () => {
    vi.useFakeTimers()
    try {
      getExecucao
        .mockResolvedValueOnce(execucao({ estado: 'coletando', marcos: [] }))
        .mockResolvedValue(
          execucao({
            estado: 'sem_risco',
            marcos: [{ marco: 'sem_risco', causa: null, criadoEm: '2026-08-30T12:00:00Z' }],
          }),
        )

      render(<SuperficieExecucao execucaoId={EXECUCAO_ID} />)
      await vi.waitFor(() => expect(getExecucao).toHaveBeenCalledTimes(1))

      await vi.advanceTimersByTimeAsync(1500)
      await vi.waitFor(() => expect(getExecucao).toHaveBeenCalledTimes(2))

      await vi.advanceTimersByTimeAsync(1500)
      await vi.waitFor(() => expect(getExecucao).toHaveBeenCalledTimes(2))
    } finally {
      vi.useRealTimers()
    }
  })

  it('mostra Indisponível com ocorrência, impacto e próxima ação quando a consulta falha', async () => {
    const { ErroExecucao } = await import('../../api/execucao')
    getExecucao.mockRejectedValue(
      new ErroExecucao({
        codigo: 'falha_de_rede',
        correlacaoId: null,
        ocorrencia: 'Não foi possível falar com o backend local.',
        impacto: 'O acompanhamento não pode ser exibido.',
        proximaAcao: 'Tente novamente.',
        status: null,
      }),
    )
    render(<SuperficieExecucao execucaoId={EXECUCAO_ID} />)

    expect(await screen.findByRole('alert')).toBeInTheDocument()
    expect(screen.getByText('Não foi possível falar com o backend local.')).toBeInTheDocument()
  })
})
