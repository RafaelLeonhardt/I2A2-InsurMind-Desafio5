import { afterEach, describe, expect, it, vi } from 'vitest'
import { ErroListaSeguradosAdmin, getSeguradosDetalhado } from './listaSeguradosAdmin'

function responder(status: number, corpo: unknown): Response {
  return new Response(JSON.stringify(corpo), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('getSeguradosDetalhado', () => {
  it('mapeia nome, área, apólice e canal de cada segurado para camelCase', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        responder(200, {
          segurados: [
            {
              id: '11111111-1111-1111-1111-111111111111',
              nome: 'Pessoa Sintética DEMO-001',
              codigo_ibge_area: '9990001',
              apolice_numero: 'RES-0001',
              canal_preferido: 'whatsapp',
            },
          ],
        }),
      ),
    )

    const segurados = await getSeguradosDetalhado()

    expect(segurados).toEqual([
      {
        id: '11111111-1111-1111-1111-111111111111',
        nome: 'Pessoa Sintética DEMO-001',
        codigoIbgeArea: '9990001',
        apoliceNumero: 'RES-0001',
        canalPreferido: 'whatsapp',
      },
    ])
  })

  it('preserva apoliceNumero nulo quando o segurado não tiver nenhuma apólice', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        responder(200, {
          segurados: [
            {
              id: '11111111-1111-1111-1111-111111111111',
              nome: 'Pessoa Sem Apólice',
              codigo_ibge_area: '9990001',
              apolice_numero: null,
              canal_preferido: 'sms',
            },
          ],
        }),
      ),
    )

    const segurados = await getSeguradosDetalhado()

    expect(segurados[0].apoliceNumero).toBeNull()
  })

  it('devolve lista vazia quando o backend responde sem segurados', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(responder(200, { segurados: [] })))

    const segurados = await getSeguradosDetalhado()

    expect(segurados).toEqual([])
  })

  it('rejeita com ErroListaSeguradosAdmin (status nulo) quando fetch lança (falha de rede)', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    const erro = await getSeguradosDetalhado().catch((causa: unknown) => causa)

    expect(erro).toBeInstanceOf(ErroListaSeguradosAdmin)
    expect((erro as ErroListaSeguradosAdmin).ocorrencia).toBe(
      'Não foi possível falar com o backend local da Central Preventiva.',
    )
    expect((erro as ErroListaSeguradosAdmin).status).toBeNull()
  })

  it('rejeita com ErroListaSeguradosAdmin com o status HTTP quando o backend falha', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(responder(500, {})))

    const erro = await getSeguradosDetalhado().catch((causa: unknown) => causa)

    expect(erro).toBeInstanceOf(ErroListaSeguradosAdmin)
    expect((erro as ErroListaSeguradosAdmin).ocorrencia).toBe(
      'Os segurados sintéticos não puderam ser consultados.',
    )
    expect((erro as ErroListaSeguradosAdmin).status).toBe(500)
  })
})
