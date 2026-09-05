import { clienteApi } from './clienteHttp'
import type { components } from './tipos-gerados'

/** Os dados da apólice exibíveis ao segurado ativo. */
export type ApoliceSegurado = {
  numero: string
  tipo: string
  situacao: string
  estadoObjetivo: string
  vigenciaInicio: string
  vigenciaFim: string
  enderecoRiscoSintetico: string
  coberturas: string[]
  canalPreferido: string
  participaDeAlertas: boolean
}

/** Um critério comparado pela regra determinística, relevante à apólice. */
export type CriterioApolice = {
  operando: string
  valorObservado: string
  atende: boolean
  justificativa: string
}

/** A explicação de critérios relevantes à apólice, do snapshot de uma execução. */
export type ExplicacaoApolice = {
  elegibilidadeId: string
  criterios: CriterioApolice[]
}

type CorpoProblema = Partial<components['schemas']['ProblemaApoliceSegurado']>

type DadosErroApoliceSegurado = {
  codigo: string
  correlacaoId: string | null
  ocorrencia: string
  impacto: string
  proximaAcao: string
  status: number | null
}

/** Falha tipada da apólice/explicação, com ocorrência, impacto e próxima ação segura. */
export class ErroApoliceSegurado extends Error {
  readonly codigo: string
  readonly correlacaoId: string | null
  readonly ocorrencia: string
  readonly impacto: string
  readonly proximaAcao: string
  readonly status: number | null

  constructor(dados: DadosErroApoliceSegurado) {
    super(dados.ocorrencia)
    this.name = 'ErroApoliceSegurado'
    this.codigo = dados.codigo
    this.correlacaoId = dados.correlacaoId
    this.ocorrencia = dados.ocorrencia
    this.impacto = dados.impacto
    this.proximaAcao = dados.proximaAcao
    this.status = dados.status
  }
}

const FALHA_INESPERADA = {
  ocorrencia: 'A apólice não pôde ser consultada.',
  impacto: 'Os dados da apólice podem estar desatualizados ou indisponíveis.',
  proximaAcao: 'Verifique se o backend local está disponível e tente novamente.',
}

const FALHA_DE_REDE: DadosErroApoliceSegurado = {
  codigo: 'falha_de_rede',
  correlacaoId: null,
  ocorrencia: 'Não foi possível falar com o backend local da Central Preventiva.',
  impacto: 'Nenhum dado de apólice pôde ser exibido.',
  proximaAcao: 'Confirme que o backend está em execução em 127.0.0.1:8000 e tente de novo.',
  status: null,
}

function erroDeResultado(erro: unknown, status: number): ErroApoliceSegurado {
  const corpo = (erro ?? {}) as CorpoProblema
  return new ErroApoliceSegurado({
    codigo: corpo.codigo ?? 'falha_inesperada',
    correlacaoId: corpo.correlacao_id ?? null,
    ocorrencia: corpo.ocorrencia ?? FALHA_INESPERADA.ocorrencia,
    impacto: corpo.impacto ?? FALHA_INESPERADA.impacto,
    proximaAcao: corpo.proxima_acao ?? FALHA_INESPERADA.proximaAcao,
    status,
  })
}

function paraApolice(corpo: components['schemas']['RespostaApolice']): ApoliceSegurado {
  return {
    numero: corpo.numero,
    tipo: corpo.tipo,
    situacao: corpo.situacao,
    estadoObjetivo: corpo.estado_objetivo,
    vigenciaInicio: corpo.vigencia_inicio,
    vigenciaFim: corpo.vigencia_fim,
    enderecoRiscoSintetico: corpo.endereco_risco_sintetico,
    coberturas: corpo.coberturas,
    canalPreferido: corpo.canal_preferido,
    participaDeAlertas: corpo.participa_de_alertas,
  }
}

function paraCriterio(
  corpo: components['schemas']['RespostaCriterioApolice'],
): CriterioApolice {
  return {
    operando: corpo.operando,
    valorObservado: corpo.valor_observado,
    atende: corpo.atende,
    justificativa: corpo.justificativa,
  }
}

function paraExplicacao(
  corpo: components['schemas']['RespostaExplicacaoApolice'],
): ExplicacaoApolice {
  return {
    elegibilidadeId: corpo.elegibilidade_id,
    criterios: corpo.criterios.map(paraCriterio),
  }
}

async function chamarApolice(seguradoId: string) {
  return clienteApi.GET('/api/v1/segurados/{segurado_id}/apolice', {
    params: { path: { segurado_id: seguradoId } },
    fetch,
  })
}

async function chamarExplicacao(seguradoId: string, elegibilidadeId: string) {
  return clienteApi.GET(
    '/api/v1/segurados/{segurado_id}/apolice/explicacao/{elegibilidade_id}',
    {
      params: { path: { segurado_id: seguradoId, elegibilidade_id: elegibilidadeId } },
      fetch,
    },
  )
}

/** Consulta a apólice do segurado, ou lança `ErroApoliceSegurado` (`status` 404 se não
 * houver apólice ou não pertencer ao segurado). */
export async function getApolice(seguradoId: string): Promise<ApoliceSegurado> {
  let resultado: Awaited<ReturnType<typeof chamarApolice>>
  try {
    resultado = await chamarApolice(seguradoId)
  } catch {
    throw new ErroApoliceSegurado(FALHA_DE_REDE)
  }

  if (!resultado.response.ok || !resultado.data) {
    throw erroDeResultado(resultado.error, resultado.response.status)
  }

  return paraApolice(resultado.data)
}

/** Consulta a explicação de critérios de uma execução, ou lança `ErroApoliceSegurado`
 * (`status` 404 se a elegibilidade não existir ou não pertencer ao segurado). */
export async function getExplicacaoApolice(
  seguradoId: string,
  elegibilidadeId: string,
): Promise<ExplicacaoApolice> {
  let resultado: Awaited<ReturnType<typeof chamarExplicacao>>
  try {
    resultado = await chamarExplicacao(seguradoId, elegibilidadeId)
  } catch {
    throw new ErroApoliceSegurado(FALHA_DE_REDE)
  }

  if (!resultado.response.ok || !resultado.data) {
    throw erroDeResultado(resultado.error, resultado.response.status)
  }

  return paraExplicacao(resultado.data)
}
