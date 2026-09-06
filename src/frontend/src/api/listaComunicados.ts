import { clienteApi } from './clienteHttp'
import type { VisualizacaoComunicado } from './comunicado'
import type { components } from './tipos-gerados'

/** Um item da lista de comunicados: canal, assunto/resumo, data e visualização. */
export type ItemComunicado = {
  entregaSimuladaId: string
  mensagemId: string
  canal: string
  assuntoOuResumo: string
  criadoEm: string
  visualizacao: VisualizacaoComunicado | null
}

type CorpoProblema = Partial<components['schemas']['ProblemaListaComunicados']>

type DadosErroListaComunicados = {
  codigo: string
  correlacaoId: string | null
  ocorrencia: string
  impacto: string
  proximaAcao: string
  status: number | null
}

/** Falha tipada da lista de comunicados, com ocorrência, impacto e próxima ação segura. */
export class ErroListaComunicados extends Error {
  readonly codigo: string
  readonly correlacaoId: string | null
  readonly ocorrencia: string
  readonly impacto: string
  readonly proximaAcao: string
  readonly status: number | null

  constructor(dados: DadosErroListaComunicados) {
    super(dados.ocorrencia)
    this.name = 'ErroListaComunicados'
    this.codigo = dados.codigo
    this.correlacaoId = dados.correlacaoId
    this.ocorrencia = dados.ocorrencia
    this.impacto = dados.impacto
    this.proximaAcao = dados.proximaAcao
    this.status = dados.status
  }
}

const FALHA_INESPERADA = {
  ocorrencia: 'Os comunicados não puderam ser consultados.',
  impacto: 'A lista de comunicados pode estar desatualizada ou indisponível.',
  proximaAcao: 'Verifique se o backend local está disponível e tente novamente.',
}

const FALHA_DE_REDE: DadosErroListaComunicados = {
  codigo: 'falha_de_rede',
  correlacaoId: null,
  ocorrencia: 'Não foi possível falar com o backend local da Central Preventiva.',
  impacto: 'Nenhum comunicado pôde ser exibido.',
  proximaAcao: 'Confirme que o backend está em execução em 127.0.0.1:8000 e tente de novo.',
  status: null,
}

function erroDeResultado(erro: unknown, status: number): ErroListaComunicados {
  const corpo = (erro ?? {}) as CorpoProblema
  return new ErroListaComunicados({
    codigo: corpo.codigo ?? 'falha_inesperada',
    correlacaoId: corpo.correlacao_id ?? null,
    ocorrencia: corpo.ocorrencia ?? FALHA_INESPERADA.ocorrencia,
    impacto: corpo.impacto ?? FALHA_INESPERADA.impacto,
    proximaAcao: corpo.proxima_acao ?? FALHA_INESPERADA.proximaAcao,
    status,
  })
}

function paraItem(corpo: components['schemas']['RespostaItemComunicado']): ItemComunicado {
  return {
    entregaSimuladaId: corpo.entrega_simulada_id,
    mensagemId: corpo.mensagem_id,
    canal: corpo.canal,
    assuntoOuResumo: corpo.assunto_ou_resumo,
    criadoEm: corpo.criado_em,
    visualizacao: corpo.visualizacao
      ? { id: corpo.visualizacao.id, visualizadaEm: corpo.visualizacao.visualizada_em }
      : null,
  }
}

async function chamarLista(seguradoId: string) {
  return clienteApi.GET('/api/v1/segurados/{segurado_id}/comunicados', {
    params: { path: { segurado_id: seguradoId } },
    fetch,
  })
}

/** Lista todos os comunicados do segurado, mais antigos primeiro. */
export async function getListaComunicados(seguradoId: string): Promise<ItemComunicado[]> {
  let resultado: Awaited<ReturnType<typeof chamarLista>>
  try {
    resultado = await chamarLista(seguradoId)
  } catch {
    throw new ErroListaComunicados(FALHA_DE_REDE)
  }

  if (!resultado.response.ok || !resultado.data) {
    throw erroDeResultado(resultado.error, resultado.response.status)
  }

  return resultado.data.comunicados.map(paraItem)
}
