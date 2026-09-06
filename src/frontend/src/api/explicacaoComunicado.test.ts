import { afterEach, describe, expect, it, vi } from 'vitest'
import { ErroExplicacaoComunicado, getExplicacaoComunicado } from './explicacaoComunicado'

const SEGURADO_ID = '11111111-1111-1111-1111-111111111111'
const ENTREGA_ID = '22222222-2222-2222-2222-222222222222'

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

describe('getExplicacaoComunicado', () => {
  it('mapeia todos os campos de snake_case para camelCase, com valores distintos entre si', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        responder(200, {
          entrega_simulada_id: ENTREGA_ID,
          mensagem_id: '33333333-3333-3333-3333-333333333333',
          execucao_id: '44444444-4444-4444-4444-444444444444',
          execucao_origem_id: '55555555-5555-5555-5555-555555555555',
          evento_e_regra: {
            origem: 'deterministica',
            evento: {
              id: '66666666-6666-6666-6666-666666666666',
              tipo: 'granizo',
              area: '9990001',
              proveniencia: 'sintetico',
            },
            regra_id: '77777777-7777-7777-7777-777777777777',
            regra_versao: 9,
          },
          contexto: {
            categorias_usadas: ['evento', 'canal'],
            categorias_nao_usadas: ['documentos'],
          },
          agente: {
            origem: 'agente',
            status: 'completa',
            causa_excecao: null,
            tentativas: [
              {
                numero_tentativa: 1,
                origem_regeneracao: 'primeira_tentativa',
                corpo: 'Corpo gerado da tentativa.',
                assunto: 'Assunto gerado da tentativa',
                modelo_redator: 'gpt-4o-mini',
                avaliacao_critica: {
                  aprovada: false,
                  motivos: ['tom'],
                  agente: 'critico',
                  modelo: 'gpt-4o',
                  duracao_ms: 123.5,
                },
                decisoes_humanas: [
                  { resultado: 'regenerar', justificativa: 'Tom alarmista.' },
                ],
              },
            ],
          },
          apresentacao_simulada: {
            canal: 'sms',
            assunto: null,
            corpo: 'Corpo da apresentação simulada.',
            rotulo: 'simulada',
          },
        }),
      ),
    )

    const explicacao = await getExplicacaoComunicado(SEGURADO_ID, ENTREGA_ID)

    expect(explicacao).toEqual({
      entregaSimuladaId: ENTREGA_ID,
      mensagemId: '33333333-3333-3333-3333-333333333333',
      execucaoId: '44444444-4444-4444-4444-444444444444',
      execucaoOrigemId: '55555555-5555-5555-5555-555555555555',
      eventoERegra: {
        origem: 'deterministica',
        evento: {
          id: '66666666-6666-6666-6666-666666666666',
          tipo: 'granizo',
          area: '9990001',
          proveniencia: 'sintetico',
        },
        regraId: '77777777-7777-7777-7777-777777777777',
        regraVersao: 9,
      },
      contexto: {
        categoriasUsadas: ['evento', 'canal'],
        categoriasNaoUsadas: ['documentos'],
      },
      agente: {
        origem: 'agente',
        status: 'completa',
        causaExcecao: null,
        tentativas: [
          {
            numeroTentativa: 1,
            origemRegeneracao: 'primeira_tentativa',
            corpo: 'Corpo gerado da tentativa.',
            assunto: 'Assunto gerado da tentativa',
            modeloRedator: 'gpt-4o-mini',
            avaliacaoCritica: {
              aprovada: false,
              motivos: ['tom'],
              agente: 'critico',
              modelo: 'gpt-4o',
              duracaoMs: 123.5,
            },
            decisoesHumanas: [{ resultado: 'regenerar', justificativa: 'Tom alarmista.' }],
          },
        ],
      },
      apresentacaoSimulada: {
        canal: 'sms',
        assunto: null,
        corpo: 'Corpo da apresentação simulada.',
        rotulo: 'simulada',
      },
    })
  })

  it('mapeia execucaoOrigemId e contexto nulos quando ausentes', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        responder(200, {
          entrega_simulada_id: ENTREGA_ID,
          mensagem_id: '33333333-3333-3333-3333-333333333333',
          execucao_id: '44444444-4444-4444-4444-444444444444',
          execucao_origem_id: null,
          evento_e_regra: {
            origem: 'deterministica',
            evento: null,
            regra_id: '77777777-7777-7777-7777-777777777777',
            regra_versao: 1,
          },
          contexto: null,
          agente: {
            origem: 'agente',
            status: 'excecao',
            causa_excecao: 'falha_integracao_ia',
            tentativas: [],
          },
          apresentacao_simulada: null,
        }),
      ),
    )

    const explicacao = await getExplicacaoComunicado(SEGURADO_ID, ENTREGA_ID)

    expect(explicacao.execucaoOrigemId).toBeNull()
    expect(explicacao.contexto).toBeNull()
    expect(explicacao.eventoERegra.evento).toBeNull()
    expect(explicacao.agente.status).toBe('excecao')
    expect(explicacao.agente.causaExcecao).toBe('falha_integracao_ia')
    expect(explicacao.apresentacaoSimulada).toBeNull()
  })

  it('rejeita com ErroExplicacaoComunicado (status 404) quando o backend responde 404', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(responder(404, problema('explicacao_nao_encontrada'))),
    )

    const erro = await getExplicacaoComunicado(SEGURADO_ID, ENTREGA_ID).catch(
      (causa: unknown) => causa,
    )

    expect(erro).toBeInstanceOf(ErroExplicacaoComunicado)
    expect((erro as ErroExplicacaoComunicado).codigo).toBe('explicacao_nao_encontrada')
    expect((erro as ErroExplicacaoComunicado).status).toBe(404)
  })

  it('rejeita com ErroExplicacaoComunicado (falha de rede) quando fetch lança', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    const erro = await getExplicacaoComunicado(SEGURADO_ID, ENTREGA_ID).catch(
      (causa: unknown) => causa,
    )

    expect(erro).toBeInstanceOf(ErroExplicacaoComunicado)
    expect((erro as ErroExplicacaoComunicado).codigo).toBe('falha_de_rede')
  })
})
