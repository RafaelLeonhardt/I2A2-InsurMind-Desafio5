import { clienteApi } from './clienteHttp'
import type { components } from './tipos-gerados'

/** Evento meteorológico que originou a execução a simular. */
export type EventoSimulacao = {
  id: string
  tipo: string
  area: string
  intensidade: number
  proveniencia: string
  periodoInicio: string
  periodoFim: string
}

/** Quantidade de destinatários do lote simulável em um canal. */
export type CanalSimulacao = {
  canal: string
  total: number
}

/** Uma entrega simulada: como o conteúdo aprovado apareceria no canal. */
export type EntregaSimulada = {
  id: string
  mensagemId: string
  canal: string
  rotulo: string
  assunto: string | null
  corpo: string
  criadoEm: string
}

/** Resumo da simulação de uma execução, antes e depois de confirmá-la. */
export type ResumoSimulacao = {
  execucaoId: string
  estado: string
  versao: number
  evento: EventoSimulacao | null
  regraId: string | null
  regraVersao: number | null
  totalDestinatarios: number
  distribuicaoPorCanal: CanalSimulacao[]
  entregas: EntregaSimulada[]
  execucaoOrigemId: string | null
  retentativas: string[]
}

/** Desfecho da confirmação: onde o agregado parou e o que a simulação registrou. */
export type SimulacaoConfirmada = {
  execucaoId: string
  estado: string
  entregasCriadas: string[]
  mensagensSimuladas: string[]
}

type CorpoProblema = Partial<components['schemas']['ProblemaSimulacao']>

type DadosErroSimulacao = {
  codigo: string
  correlacaoId: string | null
  ocorrencia: string
  impacto: string
  proximaAcao: string
  status: number | null
}

/** Falha tipada da simulação, com ocorrência, impacto e próxima ação segura. */
export class ErroSimulacao extends Error {
  readonly codigo: string
  readonly correlacaoId: string | null
  readonly ocorrencia: string
  readonly impacto: string
  readonly proximaAcao: string
  readonly status: number | null

  constructor(dados: DadosErroSimulacao) {
    super(dados.ocorrencia)
    this.name = 'ErroSimulacao'
    this.codigo = dados.codigo
    this.correlacaoId = dados.correlacaoId
    this.ocorrencia = dados.ocorrencia
    this.impacto = dados.impacto
    this.proximaAcao = dados.proximaAcao
    this.status = dados.status
  }
}

const FALHA_INESPERADA = {
  ocorrencia: 'A operação sobre a simulação não pôde ser concluída.',
  impacto: 'A simulação pode estar indisponível ou desatualizada.',
  proximaAcao: 'Verifique se o backend local está disponível e tente novamente.',
}

const FALHA_DE_REDE: DadosErroSimulacao = {
  codigo: 'falha_de_rede',
  correlacaoId: null,
  ocorrencia: 'Não foi possível falar com o backend local da Central Preventiva.',
  impacto: 'Nenhuma simulação foi executada.',
  proximaAcao: 'Confirme que o backend está em execução em 127.0.0.1:8000 e tente de novo.',
  status: null,
}

function erroDeResultado(erro: unknown, status: number): ErroSimulacao {
  const corpo = (erro ?? {}) as CorpoProblema
  return new ErroSimulacao({
    codigo: corpo.codigo ?? 'falha_inesperada',
    correlacaoId: corpo.correlacao_id ?? null,
    ocorrencia: corpo.ocorrencia ?? FALHA_INESPERADA.ocorrencia,
    impacto: corpo.impacto ?? FALHA_INESPERADA.impacto,
    proximaAcao: corpo.proxima_acao ?? FALHA_INESPERADA.proximaAcao,
    status,
  })
}

function paraResumo(
  corpo: components['schemas']['RespostaResumoSimulacao'],
): ResumoSimulacao {
  return {
    execucaoId: corpo.execucao_id,
    estado: corpo.estado,
    versao: corpo.versao,
    evento: corpo.evento
      ? {
          id: corpo.evento.id,
          tipo: corpo.evento.tipo,
          area: corpo.evento.area,
          intensidade: corpo.evento.intensidade,
          proveniencia: corpo.evento.proveniencia,
          periodoInicio: corpo.evento.periodo_inicio,
          periodoFim: corpo.evento.periodo_fim,
        }
      : null,
    regraId: corpo.regra_id,
    regraVersao: corpo.regra_versao,
    totalDestinatarios: corpo.total_destinatarios,
    distribuicaoPorCanal: corpo.distribuicao_por_canal.map((entrada) => ({
      canal: entrada.canal,
      total: entrada.total,
    })),
    entregas: corpo.entregas.map((entrega) => ({
      id: entrega.id,
      mensagemId: entrega.mensagem_id,
      canal: entrega.canal,
      rotulo: entrega.rotulo,
      assunto: entrega.assunto,
      corpo: entrega.corpo,
      criadoEm: entrega.criado_em,
    })),
    execucaoOrigemId: corpo.execucao_origem_id,
    retentativas: corpo.retentativas,
  }
}

async function chamarResumo(execucaoId: string) {
  return clienteApi.GET('/api/v1/execucoes/{execucao_id}/simulacao', {
    params: { path: { execucao_id: execucaoId } },
    fetch,
  })
}

async function chamarConfirmacao(execucaoId: string, versaoEsperada: number) {
  return clienteApi.POST('/api/v1/execucoes/{execucao_id}/confirmar-simulacao', {
    params: {
      header: { 'Idempotency-Key': crypto.randomUUID() },
      path: { execucao_id: execucaoId },
    },
    body: { versao_esperada: versaoEsperada, reconhecimento_simulacao: true },
    fetch,
  })
}

async function chamarNovaTentativa(execucaoOrigemId: string) {
  return clienteApi.POST('/api/v1/execucoes/{execucao_origem_id}/nova-tentativa-simulacao', {
    params: {
      header: { 'Idempotency-Key': crypto.randomUUID() },
      path: { execucao_origem_id: execucaoOrigemId },
    },
    fetch,
  })
}

/** Consulta o resumo da simulação: cabeçalho da confirmação e entregas já registradas. */
export async function getResumoSimulacao(execucaoId: string): Promise<ResumoSimulacao> {
  let resultado: Awaited<ReturnType<typeof chamarResumo>>
  try {
    resultado = await chamarResumo(execucaoId)
  } catch {
    throw new ErroSimulacao(FALHA_DE_REDE)
  }

  if (!resultado.response.ok || !resultado.data) {
    throw erroDeResultado(resultado.error, resultado.response.status)
  }

  return paraResumo(resultado.data)
}

/**
 * Confirma e executa a simulação, com `Idempotency-Key` nova a cada envio.
 *
 * O reconhecimento explícito só é enviado porque a interface já o exigiu de Marina: o
 * backend o cobra de novo, como defesa em profundidade (SIMUL-03).
 */
export async function confirmarSimulacao(
  execucaoId: string,
  versaoEsperada: number,
): Promise<SimulacaoConfirmada> {
  let resultado: Awaited<ReturnType<typeof chamarConfirmacao>>
  try {
    resultado = await chamarConfirmacao(execucaoId, versaoEsperada)
  } catch {
    throw new ErroSimulacao(FALHA_DE_REDE)
  }

  if (!resultado.response.ok || !resultado.data) {
    throw erroDeResultado(resultado.error, resultado.response.status)
  }

  return {
    execucaoId: resultado.data.execucao_id,
    estado: resultado.data.estado,
    entregasCriadas: resultado.data.entregas_criadas,
    mensagensSimuladas: resultado.data.mensagens_simuladas,
  }
}

/** Solicita a execução correlacionada a partir de uma falha local de simulação. */
export async function solicitarNovaTentativaSimulacao(
  execucaoOrigemId: string,
): Promise<string> {
  let resultado: Awaited<ReturnType<typeof chamarNovaTentativa>>
  try {
    resultado = await chamarNovaTentativa(execucaoOrigemId)
  } catch {
    throw new ErroSimulacao(FALHA_DE_REDE)
  }

  if (!resultado.response.ok || !resultado.data) {
    throw erroDeResultado(resultado.error, resultado.response.status)
  }

  return resultado.data.execucao_id
}
