import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Execucao } from '../../api/execucao'
import { PerfilProvider, usePerfilContexto } from '../../contexto/PerfilContexto'
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

/** Exibe a superfície ativa para confirmar a navegação disparada por `selecionarSuperficie`. */
function EspiaSuperficieAtiva() {
  const { superficieAtiva } = usePerfilContexto()
  return <p data-testid="superficie-ativa">{JSON.stringify(superficieAtiva)}</p>
}

function renderizar(execucaoId: string = EXECUCAO_ID) {
  return render(
    <PerfilProvider>
      <SuperficieExecucao execucaoId={execucaoId} />
      <EspiaSuperficieAtiva />
    </PerfilProvider>,
  )
}

function execucao(sobrescritas: Partial<Execucao>): Execucao {
  return {
    id: EXECUCAO_ID,
    estado: 'coletando',
    marcos: [],
    publicoElegivelTotal: null,
    publicoElegivelPrevia: [],
    execucaoOrigemId: null,
    retentativas: [],
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
    renderizar()

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
    renderizar()

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
    renderizar()

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
    renderizar()

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
    renderizar()

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
    const { container } = renderizar()

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
    renderizar()

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
    const { container } = renderizar()

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

      renderizar()
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
    renderizar()

    expect(await screen.findByRole('alert')).toBeInTheDocument()
    expect(screen.getByText('Não foi possível falar com o backend local.')).toBeInTheDocument()
  })

  it('trata falhou_preparacao_ia como exceção, com a mesma causa persistida', async () => {
    getExecucao.mockResolvedValue(
      execucao({
        estado: 'falhou_preparacao_ia',
        marcos: [
          { marco: 'coleta_concluida', causa: null, criadoEm: '2026-08-30T12:00:00Z' },
          {
            marco: 'falhou_preparacao_ia',
            causa: 'ErroIntegracaoIA: contexto mínimo indisponível',
            criadoEm: '2026-08-30T12:00:01Z',
          },
        ],
      }),
    )
    renderizar()

    const excecao = await screen.findByText('Falha técnica não recuperável')
    expect(excecao.closest('[data-categoria]')).toHaveAttribute('data-categoria', 'excecao')
    expect(
      screen.getByText('ErroIntegracaoIA: contexto mínimo indisponível'),
    ).toBeInTheDocument()
  })

  it('embute a decisão de risco também em sem_risco, para explicar por que o evento foi sem risco', async () => {
    getExecucao.mockResolvedValue(
      execucao({
        estado: 'sem_risco',
        marcos: [{ marco: 'sem_risco', causa: null, criadoEm: '2026-08-30T12:00:00Z' }],
      }),
    )
    const { container } = renderizar()

    await screen.findByText('Encerrado — evento sem risco relevante')
    expect(container.querySelector('.secao-evento-decisao-embutida')).toBeInTheDocument()
  })

  it('não embute a decisão de risco em coletando nem em falhou_coleta (ainda não existe)', async () => {
    getExecucao.mockResolvedValue(execucao({ estado: 'coletando', marcos: [] }))
    const { container } = renderizar()

    await screen.findByText('Coletando dados meteorológicos…')
    expect(container.querySelector('.secao-evento-decisao-embutida')).not.toBeInTheDocument()
  })

  it('mostra a execução de origem como link e navega para ela ao clicar', async () => {
    const usuario = userEvent.setup()
    const ORIGEM_ID = '99999999-9999-9999-9999-999999999999'
    getExecucao.mockResolvedValue(
      execucao({
        estado: 'falhou_preparacao_ia',
        marcos: [
          { marco: 'falhou_preparacao_ia', causa: 'erro sintético', criadoEm: '2026-08-30T12:00:00Z' },
        ],
        execucaoOrigemId: ORIGEM_ID,
      }),
    )
    renderizar()

    const link = await screen.findByRole('button', { name: ORIGEM_ID })
    await usuario.click(link)

    expect(screen.getByTestId('superficie-ativa')).toHaveTextContent(
      JSON.stringify({ tipo: 'evento-execucao', execucaoId: ORIGEM_ID, perfilPai: 'administrador' }),
    )
  })

  it('lista as retentativas como links e navega para a selecionada ao clicar', async () => {
    const usuario = userEvent.setup()
    const RETENTATIVA_ID = '88888888-8888-8888-8888-888888888888'
    getExecucao.mockResolvedValue(
      execucao({
        estado: 'falhou_coleta',
        marcos: [{ marco: 'falhou_coleta', causa: 'erro sintético', criadoEm: '2026-08-30T12:00:00Z' }],
        retentativas: [RETENTATIVA_ID],
      }),
    )
    renderizar()

    const link = await screen.findByRole('button', { name: RETENTATIVA_ID })
    await usuario.click(link)

    expect(screen.getByTestId('superficie-ativa')).toHaveTextContent(
      JSON.stringify({
        tipo: 'evento-execucao',
        execucaoId: RETENTATIVA_ID,
        perfilPai: 'administrador',
      }),
    )
  })

  it('não mostra a seção de execuções correlacionadas quando não há origem nem retentativas', async () => {
    getExecucao.mockResolvedValue(execucao({ estado: 'sem_risco', marcos: [] }))
    renderizar()

    await screen.findByText('Encerrado — evento sem risco relevante')
    expect(
      screen.queryByRole('heading', { name: 'Execuções correlacionadas' }),
    ).not.toBeInTheDocument()
  })
})
