import { clienteApi } from './clienteHttp'
import type { components } from './tipos-gerados'

/** Configuração de regra proposta, no formato aceito por `testar`/`ativar`. */
export type DadosRegra = {
  eventoTipo: string
  limiarMeteorologico: number
  areaAplicavel: string
  apoliceTipo: string
  coberturaExigida: string
  antecedenciaHoras: number
  canal: string
}

/** Uma versão de regra, para consulta e auditoria. */
export type Regra = DadosRegra & {
  id: string
  versao: number
  estado: string
}

/** Um critério avaliado no teste determinístico: operando, valor, resultado e justificativa. */
export type Criterio = {
  operando: string
  valorObservado: string
  atende: boolean
  justificativa: string
}

/** Um caso de teste determinístico: o cenário sintético usado e o resultado obtido. */
export type CasoTeste = {
  eventoId: string
  relevante: boolean
  criterios: Criterio[]
  motivo: string
}

/** Um erro de validação localizado a um campo específico, em português brasileiro. */
export type ErroCampo = {
  campo: string
  motivo: string
}

type CorpoProblema = Partial<components['schemas']['ProblemaRegras']>

type DadosErroRegras = {
  codigo: string
  correlacaoId: string | null
  ocorrencia: string
  impacto: string
  proximaAcao: string
  status: number | null
  erros: ErroCampo[]
}

/** Falha tipada de uma operação de regras, com ocorrência, impacto e próxima ação segura. */
export class ErroRegras extends Error {
  readonly codigo: string
  readonly correlacaoId: string | null
  readonly ocorrencia: string
  readonly impacto: string
  readonly proximaAcao: string
  readonly status: number | null
  readonly erros: ErroCampo[]

  constructor(dados: DadosErroRegras) {
    super(dados.ocorrencia)
    this.name = 'ErroRegras'
    this.codigo = dados.codigo
    this.correlacaoId = dados.correlacaoId
    this.ocorrencia = dados.ocorrencia
    this.impacto = dados.impacto
    this.proximaAcao = dados.proximaAcao
    this.status = dados.status
    this.erros = dados.erros
  }
}

const FALHA_INESPERADA = {
  ocorrencia: 'A operação de regras não pôde ser concluída.',
  impacto: 'As regras já ativas permanecem em vigor, sem alteração.',
  proximaAcao: 'Verifique se o backend local está disponível e tente novamente.',
}

const FALHA_DE_REDE: DadosErroRegras = {
  codigo: 'falha_de_rede',
  correlacaoId: null,
  ocorrencia: 'Não foi possível falar com o backend local da Central Preventiva.',
  impacto: 'Nenhuma operação de regras foi concluída.',
  proximaAcao: 'Confirme que o backend está em execução em 127.0.0.1:8000 e tente de novo.',
  status: null,
  erros: [],
}

/**
 * Converte o erro já desserializado pelo `openapi-fetch` em `ErroRegras`.
 *
 * O corpo não é relido de `Response` (o `openapi-fetch` já consumiu o stream ao
 * desserializar `data`/`error`); reler geraria um erro de stream já consumido.
 */
function erroDeResultado(erro: unknown, status: number): ErroRegras {
  const corpo = (erro ?? {}) as CorpoProblema
  return new ErroRegras({
    codigo: corpo.codigo ?? 'falha_inesperada',
    correlacaoId: corpo.correlacao_id ?? null,
    ocorrencia: corpo.ocorrencia ?? FALHA_INESPERADA.ocorrencia,
    impacto: corpo.impacto ?? FALHA_INESPERADA.impacto,
    proximaAcao: corpo.proxima_acao ?? FALHA_INESPERADA.proximaAcao,
    status,
    erros: (corpo.erros ?? []).map((erro) => ({ campo: erro.campo, motivo: erro.motivo })),
  })
}

function paraDadosRegra(corpo: {
  evento_tipo: string
  limiar_meteorologico: number
  area_aplicavel: string
  apolice_tipo: string
  cobertura_exigida: string
  antecedencia_horas: number
  canal: string
}): DadosRegra {
  return {
    eventoTipo: corpo.evento_tipo,
    limiarMeteorologico: corpo.limiar_meteorologico,
    areaAplicavel: corpo.area_aplicavel,
    apoliceTipo: corpo.apolice_tipo,
    coberturaExigida: corpo.cobertura_exigida,
    antecedenciaHoras: corpo.antecedencia_horas,
    canal: corpo.canal,
  }
}

function paraRegra(corpo: components['schemas']['RespostaRegra']): Regra {
  return {
    ...paraDadosRegra(corpo),
    id: corpo.id,
    versao: corpo.versao,
    estado: corpo.estado,
  }
}

function paraCriterio(corpo: components['schemas']['RespostaCriterioTeste']): Criterio {
  return {
    operando: corpo.operando,
    valorObservado: corpo.valor_observado,
    atende: corpo.atende,
    justificativa: corpo.justificativa,
  }
}

function paraCasoTeste(corpo: components['schemas']['RespostaCasoTeste']): CasoTeste {
  return {
    eventoId: corpo.evento_id,
    relevante: corpo.relevante,
    criterios: corpo.criterios.map(paraCriterio),
    motivo: corpo.motivo,
  }
}

function corpoDadosRegra(dados: DadosRegra) {
  return {
    evento_tipo: dados.eventoTipo,
    limiar_meteorologico: dados.limiarMeteorologico,
    area_aplicavel: dados.areaAplicavel,
    apolice_tipo: dados.apoliceTipo,
    cobertura_exigida: dados.coberturaExigida,
    antecedencia_horas: dados.antecedenciaHoras,
    canal: dados.canal,
  }
}

async function chamarRegras() {
  return clienteApi.GET('/api/v1/regras', { fetch })
}

async function chamarRegra(regraId: string) {
  return clienteApi.GET('/api/v1/regras/{regra_id}', {
    params: { path: { regra_id: regraId } },
    fetch,
  })
}

async function chamarTestar(regraId: string, dados: DadosRegra) {
  return clienteApi.POST('/api/v1/regras/{regra_id}/testar', {
    params: { path: { regra_id: regraId } },
    body: corpoDadosRegra(dados),
    fetch,
  })
}

async function chamarAtivar(regraId: string, versaoEsperada: number, dados: DadosRegra) {
  return clienteApi.POST('/api/v1/regras/{regra_id}/ativar', {
    params: {
      header: { 'Idempotency-Key': crypto.randomUUID() },
      path: { regra_id: regraId },
    },
    body: { ...corpoDadosRegra(dados), versao_esperada: versaoEsperada },
    fetch,
  })
}

/** Consulta todas as versões de regra registradas, ativas e substituídas. */
export async function getRegras(): Promise<Regra[]> {
  let resultado: Awaited<ReturnType<typeof chamarRegras>>
  try {
    resultado = await chamarRegras()
  } catch {
    throw new ErroRegras(FALHA_DE_REDE)
  }

  if (!resultado.response.ok || !resultado.data) {
    throw erroDeResultado(resultado.error, resultado.response.status)
  }

  return resultado.data.regras.map(paraRegra)
}

/** Consulta uma versão específica de regra pelo seu identificador. */
export async function getRegra(regraId: string): Promise<Regra> {
  let resultado: Awaited<ReturnType<typeof chamarRegra>>
  try {
    resultado = await chamarRegra(regraId)
  } catch {
    throw new ErroRegras(FALHA_DE_REDE)
  }

  if (!resultado.response.ok || !resultado.data) {
    throw erroDeResultado(resultado.error, resultado.response.status)
  }

  return paraRegra(resultado.data)
}

/**
 * Testa deterministicamente `dados` contra os cenários sintéticos do tipo de evento
 * (RISCO-11/12 do lado de regras: nenhum cálculo é replicado no frontend).
 */
export async function testarRegra(regraId: string, dados: DadosRegra): Promise<CasoTeste[]> {
  let resultado: Awaited<ReturnType<typeof chamarTestar>>
  try {
    resultado = await chamarTestar(regraId, dados)
  } catch {
    throw new ErroRegras(FALHA_DE_REDE)
  }

  if (!resultado.response.ok || !resultado.data) {
    throw erroDeResultado(resultado.error, resultado.response.status)
  }

  return resultado.data.casos.map(paraCasoTeste)
}

/** Ativa `dados` como nova versão de `regraId`, com `Idempotency-Key` nova a cada chamada. */
export async function ativarRegra(
  regraId: string,
  versaoEsperada: number,
  dados: DadosRegra,
): Promise<Regra> {
  let resultado: Awaited<ReturnType<typeof chamarAtivar>>
  try {
    resultado = await chamarAtivar(regraId, versaoEsperada, dados)
  } catch {
    throw new ErroRegras(FALHA_DE_REDE)
  }

  if (!resultado.response.ok || !resultado.data) {
    throw erroDeResultado(resultado.error, resultado.response.status)
  }

  return paraRegra(resultado.data)
}
