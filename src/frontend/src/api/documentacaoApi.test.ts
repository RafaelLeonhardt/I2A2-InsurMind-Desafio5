import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  ENDERECO_OPENAPI,
  ENDERECO_SWAGGER_UI,
  ErroDocumentacaoApi,
  verificarDocumentacaoApi,
} from './documentacaoApi'

function responder(status: number, corpo: unknown): Response {
  return new Response(JSON.stringify(corpo), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('verificarDocumentacaoApi', () => {
  it('resolve com estado disponível e os dois endereços locais quando /api/v1/saude responde 200', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(responder(200, { status: 'disponivel', ambiente: 'educacional' })),
    )

    await expect(verificarDocumentacaoApi()).resolves.toEqual({
      estado: 'disponivel',
      enderecoSwaggerUi: ENDERECO_SWAGGER_UI,
      enderecoOpenApi: ENDERECO_OPENAPI,
    })
  })

  it('rejeita com ErroDocumentacaoApi (falha de rede) quando fetch lança', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    const erro = await verificarDocumentacaoApi().catch((causa: unknown) => causa)

    expect(erro).toBeInstanceOf(ErroDocumentacaoApi)
    expect((erro as ErroDocumentacaoApi).causa).toBe(
      'Não foi possível falar com o backend local da Central Preventiva.',
    )
    expect((erro as ErroDocumentacaoApi).impacto).not.toBe('')
    expect((erro as ErroDocumentacaoApi).proximaAcao).not.toBe('')
    expect((erro as ErroDocumentacaoApi).enderecoEsperado).toBe(ENDERECO_SWAGGER_UI)
  })

  it('rejeita com ErroDocumentacaoApi quando /api/v1/saude responde status não-2xx', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(responder(503, {})))

    const erro = await verificarDocumentacaoApi().catch((causa: unknown) => causa)

    expect(erro).toBeInstanceOf(ErroDocumentacaoApi)
    expect((erro as ErroDocumentacaoApi).causa).toContain('503')
    expect((erro as ErroDocumentacaoApi).impacto).not.toBe('')
    expect((erro as ErroDocumentacaoApi).proximaAcao).not.toBe('')
    expect((erro as ErroDocumentacaoApi).enderecoEsperado).toBe(ENDERECO_SWAGGER_UI)
  })
})
