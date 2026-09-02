import { afterEach, describe, expect, it, vi } from 'vitest'
import { ErroExecucao, getExecucao, iniciarExecucao } from './execucao'

const EXECUCAO_ID = '11111111-1111-1111-1111-111111111111'
const AREA_ID = '22222222-2222-2222-2222-222222222222'

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

describe('iniciarExecucao', () => {
  it('devolve o execucao_id quando o backend responde 202', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(responder(202, { execucao_id: EXECUCAO_ID })),
    )

    await expect(iniciarExecucao(AREA_ID)).resolves.toBe(EXECUCAO_ID)
  })

  it('rejeita com ErroExecucao tipado quando o backend responde 404', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(responder(404, problema('area_monitorada_desconhecida'))),
    )

    const erro = await iniciarExecucao(AREA_ID).catch((causa: unknown) => causa)

    expect(erro).toBeInstanceOf(ErroExecucao)
    expect((erro as ErroExecucao).codigo).toBe('area_monitorada_desconhecida')
  })

  it('rejeita com ErroExecucao (falha de rede) quando fetch lança', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    const erro = await iniciarExecucao(AREA_ID).catch((causa: unknown) => causa)

    expect(erro).toBeInstanceOf(ErroExecucao)
    expect((erro as ErroExecucao).codigo).toBe('falha_de_rede')
  })
})

describe('getExecucao', () => {
  it('mapeia estado, marcos e prévia do público de snake_case para camelCase', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        responder(200, {
          id: EXECUCAO_ID,
          estado: 'aguardando_geracao',
          marcos: [
            { marco: 'coleta_concluida', causa: null, criado_em: '2026-08-30T12:00:00+00:00' },
            {
              marco: 'publico_elegivel_formado',
              causa: null,
              criado_em: '2026-08-30T12:00:05+00:00',
            },
          ],
          publico_elegivel_total: 1,
          publico_elegivel_previa: [{ nome_segurado: 'Maria Sintética', canal: 'whatsapp' }],
        }),
      ),
    )

    const execucao = await getExecucao(EXECUCAO_ID)

    expect(execucao).toEqual({
      id: EXECUCAO_ID,
      estado: 'aguardando_geracao',
      marcos: [
        { marco: 'coleta_concluida', causa: null, criadoEm: '2026-08-30T12:00:00+00:00' },
        {
          marco: 'publico_elegivel_formado',
          causa: null,
          criadoEm: '2026-08-30T12:00:05+00:00',
        },
      ],
      publicoElegivelTotal: 1,
      publicoElegivelPrevia: [{ nomeSegurado: 'Maria Sintética', canal: 'whatsapp' }],
    })
  })

  it('mapeia total e prévia nulos/vazios fora de aguardando_geracao', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        responder(200, {
          id: EXECUCAO_ID,
          estado: 'sem_risco',
          marcos: [{ marco: 'sem_risco', causa: null, criado_em: '2026-08-30T12:00:00+00:00' }],
          publico_elegivel_total: null,
          publico_elegivel_previa: [],
        }),
      ),
    )

    const execucao = await getExecucao(EXECUCAO_ID)

    expect(execucao.publicoElegivelTotal).toBeNull()
    expect(execucao.publicoElegivelPrevia).toEqual([])
  })

  it('rejeita com ErroExecucao tipado quando o backend responde 404', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(responder(404, problema('execucao_inexistente'))),
    )

    const erro = await getExecucao(EXECUCAO_ID).catch((causa: unknown) => causa)

    expect(erro).toBeInstanceOf(ErroExecucao)
    expect((erro as ErroExecucao).codigo).toBe('execucao_inexistente')
  })

  it('rejeita com ErroExecucao (falha de rede) quando fetch lança', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    const erro = await getExecucao(EXECUCAO_ID).catch((causa: unknown) => causa)

    expect(erro).toBeInstanceOf(ErroExecucao)
    expect((erro as ErroExecucao).codigo).toBe('falha_de_rede')
  })
})
