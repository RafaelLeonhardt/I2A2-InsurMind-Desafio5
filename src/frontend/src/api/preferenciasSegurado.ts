import { clienteApi } from './clienteHttp'
import type { components } from './tipos-gerados'

/** Canal preferencial, participação em alertas e versão corrente do segurado (5.6). */
export type PreferenciasSegurado = {
  seguradoId: string
  canalPreferido: string
  participaDeAlertas: boolean
  versao: number
}

type CorpoProblema = Partial<components['schemas']['ErroPreferenciasSegurado']>

type DadosErroPreferenciasSegurado = {
  codigo: string
  correlacaoId: string | null
  ocorrencia: string
  impacto: string
  proximaAcao: string
  status: number | null
}

/** Falha tipada de uma consulta/atualização de preferências, com ocorrência, impacto e
 * próxima ação segura. */
export class ErroPreferenciasSegurado extends Error {
  readonly codigo: string
  readonly correlacaoId: string | null
  readonly ocorrencia: string
  readonly impacto: string
  readonly proximaAcao: string
  readonly status: number | null

  constructor(dados: DadosErroPreferenciasSegurado) {
    super(dados.ocorrencia)
    this.name = 'ErroPreferenciasSegurado'
    this.codigo = dados.codigo
    this.correlacaoId = dados.correlacaoId
    this.ocorrencia = dados.ocorrencia
    this.impacto = dados.impacto
    this.proximaAcao = dados.proximaAcao
    this.status = dados.status
  }
}

const FALHA_INESPERADA = {
  ocorrencia: 'As preferências não puderam ser atualizadas.',
  impacto: 'O canal preferencial e a participação em alertas permanecem como estavam.',
  proximaAcao: 'Verifique se o backend local está disponível e tente novamente.',
}

const FALHA_DE_REDE: DadosErroPreferenciasSegurado = {
  codigo: 'falha_de_rede',
  correlacaoId: null,
  ocorrencia: 'Não foi possível falar com o backend local da Central Preventiva.',
  impacto: 'Nenhuma preferência foi atualizada.',
  proximaAcao: 'Confirme que o backend está em execução em 127.0.0.1:8000 e tente de novo.',
  status: null,
}

function erroDeResultado(erro: unknown, status: number): ErroPreferenciasSegurado {
  const corpo = (erro ?? {}) as CorpoProblema
  return new ErroPreferenciasSegurado({
    codigo: corpo.codigo ?? 'falha_inesperada',
    correlacaoId: corpo.correlacao_id ?? null,
    ocorrencia: corpo.ocorrencia ?? FALHA_INESPERADA.ocorrencia,
    impacto: corpo.impacto ?? FALHA_INESPERADA.impacto,
    proximaAcao: corpo.proxima_acao ?? FALHA_INESPERADA.proximaAcao,
    status,
  })
}

function paraPreferencias(
  corpo: components['schemas']['RespostaPreferencias'],
): PreferenciasSegurado {
  return {
    seguradoId: corpo.segurado_id,
    canalPreferido: corpo.canal_preferido,
    participaDeAlertas: corpo.participa_de_alertas,
    versao: corpo.versao,
  }
}

async function chamarConsultar(seguradoId: string) {
  return clienteApi.GET('/api/v1/segurados/{segurado_id}/preferencias', {
    params: { path: { segurado_id: seguradoId } },
    fetch,
  })
}

async function chamarAtualizar(
  seguradoId: string,
  versaoEsperada: number,
  canalPreferido: string,
  participaDeAlertas: boolean,
) {
  return clienteApi.PUT('/api/v1/segurados/{segurado_id}/preferencias', {
    params: {
      header: { 'Idempotency-Key': crypto.randomUUID() },
      path: { segurado_id: seguradoId },
    },
    body: {
      canal_preferido: canalPreferido,
      participa_de_alertas: participaDeAlertas,
      versao_esperada: versaoEsperada,
    },
    fetch,
  })
}

/** Consulta o canal preferencial, a participação em alertas e a versão corrente do
 * segurado ativo. */
export async function getPreferencias(seguradoId: string): Promise<PreferenciasSegurado> {
  let resultado: Awaited<ReturnType<typeof chamarConsultar>>
  try {
    resultado = await chamarConsultar(seguradoId)
  } catch {
    throw new ErroPreferenciasSegurado(FALHA_DE_REDE)
  }

  if (!resultado.response.ok || !resultado.data) {
    throw erroDeResultado(resultado.error, resultado.response.status)
  }

  return paraPreferencias(resultado.data)
}

/** Atualiza canal preferencial e participação em alertas, com `Idempotency-Key` nova a
 * cada chamada (5.6, PREFS-02/03). */
export async function atualizarPreferencias(
  seguradoId: string,
  versaoEsperada: number,
  canalPreferido: string,
  participaDeAlertas: boolean,
): Promise<PreferenciasSegurado> {
  let resultado: Awaited<ReturnType<typeof chamarAtualizar>>
  try {
    resultado = await chamarAtualizar(seguradoId, versaoEsperada, canalPreferido, participaDeAlertas)
  } catch {
    throw new ErroPreferenciasSegurado(FALHA_DE_REDE)
  }

  if (!resultado.response.ok || !resultado.data) {
    throw erroDeResultado(resultado.error, resultado.response.status)
  }

  return paraPreferencias(resultado.data)
}
