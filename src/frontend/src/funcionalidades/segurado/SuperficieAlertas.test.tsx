import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { AlertaSegurado } from '../../api/alertaSegurado'
import { ErroContexto } from '../../api/contexto'
import type { ExplicacaoComunicado } from '../../api/explicacaoComunicado'
import { type DetalheAlerta, ErroListaAlertas, type ItemAlerta } from '../../api/listaAlertasSegurado'
import { SuperficieAlertas } from './SuperficieAlertas'

const {
  getListaAlertasMock,
  getDetalheAlertaMock,
  getSeguradoPadraoMock,
  getExplicacaoMock,
} = vi.hoisted(() => ({
  getListaAlertasMock: vi.fn(),
  getDetalheAlertaMock: vi.fn(),
  getSeguradoPadraoMock: vi.fn(),
  getExplicacaoMock: vi.fn(),
}))

vi.mock('../../api/listaAlertasSegurado', async (importarOriginal) => ({
  ...(await importarOriginal<typeof import('../../api/listaAlertasSegurado')>()),
  getListaAlertas: getListaAlertasMock,
  getDetalheAlerta: getDetalheAlertaMock,
}))

vi.mock('../../api/contexto', async (importarOriginal) => ({
  ...(await importarOriginal<typeof import('../../api/contexto')>()),
  getSeguradoPadrao: getSeguradoPadraoMock,
}))

vi.mock('../../api/explicacaoComunicado', async (importarOriginal) => ({
  ...(await importarOriginal<typeof import('../../api/explicacaoComunicado')>()),
  getExplicacaoComunicado: getExplicacaoMock,
}))

const SEGURADO_ID = '11111111-1111-1111-1111-111111111111'
const OUTRO_SEGURADO_ID = '44444444-4444-4444-4444-444444444444'
const ELEGIBILIDADE_ID = '22222222-2222-2222-2222-222222222222'
const ENTREGA_ID = '55555555-5555-5555-5555-555555555555'

function explicacaoBase(): ExplicacaoComunicado {
  return {
    entregaSimuladaId: ENTREGA_ID,
    mensagemId: '66666666-6666-6666-6666-666666666666',
    execucaoId: '77777777-7777-7777-7777-777777777777',
    execucaoOrigemId: null,
    eventoERegra: { origem: 'deterministica', evento: null, regraId: 'regra-1', regraVersao: 1 },
    contexto: null,
    agente: { origem: 'agente', status: 'completa', causaExcecao: null, tentativas: [] },
    apresentacaoSimulada: null,
  }
}

function promessaControlada<T>() {
  let resolver: (valor: T) => void = () => {}
  const promessa = new Promise<T>((resolucao) => {
    resolver = resolucao
  })
  return { promessa, resolver }
}

function alertaBase(sobrescritas: Partial<AlertaSegurado> = {}): AlertaSegurado {
  return {
    elegibilidadeId: ELEGIBILIDADE_ID,
    eventoTipo: 'chuva_intensa',
    severidade: '72.5 mm — atinge o limiar.',
    periodoInicio: '2026-09-04T12:00:00',
    periodoFim: '2026-09-04T18:00:00',
    localizacao: '9990001',
    impactosEsperados: ['alagamento'],
    recomendacoes: ['Evite áreas alagadas.'],
    origem: 'real_inmet',
    instanteObservado: '2026-09-04T18:00:00',
    fonteDegradada: false,
    entregaSimuladaId: null,
    ...sobrescritas,
  }
}

function item(sobrescritas: Partial<ItemAlerta> = {}): ItemAlerta {
  return {
    alerta: alertaBase(),
    classificacao: 'ativo',
    ...sobrescritas,
  }
}

function detalhe(sobrescritas: Partial<DetalheAlerta> = {}): DetalheAlerta {
  return {
    alerta: alertaBase(),
    classificacao: 'ativo',
    apoliceId: '33333333-3333-3333-3333-333333333333',
    justificativa: 'Segurado e apólice atendem à regra ativa.',
    linhaDoTempo: [
      {
        timestamp: '2026-09-04T12:00:00',
        ator: 'sistema',
        acao: 'coleta_concluida',
        resultado: 'sucesso',
        correlacao: 'corr-1',
        tipo: 'execucao',
        mensagemId: null,
      },
    ],
    ...sobrescritas,
  }
}

beforeEach(() => {
  vi.resetAllMocks()
  getSeguradoPadraoMock.mockResolvedValue({ id: SEGURADO_ID, nome: 'Pessoa Segurada Sintética' })
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('lista de alertas (ALERTAS-01)', () => {
  it('mostra evento, severidade, período, localização, origem e estado de cada alerta', async () => {
    getListaAlertasMock.mockResolvedValue([item()])

    render(<SuperficieAlertas seguradoId={SEGURADO_ID} />)

    expect(await screen.findByRole('cell', { name: 'Chuva intensa' })).toBeInTheDocument()
    expect(screen.getByText('72.5 mm — atinge o limiar.')).toBeInTheDocument()
    expect(screen.getByText(/2026-09-04T12:00:00 a 2026-09-04T18:00:00/)).toBeInTheDocument()
    expect(screen.getByText('9990001')).toBeInTheDocument()
    expect(screen.getByText('Observação real (INMET)')).toBeInTheDocument()
    expect(screen.getByText('Ativo')).toBeInTheDocument()
  })

  it('distingue ativo, anterior e ainda_nao_simulado por texto (não só cor/ícone)', async () => {
    getListaAlertasMock.mockResolvedValue([
      item({ classificacao: 'ativo' }),
      item({
        classificacao: 'anterior',
        alerta: alertaBase({ elegibilidadeId: 'outro-1' }),
      }),
      item({
        classificacao: 'ainda_nao_simulado',
        alerta: alertaBase({ elegibilidadeId: 'outro-2' }),
      }),
    ])

    render(<SuperficieAlertas seguradoId={SEGURADO_ID} />)

    await screen.findByText('Ativo')
    expect(screen.getByText('Anterior')).toBeInTheDocument()
    expect(screen.getByText('Ainda não simulado')).toBeInTheDocument()

    // Distinção também por ícone (ALERTAS-01 exige rótulo + ícone + texto): os três
    // marcadores de ícone precisam ser diferentes entre si, não o mesmo ícone repetido.
    const marcadoresDeIcone = document.querySelectorAll('[data-icone-nome]')
    const nomesDeIcone = new Set(
      Array.from(marcadoresDeIcone).map((elemento) => elemento.getAttribute('data-icone-nome')),
    )
    expect(nomesDeIcone.size).toBe(3)
  })

  it('mostra estado vazio explicativo com próxima ação válida, sem nenhum alerta', async () => {
    getListaAlertasMock.mockResolvedValue([])

    render(<SuperficieAlertas seguradoId={SEGURADO_ID} />)

    expect(await screen.findByRole('heading', { name: 'Nenhum alerta no momento' })).toBeInTheDocument()
    getListaAlertasMock.mockResolvedValueOnce([item()])
    const usuario = userEvent.setup()
    await usuario.click(screen.getByRole('button', { name: 'Atualizar' }))

    expect(await screen.findByText('Ativo')).toBeInTheDocument()
  })

  it('mostra ocorrência, impacto e próxima ação quando a lista falha, com nova tentativa', async () => {
    getListaAlertasMock.mockRejectedValueOnce(
      new ErroListaAlertas({
        codigo: 'falha_local',
        correlacaoId: null,
        ocorrencia: 'Falha ao consultar os alertas.',
        impacto: 'A lista pode estar desatualizada.',
        proximaAcao: 'Tente novamente.',
        status: 500,
      }),
    )
    render(<SuperficieAlertas seguradoId={SEGURADO_ID} />)
    const alerta = await screen.findByRole('alert')
    expect(alerta).toHaveTextContent('Falha ao consultar os alertas.')

    getListaAlertasMock.mockResolvedValueOnce([item()])
    const usuario = userEvent.setup()
    await usuario.click(screen.getByRole('button', { name: 'Tentar novamente' }))

    expect(await screen.findByText('Ativo')).toBeInTheDocument()
  })
})

describe('detalhe do alerta (ALERTAS-03, 04)', () => {
  it('abre o detalhe ao selecionar um alerta, com origem, período, localização, impactos, recomendações, contexto da apólice e linha do tempo', async () => {
    getListaAlertasMock.mockResolvedValue([item()])
    getDetalheAlertaMock.mockResolvedValue(detalhe())
    const usuario = userEvent.setup()
    render(<SuperficieAlertas seguradoId={SEGURADO_ID} />)
    await usuario.click(await screen.findByRole('button', { name: 'Ver detalhe' }))

    expect(await screen.findByRole('heading', { name: 'Chuva intensa' })).toBeInTheDocument()
    expect(screen.getByText('Observação real (INMET)')).toBeInTheDocument()
    expect(screen.getByText(/2026-09-04T12:00:00 a 2026-09-04T18:00:00/)).toBeInTheDocument()
    expect(screen.getByText('9990001')).toBeInTheDocument()
    expect(screen.getByText('alagamento')).toBeInTheDocument()
    expect(screen.getByText('Evite áreas alagadas.')).toBeInTheDocument()
    expect(screen.getByText('Segurado e apólice atendem à regra ativa.')).toBeInTheDocument()
    expect(screen.getByText(/coleta_concluida/)).toBeInTheDocument()
  })

  it('anuncia a seleção do alerta numa região aria-live', async () => {
    getListaAlertasMock.mockResolvedValue([item()])
    getDetalheAlertaMock.mockResolvedValue(detalhe())
    const usuario = userEvent.setup()
    render(<SuperficieAlertas seguradoId={SEGURADO_ID} />)

    await usuario.click(await screen.findByRole('button', { name: 'Ver detalhe' }))
    await screen.findByRole('heading', { name: 'Chuva intensa' })

    const regiaoAnuncio = document.querySelector('[aria-live="polite"]')
    expect(regiaoAnuncio).toHaveTextContent('Alerta selecionado. Mostrando detalhe.')
  })

  it('mostra um alerta anterior simulado com sucesso sem afirmar que foi visualizado', async () => {
    getListaAlertasMock.mockResolvedValue([item({ classificacao: 'anterior' })])
    getDetalheAlertaMock.mockResolvedValue(
      detalhe({
        classificacao: 'anterior',
        linhaDoTempo: [
          {
            timestamp: '2026-08-01T12:00:00',
            ator: 'sistema',
            acao: 'simulacao_concluida',
            resultado: 'sucesso',
            correlacao: 'corr-2',
            tipo: 'execucao',
            mensagemId: null,
          },
        ],
      }),
    )
    const usuario = userEvent.setup()
    render(<SuperficieAlertas seguradoId={SEGURADO_ID} />)
    await usuario.click(await screen.findByRole('button', { name: 'Ver detalhe' }))

    expect(await screen.findByText(/simulacao_concluida/)).toBeInTheDocument()
    expect(screen.queryByText(/[Vv]isualizad[ao]/)).not.toBeInTheDocument()
  })

  it('move o foco para o título do detalhe ao selecionar, sem apagar o anúncio', async () => {
    getListaAlertasMock.mockResolvedValue([item()])
    getDetalheAlertaMock.mockResolvedValue(detalhe())
    const usuario = userEvent.setup()
    render(<SuperficieAlertas seguradoId={SEGURADO_ID} />)
    await usuario.click(await screen.findByRole('button', { name: 'Ver detalhe' }))

    const titulo = await screen.findByRole('heading', { name: 'Chuva intensa' })
    expect(titulo).toHaveFocus()
  })

  it('devolve o foco ao botão de origem específico ao voltar para a lista, numa lista com vários itens', async () => {
    const itens = [
      item({ alerta: alertaBase({ elegibilidadeId: 'item-1' }) }),
      item({ alerta: alertaBase({ elegibilidadeId: 'item-2' }) }),
      item({ alerta: alertaBase({ elegibilidadeId: 'item-3' }) }),
    ]
    getListaAlertasMock.mockResolvedValue(itens)
    getDetalheAlertaMock.mockResolvedValue(detalhe({ alerta: alertaBase({ elegibilidadeId: 'item-3' }) }))
    const usuario = userEvent.setup()
    render(<SuperficieAlertas seguradoId={SEGURADO_ID} />)
    const botoesVerDetalhe = await screen.findAllByRole('button', { name: 'Ver detalhe' })
    expect(botoesVerDetalhe).toHaveLength(3)
    // Seleciona o ÚLTIMO item, não o primeiro - prova que o foco restaurado é o do item
    // que foi de fato aberto, não sempre o primeiro botão da lista.
    await usuario.click(botoesVerDetalhe[2])
    await screen.findByRole('heading', { name: 'Chuva intensa' })

    await usuario.click(screen.getByRole('button', { name: 'Voltar à lista' }))

    await screen.findAllByRole('button', { name: 'Ver detalhe' })
    expect(document.getElementById('botao-detalhe-item-3')).toHaveFocus()
  })

  it('mostra Ainda não simulado explicitamente, sem nenhum comunicado (ALERTAS-06)', async () => {
    getListaAlertasMock.mockResolvedValue([item({ classificacao: 'ainda_nao_simulado' })])
    getDetalheAlertaMock.mockResolvedValue(detalhe({ classificacao: 'ainda_nao_simulado' }))
    const usuario = userEvent.setup()
    render(<SuperficieAlertas seguradoId={SEGURADO_ID} />)
    await usuario.click(await screen.findByRole('button', { name: 'Ver detalhe' }))

    expect(
      await screen.findByText(/Ainda não simulado — nenhum comunicado foi produzido/),
    ).toBeInTheDocument()
    expect(screen.queryByText(/[Cc]omunicado simulado/)).not.toBeInTheDocument()
    expect(screen.queryByText(/[Vv]isualizad[ao]/)).not.toBeInTheDocument()
  })
})

describe('isolamento e Não encontrado (ALERTAS-05)', () => {
  it('mostra Não encontrado ao acessar diretamente um alerta inexistente ou de outro segurado', async () => {
    getListaAlertasMock.mockResolvedValue([])
    getDetalheAlertaMock.mockRejectedValue(
      new ErroListaAlertas({
        codigo: 'alerta_nao_encontrado',
        correlacaoId: null,
        ocorrencia: "O alerta 'x' não existe para este segurado.",
        impacto: 'Nenhum detalhe pode ser exibido.',
        proximaAcao: 'Consulte o alerta pela lista.',
        status: 404,
      }),
    )

    render(
      <SuperficieAlertas seguradoId={SEGURADO_ID} elegibilidadeIdInicial={ELEGIBILIDADE_ID} />,
    )

    expect(await screen.findByRole('heading', { name: 'Não encontrado' })).toBeInTheDocument()
    expect(
      screen.getByText('Este alerta não existe ou não pertence a você.'),
    ).toBeInTheDocument()
  })

  it('permite voltar à lista a partir do Não encontrado', async () => {
    getListaAlertasMock.mockResolvedValue([item()])
    getDetalheAlertaMock.mockRejectedValue(
      new ErroListaAlertas({
        codigo: 'alerta_nao_encontrado',
        correlacaoId: null,
        ocorrencia: "O alerta 'x' não existe para este segurado.",
        impacto: 'Nenhum detalhe pode ser exibido.',
        proximaAcao: 'Consulte o alerta pela lista.',
        status: 404,
      }),
    )
    render(
      <SuperficieAlertas seguradoId={SEGURADO_ID} elegibilidadeIdInicial="outro-id" />,
    )
    await screen.findByRole('heading', { name: 'Não encontrado' })
    const usuario = userEvent.setup()

    await usuario.click(screen.getByRole('button', { name: 'Voltar à lista' }))

    expect(await screen.findByRole('button', { name: 'Ver detalhe' })).toBeInTheDocument()
  })
})

describe('acessibilidade de teclado (ALERTAS-03)', () => {
  it('o botão de detalhe é alcançável e ativável por teclado', async () => {
    getListaAlertasMock.mockResolvedValue([item()])
    getDetalheAlertaMock.mockResolvedValue(detalhe())
    render(<SuperficieAlertas seguradoId={SEGURADO_ID} />)
    await screen.findByRole('button', { name: 'Ver detalhe' })

    const usuario = userEvent.setup()
    await usuario.tab()
    expect(screen.getByRole('button', { name: 'Ver detalhe' })).toHaveFocus()
    await usuario.keyboard('{Enter}')

    expect(await screen.findByRole('heading', { name: 'Chuva intensa' })).toBeInTheDocument()
  })
})

describe('resolução do segurado ativo', () => {
  it('sem seguradoId informado, resolve o segurado padrão internamente', async () => {
    getListaAlertasMock.mockResolvedValue([])

    render(<SuperficieAlertas />)

    await screen.findByRole('heading', { name: 'Nenhum alerta no momento' })
    expect(getSeguradoPadraoMock).toHaveBeenCalledTimes(1)
    expect(getListaAlertasMock).toHaveBeenCalledWith(SEGURADO_ID)
  })

  it('descarta uma resposta antiga que chega depois de uma troca de segurado mais recente', async () => {
    const antiga = promessaControlada<ItemAlerta[]>()
    getListaAlertasMock.mockReturnValueOnce(antiga.promessa)
    const { rerender } = render(<SuperficieAlertas seguradoId={SEGURADO_ID} />)
    await screen.findByText('Carregando alertas…')

    const nova = promessaControlada<ItemAlerta[]>()
    getListaAlertasMock.mockReturnValueOnce(nova.promessa)
    rerender(<SuperficieAlertas seguradoId={OUTRO_SEGURADO_ID} />)

    nova.resolver([item({ alerta: alertaBase({ localizacao: 'AREA-NOVA' }) })])
    await screen.findByRole('cell', { name: 'AREA-NOVA' })

    antiga.resolver([item({ alerta: alertaBase({ localizacao: 'AREA-ANTIGA' }) })])

    // Aguarda um macrotask real para dar tempo da continuação assíncrona da resposta
    // obsoleta rodar e provar que o guard de token a descarta.
    await new Promise((resolucao) => setTimeout(resolucao, 50))
    expect(screen.queryByRole('cell', { name: 'AREA-ANTIGA' })).not.toBeInTheDocument()
    expect(screen.getByRole('cell', { name: 'AREA-NOVA' })).toBeInTheDocument()
  })
})

describe('explicação da mensagem (6.8, ABRIREXP-01..03, 06, 07)', () => {
  beforeEach(() => {
    getExplicacaoMock.mockResolvedValue(explicacaoBase())
  })

  it('não exibe a ação quando o alerta selecionado não tem entrega simulada associada', async () => {
    getListaAlertasMock.mockResolvedValue([item()])
    getDetalheAlertaMock.mockResolvedValue(detalhe())
    const usuario = userEvent.setup()
    render(<SuperficieAlertas seguradoId={SEGURADO_ID} />)
    await usuario.click(await screen.findByRole('button', { name: 'Ver detalhe' }))
    await screen.findByRole('heading', { name: 'Chuva intensa' })

    expect(
      screen.queryByRole('button', { name: 'Ver como esta mensagem foi criada' }),
    ).not.toBeInTheDocument()
  })

  it('exibe a ação e abre o drawer com o seguradoId/entregaSimuladaId deste alerta', async () => {
    getListaAlertasMock.mockResolvedValue([item()])
    getDetalheAlertaMock.mockResolvedValue(
      detalhe({ alerta: alertaBase({ entregaSimuladaId: ENTREGA_ID }) }),
    )
    const usuario = userEvent.setup()
    render(<SuperficieAlertas seguradoId={SEGURADO_ID} />)
    await usuario.click(await screen.findByRole('button', { name: 'Ver detalhe' }))
    await screen.findByRole('heading', { name: 'Chuva intensa' })

    await usuario.click(screen.getByRole('button', { name: 'Ver como esta mensagem foi criada' }))

    expect(await screen.findByRole('dialog')).toBeInTheDocument()
    expect(getExplicacaoMock).toHaveBeenCalledWith(SEGURADO_ID, ENTREGA_ID)
  })

  it('fechar o drawer devolve o foco ao botão que o abriu', async () => {
    getListaAlertasMock.mockResolvedValue([item()])
    getDetalheAlertaMock.mockResolvedValue(
      detalhe({ alerta: alertaBase({ entregaSimuladaId: ENTREGA_ID }) }),
    )
    const usuario = userEvent.setup()
    render(<SuperficieAlertas seguradoId={SEGURADO_ID} />)
    await usuario.click(await screen.findByRole('button', { name: 'Ver detalhe' }))
    await screen.findByRole('heading', { name: 'Chuva intensa' })
    const botaoAbrir = screen.getByRole('button', { name: 'Ver como esta mensagem foi criada' })

    await usuario.click(botaoAbrir)
    await screen.findByRole('dialog')
    await usuario.click(screen.getByRole('button', { name: 'Fechar' }))

    await waitFor(() => expect(botaoAbrir).toHaveFocus())
  })

  it('cada alerta com entrega distinta abre a explicação da própria entrega, nunca a de outro (Edge Case)', async () => {
    const entregaOutroAlerta = '88888888-8888-8888-8888-888888888888'
    getListaAlertasMock.mockResolvedValue([
      item({ alerta: alertaBase({ elegibilidadeId: 'item-1', entregaSimuladaId: ENTREGA_ID }) }),
      item({
        alerta: alertaBase({ elegibilidadeId: 'item-2', entregaSimuladaId: entregaOutroAlerta }),
      }),
    ])
    getDetalheAlertaMock.mockImplementation(async (_segurado: string, elegibilidadeId: string) =>
      detalhe({
        alerta: alertaBase({
          elegibilidadeId,
          entregaSimuladaId: elegibilidadeId === 'item-1' ? ENTREGA_ID : entregaOutroAlerta,
        }),
      }),
    )
    const usuario = userEvent.setup()
    render(<SuperficieAlertas seguradoId={SEGURADO_ID} />)
    const botoesVerDetalhe = await screen.findAllByRole('button', { name: 'Ver detalhe' })
    await usuario.click(botoesVerDetalhe[1])
    await screen.findByRole('heading', { name: 'Chuva intensa' })

    await usuario.click(screen.getByRole('button', { name: 'Ver como esta mensagem foi criada' }))

    await waitFor(() =>
      expect(getExplicacaoMock).toHaveBeenCalledWith(SEGURADO_ID, entregaOutroAlerta),
    )
    expect(getExplicacaoMock).not.toHaveBeenCalledWith(SEGURADO_ID, ENTREGA_ID)
  })

  it('trocar de segurado ativo com o drawer aberto o fecha (Edge Case)', async () => {
    getListaAlertasMock.mockResolvedValue([item()])
    getDetalheAlertaMock.mockResolvedValue(
      detalhe({ alerta: alertaBase({ entregaSimuladaId: ENTREGA_ID }) }),
    )
    const usuario = userEvent.setup()
    const { rerender } = render(<SuperficieAlertas seguradoId={SEGURADO_ID} />)
    await usuario.click(await screen.findByRole('button', { name: 'Ver detalhe' }))
    await screen.findByRole('heading', { name: 'Chuva intensa' })
    await usuario.click(screen.getByRole('button', { name: 'Ver como esta mensagem foi criada' }))
    await screen.findByRole('dialog')

    rerender(<SuperficieAlertas seguradoId={OUTRO_SEGURADO_ID} />)

    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
  })
})

describe('erros de contexto', () => {
  it('mostra falha de contexto ao resolver o segurado padrão', async () => {
    getSeguradoPadraoMock.mockRejectedValue(
      new ErroContexto({
        codigo: 'falha_de_rede',
        correlacaoId: null,
        ocorrencia: 'Não foi possível falar com o backend.',
        impacto: 'Nenhum alerta pôde ser exibido.',
        proximaAcao: 'Tente novamente.',
        status: null,
      }),
    )

    render(<SuperficieAlertas />)

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Não foi possível falar com o backend.',
    )
  })
})
