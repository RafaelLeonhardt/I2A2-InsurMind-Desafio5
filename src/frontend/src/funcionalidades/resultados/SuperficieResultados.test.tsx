import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ErroResultados, type ResultadosConsolidados } from '../../api/resultados'
import { SuperficieResultados } from './SuperficieResultados'

const { getResultados } = vi.hoisted(() => ({
  getResultados: vi.fn(),
}))

vi.mock('../../api/resultados', async (importarOriginal) => ({
  ...(await importarOriginal<typeof import('../../api/resultados')>()),
  getResultados,
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

  it('ordena a tabela de totais por estado ao ativar o cabeçalho pelo teclado', async () => {
    const utilitario = userEvent.setup()
    renderizar()

    const botaoQuantidade = await screen.findAllByRole('button', { name: /quantidade/i })
    await utilitario.click(botaoQuantidade[1])

    const cabecalho = screen.getAllByRole('columnheader', { name: /quantidade/i })[1]
    expect(cabecalho).toHaveAttribute('aria-sort', 'ascending')

    await utilitario.click(botaoQuantidade[1])
    expect(cabecalho).toHaveAttribute('aria-sort', 'descending')
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
