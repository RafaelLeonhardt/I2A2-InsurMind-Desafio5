import { afterEach, describe, expect, it, vi } from 'vitest'
import { ErroElegibilidade, getDetalheElegibilidade, getElegibilidade } from './elegibilidade'

const EXECUCAO_ID = '11111111-1111-1111-1111-111111111111'
const REGISTRO_ID = '22222222-2222-2222-2222-222222222222'

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

describe('getElegibilidade', () => {
  it('mapeia quantidades e registros de snake_case para camelCase quando o backend responde 200', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        responder(200, {
          incluidos: 1,
          excluidos: 1,
          registros: [
            {
              id: REGISTRO_ID,
              nome_segurado: 'Maria Sintética',
              apolice_id: '33333333-3333-3333-3333-333333333333',
              codigo_ibge_area: '9990001',
              canal: 'whatsapp',
              elegivel: true,
            },
          ],
        }),
      ),
    )

    const elegibilidade = await getElegibilidade(EXECUCAO_ID)

    expect(elegibilidade).toEqual({
      incluidos: 1,
      excluidos: 1,
      registros: [
        {
          id: REGISTRO_ID,
          nomeSegurado: 'Maria Sintética',
          apoliceId: '33333333-3333-3333-3333-333333333333',
          codigoIbgeArea: '9990001',
          canal: 'whatsapp',
          elegivel: true,
        },
      ],
    })
  })

  it('resolve conjunto vazio quando a execução não tem nenhum resultado (sem dado fixo)', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(responder(200, { incluidos: 0, excluidos: 0, registros: [] })),
    )

    await expect(getElegibilidade(EXECUCAO_ID)).resolves.toEqual({
      incluidos: 0,
      excluidos: 0,
      registros: [],
    })
  })

  it('rejeita com ErroElegibilidade tipado quando o backend responde 422', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(responder(422, problema('execucao_id_invalido'))),
    )

    const erro = await getElegibilidade(EXECUCAO_ID).catch((causa: unknown) => causa)

    expect(erro).toBeInstanceOf(ErroElegibilidade)
    expect((erro as ErroElegibilidade).codigo).toBe('execucao_id_invalido')
  })

  it('rejeita com ErroElegibilidade (falha de rede) quando fetch lança', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    const erro = await getElegibilidade(EXECUCAO_ID).catch((causa: unknown) => causa)

    expect(erro).toBeInstanceOf(ErroElegibilidade)
    expect((erro as ErroElegibilidade).codigo).toBe('falha_de_rede')
  })
})

describe('getDetalheElegibilidade', () => {
  it('mapeia o detalhe de snake_case para camelCase quando o backend responde 200', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        responder(200, {
          id: REGISTRO_ID,
          execucao_id: EXECUCAO_ID,
          evento_id: '44444444-4444-4444-4444-444444444444',
          regra_id: '55555555-5555-5555-5555-555555555555',
          regra_versao: 3,
          segurado_id: '66666666-6666-6666-6666-666666666666',
          nome_segurado: 'Maria Sintética',
          apolice_id: '33333333-3333-3333-3333-333333333333',
          codigo_ibge_area: '9990001',
          elegivel: true,
          criterios: [
            {
              operando: 'área afetada',
              valor_observado: '9990001',
              atende: true,
              justificativa: 'Área da apólice corresponde à área do evento (9990001).',
            },
          ],
          canal: 'whatsapp',
          justificativa: 'Segurado e apólice atendem integralmente aos critérios da regra ativa.',
          criado_em: '2026-08-30T12:00:00+00:00',
        }),
      ),
    )

    const detalhe = await getDetalheElegibilidade(EXECUCAO_ID, REGISTRO_ID)

    expect(detalhe).not.toBeNull()
    expect(detalhe?.regraVersao).toBe(3)
    expect(detalhe?.nomeSegurado).toBe('Maria Sintética')
    expect(detalhe?.criterios).toEqual([
      {
        operando: 'área afetada',
        valorObservado: '9990001',
        atende: true,
        justificativa: 'Área da apólice corresponde à área do evento (9990001).',
      },
    ])
  })

  it('resolve null quando o backend responde 404 (progresso real, não erro)', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(responder(404, problema('resultado_elegibilidade_inexistente'))),
    )

    await expect(getDetalheElegibilidade(EXECUCAO_ID, REGISTRO_ID)).resolves.toBeNull()
  })

  it('rejeita com ErroElegibilidade (falha de rede) quando fetch lança', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    const erro = await getDetalheElegibilidade(EXECUCAO_ID, REGISTRO_ID).catch(
      (causa: unknown) => causa,
    )

    expect(erro).toBeInstanceOf(ErroElegibilidade)
    expect((erro as ErroElegibilidade).codigo).toBe('falha_de_rede')
  })
})
