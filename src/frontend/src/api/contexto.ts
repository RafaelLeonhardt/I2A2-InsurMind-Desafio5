const BASE_API = 'http://127.0.0.1:8000/api/v1'
export const URL_SEGURADO_PADRAO = `${BASE_API}/segurados/padrao`

/** Segurado sintético padrão, conforme o contrato REST/JSON do backend. */
export type SeguradoPadrao = {
  id: string
  nome: string
}

type CorpoProblema = {
  codigo?: string
  correlacao_id?: string
  ocorrencia?: string
  impacto?: string
  proxima_acao?: string
}

type DadosErroContexto = {
  codigo: string
  correlacaoId: string | null
  ocorrencia: string
  impacto: string
  proximaAcao: string
  status: number | null
}

/** Falha tipada ao consultar o contexto demonstrativo, com ocorrência, impacto e próxima ação segura. */
export class ErroContexto extends Error {
  readonly codigo: string
  readonly correlacaoId: string | null
  readonly ocorrencia: string
  readonly impacto: string
  readonly proximaAcao: string
  readonly status: number | null

  constructor(dados: DadosErroContexto) {
    super(dados.ocorrencia)
    this.name = 'ErroContexto'
    this.codigo = dados.codigo
    this.correlacaoId = dados.correlacaoId
    this.ocorrencia = dados.ocorrencia
    this.impacto = dados.impacto
    this.proximaAcao = dados.proximaAcao
    this.status = dados.status
  }
}

const FALHA_INESPERADA = {
  ocorrencia: 'O segurado sintético padrão não pôde ser consultado.',
  impacto: 'A barra de contexto não pode exibir o segurado ativo no momento.',
  proximaAcao: 'Verifique se o backend local está disponível e tente novamente.',
}

const FALHA_DE_REDE = {
  codigo: 'falha_de_rede',
  correlacaoId: null,
  ocorrencia: 'Não foi possível falar com o backend local da Central Preventiva.',
  impacto: 'A barra de contexto não pode exibir o segurado ativo no momento.',
  proximaAcao: 'Confirme que o backend está em execução em 127.0.0.1:8000 e tente de novo.',
  status: null,
}

async function lerProblema(resposta: Response): Promise<ErroContexto> {
  let corpo: CorpoProblema = {}
  try {
    corpo = (await resposta.json()) as CorpoProblema
  } catch {
    corpo = {}
  }

  return new ErroContexto({
    codigo: corpo.codigo ?? 'falha_inesperada',
    correlacaoId: corpo.correlacao_id ?? null,
    ocorrencia: corpo.ocorrencia ?? FALHA_INESPERADA.ocorrencia,
    impacto: corpo.impacto ?? FALHA_INESPERADA.impacto,
    proximaAcao: corpo.proxima_acao ?? FALHA_INESPERADA.proximaAcao,
    status: resposta.status,
  })
}

/** Consulta o segurado sintético padrão da demonstração. */
export async function getSeguradoPadrao(): Promise<SeguradoPadrao> {
  let resposta: Response
  try {
    resposta = await fetch(URL_SEGURADO_PADRAO, { headers: { Accept: 'application/json' } })
  } catch {
    throw new ErroContexto(FALHA_DE_REDE)
  }

  if (!resposta.ok) {
    throw await lerProblema(resposta)
  }

  const corpo = (await resposta.json()) as { id: string; nome: string }
  return { id: corpo.id, nome: corpo.nome }
}
