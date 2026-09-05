import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { type DetalheResultado, ErroDetalheResultado } from '../../api/detalheResultado'
import { SuperficieDetalheResultado } from './SuperficieDetalheResultado'

const { getDetalheResultado } = vi.hoisted(() => ({
  getDetalheResultado: vi.fn(),
}))

vi.mock('../../api/detalheResultado', async (importarOriginal) => ({
  ...(await importarOriginal<typeof import('../../api/detalheResultado')>()),
  getDetalheResultado,
}))

const EXECUCAO_ID = '11111111-1111-1111-1111-111111111111'
const MENSAGEM_ID = '22222222-2222-2222-2222-222222222222'
const REGRA_ID = '33333333-3333-3333-3333-333333333333'

function detalhe(sobrescritas: Partial<DetalheResultado> = {}): DetalheResultado {
  return {
    mensagemId: MENSAGEM_ID,
    execucaoId: EXECUCAO_ID,
    canal: 'email',
    estado: 'simulada_entregue',
    limiteCanalCorpo: 2000,
    limiteCanalAssunto: 78,
    criadoEm: '2026-09-04T12:00:00Z',
    atualizadoEm: '2026-09-04T12:05:00Z',
    nomeSegurado: 'Marina Teste',
    apoliceId: '44444444-4444-4444-4444-444444444444',
    codigoIbgeArea: '9990001',
    evento: {
      id: '55555555-5555-5555-5555-555555555555',
      tipo: 'chuva_intensa',
      area: '9990001',
      intensidade: 62.5,
      proveniencia: 'real_inmet',
      periodoInicio: '2026-09-04T09:00:00Z',
      periodoFim: '2026-09-04T15:00:00Z',
    },
    regraId: REGRA_ID,
    regraVersao: 2,
    apresentacaoSimulada: {
      canal: 'email',
      assunto: 'Alerta preventivo',
      corpo: 'Chuva forte hoje na sua região.',
      rotulo: 'simulada',
    },
    versoes: [
      {
        numeroTentativa: 1,
        valida: true,
        motivoInvalidez: null,
        assunto: 'Alerta preventivo',
        corpo: 'Chuva forte hoje na sua região.',
        modelo: 'gpt-4o-mini',
        criadoEm: '2026-09-04T12:00:00Z',
        avaliacaoCritica: {
          aprovada: true,
          motivos: [],
          agente: 'critico',
          modelo: 'gpt-4o-mini',
          duracaoMs: 80,
          criadoEm: '2026-09-04T12:01:00Z',
        },
        decisoesHumanas: [
          {
            perfilResponsavel: 'administrador',
            resultado: 'aprovar',
            justificativa: null,
            criadoEm: '2026-09-04T12:02:00Z',
          },
        ],
      },
    ],
    excecao: null,
    ...sobrescritas,
  }
}

function renderizarComAcionador(propriedadesIniciais: Partial<Parameters<
  typeof SuperficieDetalheResultado
>[0]> = {}) {
  function Acionador() {
    const [aberto, definirAberto] = useState(false)
    return (
      <>
        <button onClick={() => definirAberto(true)} type="button">
          Abrir detalhe
        </button>
        <SuperficieDetalheResultado
          aberto={aberto}
          execucaoId={EXECUCAO_ID}
          mensagemId={MENSAGEM_ID}
          onFechar={() => definirAberto(false)}
          {...propriedadesIniciais}
        />
      </>
    )
  }
  return render(<Acionador />)
}

beforeEach(() => {
  vi.clearAllMocks()
  getDetalheResultado.mockResolvedValue(detalhe())
})

describe('prévia do canal', () => {
  it('mostra assunto e corpo de e-mail rotulados como simulação', async () => {
    renderizarComAcionador()
    await userEvent.click(screen.getByRole('button', { name: 'Abrir detalhe' }))

    expect(await screen.findByText('Alerta preventivo')).toBeInTheDocument()
    expect(screen.getByText('Chuva forte hoje na sua região.')).toBeInTheDocument()
    expect(
      screen.getByText('Prévia da simulação — nenhuma comunicação real foi enviada.'),
    ).toBeInTheDocument()
  })

  it('mostra corpo e limite do canal para WhatsApp/SMS, sem nenhum campo de telefone', async () => {
    getDetalheResultado.mockResolvedValue(
      detalhe({
        canal: 'sms',
        limiteCanalAssunto: null,
        limiteCanalCorpo: 160,
        apresentacaoSimulada: {
          canal: 'sms',
          assunto: null,
          corpo: 'Chuva forte hoje. Evite áreas alagadas.',
          rotulo: 'simulada',
        },
      }),
    )
    renderizarComAcionador()
    await userEvent.click(screen.getByRole('button', { name: 'Abrir detalhe' }))

    const dialogo = await screen.findByRole('dialog')
    expect(dialogo).toHaveTextContent('Chuva forte hoje. Evite áreas alagadas.')
    expect(dialogo).toHaveTextContent('160 caracteres')
    expect(dialogo.textContent?.toLowerCase()).not.toContain('telefone')
    expect(dialogo.textContent?.toLowerCase()).not.toContain('celular')
  })
})

describe('aprovações e versões', () => {
  it('mostra a aprovação agêntica e a decisão humana da versão final', async () => {
    renderizarComAcionador()
    await userEvent.click(screen.getByRole('button', { name: 'Abrir detalhe' }))

    const dialogo = await screen.findByRole('dialog')
    expect(dialogo).toHaveTextContent('Aprovada pelo agente crítico.')
    expect(dialogo).toHaveTextContent('aprovar por administrador.')
  })

  it('relaciona 3 versões (2 reprovadas + 1 aprovada) às suas críticas e decisões, em ordem', async () => {
    getDetalheResultado.mockResolvedValue(
      detalhe({
        versoes: [1, 2, 3].map((numero) => ({
          numeroTentativa: numero,
          valida: true,
          motivoInvalidez: null,
          assunto: null,
          corpo: `Tentativa ${numero}`,
          modelo: 'gpt-4o-mini',
          criadoEm: '2026-09-04T12:00:00Z',
          avaliacaoCritica: {
            aprovada: numero === 3,
            motivos: numero === 3 ? [] : ['tom'],
            agente: 'critico',
            modelo: 'gpt-4o-mini',
            duracaoMs: 80,
            criadoEm: '2026-09-04T12:01:00Z',
          },
          decisoesHumanas: [
            {
              perfilResponsavel: 'administrador',
              resultado: numero === 3 ? 'aprovar' : 'regenerar',
              justificativa: numero === 3 ? null : 'Tom alarmista.',
              criadoEm: '2026-09-04T12:02:00Z',
            },
          ],
        })),
      }),
    )
    renderizarComAcionador()
    await userEvent.click(screen.getByRole('button', { name: 'Abrir detalhe' }))

    const itensDeVersao = await screen.findAllByRole('listitem')
    const tentativas = itensDeVersao
      .filter((item) => item.dataset.tentativa)
      .map((item) => item.dataset.tentativa)
    expect(tentativas).toEqual(['1', '2', '3'])
  })
})

describe('não encontrado', () => {
  it('mostra o estado Não encontrado com uma ação segura de retorno', async () => {
    getDetalheResultado.mockRejectedValue(
      new ErroDetalheResultado({
        codigo: 'mensagem_nao_encontrada',
        correlacaoId: 'corr-1',
        ocorrencia: 'A mensagem não existe.',
        impacto: 'Nenhum detalhe pode ser exibido.',
        proximaAcao: 'Consulte outra mensagem.',
        status: 404,
      }),
    )
    renderizarComAcionador()
    await userEvent.click(screen.getByRole('button', { name: 'Abrir detalhe' }))

    const alerta = await screen.findByRole('alert')
    expect(alerta).toHaveTextContent('Não encontrado')
    expect(screen.getByRole('button', { name: 'Fechar' })).toBeInTheDocument()
  })
})

describe('acessibilidade: foco preso, Esc e empilhamento (DETALHE-06..08)', () => {
  it('prende o foco no drawer ao navegar com Tab e Shift+Tab', async () => {
    const usuario = userEvent.setup()
    renderizarComAcionador()
    await usuario.click(screen.getByRole('button', { name: 'Abrir detalhe' }))
    await screen.findByRole('dialog')

    const fechar = screen.getByRole('button', { name: 'Fechar' })
    expect(fechar).toHaveFocus()
    await usuario.tab()
    expect(fechar).toHaveFocus()
    await usuario.tab({ shift: true })
    expect(fechar).toHaveFocus()
  })

  it('fecha com Esc e devolve o foco ao elemento de origem', async () => {
    const usuario = userEvent.setup()
    renderizarComAcionador()
    const abrir = screen.getByRole('button', { name: 'Abrir detalhe' })

    await usuario.click(abrir)
    await screen.findByRole('dialog')
    await usuario.keyboard('{Escape}')

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(abrir).toHaveFocus()
  })

  it('nunca empilha uma segunda camada modal ao ser aberto de novo por outra origem', async () => {
    const usuario = userEvent.setup()

    function DuasOrigens() {
      const [aberto, definirAberto] = useState(false)
      return (
        <>
          <button onClick={() => definirAberto(true)} type="button">
            Origem A
          </button>
          <button onClick={() => definirAberto(true)} type="button">
            Origem B
          </button>
          <SuperficieDetalheResultado
            aberto={aberto}
            execucaoId={EXECUCAO_ID}
            mensagemId={MENSAGEM_ID}
            onFechar={() => definirAberto(false)}
          />
        </>
      )
    }
    render(<DuasOrigens />)

    await usuario.click(screen.getByRole('button', { name: 'Origem A' }))
    await screen.findByRole('dialog')
    await usuario.keyboard('{Escape}')
    await usuario.click(screen.getByRole('button', { name: 'Origem B' }))
    await screen.findByRole('dialog')

    expect(screen.getAllByRole('dialog')).toHaveLength(1)
  })

  it('não renderiza nada enquanto estiver fechado', () => {
    renderizarComAcionador()

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })
})
