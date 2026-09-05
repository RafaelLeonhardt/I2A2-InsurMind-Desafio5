import { clienteApi } from './clienteHttp'
import type { components } from './tipos-gerados'

/** Evento meteorológico que originou a mensagem detalhada. */
export type EventoDetalhe = {
  id: string
  tipo: string
  area: string
  intensidade: number
  proveniencia: string
  periodoInicio: string
  periodoFim: string
}

/** Como o conteúdo aprovado apareceria no canal, sempre rotulado como simulado. */
export type ApresentacaoSimuladaDetalhe = {
  canal: string
  assunto: string | null
  corpo: string
  rotulo: string
}

/** Avaliação crítica de uma versão da mensagem. */
export type AvaliacaoCriticaDetalhe = {
  aprovada: boolean
  motivos: string[]
  agente: string
  modelo: string
  duracaoMs: number
  criadoEm: string
}

/** Decisão humana registrada sobre uma versão da mensagem. */
export type DecisaoHumanaDetalhe = {
  perfilResponsavel: string
  resultado: string
  justificativa: string | null
  criadoEm: string
}

/** Uma tentativa de geração relacionada à sua avaliação crítica e decisões humanas. */
export type VersaoDetalhe = {
  numeroTentativa: number
  valida: boolean
  motivoInvalidez: string | null
  assunto: string | null
  corpo: string
  modelo: string
  criadoEm: string
  avaliacaoCritica: AvaliacaoCriticaDetalhe | null
  decisoesHumanas: DecisaoHumanaDetalhe[]
}

/** Exceção operacional associada à mensagem, quando ela falhou tecnicamente. */
export type ExcecaoDetalhe = {
  causa: string
  tentativas: number
  impacto: string
  criadoEm: string
}

/** Detalhe completo do resultado individual de uma mensagem simulada. */
export type DetalheResultado = {
  mensagemId: string
  execucaoId: string
  canal: string
  estado: string
  limiteCanalCorpo: number
  limiteCanalAssunto: number | null
  criadoEm: string
  atualizadoEm: string
  nomeSegurado: string
  apoliceId: string
  codigoIbgeArea: string
  evento: EventoDetalhe | null
  regraId: string
  regraVersao: number
  apresentacaoSimulada: ApresentacaoSimuladaDetalhe | null
  versoes: VersaoDetalhe[]
  excecao: ExcecaoDetalhe | null
}

type CorpoProblema = Partial<components['schemas']['ProblemaDetalheResultado']>

type DadosErroDetalheResultado = {
  codigo: string
  correlacaoId: string | null
  ocorrencia: string
  impacto: string
  proximaAcao: string
  status: number | null
}

/** Falha tipada da consulta de detalhe, com ocorrência, impacto e próxima ação segura. */
export class ErroDetalheResultado extends Error {
  readonly codigo: string
  readonly correlacaoId: string | null
  readonly ocorrencia: string
  readonly impacto: string
  readonly proximaAcao: string
  readonly status: number | null

  constructor(dados: DadosErroDetalheResultado) {
    super(dados.ocorrencia)
    this.name = 'ErroDetalheResultado'
    this.codigo = dados.codigo
    this.correlacaoId = dados.correlacaoId
    this.ocorrencia = dados.ocorrencia
    this.impacto = dados.impacto
    this.proximaAcao = dados.proximaAcao
    this.status = dados.status
  }
}

const FALHA_INESPERADA = {
  ocorrencia: 'A consulta do detalhe não pôde ser concluída.',
  impacto: 'O detalhe pode estar indisponível ou desatualizado.',
  proximaAcao: 'Verifique se o backend local está disponível e tente novamente.',
}

const FALHA_DE_REDE: DadosErroDetalheResultado = {
  codigo: 'falha_de_rede',
  correlacaoId: null,
  ocorrencia: 'Não foi possível falar com o backend local da Central Preventiva.',
  impacto: 'Nenhum detalhe pôde ser exibido.',
  proximaAcao: 'Confirme que o backend está em execução em 127.0.0.1:8000 e tente de novo.',
  status: null,
}

function erroDeResultado(erro: unknown, status: number): ErroDetalheResultado {
  const corpo = (erro ?? {}) as CorpoProblema
  return new ErroDetalheResultado({
    codigo: corpo.codigo ?? 'falha_inesperada',
    correlacaoId: corpo.correlacao_id ?? null,
    ocorrencia: corpo.ocorrencia ?? FALHA_INESPERADA.ocorrencia,
    impacto: corpo.impacto ?? FALHA_INESPERADA.impacto,
    proximaAcao: corpo.proxima_acao ?? FALHA_INESPERADA.proximaAcao,
    status,
  })
}

function paraVersao(corpo: components['schemas']['RespostaVersaoDetalhe']): VersaoDetalhe {
  const avaliacao = corpo.avaliacao_critica
  return {
    numeroTentativa: corpo.numero_tentativa,
    valida: corpo.valida,
    motivoInvalidez: corpo.motivo_invalidez,
    assunto: corpo.assunto,
    corpo: corpo.corpo,
    modelo: corpo.modelo,
    criadoEm: corpo.criado_em,
    avaliacaoCritica: avaliacao
      ? {
          aprovada: avaliacao.aprovada,
          motivos: avaliacao.motivos,
          agente: avaliacao.agente,
          modelo: avaliacao.modelo,
          duracaoMs: avaliacao.duracao_ms,
          criadoEm: avaliacao.criado_em,
        }
      : null,
    decisoesHumanas: corpo.decisoes_humanas.map((decisao) => ({
      perfilResponsavel: decisao.perfil_responsavel,
      resultado: decisao.resultado,
      justificativa: decisao.justificativa,
      criadoEm: decisao.criado_em,
    })),
  }
}

function paraDetalhe(
  corpo: components['schemas']['RespostaDetalheResultado'],
): DetalheResultado {
  const evento = corpo.evento
  const apresentacao = corpo.apresentacao_simulada
  const excecao = corpo.excecao
  return {
    mensagemId: corpo.mensagem_id,
    execucaoId: corpo.execucao_id,
    canal: corpo.canal,
    estado: corpo.estado,
    limiteCanalCorpo: corpo.limite_canal_corpo,
    limiteCanalAssunto: corpo.limite_canal_assunto,
    criadoEm: corpo.criado_em,
    atualizadoEm: corpo.atualizado_em,
    nomeSegurado: corpo.nome_segurado,
    apoliceId: corpo.apolice_id,
    codigoIbgeArea: corpo.codigo_ibge_area,
    evento: evento
      ? {
          id: evento.id,
          tipo: evento.tipo,
          area: evento.area,
          intensidade: evento.intensidade,
          proveniencia: evento.proveniencia,
          periodoInicio: evento.periodo_inicio,
          periodoFim: evento.periodo_fim,
        }
      : null,
    regraId: corpo.regra_id,
    regraVersao: corpo.regra_versao,
    apresentacaoSimulada: apresentacao
      ? {
          canal: apresentacao.canal,
          assunto: apresentacao.assunto,
          corpo: apresentacao.corpo,
          rotulo: apresentacao.rotulo,
        }
      : null,
    versoes: corpo.versoes.map(paraVersao),
    excecao: excecao
      ? {
          causa: excecao.causa,
          tentativas: excecao.tentativas,
          impacto: excecao.impacto,
          criadoEm: excecao.criado_em,
        }
      : null,
  }
}

async function chamarDetalhe(execucaoId: string, mensagemId: string) {
  return clienteApi.GET(
    '/api/v1/execucoes/{execucao_id}/mensagens/{mensagem_id}/detalhe',
    {
      params: { path: { execucao_id: execucaoId, mensagem_id: mensagemId } },
      fetch,
    },
  )
}

/** Consulta o detalhe individual de uma mensagem simulada. */
export async function getDetalheResultado(
  execucaoId: string,
  mensagemId: string,
): Promise<DetalheResultado> {
  let resultado: Awaited<ReturnType<typeof chamarDetalhe>>
  try {
    resultado = await chamarDetalhe(execucaoId, mensagemId)
  } catch {
    throw new ErroDetalheResultado(FALHA_DE_REDE)
  }

  if (!resultado.response.ok || !resultado.data) {
    throw erroDeResultado(resultado.error, resultado.response.status)
  }

  return paraDetalhe(resultado.data)
}
