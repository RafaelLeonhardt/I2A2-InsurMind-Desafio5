import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { type AlertaSegurado, ErroAlertaSegurado } from '../../api/alertaSegurado'
import { ErroContexto } from '../../api/contexto'
import { VisaoGeralSegurado } from './VisaoGeralSegurado'

const { getAlertaMaisRelevanteMock, getSeguradoPadraoMock } = vi.hoisted(() => ({
  getAlertaMaisRelevanteMock: vi.fn(),
  getSeguradoPadraoMock: vi.fn(),
}))

vi.mock('../../api/alertaSegurado', async (importarOriginal) => ({
  ...(await importarOriginal<typeof import('../../api/alertaSegurado')>()),
  getAlertaMaisRelevante: getAlertaMaisRelevanteMock,
}))

vi.mock('../../api/contexto', async (importarOriginal) => ({
  ...(await importarOriginal<typeof import('../../api/contexto')>()),
  getSeguradoPadrao: getSeguradoPadraoMock,
}))

const SEGURADO_ID = '11111111-1111-1111-1111-111111111111'
const OUTRO_SEGURADO_ID = '22222222-2222-2222-2222-222222222222'

function alertaReal(sobrescritas: Partial<AlertaSegurado> = {}): AlertaSegurado {
  return {
    elegibilidadeId: '33333333-3333-3333-3333-333333333333',
    eventoTipo: 'chuva_intensa',
    severidade: '72.5 mm — Intensidade observada atinge o limiar de 50.0 mm.',
    periodoInicio: '2026-09-04T12:00:00',
    periodoFim: '2026-09-04T18:00:00',
    localizacao: '9990001',
    impactosEsperados: ['alagamento'],
    recomendacoes: [
      'Evite áreas alagadas e não atravesse ruas com água corrente.',
      'Desligue a energia elétrica se a água ameaçar entrar no imóvel.',
    ],
    origem: 'real_inmet',
    instanteObservado: '2026-09-04T18:00:00',
    fonteDegradada: false,
    ...sobrescritas,
  }
}

/** Uma promise controlável de fora, para observar o estado antes/depois da resolução. */
function promessaControlada<T>() {
  let resolver: (valor: T) => void = () => {}
  let rejeitar: (erro: unknown) => void = () => {}
  const promessa = new Promise<T>((resolve, reject) => {
    resolver = resolve
    rejeitar = reject
  })
  return { promessa, resolver, rejeitar }
}

beforeEach(() => {
  vi.resetAllMocks()
  getSeguradoPadraoMock.mockResolvedValue({ id: SEGURADO_ID, nome: 'Pessoa Segurada Sintética' })
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('estado Carregando', () => {
  it('mostra o indicador de carregamento antes da primeira resposta', async () => {
    const controlada = promessaControlada<AlertaSegurado | null>()
    getAlertaMaisRelevanteMock.mockReturnValue(controlada.promessa)

    render(<VisaoGeralSegurado seguradoId={SEGURADO_ID} />)

    expect(await screen.findByText('Carregando alerta…')).toBeInTheDocument()

    controlada.resolver(alertaReal())
    await screen.findByRole('heading', { level: 1 })
  })
})

describe('estado Alerta (VISAO-01, 02, 03)', () => {
  it('mostra tipo, severidade, período, localização, impactos e recomendações reais', async () => {
    getAlertaMaisRelevanteMock.mockResolvedValue(alertaReal())

    render(<VisaoGeralSegurado seguradoId={SEGURADO_ID} />)

    expect(await screen.findByRole('heading', { level: 2, name: 'Chuva intensa' })).toBeInTheDocument()
    expect(screen.getByText(/72.5 mm/)).toBeInTheDocument()
    expect(
      screen.getByText(/Previsto entre 2026-09-04T12:00:00 e 2026-09-04T18:00:00 em/),
    ).toBeInTheDocument()
    expect(screen.getAllByText(/9990001/).length).toBeGreaterThan(0)
    expect(screen.getByText('alagamento')).toBeInTheDocument()
    expect(
      screen.getByText('Evite áreas alagadas e não atravesse ruas com água corrente.'),
    ).toBeInTheDocument()
  })

  it('mostra o horário do dado observado no painel de contexto (VISAO-02)', async () => {
    getAlertaMaisRelevanteMock.mockResolvedValue(
      alertaReal({ instanteObservado: '2026-09-04T18:00:00' }),
    )

    render(<VisaoGeralSegurado seguradoId={SEGURADO_ID} />)

    await screen.findByRole('heading', { level: 2, name: 'Chuva intensa' })
    expect(screen.getByText('Horário do dado').closest('div')).toHaveTextContent(
      '2026-09-04T18:00:00',
    )
  })

  it('rotula origem real como observação real, nunca como sintética', async () => {
    getAlertaMaisRelevanteMock.mockResolvedValue(alertaReal({ origem: 'real_inmet' }))

    render(<VisaoGeralSegurado seguradoId={SEGURADO_ID} />)

    await screen.findByRole('heading', { level: 1 })
    expect(screen.getAllByText(/Observação real \(INMET\)/).length).toBeGreaterThan(0)
    expect(screen.queryByText(/sintétic/i)).not.toBeInTheDocument()
  })

  it('rotula origem sintética como cenário demonstrativo, nunca como observação real', async () => {
    getAlertaMaisRelevanteMock.mockResolvedValue(alertaReal({ origem: 'sintetico' }))

    render(<VisaoGeralSegurado seguradoId={SEGURADO_ID} />)

    await screen.findByRole('heading', { level: 1 })
    expect(screen.getAllByText(/sintétic/i).length).toBeGreaterThan(0)
    expect(screen.queryByText(/Observação real/)).not.toBeInTheDocument()
  })

  it('esclarece que a comunicação é privada e não confirma cobertura/autoridade', async () => {
    getAlertaMaisRelevanteMock.mockResolvedValue(alertaReal())

    render(<VisaoGeralSegurado seguradoId={SEGURADO_ID} />)

    expect(
      await screen.findByText(/não substitui as autoridades competentes/),
    ).toBeInTheDocument()
    expect(screen.getByText(/não confirma cobertura ou indenização/)).toBeInTheDocument()
  })

  it('não contém mais nenhum texto fixo de alerta/localização/apólice/regra', async () => {
    getAlertaMaisRelevanteMock.mockResolvedValue(alertaReal())

    render(<VisaoGeralSegurado seguradoId={SEGURADO_ID} />)

    await screen.findByRole('heading', { level: 1 })
    expect(screen.queryByText('AUTO-DEMO-001')).not.toBeInTheDocument()
    expect(screen.queryByText('Campinas (SP), CEP 13000-000')).not.toBeInTheDocument()
    expect(screen.queryByText('Há chuva forte prevista para sua região.')).not.toBeInTheDocument()
  })
})

describe('fonte degradada (VISAO-05)', () => {
  it('mostra o snapshot com idade e caráter informativo, sem sugerir alerta novo', async () => {
    // Instante fixo e distante: calcularIdade sempre devolve "N d atrás" para ele,
    // independente da data real em que o teste roda (VISAO-05 exige a idade visível).
    getAlertaMaisRelevanteMock.mockResolvedValue(
      alertaReal({ fonteDegradada: true, instanteObservado: '2020-01-01T00:00:00' }),
    )

    render(<VisaoGeralSegurado seguradoId={SEGURADO_ID} />)

    expect(await screen.findByText(/Fonte meteorológica degradada/)).toBeInTheDocument()
    expect(screen.getByText(/apenas informativo/)).toBeInTheDocument()
    expect(screen.getByText(/\d+ d atrás/)).toBeInTheDocument()
  })

  it('não mostra o aviso de fonte degradada quando a fonte está operacional', async () => {
    getAlertaMaisRelevanteMock.mockResolvedValue(alertaReal({ fonteDegradada: false }))

    render(<VisaoGeralSegurado seguradoId={SEGURADO_ID} />)

    await screen.findByRole('heading', { level: 1 })
    expect(screen.queryByText(/Fonte meteorológica degradada/)).not.toBeInTheDocument()
  })
})

describe('estado Sem alerta (VISAO-04)', () => {
  it('mostra um estado vazio explicativo, sem inventar risco ou recomendação', async () => {
    getAlertaMaisRelevanteMock.mockResolvedValue(null)

    render(<VisaoGeralSegurado seguradoId={SEGURADO_ID} />)

    expect(
      await screen.findByRole('heading', { name: 'Nenhum alerta relevante no momento' }),
    ).toBeInTheDocument()
    expect(screen.queryByRole('heading', { level: 2, name: 'Chuva intensa' })).not.toBeInTheDocument()
  })

  it('não promete navegação para superfícies que ainda não existem no perfil Segurado', async () => {
    getAlertaMaisRelevanteMock.mockResolvedValue(null)

    render(<VisaoGeralSegurado seguradoId={SEGURADO_ID} />)

    await screen.findByRole('heading', { name: 'Nenhum alerta relevante no momento' })
    for (const superficieInexistente of ['Apólice', 'Comunicados', 'Meus Dados']) {
      expect(screen.queryByText(new RegExp(superficieInexistente))).not.toBeInTheDocument()
    }
  })
})

describe('estado Contexto trocando', () => {
  it('mostra Contexto trocando ao alternar de segurado sem misturar dado antigo e novo', async () => {
    getAlertaMaisRelevanteMock.mockResolvedValueOnce(
      alertaReal({ localizacao: 'AREA-ANTIGA' }),
    )
    const { rerender } = render(<VisaoGeralSegurado seguradoId={SEGURADO_ID} />)
    await screen.findAllByText(/AREA-ANTIGA/)

    const controlada = promessaControlada<AlertaSegurado | null>()
    getAlertaMaisRelevanteMock.mockReturnValueOnce(controlada.promessa)
    rerender(<VisaoGeralSegurado seguradoId={OUTRO_SEGURADO_ID} />)

    expect(await screen.findByText('Contexto trocando…')).toBeInTheDocument()
    expect(screen.queryAllByText(/AREA-ANTIGA/).length).toBe(0)

    controlada.resolver(alertaReal({ localizacao: 'AREA-NOVA' }))
    expect((await screen.findAllByText(/AREA-NOVA/)).length).toBeGreaterThan(0)
  })

  it('descarta uma resposta antiga que chega depois de uma troca mais recente', async () => {
    const antiga = promessaControlada<AlertaSegurado | null>()
    getAlertaMaisRelevanteMock.mockReturnValueOnce(antiga.promessa)
    const { rerender } = render(<VisaoGeralSegurado seguradoId={SEGURADO_ID} />)
    await screen.findByText('Carregando alerta…')

    const nova = promessaControlada<AlertaSegurado | null>()
    getAlertaMaisRelevanteMock.mockReturnValueOnce(nova.promessa)
    rerender(<VisaoGeralSegurado seguradoId={OUTRO_SEGURADO_ID} />)

    nova.resolver(alertaReal({ localizacao: 'AREA-NOVA' }))
    await screen.findAllByText(/AREA-NOVA/)

    antiga.resolver(alertaReal({ localizacao: 'AREA-ANTIGA' }))

    // Aguarda um macrotask real (não só um microtask) para que a continuação assíncrona
    // de `carregar` (após o `await` da resposta obsoleta) tenha a chance de rodar e
    // provar que o guard de token a descarta - um único `await Promise.resolve()` não
    // dá tempo suficiente e deixaria este teste passar mesmo sem o guard.
    await new Promise((resolver) => setTimeout(resolver, 50))
    expect(screen.queryAllByText(/AREA-ANTIGA/).length).toBe(0)
    expect(screen.getAllByText(/AREA-NOVA/).length).toBeGreaterThan(0)
  })
})

describe('estado Erro (VISAO-06)', () => {
  it('uma falha na primeira carga mostra Erro, nunca o estado Sem alerta', async () => {
    getAlertaMaisRelevanteMock.mockRejectedValueOnce(
      new ErroAlertaSegurado({
        codigo: 'falha_local',
        correlacaoId: null,
        ocorrencia: 'Falha ao consultar o alerta.',
        impacto: 'O alerta pode estar desatualizado.',
        proximaAcao: 'Tente novamente.',
        status: 500,
      }),
    )

    render(<VisaoGeralSegurado seguradoId={SEGURADO_ID} />)

    expect(
      await screen.findByRole('heading', { name: 'Não foi possível carregar seu alerta' }),
    ).toBeInTheDocument()
    expect(
      screen.queryByRole('heading', { name: 'Nenhum alerta relevante no momento' }),
    ).not.toBeInTheDocument()
  })

  it('informa ocorrência, impacto e próxima ação sem apagar o alerta já exibido', async () => {
    getAlertaMaisRelevanteMock.mockResolvedValueOnce(alertaReal({ localizacao: 'AREA-VALIDA' }))
    const { rerender } = render(<VisaoGeralSegurado seguradoId={SEGURADO_ID} />)
    await screen.findAllByText(/AREA-VALIDA/)

    getAlertaMaisRelevanteMock.mockRejectedValueOnce(
      new ErroAlertaSegurado({
        codigo: 'falha_local',
        correlacaoId: null,
        ocorrencia: 'Falha ao consultar o alerta.',
        impacto: 'O alerta pode estar desatualizado.',
        proximaAcao: 'Tente novamente.',
        status: 500,
      }),
    )
    // Uma troca de contexto (5.7) é o gatilho real de uma nova consulta enquanto um
    // alerta válido já está na tela — não há botão de atualizar no estado Alerta.
    rerender(<VisaoGeralSegurado seguradoId={OUTRO_SEGURADO_ID} />)

    const alerta = await screen.findByRole('alert')
    expect(alerta).toHaveTextContent('Falha ao consultar o alerta.')
    expect(alerta).toHaveTextContent('O alerta pode estar desatualizado.')
    expect(alerta).toHaveTextContent('Tente novamente.')
    expect((await screen.findAllByText(/AREA-VALIDA/)).length).toBeGreaterThan(0)
  })

  it('preserva o estado Sem alerta já exibido quando uma nova consulta falha', async () => {
    getAlertaMaisRelevanteMock.mockResolvedValueOnce(null)
    const { rerender } = render(<VisaoGeralSegurado seguradoId={SEGURADO_ID} />)
    await screen.findByRole('heading', { name: 'Nenhum alerta relevante no momento' })

    getAlertaMaisRelevanteMock.mockRejectedValueOnce(
      new ErroAlertaSegurado({
        codigo: 'falha_local',
        correlacaoId: null,
        ocorrencia: 'Falha ao consultar o alerta.',
        impacto: 'O alerta pode estar desatualizado.',
        proximaAcao: 'Tente novamente.',
        status: 500,
      }),
    )
    rerender(<VisaoGeralSegurado seguradoId={OUTRO_SEGURADO_ID} />)

    expect(await screen.findByRole('alert')).toBeInTheDocument()
    expect(
      screen.getByRole('heading', { name: 'Nenhum alerta relevante no momento' }),
    ).toBeInTheDocument()
  })

  it('permite nova tentativa que recupera o alerta', async () => {
    getAlertaMaisRelevanteMock.mockRejectedValueOnce(
      new ErroContexto({
        codigo: 'falha_de_rede',
        correlacaoId: null,
        ocorrencia: 'Não foi possível falar com o backend.',
        impacto: 'Nenhum alerta pôde ser exibido.',
        proximaAcao: 'Tente novamente.',
        status: null,
      }),
    )
    render(<VisaoGeralSegurado seguradoId={SEGURADO_ID} />)
    await screen.findByRole('alert')

    getAlertaMaisRelevanteMock.mockResolvedValueOnce(alertaReal())
    const usuario = userEvent.setup()
    await usuario.click(screen.getByRole('button', { name: 'Tentar novamente' }))

    expect(await screen.findByRole('heading', { level: 2, name: 'Chuva intensa' })).toBeInTheDocument()
  })
})

describe('acessibilidade de teclado e zoom (VISAO-07, 08)', () => {
  it('o botão de nova tentativa do estado de erro é alcançável e ativável por teclado', async () => {
    getAlertaMaisRelevanteMock.mockRejectedValueOnce(
      new ErroAlertaSegurado({
        codigo: 'falha_local',
        correlacaoId: null,
        ocorrencia: 'Falha ao consultar o alerta.',
        impacto: 'Impacto.',
        proximaAcao: 'Ação.',
        status: 500,
      }),
    )
    getAlertaMaisRelevanteMock.mockResolvedValueOnce(alertaReal())
    render(<VisaoGeralSegurado seguradoId={SEGURADO_ID} />)
    await screen.findByRole('alert')

    const usuario = userEvent.setup()
    await usuario.tab()
    expect(screen.getByRole('button', { name: 'Tentar novamente' })).toHaveFocus()
    await usuario.keyboard('{Enter}')

    expect(await screen.findByRole('heading', { level: 2, name: 'Chuva intensa' })).toBeInTheDocument()
  })

  it('preserva toda informação essencial em viewport reduzido (zoom 200%)', async () => {
    const larguraOriginal = window.innerWidth
    window.innerWidth = 640
    window.dispatchEvent(new Event('resize'))
    try {
      getAlertaMaisRelevanteMock.mockResolvedValue(alertaReal())

      render(<VisaoGeralSegurado seguradoId={SEGURADO_ID} />)

      expect(await screen.findByRole('heading', { level: 2, name: 'Chuva intensa' })).toBeInTheDocument()
      expect(screen.getByText(/72.5 mm/)).toBeInTheDocument()
      expect(screen.getAllByText(/Observação real \(INMET\)/).length).toBeGreaterThan(0)
      expect(screen.getAllByText(/9990001/).length).toBeGreaterThan(0)
      expect(screen.getByText('alagamento')).toBeInTheDocument()
      expect(
        screen.getByText('Evite áreas alagadas e não atravesse ruas com água corrente.'),
      ).toBeInTheDocument()
    } finally {
      window.innerWidth = larguraOriginal
      window.dispatchEvent(new Event('resize'))
    }
  })

  it('nenhuma informação essencial depende só de cor/ícone (rótulo textual acompanha o ícone)', async () => {
    getAlertaMaisRelevanteMock.mockResolvedValue(alertaReal({ origem: 'sintetico' }))

    render(<VisaoGeralSegurado seguradoId={SEGURADO_ID} />)

    await screen.findByRole('heading', { level: 1 })
    // O ícone de proveniência sintética é aria-hidden; o texto ao lado carrega o sinal.
    expect(screen.getAllByText(/Cenário demonstrativo \(sintético\)/).length).toBeGreaterThan(0)
  })
})

describe('resolução do segurado ativo', () => {
  it('sem seguradoId informado, resolve o segurado padrão internamente', async () => {
    getAlertaMaisRelevanteMock.mockResolvedValue(alertaReal())

    render(<VisaoGeralSegurado />)

    await screen.findByRole('heading', { level: 1 })
    expect(getSeguradoPadraoMock).toHaveBeenCalledTimes(1)
    expect(getAlertaMaisRelevanteMock).toHaveBeenCalledWith(SEGURADO_ID)
  })
})
