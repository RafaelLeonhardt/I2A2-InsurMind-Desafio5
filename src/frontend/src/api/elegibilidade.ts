import { clienteApi } from './clienteHttp'
import type { components } from './tipos-gerados'

/** Um resultado de elegibilidade na listagem: segurado, apólice, localização, canal. */
export type ResumoElegibilidade = {
  id: string
  nomeSegurado: string
  apoliceId: string
  codigoIbgeArea: string
  canal: string
  elegivel: boolean
}

/** Quantidades e lista do público avaliado de uma execução (ELEG-08). */
export type Elegibilidade = {
  incluidos: number
  excluidos: number
  registros: ResumoElegibilidade[]
}

/** Um critério avaliado: operando, valor observado, resultado e justificativa. */
export type CriterioElegibilidade = {
  operando: string
  valorObservado: string
  atende: boolean
  justificativa: string
}

/** Explicação completa de um resultado de elegibilidade (ELEG-09). */
export type DetalheElegibilidade = {
  id: string
  execucaoId: string
  eventoId: string
  regraId: string
  regraVersao: number
  seguradoId: string
  nomeSegurado: string
  apoliceId: string
  codigoIbgeArea: string
  elegivel: boolean
  criterios: CriterioElegibilidade[]
  canal: string
  justificativa: string
  criadoEm: string
}

type CorpoProblema = Partial<components['schemas']['ProblemaElegibilidade']>

type DadosErroElegibilidade = {
  codigo: string
  correlacaoId: string | null
  ocorrencia: string
  impacto: string
  proximaAcao: string
  status: number | null
}

/** Falha tipada ao consultar a elegibilidade, com ocorrência, impacto e próxima ação segura. */
export class ErroElegibilidade extends Error {
  readonly codigo: string
  readonly correlacaoId: string | null
  readonly ocorrencia: string
  readonly impacto: string
  readonly proximaAcao: string
  readonly status: number | null

  constructor(dados: DadosErroElegibilidade) {
    super(dados.ocorrencia)
    this.name = 'ErroElegibilidade'
    this.codigo = dados.codigo
    this.correlacaoId = dados.correlacaoId
    this.ocorrencia = dados.ocorrencia
    this.impacto = dados.impacto
    this.proximaAcao = dados.proximaAcao
    this.status = dados.status
  }
}

const FALHA_INESPERADA = {
  ocorrencia: 'A consulta de elegibilidade não pôde ser concluída.',
  impacto: 'O público elegível não pode ser exibido no momento.',
  proximaAcao: 'Verifique se o backend local está disponível e tente novamente.',
}

const FALHA_DE_REDE: DadosErroElegibilidade = {
  codigo: 'falha_de_rede',
  correlacaoId: null,
  ocorrencia: 'Não foi possível falar com o backend local da Central Preventiva.',
  impacto: 'O público elegível não pode ser exibido.',
  proximaAcao: 'Confirme que o backend está em execução em 127.0.0.1:8000 e tente de novo.',
  status: null,
}

/**
 * Converte o erro já desserializado pelo `openapi-fetch` em `ErroElegibilidade`.
 *
 * O corpo não é relido de `Response` (o `openapi-fetch` já consumiu o stream ao
 * desserializar `data`/`error`); reler geraria um erro de stream já consumido.
 */
function erroDeResultado(erro: unknown, status: number): ErroElegibilidade {
  const corpo = (erro ?? {}) as CorpoProblema
  return new ErroElegibilidade({
    codigo: corpo.codigo ?? 'falha_inesperada',
    correlacaoId: corpo.correlacao_id ?? null,
    ocorrencia: corpo.ocorrencia ?? FALHA_INESPERADA.ocorrencia,
    impacto: corpo.impacto ?? FALHA_INESPERADA.impacto,
    proximaAcao: corpo.proxima_acao ?? FALHA_INESPERADA.proximaAcao,
    status,
  })
}

function paraResumo(corpo: components['schemas']['RespostaResumoElegibilidade']): ResumoElegibilidade {
  return {
    id: corpo.id,
    nomeSegurado: corpo.nome_segurado,
    apoliceId: corpo.apolice_id,
    codigoIbgeArea: corpo.codigo_ibge_area,
    canal: corpo.canal,
    elegivel: corpo.elegivel,
  }
}

function paraCriterio(
  corpo: components['schemas']['RespostaCriterioElegibilidade'],
): CriterioElegibilidade {
  return {
    operando: corpo.operando,
    valorObservado: corpo.valor_observado,
    atende: corpo.atende,
    justificativa: corpo.justificativa,
  }
}

function paraDetalhe(
  corpo: components['schemas']['RespostaDetalheElegibilidade'],
): DetalheElegibilidade {
  return {
    id: corpo.id,
    execucaoId: corpo.execucao_id,
    eventoId: corpo.evento_id,
    regraId: corpo.regra_id,
    regraVersao: corpo.regra_versao,
    seguradoId: corpo.segurado_id,
    nomeSegurado: corpo.nome_segurado,
    apoliceId: corpo.apolice_id,
    codigoIbgeArea: corpo.codigo_ibge_area,
    elegivel: corpo.elegivel,
    criterios: corpo.criterios.map(paraCriterio),
    canal: corpo.canal,
    justificativa: corpo.justificativa,
    criadoEm: corpo.criado_em,
  }
}

async function chamarElegibilidade(execucaoId: string) {
  return clienteApi.GET('/api/v1/execucoes/{execucao_id}/elegibilidade', {
    params: { path: { execucao_id: execucaoId } },
    fetch,
  })
}

async function chamarRegistroElegibilidade(execucaoId: string, registroId: string) {
  return clienteApi.GET('/api/v1/execucoes/{execucao_id}/elegibilidade/{registro_id}', {
    params: { path: { execucao_id: execucaoId, registro_id: registroId } },
    fetch,
  })
}

/** Consulta as quantidades e a lista do público elegível de uma execução (ELEG-08). */
export async function getElegibilidade(execucaoId: string): Promise<Elegibilidade> {
  let resultado: Awaited<ReturnType<typeof chamarElegibilidade>>
  try {
    resultado = await chamarElegibilidade(execucaoId)
  } catch {
    throw new ErroElegibilidade(FALHA_DE_REDE)
  }

  if (!resultado.response.ok || !resultado.data) {
    throw erroDeResultado(resultado.error, resultado.response.status)
  }

  return {
    incluidos: resultado.data.incluidos,
    excluidos: resultado.data.excluidos,
    registros: resultado.data.registros.map(paraResumo),
  }
}

/**
 * Consulta a explicação completa de um resultado de elegibilidade (ELEG-09).
 *
 * Devolve `null` quando o resultado não existe para a execução (404), sem recalcular
 * nada no frontend. Qualquer outra falha rejeita com `ErroElegibilidade`.
 */
export async function getDetalheElegibilidade(
  execucaoId: string,
  registroId: string,
): Promise<DetalheElegibilidade | null> {
  let resultado: Awaited<ReturnType<typeof chamarRegistroElegibilidade>>
  try {
    resultado = await chamarRegistroElegibilidade(execucaoId, registroId)
  } catch {
    throw new ErroElegibilidade(FALHA_DE_REDE)
  }

  if (resultado.response.status === 404) {
    return null
  }

  if (!resultado.response.ok || !resultado.data) {
    throw erroDeResultado(resultado.error, resultado.response.status)
  }

  return paraDetalhe(resultado.data)
}
