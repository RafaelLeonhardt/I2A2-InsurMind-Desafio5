import { clienteApi } from './clienteHttp'
import type { AlertaSegurado } from './alertaSegurado'
import type { components } from './tipos-gerados'

/** Um marco da linha do tempo de uma execução (4.4), reusado no detalhe do alerta. */
export type MarcoLinhaDoTempo = {
  timestamp: string
  ator: string
  acao: string
  resultado: string
  correlacao: string
  tipo: string
  mensagemId: string | null
}

/** As três classificações possíveis de um alerta. */
export type ClassificacaoAlerta = 'ativo' | 'anterior' | 'ainda_nao_simulado'

/** Um item da lista de alertas: o alerta e sua classificação. */
export type ItemAlerta = {
  alerta: AlertaSegurado
  classificacao: ClassificacaoAlerta
}

/** O detalhe completo de um alerta do segurado. */
export type DetalheAlerta = {
  alerta: AlertaSegurado
  classificacao: ClassificacaoAlerta
  apoliceId: string
  justificativa: string
  linhaDoTempo: MarcoLinhaDoTempo[]
}

type CorpoProblema = Partial<components['schemas']['ProblemaListaAlertas']>

type DadosErroListaAlertas = {
  codigo: string
  correlacaoId: string | null
  ocorrencia: string
  impacto: string
  proximaAcao: string
  status: number | null
}

/** Falha tipada da lista/detalhe de alertas, com ocorrência, impacto e próxima ação segura. */
export class ErroListaAlertas extends Error {
  readonly codigo: string
  readonly correlacaoId: string | null
  readonly ocorrencia: string
  readonly impacto: string
  readonly proximaAcao: string
  readonly status: number | null

  constructor(dados: DadosErroListaAlertas) {
    super(dados.ocorrencia)
    this.name = 'ErroListaAlertas'
    this.codigo = dados.codigo
    this.correlacaoId = dados.correlacaoId
    this.ocorrencia = dados.ocorrencia
    this.impacto = dados.impacto
    this.proximaAcao = dados.proximaAcao
    this.status = dados.status
  }
}

const FALHA_INESPERADA = {
  ocorrencia: 'Os alertas não puderam ser consultados.',
  impacto: 'A lista de alertas pode estar desatualizada ou indisponível.',
  proximaAcao: 'Verifique se o backend local está disponível e tente novamente.',
}

const FALHA_DE_REDE: DadosErroListaAlertas = {
  codigo: 'falha_de_rede',
  correlacaoId: null,
  ocorrencia: 'Não foi possível falar com o backend local da Central Preventiva.',
  impacto: 'Nenhum alerta pôde ser exibido.',
  proximaAcao: 'Confirme que o backend está em execução em 127.0.0.1:8000 e tente de novo.',
  status: null,
}

function erroDeResultado(erro: unknown, status: number): ErroListaAlertas {
  const corpo = (erro ?? {}) as CorpoProblema
  return new ErroListaAlertas({
    codigo: corpo.codigo ?? 'falha_inesperada',
    correlacaoId: corpo.correlacao_id ?? null,
    ocorrencia: corpo.ocorrencia ?? FALHA_INESPERADA.ocorrencia,
    impacto: corpo.impacto ?? FALHA_INESPERADA.impacto,
    proximaAcao: corpo.proxima_acao ?? FALHA_INESPERADA.proximaAcao,
    status,
  })
}

function paraAlerta(corpo: components['schemas']['RespostaAlerta']): AlertaSegurado {
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
    entregaSimuladaId: corpo.entrega_simulada_id,
  }
}

function paraItem(corpo: components['schemas']['RespostaItemAlerta']): ItemAlerta {
  return {
    alerta: paraAlerta(corpo.alerta),
    classificacao: corpo.classificacao as ClassificacaoAlerta,
  }
}

function paraMarco(
  corpo: components['schemas']['RespostaMarcoLinhaDoTempo'],
): MarcoLinhaDoTempo {
  return {
    timestamp: corpo.timestamp,
    ator: corpo.ator,
    acao: corpo.acao,
    resultado: corpo.resultado,
    correlacao: corpo.correlacao,
    tipo: corpo.tipo,
    mensagemId: corpo.mensagem_id,
  }
}

function paraDetalhe(corpo: components['schemas']['RespostaDetalheAlerta']): DetalheAlerta {
  return {
    alerta: paraAlerta(corpo.alerta),
    classificacao: corpo.classificacao as ClassificacaoAlerta,
    apoliceId: corpo.apolice_id,
    justificativa: corpo.justificativa,
    linhaDoTempo: corpo.linha_do_tempo.map(paraMarco),
  }
}

async function chamarLista(seguradoId: string) {
  return clienteApi.GET('/api/v1/segurados/{segurado_id}/alertas', {
    params: { path: { segurado_id: seguradoId } },
    fetch,
  })
}

async function chamarDetalhe(seguradoId: string, elegibilidadeId: string) {
  return clienteApi.GET('/api/v1/segurados/{segurado_id}/alertas/{elegibilidade_id}', {
    params: { path: { segurado_id: seguradoId, elegibilidade_id: elegibilidadeId } },
    fetch,
  })
}

/** Lista todos os alertas do segurado, mais recentes primeiro, com sua classificação. */
export async function getListaAlertas(seguradoId: string): Promise<ItemAlerta[]> {
  let resultado: Awaited<ReturnType<typeof chamarLista>>
  try {
    resultado = await chamarLista(seguradoId)
  } catch {
    throw new ErroListaAlertas(FALHA_DE_REDE)
  }

  if (!resultado.response.ok || !resultado.data) {
    throw erroDeResultado(resultado.error, resultado.response.status)
  }

  return resultado.data.alertas.map(paraItem)
}

/** Consulta o detalhe de um alerta, ou lança `ErroListaAlertas` com `status` 404 se o
 * alerta não existir ou não pertencer ao segurado. */
export async function getDetalheAlerta(
  seguradoId: string,
  elegibilidadeId: string,
): Promise<DetalheAlerta> {
  let resultado: Awaited<ReturnType<typeof chamarDetalhe>>
  try {
    resultado = await chamarDetalhe(seguradoId, elegibilidadeId)
  } catch {
    throw new ErroListaAlertas(FALHA_DE_REDE)
  }

  if (!resultado.response.ok || !resultado.data) {
    throw erroDeResultado(resultado.error, resultado.response.status)
  }

  return paraDetalhe(resultado.data)
}
