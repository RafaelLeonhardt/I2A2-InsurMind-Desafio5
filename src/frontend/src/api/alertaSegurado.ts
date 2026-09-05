import { clienteApi } from './clienteHttp'
import type { components } from './tipos-gerados'

/** O alerta mais relevante exibível ao segurado ativo. */
export type AlertaSegurado = {
  elegibilidadeId: string
  eventoTipo: string
  severidade: string
  periodoInicio: string
  periodoFim: string
  localizacao: string
  impactosEsperados: string[]
  recomendacoes: string[]
  origem: string
  instanteObservado: string
  fonteDegradada: boolean
}

type CorpoProblema = Partial<components['schemas']['ProblemaAlertaSegurado']>

type DadosErroAlertaSegurado = {
  codigo: string
  correlacaoId: string | null
  ocorrencia: string
  impacto: string
  proximaAcao: string
  status: number | null
}

/** Falha tipada da consulta do alerta, com ocorrência, impacto e próxima ação segura. */
export class ErroAlertaSegurado extends Error {
  readonly codigo: string
  readonly correlacaoId: string | null
  readonly ocorrencia: string
  readonly impacto: string
  readonly proximaAcao: string
  readonly status: number | null

  constructor(dados: DadosErroAlertaSegurado) {
    super(dados.ocorrencia)
    this.name = 'ErroAlertaSegurado'
    this.codigo = dados.codigo
    this.correlacaoId = dados.correlacaoId
    this.ocorrencia = dados.ocorrencia
    this.impacto = dados.impacto
    this.proximaAcao = dados.proximaAcao
    this.status = dados.status
  }
}

const FALHA_INESPERADA = {
  ocorrencia: 'O alerta mais relevante não pôde ser consultado.',
  impacto: 'A Visão geral pode estar desatualizada ou indisponível.',
  proximaAcao: 'Verifique se o backend local está disponível e tente novamente.',
}

const FALHA_DE_REDE: DadosErroAlertaSegurado = {
  codigo: 'falha_de_rede',
  correlacaoId: null,
  ocorrencia: 'Não foi possível falar com o backend local da Central Preventiva.',
  impacto: 'Nenhum alerta pôde ser exibido.',
  proximaAcao: 'Confirme que o backend está em execução em 127.0.0.1:8000 e tente de novo.',
  status: null,
}

function erroDeResultado(erro: unknown, status: number): ErroAlertaSegurado {
  const corpo = (erro ?? {}) as CorpoProblema
  return new ErroAlertaSegurado({
    codigo: corpo.codigo ?? 'falha_inesperada',
    correlacaoId: corpo.correlacao_id ?? null,
    ocorrencia: corpo.ocorrencia ?? FALHA_INESPERADA.ocorrencia,
    impacto: corpo.impacto ?? FALHA_INESPERADA.impacto,
    proximaAcao: corpo.proxima_acao ?? FALHA_INESPERADA.proximaAcao,
    status,
  })
}

function paraAlertaSegurado(
  corpo: components['schemas']['RespostaAlerta'],
): AlertaSegurado {
  return {
    elegibilidadeId: corpo.elegibilidade_id,
    eventoTipo: corpo.evento_tipo,
    severidade: corpo.severidade,
    periodoInicio: corpo.periodo_inicio,
    periodoFim: corpo.periodo_fim,
    localizacao: corpo.localizacao,
    impactosEsperados: corpo.impactos_esperados,
    recomendacoes: corpo.recomendacoes,
    origem: corpo.origem,
    instanteObservado: corpo.instante_observado,
    fonteDegradada: corpo.fonte_degradada,
  }
}

async function chamarAlerta(seguradoId: string) {
  return clienteApi.GET('/api/v1/segurados/{segurado_id}/alerta-mais-relevante', {
    params: { path: { segurado_id: seguradoId } },
    fetch,
  })
}

/** Consulta o alerta mais relevante do segurado, ou `null` se não houver nenhum. */
export async function getAlertaMaisRelevante(seguradoId: string): Promise<AlertaSegurado | null> {
  let resultado: Awaited<ReturnType<typeof chamarAlerta>>
  try {
    resultado = await chamarAlerta(seguradoId)
  } catch {
    throw new ErroAlertaSegurado(FALHA_DE_REDE)
  }

  if (!resultado.response.ok || !resultado.data) {
    throw erroDeResultado(resultado.error, resultado.response.status)
  }

  return resultado.data.alerta ? paraAlertaSegurado(resultado.data.alerta) : null
}
