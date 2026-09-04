import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ErroSimulacao, type ResumoSimulacao } from '../../api/simulacao'
import { SuperficieSimulacao } from './SuperficieSimulacao'

const { getResumoSimulacao, confirmarSimulacao, solicitarNovaTentativaSimulacao } = vi.hoisted(
  () => ({
    getResumoSimulacao: vi.fn(),
    confirmarSimulacao: vi.fn(),
    solicitarNovaTentativaSimulacao: vi.fn(),
  }),
)

vi.mock('../../api/simulacao', async (importarOriginal) => ({
  ...(await importarOriginal<typeof import('../../api/simulacao')>()),
  getResumoSimulacao,
  confirmarSimulacao,
  solicitarNovaTentativaSimulacao,
}))

const EXECUCAO_ID = '11111111-1111-1111-1111-111111111111'
const ORIGEM_ID = '99999999-9999-9999-9999-999999999999'
const RETENTATIVA_ID = '88888888-8888-8888-8888-888888888888'
const REGRA_ID = '77777777-7777-7777-7777-777777777777'
const CORPO_SMS = 'Chuva forte hoje na sua região. Evite áreas alagadas.'
const ASSUNTO_EMAIL = 'Aviso preventivo da sua seguradora'

function resumo(sobrescritas: Partial<ResumoSimulacao> = {}): ResumoSimulacao {
  return {
    execucaoId: EXECUCAO_ID,
    estado: 'aguardando_confirmacao',
    versao: 3,
    evento: {
      id: '66666666-6666-6666-6666-666666666666',
      tipo: 'chuva_intensa',
      area: '9990001',
      intensidade: 62.5,
      proveniencia: 'real_inmet',
      periodoInicio: '2026-09-04T12:00:00',
      periodoFim: '2026-09-04T18:00:00',
    },
    regraId: REGRA_ID,
    regraVersao: 2,
    totalDestinatarios: 5,
    distribuicaoPorCanal: [
      { canal: 'whatsapp', total: 1 },
      { canal: 'email', total: 2 },
      { canal: 'sms', total: 2 },
    ],
    entregas: [],
    execucaoOrigemId: null,
    retentativas: [],
    ...sobrescritas,
  }
}

function renderizar() {
  return render(<SuperficieSimulacao execucaoId={EXECUCAO_ID} />)
}

/** Lê a cor efetivamente aplicada ao selo de um estado de progresso. */
function corDe(elemento: Element | null): string {
  expect(elemento).not.toBeNull()
  const cor = (elemento as HTMLElement).style.getPropertyValue('--cor-progresso').trim()
  expect(cor).not.toBe('')
  return cor
}

async function abrirModal() {
  const utilitario = userEvent.setup()
  renderizar()
  await utilitario.click(await screen.findByRole('button', { name: 'Confirmar simulação' }))
  return utilitario
}

beforeEach(() => {
  vi.clearAllMocks()
  getResumoSimulacao.mockResolvedValue(resumo())
  confirmarSimulacao.mockResolvedValue({
    execucaoId: EXECUCAO_ID,
    estado: 'concluida',
    entregasCriadas: ['aaaa'],
    mensagensSimuladas: ['bbbb'],
  })
  solicitarNovaTentativaSimulacao.mockResolvedValue(RETENTATIVA_ID)
})

describe('confirmação com reconhecimento explícito', () => {
  it('mantém a ação principal bloqueada até o reconhecimento ser marcado', async () => {
    const utilitario = await abrirModal()
    const dialogo = screen.getByRole('dialog')
    const confirmar = within(dialogo).getByRole('button', { name: 'Confirmar simulação' })

    expect(confirmar).toBeDisabled()

    await utilitario.click(within(dialogo).getByRole('checkbox'))

    expect(confirmar).toBeEnabled()
  })

  it('informa explicitamente que nenhuma comunicação real será enviada', async () => {
    await abrirModal()
    const dialogo = screen.getByRole('dialog')

    expect(dialogo).toHaveTextContent(
      'Esta operação é uma simulação: nenhuma comunicação real é enviada aos segurados.',
    )
    expect(within(dialogo).getByRole('checkbox')).toHaveAccessibleName(
      /nenhuma comunicação real será enviada/,
    )
  })

  it('mostra evento, regra, período, destinatários e distribuição por canal no modal', async () => {
    await abrirModal()
    const dialogo = screen.getByRole('dialog')

    expect(dialogo).toHaveTextContent('chuva_intensa na área 9990001')
    expect(dialogo).toHaveTextContent(`${REGRA_ID} (versão 2)`)
    expect(dialogo).toHaveTextContent('2026-09-04T12:00:00 até 2026-09-04T18:00:00')
    expect(dialogo).toHaveTextContent('WhatsApp: 1, E-mail: 2, SMS: 2')
    expect(within(dialogo).getByText('Destinatários').nextElementSibling).toHaveTextContent('5')
  })

  it('separa os gates: a confirmação envia a versão do agregado, sem decidir conteúdo', async () => {
    const utilitario = await abrirModal()
    const dialogo = screen.getByRole('dialog')
    await utilitario.click(within(dialogo).getByRole('checkbox'))

    await utilitario.click(within(dialogo).getByRole('button', { name: 'Confirmar simulação' }))

    await waitFor(() => expect(confirmarSimulacao).toHaveBeenCalledWith(EXECUCAO_ID, 3))
    expect(getResumoSimulacao).toHaveBeenCalledTimes(2)
  })

  it('não oferece a confirmação enquanto o lote não chega ao gate da simulação', async () => {
    getResumoSimulacao.mockResolvedValue(resumo({ estado: 'aguardando_revisao' }))

    renderizar()

    expect(await screen.findByText('Bloqueada')).toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: 'Confirmar simulação' }),
    ).not.toBeInTheDocument()
    expect(confirmarSimulacao).not.toHaveBeenCalled()
  })
})

describe('progresso da simulação', () => {
  const casos: [string, string][] = [
    ['aguardando_revisao', 'Bloqueada'],
    ['aguardando_confirmacao', 'Pronta'],
    ['simulando', 'Simulando'],
    ['concluida', 'Concluída'],
    ['falhou_simulacao', 'Falha local'],
  ]

  it.each(casos)('exibe o estado %s como "%s"', async (estado, rotulo) => {
    getResumoSimulacao.mockResolvedValue(resumo({ estado }))

    renderizar()

    expect(await screen.findByText(rotulo)).toBeInTheDocument()
  })

  it('mantém os cinco estados distintos em texto, ícone e cor', async () => {
    const rotulos: string[] = []
    const icones: (string | null | undefined)[] = []
    const cores: string[] = []

    for (const [estado] of casos) {
      getResumoSimulacao.mockResolvedValue(resumo({ estado }))
      const { container, unmount } = renderizar()
      const selo = await waitFor(() => {
        const encontrado = container.querySelector('[data-progresso]')
        expect(encontrado).not.toBeNull()
        return encontrado as HTMLElement
      })
      rotulos.push(selo.querySelector('strong')?.textContent ?? '')
      icones.push(selo.querySelector('[data-icone-nome]')?.getAttribute('data-icone-nome'))
      cores.push(corDe(selo))
      unmount()
    }

    expect(rotulos).toEqual(['Bloqueada', 'Pronta', 'Simulando', 'Concluída', 'Falha local'])
    expect(new Set(icones).size).toBe(5)
    expect(new Set(cores).size).toBe(5)
  })

  it('mantém o caráter simulado visível durante e depois da operação', async () => {
    for (const estado of ['simulando', 'concluida']) {
      getResumoSimulacao.mockResolvedValue(resumo({ estado }))
      const { unmount } = renderizar()

      expect(
        await screen.findByText(
          'Esta operação é uma simulação: nenhuma comunicação real é enviada aos segurados.',
        ),
      ).toBeInTheDocument()
      unmount()
    }
  })
})

describe('resultado e retentativa', () => {
  it('mostra cada entrega rotulada como simulada, com a apresentação do canal', async () => {
    getResumoSimulacao.mockResolvedValue(
      resumo({
        estado: 'concluida',
        entregas: [
          {
            id: 'e1',
            mensagemId: 'm1',
            canal: 'sms',
            rotulo: 'simulada',
            assunto: null,
            corpo: CORPO_SMS,
            criadoEm: '2026-09-04T19:00:00',
          },
          {
            id: 'e2',
            mensagemId: 'm2',
            canal: 'email',
            rotulo: 'simulada',
            assunto: ASSUNTO_EMAIL,
            corpo: 'Prezada, previsão de chuva intensa na sua região.',
            criadoEm: '2026-09-04T19:00:01',
          },
        ],
      }),
    )

    const { container } = renderizar()

    const sms = await waitFor(() => {
      const encontrado = container.querySelector('[data-entrega="e1"]')
      expect(encontrado).not.toBeNull()
      return encontrado as HTMLElement
    })
    const email = container.querySelector('[data-entrega="e2"]') as HTMLElement
    expect(sms).toHaveTextContent('SMS — entrega simulada')
    expect(sms).toHaveTextContent(CORPO_SMS)
    expect(sms.querySelector('.simulacao__entrega-assunto')).toBeNull()
    expect(email).toHaveTextContent('E-mail — entrega simulada')
    expect(email).toHaveTextContent(`Assunto: ${ASSUNTO_EMAIL}`)
    expect(screen.getByText(/Nenhuma confirmação nem falha de provedor externo/)).toBeVisible()
  })

  it('solicita a nova tentativa a partir da falha local e navega para a execução criada', async () => {
    const utilitario = userEvent.setup()
    getResumoSimulacao.mockImplementation(async (execucaoId: string) =>
      execucaoId === EXECUCAO_ID
        ? resumo({ estado: 'falhou_simulacao' })
        : resumo({
            execucaoId: RETENTATIVA_ID,
            estado: 'aguardando_geracao',
            execucaoOrigemId: EXECUCAO_ID,
          }),
    )
    renderizar()

    await utilitario.click(
      await screen.findByRole('button', { name: /Solicitar nova tentativa de simulação/ }),
    )

    await waitFor(() =>
      expect(solicitarNovaTentativaSimulacao).toHaveBeenCalledWith(EXECUCAO_ID),
    )
    expect(await screen.findByText(RETENTATIVA_ID)).toBeInTheDocument()
    expect(await screen.findByText('Bloqueada')).toBeInTheDocument()
  })
})

describe('navegação entre execuções correlacionadas', () => {
  it('navega da retentativa para a origem sem mesclar os históricos', async () => {
    const utilitario = userEvent.setup()
    getResumoSimulacao.mockImplementation(async (execucaoId: string) =>
      execucaoId === EXECUCAO_ID
        ? resumo({ estado: 'aguardando_geracao', execucaoOrigemId: ORIGEM_ID })
        : resumo({
            execucaoId: ORIGEM_ID,
            estado: 'falhou_simulacao',
            execucaoOrigemId: null,
            retentativas: [EXECUCAO_ID],
          }),
    )
    renderizar()

    await utilitario.click(
      await screen.findByRole('button', { name: `Ver a execução de origem ${ORIGEM_ID}` }),
    )

    expect(await screen.findByText(ORIGEM_ID)).toBeInTheDocument()
    expect(screen.getByText('Falha local')).toBeInTheDocument()
    expect(screen.queryByText(EXECUCAO_ID)).not.toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: `Ver a nova tentativa ${EXECUCAO_ID}` }),
    ).toBeInTheDocument()
  })

  it('navega da origem para a retentativa, preservando o estado de cada uma', async () => {
    const utilitario = userEvent.setup()
    getResumoSimulacao.mockImplementation(async (execucaoId: string) =>
      execucaoId === EXECUCAO_ID
        ? resumo({ estado: 'falhou_simulacao', retentativas: [RETENTATIVA_ID] })
        : resumo({
            execucaoId: RETENTATIVA_ID,
            estado: 'aguardando_confirmacao',
            execucaoOrigemId: EXECUCAO_ID,
          }),
    )
    renderizar()

    await utilitario.click(
      await screen.findByRole('button', { name: `Ver a nova tentativa ${RETENTATIVA_ID}` }),
    )

    expect(await screen.findByText(RETENTATIVA_ID)).toBeInTheDocument()
    expect(screen.getByText('Pronta')).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: `Ver a execução de origem ${EXECUCAO_ID}` }),
    ).toBeInTheDocument()
  })
})

describe('falhas da consulta', () => {
  it('explica a falha com ocorrência, impacto e próxima ação', async () => {
    getResumoSimulacao.mockRejectedValue(
      new ErroSimulacao({
        codigo: 'execucao_inexistente',
        correlacaoId: 'abc',
        ocorrencia: `A execução '${EXECUCAO_ID}' não existe.`,
        impacto: 'Nenhuma simulação pode ser consultada nem confirmada.',
        proximaAcao: 'Consulte a execução pelo identificador UUID retornado pela API.',
        status: 404,
      }),
    )

    renderizar()

    const alerta = await screen.findByRole('alert')
    expect(alerta).toHaveTextContent(`A execução '${EXECUCAO_ID}' não existe.`)
    expect(alerta).toHaveTextContent('Nenhuma simulação pode ser consultada nem confirmada.')
    expect(alerta).toHaveTextContent(
      'Consulte a execução pelo identificador UUID retornado pela API.',
    )
  })
})
