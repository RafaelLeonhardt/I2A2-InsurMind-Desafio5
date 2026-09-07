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

/** Desfecho do preflight: estado alcançado, contextos montados e causa do bloqueio. */
export type Preflight = {
  execucao_id: string
  estado: string
  contextos_montados: number
  itens_em_excecao: string[]
  causa: string | null
}

/** Aciona a preparação agêntica (preflight de IA) de uma execução. */
export function solicitarPreflight(execucaoId: string): Promise<Preflight> {
  return postar<Preflight>(`/execucoes/${execucaoId}/preflight`)
}

/** Motivo categorizado de uma avaliação do agente crítico. */
export type MotivoCritica = { categoria: string; justificativa: string }

/** Uma tentativa de geração apresentada no lote de revisão. */
export type VersaoRevisada = {
  numero_tentativa: number
  corpo: string
  valida: boolean
  motivo_invalidez: string | null
  avaliacao_critica: { aprovada: boolean; motivos: MotivoCritica[] } | null
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
    pode_regenerar: boolean
    reprovacao_historica: boolean
    tentativa_atual: number
    limite_tentativas: number
    aprovada_pelo_critico: boolean
    destinatario: { nome_segurado: string; apolice_id: string; codigo_ibge_area: string }
    origem: { evento_id: string; regra_id: string; regra_versao: number; justificativa: string }
    versoes: VersaoRevisada[]
  }[]
  evento: { tipo: string; area: string; proveniencia: string; intensidade: number } | null
  itens_em_excecao: number
  aprovacoes_agenticas: number
  total_publico_incluido: number
  regra_id: string | null
  regra_versao: number | null
}

export function obterLoteRevisao(execucaoId: string): Promise<LoteRevisao> {
  return obter<LoteRevisao>(`/execucoes/${execucaoId}/revisao`)
}

/** Desfecho do envio de decisões: o que foi aplicado e onde o agregado parou. */
export type DecisaoLote = {
  execucao_id: string
  estado: string
  aplicadas: string[]
  recusadas: { mensagem_id: string; motivo: string }[]
  mensagens_aprovadas: string[]
  regeneracoes_ativas: string[]
}

/** Aplica decisões humanas sobre o lote, numa transação única. */
export function decidirLote(
  execucaoId: string,
  decisoes: { mensagem_id: string; versao_esperada: number; resultado: string; justificativa?: string }[],
): Promise<DecisaoLote> {
  return postar<DecisaoLote>(`/execucoes/${execucaoId}/revisao/decisoes`, { decisoes })
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

/** Regra preventiva versionada. */
export type Regra = {
  id: string
  evento_tipo: string
  limiar_meteorologico: number
  area_aplicavel: string
  apolice_tipo: string
  cobertura_exigida: string
  canal: string
  versao: number
  estado: string
}

export function obterRegra(regraId: string): Promise<Regra> {
  return obter<Regra>(`/regras/${regraId}`)
}

/** Alerta mais relevante exibido ao segurado, com origem, impactos e recomendações. */
export type AlertaSegurado = {
  alerta: {
    elegibilidade_id: string
    evento_tipo: string
    origem: string
    localizacao: string
    severidade: string
    impactos_esperados: string[]
    recomendacoes: string[]
    fonte_degradada: boolean
  } | null
}

export function obterAlertaMaisRelevante(seguradoId: string): Promise<AlertaSegurado> {
  return obter<AlertaSegurado>(`/segurados/${seguradoId}/alerta-mais-relevante`)
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

/** Solicita uma coleta meteorológica manual para a área informada. */
export function solicitarColeta(areaId: string): Promise<{
  id: string
  estado: string
  registros_validos: number
  motivo_falha: string | null
}> {
  return postar('/meteorologia/coletas', { area_id: areaId })
}

/** Uma tentativa individual de coleta dentro de uma sincronização com retry (RESIL-02). */
export type TentativaColeta = { numero_tentativa: number; codigo_resultado: string }

/** Registro público de uma tentativa de sincronização meteorológica. */
export type Sincronizacao = {
  id: string
  area_monitorada_id: string
  origem: string
  estado: string
  registros_validos: number
  motivo_falha: string | null
  tentativas: TentativaColeta[]
  limite_tentativas: number
}

/** Histórico de sincronização meteorológica, com o último snapshot válido. */
export type HistoricoSincronizacoes = {
  ultima_tentativa: Sincronizacao | null
  ultima_valida: Sincronizacao | null
  resultados_anteriores: Sincronizacao[]
}

export function obterSincronizacoes(): Promise<HistoricoSincronizacoes> {
  return obter<HistoricoSincronizacoes>('/meteorologia/sincronizacoes')
}

/** Cronologia completa de uma execução, com marcos de sistema, IA e humanos. */
export type LinhaDoTempo = {
  execucao_id: string
  estado: string
  execucao_origem_id: string | null
  retentativas: string[]
  marcos: { tipo: string; ator: string; acao: string; resultado: string; correlacao: string }[]
}

export function obterLinhaDoTempo(execucaoId: string): Promise<LinhaDoTempo> {
  return obter<LinhaDoTempo>(`/execucoes/${execucaoId}/linha-do-tempo`)
}

/** Mensagens produzidas por uma execução (vazio quando nenhuma foi gerada). */
export type Mensagens = {
  execucao_id: string
  registros: { mensagem_id: string; canal: string; estado: string }[]
}

export function obterMensagens(execucaoId: string): Promise<Mensagens> {
  return obter<Mensagens>(`/execucoes/${execucaoId}/mensagens`)
}

/** Detalhe completo de uma mensagem: tentativas, avaliações e exceção técnica. */
export type DetalheMensagem = {
  mensagem_id: string
  estado: string
  canal: string
  nome_segurado: string
  excecao: { causa: string; impacto: string; tentativas: number } | null
  versoes: {
    numero_tentativa: number
    corpo: string
    valida: boolean
    avaliacao_critica: { aprovada: boolean; motivos: MotivoCritica[] } | null
  }[]
}

export function obterDetalheMensagem(
  execucaoId: string,
  mensagemId: string,
): Promise<DetalheMensagem> {
  return obter<DetalheMensagem>(`/execucoes/${execucaoId}/mensagens/${mensagemId}/detalhe`)
}

/** Resultados consolidados da simulação de uma execução. */
export type Resultados = {
  execucao_id: string
  estado: string
  concluido: boolean
  totais_por_estado: { chave: string; total: number }[]
  totais_por_canal: { chave: string; total: number }[]
  nao_simulaveis: { mensagem_id: string; canal: string; estado: string; motivo: string }[]
}

export function obterResultados(execucaoId: string): Promise<Resultados> {
  return obter<Resultados>(`/execucoes/${execucaoId}/resultados`)
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
