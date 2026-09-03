import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Execucao } from '../../api/execucao'
import { SuperficiePreparacaoIA } from './SuperficiePreparacaoIA'

const { getExecucao } = vi.hoisted(() => ({ getExecucao: vi.fn() }))
const { prepararExecucao, solicitarNovaTentativaIa } = vi.hoisted(() => ({
  prepararExecucao: vi.fn(),
  solicitarNovaTentativaIa: vi.fn(),
}))

vi.mock('../../api/execucao', async (importarOriginal) => ({
  ...(await importarOriginal<typeof import('../../api/execucao')>()),
  getExecucao,
}))

vi.mock('../../api/preparacaoIa', async (importarOriginal) => ({
  ...(await importarOriginal<typeof import('../../api/preparacaoIa')>()),
  prepararExecucao,
  solicitarNovaTentativaIa,
}))

const EXECUCAO_ID = '11111111-1111-1111-1111-111111111111'
const ORIGEM_ID = '22222222-2222-2222-2222-222222222222'
const NOVA_ID = '33333333-3333-3333-3333-333333333333'

const CAUSA = 'A credencial da OpenAI foi recusada.'

function execucao(sobrescritas: Partial<Execucao>): Execucao {
  return {
    id: EXECUCAO_ID,
    estado: 'aguardando_geracao',
    marcos: [],
    publicoElegivelTotal: null,
    publicoElegivelPrevia: [],
    execucaoOrigemId: null,
    retentativas: [],
    ...sobrescritas,
  }
}

function execucaoBloqueada(sobrescritas: Partial<Execucao> = {}): Execucao {
  return execucao({
    estado: 'falhou_preparacao_ia',
    marcos: [
      { marco: 'falhou_preparacao_ia', causa: CAUSA, criadoEm: '2026-09-03T18:00:00Z' },
    ],
    ...sobrescritas,
  })
}

beforeEach(() => {
  getExecucao.mockReset()
  prepararExecucao.mockReset()
  solicitarNovaTentativaIa.mockReset()
})

describe('superfície de preparação da IA', () => {
  it('oferece preparar a produção quando a execução está aguardando geração', async () => {
    getExecucao.mockResolvedValue(execucao({ estado: 'aguardando_geracao' }))
    render(<SuperficiePreparacaoIA execucaoId={EXECUCAO_ID} />)

    expect(
      await screen.findByRole('button', { name: 'Preparar produção de mensagens' }),
    ).toBeInTheDocument()
  })

  it('confirma a integração e a passagem para a produção quando o preflight tem sucesso', async () => {
    getExecucao
      .mockResolvedValueOnce(execucao({ estado: 'aguardando_geracao' }))
      .mockResolvedValue(execucao({ estado: 'processando_mensagens' }))
    prepararExecucao.mockResolvedValue({
      execucaoId: EXECUCAO_ID,
      estado: 'processando_mensagens',
      contextosMontados: 3,
      itensEmExcecao: [],
      causa: null,
    })
    render(<SuperficiePreparacaoIA execucaoId={EXECUCAO_ID} />)

    await userEvent.click(
      await screen.findByRole('button', { name: 'Preparar produção de mensagens' }),
    )

    expect(prepararExecucao).toHaveBeenCalledWith(EXECUCAO_ID)
    const confirmacao = await screen.findByText(
      'Integração com a OpenAI confirmada. A execução seguiu para a produção de mensagens.',
    )
    expect(confirmacao.closest('[data-estado]')).toHaveAttribute(
      'data-estado',
      'processando_mensagens',
    )
  })

  it('explica o bloqueio com causa, impacto e a ação de nova tentativa', async () => {
    getExecucao.mockResolvedValue(execucaoBloqueada())
    render(<SuperficiePreparacaoIA execucaoId={EXECUCAO_ID} />)

    const bloqueio = await screen.findByRole('alert')

    expect(bloqueio).toHaveAttribute('data-estado', 'falhou_preparacao_ia')
    expect(bloqueio).toHaveTextContent('Produção de mensagens bloqueada')
    expect(bloqueio).toHaveTextContent(CAUSA)
    expect(bloqueio).toHaveTextContent('Nenhuma mensagem preventiva é gerada nesta execução.')
    expect(bloqueio).toHaveTextContent('solicite uma nova tentativa')
    expect(
      screen.getByRole('button', { name: 'Solicitar nova tentativa' }),
    ).toBeInTheDocument()
  })

  it('afirma explicitamente que nada foi gerado nem substituído', async () => {
    getExecucao.mockResolvedValue(execucaoBloqueada())
    render(<SuperficiePreparacaoIA execucaoId={EXECUCAO_ID} />)

    const bloqueio = await screen.findByRole('alert')

    expect(bloqueio).toHaveTextContent(
      'Nenhuma mensagem foi gerada e nada foi escrito no lugar dela',
    )
    expect(bloqueio).toHaveTextContent(
      'não substitui uma resposta indisponível da OpenAI por texto fixo, simulador de modelo ou outro provedor',
    )
  })

  it('não exibe nenhum conteúdo de mensagem quando a preparação está bloqueada', async () => {
    getExecucao.mockResolvedValue(execucaoBloqueada())
    render(<SuperficiePreparacaoIA execucaoId={EXECUCAO_ID} />)
    await screen.findByRole('alert')

    expect(
      screen.queryByRole('button', { name: 'Preparar produção de mensagens' }),
    ).not.toBeInTheDocument()
    expect(screen.queryByText(/Prezado|Comunicado preventivo|Olá,/)).not.toBeInTheDocument()
    expect(
      screen.queryByText(
        'Integração com a OpenAI confirmada. A execução seguiu para a produção de mensagens.',
      ),
    ).not.toBeInTheDocument()
  })

  it('usa a causa devolvida pelo preflight quando o bloqueio acaba de acontecer', async () => {
    getExecucao
      .mockResolvedValueOnce(execucao({ estado: 'aguardando_geracao' }))
      .mockResolvedValue(execucao({ estado: 'falhou_preparacao_ia', marcos: [] }))
    prepararExecucao.mockResolvedValue({
      execucaoId: EXECUCAO_ID,
      estado: 'falhou_preparacao_ia',
      contextosMontados: 0,
      itensEmExcecao: [],
      causa: 'Tempo limite excedido ao consultar a OpenAI.',
    })
    render(<SuperficiePreparacaoIA execucaoId={EXECUCAO_ID} />)

    await userEvent.click(
      await screen.findByRole('button', { name: 'Preparar produção de mensagens' }),
    )

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Tempo limite excedido ao consultar a OpenAI.',
    )
  })

  it('solicita a nova tentativa e informa que a execução atual segue encerrada', async () => {
    getExecucao
      .mockResolvedValueOnce(execucaoBloqueada())
      .mockResolvedValue(execucaoBloqueada({ retentativas: [NOVA_ID] }))
    solicitarNovaTentativaIa.mockResolvedValue({
      execucaoId: NOVA_ID,
      execucaoOrigemId: EXECUCAO_ID,
    })
    render(<SuperficiePreparacaoIA execucaoId={EXECUCAO_ID} />)

    await userEvent.click(
      await screen.findByRole('button', { name: 'Solicitar nova tentativa' }),
    )

    expect(solicitarNovaTentativaIa).toHaveBeenCalledWith(EXECUCAO_ID)
    expect(
      await screen.findByText(
        'Nova tentativa criada. Esta execução permanece encerrada, com o histórico preservado.',
      ),
    ).toBeInTheDocument()
  })

  it('navega da origem para cada nova tentativa criada a partir dela', async () => {
    const aoNavegar = vi.fn()
    getExecucao.mockResolvedValue(execucaoBloqueada({ retentativas: [NOVA_ID] }))
    render(<SuperficiePreparacaoIA aoNavegar={aoNavegar} execucaoId={EXECUCAO_ID} />)

    await userEvent.click(await screen.findByRole('button', { name: 'Ver nova tentativa 1' }))

    expect(aoNavegar).toHaveBeenCalledWith(NOVA_ID)
    expect(
      screen.queryByRole('button', { name: 'Ver execução de origem' }),
    ).not.toBeInTheDocument()
  })

  it('navega da execução correlacionada de volta para sua origem', async () => {
    const aoNavegar = vi.fn()
    getExecucao.mockResolvedValue(
      execucao({ estado: 'aguardando_geracao', execucaoOrigemId: ORIGEM_ID }),
    )
    render(<SuperficiePreparacaoIA aoNavegar={aoNavegar} execucaoId={EXECUCAO_ID} />)

    await userEvent.click(await screen.findByRole('button', { name: 'Ver execução de origem' }))

    expect(aoNavegar).toHaveBeenCalledWith(ORIGEM_ID)
  })

  it('explica a falha da nova tentativa sem prometer uma execução que não foi criada', async () => {
    getExecucao.mockResolvedValue(execucaoBloqueada())
    solicitarNovaTentativaIa.mockRejectedValue(
      new (await import('../../api/preparacaoIa')).ErroPreparacaoIa({
        codigo: 'snapshot_invalido',
        correlacaoId: null,
        ocorrencia: 'Os snapshots da execução não passaram na validação.',
        impacto: 'Nenhuma execução nova foi criada.',
        proximaAcao: 'Reinicie uma execução preventiva a partir da área monitorada.',
        status: 422,
      }),
    )
    render(<SuperficiePreparacaoIA execucaoId={EXECUCAO_ID} />)

    await userEvent.click(
      await screen.findByRole('button', { name: 'Solicitar nova tentativa' }),
    )

    expect(
      await screen.findByText('Os snapshots da execução não passaram na validação.'),
    ).toBeInTheDocument()
    expect(
      screen.queryByText(
        'Nova tentativa criada. Esta execução permanece encerrada, com o histórico preservado.',
      ),
    ).not.toBeInTheDocument()
  })
})
