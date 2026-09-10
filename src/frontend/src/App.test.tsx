import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useEffect } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App, { SuperficieAtiva } from './App'
import { CHAVE_ARMAZENAMENTO_PERFIL, PerfilProvider, usePerfilContexto } from './contexto/PerfilContexto'

const {
  getSeguradoPadraoMock,
  restaurarDadosSinteticosMock,
  verificarDocumentacaoApiMock,
  getAlertaMaisRelevanteMock,
  getListaSeguradosMock,
  getListaAlertasMock,
  getApoliceMock,
  getListaComunicadosMock,
  getPreferenciasMock,
  getExecucaoMock,
  getEventosMock,
  getSincronizacoesMock,
  getRegrasMock,
  getSeguradosDetalhadoMock,
  getResultadosMock,
  buscarExecucoesMock,
} = vi.hoisted(() => ({
  getSeguradoPadraoMock: vi.fn(),
  restaurarDadosSinteticosMock: vi.fn(),
  verificarDocumentacaoApiMock: vi.fn(),
  getAlertaMaisRelevanteMock: vi.fn(),
  getListaSeguradosMock: vi.fn(),
  getListaAlertasMock: vi.fn(),
  getApoliceMock: vi.fn(),
  getListaComunicadosMock: vi.fn(),
  getPreferenciasMock: vi.fn(),
  getExecucaoMock: vi.fn(),
  getEventosMock: vi.fn(),
  getSincronizacoesMock: vi.fn(),
  getRegrasMock: vi.fn(),
  getSeguradosDetalhadoMock: vi.fn(),
  getResultadosMock: vi.fn(),
  buscarExecucoesMock: vi.fn(),
}))

vi.mock('./api/contexto', async () => {
  const real = await vi.importActual<typeof import('./api/contexto')>('./api/contexto')
  return {
    ...real,
    getSeguradoPadrao: getSeguradoPadraoMock,
  }
})

vi.mock('./api/alertaSegurado', async () => {
  const real = await vi.importActual<typeof import('./api/alertaSegurado')>('./api/alertaSegurado')
  return {
    ...real,
    getAlertaMaisRelevante: getAlertaMaisRelevanteMock,
  }
})

vi.mock('./api/dadosSinteticos', async () => {
  const real = await vi.importActual<typeof import('./api/dadosSinteticos')>('./api/dadosSinteticos')
  return {
    ...real,
    restaurarDadosSinteticos: restaurarDadosSinteticosMock,
  }
})

vi.mock('./api/documentacaoApi', async () => {
  const real = await vi.importActual<typeof import('./api/documentacaoApi')>('./api/documentacaoApi')
  return {
    ...real,
    verificarDocumentacaoApi: verificarDocumentacaoApiMock,
  }
})

// PainelSegurado (5.7) monta as cinco superfícies de 5.1-5.6 juntas sob o perfil Segurado —
// cada uma precisa de sua própria API mockada para o shell permanecer hermético (sem
// requisição de rede real em nenhum teste deste arquivo).
vi.mock('./api/listaSegurados', async () => {
  const real = await vi.importActual<typeof import('./api/listaSegurados')>('./api/listaSegurados')
  return { ...real, getListaSegurados: getListaSeguradosMock }
})

vi.mock('./api/listaAlertasSegurado', async () => {
  const real =
    await vi.importActual<typeof import('./api/listaAlertasSegurado')>('./api/listaAlertasSegurado')
  return { ...real, getListaAlertas: getListaAlertasMock }
})

vi.mock('./api/apoliceSegurado', async () => {
  const real = await vi.importActual<typeof import('./api/apoliceSegurado')>('./api/apoliceSegurado')
  return { ...real, getApolice: getApoliceMock }
})

vi.mock('./api/listaComunicados', async () => {
  const real = await vi.importActual<typeof import('./api/listaComunicados')>('./api/listaComunicados')
  return { ...real, getListaComunicados: getListaComunicadosMock }
})

vi.mock('./api/preferenciasSegurado', async () => {
  const real =
    await vi.importActual<typeof import('./api/preferenciasSegurado')>('./api/preferenciasSegurado')
  return { ...real, getPreferencias: getPreferenciasMock }
})

vi.mock('./api/execucao', async () => {
  const real = await vi.importActual<typeof import('./api/execucao')>('./api/execucao')
  return { ...real, getExecucao: getExecucaoMock }
})

vi.mock('./api/meteorologia', async () => {
  const real = await vi.importActual<typeof import('./api/meteorologia')>('./api/meteorologia')
  return { ...real, getEventos: getEventosMock, getSincronizacoes: getSincronizacoesMock }
})

vi.mock('./api/regras', async () => {
  const real = await vi.importActual<typeof import('./api/regras')>('./api/regras')
  return { ...real, getRegras: getRegrasMock }
})

vi.mock('./api/listaSeguradosAdmin', async () => {
  const real =
    await vi.importActual<typeof import('./api/listaSeguradosAdmin')>('./api/listaSeguradosAdmin')
  return { ...real, getSeguradosDetalhado: getSeguradosDetalhadoMock }
})

vi.mock('./api/resultados', async () => {
  const real = await vi.importActual<typeof import('./api/resultados')>('./api/resultados')
  return { ...real, getResultados: getResultadosMock }
})

vi.mock('./api/linhaDoTempo', async () => {
  const real = await vi.importActual<typeof import('./api/linhaDoTempo')>('./api/linhaDoTempo')
  return { ...real, buscarExecucoes: buscarExecucoesMock }
})

function definirLargura(largura: number) {
  Object.defineProperty(window, 'innerWidth', { configurable: true, value: largura })
}

beforeEach(() => {
  getSeguradoPadraoMock.mockResolvedValue({
    id: '11111111-1111-4111-8111-111111111111',
    nome: 'Pessoa Segurada Sintética DEMO-001',
  })
  verificarDocumentacaoApiMock.mockResolvedValue({
    estado: 'disponivel',
    enderecoSwaggerUi: 'http://127.0.0.1:8000/docs',
    enderecoOpenApi: 'http://127.0.0.1:8000/openapi.json',
  })
  getAlertaMaisRelevanteMock.mockResolvedValue({
    elegibilidadeId: '22222222-2222-2222-2222-222222222222',
    eventoTipo: 'chuva_intensa',
    severidade: '72.5 mm — Intensidade observada atinge o limiar de 50.0 mm.',
    periodoInicio: '2026-09-04T12:00:00',
    periodoFim: '2026-09-04T18:00:00',
    localizacao: '9990001',
    impactosEsperados: ['alagamento'],
    recomendacoes: ['Evite áreas alagadas.'],
    origem: 'real_inmet',
    instanteObservado: '2026-09-04T18:00:00',
    fonteDegradada: false,
  })
  getListaSeguradosMock.mockResolvedValue([
    { id: '11111111-1111-4111-8111-111111111111', nome: 'Pessoa Segurada Sintética DEMO-001' },
  ])
  getListaAlertasMock.mockResolvedValue([])
  getApoliceMock.mockResolvedValue({
    numero: 'APOL-0001',
    tipo: 'residencial',
    situacao: 'ativa',
    estadoObjetivo: 'vigente',
    vigenciaInicio: '2026-01-01',
    vigenciaFim: '2026-12-31',
    enderecoRiscoSintetico: 'Endereço sintético',
    coberturas: ['alagamento'],
    canalPreferido: 'whatsapp',
    participaDeAlertas: true,
  })
  getListaComunicadosMock.mockResolvedValue([])
  getPreferenciasMock.mockResolvedValue({
    seguradoId: '11111111-1111-4111-8111-111111111111',
    canalPreferido: 'whatsapp',
    participaDeAlertas: true,
    versao: 1,
  })
  getExecucaoMock.mockResolvedValue({
    id: '33333333-3333-4333-8333-333333333333',
    estado: 'concluida',
    marcos: [],
    publicoElegivelTotal: 0,
    publicoElegivelPrevia: [],
    execucaoOrigemId: null,
    retentativas: [],
  })
  getEventosMock.mockResolvedValue([])
  getSincronizacoesMock.mockResolvedValue({
    ultimaTentativa: null,
    ultimaValida: null,
    proximaConsulta: null,
    resultadosAnteriores: [],
  })
  getRegrasMock.mockResolvedValue([])
  getSeguradosDetalhadoMock.mockResolvedValue([])
  getResultadosMock.mockResolvedValue({
    execucaoId: '33333333-3333-4333-8333-333333333333',
    estado: 'concluida',
    concluido: true,
    totaisPorCanal: [],
    totaisPorEstado: [],
    naoSimulaveis: [],
    divergencia: null,
  })
  buscarExecucoesMock.mockResolvedValue([])
  window.localStorage.clear()
})

afterEach(() => {
  cleanup()
  window.localStorage.clear()
  vi.clearAllMocks()
  definirLargura(1024)
})

describe('shell do contexto demonstrativo', () => {
  it('mantém a faixa fixa "Ambiente educacional · Dados sintéticos · Sem envio real" em qualquer perfil', () => {
    definirLargura(1440)
    render(<App />)

    expect(
      screen.getByText('Ambiente educacional · Dados sintéticos · Sem envio real'),
    ).toBeInTheDocument()
  })

  it('abre no perfil Administrador, com Prontidão e Restaurar dados sintéticos na navegação', () => {
    definirLargura(1440)
    render(<App />)

    expect(screen.getByRole('button', { name: 'Prontidão' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Restaurar dados sintéticos' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Visão geral' })).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Prontidão das dependências' })).toBeInTheDocument()
  })

  it('navega para "Documentação da API" e renderiza a superfície', async () => {
    definirLargura(1440)
    const usuario = userEvent.setup()
    render(<App />)

    await usuario.click(screen.getByRole('button', { name: 'Documentação da API' }))

    expect(
      await screen.findByRole('heading', { name: 'Documentação da API' }),
    ).toBeInTheDocument()
    expect(verificarDocumentacaoApiMock).toHaveBeenCalled()
  })

  it('Administrador → Segurado: navegação mostra somente Visão geral', async () => {
    definirLargura(1440)
    const usuario = userEvent.setup()
    render(<App />)

    await usuario.click(screen.getByRole('button', { name: /Visualizar como Segurado/ }))

    expect(await screen.findByRole('button', { name: 'Visão geral' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Prontidão' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Restaurar dados sintéticos' })).not.toBeInTheDocument()
    expect(
      await screen.findByRole('heading', { name: 'Alerta preventivo para sua área' }),
    ).toBeInTheDocument()
  })

  it('perfil Segurado: o seletor "Visualizar como" está alcançável e troca as superfícies (5.7)', async () => {
    definirLargura(1440)
    const SEGURADO_A = { id: '11111111-1111-4111-8111-111111111111', nome: 'Pessoa Sintética DEMO-001' }
    const SEGURADO_B = { id: '22222222-2222-4222-8222-222222222222', nome: 'Pessoa Sintética DEMO-002' }
    getListaSeguradosMock.mockResolvedValue([SEGURADO_A, SEGURADO_B])
    getApoliceMock.mockImplementation(async (id: string) => ({
      numero: id === SEGURADO_A.id ? 'APOL-A' : 'APOL-B',
      tipo: 'residencial',
      situacao: 'ativa',
      estadoObjetivo: 'vigente',
      vigenciaInicio: '2026-01-01',
      vigenciaFim: '2026-12-31',
      enderecoRiscoSintetico: 'Endereço sintético',
      coberturas: ['alagamento'],
      canalPreferido: 'whatsapp',
      participaDeAlertas: true,
    }))
    const usuario = userEvent.setup()
    render(<App />)

    await usuario.click(screen.getByRole('button', { name: /Visualizar como Segurado/ }))
    await screen.findByRole('button', { name: 'Visão geral' })

    const seletorSegurado = await screen.findByRole('combobox', { name: 'Visualizar como' })
    expect(await screen.findByText('APOL-A')).toBeInTheDocument()

    await usuario.selectOptions(seletorSegurado, SEGURADO_B.id)

    expect(await screen.findByText('APOL-B')).toBeInTheDocument()
    expect(screen.queryByText('APOL-A')).not.toBeInTheDocument()
  })

  it('Segurado → Administrador: navegação mostra Prontidão e Restaurar dados sintéticos', async () => {
    definirLargura(1440)
    window.localStorage.setItem(CHAVE_ARMAZENAMENTO_PERFIL, 'segurado')
    const usuario = userEvent.setup()
    render(<App />)

    await usuario.click(screen.getByRole('button', { name: /Visualizar como Administrador/ }))

    expect(await screen.findByRole('button', { name: 'Prontidão' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Restaurar dados sintéticos' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Visão geral' })).not.toBeInTheDocument()
  })

  it('nunca descreve a troca de perfil como login, autenticação, autorização ou elevação de privilégio', async () => {
    definirLargura(1440)
    const usuario = userEvent.setup()
    const { container } = render(<App />)

    await usuario.click(screen.getByRole('button', { name: /Visualizar como Segurado/ }))
    await screen.findByRole('button', { name: 'Visão geral' })

    const texto = container.textContent ?? ''
    for (const termo of ['login', 'Login', 'autenticaç', 'Autenticaç', 'autorizaç', 'Autorizaç', 'privilégio']) {
      expect(texto).not.toContain(termo)
    }
  })

  it('fecha o modal de restauração aberto ao trocar de perfil, sem chamar nenhuma mutação', async () => {
    definirLargura(1440)
    const usuario = userEvent.setup()
    render(<App />)

    await usuario.click(screen.getByRole('button', { name: 'Restaurar dados sintéticos' }))
    await usuario.click(screen.getByRole('button', { name: 'Restaurar demonstração' }))
    expect(screen.getByRole('dialog')).toBeInTheDocument()

    await usuario.click(screen.getByRole('button', { name: /Visualizar como Segurado/ }))

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(restaurarDadosSinteticosMock).not.toHaveBeenCalled()
  })

  it('persiste o perfil em localStorage e restaura no reload, com "administrador" como padrão', async () => {
    definirLargura(1440)
    const usuario = userEvent.setup()
    const primeira = render(<App />)

    await usuario.click(screen.getByRole('button', { name: /Visualizar como Segurado/ }))
    await screen.findByRole('button', { name: 'Visão geral' })
    expect(window.localStorage.getItem(CHAVE_ARMAZENAMENTO_PERFIL)).toBe('segurado')
    primeira.unmount()

    render(<App />)
    expect(await screen.findByRole('button', { name: 'Visão geral' })).toBeInTheDocument()
  })

  it('trata um valor corrompido em localStorage como ausência de preferência (padrão Administrador)', () => {
    window.localStorage.setItem(CHAVE_ARMAZENAMENTO_PERFIL, 'super-usuario')
    definirLargura(1440)
    render(<App />)

    expect(screen.getByRole('button', { name: 'Prontidão' })).toBeInTheDocument()
    expect(screen.getByText('Administrador')).toBeInTheDocument()
  })

  it('bloqueia contexto inconsistente e oferece o retorno à Visão geral do perfil ativo', async () => {
    // Nenhum fluxo de UI alcança uma superficieAtiva fora da lista do perfil ativo - a
    // NavegacaoLateral só oferece opções válidas (ver design.md). Este teste força a
    // combinação inconsistente diretamente pelo contexto para verificar a salvaguarda.
    function ForcarSuperficieInvalida() {
      const { selecionarSuperficie } = usePerfilContexto()
      useEffect(() => {
        selecionarSuperficie({ tipo: 'visao-geral' })
        // eslint-disable-next-line react-hooks/exhaustive-deps
      }, [])
      return null
    }

    definirLargura(1440)
    const usuario = userEvent.setup()
    render(
      <PerfilProvider>
        <ForcarSuperficieInvalida />
        <SuperficieAtiva />
      </PerfilProvider>,
    )

    expect(
      screen.getByRole('heading', { name: /não está disponível para o perfil Administrador/ }),
    ).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Restaurar demonstração' })).not.toBeInTheDocument()
    expect(screen.queryByText('Pessoa Segurada Sintética DEMO-001')).not.toBeInTheDocument()

    await usuario.click(screen.getByRole('button', { name: 'Voltar para a Visão geral' }))

    expect(screen.getByRole('heading', { name: 'Prontidão das dependências' })).toBeInTheDocument()
  })

  it('mantém navegação e seletor operáveis entre 1024 px e uma largura ampla', () => {
    for (const largura of [1024, 1279, 1920]) {
      cleanup()
      definirLargura(largura)
      render(<App />)

      expect(screen.queryByRole('note')).not.toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Prontidão' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /Visualizar como Segurado/ })).toBeInTheDocument()
    }
  })

  it('exibe o aviso de resolução não suportada abaixo de 1024 px, sem perder funções', () => {
    definirLargura(1024)
    render(<App />)
    expect(screen.queryByRole('note')).not.toBeInTheDocument()

    definirLargura(1023)
    fireEvent(window, new Event('resize'))

    expect(screen.getByRole('note')).toHaveTextContent('Todas as funções permanecem disponíveis')
    expect(screen.getByRole('button', { name: 'Prontidão' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Visualizar como Segurado/ })).toBeInTheDocument()
  })

  it('permite navegação e alternância só por teclado, com foco visível e anúncio aria-live', async () => {
    definirLargura(1440)
    const usuario = userEvent.setup()
    render(<App />)

    await usuario.tab()
    await usuario.tab()
    expect(screen.getByRole('button', { name: 'Prontidão' })).toHaveFocus()

    await usuario.keyboard('{Enter}')
    expect(screen.getByRole('button', { name: 'Prontidão' })).toHaveAttribute('aria-current', 'page')

    const seletor = screen.getByRole('button', { name: /Visualizar como Segurado/ })
    seletor.focus()
    expect(seletor).toHaveFocus()

    await usuario.keyboard('{Enter}')

    expect(await screen.findByRole('button', { name: 'Visão geral' })).toBeInTheDocument()
    await waitFor(() => {
      expect(
        screen.getByText('Visualizando como Segurado').closest('[aria-live="polite"]'),
      ).not.toBeNull()
    })
  })

  it('navega para "Eventos climáticos" e monta SuperficieEventos', async () => {
    definirLargura(1440)
    getEventosMock.mockResolvedValue([
      {
        id: '44444444-4444-4444-4444-444444444444',
        tipo: 'chuva_intensa',
        area: '9990001',
        periodoInicio: '2026-08-30T17:00:00+00:00',
        periodoFim: '2026-08-30T18:00:00+00:00',
        intensidade: 55.4,
        proveniencia: 'real_inmet',
        instanteObservado: '2026-08-30T18:00:00+00:00',
        execucaoId: null,
        execucaoEstado: null,
      },
    ])
    const usuario = userEvent.setup()
    render(<App />)

    await usuario.click(screen.getByRole('button', { name: 'Eventos climáticos' }))

    expect(await screen.findByRole('heading', { name: 'Eventos climáticos' })).toBeInTheDocument()
    expect(await screen.findByText('Sem execução iniciada')).toBeInTheDocument()
    expect(getEventosMock).toHaveBeenCalled()
  })

  it('navega para "Regras de negócio" e monta SuperficieRegras', async () => {
    definirLargura(1440)
    getRegrasMock.mockResolvedValue([
      {
        id: '55555555-5555-4555-8555-555555555555',
        eventoTipo: 'chuva_intensa',
        limiarMeteorologico: 50,
        areaAplicavel: '9990001',
        apoliceTipo: 'residencial',
        coberturaExigida: 'alagamento',
        antecedenciaHoras: 24,
        canal: 'whatsapp',
        versao: 1,
        estado: 'ativa',
      },
    ])
    const usuario = userEvent.setup()
    render(<App />)

    await usuario.click(screen.getByRole('button', { name: 'Regras de negócio' }))

    expect(await screen.findByRole('heading', { name: 'Regras' })).toBeInTheDocument()
    expect(await screen.findByText('Chuva intensa')).toBeInTheDocument()
    expect(getRegrasMock).toHaveBeenCalled()
  })

  it('navega para "Segurados" e monta SuperficieSegurados (6.4)', async () => {
    definirLargura(1440)
    getSeguradosDetalhadoMock.mockResolvedValue([
      {
        id: '44444444-4444-4444-8444-444444444444',
        nome: 'Pessoa Segurada Sintética DEMO-001',
        codigoIbgeArea: '9990001',
        apoliceNumero: 'RES-0001',
        canalPreferido: 'whatsapp',
      },
    ])
    const usuario = userEvent.setup()
    render(<App />)

    await usuario.click(screen.getByRole('button', { name: 'Segurados' }))

    expect(await screen.findByRole('heading', { name: 'Segurados' })).toBeInTheDocument()
    expect(await screen.findByText('Pessoa Segurada Sintética DEMO-001')).toBeInTheDocument()
    expect(getSeguradosDetalhadoMock).toHaveBeenCalled()
  })

  it('navega para "Fontes de dados" e monta SuperficieFonteMeteorologica', async () => {
    definirLargura(1440)
    const usuario = userEvent.setup()
    render(<App />)

    await usuario.click(screen.getByRole('button', { name: 'Fontes de dados' }))

    expect(await screen.findByRole('heading', { name: 'Fonte meteorológica' })).toBeInTheDocument()
    expect(getSincronizacoesMock).toHaveBeenCalled()
  })

  it('uma superfície { tipo: "evento-execucao" } monta SuperficieExecucao com o execucaoId correto', async () => {
    function ForcarSuperficieDeExecucao() {
      const { selecionarSuperficie } = usePerfilContexto()
      useEffect(() => {
        selecionarSuperficie({
          tipo: 'evento-execucao',
          execucaoId: '33333333-3333-4333-8333-333333333333',
          perfilPai: 'administrador',
        })
        // eslint-disable-next-line react-hooks/exhaustive-deps
      }, [])
      return null
    }

    definirLargura(1440)
    render(
      <PerfilProvider>
        <ForcarSuperficieDeExecucao />
        <SuperficieAtiva />
      </PerfilProvider>,
    )

    expect(
      await screen.findByRole('heading', { name: 'Acompanhamento da execução' }),
    ).toBeInTheDocument()
    expect(getExecucaoMock).toHaveBeenCalledWith('33333333-3333-4333-8333-333333333333')
  })

  it('uma superfície { tipo: "resultado-execucao" } monta SuperficieResultados com o execucaoId correto', async () => {
    function ForcarSuperficieDeResultado() {
      const { selecionarSuperficie } = usePerfilContexto()
      useEffect(() => {
        selecionarSuperficie({
          tipo: 'resultado-execucao',
          execucaoId: '33333333-3333-4333-8333-333333333333',
          perfilPai: 'administrador',
        })
        // eslint-disable-next-line react-hooks/exhaustive-deps
      }, [])
      return null
    }

    definirLargura(1440)
    render(
      <PerfilProvider>
        <ForcarSuperficieDeResultado />
        <SuperficieAtiva />
      </PerfilProvider>,
    )

    expect(
      await screen.findByRole('heading', { name: 'Resultados da simulação' }),
    ).toBeInTheDocument()
    expect(getResultadosMock).toHaveBeenCalledWith('33333333-3333-4333-8333-333333333333')
  })

  it('navega para "Comunicações" e monta SuperficieLinhaDoTempo', async () => {
    definirLargura(1440)
    const usuario = userEvent.setup()
    render(<App />)

    await usuario.click(screen.getByRole('button', { name: 'Comunicações' }))

    expect(
      await screen.findByRole('heading', { name: 'Linha do tempo ponta a ponta' }),
    ).toBeInTheDocument()
    expect(buscarExecucoesMock).toHaveBeenCalled()
  })
})
