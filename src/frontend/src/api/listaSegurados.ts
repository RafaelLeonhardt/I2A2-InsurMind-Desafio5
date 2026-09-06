import { clienteApi } from './clienteHttp'

/** Um segurado sintético disponível para o seletor "Visualizar como" (SELETOR-01). */
export type SeguradoListado = {
  id: string
  nome: string
}

type DadosErroListaSegurados = {
  ocorrencia: string
  impacto: string
  proximaAcao: string
}

/** Falha tipada da lista de segurados sintéticos, com ocorrência, impacto e próxima ação segura. */
export class ErroListaSegurados extends Error {
  readonly ocorrencia: string
  readonly impacto: string
  readonly proximaAcao: string

  constructor(dados: DadosErroListaSegurados) {
    super(dados.ocorrencia)
    this.name = 'ErroListaSegurados'
    this.ocorrencia = dados.ocorrencia
    this.impacto = dados.impacto
    this.proximaAcao = dados.proximaAcao
  }
}

const FALHA_DE_REDE: DadosErroListaSegurados = {
  ocorrencia: 'Não foi possível falar com o backend local da Central Preventiva.',
  impacto: 'O seletor não pode exibir os segurados disponíveis no momento.',
  proximaAcao: 'Confirme que o backend está em execução em 127.0.0.1:8000 e tente de novo.',
}

const FALHA_INESPERADA: DadosErroListaSegurados = {
  ocorrencia: 'Os segurados sintéticos não puderam ser consultados.',
  impacto: 'O seletor não pode exibir os segurados disponíveis no momento.',
  proximaAcao: 'Verifique se o backend local está disponível e tente novamente.',
}

async function chamarLista() {
  return clienteApi.GET('/api/v1/segurados', { fetch })
}

/** Lista todos os segurados sintéticos do seed, ordenados por nome. */
export async function getListaSegurados(): Promise<SeguradoListado[]> {
  let resultado: Awaited<ReturnType<typeof chamarLista>>
  try {
    resultado = await chamarLista()
  } catch {
    throw new ErroListaSegurados(FALHA_DE_REDE)
  }

  if (!resultado.response.ok || !resultado.data) {
    throw new ErroListaSegurados(FALHA_INESPERADA)
  }

  return resultado.data.segurados.map((segurado) => ({ id: segurado.id, nome: segurado.nome }))
}
