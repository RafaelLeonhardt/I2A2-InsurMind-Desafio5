import { clienteApi, ENDERECO_BASE_API } from './clienteHttp'

export const ENDERECO_SWAGGER_UI = `${ENDERECO_BASE_API}/docs`
export const ENDERECO_OPENAPI = `${ENDERECO_BASE_API}/openapi.json`

/** Estado de disponibilidade da documentação da API, conforme exibido pela superfície. */
export type EstadoDocumentacaoApi = 'carregando' | 'disponivel' | 'indisponivel'

/** Resultado de sucesso da verificação de disponibilidade da documentação da API. */
export type ResultadoDocumentacaoApi = {
  estado: 'disponivel'
  enderecoSwaggerUi: string
  enderecoOpenApi: string
}

type DadosErroDocumentacaoApi = {
  causa: string
  impacto: string
  proximaAcao: string
  enderecoEsperado: string
}

/** Falha tipada ao verificar a disponibilidade da documentação da API. */
export class ErroDocumentacaoApi extends Error {
  readonly causa: string
  readonly impacto: string
  readonly proximaAcao: string
  readonly enderecoEsperado: string

  constructor(dados: DadosErroDocumentacaoApi) {
    super(dados.causa)
    this.name = 'ErroDocumentacaoApi'
    this.causa = dados.causa
    this.impacto = dados.impacto
    this.proximaAcao = dados.proximaAcao
    this.enderecoEsperado = dados.enderecoEsperado
  }
}

const FALHA_DE_REDE: DadosErroDocumentacaoApi = {
  causa: 'Não foi possível falar com o backend local da Central Preventiva.',
  impacto: 'A documentação da API (Swagger UI e openapi.json) não pode ser confirmada como disponível.',
  proximaAcao: 'Confirme que o backend está em execução em 127.0.0.1:8000 e tente de novo.',
  enderecoEsperado: ENDERECO_SWAGGER_UI,
}

function falhaDeStatus(status: number): DadosErroDocumentacaoApi {
  return {
    causa: `O backend local respondeu com status ${status} ao consultar a saúde do processo.`,
    impacto: 'A documentação da API (Swagger UI e openapi.json) não pode ser confirmada como disponível.',
    proximaAcao: 'Confirme que o backend está em execução em 127.0.0.1:8000 e tente de novo.',
    enderecoEsperado: ENDERECO_SWAGGER_UI,
  }
}

async function consultarSaude() {
  try {
    // `fetch` é passado explicitamente (em vez de depender do `baseFetch` capturado
    // por `createClient` na importação do módulo) para que o global `fetch` atual
    // seja sempre usado — inclusive quando substituído em teste após o import.
    return await clienteApi.GET('/api/v1/saude', { fetch })
  } catch {
    throw new ErroDocumentacaoApi(FALHA_DE_REDE)
  }
}

/** Verifica a disponibilidade da documentação da API via GET /api/v1/saude, tipado. */
export async function verificarDocumentacaoApi(): Promise<ResultadoDocumentacaoApi> {
  const resultado = await consultarSaude()

  if (resultado.error || !resultado.response.ok) {
    throw new ErroDocumentacaoApi(falhaDeStatus(resultado.response.status))
  }

  return {
    estado: 'disponivel',
    enderecoSwaggerUi: ENDERECO_SWAGGER_UI,
    enderecoOpenApi: ENDERECO_OPENAPI,
  }
}
