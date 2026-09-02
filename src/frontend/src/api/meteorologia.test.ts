import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  ErroMeteorologia,
  IDENTIFICADOR_CENARIO_GRANIZO,
  ativarCenarioSintetico,
  getEventos,
  getSincronizacoes,
  solicitarColeta,
  solicitarNovaTentativa,
} from './meteorologia'

const AREA_ID = '11111111-1111-1111-1111-111111111111'
const SINCRONIZACAO_ID = '22222222-2222-2222-2222-222222222222'

function responder(status: number, corpo: unknown): Response {
  return new Response(JSON.stringify(corpo), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function problema(codigo: string) {
  return {
    codigo,
    correlacao_id: '9f8e7d6c-5b4a-3210-9876-543210fedcba',
    ocorrencia: 'Ocorrência sintética da falha.',
    impacto: 'Impacto sintético da falha.',
    proxima_acao: 'Próxima ação segura sintética.',
  }
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('solicitarColeta', () => {
  it('mapeia snake_case para camelCase quando o backend responde 202', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        responder(202, {
          id: '22222222-2222-2222-2222-222222222222',
          requisicao_id: '33333333-3333-3333-3333-333333333333',
          estado: 'concluido',
          registros_validos: 1,
          motivo_falha: null,
          aceito_em: '2026-08-30T12:00:00+00:00',
        }),
      ),
    )

    const aceita = await solicitarColeta(AREA_ID)

    expect(aceita).toEqual({
      id: '22222222-2222-2222-2222-222222222222',
      requisicaoId: '33333333-3333-3333-3333-333333333333',
      estado: 'concluido',
      registrosValidos: 1,
      motivoFalha: null,
      aceitoEm: '2026-08-30T12:00:00+00:00',
    })
  })

  it('envia uma Idempotency-Key nova em cada chamada', async () => {
    const chamadaFetch = vi.fn().mockImplementation(() =>
      Promise.resolve(
        responder(202, {
          id: '2',
          requisicao_id: '3',
          estado: 'concluido',
          registros_validos: 1,
          motivo_falha: null,
          aceito_em: '2026-08-30T12:00:00+00:00',
        }),
      ),
    )
    vi.stubGlobal('fetch', chamadaFetch)

    await solicitarColeta(AREA_ID)
    await solicitarColeta(AREA_ID)

    const chaves = chamadaFetch.mock.calls.map((chamada) => {
      const requisicao = chamada[0] as Request
      return requisicao.headers.get('Idempotency-Key')
    })
    expect(chaves[0]).toBeTruthy()
    expect(chaves[1]).toBeTruthy()
    expect(chaves[0]).not.toBe(chaves[1])
  })

  it('rejeita com ErroMeteorologia tipado quando o backend responde 404', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(responder(404, problema('area_monitorada_desconhecida'))),
    )

    const erro = await solicitarColeta(AREA_ID).catch((causa: unknown) => causa)

    expect(erro).toBeInstanceOf(ErroMeteorologia)
    expect((erro as ErroMeteorologia).codigo).toBe('area_monitorada_desconhecida')
    expect((erro as ErroMeteorologia).status).toBe(404)
  })

  it('rejeita com ErroMeteorologia (falha de rede) quando fetch lança', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    const erro = await solicitarColeta(AREA_ID).catch((causa: unknown) => causa)

    expect(erro).toBeInstanceOf(ErroMeteorologia)
    expect((erro as ErroMeteorologia).codigo).toBe('falha_de_rede')
    expect((erro as ErroMeteorologia).status).toBeNull()
  })
})

describe('solicitarNovaTentativa', () => {
  it('mapeia snake_case para camelCase quando o backend responde 202', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        responder(202, {
          id: '33333333-3333-3333-3333-333333333333',
          requisicao_id: '44444444-4444-4444-4444-444444444444',
          estado: 'concluido',
          registros_validos: 1,
          motivo_falha: null,
          aceito_em: '2026-08-30T12:00:00+00:00',
        }),
      ),
    )

    const aceita = await solicitarNovaTentativa(SINCRONIZACAO_ID)

    expect(aceita).toEqual({
      id: '33333333-3333-3333-3333-333333333333',
      requisicaoId: '44444444-4444-4444-4444-444444444444',
      estado: 'concluido',
      registrosValidos: 1,
      motivoFalha: null,
      aceitoEm: '2026-08-30T12:00:00+00:00',
    })
  })

  it('chama o caminho com o id da sincronização de origem e uma Idempotency-Key nova', async () => {
    const chamadaFetch = vi.fn().mockResolvedValue(
      responder(202, {
        id: '3',
        requisicao_id: '4',
        estado: 'concluido',
        registros_validos: 1,
        motivo_falha: null,
        aceito_em: '2026-08-30T12:00:00+00:00',
      }),
    )
    vi.stubGlobal('fetch', chamadaFetch)

    await solicitarNovaTentativa(SINCRONIZACAO_ID)

    const requisicao = chamadaFetch.mock.calls[0][0] as Request
    expect(requisicao.url).toContain(`/${SINCRONIZACAO_ID}/nova-tentativa`)
    expect(requisicao.headers.get('Idempotency-Key')).toBeTruthy()
  })

  it('rejeita com ErroMeteorologia tipado quando o backend responde 404', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(responder(404, problema('sincronizacao_desconhecida'))),
    )

    const erro = await solicitarNovaTentativa(SINCRONIZACAO_ID).catch((causa: unknown) => causa)

    expect(erro).toBeInstanceOf(ErroMeteorologia)
    expect((erro as ErroMeteorologia).codigo).toBe('sincronizacao_desconhecida')
  })

  it('rejeita com ErroMeteorologia (falha de rede) quando fetch lança', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    const erro = await solicitarNovaTentativa(SINCRONIZACAO_ID).catch((causa: unknown) => causa)

    expect(erro).toBeInstanceOf(ErroMeteorologia)
    expect((erro as ErroMeteorologia).codigo).toBe('falha_de_rede')
  })
})

describe('ativarCenarioSintetico', () => {
  it('mapeia snake_case para camelCase quando o backend responde 202', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        responder(202, {
          id: '55555555-5555-5555-5555-555555555555',
          requisicao_id: '66666666-6666-6666-6666-666666666666',
          estado: 'concluido',
          registros_validos: 1,
          motivo_falha: null,
          aceito_em: '2026-08-30T12:00:00+00:00',
        }),
      ),
    )

    const aceita = await ativarCenarioSintetico(IDENTIFICADOR_CENARIO_GRANIZO, AREA_ID)

    expect(aceita).toEqual({
      id: '55555555-5555-5555-5555-555555555555',
      requisicaoId: '66666666-6666-6666-6666-666666666666',
      estado: 'concluido',
      registrosValidos: 1,
      motivoFalha: null,
      aceitoEm: '2026-08-30T12:00:00+00:00',
    })
  })

  it('chama o caminho com o identificador do cenário e uma Idempotency-Key nova', async () => {
    const chamadaFetch = vi.fn().mockResolvedValue(
      responder(202, {
        id: '5',
        requisicao_id: '6',
        estado: 'concluido',
        registros_validos: 1,
        motivo_falha: null,
        aceito_em: '2026-08-30T12:00:00+00:00',
      }),
    )
    vi.stubGlobal('fetch', chamadaFetch)

    await ativarCenarioSintetico(IDENTIFICADOR_CENARIO_GRANIZO, AREA_ID)

    const requisicao = chamadaFetch.mock.calls[0][0] as Request
    expect(requisicao.url).toContain(
      `/cenarios-sinteticos/${IDENTIFICADOR_CENARIO_GRANIZO}/ativar`,
    )
    expect(requisicao.headers.get('Idempotency-Key')).toBeTruthy()
  })

  it('rejeita com ErroMeteorologia tipado quando o backend responde 404', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(responder(404, problema('area_monitorada_desconhecida'))),
    )

    const erro = await ativarCenarioSintetico(IDENTIFICADOR_CENARIO_GRANIZO, AREA_ID).catch(
      (causa: unknown) => causa,
    )

    expect(erro).toBeInstanceOf(ErroMeteorologia)
    expect((erro as ErroMeteorologia).codigo).toBe('area_monitorada_desconhecida')
  })

  it('rejeita com ErroMeteorologia (falha de rede) quando fetch lança', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    const erro = await ativarCenarioSintetico(IDENTIFICADOR_CENARIO_GRANIZO, AREA_ID).catch(
      (causa: unknown) => causa,
    )

    expect(erro).toBeInstanceOf(ErroMeteorologia)
    expect((erro as ErroMeteorologia).codigo).toBe('falha_de_rede')
  })
})

describe('getEventos', () => {
  it('mapeia a lista de eventos de snake_case para camelCase quando o backend responde 200', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        responder(200, {
          eventos: [
            {
              id: '1',
              tipo: 'chuva_intensa',
              area: '9990001',
              periodo_inicio: '2026-08-30T17:00:00+00:00',
              periodo_fim: '2026-08-30T18:00:00+00:00',
              intensidade: 55.4,
              proveniencia: 'real_inmet',
              instante_observado: '2026-08-30T18:00:00+00:00',
            },
          ],
        }),
      ),
    )

    const eventos = await getEventos()

    expect(eventos).toEqual([
      {
        id: '1',
        tipo: 'chuva_intensa',
        area: '9990001',
        periodoInicio: '2026-08-30T17:00:00+00:00',
        periodoFim: '2026-08-30T18:00:00+00:00',
        intensidade: 55.4,
        proveniencia: 'real_inmet',
        instanteObservado: '2026-08-30T18:00:00+00:00',
      },
    ])
  })

  it('resolve lista vazia quando o backend não tem nenhum evento (sem dado fixo)', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(responder(200, { eventos: [] })))

    await expect(getEventos()).resolves.toEqual([])
  })

  it('rejeita com ErroMeteorologia (falha de rede) quando fetch lança', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    const erro = await getEventos().catch((causa: unknown) => causa)

    expect(erro).toBeInstanceOf(ErroMeteorologia)
    expect((erro as ErroMeteorologia).codigo).toBe('falha_de_rede')
  })
})

describe('getSincronizacoes', () => {
  it('mapeia o histórico de snake_case para camelCase quando o backend responde 200', async () => {
    const sincronizacaoBruta = {
      id: 's1',
      requisicao_id: 'r1',
      area_monitorada_id: 'a1',
      origem: 'manual',
      estado: 'concluido',
      registros_validos: 1,
      motivo_falha: null,
      iniciado_em: '2026-08-30T12:00:00+00:00',
      finalizado_em: '2026-08-30T12:00:05+00:00',
      tentativas: [
        {
          numero_tentativa: 1,
          codigo_resultado: 'sucesso',
          iniciado_em: '2026-08-30T12:00:00+00:00',
          finalizado_em: '2026-08-30T12:00:01+00:00',
        },
      ],
      limite_tentativas: 3,
    }
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        responder(200, {
          ultima_tentativa: sincronizacaoBruta,
          ultima_valida: sincronizacaoBruta,
          proxima_consulta: '2026-08-30T12:15:00+00:00',
          resultados_anteriores: [sincronizacaoBruta],
        }),
      ),
    )

    const historico = await getSincronizacoes()

    expect(historico).toEqual({
      ultimaTentativa: {
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
      },
      ultimaValida: {
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
      },
      proximaConsulta: '2026-08-30T12:15:00+00:00',
      resultadosAnteriores: [
        {
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
        },
      ],
    })
  })

  it('resolve marcos nulos e lista vazia quando nunca houve sincronização (sem dado fixo)', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        responder(200, {
          ultima_tentativa: null,
          ultima_valida: null,
          proxima_consulta: null,
          resultados_anteriores: [],
        }),
      ),
    )

    await expect(getSincronizacoes()).resolves.toEqual({
      ultimaTentativa: null,
      ultimaValida: null,
      proximaConsulta: null,
      resultadosAnteriores: [],
    })
  })

  it('rejeita com ErroMeteorologia (falha de rede) quando fetch lança', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    const erro = await getSincronizacoes().catch((causa: unknown) => causa)

    expect(erro).toBeInstanceOf(ErroMeteorologia)
    expect((erro as ErroMeteorologia).codigo).toBe('falha_de_rede')
  })
})
