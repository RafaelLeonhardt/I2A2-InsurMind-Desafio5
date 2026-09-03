import { clienteApi } from './clienteHttp'
import type { components } from './tipos-gerados'

/** Desfecho do preflight de uma execução, conforme o contrato REST/JSON do backend. */
export type Preflight = {
  execucaoId: string
  estado: string
  contextosMontados: number
  itensEmExcecao: string[]
  causa: string | null
}

/** Ack da execução correlacionada criada por uma nova tentativa de preparação. */
export type NovaTentativaIa = {
  execucaoId: string
  execucaoOrigemId: string
}

type CorpoProblema = Partial<components['schemas']['ProblemaPreflight']>

type DadosErroPreparacaoIa = {
  codigo: string
  correlacaoId: string | null
  ocorrencia: string
  impacto: string
  proximaAcao: string
  status: number | null
}

/** Falha tipada da preparação agêntica, com ocorrência, impacto e próxima ação segura. */
export class ErroPreparacaoIa extends Error {
  readonly codigo: string
  readonly correlacaoId: string | null
  readonly ocorrencia: string
  readonly impacto: string
  readonly proximaAcao: string
  readonly status: number | null

  constructor(dados: DadosErroPreparacaoIa) {
    super(dados.ocorrencia)
    this.name = 'ErroPreparacaoIa'
    this.codigo = dados.codigo
    this.correlacaoId = dados.correlacaoId
    this.ocorrencia = dados.ocorrencia
    this.impacto = dados.impacto
    this.proximaAcao = dados.proximaAcao
    this.status = dados.status
  }
}

const FALHA_INESPERADA = {
  ocorrencia: 'A preparação da produção de mensagens não pôde ser concluída.',
  impacto: 'Nenhuma mensagem preventiva foi gerada nesta execução.',
  proximaAcao: 'Verifique se o backend local está disponível e tente novamente.',
}

const FALHA_DE_REDE: DadosErroPreparacaoIa = {
  codigo: 'falha_de_rede',
  correlacaoId: null,
  ocorrencia: 'Não foi possível falar com o backend local da Central Preventiva.',
  impacto: 'Nenhuma preparação agêntica pôde ser iniciada ou consultada.',
  proximaAcao: 'Confirme que o backend está em execução em 127.0.0.1:8000 e tente de novo.',
  status: null,
}

function erroDeResultado(erro: unknown, status: number): ErroPreparacaoIa {
  const corpo = (erro ?? {}) as CorpoProblema
  return new ErroPreparacaoIa({
    codigo: corpo.codigo ?? 'falha_inesperada',
    correlacaoId: corpo.correlacao_id ?? null,
    ocorrencia: corpo.ocorrencia ?? FALHA_INESPERADA.ocorrencia,
    impacto: corpo.impacto ?? FALHA_INESPERADA.impacto,
    proximaAcao: corpo.proxima_acao ?? FALHA_INESPERADA.proximaAcao,
    status,
  })
}

async function chamarPreflight(execucaoId: string) {
  return clienteApi.POST('/api/v1/execucoes/{execucao_id}/preflight', {
    params: {
      path: { execucao_id: execucaoId },
      header: { 'Idempotency-Key': crypto.randomUUID() },
    },
    fetch,
  })
}

async function chamarNovaTentativa(execucaoOrigemId: string) {
  return clienteApi.POST('/api/v1/execucoes/{execucao_origem_id}/nova-tentativa-ia', {
    params: {
      path: { execucao_origem_id: execucaoOrigemId },
      header: { 'Idempotency-Key': crypto.randomUUID() },
    },
    fetch,
  })
}

/** Prepara a etapa agêntica da execução: verifica a OpenAI e monta o contexto mínimo. */
export async function prepararExecucao(execucaoId: string): Promise<Preflight> {
  let resultado: Awaited<ReturnType<typeof chamarPreflight>>
  try {
    resultado = await chamarPreflight(execucaoId)
  } catch {
    throw new ErroPreparacaoIa(FALHA_DE_REDE)
  }

  if (!resultado.response.ok || !resultado.data) {
    throw erroDeResultado(resultado.error, resultado.response.status)
  }

  return {
    execucaoId: resultado.data.execucao_id,
    estado: resultado.data.estado,
    contextosMontados: resultado.data.contextos_montados,
    itensEmExcecao: resultado.data.itens_em_excecao,
    causa: resultado.data.causa,
  }
}

/** Solicita uma nova tentativa de preparação a partir de uma execução terminal. */
export async function solicitarNovaTentativaIa(
  execucaoOrigemId: string,
): Promise<NovaTentativaIa> {
  let resultado: Awaited<ReturnType<typeof chamarNovaTentativa>>
  try {
    resultado = await chamarNovaTentativa(execucaoOrigemId)
  } catch {
    throw new ErroPreparacaoIa(FALHA_DE_REDE)
  }

  if (!resultado.response.ok || !resultado.data) {
    throw erroDeResultado(resultado.error, resultado.response.status)
  }

  return {
    execucaoId: resultado.data.execucao_id,
    execucaoOrigemId: resultado.data.execucao_origem_id,
  }
}
