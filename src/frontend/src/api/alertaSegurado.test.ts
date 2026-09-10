import { afterEach, describe, expect, it, vi } from 'vitest'
import { ErroAlertaSegurado, getAlertaMaisRelevante } from './alertaSegurado'

const SEGURADO_ID = '11111111-1111-1111-1111-111111111111'

function responder(status: number, corpo: unknown): Response {
  return new Response(JSON.stringify(corpo), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function alertaCorpo(sobrescritas: Record<string, unknown> = {}) {
  return {
    elegibilidade_id: '22222222-2222-2222-2222-222222222222',
    evento_tipo: 'chuva_intensa',
    severidade: 'Alta — 65mm/h observados.',
    periodo_inicio: '2026-09-06T06:00:00Z',
    periodo_fim: '2026-09-06T18:00:00Z',
    localizacao: '9990001',
    impactos_esperados: ['alagamento'],
    recomendacoes: ['Evite áreas baixas'],
    origem: 'real_inmet',
    instante_observado: '2026-09-06T05:00:00Z',
    fonte_degradada: false,
    entrega_simulada_id: '33333333-3333-3333-3333-333333333333',
    ...sobrescritas,
  }
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('getAlertaMaisRelevante', () => {
  it('mapeia todos os campos de snake_case para camelCase, com valores distintos entre si (6.8: entregaSimuladaId)', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(responder(200, { alerta: alertaCorpo() })),
    )

    const alerta = await getAlertaMaisRelevante(SEGURADO_ID)

    expect(alerta).toEqual({
      elegibilidadeId: '22222222-2222-2222-2222-222222222222',
      eventoTipo: 'chuva_intensa',
      severidade: 'Alta — 65mm/h observados.',
      periodoInicio: '2026-09-06T06:00:00Z',
      periodoFim: '2026-09-06T18:00:00Z',
      localizacao: '9990001',
      impactosEsperados: ['alagamento'],
      recomendacoes: ['Evite áreas baixas'],
      origem: 'real_inmet',
      instanteObservado: '2026-09-06T05:00:00Z',
      fonteDegradada: false,
      entregaSimuladaId: '33333333-3333-3333-3333-333333333333',
    })
  })

  it('mapeia entregaSimuladaId nulo quando o alerta ainda não tem entrega simulada', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        responder(200, { alerta: alertaCorpo({ entrega_simulada_id: null }) }),
      ),
    )

    const alerta = await getAlertaMaisRelevante(SEGURADO_ID)

    expect(alerta?.entregaSimuladaId).toBeNull()
  })

  it('devolve null quando o backend responde sem alerta', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(responder(200, { alerta: null })))

    const alerta = await getAlertaMaisRelevante(SEGURADO_ID)

    expect(alerta).toBeNull()
  })

  it('rejeita com ErroAlertaSegurado (falha de rede) quando fetch lança', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    const erro = await getAlertaMaisRelevante(SEGURADO_ID).catch((causa: unknown) => causa)

    expect(erro).toBeInstanceOf(ErroAlertaSegurado)
    expect((erro as ErroAlertaSegurado).codigo).toBe('falha_de_rede')
  })
})
