import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { EventoMeteorologico, HistoricoSincronizacoes } from '../../api/meteorologia'
import { SuperficieFonteMeteorologica } from './SuperficieFonteMeteorologica'

const { getEventos, getSincronizacoes } = vi.hoisted(() => ({
  getEventos: vi.fn(),
  getSincronizacoes: vi.fn(),
}))

vi.mock('../../api/meteorologia', async (importarOriginal) => ({
  ...(await importarOriginal<typeof import('../../api/meteorologia')>()),
  getEventos,
  getSincronizacoes,
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
    ...sobrescritas,
  }
}

function historicoVazio(): HistoricoSincronizacoes {
  return {
    ultimaTentativa: null,
    ultimaValida: null,
    proximaConsulta: null,
    resultadosAnteriores: [],
  }
}

function historicoComSincronizacao(): HistoricoSincronizacoes {
  const sincronizacao = {
    id: 's1',
    requisicaoId: 'r1',
    origem: 'manual' as const,
    estado: 'concluido',
    registrosValidos: 1,
    motivoFalha: null,
    iniciadoEm: '2026-08-30T12:00:00+00:00',
    finalizadoEm: '2026-08-30T12:00:05+00:00',
  }
  return {
    ultimaTentativa: sincronizacao,
    ultimaValida: sincronizacao,
    proximaConsulta: '2026-08-30T12:15:00+00:00',
    resultadosAnteriores: [sincronizacao],
  }
}

beforeEach(() => {
  getEventos.mockReset()
  getSincronizacoes.mockReset()
})

describe('superfície de fonte meteorológica', () => {
  it('mostra o estado de carregamento até a primeira resposta real', () => {
    let resolverEventos: (valor: EventoMeteorologico[]) => void = () => {}
    getEventos.mockReturnValue(
      new Promise((resolve) => {
        resolverEventos = resolve
      }),
    )
    getSincronizacoes.mockResolvedValue(historicoVazio())

    render(<SuperficieFonteMeteorologica />)

    expect(screen.getByRole('status')).toHaveTextContent('Carregando eventos meteorológicos…')
    expect(screen.queryByRole('table')).not.toBeInTheDocument()

    resolverEventos([])
  })

  it('exibe tipo, local, período, intensidade, origem e horário de cada evento', async () => {
    getEventos.mockResolvedValue([evento()])
    getSincronizacoes.mockResolvedValue(historicoVazio())

    render(<SuperficieFonteMeteorologica />)

    await screen.findByRole('table')
    expect(screen.getByText('Chuva intensa')).toBeInTheDocument()
    expect(screen.getByText('9990001')).toBeInTheDocument()
    expect(screen.getByText(/2026-08-30T17:00:00\+00:00.*2026-08-30T18:00:00\+00:00/)).toBeInTheDocument()
    expect(screen.getByText('55.4')).toBeInTheDocument()
    expect(screen.getByText('INMET (real)')).toBeInTheDocument()
    expect(screen.getAllByText('2026-08-30T18:00:00+00:00')).not.toHaveLength(0)
  })

  it('oferece uma seleção de evento operável por teclado, equivalente à seleção do mapa', async () => {
    getEventos.mockResolvedValue([evento()])
    getSincronizacoes.mockResolvedValue(historicoVazio())
    const usuario = userEvent.setup()

    render(<SuperficieFonteMeteorologica />)

    const botaoSelecionar = await screen.findByRole('button', { name: 'Selecionar' })
    botaoSelecionar.focus()
    expect(botaoSelecionar).toHaveFocus()

    await usuario.keyboard('{Enter}')

    expect(await screen.findByRole('button', { name: 'Selecionado' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
    expect(screen.getByRole('row', { name: /Chuva intensa/ })).toHaveAttribute(
      'aria-selected',
      'true',
    )
  })

  it('exibe o histórico de sincronização: última tentativa, última válida, próxima consulta e resultados anteriores', async () => {
    getEventos.mockResolvedValue([])
    getSincronizacoes.mockResolvedValue(historicoComSincronizacao())

    render(<SuperficieFonteMeteorologica />)

    await screen.findByText('Histórico de sincronização')
    expect(screen.getByText(/Manual — concluido — 2026-08-30T12:00:00\+00:00/)).toBeInTheDocument()
    expect(screen.getByText('2026-08-30T12:00:05+00:00')).toBeInTheDocument()
    expect(screen.getByText('2026-08-30T12:15:00+00:00')).toBeInTheDocument()
    expect(screen.getByText(/Manual — concluido — iniciado em 2026-08-30T12:00:00\+00:00/)).toBeInTheDocument()
  })

  it('mostra Indisponível com ocorrência, impacto e próxima ação quando a consulta falha', async () => {
    getEventos.mockRejectedValue(new TypeError('Failed to fetch'))
    getSincronizacoes.mockResolvedValue(historicoVazio())

    render(<SuperficieFonteMeteorologica />)

    expect(await screen.findByRole('alert')).toHaveTextContent('Indisponível')
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })

  it('sem nenhum evento normalizado, mostra a lista vazia sem dado fixo', async () => {
    getEventos.mockResolvedValue([])
    getSincronizacoes.mockResolvedValue(historicoVazio())

    render(<SuperficieFonteMeteorologica />)

    expect(await screen.findByText('Nenhum evento meteorológico normalizado até o momento.')).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })
})
