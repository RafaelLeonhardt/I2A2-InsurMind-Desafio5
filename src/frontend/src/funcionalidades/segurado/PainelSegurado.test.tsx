import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { AlertaSegurado } from '../../api/alertaSegurado'
import type { ApoliceSegurado } from '../../api/apoliceSegurado'
import type { ItemAlerta } from '../../api/listaAlertasSegurado'
import type { ItemComunicado } from '../../api/listaComunicados'
import type { PreferenciasSegurado } from '../../api/preferenciasSegurado'
import { PainelSegurado } from './PainelSegurado'

const {
  getListaSeguradosMock,
  getAlertaMaisRelevanteMock,
  getListaAlertasMock,
  getApoliceMock,
  getListaComunicadosMock,
  getPreferenciasMock,
} = vi.hoisted(() => ({
  getListaSeguradosMock: vi.fn(),
  getAlertaMaisRelevanteMock: vi.fn(),
  getListaAlertasMock: vi.fn(),
  getApoliceMock: vi.fn(),
  getListaComunicadosMock: vi.fn(),
  getPreferenciasMock: vi.fn(),
}))

vi.mock('../../api/listaSegurados', async (importarOriginal) => {
  const original = await importarOriginal<typeof import('../../api/listaSegurados')>()
  return { ...original, getListaSegurados: getListaSeguradosMock }
})
vi.mock('../../api/alertaSegurado', async (importarOriginal) => {
  const original = await importarOriginal<typeof import('../../api/alertaSegurado')>()
  return { ...original, getAlertaMaisRelevante: getAlertaMaisRelevanteMock }
})
vi.mock('../../api/listaAlertasSegurado', async (importarOriginal) => {
  const original = await importarOriginal<typeof import('../../api/listaAlertasSegurado')>()
  return { ...original, getListaAlertas: getListaAlertasMock }
})
vi.mock('../../api/apoliceSegurado', async (importarOriginal) => {
  const original = await importarOriginal<typeof import('../../api/apoliceSegurado')>()
  return { ...original, getApolice: getApoliceMock }
})
vi.mock('../../api/listaComunicados', async (importarOriginal) => {
  const original = await importarOriginal<typeof import('../../api/listaComunicados')>()
  return { ...original, getListaComunicados: getListaComunicadosMock }
})
vi.mock('../../api/preferenciasSegurado', async (importarOriginal) => {
  const original = await importarOriginal<typeof import('../../api/preferenciasSegurado')>()
  return { ...original, getPreferencias: getPreferenciasMock }
})

const SEGURADO_A = { id: '11111111-1111-1111-1111-111111111111', nome: 'Pessoa Sintética DEMO-001' }
const SEGURADO_B = { id: '22222222-2222-2222-2222-222222222222', nome: 'Pessoa Sintética DEMO-002' }

function criarAlerta(localizacao: string): AlertaSegurado {
  return {
    elegibilidadeId: `elegibilidade-${localizacao}`,
    eventoTipo: 'chuva_intensa',
    severidade: 'Alta',
    periodoInicio: '2026-09-06T06:00:00Z',
    periodoFim: '2026-09-06T18:00:00Z',
    localizacao,
    impactosEsperados: ['Alagamento'],
    recomendacoes: ['Evite áreas baixas'],
    origem: 'sintetico',
    instanteObservado: '2026-09-06T05:00:00Z',
    fonteDegradada: false,
  }
}

function criarItemAlerta(localizacao: string): ItemAlerta {
  return { alerta: criarAlerta(localizacao), classificacao: 'ativo' }
}

function criarApolice(numero: string): ApoliceSegurado {
  return {
    numero,
    tipo: 'residencial',
    situacao: 'ativa',
    estadoObjetivo: 'vigente',
    vigenciaInicio: '2026-01-01',
    vigenciaFim: '2026-12-31',
    enderecoRiscoSintetico: 'Endereço sintético',
    coberturas: ['alagamento'],
    canalPreferido: 'whatsapp',
    participaDeAlertas: true,
  }
}

function criarComunicado(assunto: string): ItemComunicado {
  return {
    entregaSimuladaId: `entrega-${assunto}`,
    mensagemId: `mensagem-${assunto}`,
    canal: 'email',
    assuntoOuResumo: assunto,
    criadoEm: '2026-09-05T12:00:00Z',
    visualizacao: null,
  }
}

function criarPreferencias(seguradoId: string, participaDeAlertas: boolean): PreferenciasSegurado {
  return { seguradoId, canalPreferido: 'whatsapp', participaDeAlertas, versao: 1 }
}

function configurarDadosPorSegurado() {
  const dados = {
    [SEGURADO_A.id]: {
      alerta: criarAlerta('Área Demo A'),
      alertas: [criarItemAlerta('Área Demo A')],
      apolice: criarApolice('APOL-A'),
      comunicados: [criarComunicado('Assunto A')],
      preferencias: criarPreferencias(SEGURADO_A.id, true),
    },
    [SEGURADO_B.id]: {
      alerta: criarAlerta('Área Demo B'),
      alertas: [criarItemAlerta('Área Demo B')],
      apolice: criarApolice('APOL-B'),
      comunicados: [criarComunicado('Assunto B')],
      preferencias: criarPreferencias(SEGURADO_B.id, false),
    },
  } as const

  getListaSeguradosMock.mockResolvedValue([SEGURADO_A, SEGURADO_B])
  getAlertaMaisRelevanteMock.mockImplementation(
    async (id: string) => dados[id as keyof typeof dados].alerta,
  )
  getListaAlertasMock.mockImplementation(
    async (id: string) => dados[id as keyof typeof dados].alertas,
  )
  getApoliceMock.mockImplementation(async (id: string) => dados[id as keyof typeof dados].apolice)
  getListaComunicadosMock.mockImplementation(
    async (id: string) => dados[id as keyof typeof dados].comunicados,
  )
  getPreferenciasMock.mockImplementation(
    async (id: string) => dados[id as keyof typeof dados].preferencias,
  )
}

beforeEach(() => {
  window.localStorage.clear()
  vi.clearAllMocks()
})

afterEach(() => {
  window.localStorage.clear()
})

describe('PainelSegurado', () => {
  it('todas as cinco superfícies exibem dado do primeiro segurado sintético ao montar', async () => {
    configurarDadosPorSegurado()
    render(<PainelSegurado />)

    await waitFor(() => expect(screen.getAllByText('Área Demo A').length).toBeGreaterThan(0))
    expect(screen.getByText('APOL-A')).toBeInTheDocument()
    expect(screen.getByText('Assunto A')).toBeInTheDocument()
    expect(screen.getByRole('checkbox', { name: 'Participar de alertas' })).toBeChecked()
  })

  it('trocar de segurado atualiza as cinco superfícies em conjunto, sem mistura de dado', async () => {
    configurarDadosPorSegurado()
    const usuario = userEvent.setup()
    render(<PainelSegurado />)
    await waitFor(() => expect(screen.getAllByText('Área Demo A').length).toBeGreaterThan(0))

    // SeguradoContexto revalida a troca revalidando a lista (T3) — segura essa requisição em
    // voo para observar o estado intermediário antes de liberá-la.
    let liberarRevalidacao: (valor: (typeof SEGURADO_A)[]) => void = () => {}
    getListaSeguradosMock.mockReturnValueOnce(
      new Promise((resolver) => {
        liberarRevalidacao = resolver
      }),
    )

    const seletor = screen.getByRole('combobox', { name: 'Visualizar como' })
    await usuario.selectOptions(seletor, SEGURADO_B.id)

    // Enquanto a troca ainda não foi confirmada, nenhuma superfície já mudou para o segurado
    // B: a prop só muda depois que SeguradoContexto confirma a troca — nunca uma combinação
    // de A e B.
    expect(screen.queryByText('APOL-B')).not.toBeInTheDocument()
    expect(screen.getByText('APOL-A')).toBeInTheDocument()

    liberarRevalidacao([SEGURADO_A, SEGURADO_B])

    await waitFor(() => expect(screen.getAllByText('Área Demo B').length).toBeGreaterThan(0))
    expect(screen.getByText('APOL-B')).toBeInTheDocument()
    expect(screen.getByText('Assunto B')).toBeInTheDocument()
    expect(screen.getByRole('checkbox', { name: 'Participar de alertas' })).not.toBeChecked()

    // Nenhum dado do segurado A permanece em nenhuma superfície após a troca.
    expect(screen.queryByText('Área Demo A')).not.toBeInTheDocument()
    expect(screen.queryByText('APOL-A')).not.toBeInTheDocument()
    expect(screen.queryByText('Assunto A')).not.toBeInTheDocument()
  })

  it('exibe a seção de dúvidas frequentes independente do segurado ativo (6.9)', async () => {
    configurarDadosPorSegurado()
    render(<PainelSegurado />)
    await waitFor(() => expect(screen.getAllByText('Área Demo A').length).toBeGreaterThan(0))

    expect(screen.getByRole('heading', { name: 'Dúvidas frequentes' })).toBeInTheDocument()
    expect(screen.getByText('Como trocar o segurado simulado?')).toBeInTheDocument()
  })

  it('nenhuma das cinco superfícies expõe qualquer ação administrativa', async () => {
    configurarDadosPorSegurado()
    render(<PainelSegurado />)
    await waitFor(() => expect(screen.getAllByText('Área Demo A').length).toBeGreaterThan(0))

    const acoesProibidas = [/editar regra/i, /gerar mensagem/i, /aprovar lote/i, /iniciar simulação/i]
    const controlesAcionaveis = [
      ...screen.queryAllByRole('button'),
      ...screen.queryAllByRole('link'),
    ]
    for (const controle of controlesAcionaveis) {
      const nomeAcessivel = controle.textContent ?? ''
      for (const proibida of acoesProibidas) {
        expect(nomeAcessivel).not.toMatch(proibida)
      }
    }
  })
})
