import { clienteApi } from './clienteHttp'
import type { components } from './tipos-gerados'

/** Um segurado sintético com os dados básicos exibidos ao administrador (LISTASEG-01..03):
 * nome, área, apólice mais recente (nula sem nenhuma) e canal preferencial. */
export type SeguradoDetalhado = {
  id: string
  nome: string
  codigoIbgeArea: string
  apoliceNumero: string | null
  canalPreferido: string
}

type DadosErroListaSeguradosAdmin = {
  ocorrencia: string
  impacto: string
  proximaAcao: string
  status: number | null
}

/** Falha tipada da lista detalhada de segurados sintéticos, com ocorrência, impacto e
 * próxima ação segura. */
export class ErroListaSeguradosAdmin extends Error {
  readonly ocorrencia: string
  readonly impacto: string
  readonly proximaAcao: string
  readonly status: number | null

  constructor(dados: DadosErroListaSeguradosAdmin) {
    super(dados.ocorrencia)
    this.name = 'ErroListaSeguradosAdmin'
    this.ocorrencia = dados.ocorrencia
    this.impacto = dados.impacto
    this.proximaAcao = dados.proximaAcao
    this.status = dados.status
  }
}

const FALHA_DE_REDE: DadosErroListaSeguradosAdmin = {
  ocorrencia: 'Não foi possível falar com o backend local da Central Preventiva.',
  impacto: 'A lista de segurados não pode ser exibida no momento.',
  proximaAcao: 'Confirme que o backend está em execução em 127.0.0.1:8000 e tente de novo.',
  status: null,
}

const FALHA_INESPERADA_SEM_STATUS: Omit<DadosErroListaSeguradosAdmin, 'status'> = {
  ocorrencia: 'Os segurados sintéticos não puderam ser consultados.',
  impacto: 'A lista de segurados não pode ser exibida no momento.',
  proximaAcao: 'Verifique se o backend local está disponível e tente novamente.',
}

function paraSeguradoDetalhado(
  corpo: components['schemas']['RespostaSeguradoDetalhado'],
): SeguradoDetalhado {
  return {
    id: corpo.id,
    nome: corpo.nome,
    codigoIbgeArea: corpo.codigo_ibge_area,
    apoliceNumero: corpo.apolice_numero,
    canalPreferido: corpo.canal_preferido,
  }
}

async function chamarListaDetalhada() {
  return clienteApi.GET('/api/v1/segurados/detalhado', { fetch })
}

/** Consulta a lista detalhada de segurados sintéticos (nome, área, apólice e canal) para a
 * superfície "Segurados" do perfil Administrador (LISTASEG-01), ordenados por nome. */
export async function getSeguradosDetalhado(): Promise<SeguradoDetalhado[]> {
  let resultado: Awaited<ReturnType<typeof chamarListaDetalhada>>
  try {
    resultado = await chamarListaDetalhada()
  } catch {
    throw new ErroListaSeguradosAdmin(FALHA_DE_REDE)
  }

  if (!resultado.response.ok || !resultado.data) {
    throw new ErroListaSeguradosAdmin({
      ...FALHA_INESPERADA_SEM_STATUS,
      status: resultado.response.status,
    })
  }

  return resultado.data.segurados.map(paraSeguradoDetalhado)
}
