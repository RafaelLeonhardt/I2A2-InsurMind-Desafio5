import { afterEach, describe, expect, it, vi } from 'vitest'
import { ErroListaComunicados, getListaComunicados } from './listaComunicados'

const SEGURADO_ID = '11111111-1111-1111-1111-111111111111'

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

describe('getListaComunicados', () => {
  it('mapeia todos os campos de snake_case para camelCase, com valores distintos entre si', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        responder(200, {
          comunicados: [
            {
              entrega_simulada_id: '22222222-2222-2222-2222-222222222222',
              mensagem_id: '33333333-3333-3333-3333-333333333333',
              canal: 'email',
              assunto_ou_resumo: 'Aviso preventivo',
              criado_em: '2026-09-05T12:00:00Z',
              visualizacao: {
                id: '44444444-4444-4444-4444-444444444444',
                visualizada_em: '2026-09-05T12:05:00Z',
              },
            },
          ],
        }),
      ),
    )

    const itens = await getListaComunicados(SEGURADO_ID)

    expect(itens).toEqual([
      {
        entregaSimuladaId: '22222222-2222-2222-2222-222222222222',
        mensagemId: '33333333-3333-3333-3333-333333333333',
        canal: 'email',
        assuntoOuResumo: 'Aviso preventivo',
        criadoEm: '2026-09-05T12:00:00Z',
        visualizacao: {
          id: '44444444-4444-4444-4444-444444444444',
          visualizadaEm: '2026-09-05T12:05:00Z',
        },
      },
    ])
  })

  it('mapeia visualizacao nula quando o comunicado ainda não foi visualizado', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        responder(200, {
          comunicados: [
            {
              entrega_simulada_id: '22222222-2222-2222-2222-222222222222',
              mensagem_id: '33333333-3333-3333-3333-333333333333',
              canal: 'sms',
              assunto_ou_resumo: 'Chuva forte hoje.',
              criado_em: '2026-09-05T12:00:00Z',
              visualizacao: null,
            },
          ],
        }),
      ),
    )

    const [item] = await getListaComunicados(SEGURADO_ID)

    expect(item.visualizacao).toBeNull()
  })

  it('devolve lista vazia quando o backend responde sem comunicados', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(responder(200, { comunicados: [] })),
    )

    const itens = await getListaComunicados(SEGURADO_ID)

    expect(itens).toEqual([])
  })

  it('rejeita com ErroListaComunicados (status 422) quando o backend responde 422', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(responder(422, problema('identificador_invalido'))),
    )

    const erro = await getListaComunicados(SEGURADO_ID).catch((causa: unknown) => causa)

    expect(erro).toBeInstanceOf(ErroListaComunicados)
    expect((erro as ErroListaComunicados).codigo).toBe('identificador_invalido')
    expect((erro as ErroListaComunicados).status).toBe(422)
  })

  it('rejeita com ErroListaComunicados (falha de rede) quando fetch lança', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    const erro = await getListaComunicados(SEGURADO_ID).catch((causa: unknown) => causa)

    expect(erro).toBeInstanceOf(ErroListaComunicados)
    expect((erro as ErroListaComunicados).codigo).toBe('falha_de_rede')
  })
})
