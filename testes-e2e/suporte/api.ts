/**
 * Cliente HTTP da API real, usado pelos cenários E2E para dirigir o fluxo ponta a ponta.
 *
 * Só o que a suíte precisa: nenhuma abstração além do `fetch` cru com `Idempotency-Key`
 * fresco por mutação (AD-002 — reusar uma chave com corpo diferente devolve `409`).
 */

import { randomUUID } from 'node:crypto'
import { ENDERECO_BACKEND } from './ambiente.ts'

const PREFIXO = `${ENDERECO_BACKEND}/api/v1`

async function pedir<T>(
  metodo: string,
  caminho: string,
  opcoes: { corpo?: unknown; idempotente?: boolean } = {},
): Promise<T> {
  const cabecalhos: Record<string, string> = { 'Content-Type': 'application/json' }
  if (opcoes.idempotente) cabecalhos['Idempotency-Key'] = randomUUID()
  const resposta = await fetch(`${PREFIXO}${caminho}`, {
    method: metodo,
    headers: cabecalhos,
    body: opcoes.corpo === undefined ? undefined : JSON.stringify(opcoes.corpo),
  })
  const texto = await resposta.text()
  if (!resposta.ok) {
    throw new Error(`${metodo} ${caminho} respondeu ${resposta.status}: ${texto}`)
  }
  return (texto === '' ? undefined : JSON.parse(texto)) as T
}

/** `GET` público, já desserializado. */
export function obter<T>(caminho: string): Promise<T> {
  return pedir<T>('GET', caminho)
}

/** `POST` mutável, com `Idempotency-Key` novo a cada chamada. */
export function postar<T>(caminho: string, corpo?: unknown): Promise<T> {
  return pedir<T>('POST', caminho, { corpo: corpo ?? {}, idempotente: true })
}

/** `POST` mutável reusando uma `Idempotency-Key` conhecida (prova de não duplicação). */
export async function postarComChave<T>(
  caminho: string,
  chave: string,
  corpo?: unknown,
): Promise<T> {
  const resposta = await fetch(`${PREFIXO}${caminho}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Idempotency-Key': chave },
    body: JSON.stringify(corpo ?? {}),
  })
  const texto = await resposta.text()
  if (!resposta.ok) throw new Error(`POST ${caminho} respondeu ${resposta.status}: ${texto}`)
  return (texto === '' ? undefined : JSON.parse(texto)) as T
}

/** `PUT` mutável, com `Idempotency-Key` novo a cada chamada. */
export function atualizar<T>(caminho: string, corpo: unknown): Promise<T> {
  return pedir<T>('PUT', caminho, { corpo, idempotente: true })
}

/**
 * Restaura o conjunto sintético pelo endpoint ao vivo, garantindo o estado inicial completo.
 *
 * Deliberadamente pelo REST e não pelo CLI `composicao.inicializador`: o DuckDB aceita um
 * único processo escritor, e o servidor está no ar durante toda a suíte. O endpoint abre a
 * própria conexão curta dentro do processo do servidor, sem concorrência de escrita.
 */
export async function restaurarDadosSinteticos(): Promise<void> {
  await postar('/dados-sinteticos/restauracoes')
}

/** Estado agregado e marcos de uma execução preventiva. */
export type Execucao = {
  id: string
  estado: string
  marcos: { marco: string; causa: string | null; criado_em: string }[]
  publico_elegivel_total: number | null
  publico_elegivel_previa: { nome_segurado: string; canal: string }[]
  execucao_origem_id: string | null
  retentativas: string[]
}

/** Inicia uma execução preventiva para a área informada e devolve o identificador. */
export async function iniciarExecucao(areaId: string): Promise<string> {
  const aceita = await postar<{ execucao_id: string }>('/execucoes', { area_id: areaId })
  return aceita.execucao_id
}

/** Lê o estado corrente de uma execução. */
export function obterExecucao(execucaoId: string): Promise<Execucao> {
  return obter<Execucao>(`/execucoes/${execucaoId}`)
}

/**
 * Espera a execução alcançar um dos estados informados.
 *
 * Falha com o estado observado e os marcos já registrados: um cenário que não avança precisa
 * ser diagnosticável, nunca um resultado parcial silencioso (Edge Case de `spec.md`).
 */
export async function aguardarEstado(
  execucaoId: string,
  estados: readonly string[],
  limiteMs = 60_000,
): Promise<Execucao> {
  const limite = Date.now() + limiteMs
  let ultima: Execucao | null = null
  while (Date.now() < limite) {
    ultima = await obterExecucao(execucaoId)
    if (estados.includes(ultima.estado)) return ultima
    await new Promise((resolver) => setTimeout(resolver, 200))
  }
  const marcos = ultima?.marcos.map((marco) => marco.marco).join(' → ') ?? 'nenhum'
  throw new Error(
    `A execução ${execucaoId} não alcançou ${estados.join('/')} em ${limiteMs}ms. ` +
      `Estado observado: ${ultima?.estado ?? 'desconhecido'}. Marcos: ${marcos}.`,
  )
}

/** Snapshot público da avaliação de relevância meteorológica. */
export type AvaliacaoRisco = {
  execucao_id: string
  evento_id: string
  regra_id: string | null
  motivo: string
  criterios: { operando: string; valor_observado: string; atende: boolean; justificativa: string }[]
}

export function obterAvaliacaoRisco(execucaoId: string): Promise<AvaliacaoRisco> {
  return obter<AvaliacaoRisco>(`/execucoes/${execucaoId}/avaliacao-risco`)
}

/** Público avaliado de uma execução: incluídos, excluídos e cada registro. */
export type Elegibilidade = {
  incluidos: number
  excluidos: number
  registros: {
    id: string
    nome_segurado: string
    apolice_id: string
    codigo_ibge_area: string
    canal: string
    elegivel: boolean
  }[]
}

export function obterElegibilidade(execucaoId: string): Promise<Elegibilidade> {
  return obter<Elegibilidade>(`/execucoes/${execucaoId}/elegibilidade`)
}

/** Explicação completa de um registro de elegibilidade (ELEG-09). */
export type DetalheElegibilidade = {
  id: string
  nome_segurado: string
  elegivel: boolean
  criterios: { operando: string; valor_observado: string; atende: boolean; justificativa: string }[]
}

export function obterDetalheElegibilidade(
  execucaoId: string,
  registroId: string,
): Promise<DetalheElegibilidade> {
  return obter<DetalheElegibilidade>(`/execucoes/${execucaoId}/elegibilidade/${registroId}`)
}

/** Aciona a preparação agêntica (preflight de IA) de uma execução. */
export function solicitarPreflight(execucaoId: string): Promise<unknown> {
  return postar(`/execucoes/${execucaoId}/preflight`)
}

/** Lote de revisão humana de uma execução. */
export type LoteRevisao = {
  execucao_id: string
  estado: string
  itens: {
    mensagem_id: string
    canal: string
    estado: string
    versao: number
    decidivel: boolean
    em_excecao: boolean
    aprovada_pelo_critico: boolean
    destinatario: { nome_segurado: string }
  }[]
  evento: { tipo: string; area: string; proveniencia: string } | null
  regra_id: string | null
}

export function obterLoteRevisao(execucaoId: string): Promise<LoteRevisao> {
  return obter<LoteRevisao>(`/execucoes/${execucaoId}/revisao`)
}

/** Aplica decisões humanas sobre o lote, numa transação única. */
export function decidirLote(
  execucaoId: string,
  decisoes: { mensagem_id: string; versao_esperada: number; resultado: string; justificativa?: string }[],
): Promise<unknown> {
  return postar(`/execucoes/${execucaoId}/revisao/decisoes`, { decisoes })
}

/** Resumo da simulação, antes e depois da confirmação. */
export type ResumoSimulacao = {
  execucao_id: string
  estado: string
  versao: number
  entregas: {
    id: string
    mensagem_id: string
    canal: string
    rotulo: string
    assunto: string | null
    corpo: string
  }[]
}

export function obterSimulacao(execucaoId: string): Promise<ResumoSimulacao> {
  return obter<ResumoSimulacao>(`/execucoes/${execucaoId}/simulacao`)
}

/** Confirma a simulação com o reconhecimento explícito exigido por SIMUL-03. */
export function confirmarSimulacao(
  execucaoId: string,
  versaoEsperada: number,
): Promise<{ estado: string; entregas_criadas: string[]; mensagens_simuladas: string[] }> {
  return postar(`/execucoes/${execucaoId}/confirmar-simulacao`, {
    versao_esperada: versaoEsperada,
    reconhecimento_simulacao: true,
  })
}

/** Ativa o cenário sintético rotulado de contingência (AD-013). */
export function ativarCenarioSintetico(identificador: string, areaId: string): Promise<unknown> {
  return postar(`/meteorologia/cenarios-sinteticos/${identificador}/ativar`, { area_id: areaId })
}

/** Eventos meteorológicos normalizados, do mais recente. */
export type Evento = {
  id: string
  tipo: string
  area: string
  intensidade: number
  proveniencia: string
}

export function listarEventos(): Promise<{ eventos: Evento[] }> {
  return obter<{ eventos: Evento[] }>('/meteorologia/eventos')
}

/** Preferências de um segurado sintético. */
export type Preferencias = {
  segurado_id: string
  canal_preferido: string
  participa_de_alertas: boolean
  versao: number
}

export function obterPreferencias(seguradoId: string): Promise<Preferencias> {
  return obter<Preferencias>(`/segurados/${seguradoId}/preferencias`)
}

export function atualizarPreferencias(
  seguradoId: string,
  corpo: { canal_preferido: string; participa_de_alertas: boolean; versao_esperada: number },
): Promise<Preferencias> {
  return atualizar<Preferencias>(`/segurados/${seguradoId}/preferencias`, corpo)
}

/** Comunicados simulados visíveis para um segurado. */
export type ListaComunicados = {
  comunicados: {
    entrega_simulada_id: string
    canal: string
    assunto_ou_resumo: string
    criado_em: string
  }[]
}

export function listarComunicados(seguradoId: string): Promise<ListaComunicados> {
  return obter<ListaComunicados>(`/segurados/${seguradoId}/comunicados`)
}
