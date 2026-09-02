import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { AvaliacaoRisco } from '../../api/avaliacaoRisco'
import type { DetalheElegibilidade, Elegibilidade } from '../../api/elegibilidade'
import { SuperficieEventoDecisao } from './SuperficieEventoDecisao'

const { getAvaliacaoRisco } = vi.hoisted(() => ({
  getAvaliacaoRisco: vi.fn(),
}))

const { getElegibilidade, getDetalheElegibilidade } = vi.hoisted(() => ({
  getElegibilidade: vi.fn(),
  getDetalheElegibilidade: vi.fn(),
}))

vi.mock('../../api/avaliacaoRisco', async (importarOriginal) => ({
  ...(await importarOriginal<typeof import('../../api/avaliacaoRisco')>()),
  getAvaliacaoRisco,
}))

vi.mock('../../api/elegibilidade', async (importarOriginal) => ({
  ...(await importarOriginal<typeof import('../../api/elegibilidade')>()),
  getElegibilidade,
  getDetalheElegibilidade,
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

const ELEGIBILIDADE_VAZIA: Elegibilidade = { incluidos: 0, excluidos: 0, registros: [] }

function elegibilidade(sobrescritas: Partial<Elegibilidade> = {}): Elegibilidade {
  return {
    incluidos: 1,
    excluidos: 1,
    registros: [
      {
        id: '44444444-4444-4444-4444-444444444444',
        nomeSegurado: 'Maria Sintética',
        apoliceId: '55555555-5555-5555-5555-555555555555',
        codigoIbgeArea: '9990001',
        canal: 'whatsapp',
        elegivel: true,
      },
      {
        id: '66666666-6666-6666-6666-666666666666',
        nomeSegurado: 'João Sintético',
        apoliceId: '77777777-7777-7777-7777-777777777777',
        codigoIbgeArea: '9990001',
        canal: 'sms',
        elegivel: false,
      },
    ],
    ...sobrescritas,
  }
}

function detalheElegibilidade(
  sobrescritas: Partial<DetalheElegibilidade> = {},
): DetalheElegibilidade {
  return {
    id: '44444444-4444-4444-4444-444444444444',
    execucaoId: EXECUCAO_ID,
    eventoId: '22222222-2222-2222-2222-222222222222',
    regraId: '33333333-3333-3333-3333-333333333333',
    regraVersao: 3,
    seguradoId: '88888888-8888-8888-8888-888888888888',
    nomeSegurado: 'Maria Sintética',
    apoliceId: '55555555-5555-5555-5555-555555555555',
    codigoIbgeArea: '9990001',
    elegivel: true,
    criterios: [
      {
        operando: 'área afetada',
        valorObservado: '9990001',
        atende: true,
        justificativa: 'Área da apólice corresponde à área do evento (9990001).',
      },
    ],
    canal: 'whatsapp',
    justificativa: 'Segurado e apólice atendem integralmente aos critérios da regra ativa.',
    criadoEm: '2026-08-30T12:00:00+00:00',
    ...sobrescritas,
  }
}

beforeEach(() => {
  getAvaliacaoRisco.mockReset()
  getElegibilidade.mockReset()
  getDetalheElegibilidade.mockReset()
  getElegibilidade.mockResolvedValue(ELEGIBILIDADE_VAZIA)
})

describe('superfície de evento e decisão', () => {
  it('mostra o estado de carregamento até a primeira resposta real', () => {
    getAvaliacaoRisco.mockReturnValue(new Promise(() => {}))

    render(<SuperficieEventoDecisao execucaoId={EXECUCAO_ID} />)

    expect(screen.getByText('Carregando decisão de risco…')).toBeInTheDocument()
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

describe('superfície de evento e decisão — público elegível', () => {
  it('mostra as quantidades de incluídos e excluídos', async () => {
    getAvaliacaoRisco.mockResolvedValue(null)
    getElegibilidade.mockResolvedValue(elegibilidade())

    render(<SuperficieEventoDecisao execucaoId={EXECUCAO_ID} />)

    const secao = await screen.findByRole('region', { name: 'Público elegível' })
    expect(within(secao).getAllByText('1')).toHaveLength(2)
    expect(within(secao).getByText(/incluído/)).toBeInTheDocument()
    expect(within(secao).getByText(/excluído/)).toBeInTheDocument()
  })

  it('mostra conjunto vazio como resultado válido, não como erro', async () => {
    getAvaliacaoRisco.mockResolvedValue(null)
    getElegibilidade.mockResolvedValue(ELEGIBILIDADE_VAZIA)

    render(<SuperficieEventoDecisao execucaoId={EXECUCAO_ID} />)

    await screen.findByText('Nenhum segurado avaliado até o momento.')
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('exibe a tabela com segurado, apólice, localização, canal e resultado', async () => {
    getAvaliacaoRisco.mockResolvedValue(null)
    getElegibilidade.mockResolvedValue(elegibilidade())

    render(<SuperficieEventoDecisao execucaoId={EXECUCAO_ID} />)

    const tabela = await screen.findByRole('table', { name: /Público elegível/ })
    expect(within(tabela).getByText('Maria Sintética')).toBeInTheDocument()
    expect(within(tabela).getByText('João Sintético')).toBeInTheDocument()
    expect(within(tabela).getByText('whatsapp')).toBeInTheDocument()
    expect(within(tabela).getByText('sms')).toBeInTheDocument()
    expect(within(tabela).getByText('Incluído')).toBeInTheDocument()
    expect(within(tabela).getByText('Excluído')).toBeInTheDocument()
  })

  it('distingue incluído e excluído por texto, ícone e cor', async () => {
    getAvaliacaoRisco.mockResolvedValue(null)
    getElegibilidade.mockResolvedValue(elegibilidade())

    render(<SuperficieEventoDecisao execucaoId={EXECUCAO_ID} />)

    const tabela = await screen.findByRole('table', { name: /Público elegível/ })
    const badgeIncluido = within(tabela).getByText('Incluído').closest('span')
    const badgeExcluido = within(tabela).getByText('Excluído').closest('span')

    expect(badgeIncluido).toHaveClass('resultado-elegibilidade-badge--incluido')
    expect(badgeExcluido).toHaveClass('resultado-elegibilidade-badge--excluido')
    expect(
      badgeIncluido?.querySelector('svg[data-icone-nome="check-circle"]'),
    ).toBeInTheDocument()
    expect(badgeExcluido?.querySelector('svg[data-icone-nome="x-circle"]')).toBeInTheDocument()
  })

  it('abre a explicação de uma linha por teclado, sem depender de hover', async () => {
    getAvaliacaoRisco.mockResolvedValue(null)
    getElegibilidade.mockResolvedValue(elegibilidade())
    getDetalheElegibilidade.mockResolvedValue(detalheElegibilidade())
    const usuario = userEvent.setup()

    render(<SuperficieEventoDecisao execucaoId={EXECUCAO_ID} />)

    const botaoVerCriterios = (
      await screen.findAllByRole('button', { name: 'Ver critérios' })
    )[0]
    botaoVerCriterios.focus()
    expect(botaoVerCriterios).toHaveFocus()
    await usuario.keyboard('{Enter}')

    expect(await screen.findByText(/Explicação — Maria Sintética/)).toBeInTheDocument()
    expect(screen.getByText('área afetada')).toBeInTheDocument()
    expect(
      screen.getByText('Segurado e apólice atendem integralmente aos critérios da regra ativa.'),
    ).toBeInTheDocument()
    expect(getDetalheElegibilidade).toHaveBeenCalledWith(
      EXECUCAO_ID,
      '44444444-4444-4444-4444-444444444444',
    )
  })

  it('mostra Indisponível quando a consulta de elegibilidade falha', async () => {
    getAvaliacaoRisco.mockResolvedValue(null)
    getElegibilidade.mockRejectedValue(new TypeError('Failed to fetch'))

    render(<SuperficieEventoDecisao execucaoId={EXECUCAO_ID} />)

    expect(await screen.findByRole('alert')).toHaveTextContent('Indisponível')
  })
})
