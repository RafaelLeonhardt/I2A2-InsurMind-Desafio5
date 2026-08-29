import { afterEach, describe, expect, it, vi } from 'vitest'
import { ErroContexto, getSeguradoPadrao, URL_SEGURADO_PADRAO } from './contexto'

const ID_SEGURADO = '11111111-1111-4111-8111-111111111111'
const NOME_SEGURADO = 'Pessoa Segurada Sintética DEMO-001'

function responder(status: number, corpo: unknown, tipo = 'application/json'): Response {
  return new Response(JSON.stringify(corpo), {
    status,
    headers: { 'Content-Type': tipo },
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

describe('cliente do segurado padrão (getSeguradoPadrao)', () => {
  it('resolve com {id, nome} quando o backend responde 200', async () => {
    const buscar = vi.fn().mockResolvedValue(
      responder(200, { id: ID_SEGURADO, nome: NOME_SEGURADO }),
    )
    vi.stubGlobal('fetch', buscar)

    await expect(getSeguradoPadrao()).resolves.toEqual({
      id: ID_SEGURADO,
      nome: NOME_SEGURADO,
    })
    expect(buscar.mock.calls[0][0]).toBe(URL_SEGURADO_PADRAO)
  })

  it('rejeita com ErroContexto tipado quando o backend responde 503 problem+json', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        responder(503, problema('segurado_padrao_ausente'), 'application/problem+json'),
      ),
    )

    const erro = await getSeguradoPadrao().catch((causa: unknown) => causa)

    expect(erro).toBeInstanceOf(ErroContexto)
    expect((erro as ErroContexto).codigo).toBe('segurado_padrao_ausente')
    expect((erro as ErroContexto).status).toBe(503)
    expect((erro as ErroContexto).correlacaoId).toBe('9f8e7d6c-5b4a-3210-9876-543210fedcba')
    expect((erro as ErroContexto).proximaAcao).toBe('Próxima ação segura sintética.')
  })

  it('rejeita com ErroContexto (falha_de_rede) quando fetch lança', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    const erro = await getSeguradoPadrao().catch((causa: unknown) => causa)

    expect(erro).toBeInstanceOf(ErroContexto)
    expect((erro as ErroContexto).codigo).toBe('falha_de_rede')
    expect((erro as ErroContexto).status).toBeNull()
  })

  it('descreve a falha mesmo quando a resposta de erro não é problem+json', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response('<html>erro</html>', { status: 500 })),
    )

    const erro = await getSeguradoPadrao().catch((causa: unknown) => causa)

    expect(erro).toBeInstanceOf(ErroContexto)
    expect((erro as ErroContexto).codigo).toBe('falha_inesperada')
    expect((erro as ErroContexto).status).toBe(500)
  })
})
