const BASE_API = 'http://127.0.0.1:8000/api/v1'
export const URL_DEPENDENCIAS = `${BASE_API}/prontidao/dependencias`

/** Nomes canônicos das 4 dependências cuja prontidão é verificada. */
export type NomeDependencia = 'backend' | 'banco_dados' | 'inmet' | 'openai'

/** Estado de prontidão de uma dependência, conforme o contrato REST/JSON do backend. */
export type EstadoDependencia = {
  nome: NomeDependencia
  estado: 'verificando' | 'disponivel' | 'degradada' | 'indisponivel'
  verificadoEm: string | null
  causa: string | null
  impacto: string
  acaoDisponivel: string
}

/** Ack de uma nova verificação aceita, conforme o contrato REST/JSON do backend. */
export type VerificacaoAceita = {
  nome: NomeDependencia
  estado: 'verificando' | 'disponivel' | 'degradada' | 'indisponivel'
  aceitoEm: string
}

type CorpoProblema = {
  codigo?: string
  correlacao_id?: string
  ocorrencia?: string
  impacto?: string
  proxima_acao?: string
}

type CorpoDependencia = {
  nome: NomeDependencia
  estado: EstadoDependencia['estado']
  verificado_em: string | null
  causa: string | null
  impacto: string
  acao_disponivel: string
}

type CorpoVerificacaoAceita = {
  nome: NomeDependencia
  estado: VerificacaoAceita['estado']
  aceito_em: string
}

type DadosErroProntidao = {
  codigo: string
  correlacaoId: string | null
  ocorrencia: string
  impacto: string
  proximaAcao: string
  status: number | null
}

/** Falha tipada de uma operação de prontidão, com ocorrência, impacto e próxima ação segura. */
export class ErroProntidao extends Error {
  readonly codigo: string
  readonly correlacaoId: string | null
  readonly ocorrencia: string
  readonly impacto: string
  readonly proximaAcao: string
  readonly status: number | null

  constructor(dados: DadosErroProntidao) {
    super(dados.ocorrencia)
    this.name = 'ErroProntidao'
    this.codigo = dados.codigo
    this.correlacaoId = dados.correlacaoId
    this.ocorrencia = dados.ocorrencia
    this.impacto = dados.impacto
    this.proximaAcao = dados.proximaAcao
    this.status = dados.status
  }
}

const FALHA_INESPERADA = {
  ocorrencia: 'A operação de prontidão não pôde ser concluída.',
  impacto: 'O estado de prontidão conhecido até agora permanece disponível para consulta.',
  proximaAcao: 'Verifique se o backend local está disponível e tente novamente.',
}

const FALHA_DE_REDE = {
  codigo: 'falha_de_rede',
  correlacaoId: null,
  ocorrencia: 'Não foi possível falar com o backend local da Central Preventiva.',
  impacto: 'Nenhuma operação de prontidão foi concluída.',
  proximaAcao: 'Confirme que o backend está em execução em 127.0.0.1:8000 e tente de novo.',
  status: null,
}

async function lerProblema(resposta: Response): Promise<ErroProntidao> {
  let corpo: CorpoProblema = {}
  try {
    corpo = (await resposta.json()) as CorpoProblema
  } catch {
    corpo = {}
  }

  return new ErroProntidao({
    codigo: corpo.codigo ?? 'falha_inesperada',
    correlacaoId: corpo.correlacao_id ?? null,
    ocorrencia: corpo.ocorrencia ?? FALHA_INESPERADA.ocorrencia,
    impacto: corpo.impacto ?? FALHA_INESPERADA.impacto,
    proximaAcao: corpo.proxima_acao ?? FALHA_INESPERADA.proximaAcao,
    status: resposta.status,
  })
}

function paraEstadoDependencia(corpo: CorpoDependencia): EstadoDependencia {
  return {
    nome: corpo.nome,
    estado: corpo.estado,
    verificadoEm: corpo.verificado_em,
    causa: corpo.causa,
    impacto: corpo.impacto,
    acaoDisponivel: corpo.acao_disponivel,
  }
}

/** Consulta o estado de prontidão das 4 dependências. */
export async function getDependencias(): Promise<EstadoDependencia[]> {
  let resposta: Response
  try {
    resposta = await fetch(URL_DEPENDENCIAS, { headers: { Accept: 'application/json' } })
  } catch {
    throw new ErroProntidao(FALHA_DE_REDE)
  }

  if (!resposta.ok) {
    throw await lerProblema(resposta)
  }

  const corpo = (await resposta.json()) as { dependencias: CorpoDependencia[] }
  return corpo.dependencias.map(paraEstadoDependencia)
}

/** Solicita uma nova verificação da dependência informada, com uma `Idempotency-Key` nova. */
export async function solicitarNovaVerificacao(
  nome: NomeDependencia,
): Promise<VerificacaoAceita> {
  let resposta: Response
  try {
    resposta = await fetch(`${URL_DEPENDENCIAS}/${nome}/verificacoes`, {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        'Idempotency-Key': crypto.randomUUID(),
      },
    })
  } catch {
    throw new ErroProntidao(FALHA_DE_REDE)
  }

  if (!resposta.ok) {
    throw await lerProblema(resposta)
  }

  const corpo = (await resposta.json()) as CorpoVerificacaoAceita
  return { nome: corpo.nome, estado: corpo.estado, aceitoEm: corpo.aceito_em }
}
