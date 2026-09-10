import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ErroResultados, type ResultadosConsolidados } from '../../api/resultados'
import { SuperficieResultados } from './SuperficieResultados'

const { getResultados } = vi.hoisted(() => ({
  getResultados: vi.fn(),
}))

const { getDetalheResultado } = vi.hoisted(() => ({
  getDetalheResultado: vi.fn(),
}))

vi.mock('../../api/resultados', async (importarOriginal) => ({
  ...(await importarOriginal<typeof import('../../api/resultados')>()),
  getResultados,
}))

vi.mock('../../api/detalheResultado', async (importarOriginal) => ({
  ...(await importarOriginal<typeof import('../../api/detalheResultado')>()),
  getDetalheResultado,
}))

const EXECUCAO_ID = '11111111-1111-1111-1111-111111111111'

function resultados(sobrescritas: Partial<ResultadosConsolidados> = {}): ResultadosConsolidados {
  return {
    execucaoId: EXECUCAO_ID,
    estado: 'concluida',
    concluido: true,
    totaisPorCanal: [
      { chave: 'sms', total: 2 },
      { chave: 'email', total: 1 },
    ],
    totaisPorEstado: [
      { chave: 'simulada_entregue', total: 2 },
      { chave: 'rejeitada', total: 1 },
    ],
    naoSimulaveis: [
      {
        mensagemId: '22222222-2222-2222-2222-222222222222',
        canal: 'email',
        estado: 'rejeitada',
        motivo: 'rejeitada pela revisão humana',
      },
    ],
    divergencia: null,
    ...sobrescritas,
  }
}

function renderizar() {
  return render(<SuperficieResultados execucaoId={EXECUCAO_ID} />)
}

/** Lê a cor efetivamente aplicada ao selo de um estado. */
function corDe(elemento: Element | null): string {
  expect(elemento).not.toBeNull()
  const cor = (elemento as HTMLElement).style.getPropertyValue('--cor-estado').trim()
  expect(cor).not.toBe('')
  return cor
}

beforeEach(() => {
  vi.clearAllMocks()
  getResultados.mockResolvedValue(resultados())
  getDetalheResultado.mockResolvedValue({
    mensagemId: '22222222-2222-2222-2222-222222222222',
    execucaoId: EXECUCAO_ID,
    canal: 'email',
    estado: 'rejeitada',
    limiteCanalCorpo: 2000,
    limiteCanalAssunto: 78,
    criadoEm: '2026-09-04T12:00:00Z',
    atualizadoEm: '2026-09-04T12:05:00Z',
    nomeSegurado: 'Marina Teste',
    apoliceId: '44444444-4444-4444-4444-444444444444',
    codigoIbgeArea: '9990001',
    evento: null,
    regraId: '33333333-3333-3333-3333-333333333333',
    regraVersao: 2,
    apresentacaoSimulada: null,
    versoes: [],
    excecao: null,
  })
})

describe('totais por canal e por estado', () => {
  it('exibe "Enviada — simulação" por extenso para mensagens simuladas', async () => {
    renderizar()

    expect(await screen.findByText('Enviada — simulação')).toBeInTheDocument()
  })

  it('distingue "Enviada — simulação" de "Rejeitada" por texto, ícone e cor (L-024)', async () => {
    renderizar()

    const enviada = (await screen.findByText('Enviada — simulação')).closest(
      '[data-estado]',
    ) as HTMLElement
    const rejeitadas = screen.getAllByText('Rejeitada')
    const rejeitada = rejeitadas[0].closest('[data-estado]') as HTMLElement

    expect(enviada.dataset.estado).toBe('simulada_entregue')
    expect(rejeitada.dataset.estado).toBe('rejeitada')
    expect(corDe(enviada)).not.toBe(corDe(rejeitada))
    expect(enviada.querySelector('[data-icone-nome]')?.getAttribute('data-icone-nome')).not.toBe(
      rejeitada.querySelector('[data-icone-nome]')?.getAttribute('data-icone-nome'),
    )
  })

  it('soma dos totais por canal reconcilia com a quantidade do lote', async () => {
    renderizar()

    const tabela = await screen.findByRole('table', { name: /totais por canal/i })
    expect(tabela).toHaveTextContent('SMS')
    expect(tabela).toHaveTextContent('2')
    expect(tabela).toHaveTextContent('E-mail')
    expect(tabela).toHaveTextContent('1')
  })

  it('mostra as mensagens não simuladas separadas, com motivo', async () => {
    renderizar()

    const tabela = await screen.findByRole('table', { name: /mensagens não simuladas/i })
    expect(tabela).toHaveTextContent('rejeitada pela revisão humana')
  })
})

describe('acessibilidade da tabela: cabeçalhos e ordenação', () => {
  it('tem nomes acessíveis nos cabeçalhos e no controle de ordenação', async () => {
    renderizar()

    const tabelaEstado = await screen.findByRole('table', { name: /totais por estado/i })
    const cabecalhoEstado = within(tabelaEstado).getByRole('columnheader', { name: /estado/i })
    expect(cabecalhoEstado).toHaveAttribute('aria-sort', 'none')
    expect(
      within(tabelaEstado).getByRole('button', { name: 'Estado' }),
    ).toBeInTheDocument()
  })

  it('ordena de fato as linhas da tabela por estado ao ativar o cabeçalho de quantidade', async () => {
    const utilitario = userEvent.setup()
    renderizar()

    const tabelaEstado = await screen.findByRole('table', { name: /totais por estado/i })
    const botaoQuantidade = within(tabelaEstado).getByRole('button', { name: /quantidade/i })
    const cabecalho = within(tabelaEstado).getByRole('columnheader', { name: /quantidade/i })
    const linhasDeDados = () => within(tabelaEstado).getAllByRole('row').slice(1)

    // Dados: "Enviada — simulação" tem quantidade 2, "Rejeitada" tem quantidade 1.
    await utilitario.click(botaoQuantidade)
    expect(cabecalho).toHaveAttribute('aria-sort', 'ascending')
    let linhas = linhasDeDados()
    expect(linhas[0]).toHaveTextContent('Rejeitada')
    expect(linhas[1]).toHaveTextContent('Enviada — simulação')

    await utilitario.click(botaoQuantidade)
    expect(cabecalho).toHaveAttribute('aria-sort', 'descending')
    linhas = linhasDeDados()
    expect(linhas[0]).toHaveTextContent('Enviada — simulação')
    expect(linhas[1]).toHaveTextContent('Rejeitada')
  })

  it('permite alcançar e ativar o botão de ordenação só com o teclado', async () => {
    const utilitario = userEvent.setup()
    renderizar()
    await screen.findByRole('table', { name: /totais por canal/i })

    const botaoCanal = screen.getAllByRole('button', { name: /canal/i })[0]
    botaoCanal.focus()
    expect(botaoCanal).toHaveFocus()

    await utilitario.keyboard('{Enter}')

    const cabecalho = screen.getAllByRole('columnheader', { name: /canal/i })[0]
    expect(cabecalho).toHaveAttribute('aria-sort', 'ascending')
  })
})

describe('divergência consultável', () => {
  it('exibe a divergência com correlação e impacto, sem corrigir o total', async () => {
    getResultados.mockResolvedValue(
      resultados({
        divergencia: {
          execucaoId: EXECUCAO_ID,
          mensagensSimuladaEntregue: 2,
          entregasPersistidas: 1,
        },
      }),
    )
    renderizar()

    const alerta = await screen.findByRole('alert')
    expect(alerta).toHaveTextContent('Divergência detectada')
    expect(alerta).toHaveTextContent(EXECUCAO_ID)
    expect(alerta).toHaveTextContent('2')
    expect(alerta).toHaveTextContent('1')
    expect(alerta).toHaveTextContent(/nenhum valor foi corrigido/i)
  })

  it('não exibe nenhum alerta de divergência quando ela é nula', async () => {
    renderizar()
    await screen.findByRole('table', { name: /totais por canal/i })

    expect(screen.queryByText(/Divergência detectada/i)).not.toBeInTheDocument()
  })
})

describe('execução ainda não concluída', () => {
  it('mostra o progresso real, nunca um total parcial como final', async () => {
    getResultados.mockResolvedValue(
      resultados({
        estado: 'simulando',
        concluido: false,
        totaisPorCanal: [],
        totaisPorEstado: [],
        naoSimulaveis: [],
      }),
    )
    renderizar()

    expect(await screen.findByText(/ainda está em/i)).toHaveTextContent('simulando')
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })
})

describe('falha na consulta', () => {
  it('exibe ocorrência, impacto e próxima ação quando a consulta falha', async () => {
    getResultados.mockRejectedValue(
      new ErroResultados({
        codigo: 'execucao_inexistente',
        correlacaoId: 'corr-1',
        ocorrencia: 'A execução não existe.',
        impacto: 'Nenhum resultado pode ser exibido.',
        proximaAcao: 'Consulte outra execução.',
        status: 404,
      }),
    )
    renderizar()

    const alerta = await screen.findByRole('alert')
    expect(alerta).toHaveTextContent('A execução não existe.')
    expect(alerta).toHaveTextContent('Nenhum resultado pode ser exibido.')
    expect(alerta).toHaveTextContent('Consulte outra execução.')
  })
})

describe('resumo estatístico (PAINELRES-01)', () => {
  it('deriva total processado, entregue e com falha a partir de totaisPorEstado', async () => {
    getResultados.mockResolvedValue(
      resultados({
        totaisPorEstado: [
          { chave: 'simulada_entregue', total: 5 },
          { chave: 'aprovada', total: 1 },
          { chave: 'rejeitada', total: 2 },
          { chave: 'falhou_conteudo', total: 1 },
          { chave: 'falhou_integracao_ia', total: 1 },
        ],
      }),
    )
    renderizar()

    const resumo = (await screen.findByRole('heading', { name: 'Resumo' })).closest('section')
    expect(within(resumo as HTMLElement).getByText('Total processado').nextElementSibling).toHaveTextContent(
      '10',
    )
    expect(within(resumo as HTMLElement).getByText('Total entregue').nextElementSibling).toHaveTextContent(
      '5',
    )
    expect(within(resumo as HTMLElement).getByText('Total com falha').nextElementSibling).toHaveTextContent(
      '2',
    )
  })

  it('mostra 0 para entregue/com falha quando nenhum item está nesses estados', async () => {
    getResultados.mockResolvedValue(
      resultados({
        totaisPorEstado: [
          { chave: 'aprovada', total: 3 },
          { chave: 'excluida', total: 1 },
        ],
      }),
    )
    renderizar()

    const resumo = (await screen.findByRole('heading', { name: 'Resumo' })).closest('section')
    expect(within(resumo as HTMLElement).getByText('Total processado').nextElementSibling).toHaveTextContent(
      '4',
    )
    expect(within(resumo as HTMLElement).getByText('Total entregue').nextElementSibling).toHaveTextContent(
      '0',
    )
    expect(within(resumo as HTMLElement).getByText('Total com falha').nextElementSibling).toHaveTextContent(
      '0',
    )
  })
})

describe('filtro por canal/estado nas mensagens não simuladas (PAINELRES-02/03)', () => {
  function doisItens() {
    return resultados({
      naoSimulaveis: [
        {
          mensagemId: 'item-sms-rejeitada',
          canal: 'sms',
          estado: 'rejeitada',
          motivo: 'rejeitada pela revisão humana',
        },
        {
          mensagemId: 'item-email-falha',
          canal: 'email',
          estado: 'falhou_integracao_ia',
          motivo: 'falha de integração com a OpenAI',
        },
      ],
    })
  }

  it('filtra por canal, mostrando só os itens daquele canal', async () => {
    const utilitario = userEvent.setup()
    getResultados.mockResolvedValue(doisItens())
    renderizar()

    await screen.findByText('rejeitada pela revisão humana')
    await utilitario.selectOptions(screen.getByLabelText('Canal'), 'sms')

    expect(screen.getByText('rejeitada pela revisão humana')).toBeInTheDocument()
    expect(screen.queryByText('falha de integração com a OpenAI')).not.toBeInTheDocument()
  })

  it('filtra por estado, mostrando só os itens daquele estado', async () => {
    const utilitario = userEvent.setup()
    getResultados.mockResolvedValue(doisItens())
    renderizar()

    await screen.findByText('rejeitada pela revisão humana')
    await utilitario.selectOptions(screen.getByLabelText('Estado'), 'falhou_integracao_ia')

    expect(screen.queryByText('rejeitada pela revisão humana')).not.toBeInTheDocument()
    expect(screen.getByText('falha de integração com a OpenAI')).toBeInTheDocument()
  })

  it('a soma dos itens exibidos após o filtro nunca excede o total de itens não simulados', async () => {
    const utilitario = userEvent.setup()
    getResultados.mockResolvedValue(doisItens())
    renderizar()

    await screen.findByText('rejeitada pela revisão humana')
    await utilitario.selectOptions(screen.getByLabelText('Canal'), 'sms')

    const tabela = screen.getByRole('table', { name: /mensagens não simuladas/i })
    expect(within(tabela).getAllByRole('row')).toHaveLength(2) // cabeçalho + 1 item filtrado
  })

  it('limpar o filtro (Todos) mostra a lista completa de novo', async () => {
    const utilitario = userEvent.setup()
    getResultados.mockResolvedValue(doisItens())
    renderizar()

    await screen.findByText('rejeitada pela revisão humana')
    await utilitario.selectOptions(screen.getByLabelText('Canal'), 'sms')
    expect(screen.queryByText('falha de integração com a OpenAI')).not.toBeInTheDocument()

    await utilitario.selectOptions(screen.getByLabelText('Canal'), 'Todos')
    expect(screen.getByText('rejeitada pela revisão humana')).toBeInTheDocument()
    expect(screen.getByText('falha de integração com a OpenAI')).toBeInTheDocument()
  })

  it('combina canal e estado (interseção), não exibindo nada quando nenhum item satisfaz ambos', async () => {
    const utilitario = userEvent.setup()
    getResultados.mockResolvedValue(doisItens())
    renderizar()

    await screen.findByText('rejeitada pela revisão humana')
    await utilitario.selectOptions(screen.getByLabelText('Canal'), 'sms')
    await utilitario.selectOptions(screen.getByLabelText('Estado'), 'falhou_integracao_ia')

    expect(screen.queryByText('rejeitada pela revisão humana')).not.toBeInTheDocument()
    expect(screen.queryByText('falha de integração com a OpenAI')).not.toBeInTheDocument()
    expect(screen.getByText('Nenhuma mensagem corresponde ao filtro selecionado.')).toBeInTheDocument()
  })
})

describe('drill-down para SuperficieDetalheResultado (PAINELRES-04/05)', () => {
  it('clicar em "Ver detalhe" de uma linha abre o drawer com o mensagemId correto', async () => {
    const utilitario = userEvent.setup()
    getResultados.mockResolvedValue(
      resultados({
        naoSimulaveis: [
          {
            mensagemId: 'msg-alvo',
            canal: 'sms',
            estado: 'rejeitada',
            motivo: 'rejeitada pela revisão humana',
          },
        ],
      }),
    )
    renderizar()

    await screen.findByText('rejeitada pela revisão humana')
    await utilitario.click(screen.getByRole('button', { name: 'Ver detalhe' }))

    await screen.findByRole('dialog')
    expect(getDetalheResultado).toHaveBeenCalledWith(EXECUCAO_ID, 'msg-alvo')
  })

  it('fechar o drawer limpa mensagemAberta (drawer não fica mais presente)', async () => {
    const utilitario = userEvent.setup()
    getResultados.mockResolvedValue(
      resultados({
        naoSimulaveis: [
          {
            mensagemId: 'msg-alvo',
            canal: 'sms',
            estado: 'rejeitada',
            motivo: 'rejeitada pela revisão humana',
          },
        ],
      }),
    )
    renderizar()

    await screen.findByText('rejeitada pela revisão humana')
    await utilitario.click(screen.getByRole('button', { name: 'Ver detalhe' }))
    await screen.findByRole('dialog')

    await utilitario.keyboard('{Escape}')
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })
})

describe('exportação CSV do que está filtrado (PAINELRES-07)', () => {
  function doisItens() {
    return resultados({
      naoSimulaveis: [
        {
          mensagemId: 'item-sms-rejeitada',
          canal: 'sms',
          estado: 'rejeitada',
          motivo: 'rejeitada pela revisão humana',
        },
        {
          mensagemId: 'item-email-falha',
          canal: 'email',
          estado: 'falhou_integracao_ia',
          motivo: 'falha de integração com a OpenAI',
        },
      ],
    })
  }

  async function csvExportado(): Promise<string> {
    const chamada = (URL.createObjectURL as ReturnType<typeof vi.fn>).mock.calls[0]
    const blob = chamada[0] as Blob
    return blob.text()
  }

  beforeEach(() => {
    if (!('createObjectURL' in URL)) {
      Object.defineProperty(URL, 'createObjectURL', { configurable: true, value: () => '' })
    }
    if (!('revokeObjectURL' in URL)) {
      Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, value: () => {} })
    }
    vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:mock-url')
    vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {})
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('sem filtro ativo, exporta todos os itens de naoSimulaveis', async () => {
    const utilitario = userEvent.setup()
    getResultados.mockResolvedValue(doisItens())
    renderizar()

    await screen.findByText('rejeitada pela revisão humana')
    await utilitario.click(screen.getByRole('button', { name: 'Exportar CSV' }))

    const csv = await csvExportado()
    expect(csv).toContain('rejeitada pela revisão humana')
    expect(csv).toContain('falha de integração com a OpenAI')
  })

  it('com um filtro por estado ativo, exporta só os itens daquele estado', async () => {
    const utilitario = userEvent.setup()
    getResultados.mockResolvedValue(doisItens())
    renderizar()

    await screen.findByText('rejeitada pela revisão humana')
    await utilitario.selectOptions(screen.getByLabelText('Estado'), 'rejeitada')
    await utilitario.click(screen.getByRole('button', { name: 'Exportar CSV' }))

    const csv = await csvExportado()
    expect(csv).toContain('rejeitada pela revisão humana')
    expect(csv).not.toContain('falha de integração com a OpenAI')
  })
})
