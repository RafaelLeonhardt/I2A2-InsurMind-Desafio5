import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  ErroProntidao,
  getDependencias,
  solicitarNovaVerificacao,
  URL_DEPENDENCIAS,
} from './prontidao'

const VERIFICADO_EM = '2026-08-29T12:00:00+00:00'
const ACEITO_EM = '2026-08-29T12:00:05+00:00'

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

describe('cliente de leitura da prontidão (getDependencias)', () => {
  it('mapeia snake_case para camelCase quando o backend responde 200', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        responder(200, {
          dependencias: [
            {
              nome: 'backend',
              estado: 'disponivel',
              verificado_em: VERIFICADO_EM,
              causa: null,
              impacto: 'Nenhum.',
              acao_disponivel: 'Nenhuma ação necessária.',
            },
            {
              nome: 'openai',
              estado: 'indisponivel',
              verificado_em: null,
              causa: 'Credencial ausente.',
              impacto: 'Produção agêntica indisponível.',
              acao_disponivel: 'Defina OPENAI_API_KEY e verifique novamente.',
            },
          ],
        }),
      ),
    )

    const dependencias = await getDependencias()

    expect(dependencias).toEqual([
      {
        nome: 'backend',
        estado: 'disponivel',
        verificadoEm: VERIFICADO_EM,
        causa: null,
        impacto: 'Nenhum.',
        acaoDisponivel: 'Nenhuma ação necessária.',
      },
      {
        nome: 'openai',
        estado: 'indisponivel',
        verificadoEm: null,
        causa: 'Credencial ausente.',
        impacto: 'Produção agêntica indisponível.',
        acaoDisponivel: 'Defina OPENAI_API_KEY e verifique novamente.',
      },
    ])
  })

  it('chama a URL de dependências com o método GET', async () => {
    const buscar = vi.fn().mockResolvedValue(responder(200, { dependencias: [] }))
    vi.stubGlobal('fetch', buscar)

    await getDependencias()

    expect(buscar.mock.calls[0][0]).toBe(URL_DEPENDENCIAS)
  })

  it('rejeita com erro tipado quando o backend responde erro', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        responder(500, problema('falha_inesperada'), 'application/problem+json'),
      ),
    )

    const erro = await getDependencias().catch((causa: unknown) => causa)

    expect(erro).toBeInstanceOf(ErroProntidao)
    expect((erro as ErroProntidao).codigo).toBe('falha_inesperada')
    expect((erro as ErroProntidao).status).toBe(500)
  })

  it('converte a falha de rede em erro tipado', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    const erro = await getDependencias().catch((causa: unknown) => causa)

    expect(erro).toBeInstanceOf(ErroProntidao)
    expect((erro as ErroProntidao).codigo).toBe('falha_de_rede')
    expect((erro as ErroProntidao).status).toBeNull()
  })
})

describe('cliente de nova verificação (solicitarNovaVerificacao)', () => {
  it('resolve com o ack quando o backend responde 202', async () => {
    const buscar = vi.fn().mockResolvedValue(
      responder(202, { nome: 'inmet', estado: 'verificando', aceito_em: ACEITO_EM }),
    )
    vi.stubGlobal('fetch', buscar)

    await expect(solicitarNovaVerificacao('inmet')).resolves.toEqual({
      nome: 'inmet',
      estado: 'verificando',
      aceitoEm: ACEITO_EM,
    })
    expect(buscar.mock.calls[0][0]).toBe(`${URL_DEPENDENCIAS}/inmet/verificacoes`)
    expect((buscar.mock.calls[0][1] as { method: string }).method).toBe('POST')
  })

  it('envia uma Idempotency-Key nova a cada chamada', async () => {
    const buscar = vi.fn().mockImplementation(() =>
      Promise.resolve(
        responder(202, { nome: 'openai', estado: 'verificando', aceito_em: ACEITO_EM }),
      ),
    )
    vi.stubGlobal('fetch', buscar)

    await solicitarNovaVerificacao('openai')
    await solicitarNovaVerificacao('openai')

    const primeira = cabecalhoIdempotencia(buscar.mock.calls[0])
    const segunda = cabecalhoIdempotencia(buscar.mock.calls[1])
    expect(primeira).toMatch(/^[0-9a-f-]{36}$/)
    expect(segunda).toMatch(/^[0-9a-f-]{36}$/)
    expect(primeira).not.toBe(segunda)
  })

  it('rejeita com erro tipado quando o backend responde 404', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        responder(404, problema('dependencia_desconhecida'), 'application/problem+json'),
      ),
    )

    const erro = await solicitarNovaVerificacao('inmet').catch((causa: unknown) => causa)

    expect(erro).toBeInstanceOf(ErroProntidao)
    expect((erro as ErroProntidao).codigo).toBe('dependencia_desconhecida')
    expect((erro as ErroProntidao).status).toBe(404)
  })

  it('rejeita com erro tipado quando o backend responde 409 de conflito de idempotência', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        responder(409, problema('conflito_idempotencia'), 'application/problem+json'),
      ),
    )

    const erro = await solicitarNovaVerificacao('inmet').catch((causa: unknown) => causa)

    expect(erro).toBeInstanceOf(ErroProntidao)
    expect((erro as ErroProntidao).codigo).toBe('conflito_idempotencia')
    expect((erro as ErroProntidao).status).toBe(409)
  })

  it('rejeita com erro tipado quando o backend responde 409 de verificação em andamento', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        responder(409, problema('verificacao_em_andamento'), 'application/problem+json'),
      ),
    )

    const erro = await solicitarNovaVerificacao('inmet').catch((causa: unknown) => causa)

    expect(erro).toBeInstanceOf(ErroProntidao)
    expect((erro as ErroProntidao).codigo).toBe('verificacao_em_andamento')
    expect((erro as ErroProntidao).status).toBe(409)
  })

  it('rejeita com erro tipado quando o backend responde 422 por Idempotency-Key ausente', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        responder(422, problema('idempotency_key_ausente'), 'application/problem+json'),
      ),
    )

    const erro = await solicitarNovaVerificacao('inmet').catch((causa: unknown) => causa)

    expect(erro).toBeInstanceOf(ErroProntidao)
    expect((erro as ErroProntidao).codigo).toBe('idempotency_key_ausente')
    expect((erro as ErroProntidao).status).toBe(422)
  })

  it('rejeita com erro tipado quando o backend responde 422 por dependência local', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        responder(422, problema('dependencia_local_nao_reverifica'), 'application/problem+json'),
      ),
    )

    const erro = await solicitarNovaVerificacao('backend').catch((causa: unknown) => causa)

    expect(erro).toBeInstanceOf(ErroProntidao)
    expect((erro as ErroProntidao).codigo).toBe('dependencia_local_nao_reverifica')
    expect((erro as ErroProntidao).status).toBe(422)
  })

  it('converte a falha de rede em erro tipado', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    const erro = await solicitarNovaVerificacao('inmet').catch((causa: unknown) => causa)

    expect(erro).toBeInstanceOf(ErroProntidao)
    expect((erro as ErroProntidao).codigo).toBe('falha_de_rede')
    expect((erro as ErroProntidao).status).toBeNull()
  })
})
