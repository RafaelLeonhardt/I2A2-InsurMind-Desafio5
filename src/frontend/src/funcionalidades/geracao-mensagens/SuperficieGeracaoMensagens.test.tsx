import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as apiMensagens from '../../api/mensagens'
import { type Mensagem, ErroMensagens } from '../../api/mensagens'
import { SuperficieGeracaoMensagens } from './SuperficieGeracaoMensagens'

const { getMensagens } = vi.hoisted(() => ({
  getMensagens: vi.fn(),
}))

vi.mock('../../api/mensagens', async (importarOriginal) => ({
  ...(await importarOriginal<typeof import('../../api/mensagens')>()),
  getMensagens,
}))

const EXECUCAO_ID = '11111111-1111-1111-1111-111111111111'

function corDe(elemento: Element | null): string {
  return (elemento as HTMLElement).style.getPropertyValue('--cor-categoria').trim()
}

function mensagem(sobrescritas: Partial<Mensagem> = {}): Mensagem {
  return {
    id: crypto.randomUUID(),
    elegibilidadeId: crypto.randomUUID(),
    canal: 'sms',
    estado: 'criticando',
    tentativaAtual: 1,
    limiteTentativas: 3,
    versao: 2,
    versaoAtual: {
      numeroTentativa: 1,
      valida: true,
      motivoInvalidez: null,
      modelo: 'gpt-4o-mini',
      versaoPrompt: 'v1',
      duracaoMs: 742.5,
      tokensEntrada: 210,
      tokensSaida: 64,
      criadoEm: '2026-09-03T19:00:00Z',
    },
    ...sobrescritas,
  }
}

beforeEach(() => {
  getMensagens.mockReset()
})

describe('superfície de geração de mensagens', () => {
  it('reconstrói o progresso da API a cada montagem', async () => {
    getMensagens.mockResolvedValue([
      mensagem({ canal: 'sms', estado: 'criticando' }),
      mensagem({ canal: 'email', estado: 'gerando', versaoAtual: null }),
    ])

    render(<SuperficieGeracaoMensagens execucaoId={EXECUCAO_ID} />)

    expect(await screen.findByText('1 de 2 mensagens geradas')).toBeInTheDocument()
    expect(getMensagens).toHaveBeenCalledWith(EXECUCAO_ID)
    expect(screen.getByText('SMS')).toBeInTheDocument()
    expect(screen.getByText('E-mail')).toBeInTheDocument()
    expect(screen.getByText('Mensagem gerada — em avaliação')).toBeInTheDocument()
    expect(screen.getByText('Gerando mensagem…')).toBeInTheDocument()
  })

  it('distingue mensagem gerada de mensagem em geração por texto, ícone e categoria', async () => {
    getMensagens.mockResolvedValue([
      mensagem({ canal: 'whatsapp', estado: 'criticando' }),
      mensagem({ canal: 'sms', estado: 'gerando', versaoAtual: null }),
    ])

    render(<SuperficieGeracaoMensagens execucaoId={EXECUCAO_ID} />)

    const gerada = (await screen.findByText('Mensagem gerada — em avaliação')).closest('li')
    const gerando = screen.getByText('Gerando mensagem…').closest('li')
    expect(gerada).toHaveAttribute('data-categoria', 'gerada')
    expect(gerando).toHaveAttribute('data-categoria', 'gerando')
    expect(gerada?.querySelector('[data-icone-nome="check-circle"]')).not.toBeNull()
    expect(gerando?.querySelector('[data-icone-nome="circle-notch"]')).not.toBeNull()
    expect(gerada?.className).toContain('geracao-mensagens__item--gerada')
    expect(gerando?.className).toContain('geracao-mensagens__item--gerando')
  })

  it('mostra a saída recusada como aguardando nova tentativa, com o motivo persistido', async () => {
    getMensagens.mockResolvedValue([
      mensagem({
        canal: 'sms',
        estado: 'gerando',
        versaoAtual: {
          numeroTentativa: 1,
          valida: false,
          motivoInvalidez: 'limite_excedido:corpo:161:160',
          modelo: 'gpt-4o-mini',
          versaoPrompt: 'v1',
          duracaoMs: 120,
          tokensEntrada: null,
          tokensSaida: null,
          criadoEm: '2026-09-03T19:00:00Z',
        },
      }),
    ])

    render(<SuperficieGeracaoMensagens execucaoId={EXECUCAO_ID} />)

    const item = (await screen.findByText('Aguardando nova tentativa')).closest('li')
    expect(item).toHaveAttribute('data-categoria', 'nova-tentativa')
    expect(item?.querySelector('[data-icone-nome="hourglass"]')).not.toBeNull()
    expect(screen.getByText('limite_excedido:corpo:161:160')).toBeInTheDocument()
    expect(screen.getByText('0 de 1 mensagens geradas')).toBeInTheDocument()
  })

  it('mostra a falha de integração como exceção do item', async () => {
    getMensagens.mockResolvedValue([
      mensagem({ canal: 'email', estado: 'falhou_integracao_ia', versaoAtual: null }),
    ])

    render(<SuperficieGeracaoMensagens execucaoId={EXECUCAO_ID} />)

    const item = (await screen.findByText('Falha de integração com a OpenAI')).closest('li')
    expect(item).toHaveAttribute('data-categoria', 'excecao')
    expect(item?.querySelector('[data-icone-nome="warning"]')).not.toBeNull()
  })

  it('mostra ausência de mensagens sem inventar progresso', async () => {
    getMensagens.mockResolvedValue([])

    render(<SuperficieGeracaoMensagens execucaoId={EXECUCAO_ID} />)

    expect(await screen.findByText('Nenhuma mensagem registrada até o momento.')).toBeInTheDocument()
    expect(screen.getByText('0 de 0 mensagens geradas')).toBeInTheDocument()
  })

  it('não dispara nenhuma geração: a superfície só lê mensagens', async () => {
    getMensagens.mockResolvedValue([mensagem({ canal: 'sms', estado: 'criticando' })])

    render(<SuperficieGeracaoMensagens execucaoId={EXECUCAO_ID} />)
    await screen.findByText('1 de 1 mensagens geradas')
    await userEvent.click(screen.getByRole('button', { name: /atualizar progresso/i }))

    await waitFor(() => expect(getMensagens).toHaveBeenCalledTimes(2))
    expect(Object.keys(apiMensagens).filter((nome) => nome.startsWith('get'))).toEqual([
      'getMensagens',
    ])
    expect(
      Object.entries(apiMensagens).filter(
        ([nome]) => nome.includes('gerar') || nome.includes('Gerar') || nome.includes('post')
      )
    ).toEqual([])
  })

  it('remontar reconstrói o mesmo progresso, sem duplicar mensagem', async () => {
    const persistidas = [
      mensagem({ canal: 'sms', estado: 'criticando' }),
      mensagem({ canal: 'email', estado: 'criticando' }),
    ]
    getMensagens.mockResolvedValue(persistidas)

    const primeira = render(<SuperficieGeracaoMensagens execucaoId={EXECUCAO_ID} />)
    await screen.findByText('2 de 2 mensagens geradas')
    primeira.unmount()
    render(<SuperficieGeracaoMensagens execucaoId={EXECUCAO_ID} />)

    expect(await screen.findByText('2 de 2 mensagens geradas')).toBeInTheDocument()
    expect(screen.getAllByRole('listitem')).toHaveLength(2)
    expect(getMensagens).toHaveBeenCalledTimes(2)
  })

  it('explica a falha da consulta com ocorrência, impacto e próxima ação', async () => {
    getMensagens.mockRejectedValue(
      new ErroMensagens({
        codigo: 'execucao_inexistente',
        correlacaoId: 'abc',
        ocorrencia: "A execução '1' não existe.",
        impacto: 'Nenhuma mensagem pode ser exibida.',
        proximaAcao: 'Consulte a execução pelo identificador UUID retornado pela API.',
        status: 404,
      })
    )

    render(<SuperficieGeracaoMensagens execucaoId={EXECUCAO_ID} />)

    const alerta = await screen.findByRole('alert')
    expect(alerta).toHaveTextContent("A execução '1' não existe.")
    expect(alerta).toHaveTextContent('Nenhuma mensagem pode ser exibida.')
    expect(alerta).toHaveTextContent(
      'Consulte a execução pelo identificador UUID retornado pela API.'
    )
  })

  it('mostra a tentativa atual e o limite de cada item', async () => {
    getMensagens.mockResolvedValue([
      mensagem({ canal: 'sms', estado: 'criticando', tentativaAtual: 2, limiteTentativas: 3 }),
      mensagem({
        canal: 'email',
        estado: 'gerando',
        tentativaAtual: 3,
        limiteTentativas: 3,
        versaoAtual: null,
      }),
    ])

    render(<SuperficieGeracaoMensagens execucaoId={EXECUCAO_ID} />)

    expect(await screen.findByText('Tentativa 2 de 3')).toBeInTheDocument()
    expect(screen.getByText('Tentativa 3 de 3')).toBeInTheDocument()
  })

  it('distingue aprovação, reprovação de conteúdo e falha de integração por texto, ícone e cor', async () => {
    getMensagens.mockResolvedValue([
      mensagem({ canal: 'sms', estado: 'aguardando_revisao', tentativaAtual: 2 }),
      mensagem({ canal: 'email', estado: 'falhou_conteudo', tentativaAtual: 3 }),
      mensagem({ canal: 'whatsapp', estado: 'falhou_integracao_ia', versaoAtual: null }),
    ])

    render(<SuperficieGeracaoMensagens execucaoId={EXECUCAO_ID} />)

    const aprovada = (
      await screen.findByText('Aprovada pelo crítico — aguardando revisão')
    ).closest('li')
    const reprovada = screen.getByText('Reprovada em todas as tentativas').closest('li')
    const integracao = screen.getByText('Falha de integração com a OpenAI').closest('li')

    expect(aprovada).toHaveAttribute('data-categoria', 'aprovada')
    expect(reprovada).toHaveAttribute('data-categoria', 'reprovada')
    expect(integracao).toHaveAttribute('data-categoria', 'excecao')
    expect(aprovada?.querySelector('[data-icone-nome="thumbs-up"]')).not.toBeNull()
    expect(reprovada?.querySelector('[data-icone-nome="prohibit"]')).not.toBeNull()
    expect(integracao?.querySelector('[data-icone-nome="warning"]')).not.toBeNull()
    expect(new Set([corDe(aprovada), corDe(reprovada), corDe(integracao)]).size).toBe(3)
    expect(corDe(aprovada)).not.toBe('')
  })

  it('resume aprovações e exceções do lote', async () => {
    getMensagens.mockResolvedValue([
      mensagem({ canal: 'sms', estado: 'aguardando_revisao' }),
      mensagem({ canal: 'email', estado: 'falhou_conteudo' }),
      mensagem({ canal: 'whatsapp', estado: 'falhou_integracao_ia', versaoAtual: null }),
      mensagem({ canal: 'sms', estado: 'gerando', versaoAtual: null }),
    ])

    render(<SuperficieGeracaoMensagens execucaoId={EXECUCAO_ID} />)

    expect(await screen.findByText('1 aprovadas pelo crítico, 2 em exceção')).toBeInTheDocument()
    expect(screen.getByText('1 de 4 mensagens geradas')).toBeInTheDocument()
  })

  it('mantém o foco do teclado onde estava quando o estado dos itens muda', async () => {
    getMensagens.mockResolvedValueOnce([
      mensagem({ canal: 'sms', estado: 'gerando', tentativaAtual: 1, versaoAtual: null }),
    ])
    getMensagens.mockResolvedValueOnce([
      mensagem({ canal: 'sms', estado: 'aguardando_revisao', tentativaAtual: 2 }),
    ])

    render(<SuperficieGeracaoMensagens execucaoId={EXECUCAO_ID} />)
    await screen.findByText('Gerando mensagem…')
    const botao = screen.getByRole('button', { name: /atualizar progresso/i })
    botao.focus()
    const focadoAntes = document.activeElement

    botao.click()

    expect(await screen.findByText('Aprovada pelo crítico — aguardando revisão')).toBeInTheDocument()
    expect(document.activeElement).toBe(focadoAntes)
    expect(document.activeElement).toBe(botao)
  })

  it('não rouba o foco de um elemento fora da lista durante a atualização', async () => {
    getMensagens.mockResolvedValueOnce([
      mensagem({ canal: 'sms', estado: 'gerando', tentativaAtual: 1, versaoAtual: null }),
    ])
    getMensagens.mockResolvedValueOnce([
      mensagem({ canal: 'sms', estado: 'falhou_conteudo', tentativaAtual: 3 }),
    ])

    render(<SuperficieGeracaoMensagens execucaoId={EXECUCAO_ID} />)
    await screen.findByText('Gerando mensagem…')
    const principal = document.getElementById('conteudo-principal') as HTMLElement
    principal.focus()
    expect(document.activeElement).toBe(principal)

    screen.getByRole('button', { name: /atualizar progresso/i }).click()

    expect(await screen.findByText('Reprovada em todas as tentativas')).toBeInTheDocument()
    expect(document.activeElement).toBe(principal)
  })

  it('anuncia a mudança de estado por região viva, sem mover o foco', async () => {
    getMensagens.mockResolvedValue([mensagem({ canal: 'sms', estado: 'criticando' })])

    render(<SuperficieGeracaoMensagens execucaoId={EXECUCAO_ID} />)
    await screen.findByText('Mensagem gerada — em avaliação')

    const lista = screen.getByRole('list')
    expect(lista).toHaveAttribute('aria-live', 'polite')
    expect(document.activeElement).toBe(document.body)
  })
})
