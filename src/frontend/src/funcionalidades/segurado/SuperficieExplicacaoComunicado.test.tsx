import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  type ExplicacaoComunicado,
  ErroExplicacaoComunicado,
} from '../../api/explicacaoComunicado'
import { SuperficieExplicacaoComunicado } from './SuperficieExplicacaoComunicado'

const { getExplicacaoMock } = vi.hoisted(() => ({
  getExplicacaoMock: vi.fn(),
}))

vi.mock('../../api/explicacaoComunicado', async (importarOriginal) => ({
  ...(await importarOriginal<typeof import('../../api/explicacaoComunicado')>()),
  getExplicacaoComunicado: getExplicacaoMock,
}))

const SEGURADO_ID = '11111111-1111-1111-1111-111111111111'
const ENTREGA_ID = '22222222-2222-2222-2222-222222222222'

function explicacaoBase(
  sobrescritas: Partial<ExplicacaoComunicado> = {},
): ExplicacaoComunicado {
  return {
    entregaSimuladaId: ENTREGA_ID,
    mensagemId: '33333333-3333-3333-3333-333333333333',
    execucaoId: '44444444-4444-4444-4444-444444444444',
    execucaoOrigemId: null,
    eventoERegra: {
      origem: 'deterministica',
      evento: { id: '66666666-6666-6666-6666-666666666666', tipo: 'granizo', area: '9990001', proveniencia: 'sintetico' },
      regraId: '77777777-7777-7777-7777-777777777777',
      regraVersao: 5,
    },
    contexto: {
      categoriasUsadas: ['evento', 'canal'],
      categoriasNaoUsadas: ['documentos', 'dados_financeiros'],
    },
    agente: {
      origem: 'agente',
      status: 'completa',
      causaExcecao: null,
      tentativas: [
        {
          numeroTentativa: 1,
          origemRegeneracao: 'primeira_tentativa',
          corpo: 'Corpo gerado da mensagem.',
          assunto: null,
          modeloRedator: 'gpt-4o-mini',
          avaliacaoCritica: {
            aprovada: true,
            motivos: [],
            agente: 'critico',
            modelo: 'gpt-4o',
            duracaoMs: 80,
          },
          decisoesHumanas: [{ resultado: 'aprovar', justificativa: null }],
        },
      ],
    },
    apresentacaoSimulada: {
      canal: 'sms',
      assunto: null,
      corpo: 'Corpo final simulado da mensagem.',
      rotulo: 'simulada',
    },
    ...sobrescritas,
  }
}

beforeEach(() => {
  vi.resetAllMocks()
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('separação determinístico/IA (EXPLICACAO-01, 02)', () => {
  it('mostra evento/regra rotulados Determinístico e a tentativa rotulada IA', async () => {
    getExplicacaoMock.mockResolvedValue(explicacaoBase())

    render(
      <SuperficieExplicacaoComunicado
        aberto
        entregaSimuladaId={ENTREGA_ID}
        onFechar={() => {}}
        seguradoId={SEGURADO_ID}
      />,
    )

    await screen.findByText('Como esta mensagem foi criada')
    const secaoEvento = screen.getByRole('region', { name: 'Evento e regra aplicada' })
    expect(within(secaoEvento).getByText('Determinístico')).toBeInTheDocument()
    expect(within(secaoEvento).getByText(/granizo na área 9990001/)).toBeInTheDocument()

    const secaoAgente = screen.getByRole('region', { name: 'Como a mensagem foi gerada' })
    expect(within(secaoAgente).getByText('Inteligência artificial')).toBeInTheDocument()
    expect(within(secaoAgente).getByText(/Primeira tentativa/)).toBeInTheDocument()
    expect(within(secaoAgente).getByText(/aprovada pelo agente crítico/)).toBeInTheDocument()
    expect(within(secaoAgente).getByText(/Aprovação humana: aprovar/)).toBeInTheDocument()
  })

  it('distingue regeneração automática de regeneração solicitada por decisão humana', async () => {
    getExplicacaoMock.mockResolvedValue(
      explicacaoBase({
        agente: {
          origem: 'agente',
          status: 'completa',
          causaExcecao: null,
          tentativas: [
            {
              numeroTentativa: 1,
              origemRegeneracao: 'primeira_tentativa',
              corpo: 'Tentativa 1',
              assunto: null,
              modeloRedator: 'gpt-4o-mini',
              avaliacaoCritica: { aprovada: false, motivos: ['tom'], agente: 'critico', modelo: 'gpt-4o', duracaoMs: 50 },
              decisoesHumanas: [],
            },
            {
              numeroTentativa: 2,
              origemRegeneracao: 'automatica',
              corpo: 'Tentativa 2',
              assunto: null,
              modeloRedator: 'gpt-4o-mini',
              avaliacaoCritica: { aprovada: false, motivos: ['tom'], agente: 'critico', modelo: 'gpt-4o', duracaoMs: 55 },
              decisoesHumanas: [{ resultado: 'regenerar', justificativa: 'Ainda alarmista.' }],
            },
            {
              numeroTentativa: 3,
              origemRegeneracao: 'humana',
              corpo: 'Tentativa 3',
              assunto: null,
              modeloRedator: 'gpt-4o-mini',
              avaliacaoCritica: { aprovada: true, motivos: [], agente: 'critico', modelo: 'gpt-4o', duracaoMs: 60 },
              decisoesHumanas: [{ resultado: 'aprovar', justificativa: null }],
            },
          ],
        },
      }),
    )

    render(
      <SuperficieExplicacaoComunicado
        aberto
        entregaSimuladaId={ENTREGA_ID}
        onFechar={() => {}}
        seguradoId={SEGURADO_ID}
      />,
    )

    await screen.findByText('Como esta mensagem foi criada')
    expect(screen.getByText(/Nova tentativa automática, após reprovação/)).toBeInTheDocument()
    expect(screen.getByText(/Nova tentativa solicitada por decisão humana/)).toBeInTheDocument()
  })
})

describe('contexto minimizado (EXPLICACAO-03)', () => {
  it('mostra categorias usadas e não usadas distintas entre si', async () => {
    getExplicacaoMock.mockResolvedValue(explicacaoBase())

    render(
      <SuperficieExplicacaoComunicado
        aberto
        entregaSimuladaId={ENTREGA_ID}
        onFechar={() => {}}
        seguradoId={SEGURADO_ID}
      />,
    )

    const secaoContexto = await screen.findByRole('region', {
      name: 'Dados usados na sua mensagem',
    })
    expect(within(secaoContexto).getByText('evento, canal')).toBeInTheDocument()
    expect(within(secaoContexto).getByText('documentos, dados_financeiros')).toBeInTheDocument()
  })

  it('mostra Procedência parcial quando o contexto ainda não está disponível', async () => {
    getExplicacaoMock.mockResolvedValue(explicacaoBase({ contexto: null }))

    render(
      <SuperficieExplicacaoComunicado
        aberto
        entregaSimuladaId={ENTREGA_ID}
        onFechar={() => {}}
        seguradoId={SEGURADO_ID}
      />,
    )

    expect(await screen.findByText(/Procedência parcial/)).toBeInTheDocument()
  })
})

describe('procedência parcial e exceção da seção agêntica (EXPLICACAO-05)', () => {
  it('mostra Procedência parcial sem preencher a avaliação ausente', async () => {
    getExplicacaoMock.mockResolvedValue(
      explicacaoBase({
        agente: {
          origem: 'agente',
          status: 'parcial',
          causaExcecao: null,
          tentativas: [
            {
              numeroTentativa: 1,
              origemRegeneracao: 'primeira_tentativa',
              corpo: 'Tentativa 1',
              assunto: null,
              modeloRedator: 'gpt-4o-mini',
              avaliacaoCritica: null,
              decisoesHumanas: [],
            },
          ],
        },
      }),
    )

    render(
      <SuperficieExplicacaoComunicado
        aberto
        entregaSimuladaId={ENTREGA_ID}
        onFechar={() => {}}
        seguradoId={SEGURADO_ID}
      />,
    )

    expect(await screen.findByText(/Procedência parcial/)).toBeInTheDocument()
    expect(screen.getByText(/ainda não avaliada/)).toBeInTheDocument()
  })

  it('mostra Exceção com a causa, sem seção de crítica vazia parecendo incompleta', async () => {
    getExplicacaoMock.mockResolvedValue(
      explicacaoBase({
        agente: {
          origem: 'agente',
          status: 'excecao',
          causaExcecao: 'falha_integracao_ia',
          tentativas: [],
        },
      }),
    )

    render(
      <SuperficieExplicacaoComunicado
        aberto
        entregaSimuladaId={ENTREGA_ID}
        onFechar={() => {}}
        seguradoId={SEGURADO_ID}
      />,
    )

    expect(await screen.findByText('Exceção registrada.')).toBeInTheDocument()
    expect(screen.getByText(/falha_integracao_ia/)).toBeInTheDocument()
    expect(screen.getByText('Nenhuma tentativa de geração registrada.')).toBeInTheDocument()
  })
})

describe('prévia fiel sem promessa oficial (EXPLICACAO-04)', () => {
  it('mostra a prévia com o aviso de privada, simulada e não oficial', async () => {
    getExplicacaoMock.mockResolvedValue(explicacaoBase())

    render(
      <SuperficieExplicacaoComunicado
        aberto
        entregaSimuladaId={ENTREGA_ID}
        onFechar={() => {}}
        seguradoId={SEGURADO_ID}
      />,
    )

    expect(
      await screen.findByText(/privada e simulada.*não constitui um alerta oficial/),
    ).toBeInTheDocument()
    expect(screen.getByText('Corpo final simulado da mensagem.')).toBeInTheDocument()
  })
})

describe('execução correlacionada (Edge Case)', () => {
  it('indica quando o comunicado pertence a uma execução correlacionada', async () => {
    getExplicacaoMock.mockResolvedValue(
      explicacaoBase({ execucaoOrigemId: '88888888-8888-8888-8888-888888888888' }),
    )

    render(
      <SuperficieExplicacaoComunicado
        aberto
        entregaSimuladaId={ENTREGA_ID}
        onFechar={() => {}}
        seguradoId={SEGURADO_ID}
      />,
    )

    expect(await screen.findByText(/nova tentativa, correlacionada/)).toBeInTheDocument()
  })

  it('não mostra a nota de correlação quando a execução não é uma retentativa', async () => {
    getExplicacaoMock.mockResolvedValue(explicacaoBase())

    render(
      <SuperficieExplicacaoComunicado
        aberto
        entregaSimuladaId={ENTREGA_ID}
        onFechar={() => {}}
        seguradoId={SEGURADO_ID}
      />,
    )

    await screen.findByText('Como esta mensagem foi criada')
    expect(screen.queryByText(/correlacionada/)).not.toBeInTheDocument()
  })
})

describe('Não encontrada e falha de consulta', () => {
  it('mostra Não encontrada quando o comunicado não existe ou não pertence ao segurado', async () => {
    getExplicacaoMock.mockRejectedValue(
      new ErroExplicacaoComunicado({
        codigo: 'explicacao_nao_encontrada',
        correlacaoId: null,
        ocorrencia: 'Este comunicado não existe.',
        impacto: 'Nenhuma explicação pode ser exibida.',
        proximaAcao: 'Consulte pelo identificador retornado pela API.',
        status: 404,
      }),
    )

    render(
      <SuperficieExplicacaoComunicado
        aberto
        entregaSimuladaId={ENTREGA_ID}
        onFechar={() => {}}
        seguradoId={SEGURADO_ID}
      />,
    )

    expect(await screen.findByText('Não encontrada')).toBeInTheDocument()
    expect(
      screen.getByText('Este comunicado não existe ou não pertence a você.'),
    ).toBeInTheDocument()
  })

  it('mostra ocorrência, impacto e próxima ação numa falha local', async () => {
    getExplicacaoMock.mockRejectedValue(
      new ErroExplicacaoComunicado({
        codigo: 'falha_de_rede',
        correlacaoId: null,
        ocorrencia: 'Não foi possível falar com o backend.',
        impacto: 'Nenhuma explicação pôde ser exibida.',
        proximaAcao: 'Tente novamente.',
        status: null,
      }),
    )

    render(
      <SuperficieExplicacaoComunicado
        aberto
        entregaSimuladaId={ENTREGA_ID}
        onFechar={() => {}}
        seguradoId={SEGURADO_ID}
      />,
    )

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Não foi possível falar com o backend.',
    )
  })
})

describe('navegação acessível do drawer (EXPLICACAO-06, 07)', () => {
  it('prende o foco: Tab no último elemento focável volta ao primeiro', async () => {
    getExplicacaoMock.mockResolvedValue(explicacaoBase())
    const usuario = userEvent.setup()

    render(
      <SuperficieExplicacaoComunicado
        aberto
        entregaSimuladaId={ENTREGA_ID}
        onFechar={() => {}}
        seguradoId={SEGURADO_ID}
      />,
    )

    await screen.findByText('Como esta mensagem foi criada')
    const botaoFechar = screen.getByRole('button', { name: 'Fechar' })
    botaoFechar.focus()
    expect(document.activeElement).toBe(botaoFechar)

    await usuario.tab()
    expect(document.activeElement).toBe(botaoFechar)
  })

  it('Esc fecha o drawer e devolve o foco à origem', async () => {
    getExplicacaoMock.mockResolvedValue(explicacaoBase())
    const aoFechar = vi.fn()

    const origem = document.createElement('button')
    origem.textContent = 'Abrir explicação'
    document.body.appendChild(origem)
    origem.focus()

    const { rerender } = render(
      <SuperficieExplicacaoComunicado
        aberto
        entregaSimuladaId={ENTREGA_ID}
        onFechar={aoFechar}
        seguradoId={SEGURADO_ID}
      />,
    )

    await screen.findByText('Como esta mensagem foi criada')
    const usuario = userEvent.setup()
    await usuario.keyboard('{Escape}')

    expect(aoFechar).toHaveBeenCalledTimes(1)

    rerender(
      <SuperficieExplicacaoComunicado
        aberto={false}
        entregaSimuladaId={ENTREGA_ID}
        onFechar={aoFechar}
        seguradoId={SEGURADO_ID}
      />,
    )
    expect(document.activeElement).toBe(origem)
    origem.remove()
  })

  it('mantém o título sempre visível, mesmo durante o carregamento', () => {
    getExplicacaoMock.mockReturnValue(new Promise(() => {}))

    render(
      <SuperficieExplicacaoComunicado
        aberto
        entregaSimuladaId={ENTREGA_ID}
        onFechar={() => {}}
        seguradoId={SEGURADO_ID}
      />,
    )

    expect(screen.getByText('Como esta mensagem foi criada')).toBeInTheDocument()
  })

  it('não renderiza nenhum elemento quando fechado', () => {
    getExplicacaoMock.mockResolvedValue(explicacaoBase())

    const { container } = render(
      <SuperficieExplicacaoComunicado
        aberto={false}
        entregaSimuladaId={ENTREGA_ID}
        onFechar={() => {}}
        seguradoId={SEGURADO_ID}
      />,
    )

    expect(container).toBeEmptyDOMElement()
    expect(screen.queryAllByRole('dialog')).toHaveLength(0)
  })
})
