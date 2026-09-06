import { afterEach, describe, expect, it, vi } from 'vitest'
import { ErroListaSegurados, getListaSegurados } from './listaSegurados'

function responder(status: number, corpo: unknown): Response {
  return new Response(JSON.stringify(corpo), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('getListaSegurados', () => {
  it('mapeia id e nome de cada segurado, com valores distintos entre si', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        responder(200, {
          segurados: [
            { id: '11111111-1111-1111-1111-111111111111', nome: 'Pessoa Sintética DEMO-001' },
            { id: '22222222-2222-2222-2222-222222222222', nome: 'Pessoa Sintética DEMO-002' },
          ],
        }),
      ),
    )

    const segurados = await getListaSegurados()

    expect(segurados).toEqual([
      { id: '11111111-1111-1111-1111-111111111111', nome: 'Pessoa Sintética DEMO-001' },
      { id: '22222222-2222-2222-2222-222222222222', nome: 'Pessoa Sintética DEMO-002' },
    ])
  })

  it('devolve lista vazia quando o backend responde sem segurados', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(responder(200, { segurados: [] })))

    const segurados = await getListaSegurados()

    expect(segurados).toEqual([])
  })

  it('rejeita com ErroListaSegurados quando fetch lança (falha de rede)', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    const erro = await getListaSegurados().catch((causa: unknown) => causa)

    expect(erro).toBeInstanceOf(ErroListaSegurados)
    expect((erro as ErroListaSegurados).ocorrencia).toBe(
      'Não foi possível falar com o backend local da Central Preventiva.',
    )
  })

  it('rejeita com ErroListaSegurados quando o backend responde com falha inesperada', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(responder(500, {})))

    const erro = await getListaSegurados().catch((causa: unknown) => causa)

    expect(erro).toBeInstanceOf(ErroListaSegurados)
    expect((erro as ErroListaSegurados).ocorrencia).toBe(
      'Os segurados sintéticos não puderam ser consultados.',
    )
  })
})
