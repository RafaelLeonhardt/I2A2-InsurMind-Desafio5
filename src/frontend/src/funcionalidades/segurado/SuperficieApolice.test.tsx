import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  type ApoliceSegurado,
  ErroApoliceSegurado,
  type ExplicacaoApolice,
} from '../../api/apoliceSegurado'
import { ErroContexto } from '../../api/contexto'
import { SuperficieApolice } from './SuperficieApolice'

const { getApoliceMock, getExplicacaoApoliceMock, getSeguradoPadraoMock } = vi.hoisted(() => ({
  getApoliceMock: vi.fn(),
  getExplicacaoApoliceMock: vi.fn(),
  getSeguradoPadraoMock: vi.fn(),
}))

vi.mock('../../api/apoliceSegurado', async (importarOriginal) => ({
  ...(await importarOriginal<typeof import('../../api/apoliceSegurado')>()),
  getApolice: getApoliceMock,
  getExplicacaoApolice: getExplicacaoApoliceMock,
}))

vi.mock('../../api/contexto', async (importarOriginal) => ({
  ...(await importarOriginal<typeof import('../../api/contexto')>()),
  getSeguradoPadrao: getSeguradoPadraoMock,
}))

const SEGURADO_ID = '11111111-1111-1111-1111-111111111111'
const OUTRO_SEGURADO_ID = '44444444-4444-4444-4444-444444444444'
const ELEGIBILIDADE_ID = '22222222-2222-2222-2222-222222222222'

function promessaControlada<T>() {
  let resolver: (valor: T) => void = () => {}
  const promessa = new Promise<T>((resolucao) => {
    resolver = resolucao
  })
  return { promessa, resolver }
}

function apoliceBase(sobrescritas: Partial<ApoliceSegurado> = {}): ApoliceSegurado {
  return {
    numero: 'RES-0001',
    tipo: 'residencial',
    situacao: 'ativa',
    estadoObjetivo: 'ativa',
    vigenciaInicio: '2026-01-01',
    vigenciaFim: '2030-12-31',
    enderecoRiscoSintetico: 'Rua Sintética, 123',
    coberturas: ['alagamento', 'vendaval'],
    canalPreferido: 'sms',
    participaDeAlertas: true,
    ...sobrescritas,
  }
}

function explicacaoBase(sobrescritas: Partial<ExplicacaoApolice> = {}): ExplicacaoApolice {
  return {
    elegibilidadeId: ELEGIBILIDADE_ID,
    criterios: [
      {
        operando: 'área afetada',
        valorObservado: '9990001',
        atende: true,
        justificativa: 'Área da apólice corresponde à área do evento.',
      },
      {
        operando: 'cobertura exigida',
        valorObservado: 'alagamento',
        atende: true,
        justificativa: 'Apólice possui a cobertura exigida (alagamento).',
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

describe('dados da apólice (APOLICE-01)', () => {
  it('mostra número, tipo, vigência, endereço, coberturas, canal e participação', async () => {
    getApoliceMock.mockResolvedValue(apoliceBase())

    render(<SuperficieApolice seguradoId={SEGURADO_ID} />)

    expect(await screen.findByText('RES-0001')).toBeInTheDocument()
    expect(screen.getByText('Residencial')).toBeInTheDocument()
    expect(screen.getByText('2026-01-01 a 2030-12-31')).toBeInTheDocument()
    expect(screen.getByText('Rua Sintética, 123')).toBeInTheDocument()
    expect(screen.getByText('alagamento')).toBeInTheDocument()
    expect(screen.getByText('vendaval')).toBeInTheDocument()
    expect(screen.getByText('SMS')).toBeInTheDocument()
    expect(screen.getByText('Participando')).toBeInTheDocument()
  })

  it('mostra "Não participando" quando o segurado não participa de alertas', async () => {
    getApoliceMock.mockResolvedValue(apoliceBase({ participaDeAlertas: false }))

    render(<SuperficieApolice seguradoId={SEGURADO_ID} />)

    expect(await screen.findByText('Não participando')).toBeInTheDocument()
    expect(screen.queryByText('Participando')).not.toBeInTheDocument()
  })

  it('mostra o aviso de que alterações afetam só decisões futuras (APOLICE-06)', async () => {
    getApoliceMock.mockResolvedValue(apoliceBase())

    render(<SuperficieApolice seguradoId={SEGURADO_ID} />)

    expect(
      await screen.findByText(/afetam apenas decisões futuras/),
    ).toBeInTheDocument()
  })
})

describe('estado objetivo sem falha técnica (APOLICE-03)', () => {
  it('mostra apólice cancelada como texto comum, sem role alert', async () => {
    getApoliceMock.mockResolvedValue(
      apoliceBase({ situacao: 'cancelada', estadoObjetivo: 'cancelada' }),
    )

    render(<SuperficieApolice seguradoId={SEGURADO_ID} />)

    expect(await screen.findByText('Cancelada')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('mostra apólice expirada distinta de cancelada/suspensa', async () => {
    getApoliceMock.mockResolvedValue(
      apoliceBase({ situacao: 'ativa', estadoObjetivo: 'expirada' }),
    )

    render(<SuperficieApolice seguradoId={SEGURADO_ID} />)

    expect(await screen.findByText('Expirada')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('mostra apólice suspensa como texto comum, sem role alert', async () => {
    getApoliceMock.mockResolvedValue(
      apoliceBase({ situacao: 'suspensa', estadoObjetivo: 'suspensa' }),
    )

    render(<SuperficieApolice seguradoId={SEGURADO_ID} />)

    expect(await screen.findByText('Suspensa')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })
})

describe('Não encontrada (APOLICE-04)', () => {
  it('mostra Não encontrada quando a apólice não existe ou não pertence ao segurado', async () => {
    getApoliceMock.mockRejectedValue(
      new ErroApoliceSegurado({
        codigo: 'apolice_nao_encontrada',
        correlacaoId: null,
        ocorrencia: 'Não existe apólice para este segurado.',
        impacto: 'Nenhum dado pode ser exibido.',
        proximaAcao: 'Consulte pelo identificador do segurado ativo.',
        status: 404,
      }),
    )

    render(<SuperficieApolice seguradoId={SEGURADO_ID} />)

    expect(await screen.findByRole('heading', { name: 'Não encontrada' })).toBeInTheDocument()
    expect(
      screen.getByText('Esta apólice não existe ou não pertence a você.'),
    ).toBeInTheDocument()
  })
})

describe('falha de consulta', () => {
  it('mostra ocorrência, impacto e próxima ação, com nova tentativa', async () => {
    getApoliceMock.mockRejectedValueOnce(
      new ErroApoliceSegurado({
        codigo: 'falha_local',
        correlacaoId: null,
        ocorrencia: 'Falha ao consultar a apólice.',
        impacto: 'A apólice pode estar desatualizada.',
        proximaAcao: 'Tente novamente.',
        status: 500,
      }),
    )
    render(<SuperficieApolice seguradoId={SEGURADO_ID} />)
    const alerta = await screen.findByRole('alert')
    expect(alerta).toHaveTextContent('Falha ao consultar a apólice.')

    getApoliceMock.mockResolvedValueOnce(apoliceBase())
    const usuario = userEvent.setup()
    await usuario.click(screen.getByRole('button', { name: 'Tentar novamente' }))

    expect(await screen.findByText('RES-0001')).toBeInTheDocument()
  })
})

describe('explicação de critérios (APOLICE-02)', () => {
  it('mostra a explicação com aviso de que não confirma cobertura, indenização ou sinistro', async () => {
    getApoliceMock.mockResolvedValue(apoliceBase())
    getExplicacaoApoliceMock.mockResolvedValue(explicacaoBase())

    render(
      <SuperficieApolice
        elegibilidadeIdExplicacao={ELEGIBILIDADE_ID}
        seguradoId={SEGURADO_ID}
      />,
    )

    expect(
      await screen.findByText(/não confirma cobertura, indenização nem decisão de sinistro/),
    ).toBeInTheDocument()
    expect(screen.getByText(/Área da apólice corresponde à área do evento\./)).toBeInTheDocument()
    expect(screen.getByText(/Apólice possui a cobertura exigida \(alagamento\)\./)).toBeInTheDocument()
  })

  it('destaca só a cobertura avaliada, sem listar as demais coberturas da apólice (Edge Case)', async () => {
    // A apólice tem duas coberturas ("alagamento", "vendaval"), mas o snapshot da
    // execução só avaliou "alagamento" - a seção de explicação nunca deve citar
    // "vendaval" como se também tivesse participado, mesmo que ele apareça em outra
    // parte da página (a lista de Coberturas da apólice em si).
    getApoliceMock.mockResolvedValue(apoliceBase())
    getExplicacaoApoliceMock.mockResolvedValue(explicacaoBase())

    render(
      <SuperficieApolice
        elegibilidadeIdExplicacao={ELEGIBILIDADE_ID}
        seguradoId={SEGURADO_ID}
      />,
    )

    const secaoExplicacao = await screen.findByRole('region', {
      name: 'Como sua apólice participou desta decisão',
    })
    expect(within(secaoExplicacao).getByText(/alagamento/)).toBeInTheDocument()
    expect(within(secaoExplicacao).queryByText(/vendaval/)).not.toBeInTheDocument()
  })

  it('não mostra nenhuma seção de explicação quando a prop não é informada', async () => {
    getApoliceMock.mockResolvedValue(apoliceBase())

    render(<SuperficieApolice seguradoId={SEGURADO_ID} />)

    await screen.findByText('RES-0001')
    expect(
      screen.queryByRole('heading', { name: 'Como sua apólice participou desta decisão' }),
    ).not.toBeInTheDocument()
    expect(getExplicacaoApoliceMock).not.toHaveBeenCalled()
  })

  it('mostra que a explicação não foi encontrada quando de outro segurado', async () => {
    getApoliceMock.mockResolvedValue(apoliceBase())
    getExplicacaoApoliceMock.mockRejectedValue(
      new ErroApoliceSegurado({
        codigo: 'explicacao_nao_encontrada',
        correlacaoId: null,
        ocorrencia: "A explicação 'x' não existe para este segurado.",
        impacto: 'Nenhuma explicação pode ser exibida.',
        proximaAcao: 'Consulte pelo identificador retornado pela API.',
        status: 404,
      }),
    )

    render(
      <SuperficieApolice
        elegibilidadeIdExplicacao={ELEGIBILIDADE_ID}
        seguradoId={SEGURADO_ID}
      />,
    )

    expect(
      await screen.findByText('Esta explicação não existe ou não pertence a você.'),
    ).toBeInTheDocument()
  })
})

describe('resolução do segurado ativo', () => {
  it('sem seguradoId informado, resolve o segurado padrão internamente', async () => {
    getApoliceMock.mockResolvedValue(apoliceBase())

    render(<SuperficieApolice />)

    await screen.findByText('RES-0001')
    expect(getSeguradoPadraoMock).toHaveBeenCalledTimes(1)
    expect(getApoliceMock).toHaveBeenCalledWith(SEGURADO_ID)
  })

  it('descarta uma resposta antiga que chega depois de uma troca de segurado mais recente', async () => {
    const antiga = promessaControlada<ApoliceSegurado>()
    getApoliceMock.mockReturnValueOnce(antiga.promessa)
    const { rerender } = render(<SuperficieApolice seguradoId={SEGURADO_ID} />)
    await screen.findByText('Carregando apólice…')

    const nova = promessaControlada<ApoliceSegurado>()
    getApoliceMock.mockReturnValueOnce(nova.promessa)
    rerender(<SuperficieApolice seguradoId={OUTRO_SEGURADO_ID} />)

    nova.resolver(apoliceBase({ numero: 'RES-NOVA' }))
    await screen.findByText('RES-NOVA')

    antiga.resolver(apoliceBase({ numero: 'RES-ANTIGA' }))

    // Aguarda um macrotask real para dar tempo da continuação assíncrona da resposta
    // obsoleta rodar e provar que o guard de token a descarta.
    await new Promise((resolucao) => setTimeout(resolucao, 50))
    expect(screen.queryByText('RES-ANTIGA')).not.toBeInTheDocument()
    expect(screen.getByText('RES-NOVA')).toBeInTheDocument()
  })

  it('mostra falha de contexto ao resolver o segurado padrão', async () => {
    getSeguradoPadraoMock.mockRejectedValue(
      new ErroContexto({
        codigo: 'falha_de_rede',
        correlacaoId: null,
        ocorrencia: 'Não foi possível falar com o backend.',
        impacto: 'Nenhum dado pôde ser exibido.',
        proximaAcao: 'Tente novamente.',
        status: null,
      }),
    )

    render(<SuperficieApolice />)

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Não foi possível falar com o backend.',
    )
  })
})
