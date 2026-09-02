import { afterEach, describe, expect, it, vi } from 'vitest'
import { ErroAvaliacaoRisco, getAvaliacaoRisco } from './avaliacaoRisco'

const EXECUCAO_ID = '11111111-1111-1111-1111-111111111111'

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

describe('getAvaliacaoRisco', () => {
  it('mapeia snake_case para camelCase quando o backend responde 200', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        responder(200, {
          execucao_id: EXECUCAO_ID,
          evento_id: '22222222-2222-2222-2222-222222222222',
          regra_id: '33333333-3333-3333-3333-333333333333',
          regra_versao: 1,
          relevante: true,
          criterios: [
            {
              operando: 'área aplicável',
              valor_observado: '9990001',
              atende: true,
              justificativa: 'Área do evento corresponde à área aplicável da regra (9990001).',
            },
          ],
          motivo: 'relevante',
          criado_em: '2026-08-30T12:00:00+00:00',
        }),
      ),
    )

    const avaliacao = await getAvaliacaoRisco(EXECUCAO_ID)

    expect(avaliacao).toEqual({
      execucaoId: EXECUCAO_ID,
      eventoId: '22222222-2222-2222-2222-222222222222',
      regraId: '33333333-3333-3333-3333-333333333333',
      regraVersao: 1,
      relevante: true,
      criterios: [
        {
          operando: 'área aplicável',
          valorObservado: '9990001',
          atende: true,
          justificativa: 'Área do evento corresponde à área aplicável da regra (9990001).',
        },
      ],
      motivo: 'relevante',
      criadoEm: '2026-08-30T12:00:00+00:00',
    })
  })

  it('resolve null quando o backend responde 404 (avaliação ainda não existe)', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(responder(404, problema('avaliacao_risco_inexistente'))),
    )

    await expect(getAvaliacaoRisco(EXECUCAO_ID)).resolves.toBeNull()
  })

  it('rejeita com ErroAvaliacaoRisco tipado quando o backend responde 422', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(responder(422, problema('execucao_id_invalido'))),
    )

    const erro = await getAvaliacaoRisco('nao-e-um-uuid').catch((causa: unknown) => causa)

    expect(erro).toBeInstanceOf(ErroAvaliacaoRisco)
    expect((erro as ErroAvaliacaoRisco).codigo).toBe('execucao_id_invalido')
    expect((erro as ErroAvaliacaoRisco).status).toBe(422)
  })

  it('rejeita com ErroAvaliacaoRisco (falha de rede) quando fetch lança', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    const erro = await getAvaliacaoRisco(EXECUCAO_ID).catch((causa: unknown) => causa)

    expect(erro).toBeInstanceOf(ErroAvaliacaoRisco)
    expect((erro as ErroAvaliacaoRisco).codigo).toBe('falha_de_rede')
    expect((erro as ErroAvaliacaoRisco).status).toBeNull()
  })
})
