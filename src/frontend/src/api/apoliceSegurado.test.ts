import { afterEach, describe, expect, it, vi } from 'vitest'
import { ErroApoliceSegurado, getApolice, getExplicacaoApolice } from './apoliceSegurado'

const SEGURADO_ID = '11111111-1111-1111-1111-111111111111'
const ELEGIBILIDADE_ID = '22222222-2222-2222-2222-222222222222'

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

describe('getApolice', () => {
  it('mapeia todos os campos de snake_case para camelCase, com valores distintos entre si', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        responder(200, {
          numero: 'RES-0001',
          tipo: 'residencial',
          situacao: 'ativa',
          estado_objetivo: 'expirada',
          vigencia_inicio: '2026-01-01',
          vigencia_fim: '2030-12-31',
          endereco_risco_sintetico: 'Rua Sintética, 123',
          coberturas: ['alagamento', 'vendaval'],
          canal_preferido: 'sms',
          participa_de_alertas: false,
        }),
      ),
    )

    const apolice = await getApolice(SEGURADO_ID)

    expect(apolice).toEqual({
      numero: 'RES-0001',
      tipo: 'residencial',
      situacao: 'ativa',
      estadoObjetivo: 'expirada',
      vigenciaInicio: '2026-01-01',
      vigenciaFim: '2030-12-31',
      enderecoRiscoSintetico: 'Rua Sintética, 123',
      coberturas: ['alagamento', 'vendaval'],
      canalPreferido: 'sms',
      participaDeAlertas: false,
    })
  })

  it('rejeita com ErroApoliceSegurado (status 404) quando o backend responde 404', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(responder(404, problema('apolice_nao_encontrada'))),
    )

    const erro = await getApolice(SEGURADO_ID).catch((causa: unknown) => causa)

    expect(erro).toBeInstanceOf(ErroApoliceSegurado)
    expect((erro as ErroApoliceSegurado).codigo).toBe('apolice_nao_encontrada')
    expect((erro as ErroApoliceSegurado).status).toBe(404)
  })

  it('rejeita com ErroApoliceSegurado (falha de rede) quando fetch lança', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    const erro = await getApolice(SEGURADO_ID).catch((causa: unknown) => causa)

    expect(erro).toBeInstanceOf(ErroApoliceSegurado)
    expect((erro as ErroApoliceSegurado).codigo).toBe('falha_de_rede')
  })
})

describe('getExplicacaoApolice', () => {
  it('mapeia a explicação e os critérios de snake_case para camelCase', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        responder(200, {
          elegibilidade_id: ELEGIBILIDADE_ID,
          criterios: [
            {
              operando: 'área afetada',
              valor_observado: '9990001',
              atende: true,
              justificativa: 'Área da apólice corresponde à área do evento.',
            },
            {
              operando: 'cobertura exigida',
              valor_observado: 'nenhuma',
              atende: false,
              justificativa: 'Apólice não possui a cobertura exigida pela regra.',
            },
          ],
        }),
      ),
    )

    const explicacao = await getExplicacaoApolice(SEGURADO_ID, ELEGIBILIDADE_ID)

    expect(explicacao).toEqual({
      elegibilidadeId: ELEGIBILIDADE_ID,
      criterios: [
        {
          operando: 'área afetada',
          valorObservado: '9990001',
          atende: true,
          justificativa: 'Área da apólice corresponde à área do evento.',
        },
        {
          operando: 'cobertura exigida',
          valorObservado: 'nenhuma',
          atende: false,
          justificativa: 'Apólice não possui a cobertura exigida pela regra.',
        },
      ],
    })
  })

  it('rejeita com ErroApoliceSegurado (status 404) quando o backend responde 404', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(responder(404, problema('explicacao_nao_encontrada'))),
    )

    const erro = await getExplicacaoApolice(SEGURADO_ID, ELEGIBILIDADE_ID).catch(
      (causa: unknown) => causa,
    )

    expect(erro).toBeInstanceOf(ErroApoliceSegurado)
    expect((erro as ErroApoliceSegurado).codigo).toBe('explicacao_nao_encontrada')
    expect((erro as ErroApoliceSegurado).status).toBe(404)
  })

  it('rejeita com ErroApoliceSegurado (falha de rede) quando fetch lança', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    const erro = await getExplicacaoApolice(SEGURADO_ID, ELEGIBILIDADE_ID).catch(
      (causa: unknown) => causa,
    )

    expect(erro).toBeInstanceOf(ErroApoliceSegurado)
    expect((erro as ErroApoliceSegurado).codigo).toBe('falha_de_rede')
  })
})
