import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ErroMeteorologia, type EventoMeteorologico } from '../../api/meteorologia'
import { PerfilProvider, usePerfilContexto } from '../../contexto/PerfilContexto'
import { SuperficieEventos } from './SuperficieEventos'

const { getEventosMock } = vi.hoisted(() => ({
  getEventosMock: vi.fn(),
}))

vi.mock('../../api/meteorologia', async (importarOriginal) => ({
  ...(await importarOriginal<typeof import('../../api/meteorologia')>()),
  getEventos: getEventosMock,
}))

function evento(sobrescritas: Partial<EventoMeteorologico> = {}): EventoMeteorologico {
  return {
    id: '11111111-1111-1111-1111-111111111111',
    tipo: 'chuva_intensa',
    area: '9990001',
    periodoInicio: '2026-08-30T17:00:00+00:00',
    periodoFim: '2026-08-30T18:00:00+00:00',
    intensidade: 55.4,
    proveniencia: 'real_inmet',
    instanteObservado: '2026-08-30T18:00:00+00:00',
    execucaoId: null,
    execucaoEstado: null,
    ...sobrescritas,
  }
}

/** Exibe a superfície ativa para confirmar a navegação disparada por `selecionarSuperficie`. */
function EspiaSuperficieAtiva() {
  const { superficieAtiva } = usePerfilContexto()
  return <p data-testid="superficie-ativa">{JSON.stringify(superficieAtiva)}</p>
}

function renderizar() {
  return render(
    <PerfilProvider>
      <SuperficieEventos />
      <EspiaSuperficieAtiva />
    </PerfilProvider>,
  )
}

afterEach(() => {
  vi.clearAllMocks()
})

describe('SuperficieEventos', () => {
  it('mostra o estado de carregamento antes da resposta da API', () => {
    getEventosMock.mockReturnValue(new Promise(() => {}))

    renderizar()

    expect(screen.getByRole('status')).toHaveTextContent('Carregando eventos climáticos')
  })

  it('lista um evento com execução associada e permite abrir a execução', async () => {
    const usuario = userEvent.setup()
    getEventosMock.mockResolvedValue([
      evento({
        execucaoId: '22222222-2222-2222-2222-222222222222',
        execucaoEstado: 'aguardando_geracao',
      }),
    ])

    renderizar()

    expect(await screen.findByText('Chuva intensa')).toBeInTheDocument()
    expect(screen.getByText('Em andamento')).toBeInTheDocument()
    const botao = screen.getByRole('button', { name: 'Ver execução' })

    await usuario.click(botao)

    await waitFor(() => {
      expect(screen.getByTestId('superficie-ativa')).toHaveTextContent(
        JSON.stringify({
          tipo: 'evento-execucao',
          execucaoId: '22222222-2222-2222-2222-222222222222',
          perfilPai: 'administrador',
        }),
      )
    })
  })

  it('mostra "Sem execução iniciada" e nenhuma ação para um evento sem execução associada', async () => {
    getEventosMock.mockResolvedValue([evento()])

    renderizar()

    expect(await screen.findByText('Sem execução iniciada')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Ver execução' })).not.toBeInTheDocument()
  })

  it('deriva a severidade em mm para chuva intensa e como ocorrência para granizo', async () => {
    getEventosMock.mockResolvedValue([
      evento({ id: '1', tipo: 'chuva_intensa', intensidade: 72.5 }),
      evento({ id: '2', tipo: 'granizo', intensidade: 1 }),
    ])

    renderizar()

    expect(await screen.findByText('72.5 mm')).toBeInTheDocument()
    expect(screen.getByText('Ocorrência de granizo')).toBeInTheDocument()
  })

  it('mostra "Concluída" para uma execução no estado terminal concluida', async () => {
    getEventosMock.mockResolvedValue([
      evento({ execucaoId: '22222222-2222-2222-2222-222222222222', execucaoEstado: 'concluida' }),
    ])

    renderizar()

    expect(await screen.findByText('Concluída')).toBeInTheDocument()
  })

  it('mostra "Com falha" para qualquer estado terminal falhou_*', async () => {
    getEventosMock.mockResolvedValue([
      evento({
        execucaoId: '22222222-2222-2222-2222-222222222222',
        execucaoEstado: 'falhou_preparacao_ia',
      }),
    ])

    renderizar()

    expect(await screen.findByText('Com falha')).toBeInTheDocument()
  })

  it('mostra o estado vazio explícito quando não houver nenhum evento', async () => {
    getEventosMock.mockResolvedValue([])

    renderizar()

    expect(await screen.findByRole('heading', { name: 'Nenhum evento climático identificado' })).toBeInTheDocument()
  })

  it('mostra o estado de erro explícito com ação de tentar novamente quando getEventos rejeitar', async () => {
    getEventosMock.mockRejectedValue(
      new ErroMeteorologia({
        codigo: 'falha_de_rede',
        correlacaoId: null,
        ocorrencia: 'Ocorrência sintética.',
        impacto: 'Impacto sintético.',
        proximaAcao: 'Próxima ação sintética.',
        status: null,
      }),
    )

    renderizar()

    expect(
      await screen.findByRole('heading', { name: 'Não foi possível carregar os eventos climáticos' }),
    ).toBeInTheDocument()
    expect(screen.getByText('Ocorrência sintética.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Tentar novamente' })).toBeInTheDocument()
  })
})
