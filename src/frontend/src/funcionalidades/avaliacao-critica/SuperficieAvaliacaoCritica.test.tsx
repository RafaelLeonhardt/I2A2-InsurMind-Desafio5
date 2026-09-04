import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { type AvaliacaoCritica, ErroAvaliacaoCritica } from '../../api/avaliacaoCritica'
import { SuperficieAvaliacaoCritica } from './SuperficieAvaliacaoCritica'

const { getAvaliacaoCritica } = vi.hoisted(() => ({
  getAvaliacaoCritica: vi.fn(),
}))

vi.mock('../../api/avaliacaoCritica', async (importarOriginal) => ({
  ...(await importarOriginal<typeof import('../../api/avaliacaoCritica')>()),
  getAvaliacaoCritica,
}))

const MENSAGEM_ID = '11111111-1111-1111-1111-111111111111'
const VERSAO_ID = '22222222-2222-2222-2222-222222222222'

const CRITERIOS = [
  'tom',
  'utilidade',
  'clareza',
  'seguranca',
  'promessa_indevida',
  'distincao_oficial',
  'adequacao_canal',
]

function avaliacao(sobrescritas: Partial<AvaliacaoCritica> = {}): AvaliacaoCritica {
  return {
    mensagemId: MENSAGEM_ID,
    versaoMensagemId: VERSAO_ID,
    numeroTentativa: 1,
    origem: 'agente_ia',
    criterios: CRITERIOS,
    aprovada: true,
    motivos: [],
    agente: 'critico',
    modelo: 'gpt-4o-mini',
    duracaoMs: 742.5,
    criadoEm: '2026-09-03T19:00:00Z',
    validacaoDeterministica: {
      origem: 'regras_deterministicas',
      valida: true,
      motivoInvalidez: null,
    },
    ...sobrescritas,
  }
}

/** Lê a cor efetivamente aplicada ao elemento de uma origem de decisão. */
function corDe(elemento: Element | null): string {
  expect(elemento).not.toBeNull()
  const cor = (elemento as HTMLElement).style.getPropertyValue('--cor-origem').trim()
  expect(cor).not.toBe('')
  return cor
}

function renderizar() {
  return render(<SuperficieAvaliacaoCritica mensagemId={MENSAGEM_ID} versaoId={VERSAO_ID} />)
}

beforeEach(() => {
  getAvaliacaoCritica.mockReset()
})

describe('superfície de detalhe da avaliação crítica', () => {
  it('exibe versão, tentativa, agente, modelo e duração da avaliação', async () => {
    getAvaliacaoCritica.mockResolvedValue(avaliacao({ numeroTentativa: 2, duracaoMs: 742.5 }))

    renderizar()

    expect(await screen.findByText(VERSAO_ID)).toBeInTheDocument()
    expect(getAvaliacaoCritica).toHaveBeenCalledWith(MENSAGEM_ID, VERSAO_ID)
    expect(screen.getByText('2ª tentativa')).toBeInTheDocument()
    expect(screen.getByText('critico')).toBeInTheDocument()
    expect(screen.getByText('gpt-4o-mini')).toBeInTheDocument()
    expect(screen.getByText('743 ms')).toBeInTheDocument()
  })

  it('exibe os sete critérios avaliados em linguagem acessível', async () => {
    getAvaliacaoCritica.mockResolvedValue(avaliacao())

    const { container } = renderizar()

    await screen.findByText('Critérios avaliados')
    const itens = Array.from(container.querySelectorAll('[data-criterio]'))
    expect(itens.map((item) => item.getAttribute('data-criterio'))).toEqual(CRITERIOS)
    expect(screen.getByText('Tom preventivo, não alarmista')).toBeInTheDocument()
    expect(screen.getByText('Utilidade da orientação')).toBeInTheDocument()
    expect(screen.getByText('Clareza do texto')).toBeInTheDocument()
    expect(screen.getByText('Segurança da orientação')).toBeInTheDocument()
    expect(screen.getByText('Ausência de promessa de cobertura')).toBeInTheDocument()
    expect(screen.getByText('Distinção de um alerta oficial')).toBeInTheDocument()
    expect(screen.getByText('Adequação ao canal')).toBeInTheDocument()
  })

  it('exibe cada motivo da reprovação com sua categoria e justificativa', async () => {
    getAvaliacaoCritica.mockResolvedValue(
      avaliacao({
        aprovada: false,
        motivos: [
          { categoria: 'tom', justificativa: 'O texto usa tom alarmista, não preventivo.' },
          {
            categoria: 'promessa_indevida',
            justificativa: 'Promete indenização integral.',
          },
        ],
      })
    )

    const { container } = renderizar()

    expect(await screen.findByText('Reprovada pelo agente de IA')).toBeInTheDocument()
    const motivos = Array.from(
      container.querySelectorAll('.avaliacao-critica__motivos [data-categoria]')
    )
    expect(motivos.map((item) => item.getAttribute('data-categoria'))).toEqual([
      'tom',
      'promessa_indevida',
    ])
    expect(motivos[0]).toHaveTextContent('Tom preventivo, não alarmista')
    expect(motivos[0]).toHaveTextContent('O texto usa tom alarmista, não preventivo.')
    expect(motivos[1]).toHaveTextContent('Ausência de promessa de cobertura')
    expect(motivos[1]).toHaveTextContent('Promete indenização integral.')
  })

  it('distingue a aprovação agêntica da decisão humana por rótulo, ícone e cor', async () => {
    getAvaliacaoCritica.mockResolvedValue(avaliacao({ aprovada: true }))

    const { container } = renderizar()

    await screen.findByText('Aprovada pelo agente de IA')
    const agente = container.querySelector('[data-origem="agente_ia"]')
    const humana = container.querySelector('[data-origem="decisao_humana"]')
    expect(agente).not.toBeNull()
    expect(humana).not.toBeNull()

    expect(agente).toHaveTextContent('Decisão do agente de IA')
    expect(agente).toHaveTextContent('Aprovada pelo agente de IA')
    expect(humana).toHaveTextContent('Decisão humana')
    expect(humana).toHaveTextContent('Ainda não tomada')
    expect(humana).not.toHaveTextContent('Aprovada pelo agente de IA')

    expect(agente?.querySelector('[data-icone-nome="robot"]')).not.toBeNull()
    expect(humana?.querySelector('[data-icone-nome="user"]')).not.toBeNull()

    expect(corDe(agente)).not.toBe(corDe(humana))
  })

  it('mantém as três origens de decisão distintas em texto, ícone e cor', async () => {
    getAvaliacaoCritica.mockResolvedValue(avaliacao())

    const { container } = renderizar()

    await screen.findByText('Aprovada pelo agente de IA')
    const origens = Array.from(container.querySelectorAll('[data-origem]'))
    expect(origens).toHaveLength(3)

    const textos = origens.map((item) => item.textContent)
    const icones = origens.map((item) =>
      item.querySelector('[data-icone-nome]')?.getAttribute('data-icone-nome')
    )
    const cores = origens.map((item) => corDe(item))

    expect(new Set(textos).size).toBe(3)
    expect(new Set(icones).size).toBe(3)
    expect(new Set(cores).size).toBe(3)
  })

  it('não esconde a validação determinística quando o agente aprova', async () => {
    getAvaliacaoCritica.mockResolvedValue(
      avaliacao({
        aprovada: true,
        validacaoDeterministica: {
          origem: 'regras_deterministicas',
          valida: false,
          motivoInvalidez: 'limite_excedido:corpo:161:160',
        },
      })
    )

    const { container } = renderizar()

    await screen.findByText('Aprovada pelo agente de IA')
    const regras = container.querySelector('[data-origem="regras_deterministicas"]')
    expect(regras).toHaveTextContent('Validação por regras fixas')
    expect(regras).toHaveTextContent('Reprovada pelas regras fixas')
    expect(regras).toHaveTextContent('limite_excedido:corpo:161:160')
    expect(regras?.querySelector('[data-icone-nome="ruler"]')).not.toBeNull()
  })

  it('mostra a aprovação sem motivos sem inventar motivo nenhum', async () => {
    getAvaliacaoCritica.mockResolvedValue(avaliacao({ aprovada: true, motivos: [] }))

    const { container } = renderizar()

    expect(
      await screen.findByText(
        'O agente de IA não registrou nenhum motivo de reprovação para esta versão.'
      )
    ).toBeInTheDocument()
    expect(container.querySelectorAll('.avaliacao-critica__motivos li')).toHaveLength(0)
  })

  it('deixa explícito que a aprovação é do agente e não de uma pessoa', async () => {
    getAvaliacaoCritica.mockResolvedValue(avaliacao({ aprovada: true }))

    renderizar()

    expect(
      await screen.findByText(
        'A aprovação acima é do agente de IA, não de uma pessoa. A revisão humana continua pendente e pode decidir de outra forma.'
      )
    ).toBeInTheDocument()
  })

  it('explica a falha da consulta com ocorrência, impacto e próxima ação', async () => {
    getAvaliacaoCritica.mockRejectedValue(
      new ErroAvaliacaoCritica({
        codigo: 'avaliacao_inexistente',
        correlacaoId: 'abc',
        ocorrencia: `A versão '${VERSAO_ID}' ainda não foi avaliada pelo agente crítico.`,
        impacto: 'Nenhum detalhe de avaliação pode ser exibido; a versão segue em avaliação.',
        proximaAcao: 'Acompanhe o progresso da execução e consulte de novo.',
        status: 404,
      })
    )

    renderizar()

    const alerta = await screen.findByRole('alert')
    expect(alerta).toHaveTextContent('ainda não foi avaliada pelo agente crítico.')
    expect(alerta).toHaveTextContent(
      'Nenhum detalhe de avaliação pode ser exibido; a versão segue em avaliação.'
    )
    expect(alerta).toHaveTextContent('Acompanhe o progresso da execução e consulte de novo.')
  })

  it('não expõe nenhuma ação de reavaliação: a superfície só lê', async () => {
    const api = await import('../../api/avaliacaoCritica')
    getAvaliacaoCritica.mockResolvedValue(avaliacao())

    renderizar()

    await screen.findByText('Aprovada pelo agente de IA')
    expect(screen.queryAllByRole('button')).toEqual([])
    expect(
      Object.entries(api).filter(
        ([nome]) => nome.startsWith('post') || nome.toLowerCase().includes('avaliar')
      )
    ).toEqual([])
  })
})
