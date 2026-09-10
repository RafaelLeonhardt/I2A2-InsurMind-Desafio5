import { afterEach, describe, expect, it, vi } from 'vitest'
import { ErroListaAlertas, getDetalheAlerta, getListaAlertas } from './listaAlertasSegurado'

const SEGURADO_ID = '11111111-1111-1111-1111-111111111111'
const ELEGIBILIDADE_ID = '22222222-2222-2222-2222-222222222222'

function responder(status: number, corpo: unknown): Response {
  return new Response(JSON.stringify(corpo), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function alertaCorpo(sobrescritas: Record<string, unknown> = {}) {
  return {
    elegibilidade_id: ELEGIBILIDADE_ID,
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

describe('getListaAlertas', () => {
  it('mapeia cada item, incluindo entregaSimuladaId (6.8), de snake_case para camelCase', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        responder(200, { alertas: [{ alerta: alertaCorpo(), classificacao: 'ativo' }] }),
      ),
    )

    const [item] = await getListaAlertas(SEGURADO_ID)

    expect(item.classificacao).toBe('ativo')
    expect(item.alerta.entregaSimuladaId).toBe('33333333-3333-3333-3333-333333333333')
    expect(item.alerta.elegibilidadeId).toBe(ELEGIBILIDADE_ID)
  })

  it('mapeia entregaSimuladaId nulo para um alerta ainda não simulado', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        responder(200, {
          alertas: [
            {
              alerta: alertaCorpo({ entrega_simulada_id: null }),
              classificacao: 'ainda_nao_simulado',
            },
          ],
        }),
      ),
    )

    const [item] = await getListaAlertas(SEGURADO_ID)

    expect(item.alerta.entregaSimuladaId).toBeNull()
  })

  it('devolve lista vazia quando o backend responde sem alertas', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(responder(200, { alertas: [] })))

    expect(await getListaAlertas(SEGURADO_ID)).toEqual([])
  })

  it('rejeita com ErroListaAlertas (falha de rede) quando fetch lança', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    const erro = await getListaAlertas(SEGURADO_ID).catch((causa: unknown) => causa)

    expect(erro).toBeInstanceOf(ErroListaAlertas)
    expect((erro as ErroListaAlertas).codigo).toBe('falha_de_rede')
  })
})

describe('getDetalheAlerta', () => {
  it('mapeia o detalhe completo, incluindo entregaSimuladaId (6.8) do alerta selecionado', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        responder(200, {
          alerta: alertaCorpo(),
          classificacao: 'ativo',
          apolice_id: '44444444-4444-4444-4444-444444444444',
          justificativa: 'Segurado e apólice atendem à regra ativa.',
          linha_do_tempo: [],
        }),
      ),
    )

    const detalhe = await getDetalheAlerta(SEGURADO_ID, ELEGIBILIDADE_ID)

    expect(detalhe.apoliceId).toBe('44444444-4444-4444-4444-444444444444')
    expect(detalhe.justificativa).toBe('Segurado e apólice atendem à regra ativa.')
    expect(detalhe.alerta.entregaSimuladaId).toBe('33333333-3333-3333-3333-333333333333')
  })

  it('rejeita com ErroListaAlertas (status 404) quando o alerta não existe ou não pertence ao segurado', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        responder(404, {
          codigo: 'alerta_nao_encontrado',
          correlacao_id: '9f8e7d6c-5b4a-3210-9876-543210fedcba',
          ocorrencia: 'O alerta não existe para este segurado.',
          impacto: 'Nenhum detalhe pode ser exibido.',
          proxima_acao: 'Consulte o alerta pelo identificador retornado pela lista de alertas.',
        }),
      ),
    )

    const erro = await getDetalheAlerta(SEGURADO_ID, ELEGIBILIDADE_ID).catch(
      (causa: unknown) => causa,
    )

    expect(erro).toBeInstanceOf(ErroListaAlertas)
    expect((erro as ErroListaAlertas).status).toBe(404)
  })
})
