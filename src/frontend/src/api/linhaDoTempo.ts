import { clienteApi } from './clienteHttp'
import type { components } from './tipos-gerados'

/** Um evento normalizado da cronologia, de qualquer uma das fontes agregadas. */
export type MarcoLinhaDoTempo = {
  timestamp: string
  ator: string
  acao: string
  resultado: string
  correlacao: string
  tipo: string
  mensagemId: string | null
}

/** A cronologia completa de uma execução, com a cadeia de correlação. */
export type LinhaDoTempo = {
  execucaoId: string
  estado: string
  marcos: MarcoLinhaDoTempo[]
  execucaoOrigemId: string | null
  retentativas: string[]
}

/** Um resultado da busca de execuções, mínimo o bastante para decidir qual abrir. */
export type ExecucaoResumo = {
  execucaoId: string
  estado: string
}

export type FiltroExecucoes = {
  segurado?: string
  canal?: string
  estado?: string
}

type CorpoProblema = Partial<components['schemas']['ProblemaLinhaDoTempo']>

type DadosErroLinhaDoTempo = {
  codigo: string
  correlacaoId: string | null
  ocorrencia: string
  impacto: string
  proximaAcao: string
  status: number | null
}

/** Falha tipada da linha do tempo/busca, com ocorrência, impacto e próxima ação segura. */
export class ErroLinhaDoTempo extends Error {
  readonly codigo: string
  readonly correlacaoId: string | null
  readonly ocorrencia: string
  readonly impacto: string
  readonly proximaAcao: string
  readonly status: number | null

  constructor(dados: DadosErroLinhaDoTempo) {
    super(dados.ocorrencia)
    this.name = 'ErroLinhaDoTempo'
    this.codigo = dados.codigo
    this.correlacaoId = dados.correlacaoId
    this.ocorrencia = dados.ocorrencia
    this.impacto = dados.impacto
    this.proximaAcao = dados.proximaAcao
    this.status = dados.status
  }
}

const FALHA_INESPERADA = {
  ocorrencia: 'A consulta da linha do tempo não pôde ser concluída.',
  impacto: 'A linha do tempo pode estar indisponível ou desatualizada.',
  proximaAcao: 'Verifique se o backend local está disponível e tente novamente.',
}

const FALHA_DE_REDE: DadosErroLinhaDoTempo = {
  codigo: 'falha_de_rede',
  correlacaoId: null,
  ocorrencia: 'Não foi possível falar com o backend local da Central Preventiva.',
  impacto: 'Nenhuma linha do tempo pôde ser exibida.',
  proximaAcao: 'Confirme que o backend está em execução em 127.0.0.1:8000 e tente de novo.',
  status: null,
}

function erroDeResultado(erro: unknown, status: number): ErroLinhaDoTempo {
  const corpo = (erro ?? {}) as CorpoProblema
  return new ErroLinhaDoTempo({
    codigo: corpo.codigo ?? 'falha_inesperada',
    correlacaoId: corpo.correlacao_id ?? null,
    ocorrencia: corpo.ocorrencia ?? FALHA_INESPERADA.ocorrencia,
    impacto: corpo.impacto ?? FALHA_INESPERADA.impacto,
    proximaAcao: corpo.proxima_acao ?? FALHA_INESPERADA.proximaAcao,
    status,
  })
}

function paraMarco(corpo: components['schemas']['RespostaMarcoLinhaDoTempo']): MarcoLinhaDoTempo {
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

function paraLinhaDoTempo(
  corpo: components['schemas']['RespostaLinhaDoTempo'],
): LinhaDoTempo {
  return {
    execucaoId: corpo.execucao_id,
    estado: corpo.estado,
    marcos: corpo.marcos.map(paraMarco),
    execucaoOrigemId: corpo.execucao_origem_id,
    retentativas: corpo.retentativas,
  }
}

function paraResumo(corpo: components['schemas']['RespostaExecucaoResumo']): ExecucaoResumo {
  return { execucaoId: corpo.execucao_id, estado: corpo.estado }
}

async function chamarLinhaDoTempo(execucaoId: string) {
  return clienteApi.GET('/api/v1/execucoes/{execucao_id}/linha-do-tempo', {
    params: { path: { execucao_id: execucaoId } },
    fetch,
  })
}

async function chamarBusca(filtro: FiltroExecucoes) {
  return clienteApi.GET('/api/v1/execucoes', {
    params: {
      query: {
        segurado: filtro.segurado || undefined,
        canal: filtro.canal || undefined,
        estado: filtro.estado || undefined,
      },
    },
    fetch,
  })
}

/** Consulta a linha do tempo ponta a ponta de uma execução. */
export async function getLinhaDoTempo(execucaoId: string): Promise<LinhaDoTempo> {
  let resultado: Awaited<ReturnType<typeof chamarLinhaDoTempo>>
  try {
    resultado = await chamarLinhaDoTempo(execucaoId)
  } catch {
    throw new ErroLinhaDoTempo(FALHA_DE_REDE)
  }

  if (!resultado.response.ok || !resultado.data) {
    throw erroDeResultado(resultado.error, resultado.response.status)
  }

  return paraLinhaDoTempo(resultado.data)
}

/** Busca execuções por segurado, canal e/ou estado, todos opcionais e combináveis. */
export async function buscarExecucoes(filtro: FiltroExecucoes = {}): Promise<ExecucaoResumo[]> {
  let resultado: Awaited<ReturnType<typeof chamarBusca>>
  try {
    resultado = await chamarBusca(filtro)
  } catch {
    throw new ErroLinhaDoTempo(FALHA_DE_REDE)
  }

  if (!resultado.response.ok || !resultado.data) {
    throw erroDeResultado(resultado.error, resultado.response.status)
  }

  return resultado.data.resultados.map(paraResumo)
}
