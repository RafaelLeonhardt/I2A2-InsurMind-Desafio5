import { clienteApi } from './clienteHttp'
import type { components } from './tipos-gerados'

/** Perfil demonstrativo que assina a decisão; o backend registra o que o cliente informa. */
export const PERFIL_REVISOR = 'administrador'

/** As quatro decisões possíveis sobre uma mensagem; nunca existe "editar" (AD-5/AD-6). */
export type ResultadoDecisao = 'aprovar' | 'rejeitar' | 'excluir' | 'regenerar'

/** Destinatário sintético da mensagem, como o snapshot da elegibilidade registrou. */
export type Destinatario = {
  elegibilidadeId: string
  seguradoId: string
  nomeSegurado: string
  apoliceId: string
  codigoIbgeArea: string
  canal: string
}

/** Um critério avaliado da elegibilidade, com o valor observado e o veredito. */
export type CriterioOrigem = {
  operando: string
  valorObservado: string
  atende: boolean
  justificativa: string
}

/** Dados de origem da mensagem: evento, regra versionada e critérios avaliados. */
export type OrigemItem = {
  eventoId: string
  regraId: string
  regraVersao: number
  justificativa: string
  criterios: CriterioOrigem[]
}

/** Proveniência do contexto do agente: o que foi e o que não foi usado (3.1). */
export type ProvenienciaItem = {
  categoriasUsadas: string[]
  categoriasNaoUsadas: string[]
}

/** Um motivo categorizado da reprovação do agente crítico. */
export type MotivoCriticoLote = {
  categoria: string
  justificativa: string
}

/** Avaliação do agente crítico sobre uma versão da mensagem. */
export type AvaliacaoCriticaLote = {
  aprovada: boolean
  motivos: MotivoCriticoLote[]
  agente: string
  modelo: string
  duracaoMs: number
}

/** Uma tentativa de geração: conteúdo, verificação determinística e crítica. */
export type VersaoRevisada = {
  id: string
  numeroTentativa: number
  assunto: string | null
  corpo: string
  valida: boolean
  motivoInvalidez: string | null
  modelo: string
  versaoPrompt: string
  duracaoMs: number
  criadoEm: string
  avaliacaoCritica: AvaliacaoCriticaLote | null
}

/** Uma decisão humana já registrada sobre a mensagem. */
export type DecisaoRegistrada = {
  versaoMensagemId: string
  perfilResponsavel: string
  resultado: string
  justificativa: string | null
  criadoEm: string
}

/** Uma mensagem do lote, com tudo que a decisão humana precisa. */
export type ItemLote = {
  mensagemId: string
  canal: string
  estado: string
  tentativaAtual: number
  limiteTentativas: number
  versao: number
  destinatario: Destinatario
  origem: OrigemItem
  proveniencia: ProvenienciaItem | null
  versoes: VersaoRevisada[]
  decisoes: DecisaoRegistrada[]
  aprovadaPeloCritico: boolean
  reprovacaoHistorica: boolean
  emExcecao: boolean
  decidivel: boolean
  podeRegenerar: boolean
}

/** Evento meteorológico que originou a execução em revisão. */
export type EventoLote = {
  id: string
  tipo: string
  area: string
  intensidade: number
  proveniencia: string
  periodoInicio: string
  periodoFim: string
}

/** O lote de revisão de uma execução, com os itens de atenção primeiro. */
export type LoteRevisao = {
  execucaoId: string
  estado: string
  evento: EventoLote | null
  regraId: string | null
  regraVersao: number | null
  totalPublicoIncluido: number
  distribuicaoPorCanal: { canal: string; total: number }[]
  aprovacoesAgenticas: number
  itensEmExcecao: number
  itens: ItemLote[]
}

/** Uma decisão a enviar sobre uma mensagem específica. */
export type DecisaoEnviada = {
  mensagemId: string
  versaoEsperada: number
  resultado: ResultadoDecisao
  justificativa: string | null
}

/** Um item recusado do envio, com o motivo estável da recusa. */
export type DecisaoRecusada = {
  mensagemId: string
  motivo: string
}

/** Desfecho do envio: o que foi aplicado, o que foi recusado e onde o agregado parou. */
export type ResultadoDecisaoLote = {
  execucaoId: string
  estado: string
  aplicadas: string[]
  recusadas: DecisaoRecusada[]
  mensagensAprovadas: string[]
  regeneracoesAtivas: string[]
}

type CorpoProblema = Partial<components['schemas']['ProblemaRevisao']>

type DadosErroRevisao = {
  codigo: string
  correlacaoId: string | null
  ocorrencia: string
  impacto: string
  proximaAcao: string
  status: number | null
}

/** Falha tipada da revisão do lote, com ocorrência, impacto e próxima ação segura. */
export class ErroRevisaoLote extends Error {
  readonly codigo: string
  readonly correlacaoId: string | null
  readonly ocorrencia: string
  readonly impacto: string
  readonly proximaAcao: string
  readonly status: number | null

  constructor(dados: DadosErroRevisao) {
    super(dados.ocorrencia)
    this.name = 'ErroRevisaoLote'
    this.codigo = dados.codigo
    this.correlacaoId = dados.correlacaoId
    this.ocorrencia = dados.ocorrencia
    this.impacto = dados.impacto
    this.proximaAcao = dados.proximaAcao
    this.status = dados.status
  }
}

const FALHA_INESPERADA = {
  ocorrencia: 'A operação sobre o lote de revisão não pôde ser concluída.',
  impacto: 'O lote pode estar indisponível ou desatualizado.',
  proximaAcao: 'Verifique se o backend local está disponível e tente novamente.',
}

const FALHA_DE_REDE: DadosErroRevisao = {
  codigo: 'falha_de_rede',
  correlacaoId: null,
  ocorrencia: 'Não foi possível falar com o backend local da Central Preventiva.',
  impacto: 'Nenhuma decisão foi aplicada.',
  proximaAcao: 'Confirme que o backend está em execução em 127.0.0.1:8000 e tente de novo.',
  status: null,
}

function erroDeResultado(erro: unknown, status: number): ErroRevisaoLote {
  const corpo = (erro ?? {}) as CorpoProblema
  return new ErroRevisaoLote({
    codigo: corpo.codigo ?? 'falha_inesperada',
    correlacaoId: corpo.correlacao_id ?? null,
    ocorrencia: corpo.ocorrencia ?? FALHA_INESPERADA.ocorrencia,
    impacto: corpo.impacto ?? FALHA_INESPERADA.impacto,
    proximaAcao: corpo.proxima_acao ?? FALHA_INESPERADA.proximaAcao,
    status,
  })
}

function paraVersao(
  versao: components['schemas']['RespostaVersaoRevisada'],
): VersaoRevisada {
  return {
    id: versao.id,
    numeroTentativa: versao.numero_tentativa,
    assunto: versao.assunto,
    corpo: versao.corpo,
    valida: versao.valida,
    motivoInvalidez: versao.motivo_invalidez,
    modelo: versao.modelo,
    versaoPrompt: versao.versao_prompt,
    duracaoMs: versao.duracao_ms,
    criadoEm: versao.criado_em,
    avaliacaoCritica: versao.avaliacao_critica
      ? {
          aprovada: versao.avaliacao_critica.aprovada,
          motivos: versao.avaliacao_critica.motivos.map((motivo) => ({
            categoria: motivo.categoria,
            justificativa: motivo.justificativa,
          })),
          agente: versao.avaliacao_critica.agente,
          modelo: versao.avaliacao_critica.modelo,
          duracaoMs: versao.avaliacao_critica.duracao_ms,
        }
      : null,
  }
}

function paraItem(item: components['schemas']['RespostaItemLote']): ItemLote {
  return {
    mensagemId: item.mensagem_id,
    canal: item.canal,
    estado: item.estado,
    tentativaAtual: item.tentativa_atual,
    limiteTentativas: item.limite_tentativas,
    versao: item.versao,
    destinatario: {
      elegibilidadeId: item.destinatario.elegibilidade_id,
      seguradoId: item.destinatario.segurado_id,
      nomeSegurado: item.destinatario.nome_segurado,
      apoliceId: item.destinatario.apolice_id,
      codigoIbgeArea: item.destinatario.codigo_ibge_area,
      canal: item.destinatario.canal,
    },
    origem: {
      eventoId: item.origem.evento_id,
      regraId: item.origem.regra_id,
      regraVersao: item.origem.regra_versao,
      justificativa: item.origem.justificativa,
      criterios: item.origem.criterios.map((criterio) => ({
        operando: criterio.operando,
        valorObservado: criterio.valor_observado,
        atende: criterio.atende,
        justificativa: criterio.justificativa,
      })),
    },
    proveniencia: item.proveniencia
      ? {
          categoriasUsadas: item.proveniencia.categorias_usadas,
          categoriasNaoUsadas: item.proveniencia.categorias_nao_usadas,
        }
      : null,
    versoes: item.versoes.map(paraVersao),
    decisoes: item.decisoes.map((decisao) => ({
      versaoMensagemId: decisao.versao_mensagem_id,
      perfilResponsavel: decisao.perfil_responsavel,
      resultado: decisao.resultado,
      justificativa: decisao.justificativa,
      criadoEm: decisao.criado_em,
    })),
    aprovadaPeloCritico: item.aprovada_pelo_critico,
    reprovacaoHistorica: item.reprovacao_historica,
    emExcecao: item.em_excecao,
    decidivel: item.decidivel,
    podeRegenerar: item.pode_regenerar,
  }
}

function paraLote(corpo: components['schemas']['RespostaLoteRevisao']): LoteRevisao {
  return {
    execucaoId: corpo.execucao_id,
    estado: corpo.estado,
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
    totalPublicoIncluido: corpo.total_publico_incluido,
    distribuicaoPorCanal: corpo.distribuicao_por_canal.map((entrada) => ({
      canal: entrada.canal,
      total: entrada.total,
    })),
    aprovacoesAgenticas: corpo.aprovacoes_agenticas,
    itensEmExcecao: corpo.itens_em_excecao,
    itens: corpo.itens.map(paraItem),
  }
}

async function chamarLote(execucaoId: string) {
  return clienteApi.GET('/api/v1/execucoes/{execucao_id}/revisao', {
    params: { path: { execucao_id: execucaoId } },
    fetch,
  })
}

async function chamarDecisoes(execucaoId: string, decisoes: DecisaoEnviada[]) {
  return clienteApi.POST('/api/v1/execucoes/{execucao_id}/revisao/decisoes', {
    params: {
      header: { 'Idempotency-Key': crypto.randomUUID() },
      path: { execucao_id: execucaoId },
    },
    body: {
      perfil: PERFIL_REVISOR,
      decisoes: decisoes.map((decisao) => ({
        mensagem_id: decisao.mensagemId,
        versao_esperada: decisao.versaoEsperada,
        resultado: decisao.resultado,
        justificativa: decisao.justificativa,
      })),
    },
    fetch,
  })
}

/** Consulta o lote de revisão da execução, já ordenado com os itens de atenção primeiro. */
export async function getLoteRevisao(execucaoId: string): Promise<LoteRevisao> {
  let resultado: Awaited<ReturnType<typeof chamarLote>>
  try {
    resultado = await chamarLote(execucaoId)
  } catch {
    throw new ErroRevisaoLote(FALHA_DE_REDE)
  }

  if (!resultado.response.ok || !resultado.data) {
    throw erroDeResultado(resultado.error, resultado.response.status)
  }

  return paraLote(resultado.data)
}

/**
 * Envia as decisões humanas do lote, com `Idempotency-Key` nova a cada envio.
 *
 * Nenhuma decisão altera o texto gerado: o corpo carrega só o identificador da mensagem, a
 * versão esperada, o resultado e a justificativa (AD-5/AD-6).
 */
export async function decidirLote(
  execucaoId: string,
  decisoes: DecisaoEnviada[],
): Promise<ResultadoDecisaoLote> {
  let resultado: Awaited<ReturnType<typeof chamarDecisoes>>
  try {
    resultado = await chamarDecisoes(execucaoId, decisoes)
  } catch {
    throw new ErroRevisaoLote(FALHA_DE_REDE)
  }

  if (!resultado.response.ok || !resultado.data) {
    throw erroDeResultado(resultado.error, resultado.response.status)
  }

  return {
    execucaoId: resultado.data.execucao_id,
    estado: resultado.data.estado,
    aplicadas: resultado.data.aplicadas,
    recusadas: resultado.data.recusadas.map((item) => ({
      mensagemId: item.mensagem_id,
      motivo: item.motivo,
    })),
    mensagensAprovadas: resultado.data.mensagens_aprovadas,
    regeneracoesAtivas: resultado.data.regeneracoes_ativas,
  }
}
