import { afterEach, describe, expect, it, vi } from 'vitest'
import { ErroRegras, ativarRegra, getRegra, getRegras, testarRegra } from './regras'
import type { DadosRegra } from './regras'

const REGRA_ID = '11111111-1111-1111-1111-111111111111'

const DADOS_CHUVA: DadosRegra = {
  eventoTipo: 'chuva_intensa',
  limiarMeteorologico: 60,
  areaAplicavel: '9990001',
  apoliceTipo: 'residencial',
  coberturaExigida: 'alagamento',
  antecedenciaHoras: 48,
  canal: 'email',
}

const REGRA_BRUTA = {
  id: REGRA_ID,
  evento_tipo: 'chuva_intensa',
  limiar_meteorologico: 50,
  area_aplicavel: '9990001',
  apolice_tipo: 'residencial',
  cobertura_exigida: 'alagamento',
  antecedencia_horas: 24,
  canal: 'whatsapp',
  versao: 1,
  estado: 'ativa',
}

const REGRA_ESPERADA = {
  id: REGRA_ID,
  eventoTipo: 'chuva_intensa',
  limiarMeteorologico: 50,
  areaAplicavel: '9990001',
  apoliceTipo: 'residencial',
  coberturaExigida: 'alagamento',
  antecedenciaHoras: 24,
  canal: 'whatsapp',
  versao: 1,
  estado: 'ativa',
}

function responder(status: number, corpo: unknown): Response {
  return new Response(JSON.stringify(corpo), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function problema(codigo: string, erros: { campo: string; motivo: string }[] = []) {
  return {
    codigo,
    correlacao_id: '9f8e7d6c-5b4a-3210-9876-543210fedcba',
    ocorrencia: 'Ocorrência sintética da falha.',
    impacto: 'Impacto sintético da falha.',
    proxima_acao: 'Próxima ação segura sintética.',
    erros,
  }
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('getRegras', () => {
  it('mapeia a lista de regras de snake_case para camelCase quando o backend responde 200', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(responder(200, { regras: [REGRA_BRUTA] })))

    const regras = await getRegras()

    expect(regras).toEqual([REGRA_ESPERADA])
  })

  it('resolve lista vazia quando o backend não tem nenhuma regra (sem dado fixo)', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(responder(200, { regras: [] })))

    await expect(getRegras()).resolves.toEqual([])
  })

  it('rejeita com ErroRegras (falha de rede) quando fetch lança', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    const erro = await getRegras().catch((causa: unknown) => causa)

    expect(erro).toBeInstanceOf(ErroRegras)
    expect((erro as ErroRegras).codigo).toBe('falha_de_rede')
  })
})

describe('getRegra', () => {
  it('mapeia a regra de snake_case para camelCase quando o backend responde 200', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(responder(200, REGRA_BRUTA)))

    const regra = await getRegra(REGRA_ID)

    expect(regra).toEqual(REGRA_ESPERADA)
  })

  it('rejeita com ErroRegras tipado quando o backend responde 404', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(responder(404, problema('regra_inexistente'))))

    const erro = await getRegra(REGRA_ID).catch((causa: unknown) => causa)

    expect(erro).toBeInstanceOf(ErroRegras)
    expect((erro as ErroRegras).codigo).toBe('regra_inexistente')
    expect((erro as ErroRegras).status).toBe(404)
  })
})

describe('testarRegra', () => {
  it('mapeia os casos de teste de snake_case para camelCase quando o backend responde 200', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        responder(200, {
          casos: [
            {
              evento_id: '22222222-2222-2222-2222-222222222222',
              relevante: true,
              motivo: 'relevante',
              criterios: [
                {
                  operando: 'área aplicável',
                  valor_observado: '9990001',
                  atende: true,
                  justificativa: 'Área do evento corresponde à área aplicável da regra.',
                },
              ],
            },
          ],
        }),
      ),
    )

    const casos = await testarRegra(REGRA_ID, DADOS_CHUVA)

    expect(casos).toEqual([
      {
        eventoId: '22222222-2222-2222-2222-222222222222',
        relevante: true,
        motivo: 'relevante',
        criterios: [
          {
            operando: 'área aplicável',
            valorObservado: '9990001',
            atende: true,
            justificativa: 'Área do evento corresponde à área aplicável da regra.',
          },
        ],
      },
    ])
  })

  it('resolve lista vazia quando nenhum cenário sintético é aplicável (sem dado fixo)', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(responder(200, { casos: [] })))

    await expect(testarRegra(REGRA_ID, DADOS_CHUVA)).resolves.toEqual([])
  })

  it('rejeita com ErroRegras carregando os erros por campo quando o backend responde 422', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        responder(
          422,
          problema('configuracao_invalida', [
            { campo: 'limiar_meteorologico', motivo: 'Limiar meteorológico deve ser maior que zero.' },
          ]),
        ),
      ),
    )

    const erro = await testarRegra(REGRA_ID, DADOS_CHUVA).catch((causa: unknown) => causa)

    expect(erro).toBeInstanceOf(ErroRegras)
    expect((erro as ErroRegras).codigo).toBe('configuracao_invalida')
    expect((erro as ErroRegras).erros).toEqual([
      { campo: 'limiar_meteorologico', motivo: 'Limiar meteorológico deve ser maior que zero.' },
    ])
  })
})

describe('ativarRegra', () => {
  it('mapeia a nova versão de snake_case para camelCase quando o backend responde 200', async () => {
    const novaVersao = { ...REGRA_BRUTA, versao: 2, limiar_meteorologico: 60 }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(responder(200, novaVersao)))

    const ativada = await ativarRegra(REGRA_ID, 1, DADOS_CHUVA)

    expect(ativada.versao).toBe(2)
    expect(ativada.limiarMeteorologico).toBe(60)
  })

  it('envia uma Idempotency-Key nova em cada chamada', async () => {
    const chamadaFetch = vi.fn().mockImplementation(() => Promise.resolve(responder(200, REGRA_BRUTA)))
    vi.stubGlobal('fetch', chamadaFetch)

    await ativarRegra(REGRA_ID, 1, DADOS_CHUVA)
    await ativarRegra(REGRA_ID, 1, DADOS_CHUVA)

    const chaves = chamadaFetch.mock.calls.map((chamada) => {
      const requisicao = chamada[0] as Request
      return requisicao.headers.get('Idempotency-Key')
    })
    expect(chaves[0]).toBeTruthy()
    expect(chaves[1]).toBeTruthy()
    expect(chaves[0]).not.toBe(chaves[1])
  })

  it('envia versao_esperada no corpo da requisição', async () => {
    const chamadaFetch = vi.fn().mockResolvedValue(responder(200, REGRA_BRUTA))
    vi.stubGlobal('fetch', chamadaFetch)

    await ativarRegra(REGRA_ID, 7, DADOS_CHUVA)

    const requisicao = chamadaFetch.mock.calls[0][0] as Request
    const corpo = (await requisicao.clone().json()) as { versao_esperada: number }
    expect(corpo.versao_esperada).toBe(7)
  })

  it('rejeita com ErroRegras tipado quando o backend responde 409 (conflito de versão)', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(responder(409, problema('conflito_versao'))))

    const erro = await ativarRegra(REGRA_ID, 1, DADOS_CHUVA).catch((causa: unknown) => causa)

    expect(erro).toBeInstanceOf(ErroRegras)
    expect((erro as ErroRegras).codigo).toBe('conflito_versao')
    expect((erro as ErroRegras).status).toBe(409)
  })

  it('rejeita com ErroRegras (falha de rede) quando fetch lança', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    const erro = await ativarRegra(REGRA_ID, 1, DADOS_CHUVA).catch((causa: unknown) => causa)

    expect(erro).toBeInstanceOf(ErroRegras)
    expect((erro as ErroRegras).codigo).toBe('falha_de_rede')
  })
})
