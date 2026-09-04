import { clienteApi } from './clienteHttp'
import type { components } from './tipos-gerados'

/** Uma contagem agregada por canal ou por estado. */
export type TotalPorChave = {
  chave: string
  total: number
}

/** Uma mensagem que nunca foi nem será simulada nesta execução, com o motivo. */
export type MensagemNaoSimulavel = {
  mensagemId: string
  canal: string
  estado: string
  motivo: string
}

/** Inconsistência entre mensagens `simulada_entregue` e entregas persistidas. */
export type DivergenciaTotais = {
  execucaoId: string
  mensagensSimuladaEntregue: number
  entregasPersistidas: number
}

/** Resultados consolidados de uma execução, ou o progresso real enquanto ela não termina. */
export type ResultadosConsolidados = {
  execucaoId: string
  estado: string
  concluido: boolean
  totaisPorCanal: TotalPorChave[]
  totaisPorEstado: TotalPorChave[]
  naoSimulaveis: MensagemNaoSimulavel[]
  divergencia: DivergenciaTotais | null
}

type CorpoProblema = Partial<components['schemas']['ProblemaResultados']>

type DadosErroResultados = {
  codigo: string
  correlacaoId: string | null
  ocorrencia: string
  impacto: string
  proximaAcao: string
  status: number | null
}

/** Falha tipada da consulta de resultados, com ocorrência, impacto e próxima ação segura. */
export class ErroResultados extends Error {
  readonly codigo: string
  readonly correlacaoId: string | null
  readonly ocorrencia: string
  readonly impacto: string
  readonly proximaAcao: string
  readonly status: number | null

  constructor(dados: DadosErroResultados) {
    super(dados.ocorrencia)
    this.name = 'ErroResultados'
    this.codigo = dados.codigo
    this.correlacaoId = dados.correlacaoId
    this.ocorrencia = dados.ocorrencia
    this.impacto = dados.impacto
    this.proximaAcao = dados.proximaAcao
    this.status = dados.status
  }
}

const FALHA_INESPERADA = {
  ocorrencia: 'A consulta dos resultados não pôde ser concluída.',
  impacto: 'Os resultados podem estar indisponíveis ou desatualizados.',
  proximaAcao: 'Verifique se o backend local está disponível e tente novamente.',
}

const FALHA_DE_REDE: DadosErroResultados = {
  codigo: 'falha_de_rede',
  correlacaoId: null,
  ocorrencia: 'Não foi possível falar com o backend local da Central Preventiva.',
  impacto: 'Nenhum resultado pôde ser exibido.',
  proximaAcao: 'Confirme que o backend está em execução em 127.0.0.1:8000 e tente de novo.',
  status: null,
}

function erroDeResultado(erro: unknown, status: number): ErroResultados {
  const corpo = (erro ?? {}) as CorpoProblema
  return new ErroResultados({
    codigo: corpo.codigo ?? 'falha_inesperada',
    correlacaoId: corpo.correlacao_id ?? null,
    ocorrencia: corpo.ocorrencia ?? FALHA_INESPERADA.ocorrencia,
    impacto: corpo.impacto ?? FALHA_INESPERADA.impacto,
    proximaAcao: corpo.proxima_acao ?? FALHA_INESPERADA.proximaAcao,
    status,
  })
}

function paraResultados(
  corpo: components['schemas']['RespostaResultadosConsolidados'],
): ResultadosConsolidados {
  return {
    execucaoId: corpo.execucao_id,
    estado: corpo.estado,
    concluido: corpo.concluido,
    totaisPorCanal: corpo.totais_por_canal.map((item) => ({
      chave: item.chave,
      total: item.total,
    })),
    totaisPorEstado: corpo.totais_por_estado.map((item) => ({
      chave: item.chave,
      total: item.total,
    })),
    naoSimulaveis: corpo.nao_simulaveis.map((item) => ({
      mensagemId: item.mensagem_id,
      canal: item.canal,
      estado: item.estado,
      motivo: item.motivo,
    })),
    divergencia: corpo.divergencia
      ? {
          execucaoId: corpo.divergencia.execucao_id,
          mensagensSimuladaEntregue: corpo.divergencia.mensagens_simulada_entregue,
          entregasPersistidas: corpo.divergencia.entregas_persistidas,
        }
      : null,
  }
}

async function chamarResultados(execucaoId: string) {
  return clienteApi.GET('/api/v1/execucoes/{execucao_id}/resultados', {
    params: { path: { execucao_id: execucaoId } },
    fetch,
  })
}

/** Consulta os resultados consolidados da simulação de uma execução. */
export async function getResultados(execucaoId: string): Promise<ResultadosConsolidados> {
  let resultado: Awaited<ReturnType<typeof chamarResultados>>
  try {
    resultado = await chamarResultados(execucaoId)
  } catch {
    throw new ErroResultados(FALHA_DE_REDE)
  }

  if (!resultado.response.ok || !resultado.data) {
    throw erroDeResultado(resultado.error, resultado.response.status)
  }

  return paraResultados(resultado.data)
}
