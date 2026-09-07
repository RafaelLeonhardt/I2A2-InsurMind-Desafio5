import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { type Comunicado } from '../../api/comunicado'
import { ErroContexto } from '../../api/contexto'
import { ErroListaComunicados, type ItemComunicado } from '../../api/listaComunicados'
import { SuperficieComunicados } from './SuperficieComunicados'

const { getListaComunicadosMock, getSeguradoPadraoMock, getComunicadoMock, registrarVisualizacaoComunicadoMock } =
  vi.hoisted(() => ({
    getListaComunicadosMock: vi.fn(),
    getSeguradoPadraoMock: vi.fn(),
    getComunicadoMock: vi.fn(),
    registrarVisualizacaoComunicadoMock: vi.fn(),
  }))

vi.mock('../../api/listaComunicados', async (importarOriginal) => ({
  ...(await importarOriginal<typeof import('../../api/listaComunicados')>()),
  getListaComunicados: getListaComunicadosMock,
}))

vi.mock('../../api/contexto', async (importarOriginal) => ({
  ...(await importarOriginal<typeof import('../../api/contexto')>()),
  getSeguradoPadrao: getSeguradoPadraoMock,
}))

vi.mock('../../api/comunicado', async (importarOriginal) => ({
  ...(await importarOriginal<typeof import('../../api/comunicado')>()),
  getComunicado: getComunicadoMock,
  registrarVisualizacaoComunicado: registrarVisualizacaoComunicadoMock,
}))

const SEGURADO_ID = '11111111-1111-1111-1111-111111111111'
const OUTRO_SEGURADO_ID = '99999999-9999-9999-9999-999999999999'
const ENTREGA_ID = '22222222-2222-2222-2222-222222222222'

function item(sobrescritas: Partial<ItemComunicado> = {}): ItemComunicado {
  return {
    entregaSimuladaId: ENTREGA_ID,
    mensagemId: '33333333-3333-3333-3333-333333333333',
    canal: 'email',
    assuntoOuResumo: 'Aviso preventivo',
    criadoEm: '2026-09-05T12:00:00Z',
    visualizacao: null,
    ...sobrescritas,
  }
}

function promessaControlada<T>() {
  let resolver: (valor: T) => void = () => {}
  const promessa = new Promise<T>((resolucao) => {
    resolver = resolucao
  })
  return { promessa, resolver }
}

function comunicado(sobrescritas: Partial<Comunicado> = {}): Comunicado {
  return {
    entregaSimuladaId: ENTREGA_ID,
    mensagemId: '33333333-3333-3333-3333-333333333333',
    canal: 'email',
    assunto: 'Aviso preventivo',
    corpo: 'Chuva forte hoje na sua região.',
    rotulo: 'simulada',
    criadoEm: '2026-09-05T12:00:00Z',
    visualizacao: null,
    ...sobrescritas,
  }
}

beforeEach(() => {
  vi.resetAllMocks()
  getSeguradoPadraoMock.mockResolvedValue({ id: SEGURADO_ID, nome: 'Pessoa Segurada Sintética' })
  getComunicadoMock.mockResolvedValue(comunicado())
  registrarVisualizacaoComunicadoMock.mockResolvedValue({
    id: '44444444-4444-4444-4444-444444444444',
    visualizadaEm: '2026-09-05T12:05:00Z',
  })
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('lista de comunicados (COMUNICADOS-01)', () => {
  it('mostra canal, assunto/resumo, data e estado de cada comunicado', async () => {
    getListaComunicadosMock.mockResolvedValue([item()])

    render(<SuperficieComunicados seguradoId={SEGURADO_ID} />)

    expect(await screen.findByRole('cell', { name: 'E-mail' })).toBeInTheDocument()
    expect(screen.getByText('Aviso preventivo')).toBeInTheDocument()
    expect(screen.getByText('2026-09-05T12:00:00Z')).toBeInTheDocument()
    expect(screen.getByText('Enviada — simulação')).toBeInTheDocument()
  })

  it('mostra "Visualizada no portal" quando o comunicado já foi visualizado', async () => {
    getListaComunicadosMock.mockResolvedValue([
      item({
        visualizacao: { id: '44444444-4444-4444-4444-444444444444', visualizadaEm: '2026-09-05T12:05:00Z' },
      }),
    ])

    render(<SuperficieComunicados seguradoId={SEGURADO_ID} />)

    expect(await screen.findByText('Visualizada no portal')).toBeInTheDocument()
    expect(screen.queryByText('Enviada — simulação')).not.toBeInTheDocument()
  })

  it('consulta a lista com o segurado informado, isolando de outro segurado', async () => {
    getListaComunicadosMock.mockImplementation((seguradoId: string) =>
      Promise.resolve(seguradoId === SEGURADO_ID ? [item()] : []),
    )

    const { unmount } = render(<SuperficieComunicados seguradoId={SEGURADO_ID} />)
    expect(await screen.findByText('Aviso preventivo')).toBeInTheDocument()
    unmount()

    render(<SuperficieComunicados seguradoId={OUTRO_SEGURADO_ID} />)
    expect(await screen.findByRole('heading', { name: 'Nenhum comunicado no momento' })).toBeInTheDocument()
    expect(getListaComunicadosMock).toHaveBeenCalledWith(OUTRO_SEGURADO_ID)
  })

  it('descarta uma resposta antiga que chega depois de uma troca de segurado mais recente', async () => {
    const antiga = promessaControlada<ItemComunicado[]>()
    getListaComunicadosMock.mockReturnValueOnce(antiga.promessa)
    const { rerender } = render(<SuperficieComunicados seguradoId={SEGURADO_ID} />)
    await screen.findByText('Carregando comunicados…')

    const nova = promessaControlada<ItemComunicado[]>()
    getListaComunicadosMock.mockReturnValueOnce(nova.promessa)
    rerender(<SuperficieComunicados seguradoId={OUTRO_SEGURADO_ID} />)

    nova.resolver([item({ assuntoOuResumo: 'Aviso novo' })])
    await screen.findByText('Aviso novo')

    antiga.resolver([item({ assuntoOuResumo: 'Aviso antigo' })])

    // Aguarda um macrotask real para dar tempo da continuação assíncrona da resposta
    // obsoleta rodar e provar que o guard de token a descarta.
    await new Promise((resolucao) => setTimeout(resolucao, 50))
    expect(screen.queryByText('Aviso antigo')).not.toBeInTheDocument()
    expect(screen.getByText('Aviso novo')).toBeInTheDocument()
  })

  it('mostra estado vazio explicativo mencionando Alertas, Apólice e Meus Dados', async () => {
    getListaComunicadosMock.mockResolvedValue([])

    render(<SuperficieComunicados seguradoId={SEGURADO_ID} />)

    expect(await screen.findByRole('heading', { name: 'Nenhum comunicado no momento' })).toBeInTheDocument()
    expect(screen.getByText(/Alertas/)).toBeInTheDocument()
    expect(screen.getByText(/Apólice/)).toBeInTheDocument()
    expect(screen.getByText(/Meus Dados/)).toBeInTheDocument()
  })

  it('mostra ocorrência, impacto e próxima ação quando a lista falha, sem conteúdo fixo', async () => {
    getListaComunicadosMock.mockRejectedValueOnce(
      new ErroListaComunicados({
        codigo: 'falha_local',
        correlacaoId: null,
        ocorrencia: 'Falha ao consultar os comunicados.',
        impacto: 'A lista pode estar desatualizada.',
        proximaAcao: 'Tente novamente.',
        status: 500,
      }),
    )
    render(<SuperficieComunicados seguradoId={SEGURADO_ID} />)

    const alerta = await screen.findByRole('alert')
    expect(alerta).toHaveTextContent('Falha ao consultar os comunicados.')
    expect(screen.queryByRole('table')).not.toBeInTheDocument()

    getListaComunicadosMock.mockResolvedValueOnce([item()])
    const usuario = userEvent.setup()
    await usuario.click(screen.getByRole('button', { name: 'Tentar novamente' }))

    expect(await screen.findByText('Aviso preventivo')).toBeInTheDocument()
  })

  it('mostra falha de contexto ao resolver o segurado padrão', async () => {
    getSeguradoPadraoMock.mockRejectedValue(
      new ErroContexto({
        codigo: 'falha_de_rede',
        correlacaoId: null,
        ocorrencia: 'Não foi possível falar com o backend.',
        impacto: 'Nenhum comunicado pôde ser exibido.',
        proximaAcao: 'Tente novamente.',
        status: null,
      }),
    )

    render(<SuperficieComunicados />)

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Não foi possível falar com o backend.',
    )
  })
})

describe('detalhe do comunicado (COMUNICADOS-03, 04)', () => {
  it('abre o detalhe ao selecionar um comunicado, reusando SuperficieComunicado (4.3)', async () => {
    getListaComunicadosMock.mockResolvedValue([item()])
    const usuario = userEvent.setup()
    render(<SuperficieComunicados seguradoId={SEGURADO_ID} />)

    await usuario.click(await screen.findByRole('button', { name: 'Ver detalhe' }))

    expect(await screen.findByText('Chuva forte hoje na sua região.')).toBeInTheDocument()
    expect(getComunicadoMock).toHaveBeenCalledWith(SEGURADO_ID, ENTREGA_ID)
  })

  it('anuncia a seleção do comunicado numa região aria-live', async () => {
    getListaComunicadosMock.mockResolvedValue([item()])
    const usuario = userEvent.setup()
    render(<SuperficieComunicados seguradoId={SEGURADO_ID} />)

    await usuario.click(await screen.findByRole('button', { name: 'Ver detalhe' }))
    await screen.findByText('Chuva forte hoje na sua região.')

    const regiaoAnuncio = document.querySelector('[aria-live="polite"]')
    expect(regiaoAnuncio).toHaveTextContent('Comunicado selecionado. Mostrando detalhe.')
  })

  it('move o foco para "Voltar à lista" ao selecionar um comunicado', async () => {
    getListaComunicadosMock.mockResolvedValue([item()])
    const usuario = userEvent.setup()
    render(<SuperficieComunicados seguradoId={SEGURADO_ID} />)

    await usuario.click(await screen.findByRole('button', { name: 'Ver detalhe' }))

    expect(await screen.findByRole('button', { name: 'Voltar à lista' })).toHaveFocus()
  })

  it('devolve o foco ao botão de origem ao voltar para a lista', async () => {
    getListaComunicadosMock.mockResolvedValue([item()])
    const usuario = userEvent.setup()
    render(<SuperficieComunicados seguradoId={SEGURADO_ID} />)

    await usuario.click(await screen.findByRole('button', { name: 'Ver detalhe' }))
    await usuario.click(screen.getByRole('button', { name: 'Voltar à lista' }))

    expect(await screen.findByRole('button', { name: 'Ver detalhe' })).toHaveFocus()
  })

  it('reabrir um comunicado já visualizado não registra uma segunda visualização', async () => {
    getListaComunicadosMock.mockResolvedValue([item()])
    getComunicadoMock.mockResolvedValue(
      comunicado({
        visualizacao: { id: '44444444-4444-4444-4444-444444444444', visualizadaEm: '2026-09-05T12:05:00Z' },
      }),
    )
    const usuario = userEvent.setup()
    render(<SuperficieComunicados seguradoId={SEGURADO_ID} />)

    await usuario.click(await screen.findByRole('button', { name: 'Ver detalhe' }))
    await screen.findByText(/Visualizada no portal em 2026-09-05T12:05:00Z/)
    await usuario.click(screen.getByRole('button', { name: 'Voltar à lista' }))
    await usuario.click(await screen.findByRole('button', { name: 'Ver detalhe' }))

    expect(await screen.findByText(/Visualizada no portal em 2026-09-05T12:05:00Z/)).toBeInTheDocument()
    expect(registrarVisualizacaoComunicadoMock).not.toHaveBeenCalled()
  })
})

describe('acessibilidade de teclado', () => {
  it('o botão de detalhe é alcançável e ativável por teclado', async () => {
    getListaComunicadosMock.mockResolvedValue([item()])
    render(<SuperficieComunicados seguradoId={SEGURADO_ID} />)
    await screen.findByRole('button', { name: 'Ver detalhe' })

    const usuario = userEvent.setup()
    await usuario.tab()
    expect(screen.getByRole('button', { name: 'Ver detalhe' })).toHaveFocus()
    await usuario.keyboard('{Enter}')

    expect(await screen.findByText('Chuva forte hoje na sua região.')).toBeInTheDocument()
  })
})

describe('resolução do segurado ativo', () => {
  it('sem seguradoId informado, resolve o segurado padrão internamente', async () => {
    getListaComunicadosMock.mockResolvedValue([])

    render(<SuperficieComunicados />)

    await screen.findByRole('heading', { name: 'Nenhum comunicado no momento' })
    expect(getSeguradoPadraoMock).toHaveBeenCalledTimes(1)
    expect(getListaComunicadosMock).toHaveBeenCalledWith(SEGURADO_ID)
  })
})
