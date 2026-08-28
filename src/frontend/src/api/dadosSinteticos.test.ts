import { afterEach, describe, expect, it, vi } from 'vitest'
import { ErroRestauracao, restaurarDadosSinteticos, URL_RESTAURACOES } from './dadosSinteticos'

const RESTAURADO_EM = '2026-03-10T12:30:45+00:00'

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

function cabecalhoIdempotencia(chamada: unknown[]): string {
  const opcoes = chamada[1] as { headers: Record<string, string> }
  return opcoes.headers['Idempotency-Key']
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('cliente de restauração dos dados sintéticos', () => {
  it('resolve com o resultado quando o backend responde 201', async () => {
    const buscar = vi.fn().mockResolvedValue(
      responder(201, { status: 'restaurado', restaurado_em: RESTAURADO_EM }),
    )
    vi.stubGlobal('fetch', buscar)

    await expect(restaurarDadosSinteticos()).resolves.toEqual({
      status: 'restaurado',
      restauradoEm: RESTAURADO_EM,
    })
    expect(buscar.mock.calls[0][0]).toBe(URL_RESTAURACOES)
    expect((buscar.mock.calls[0][1] as { method: string }).method).toBe('POST')
  })

  it('rejeita com erro tipado quando o backend responde 409', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        responder(409, problema('conflito_idempotencia'), 'application/problem+json'),
      ),
    )

    const erro = await restaurarDadosSinteticos().catch((causa: unknown) => causa)

    expect(erro).toBeInstanceOf(ErroRestauracao)
    expect((erro as ErroRestauracao).codigo).toBe('conflito_idempotencia')
    expect((erro as ErroRestauracao).correlacaoId).toBe('9f8e7d6c-5b4a-3210-9876-543210fedcba')
    expect((erro as ErroRestauracao).status).toBe(409)
    expect((erro as ErroRestauracao).proximaAcao).toBe('Próxima ação segura sintética.')
  })

  it('rejeita com erro tipado quando o backend responde 422', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        responder(422, problema('idempotency_key_ausente'), 'application/problem+json'),
      ),
    )

    const erro = await restaurarDadosSinteticos().catch((causa: unknown) => causa)

    expect(erro).toBeInstanceOf(ErroRestauracao)
    expect((erro as ErroRestauracao).codigo).toBe('idempotency_key_ausente')
    expect((erro as ErroRestauracao).status).toBe(422)
  })

  it('converte a falha de rede em erro tipado', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    const erro = await restaurarDadosSinteticos().catch((causa: unknown) => causa)

    expect(erro).toBeInstanceOf(ErroRestauracao)
    expect((erro as ErroRestauracao).codigo).toBe('falha_de_rede')
    expect((erro as ErroRestauracao).status).toBeNull()
    expect((erro as ErroRestauracao).ocorrencia).toContain('backend local')
    expect((erro as ErroRestauracao).proximaAcao).toContain('127.0.0.1:8000')
  })

  it('descreve a falha mesmo quando a resposta de erro não é problem+json', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response('<html>erro</html>', { status: 500 })),
    )

    const erro = await restaurarDadosSinteticos().catch((causa: unknown) => causa)

    expect(erro).toBeInstanceOf(ErroRestauracao)
    expect((erro as ErroRestauracao).codigo).toBe('falha_inesperada')
    expect((erro as ErroRestauracao).status).toBe(500)
    expect((erro as ErroRestauracao).impacto).toContain('preservado')
  })

  it('envia uma Idempotency-Key nova a cada chamada', async () => {
    const buscar = vi.fn().mockImplementation(() =>
      Promise.resolve(responder(201, { status: 'restaurado', restaurado_em: RESTAURADO_EM })),
    )
    vi.stubGlobal('fetch', buscar)

    await restaurarDadosSinteticos()
    await restaurarDadosSinteticos()

    const primeira = cabecalhoIdempotencia(buscar.mock.calls[0])
    const segunda = cabecalhoIdempotencia(buscar.mock.calls[1])
    expect(primeira).toMatch(/^[0-9a-f-]{36}$/)
    expect(segunda).toMatch(/^[0-9a-f-]{36}$/)
    expect(primeira).not.toBe(segunda)
  })
})
