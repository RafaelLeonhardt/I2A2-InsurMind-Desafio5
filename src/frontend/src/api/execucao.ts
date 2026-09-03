import { clienteApi } from './clienteHttp'
import type { components } from './tipos-gerados'

/** Um marco de transição já persistido da execução (RUNNER-02). */
export type Marco = {
  marco: string
  causa: string | null
  criadoEm: string
}

/** Um item da amostra do público elegível formado. */
export type PreviaPublico = {
  nomeSegurado: string
  canal: string
}

/** Estado, marcos e, quando aplicável, prévia do público elegível de uma execução. */
export type Execucao = {
  id: string
  estado: string
  marcos: Marco[]
  publicoElegivelTotal: number | null
  publicoElegivelPrevia: PreviaPublico[]
  /** Execução terminal que originou esta nova tentativa; nula fora de uma correlação. */
  execucaoOrigemId: string | null
  /** Execuções criadas como nova tentativa a partir desta, sem mesclar históricos. */
  retentativas: string[]
}

type CorpoProblema = Partial<components['schemas']['ProblemaExecucao']>

type DadosErroExecucao = {
  codigo: string
  correlacaoId: string | null
  ocorrencia: string
  impacto: string
  proximaAcao: string
  status: number | null
}

/** Falha tipada de uma operação de execução, com ocorrência, impacto e próxima ação segura. */
export class ErroExecucao extends Error {
  readonly codigo: string
  readonly correlacaoId: string | null
  readonly ocorrencia: string
  readonly impacto: string
  readonly proximaAcao: string
  readonly status: number | null

  constructor(dados: DadosErroExecucao) {
    super(dados.ocorrencia)
    this.name = 'ErroExecucao'
    this.codigo = dados.codigo
    this.correlacaoId = dados.correlacaoId
    this.ocorrencia = dados.ocorrencia
    this.impacto = dados.impacto
    this.proximaAcao = dados.proximaAcao
    this.status = dados.status
  }
}

const FALHA_INESPERADA = {
  ocorrencia: 'A operação de execução não pôde ser concluída.',
  impacto: 'O acompanhamento da execução pode estar incompleto.',
  proximaAcao: 'Verifique se o backend local está disponível e tente novamente.',
}

const FALHA_DE_REDE: DadosErroExecucao = {
  codigo: 'falha_de_rede',
  correlacaoId: null,
  ocorrencia: 'Não foi possível falar com o backend local da Central Preventiva.',
  impacto: 'Nenhuma execução pôde ser iniciada ou consultada.',
  proximaAcao: 'Confirme que o backend está em execução em 127.0.0.1:8000 e tente de novo.',
  status: null,
}

/**
 * Converte o erro já desserializado pelo `openapi-fetch` em `ErroExecucao`.
 *
 * O corpo não é relido de `Response` (o `openapi-fetch` já consumiu o stream ao
 * desserializar `data`/`error`); reler geraria um erro de stream já consumido.
 */
function erroDeResultado(erro: unknown, status: number): ErroExecucao {
  const corpo = (erro ?? {}) as CorpoProblema
  return new ErroExecucao({
    codigo: corpo.codigo ?? 'falha_inesperada',
    correlacaoId: corpo.correlacao_id ?? null,
    ocorrencia: corpo.ocorrencia ?? FALHA_INESPERADA.ocorrencia,
    impacto: corpo.impacto ?? FALHA_INESPERADA.impacto,
    proximaAcao: corpo.proxima_acao ?? FALHA_INESPERADA.proximaAcao,
    status,
  })
}

function paraMarco(corpo: components['schemas']['RespostaMarco']): Marco {
  return {
    marco: corpo.marco,
    causa: corpo.causa,
    criadoEm: corpo.criado_em,
  }
}

function paraPreviaPublico(corpo: components['schemas']['RespostaPreviaPublico']): PreviaPublico {
  return {
    nomeSegurado: corpo.nome_segurado,
    canal: corpo.canal,
  }
}

function paraExecucao(corpo: components['schemas']['RespostaExecucao']): Execucao {
  return {
    id: corpo.id,
    estado: corpo.estado,
    marcos: corpo.marcos.map(paraMarco),
    publicoElegivelTotal: corpo.publico_elegivel_total,
    publicoElegivelPrevia: corpo.publico_elegivel_previa.map(paraPreviaPublico),
    execucaoOrigemId: corpo.execucao_origem_id,
    retentativas: corpo.retentativas,
  }
}

async function chamarIniciarExecucao(areaId: string) {
  return clienteApi.POST('/api/v1/execucoes', {
    params: { header: { 'Idempotency-Key': crypto.randomUUID() } },
    body: { area_id: areaId },
    fetch,
  })
}

async function chamarExecucao(execucaoId: string) {
  return clienteApi.GET('/api/v1/execucoes/{execucao_id}', {
    params: { path: { execucao_id: execucaoId } },
    fetch,
  })
}

/** Inicia, com `Idempotency-Key` nova, a orquestração completa de uma área monitorada. */
export async function iniciarExecucao(areaId: string): Promise<string> {
  let resultado: Awaited<ReturnType<typeof chamarIniciarExecucao>>
  try {
    resultado = await chamarIniciarExecucao(areaId)
  } catch {
    throw new ErroExecucao(FALHA_DE_REDE)
  }

  if (!resultado.response.ok || !resultado.data) {
    throw erroDeResultado(resultado.error, resultado.response.status)
  }

  return resultado.data.execucao_id
}

/** Consulta o estado, os marcos e, quando aplicável, a prévia do público de uma execução. */
export async function getExecucao(execucaoId: string): Promise<Execucao> {
  let resultado: Awaited<ReturnType<typeof chamarExecucao>>
  try {
    resultado = await chamarExecucao(execucaoId)
  } catch {
    throw new ErroExecucao(FALHA_DE_REDE)
  }

  if (!resultado.response.ok || !resultado.data) {
    throw erroDeResultado(resultado.error, resultado.response.status)
  }

  return paraExecucao(resultado.data)
}
