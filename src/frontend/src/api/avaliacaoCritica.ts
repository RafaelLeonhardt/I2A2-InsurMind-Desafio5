import { clienteApi } from './clienteHttp'
import type { components } from './tipos-gerados'

/** Um motivo da decisão do crítico: a categoria avaliada e a justificativa dela. */
export type MotivoCritica = {
  categoria: string
  justificativa: string
}

/** Veredito estrutural de 3.2 sobre a mesma versão, decidido por regra e não pelo modelo. */
export type ValidacaoDeterministica = {
  origem: string
  valida: boolean
  motivoInvalidez: string | null
}

/** Detalhe de uma avaliação crítica: versão, critérios, decisão, motivos e proveniência. */
export type AvaliacaoCritica = {
  mensagemId: string
  versaoMensagemId: string
  numeroTentativa: number
  origem: string
  criterios: string[]
  aprovada: boolean
  motivos: MotivoCritica[]
  agente: string
  modelo: string
  duracaoMs: number
  criadoEm: string
  validacaoDeterministica: ValidacaoDeterministica
}

type CorpoProblema = Partial<components['schemas']['ProblemaAvaliacaoCritica']>

type DadosErroAvaliacaoCritica = {
  codigo: string
  correlacaoId: string | null
  ocorrencia: string
  impacto: string
  proximaAcao: string
  status: number | null
}

/** Falha tipada da consulta do detalhe, com ocorrência, impacto e próxima ação segura. */
export class ErroAvaliacaoCritica extends Error {
  readonly codigo: string
  readonly correlacaoId: string | null
  readonly ocorrencia: string
  readonly impacto: string
  readonly proximaAcao: string
  readonly status: number | null

  constructor(dados: DadosErroAvaliacaoCritica) {
    super(dados.ocorrencia)
    this.name = 'ErroAvaliacaoCritica'
    this.codigo = dados.codigo
    this.correlacaoId = dados.correlacaoId
    this.ocorrencia = dados.ocorrencia
    this.impacto = dados.impacto
    this.proximaAcao = dados.proximaAcao
    this.status = dados.status
  }
}

const FALHA_INESPERADA = {
  ocorrencia: 'A consulta do detalhe da avaliação não pôde ser concluída.',
  impacto: 'O detalhe da avaliação pode estar indisponível.',
  proximaAcao: 'Verifique se o backend local está disponível e tente novamente.',
}

const FALHA_DE_REDE: DadosErroAvaliacaoCritica = {
  codigo: 'falha_de_rede',
  correlacaoId: null,
  ocorrencia: 'Não foi possível falar com o backend local da Central Preventiva.',
  impacto: 'Nenhum detalhe de avaliação pôde ser consultado.',
  proximaAcao: 'Confirme que o backend está em execução em 127.0.0.1:8000 e tente de novo.',
  status: null,
}

/** Converte o erro já desserializado pelo `openapi-fetch` em `ErroAvaliacaoCritica`. */
function erroDeResultado(erro: unknown, status: number): ErroAvaliacaoCritica {
  const corpo = (erro ?? {}) as CorpoProblema
  return new ErroAvaliacaoCritica({
    codigo: corpo.codigo ?? 'falha_inesperada',
    correlacaoId: corpo.correlacao_id ?? null,
    ocorrencia: corpo.ocorrencia ?? FALHA_INESPERADA.ocorrencia,
    impacto: corpo.impacto ?? FALHA_INESPERADA.impacto,
    proximaAcao: corpo.proxima_acao ?? FALHA_INESPERADA.proximaAcao,
    status,
  })
}

function paraAvaliacao(
  corpo: components['schemas']['RespostaAvaliacaoCritica']
): AvaliacaoCritica {
  return {
    mensagemId: corpo.mensagem_id,
    versaoMensagemId: corpo.versao_mensagem_id,
    numeroTentativa: corpo.numero_tentativa,
    origem: corpo.origem,
    criterios: corpo.criterios,
    aprovada: corpo.aprovada,
    motivos: corpo.motivos.map((motivo) => ({
      categoria: motivo.categoria,
      justificativa: motivo.justificativa,
    })),
    agente: corpo.agente,
    modelo: corpo.modelo,
    duracaoMs: corpo.duracao_ms,
    criadoEm: corpo.criado_em,
    validacaoDeterministica: {
      origem: corpo.validacao_deterministica.origem,
      valida: corpo.validacao_deterministica.valida,
      motivoInvalidez: corpo.validacao_deterministica.motivo_invalidez,
    },
  }
}

async function chamarAvaliacao(mensagemId: string, versaoId: string) {
  return clienteApi.GET(
    '/api/v1/mensagens/{mensagem_id}/versoes/{versao_id}/avaliacao-critica',
    {
      params: { path: { mensagem_id: mensagemId, versao_id: versaoId } },
      fetch,
    }
  )
}

/**
 * Consulta o detalhe da avaliação crítica de uma versão de mensagem.
 *
 * Só leitura: nenhuma chamada do frontend reavalia conteúdo nem aciona a OpenAI — quem avalia
 * é o backend, ao entrar em `criticando` (CRIT-08).
 */
export async function getAvaliacaoCritica(
  mensagemId: string,
  versaoId: string
): Promise<AvaliacaoCritica> {
  let resultado: Awaited<ReturnType<typeof chamarAvaliacao>>
  try {
    resultado = await chamarAvaliacao(mensagemId, versaoId)
  } catch {
    throw new ErroAvaliacaoCritica(FALHA_DE_REDE)
  }

  if (!resultado.response.ok || !resultado.data) {
    throw erroDeResultado(resultado.error, resultado.response.status)
  }

  return paraAvaliacao(resultado.data)
}
