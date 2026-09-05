import { clienteApi } from './clienteHttp'
import type { components } from './tipos-gerados'

/** A primeira visualização registrada de um comunicado. */
export type VisualizacaoComunicado = {
  id: string
  visualizadaEm: string
}

/** O comunicado exibível ao segurado sintético: conteúdo, canal e visualização. */
export type Comunicado = {
  entregaSimuladaId: string
  mensagemId: string
  canal: string
  assunto: string | null
  corpo: string
  rotulo: string
  criadoEm: string
  visualizacao: VisualizacaoComunicado | null
}

type CorpoProblema = Partial<components['schemas']['ProblemaComunicado']>

type DadosErroComunicado = {
  codigo: string
  correlacaoId: string | null
  ocorrencia: string
  impacto: string
  proximaAcao: string
  status: number | null
}

/** Falha tipada do comunicado, com ocorrência, impacto e próxima ação segura. */
export class ErroComunicado extends Error {
  readonly codigo: string
  readonly correlacaoId: string | null
  readonly ocorrencia: string
  readonly impacto: string
  readonly proximaAcao: string
  readonly status: number | null

  constructor(dados: DadosErroComunicado) {
    super(dados.ocorrencia)
    this.name = 'ErroComunicado'
    this.codigo = dados.codigo
    this.correlacaoId = dados.correlacaoId
    this.ocorrencia = dados.ocorrencia
    this.impacto = dados.impacto
    this.proximaAcao = dados.proximaAcao
    this.status = dados.status
  }
}

const FALHA_INESPERADA = {
  ocorrencia: 'A operação sobre o comunicado não pôde ser concluída.',
  impacto: 'O comunicado pode estar indisponível ou desatualizado.',
  proximaAcao: 'Verifique se o backend local está disponível e tente novamente.',
}

const FALHA_DE_REDE: DadosErroComunicado = {
  codigo: 'falha_de_rede',
  correlacaoId: null,
  ocorrencia: 'Não foi possível falar com o backend local da Central Preventiva.',
  impacto: 'Nenhum comunicado pôde ser exibido.',
  proximaAcao: 'Confirme que o backend está em execução em 127.0.0.1:8000 e tente de novo.',
  status: null,
}

function erroDeResultado(erro: unknown, status: number): ErroComunicado {
  const corpo = (erro ?? {}) as CorpoProblema
  return new ErroComunicado({
    codigo: corpo.codigo ?? 'falha_inesperada',
    correlacaoId: corpo.correlacao_id ?? null,
    ocorrencia: corpo.ocorrencia ?? FALHA_INESPERADA.ocorrencia,
    impacto: corpo.impacto ?? FALHA_INESPERADA.impacto,
    proximaAcao: corpo.proxima_acao ?? FALHA_INESPERADA.proximaAcao,
    status,
  })
}

function paraVisualizacao(
  corpo: components['schemas']['RespostaVisualizacaoComunicado'],
): VisualizacaoComunicado {
  return { id: corpo.id, visualizadaEm: corpo.visualizada_em }
}

function paraComunicado(corpo: components['schemas']['RespostaComunicado']): Comunicado {
  return {
    entregaSimuladaId: corpo.entrega_simulada_id,
    mensagemId: corpo.mensagem_id,
    canal: corpo.canal,
    assunto: corpo.assunto,
    corpo: corpo.corpo,
    rotulo: corpo.rotulo,
    criadoEm: corpo.criado_em,
    visualizacao: corpo.visualizacao ? paraVisualizacao(corpo.visualizacao) : null,
  }
}

async function chamarComunicado(seguradoId: string, entregaSimuladaId: string) {
  return clienteApi.GET(
    '/api/v1/segurados/{segurado_id}/comunicados/{entrega_simulada_id}',
    {
      params: {
        path: { segurado_id: seguradoId, entrega_simulada_id: entregaSimuladaId },
      },
      fetch,
    },
  )
}

async function chamarVisualizacao(seguradoId: string, entregaSimuladaId: string) {
  return clienteApi.POST(
    '/api/v1/segurados/{segurado_id}/comunicados/{entrega_simulada_id}/visualizacao',
    {
      params: {
        path: { segurado_id: seguradoId, entrega_simulada_id: entregaSimuladaId },
      },
      fetch,
    },
  )
}

/** Consulta o comunicado de uma entrega simulada, sem registrar visualização nenhuma. */
export async function getComunicado(
  seguradoId: string,
  entregaSimuladaId: string,
): Promise<Comunicado> {
  let resultado: Awaited<ReturnType<typeof chamarComunicado>>
  try {
    resultado = await chamarComunicado(seguradoId, entregaSimuladaId)
  } catch {
    throw new ErroComunicado(FALHA_DE_REDE)
  }

  if (!resultado.response.ok || !resultado.data) {
    throw erroDeResultado(resultado.error, resultado.response.status)
  }

  return paraComunicado(resultado.data)
}

/**
 * Registra a primeira visualização do comunicado.
 *
 * Só deve ser chamada depois que o conteúdo do comunicado já foi renderizado com sucesso na
 * tela — nunca no carregamento inicial da página (Tech Decision da História 4.3).
 */
export async function registrarVisualizacaoComunicado(
  seguradoId: string,
  entregaSimuladaId: string,
): Promise<VisualizacaoComunicado> {
  let resultado: Awaited<ReturnType<typeof chamarVisualizacao>>
  try {
    resultado = await chamarVisualizacao(seguradoId, entregaSimuladaId)
  } catch {
    throw new ErroComunicado(FALHA_DE_REDE)
  }

  if (!resultado.response.ok || !resultado.data) {
    throw erroDeResultado(resultado.error, resultado.response.status)
  }

  return paraVisualizacao(resultado.data)
}
