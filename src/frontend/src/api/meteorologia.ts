import { clienteApi } from './clienteHttp'
import type { components } from './tipos-gerados'

/** Evento meteorológico normalizado, conforme o contrato REST/JSON do backend. */
export type EventoMeteorologico = {
  id: string
  tipo: string
  area: string
  periodoInicio: string
  periodoFim: string
  intensidade: number
  proveniencia: string
  instanteObservado: string
}

/** Registro de uma tentativa de sincronização meteorológica. */
export type Sincronizacao = {
  id: string
  requisicaoId: string
  origem: string
  estado: string
  registrosValidos: number
  motivoFalha: string | null
  iniciadoEm: string
  finalizadoEm: string | null
}

/** Histórico de sincronização, com os marcos exigidos pela consulta de Marina. */
export type HistoricoSincronizacoes = {
  ultimaTentativa: Sincronizacao | null
  ultimaValida: Sincronizacao | null
  proximaConsulta: string | null
  resultadosAnteriores: Sincronizacao[]
}

/** Ack de uma coleta manual aceita ou já registrada. */
export type ColetaAceita = {
  id: string
  requisicaoId: string
  estado: string
  registrosValidos: number
  motivoFalha: string | null
  aceitoEm: string
}

type CorpoProblema = Partial<components['schemas']['ProblemaMeteorologia']>

type DadosErroMeteorologia = {
  codigo: string
  correlacaoId: string | null
  ocorrencia: string
  impacto: string
  proximaAcao: string
  status: number | null
}

/** Falha tipada de uma operação meteorológica, com ocorrência, impacto e próxima ação segura. */
export class ErroMeteorologia extends Error {
  readonly codigo: string
  readonly correlacaoId: string | null
  readonly ocorrencia: string
  readonly impacto: string
  readonly proximaAcao: string
  readonly status: number | null

  constructor(dados: DadosErroMeteorologia) {
    super(dados.ocorrencia)
    this.name = 'ErroMeteorologia'
    this.codigo = dados.codigo
    this.correlacaoId = dados.correlacaoId
    this.ocorrencia = dados.ocorrencia
    this.impacto = dados.impacto
    this.proximaAcao = dados.proximaAcao
    this.status = dados.status
  }
}

const FALHA_INESPERADA = {
  ocorrencia: 'A operação meteorológica não pôde ser concluída.',
  impacto: 'Os dados meteorológicos conhecidos até agora permanecem disponíveis para consulta.',
  proximaAcao: 'Verifique se o backend local está disponível e tente novamente.',
}

const FALHA_DE_REDE: DadosErroMeteorologia = {
  codigo: 'falha_de_rede',
  correlacaoId: null,
  ocorrencia: 'Não foi possível falar com o backend local da Central Preventiva.',
  impacto: 'Nenhuma operação meteorológica foi concluída.',
  proximaAcao: 'Confirme que o backend está em execução em 127.0.0.1:8000 e tente de novo.',
  status: null,
}

/**
 * Converte o erro já desserializado pelo `openapi-fetch` em `ErroMeteorologia`.
 *
 * O corpo não é relido de `Response` (o `openapi-fetch` já consumiu o stream ao
 * desserializar `data`/`error`); reler geraria um erro de stream já consumido.
 */
function erroDeResultado(erro: unknown, status: number): ErroMeteorologia {
  const corpo = (erro ?? {}) as CorpoProblema
  return new ErroMeteorologia({
    codigo: corpo.codigo ?? 'falha_inesperada',
    correlacaoId: corpo.correlacao_id ?? null,
    ocorrencia: corpo.ocorrencia ?? FALHA_INESPERADA.ocorrencia,
    impacto: corpo.impacto ?? FALHA_INESPERADA.impacto,
    proximaAcao: corpo.proxima_acao ?? FALHA_INESPERADA.proximaAcao,
    status,
  })
}

function paraSincronizacao(corpo: components['schemas']['RespostaSincronizacao']): Sincronizacao {
  return {
    id: corpo.id,
    requisicaoId: corpo.requisicao_id,
    origem: corpo.origem,
    estado: corpo.estado,
    registrosValidos: corpo.registros_validos,
    motivoFalha: corpo.motivo_falha,
    iniciadoEm: corpo.iniciado_em,
    finalizadoEm: corpo.finalizado_em,
  }
}

function paraEvento(corpo: components['schemas']['RespostaEvento']): EventoMeteorologico {
  return {
    id: corpo.id,
    tipo: corpo.tipo,
    area: corpo.area,
    periodoInicio: corpo.periodo_inicio,
    periodoFim: corpo.periodo_fim,
    intensidade: corpo.intensidade,
    proveniencia: corpo.proveniencia,
    instanteObservado: corpo.instante_observado,
  }
}

async function chamarColeta(areaId: string) {
  return clienteApi.POST('/api/v1/meteorologia/coletas', {
    params: { header: { 'Idempotency-Key': crypto.randomUUID() } },
    body: { area_id: areaId },
    fetch,
  })
}

async function chamarEventos() {
  return clienteApi.GET('/api/v1/meteorologia/eventos', { fetch })
}

async function chamarSincronizacoes() {
  return clienteApi.GET('/api/v1/meteorologia/sincronizacoes', { fetch })
}

/** Solicita uma coleta meteorológica manual para a área informada, com `Idempotency-Key` nova. */
export async function solicitarColeta(areaId: string): Promise<ColetaAceita> {
  let resultado: Awaited<ReturnType<typeof chamarColeta>>
  try {
    resultado = await chamarColeta(areaId)
  } catch {
    throw new ErroMeteorologia(FALHA_DE_REDE)
  }

  if (!resultado.response.ok || !resultado.data) {
    throw erroDeResultado(resultado.error, resultado.response.status)
  }

  const corpo = resultado.data
  return {
    id: corpo.id,
    requisicaoId: corpo.requisicao_id,
    estado: corpo.estado,
    registrosValidos: corpo.registros_validos,
    motivoFalha: corpo.motivo_falha,
    aceitoEm: corpo.aceito_em,
  }
}

/** Consulta os eventos meteorológicos normalizados, do mais recente para o mais antigo. */
export async function getEventos(): Promise<EventoMeteorologico[]> {
  let resultado: Awaited<ReturnType<typeof chamarEventos>>
  try {
    resultado = await chamarEventos()
  } catch {
    throw new ErroMeteorologia(FALHA_DE_REDE)
  }

  if (!resultado.response.ok || !resultado.data) {
    throw erroDeResultado(resultado.error, resultado.response.status)
  }

  return resultado.data.eventos.map(paraEvento)
}

/** Consulta o histórico de sincronizações meteorológicas, só com dados persistidos. */
export async function getSincronizacoes(): Promise<HistoricoSincronizacoes> {
  let resultado: Awaited<ReturnType<typeof chamarSincronizacoes>>
  try {
    resultado = await chamarSincronizacoes()
  } catch {
    throw new ErroMeteorologia(FALHA_DE_REDE)
  }

  if (!resultado.response.ok || !resultado.data) {
    throw erroDeResultado(resultado.error, resultado.response.status)
  }

  const corpo = resultado.data
  return {
    ultimaTentativa: corpo.ultima_tentativa ? paraSincronizacao(corpo.ultima_tentativa) : null,
    ultimaValida: corpo.ultima_valida ? paraSincronizacao(corpo.ultima_valida) : null,
    proximaConsulta: corpo.proxima_consulta,
    resultadosAnteriores: corpo.resultados_anteriores.map(paraSincronizacao),
  }
}
