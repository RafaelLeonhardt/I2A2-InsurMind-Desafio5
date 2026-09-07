/**
 * Servidor de dublês das integrações externas da suíte E2E (História 5.8).
 *
 * Um único processo Node, ouvindo em `127.0.0.1` numa porta efêmera, que substitui INMET e
 * OpenAI durante toda a execução da suíte. O backend real é iniciado apontando para ele:
 *
 * - `CENTRAL_PREVENTIVA_URL_BASE_INMET=http://127.0.0.1:<porta>` (cliente do INMET)
 * - `CENTRAL_PREVENTIVA_URL_BASE_OPENAI=http://127.0.0.1:<porta>` (sonda de prontidão e
 *   preflight de IA, ambos `GET /v1/models`)
 * - `OPENAI_BASE_URL=http://127.0.0.1:<porta>/v1` (SDK usado por `langchain_openai.ChatOpenAI`)
 *
 * Com isso nenhuma chamada de rede real sai da máquina, que é o que o AC de 5.8 exige.
 *
 * ## Rotas dubladas
 *
 * | Rota | Quem chama |
 * | --- | --- |
 * | `GET /estacao/dados/:data/:estacao` | `ClienteInmet.coletar` |
 * | `GET /v1/models` | `SondaOpenAI.verificar`, `VerificadorDisponibilidadeOpenAI.verificar` |
 * | `POST /v1/chat/completions` | `AgenteRedator.gerar`, `AgenteCritico.avaliar` |
 *
 * ## API de controle (`/__mock__`)
 *
 * É por aqui que cada cenário roteiriza o comportamento das integrações. O vocabulário
 * espelha os dublês já usados nos testes de integração do backend (`AdaptadorInmetFalso`,
 * `RedatorFalso`, `CriticoFalso`): uma fila ordenada de respostas, e a **última resposta da
 * fila se repete indefinidamente** depois que a fila é consumida. Fila vazia = resposta
 * padrão embutida.
 *
 * ### `POST /__mock__/resetar`
 *
 * Corpo vazio. Limpa todas as filas programadas e o diário de chamadas. Responde
 * `200 {"ok": true}`. Chame antes de cada cenário, junto da restauração do banco.
 *
 * ### `POST /__mock__/programar-inmet`
 *
 * ```jsonc
 * {
 *   "estacao": "A701",   // opcional; ausente/null = fila coringa, usada por qualquer estação
 *   "respostas": [ RespostaProgramada, ... ]
 * }
 * ```
 *
 * ### `POST /__mock__/programar-openai`
 *
 * ```jsonc
 * {
 *   "endpoint": "chat",  // "chat" = POST /v1/chat/completions; "modelos" = GET /v1/models
 *   "esquema": "AvaliacaoEstruturada",  // opcional; só em "chat" (ver abaixo)
 *   "respostas": [ RespostaProgramada, ... ]
 * }
 * ```
 *
 * Redator e crítico compartilham a mesma rota `POST /v1/chat/completions` e se distinguem
 * pelo `response_format.json_schema.name` da requisição: `SaidaWhatsApp`/`SaidaSMS`/
 * `SaidaEmail` para o redator, `AvaliacaoEstruturada` para o crítico. Informar `esquema`
 * programa uma fila só daquele agente; omiti-lo programa a fila coringa, usada por qualquer
 * esquema sem fila própria — mesma composição das filas por estação do INMET. É o que
 * permite reprovar o crítico três vezes seguidas sem que a resposta de reprovação caia na
 * chamada do redator.
 *
 * ### `RespostaProgramada`
 *
 * Exatamente uma destas formas:
 *
 * | Forma | Efeito |
 * | --- | --- |
 * | `{ "status": 200, "corpo": {...} }` | devolve esse status e esse corpo JSON literalmente |
 * | `{ "status": 500 }` | devolve o status sem corpo útil (erro de servidor, 401, 429, ...) |
 * | `{ "falha": "timeout", "atrasoMs": 20000 }` | segura a conexão além do limite do cliente |
 * | `{ "falha": "conexao" }` | derruba a conexão sem resposta (erro de transporte) |
 * | `{ "preset": "chuva", "milimetros": 55.4 }` | só INMET: leitura horária real de chuva |
 * | `{ "preset": "granizo-sintetico", "intensidade": 31 }` | só INMET: payload do cenário sintético rotulado (AD-013) |
 * | `{ "conteudo": {...} }` | só OpenAI `chat`: vira `choices[0].message.content` serializado |
 * | `{ "modelos": ["gpt-4o-mini"] }` | só OpenAI `modelos`: catálogo devolvido |
 *
 * Os dois `preset` de INMET geram um instante de medição **distinto a cada chamada**, de
 * propósito: `eventos_meteorologicos` tem `UNIQUE (tipo, area, periodo_inicio, periodo_fim)`
 * (migração 0003) e grava com insert-or-noop (AD-010), então duas coletas com o mesmo período
 * produziriam um evento não persistido e uma referência pendurada. O tipo e a intensidade —
 * o que decide relevância e elegibilidade — continuam determinísticos.
 *
 * ### `GET /__mock__/chamadas`
 *
 * ```jsonc
 * {
 *   "inmet":         [ { "estacao": "A701", "data": "2026-09-06" } ],
 *   "openaiModelos": [ {} ],
 *   "openaiChat":    [ { "esquema": "SaidaWhatsApp" } ]
 * }
 * ```
 *
 * `openaiChat` é o que comprova "nenhuma chamada à OpenAI" nos cenários de encerramento
 * antecipado: a lista tem de estar vazia.
 */

import { createServer, type IncomingMessage, type Server, type ServerResponse } from 'node:http'

/** Uma resposta programada para uma das integrações dubladas. */
export type RespostaProgramada =
  | { status: number; corpo?: unknown }
  | { falha: 'timeout'; atrasoMs?: number }
  | { falha: 'conexao' }
  | { preset: 'chuva'; milimetros: number }
  | { preset: 'granizo-sintetico'; intensidade: number }
  | { conteudo: unknown }
  | { modelos: string[] }

/** Uma chamada registrada no diário do dublê. */
export type ChamadaRegistrada = { estacao?: string; data?: string; esquema?: string }

/** Diário de chamadas devolvido por `GET /__mock__/chamadas`. */
export type DiarioChamadas = {
  inmet: ChamadaRegistrada[]
  openaiModelos: ChamadaRegistrada[]
  openaiChat: ChamadaRegistrada[]
}

/**
 * Conteúdo que o dublê da OpenAI devolve quando nada foi programado, por canal.
 *
 * Exportado para que os cenários possam afirmar que **este** texto chegou ao comunicado do
 * segurado: é o que prova que a saída do redator atravessou crítica, revisão e simulação sem
 * ser substituída por conteúdo fixo em nenhum ponto do caminho.
 */
export const CONTEUDO_PADRAO_DUBLE = {
  whatsapp:
    'Chuva forte prevista na sua regiao nas proximas horas. Evite areas alagadas, ' +
    'recolha objetos soltos e mantenha documentos em local alto. Comunicacao preventiva.',
  sms: 'Chuva forte prevista hoje. Evite areas alagadas. Comunicacao preventiva.',
  assuntoEmail: 'Comunicado preventivo sobre o tempo na sua regiao',
  corpoEmail:
    'Chuva forte prevista na sua regiao nas proximas horas. Evite areas alagadas, ' +
    'recolha objetos soltos e mantenha documentos em local alto. Comunicacao preventiva.',
} as const

const INSTANTE_BASE_INMET = Date.UTC(2026, 7, 30, 0, 0, 0)
const CHUVA_PADRAO_MILIMETROS = 2.4

/** Fila de respostas cuja última entrada se repete depois de consumida (mesma semântica dos
 * dublês de `testes/test_grafo_geracao_mensagem.py`). */
class FilaRespostas {
  private readonly respostas: RespostaProgramada[] = []
  private consumidas = 0

  programar(respostas: RespostaProgramada[]): void {
    this.respostas.length = 0
    this.respostas.push(...respostas)
    this.consumidas = 0
  }

  proxima(): RespostaProgramada | null {
    if (this.respostas.length === 0) return null
    const indice = Math.min(this.consumidas, this.respostas.length - 1)
    this.consumidas += 1
    return this.respostas[indice] ?? null
  }

  limpar(): void {
    this.respostas.length = 0
    this.consumidas = 0
  }
}

function doisDigitos(valor: number): string {
  return String(valor).padStart(2, '0')
}

/** Corpo de uma leitura horária real de estação automática, no formato que
 * `NormalizadorInmet._normalizar_leitura_real` espera (mesma forma de
 * `src/backend/testes/fixtures/inmet/leitura_chuva_valida.json`). */
function corpoLeituraChuva(estacao: string, milimetros: number, sequencia: number): unknown {
  const instante = new Date(INSTANTE_BASE_INMET + sequencia * 3_600_000)
  const data = `${instante.getUTCFullYear()}-${doisDigitos(instante.getUTCMonth() + 1)}-${doisDigitos(instante.getUTCDate())}`
  return {
    CD_ESTACAO: estacao,
    DT_MEDICAO: data,
    HR_MEDICAO: `${doisDigitos(instante.getUTCHours())}00`,
    CHUVA: String(milimetros),
    TEM_INS: '24.3',
    UMD_INS: '88',
    PRE_INS: '1008.2',
    VEN_VEL: '3.1',
    VEN_DIR: '140',
    RAD_GLO: '210.5',
  }
}

/** Corpo do cenário sintético rotulado de granizo, no formato que
 * `NormalizadorInmet._normalizar_cenario_sintetico_granizo` espera (mesma forma de
 * `src/backend/testes/fixtures/inmet/cenario_sintetico_granizo.json`). */
function corpoGranizoSintetico(estacao: string, intensidade: number, sequencia: number): unknown {
  const fim = new Date(INSTANTE_BASE_INMET + sequencia * 3_600_000)
  const inicio = new Date(fim.getTime() - 6 * 3_600_000)
  return {
    _sintetico: true,
    CD_ESTACAO: estacao,
    TIPO_EVENTO_SINTETICO: 'granizo',
    INTENSIDADE: String(intensidade),
    PERIODO_INICIO: inicio.toISOString().slice(0, 19),
    PERIODO_FIM: fim.toISOString().slice(0, 19),
    INSTANTE_OBSERVADO: fim.toISOString().slice(0, 19),
  }
}

function conteudoPadraoDoEsquema(esquema: string): unknown {
  if (esquema === 'AvaliacaoEstruturada') return { aprovada: true, motivos: [] }
  if (esquema === 'SaidaEmail') {
    return {
      assunto: CONTEUDO_PADRAO_DUBLE.assuntoEmail,
      corpo: CONTEUDO_PADRAO_DUBLE.corpoEmail,
    }
  }
  if (esquema === 'SaidaSMS') return { corpo: CONTEUDO_PADRAO_DUBLE.sms }
  return { corpo: CONTEUDO_PADRAO_DUBLE.whatsapp }
}

/** Monta uma resposta de `POST /v1/chat/completions` no formato da API de chat da OpenAI. */
function completacaoDeChat(modelo: string, conteudo: unknown): unknown {
  return {
    id: 'chatcmpl-duble-e2e',
    object: 'chat.completion',
    created: Math.floor(Date.now() / 1000),
    model: modelo,
    choices: [
      {
        index: 0,
        message: { role: 'assistant', content: JSON.stringify(conteudo), refusal: null },
        finish_reason: 'stop',
        logprobs: null,
      },
    ],
    usage: { prompt_tokens: 120, completion_tokens: 60, total_tokens: 180 },
  }
}

/** Servidor de dublês em execução, com a porta atribuída e o encerramento limpo. */
export type ServidorDubles = { porta: number; encerrar: () => Promise<void> }

async function lerCorpo(requisicao: IncomingMessage): Promise<unknown> {
  const partes: Buffer[] = []
  for await (const parte of requisicao) partes.push(parte as Buffer)
  const bruto = Buffer.concat(partes).toString('utf8')
  if (bruto.trim() === '') return {}
  try {
    return JSON.parse(bruto)
  } catch {
    return {}
  }
}

function responderJson(resposta: ServerResponse, status: number, corpo: unknown): void {
  const dados = Buffer.from(JSON.stringify(corpo ?? {}), 'utf8')
  resposta.writeHead(status, {
    'Content-Type': 'application/json',
    'Content-Length': String(dados.byteLength),
  })
  resposta.end(dados)
}

/**
 * Sobe o servidor de dublês numa porta efêmera de `127.0.0.1`.
 *
 * @param modelosDisponiveis catálogo devolvido por `GET /v1/models` enquanto nada for
 * programado. Precisa conter o `CENTRAL_PREVENTIVA_MODELO_OPENAI` configurado, senão todo
 * preflight termina em `falhou_preparacao_ia` por "modelo não está no catálogo".
 */
export async function iniciarServidorDubles(
  modelosDisponiveis: readonly string[],
): Promise<ServidorDubles> {
  const filasInmet = new Map<string, FilaRespostas>()
  const filaInmetCoringa = new FilaRespostas()
  const filasChat = new Map<string, FilaRespostas>()
  const filaChat = new FilaRespostas()
  const filaModelos = new FilaRespostas()
  const diario: DiarioChamadas = { inmet: [], openaiModelos: [], openaiChat: [] }
  let sequenciaInmet = 0

  function filaDaEstacao(estacao: string): FilaRespostas {
    const existente = filasInmet.get(estacao)
    if (existente) return existente
    const nova = new FilaRespostas()
    filasInmet.set(estacao, nova)
    return nova
  }

  function filaDoEsquema(esquema: string): FilaRespostas {
    const existente = filasChat.get(esquema)
    if (existente) return existente
    const nova = new FilaRespostas()
    filasChat.set(esquema, nova)
    return nova
  }

  function resetar(): void {
    for (const fila of filasInmet.values()) fila.limpar()
    filaInmetCoringa.limpar()
    for (const fila of filasChat.values()) fila.limpar()
    filaChat.limpar()
    filaModelos.limpar()
    diario.inmet.length = 0
    diario.openaiModelos.length = 0
    diario.openaiChat.length = 0
  }

  /** Aplica uma resposta programada; devolve `false` quando a forma não é aplicável aqui. */
  function aplicar(
    resposta: RespostaProgramada,
    res: ServerResponse,
    contexto: { estacao?: string; modelo?: string },
  ): boolean {
    if ('falha' in resposta) {
      if (resposta.falha === 'conexao') {
        res.socket?.destroy()
        return true
      }
      const atraso = resposta.atrasoMs ?? 20_000
      setTimeout(() => res.socket?.destroy(), atraso).unref()
      return true
    }
    if ('preset' in resposta) {
      sequenciaInmet += 1
      const estacao = contexto.estacao ?? 'A000'
      const corpo =
        resposta.preset === 'chuva'
          ? corpoLeituraChuva(estacao, resposta.milimetros, sequenciaInmet)
          : corpoGranizoSintetico(estacao, resposta.intensidade, sequenciaInmet)
      responderJson(res, 200, corpo)
      return true
    }
    if ('conteudo' in resposta) {
      responderJson(res, 200, completacaoDeChat(contexto.modelo ?? 'gpt-4o-mini', resposta.conteudo))
      return true
    }
    if ('modelos' in resposta) {
      responderJson(res, 200, {
        object: 'list',
        data: resposta.modelos.map((id) => ({ id, object: 'model', owned_by: 'duble-e2e' })),
      })
      return true
    }
    if ('status' in resposta) {
      responderJson(res, resposta.status, resposta.corpo ?? {})
      return true
    }
    return false
  }

  const servidor: Server = createServer((req, res) => {
    const caminho = (req.url ?? '/').split('?')[0] ?? '/'
    const metodo = req.method ?? 'GET'

    if (caminho.startsWith('/__mock__')) {
      void (async () => {
        const corpo = (await lerCorpo(req)) as Record<string, unknown>
        if (caminho === '/__mock__/resetar' && metodo === 'POST') {
          resetar()
          responderJson(res, 200, { ok: true })
          return
        }
        if (caminho === '/__mock__/programar-inmet' && metodo === 'POST') {
          const respostas = (corpo.respostas ?? []) as RespostaProgramada[]
          const estacao = corpo.estacao
          if (typeof estacao === 'string' && estacao !== '') {
            filaDaEstacao(estacao).programar(respostas)
          } else {
            filaInmetCoringa.programar(respostas)
          }
          responderJson(res, 200, { ok: true })
          return
        }
        if (caminho === '/__mock__/programar-openai' && metodo === 'POST') {
          const respostas = (corpo.respostas ?? []) as RespostaProgramada[]
          const esquema = corpo.esquema
          if (corpo.endpoint === 'modelos') filaModelos.programar(respostas)
          else if (typeof esquema === 'string' && esquema !== '') {
            filaDoEsquema(esquema).programar(respostas)
          } else filaChat.programar(respostas)
          responderJson(res, 200, { ok: true })
          return
        }
        if (caminho === '/__mock__/chamadas' && metodo === 'GET') {
          responderJson(res, 200, diario)
          return
        }
        responderJson(res, 404, { erro: 'rota de controle desconhecida', caminho })
      })()
      return
    }

    if (metodo === 'GET' && caminho.startsWith('/estacao/dados/')) {
      const partes = caminho.split('/').filter((parte) => parte !== '')
      const data = partes[2] ?? ''
      const estacao = partes[3] ?? ''
      diario.inmet.push({ estacao, data })
      const programada = filaDaEstacao(estacao).proxima() ?? filaInmetCoringa.proxima()
      if (programada && aplicar(programada, res, { estacao })) return
      sequenciaInmet += 1
      responderJson(res, 200, corpoLeituraChuva(estacao, CHUVA_PADRAO_MILIMETROS, sequenciaInmet))
      return
    }

    if (metodo === 'GET' && caminho === '/v1/models') {
      diario.openaiModelos.push({})
      const programada = filaModelos.proxima()
      if (programada && aplicar(programada, res, {})) return
      responderJson(res, 200, {
        object: 'list',
        data: modelosDisponiveis.map((id) => ({ id, object: 'model', owned_by: 'duble-e2e' })),
      })
      return
    }

    if (metodo === 'POST' && caminho === '/v1/chat/completions') {
      void (async () => {
        const corpo = (await lerCorpo(req)) as {
          model?: string
          response_format?: { json_schema?: { name?: string } }
        }
        const esquema = corpo.response_format?.json_schema?.name ?? 'desconhecido'
        const modelo = corpo.model ?? 'gpt-4o-mini'
        diario.openaiChat.push({ esquema })
        const programada = filaDoEsquema(esquema).proxima() ?? filaChat.proxima()
        if (programada && aplicar(programada, res, { modelo })) return
        responderJson(res, 200, completacaoDeChat(modelo, conteudoPadraoDoEsquema(esquema)))
      })()
      return
    }

    responderJson(res, 404, { erro: 'rota dublada desconhecida', caminho, metodo })
  })

  await new Promise<void>((resolver) => servidor.listen(0, '127.0.0.1', resolver))
  const endereco = servidor.address()
  if (endereco === null || typeof endereco === 'string') {
    throw new Error('O servidor de dublês não recebeu uma porta TCP.')
  }

  return {
    porta: endereco.port,
    encerrar: () =>
      new Promise<void>((resolver) => {
        servidor.closeAllConnections()
        servidor.close(() => resolver())
      }),
  }
}
