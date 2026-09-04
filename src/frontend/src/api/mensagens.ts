import { clienteApi } from './clienteHttp'
import type { components } from './tipos-gerados'

/** Metadados da versão atual de uma mensagem: veredito determinístico e proveniência. */
export type VersaoMensagem = {
  numeroTentativa: number
  valida: boolean
  motivoInvalidez: string | null
  modelo: string
  versaoPrompt: string
  duracaoMs: number
  tokensEntrada: number | null
  tokensSaida: number | null
  criadoEm: string
}

/** Uma mensagem persistida de uma execução: origem, canal, estado e versão atual. */
export type Mensagem = {
  id: string
  elegibilidadeId: string
  canal: string
  estado: string
  tentativaAtual: number
  limiteTentativas: number
  versao: number
  versaoAtual: VersaoMensagem | null
}

type CorpoProblema = Partial<components['schemas']['ProblemaMensagens']>

type DadosErroMensagens = {
  codigo: string
  correlacaoId: string | null
  ocorrencia: string
  impacto: string
  proximaAcao: string
  status: number | null
}

/** Falha tipada da consulta de mensagens, com ocorrência, impacto e próxima ação segura. */
export class ErroMensagens extends Error {
  readonly codigo: string
  readonly correlacaoId: string | null
  readonly ocorrencia: string
  readonly impacto: string
  readonly proximaAcao: string
  readonly status: number | null

  constructor(dados: DadosErroMensagens) {
    super(dados.ocorrencia)
    this.name = 'ErroMensagens'
    this.codigo = dados.codigo
    this.correlacaoId = dados.correlacaoId
    this.ocorrencia = dados.ocorrencia
    this.impacto = dados.impacto
    this.proximaAcao = dados.proximaAcao
    this.status = dados.status
  }
}

const FALHA_INESPERADA = {
  ocorrencia: 'A consulta das mensagens não pôde ser concluída.',
  impacto: 'O acompanhamento da geração pode estar incompleto.',
  proximaAcao: 'Verifique se o backend local está disponível e tente novamente.',
}

const FALHA_DE_REDE: DadosErroMensagens = {
  codigo: 'falha_de_rede',
  correlacaoId: null,
  ocorrencia: 'Não foi possível falar com o backend local da Central Preventiva.',
  impacto: 'Nenhuma mensagem pôde ser consultada.',
  proximaAcao: 'Confirme que o backend está em execução em 127.0.0.1:8000 e tente de novo.',
  status: null,
}

/** Converte o erro já desserializado pelo `openapi-fetch` em `ErroMensagens`. */
function erroDeResultado(erro: unknown, status: number): ErroMensagens {
  const corpo = (erro ?? {}) as CorpoProblema
  return new ErroMensagens({
    codigo: corpo.codigo ?? 'falha_inesperada',
    correlacaoId: corpo.correlacao_id ?? null,
    ocorrencia: corpo.ocorrencia ?? FALHA_INESPERADA.ocorrencia,
    impacto: corpo.impacto ?? FALHA_INESPERADA.impacto,
    proximaAcao: corpo.proxima_acao ?? FALHA_INESPERADA.proximaAcao,
    status,
  })
}

function paraVersao(
  corpo: components['schemas']['RespostaVersaoMensagem'] | null
): VersaoMensagem | null {
  if (corpo === null) return null
  return {
    numeroTentativa: corpo.numero_tentativa,
    valida: corpo.valida,
    motivoInvalidez: corpo.motivo_invalidez,
    modelo: corpo.modelo,
    versaoPrompt: corpo.versao_prompt,
    duracaoMs: corpo.duracao_ms,
    tokensEntrada: corpo.tokens_entrada,
    tokensSaida: corpo.tokens_saida,
    criadoEm: corpo.criado_em,
  }
}

function paraMensagem(corpo: components['schemas']['RespostaMensagem']): Mensagem {
  return {
    id: corpo.id,
    elegibilidadeId: corpo.elegibilidade_id,
    canal: corpo.canal,
    estado: corpo.estado,
    tentativaAtual: corpo.tentativa_atual,
    limiteTentativas: corpo.limite_tentativas,
    versao: corpo.versao,
    versaoAtual: paraVersao(corpo.versao_atual),
  }
}

async function chamarMensagens(execucaoId: string) {
  return clienteApi.GET('/api/v1/execucoes/{execucao_id}/mensagens', {
    params: { path: { execucao_id: execucaoId } },
    fetch,
  })
}

/**
 * Consulta as mensagens já persistidas de uma execução.
 *
 * Só leitura: nenhuma chamada do frontend inicia, reenvia ou repete a geração — ela é
 * acionada pelo backend ao entrar em `processando_mensagens` (GERAR-04, GERAR-12).
 */
export async function getMensagens(execucaoId: string): Promise<Mensagem[]> {
  let resultado: Awaited<ReturnType<typeof chamarMensagens>>
  try {
    resultado = await chamarMensagens(execucaoId)
  } catch {
    throw new ErroMensagens(FALHA_DE_REDE)
  }

  if (!resultado.response.ok || !resultado.data) {
    throw erroDeResultado(resultado.error, resultado.response.status)
  }

  return resultado.data.registros.map(paraMensagem)
}
