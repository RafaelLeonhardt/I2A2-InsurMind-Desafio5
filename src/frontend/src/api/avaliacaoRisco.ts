import { clienteApi } from './clienteHttp'
import type { components } from './tipos-gerados'

/** Um critério avaliado: operando, valor observado, resultado e justificativa. */
export type Criterio = {
  operando: string
  valorObservado: string
  atende: boolean
  justificativa: string
}

/** Snapshot público da avaliação de relevância meteorológica de uma execução. */
export type AvaliacaoRisco = {
  execucaoId: string
  eventoId: string
  regraId: string
  regraVersao: number
  relevante: boolean
  criterios: Criterio[]
  motivo: string
  criadoEm: string
}

type CorpoProblema = Partial<components['schemas']['ProblemaAvaliacaoRisco']>

type DadosErroAvaliacaoRisco = {
  codigo: string
  correlacaoId: string | null
  ocorrencia: string
  impacto: string
  proximaAcao: string
  status: number | null
}

/** Falha tipada ao consultar a avaliação de risco, com ocorrência, impacto e próxima ação segura. */
export class ErroAvaliacaoRisco extends Error {
  readonly codigo: string
  readonly correlacaoId: string | null
  readonly ocorrencia: string
  readonly impacto: string
  readonly proximaAcao: string
  readonly status: number | null

  constructor(dados: DadosErroAvaliacaoRisco) {
    super(dados.ocorrencia)
    this.name = 'ErroAvaliacaoRisco'
    this.codigo = dados.codigo
    this.correlacaoId = dados.correlacaoId
    this.ocorrencia = dados.ocorrencia
    this.impacto = dados.impacto
    this.proximaAcao = dados.proximaAcao
    this.status = dados.status
  }
}

const FALHA_INESPERADA = {
  ocorrencia: 'A consulta de avaliação de risco não pôde ser concluída.',
  impacto: 'O detalhe da decisão de risco não pode ser exibido no momento.',
  proximaAcao: 'Verifique se o backend local está disponível e tente novamente.',
}

const FALHA_DE_REDE: DadosErroAvaliacaoRisco = {
  codigo: 'falha_de_rede',
  correlacaoId: null,
  ocorrencia: 'Não foi possível falar com o backend local da Central Preventiva.',
  impacto: 'O detalhe da decisão de risco não pode ser exibido.',
  proximaAcao: 'Confirme que o backend está em execução em 127.0.0.1:8000 e tente de novo.',
  status: null,
}

/**
 * Converte o erro já desserializado pelo `openapi-fetch` em `ErroAvaliacaoRisco`.
 *
 * O corpo não é relido de `Response` (o `openapi-fetch` já consumiu o stream ao
 * desserializar `data`/`error`); reler geraria um erro de stream já consumido.
 */
function erroDeResultado(erro: unknown, status: number): ErroAvaliacaoRisco {
  const corpo = (erro ?? {}) as CorpoProblema
  return new ErroAvaliacaoRisco({
    codigo: corpo.codigo ?? 'falha_inesperada',
    correlacaoId: corpo.correlacao_id ?? null,
    ocorrencia: corpo.ocorrencia ?? FALHA_INESPERADA.ocorrencia,
    impacto: corpo.impacto ?? FALHA_INESPERADA.impacto,
    proximaAcao: corpo.proxima_acao ?? FALHA_INESPERADA.proximaAcao,
    status,
  })
}

function paraCriterio(corpo: components['schemas']['RespostaCriterio']): Criterio {
  return {
    operando: corpo.operando,
    valorObservado: corpo.valor_observado,
    atende: corpo.atende,
    justificativa: corpo.justificativa,
  }
}

function paraAvaliacaoRisco(
  corpo: components['schemas']['RespostaAvaliacaoRisco'],
): AvaliacaoRisco {
  return {
    execucaoId: corpo.execucao_id,
    eventoId: corpo.evento_id,
    regraId: corpo.regra_id,
    regraVersao: corpo.regra_versao,
    relevante: corpo.relevante,
    criterios: corpo.criterios.map(paraCriterio),
    motivo: corpo.motivo,
    criadoEm: corpo.criado_em,
  }
}

async function chamarAvaliacaoRisco(execucaoId: string) {
  return clienteApi.GET('/api/v1/execucoes/{execucao_id}/avaliacao-risco', {
    params: { path: { execucao_id: execucaoId } },
    fetch,
  })
}

/**
 * Consulta o detalhe da decisão de risco de uma execução, sem recalcular nada (RISCO-11).
 *
 * Devolve `null` quando a execução ainda não tem avaliação (404 `avaliacao_risco_inexistente`)
 * — um estado real de progresso da máquina de estados, não uma falha (RISCO-13). Qualquer
 * outra falha (rede, id malformado, erro do servidor) rejeita com `ErroAvaliacaoRisco`.
 */
export async function getAvaliacaoRisco(execucaoId: string): Promise<AvaliacaoRisco | null> {
  let resultado: Awaited<ReturnType<typeof chamarAvaliacaoRisco>>
  try {
    resultado = await chamarAvaliacaoRisco(execucaoId)
  } catch {
    throw new ErroAvaliacaoRisco(FALHA_DE_REDE)
  }

  if (resultado.response.status === 404) {
    return null
  }

  if (!resultado.response.ok || !resultado.data) {
    throw erroDeResultado(resultado.error, resultado.response.status)
  }

  return paraAvaliacaoRisco(resultado.data)
}
