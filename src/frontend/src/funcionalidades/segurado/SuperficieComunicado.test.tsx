import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { type Comunicado, ErroComunicado } from '../../api/comunicado'
import type { ExplicacaoComunicado } from '../../api/explicacaoComunicado'
import { SuperficieComunicado } from './SuperficieComunicado'

const { getComunicado, registrarVisualizacaoComunicado, getExplicacaoMock } = vi.hoisted(() => ({
  getComunicado: vi.fn(),
  registrarVisualizacaoComunicado: vi.fn(),
  getExplicacaoMock: vi.fn(),
}))

vi.mock('../../api/comunicado', async (importarOriginal) => ({
  ...(await importarOriginal<typeof import('../../api/comunicado')>()),
  getComunicado,
  registrarVisualizacaoComunicado,
}))

vi.mock('../../api/explicacaoComunicado', async (importarOriginal) => ({
  ...(await importarOriginal<typeof import('../../api/explicacaoComunicado')>()),
  getExplicacaoComunicado: getExplicacaoMock,
}))

const SEGURADO_ID = '11111111-1111-1111-1111-111111111111'
const OUTRO_SEGURADO_ID = '99999999-9999-9999-9999-999999999999'
const ENTREGA_ID = '22222222-2222-2222-2222-222222222222'

function explicacaoBase(): ExplicacaoComunicado {
  return {
    entregaSimuladaId: ENTREGA_ID,
    mensagemId: '33333333-3333-3333-3333-333333333333',
    execucaoId: '44444444-4444-4444-4444-444444444444',
    execucaoOrigemId: null,
    eventoERegra: { origem: 'deterministica', evento: null, regraId: 'regra-1', regraVersao: 1 },
    contexto: null,
    agente: { origem: 'agente', status: 'completa', causaExcecao: null, tentativas: [] },
    apresentacaoSimulada: null,
  }
}

function comunicado(sobrescritas: Partial<Comunicado> = {}): Comunicado {
  return {
    entregaSimuladaId: ENTREGA_ID,
    mensagemId: '33333333-3333-3333-3333-333333333333',
    canal: 'email',
    assunto: 'Alerta preventivo',
    corpo: 'Chuva forte hoje na sua região. Evite áreas alagadas.',
    rotulo: 'simulada',
    criadoEm: '2026-09-05T12:00:00Z',
    visualizacao: null,
    ...sobrescritas,
  }
}

function renderizar() {
  return render(
    <SuperficieComunicado entregaSimuladaId={ENTREGA_ID} seguradoId={SEGURADO_ID} />,
  )
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
  vi.clearAllMocks()
  registrarVisualizacaoComunicado.mockResolvedValue({
    id: '44444444-4444-4444-4444-444444444444',
    visualizadaEm: '2026-09-05T12:05:00Z',
  })
})

describe('gatilho de visualização (VISU-01)', () => {
  it('não dispara o POST de visualização enquanto o conteúdo ainda não renderizou', async () => {
    const controlada = promessaControlada<Comunicado>()
    getComunicado.mockReturnValue(controlada.promessa)
    renderizar()

    await screen.findByText('Carregando comunicado…')
    expect(registrarVisualizacaoComunicado).not.toHaveBeenCalled()

    controlada.resolver(comunicado())
    await screen.findByText(comunicado().corpo)

    expect(registrarVisualizacaoComunicado).toHaveBeenCalledWith(SEGURADO_ID, ENTREGA_ID)
  })

  it('não dispara uma segunda visualização quando o comunicado já chega com uma', async () => {
    getComunicado.mockResolvedValue(
      comunicado({
        visualizacao: { id: 'ja-visto', visualizadaEm: '2026-09-04T10:00:00Z' },
      }),
    )
    renderizar()

    await screen.findByText(/Visualizada no portal em 2026-09-04T10:00:00Z/)

    expect(registrarVisualizacaoComunicado).not.toHaveBeenCalled()
  })
})

describe('conteúdo apresentado (VISU-01/02)', () => {
  beforeEach(() => {
    getComunicado.mockResolvedValue(comunicado())
  })

  it('mostra assunto e corpo de e-mail, canal e rótulo de simulação', async () => {
    renderizar()

    expect(await screen.findByText('Alerta preventivo')).toBeInTheDocument()
    expect(screen.getByText(comunicado().corpo)).toBeInTheDocument()
    expect(screen.getByText(/E-mail/)).toBeInTheDocument()
    expect(screen.getByText(/Simulação/)).toBeInTheDocument()
    expect(
      screen.getByText('Comunicado simulado — nenhuma comunicação real foi enviada a você.'),
    ).toBeInTheDocument()
  })

  it('não apresenta nenhum elemento de ação administrativa', async () => {
    renderizar()
    await screen.findByText(comunicado().corpo)
    await screen.findByText(/Visualizada no portal/)

    const acoesProibidas = [/editar regra/i, /gerar mensagem/i, /aprovar lote/i, /iniciar simulação/i]
    for (const botao of screen.queryAllByRole('button')) {
      for (const proibida of acoesProibidas) {
        expect(botao.textContent ?? '').not.toMatch(proibida)
      }
    }
  })
})

describe('explicação da mensagem (6.8, ABRIREXP-04..07)', () => {
  beforeEach(() => {
    getComunicado.mockResolvedValue(comunicado())
    getExplicacaoMock.mockResolvedValue(explicacaoBase())
  })

  it('exibe a ação e abre o drawer com o seguradoId/entregaSimuladaId deste comunicado', async () => {
    const usuario = userEvent.setup()
    renderizar()
    await screen.findByText(comunicado().corpo)

    await usuario.click(screen.getByRole('button', { name: 'Ver como esta mensagem foi criada' }))

    expect(await screen.findByRole('dialog')).toBeInTheDocument()
    expect(getExplicacaoMock).toHaveBeenCalledWith(SEGURADO_ID, ENTREGA_ID)
  })

  it('fechar o drawer devolve o foco ao botão que o abriu', async () => {
    const usuario = userEvent.setup()
    renderizar()
    await screen.findByText(comunicado().corpo)
    const botaoAbrir = screen.getByRole('button', { name: 'Ver como esta mensagem foi criada' })

    await usuario.click(botaoAbrir)
    await screen.findByRole('dialog')
    await usuario.click(screen.getByRole('button', { name: 'Fechar' }))

    await waitFor(() => expect(botaoAbrir).toHaveFocus())
  })

  it('trocar de segurado ativo com o drawer aberto o fecha (Edge Case)', async () => {
    const usuario = userEvent.setup()
    const { rerender } = render(
      <SuperficieComunicado entregaSimuladaId={ENTREGA_ID} seguradoId={SEGURADO_ID} />,
    )
    await screen.findByText(comunicado().corpo)
    await usuario.click(screen.getByRole('button', { name: 'Ver como esta mensagem foi criada' }))
    await screen.findByRole('dialog')

    rerender(<SuperficieComunicado entregaSimuladaId={ENTREGA_ID} seguradoId={OUTRO_SEGURADO_ID} />)

    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
  })
})

describe('falha local ao registrar a visualização (VISU-06/07)', () => {
  it('mantém estado de erro visível e nunca mostra Visualizada no portal', async () => {
    getComunicado.mockResolvedValue(comunicado())
    registrarVisualizacaoComunicado.mockRejectedValue(
      new ErroComunicado({
        codigo: 'falha_local',
        correlacaoId: null,
        ocorrencia: 'Falha local ao registrar.',
        impacto: 'A visualização não foi confirmada.',
        proximaAcao: 'Tente novamente.',
        status: 500,
      }),
    )
    renderizar()

    const alerta = await screen.findByText('Não foi possível confirmar sua visualização.')
    expect(alerta).toBeInTheDocument()
    expect(screen.getByText('Não confirmada')).toBeInTheDocument()
    expect(screen.queryByText(/Visualizada no portal/)).not.toBeInTheDocument()
  })

  it('permite nova tentativa idempotente que confirma a visualização', async () => {
    const usuario = userEvent.setup()
    getComunicado.mockResolvedValue(comunicado())
    registrarVisualizacaoComunicado.mockRejectedValueOnce(
      new ErroComunicado({
        codigo: 'falha_local',
        correlacaoId: null,
        ocorrencia: 'Falha local ao registrar.',
        impacto: 'A visualização não foi confirmada.',
        proximaAcao: 'Tente novamente.',
        status: 500,
      }),
    )
    renderizar()
    await screen.findByText('Não confirmada')

    await usuario.click(screen.getByRole('button', { name: 'Tentar novamente' }))

    expect(await screen.findByText(/Visualizada no portal/)).toBeInTheDocument()
    expect(registrarVisualizacaoComunicado).toHaveBeenCalledTimes(2)
  })
})

describe('falha ao consultar o comunicado', () => {
  it('exibe ocorrência, impacto e próxima ação quando o GET falha', async () => {
    getComunicado.mockRejectedValue(
      new ErroComunicado({
        codigo: 'comunicado_nao_encontrado',
        correlacaoId: 'corr-1',
        ocorrencia: 'O comunicado não existe.',
        impacto: 'Nenhum comunicado pode ser exibido.',
        proximaAcao: 'Consulte outro comunicado.',
        status: 404,
      }),
    )
    renderizar()

    const alerta = await screen.findByRole('alert')
    expect(alerta).toHaveTextContent('O comunicado não existe.')
    expect(alerta).toHaveTextContent('Nenhum comunicado pode ser exibido.')
    expect(registrarVisualizacaoComunicado).not.toHaveBeenCalled()
  })
})
