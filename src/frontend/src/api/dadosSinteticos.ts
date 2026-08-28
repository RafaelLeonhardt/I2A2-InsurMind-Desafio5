const BASE_API = 'http://127.0.0.1:8000/api/v1'
export const URL_RESTAURACOES = `${BASE_API}/dados-sinteticos/restauracoes`

/** Restauração concluída, conforme o contrato REST/JSON do backend. */
export type ResultadoRestauracao = {
  status: 'restaurado'
  restauradoEm: string
}

type CorpoProblema = {
  codigo?: string
  correlacao_id?: string
  ocorrencia?: string
  impacto?: string
  proxima_acao?: string
}

type DadosErroRestauracao = {
  codigo: string
  correlacaoId: string | null
  ocorrencia: string
  impacto: string
  proximaAcao: string
  status: number | null
}

/** Falha tipada da restauração, com ocorrência, impacto e próxima ação segura. */
export class ErroRestauracao extends Error {
  readonly codigo: string
  readonly correlacaoId: string | null
  readonly ocorrencia: string
  readonly impacto: string
  readonly proximaAcao: string
  readonly status: number | null

  constructor(dados: DadosErroRestauracao) {
    super(dados.ocorrencia)
    this.name = 'ErroRestauracao'
    this.codigo = dados.codigo
    this.correlacaoId = dados.correlacaoId
    this.ocorrencia = dados.ocorrencia
    this.impacto = dados.impacto
    this.proximaAcao = dados.proximaAcao
    this.status = dados.status
  }
}

const FALHA_INESPERADA = {
  ocorrencia: 'A restauração não pôde ser concluída.',
  impacto: 'O conjunto de dados anterior foi preservado e continua consultável.',
  proximaAcao: 'Verifique se o backend local está disponível e tente novamente.',
}

async function lerProblema(resposta: Response): Promise<ErroRestauracao> {
  let corpo: CorpoProblema = {}
  try {
    corpo = (await resposta.json()) as CorpoProblema
  } catch {
    corpo = {}
  }

  return new ErroRestauracao({
    codigo: corpo.codigo ?? 'falha_inesperada',
    correlacaoId: corpo.correlacao_id ?? null,
    ocorrencia: corpo.ocorrencia ?? FALHA_INESPERADA.ocorrencia,
    impacto: corpo.impacto ?? FALHA_INESPERADA.impacto,
    proximaAcao: corpo.proxima_acao ?? FALHA_INESPERADA.proximaAcao,
    status: resposta.status,
  })
}

/** Solicita a restauração dos dados sintéticos com uma `Idempotency-Key` nova. */
export async function restaurarDadosSinteticos(): Promise<ResultadoRestauracao> {
  let resposta: Response
  try {
    resposta = await fetch(URL_RESTAURACOES, {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        'Idempotency-Key': crypto.randomUUID(),
      },
    })
  } catch {
    throw new ErroRestauracao({
      codigo: 'falha_de_rede',
      correlacaoId: null,
      ocorrencia: 'Não foi possível falar com o backend local da Central Preventiva.',
      impacto: 'Nenhuma restauração foi solicitada e os dados permanecem como estavam.',
      proximaAcao: 'Confirme que o backend está em execução em 127.0.0.1:8000 e tente de novo.',
      status: null,
    })
  }

  if (!resposta.ok) {
    throw await lerProblema(resposta)
  }

  const corpo = (await resposta.json()) as { restaurado_em: string }
  return { status: 'restaurado', restauradoEm: corpo.restaurado_em }
}
