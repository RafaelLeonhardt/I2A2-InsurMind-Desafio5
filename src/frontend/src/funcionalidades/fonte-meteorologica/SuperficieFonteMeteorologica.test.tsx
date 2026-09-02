import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type {
  EventoMeteorologico,
  HistoricoSincronizacoes,
  Sincronizacao,
} from '../../api/meteorologia'
import {
  calcularEstadoFonte,
  calcularIdade,
  SuperficieFonteMeteorologica,
} from './SuperficieFonteMeteorologica'

const { getEventos, getSincronizacoes, solicitarNovaTentativa, ativarCenarioSintetico } = vi.hoisted(
  () => ({
    getEventos: vi.fn(),
    getSincronizacoes: vi.fn(),
    solicitarNovaTentativa: vi.fn(),
    ativarCenarioSintetico: vi.fn(),
  }),
)

vi.mock('../../api/meteorologia', async (importarOriginal) => ({
  ...(await importarOriginal<typeof import('../../api/meteorologia')>()),
  getEventos,
  getSincronizacoes,
  solicitarNovaTentativa,
  ativarCenarioSintetico,
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

function sincronizacao(sobrescritas: Partial<Sincronizacao> = {}): Sincronizacao {
  return {
    id: 's1',
    requisicaoId: 'r1',
    areaMonitoradaId: 'a1',
    origem: 'manual',
    estado: 'concluido',
    registrosValidos: 1,
    motivoFalha: null,
    iniciadoEm: '2026-08-30T12:00:00+00:00',
    finalizadoEm: '2026-08-30T12:00:05+00:00',
    tentativas: [
      {
        numeroTentativa: 1,
        codigoResultado: 'sucesso',
        iniciadoEm: '2026-08-30T12:00:00+00:00',
        finalizadoEm: '2026-08-30T12:00:01+00:00',
      },
    ],
    limiteTentativas: 3,
    ...sobrescritas,
  }
}

function historicoComFalha(): HistoricoSincronizacoes {
  const falha = sincronizacao({
    id: 's2',
    requisicaoId: 'r2',
    origem: 'automatica',
    estado: 'falha',
    registrosValidos: 0,
    motivoFalha: 'campo_ausente',
    iniciadoEm: '2026-08-30T13:00:00+00:00',
    finalizadoEm: '2026-08-30T13:00:02+00:00',
    tentativas: [
      { numeroTentativa: 1, codigoResultado: 'timeout', iniciadoEm: 't1', finalizadoEm: 't1f' },
      { numeroTentativa: 2, codigoResultado: 'timeout', iniciadoEm: 't2', finalizadoEm: 't2f' },
      { numeroTentativa: 3, codigoResultado: 'timeout', iniciadoEm: 't3', finalizadoEm: 't3f' },
    ],
  })
  return {
    ultimaTentativa: falha,
    ultimaValida: null,
    proximaConsulta: '2026-08-30T13:15:00+00:00',
    resultadosAnteriores: [falha],
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
  const ok = sincronizacao()
  return {
    ultimaTentativa: ok,
    ultimaValida: ok,
    proximaConsulta: '2026-08-30T12:15:00+00:00',
    resultadosAnteriores: [ok],
  }
}

beforeEach(() => {
  getEventos.mockReset()
  getSincronizacoes.mockReset()
  solicitarNovaTentativa.mockReset()
  ativarCenarioSintetico.mockReset()
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
    expect(screen.getByText(/Manual — Concluído — 2026-08-30T12:00:00\+00:00/)).toBeInTheDocument()
    expect(screen.getByText('2026-08-30T12:00:05+00:00')).toBeInTheDocument()
    expect(screen.getByText('2026-08-30T12:15:00+00:00')).toBeInTheDocument()
    expect(screen.getByText(/Manual — Concluído — iniciado em 2026-08-30T12:00:00\+00:00/)).toBeInTheDocument()
  })

  it('exibe o estado Falha com o motivo, quando a última tentativa não foi concluída', async () => {
    getEventos.mockResolvedValue([])
    getSincronizacoes.mockResolvedValue(historicoComFalha())

    render(<SuperficieFonteMeteorologica />)

    await screen.findByText('Histórico de sincronização')
    expect(screen.getByText(/Automática — Falha — 2026-08-30T13:00:00\+00:00/)).toBeInTheDocument()
    expect(
      screen.getByText(/Automática — Falha — iniciado em 2026-08-30T13:00:00\+00:00 — motivo: campo_ausente/),
    ).toBeInTheDocument()
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

  it('mostra o estado Operacional e nenhuma ação quando nunca houve coleta', async () => {
    getEventos.mockResolvedValue([])
    getSincronizacoes.mockResolvedValue(historicoVazio())

    render(<SuperficieFonteMeteorologica />)

    expect(await screen.findByText('Operacional')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Solicitar nova tentativa' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Ativar cenário sintético' })).not.toBeInTheDocument()
  })

  it('mostra Indisponível com as duas ações seguras: nova tentativa e cenário sintético', async () => {
    getEventos.mockResolvedValue([])
    getSincronizacoes.mockResolvedValue(historicoComFalha())

    render(<SuperficieFonteMeteorologica />)

    expect(await screen.findByText('Indisponível')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Solicitar nova tentativa' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Ativar cenário sintético' })).toBeInTheDocument()
  })

  it('mostra Sintética com só a ação de nova tentativa, nunca a de ativar de novo', async () => {
    getEventos.mockResolvedValue([evento({ proveniencia: 'sintetico', tipo: 'granizo' })])
    getSincronizacoes.mockResolvedValue(historicoComSincronizacao())

    render(<SuperficieFonteMeteorologica />)

    expect(await screen.findByText('Sintética')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Solicitar nova tentativa' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Ativar cenário sintético' })).not.toBeInTheDocument()
  })

  it('mostra Degradada quando a última tentativa concluiu após mais de uma tentativa', async () => {
    getEventos.mockResolvedValue([evento()])
    const ok = sincronizacao({
      tentativas: [
        { numeroTentativa: 1, codigoResultado: 'timeout', iniciadoEm: 't1', finalizadoEm: 't1f' },
        { numeroTentativa: 2, codigoResultado: 'sucesso', iniciadoEm: 't2', finalizadoEm: 't2f' },
      ],
    })
    getSincronizacoes.mockResolvedValue({
      ultimaTentativa: ok,
      ultimaValida: ok,
      proximaConsulta: null,
      resultadosAnteriores: [ok],
    })

    render(<SuperficieFonteMeteorologica />)

    expect(await screen.findByText('Degradada')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Solicitar nova tentativa' })).not.toBeInTheDocument()
  })

  it('mostra Recuperada quando a última tentativa concluiu logo após uma que falhou', async () => {
    getEventos.mockResolvedValue([evento()])
    const ok = sincronizacao({ id: 's-nova' })
    const falhou = sincronizacao({ id: 's-antiga', estado: 'falha', motivoFalha: 'retentativas_esgotadas' })
    getSincronizacoes.mockResolvedValue({
      ultimaTentativa: ok,
      ultimaValida: ok,
      proximaConsulta: null,
      resultadosAnteriores: [ok, falhou],
    })

    render(<SuperficieFonteMeteorologica />)

    expect(await screen.findByText('Recuperada')).toBeInTheDocument()
  })

  it('mostra Em tentativa com a contagem atual, quando a sincronização ainda está coletando', async () => {
    getEventos.mockResolvedValue([])
    const emAndamento = sincronizacao({
      estado: 'coletando',
      finalizadoEm: null,
      tentativas: [
        { numeroTentativa: 1, codigoResultado: 'timeout', iniciadoEm: 't1', finalizadoEm: 't1f' },
      ],
    })
    getSincronizacoes.mockResolvedValue({
      ultimaTentativa: emAndamento,
      ultimaValida: null,
      proximaConsulta: null,
      resultadosAnteriores: [emAndamento],
    })

    render(<SuperficieFonteMeteorologica />)

    expect(await screen.findByText('Em tentativa')).toBeInTheDocument()
    expect(screen.getByText('Tentativa 2 de 3')).toBeInTheDocument()
  })

  it('solicitar nova tentativa chama a API com o id da última tentativa e atualiza a consulta', async () => {
    const usuario = userEvent.setup()
    getEventos.mockResolvedValue([])
    getSincronizacoes.mockResolvedValueOnce(historicoComFalha()).mockResolvedValue(historicoVazio())
    solicitarNovaTentativa.mockResolvedValue({
      id: 'nova',
      requisicaoId: 'r',
      estado: 'concluido',
      registrosValidos: 1,
      motivoFalha: null,
      aceitoEm: 'agora',
    })

    render(<SuperficieFonteMeteorologica />)
    await usuario.click(await screen.findByRole('button', { name: 'Solicitar nova tentativa' }))

    await waitFor(() => expect(solicitarNovaTentativa).toHaveBeenCalledWith('s2'))
    await waitFor(() => expect(getSincronizacoes).toHaveBeenCalledTimes(2))
  })

  it('ativar cenário sintético chama a API com o identificador e a área da última tentativa', async () => {
    const usuario = userEvent.setup()
    getEventos.mockResolvedValue([])
    getSincronizacoes.mockResolvedValue(historicoComFalha())
    ativarCenarioSintetico.mockResolvedValue({
      id: 'nova',
      requisicaoId: 'r',
      estado: 'concluido',
      registrosValidos: 1,
      motivoFalha: null,
      aceitoEm: 'agora',
    })

    render(<SuperficieFonteMeteorologica />)
    await usuario.click(await screen.findByRole('button', { name: 'Ativar cenário sintético' }))

    await waitFor(() =>
      expect(ativarCenarioSintetico).toHaveBeenCalledWith('granizo-demonstrativo', 'a1'),
    )
  })
})

describe('calcularEstadoFonte', () => {
  it('operacional quando nunca houve nenhuma coleta', () => {
    expect(calcularEstadoFonte(historicoVazio(), [])).toBe('operacional')
  })

  it('em_tentativa quando a última sincronização ainda está coletando', () => {
    const historico: HistoricoSincronizacoes = {
      ultimaTentativa: sincronizacao({ estado: 'coletando', finalizadoEm: null }),
      ultimaValida: null,
      proximaConsulta: null,
      resultadosAnteriores: [],
    }
    expect(calcularEstadoFonte(historico, [])).toBe('em_tentativa')
  })

  it('indisponivel quando a última sincronização esgotou as tentativas', () => {
    expect(calcularEstadoFonte(historicoComFalha(), [])).toBe('indisponivel')
  })

  it('sintetica quando o evento mais recente é sintético', () => {
    const historico = historicoComSincronizacao()
    expect(
      calcularEstadoFonte(historico, [evento({ proveniencia: 'sintetico', tipo: 'granizo' })]),
    ).toBe('sintetica')
  })

  it('recuperada quando a última sincronização concluiu logo após uma que falhou', () => {
    const ok = sincronizacao({ id: 's-nova' })
    const falhou = sincronizacao({ id: 's-antiga', estado: 'falha' })
    const historico: HistoricoSincronizacoes = {
      ultimaTentativa: ok,
      ultimaValida: ok,
      proximaConsulta: null,
      resultadosAnteriores: [ok, falhou],
    }
    expect(calcularEstadoFonte(historico, [evento()])).toBe('recuperada')
  })

  it('degradada quando a última sincronização concluiu após mais de uma tentativa', () => {
    const ok = sincronizacao({
      tentativas: [
        { numeroTentativa: 1, codigoResultado: 'timeout', iniciadoEm: 't1', finalizadoEm: 't1f' },
        { numeroTentativa: 2, codigoResultado: 'sucesso', iniciadoEm: 't2', finalizadoEm: 't2f' },
      ],
    })
    const historico: HistoricoSincronizacoes = {
      ultimaTentativa: ok,
      ultimaValida: ok,
      proximaConsulta: null,
      resultadosAnteriores: [ok],
    }
    expect(calcularEstadoFonte(historico, [evento()])).toBe('degradada')
  })

  it('precedência: recuperada vence degradada quando as duas condições valem ao mesmo tempo', () => {
    const ok = sincronizacao({
      id: 's-nova',
      tentativas: [
        { numeroTentativa: 1, codigoResultado: 'timeout', iniciadoEm: 't1', finalizadoEm: 't1f' },
        { numeroTentativa: 2, codigoResultado: 'sucesso', iniciadoEm: 't2', finalizadoEm: 't2f' },
      ],
    })
    const falhou = sincronizacao({ id: 's-antiga', estado: 'falha' })
    const historico: HistoricoSincronizacoes = {
      ultimaTentativa: ok,
      ultimaValida: ok,
      proximaConsulta: null,
      resultadosAnteriores: [ok, falhou],
    }
    expect(calcularEstadoFonte(historico, [evento()])).toBe('recuperada')
  })

  it('precedência: indisponivel vence sintetica quando a última tentativa falhou mesmo com evento sintético mais recente', () => {
    const falhou = sincronizacao({ estado: 'falha' })
    const historico: HistoricoSincronizacoes = {
      ultimaTentativa: falhou,
      ultimaValida: null,
      proximaConsulta: null,
      resultadosAnteriores: [falhou],
    }
    expect(
      calcularEstadoFonte(historico, [evento({ proveniencia: 'sintetico', tipo: 'granizo' })]),
    ).toBe('indisponivel')
  })

  it('operacional quando a última sincronização concluiu de primeira, sem histórico de falha', () => {
    expect(calcularEstadoFonte(historicoComSincronizacao(), [evento()])).toBe('operacional')
  })
})

describe('calcularIdade', () => {
  const agora = new Date('2026-08-30T18:30:00+00:00')

  it('mostra "agora mesmo" para um instante há menos de um minuto', () => {
    expect(calcularIdade('2026-08-30T18:29:30+00:00', agora)).toBe('agora mesmo')
  })

  it('mostra minutos para um instante há menos de uma hora', () => {
    expect(calcularIdade('2026-08-30T18:00:00+00:00', agora)).toBe('30 min atrás')
  })

  it('mostra horas para um instante há menos de um dia', () => {
    expect(calcularIdade('2026-08-30T12:30:00+00:00', agora)).toBe('6 h atrás')
  })

  it('mostra dias para um instante há um dia ou mais', () => {
    expect(calcularIdade('2026-08-28T18:30:00+00:00', agora)).toBe('2 d atrás')
  })
})

describe('superfície de fonte meteorológica — marcação de dados desatualizados e badge visual', () => {
  beforeEach(() => {
    getEventos.mockReset()
    getSincronizacoes.mockReset()
  })

  it('marca os eventos como desatualizados só no estado Indisponível', async () => {
    getEventos.mockResolvedValue([evento()])
    getSincronizacoes.mockResolvedValue(historicoComFalha())

    render(<SuperficieFonteMeteorologica />)

    expect(await screen.findByText(/Dados desatualizados/)).toBeInTheDocument()
  })

  it('não marca os eventos como desatualizados no estado Operacional', async () => {
    getEventos.mockResolvedValue([evento()])
    getSincronizacoes.mockResolvedValue(historicoComSincronizacao())

    render(<SuperficieFonteMeteorologica />)

    await screen.findByText('Operacional')
    expect(screen.queryByText(/Dados desatualizados/)).not.toBeInTheDocument()
  })

  it('exibe a idade calculada de cada evento ao lado do horário', async () => {
    const noventaMinutosAtras = new Date(Date.now() - 90 * 60_000).toISOString()
    getEventos.mockResolvedValue([evento({ instanteObservado: noventaMinutosAtras })])
    getSincronizacoes.mockResolvedValue(historicoVazio())

    render(<SuperficieFonteMeteorologica />)

    expect(await screen.findByText('1 h atrás')).toBeInTheDocument()
  })

  it('cada estado tem uma classe de badge e um ícone próprios (texto + ícone + cor)', async () => {
    getEventos.mockResolvedValue([])
    getSincronizacoes.mockResolvedValue(historicoComFalha())

    const { container } = render(<SuperficieFonteMeteorologica />)

    await screen.findByText('Indisponível')
    const badge = container.querySelector('[data-icone="indisponivel"]')
    expect(badge).toBeInTheDocument()
    expect(badge).toHaveClass('estado-fonte-badge--indisponivel')
    expect(badge?.querySelector('svg')).toBeInTheDocument()
  })

  it('não oferece nenhuma ação no estado Em tentativa', async () => {
    getEventos.mockResolvedValue([])
    const emAndamento = sincronizacao({ estado: 'coletando', finalizadoEm: null })
    getSincronizacoes.mockResolvedValue({
      ultimaTentativa: emAndamento,
      ultimaValida: null,
      proximaConsulta: null,
      resultadosAnteriores: [emAndamento],
    })

    render(<SuperficieFonteMeteorologica />)

    await screen.findByText('Em tentativa')
    expect(screen.queryByRole('button', { name: 'Solicitar nova tentativa' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Ativar cenário sintético' })).not.toBeInTheDocument()
  })

  it('não oferece nenhuma ação no estado Recuperada', async () => {
    getEventos.mockResolvedValue([evento()])
    const ok = sincronizacao({ id: 's-nova' })
    const falhou = sincronizacao({ id: 's-antiga', estado: 'falha' })
    getSincronizacoes.mockResolvedValue({
      ultimaTentativa: ok,
      ultimaValida: ok,
      proximaConsulta: null,
      resultadosAnteriores: [ok, falhou],
    })

    render(<SuperficieFonteMeteorologica />)

    await screen.findByText('Recuperada')
    expect(screen.queryByRole('button', { name: 'Solicitar nova tentativa' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Ativar cenário sintético' })).not.toBeInTheDocument()
  })
})
