/**
 * Cliente tipado da API de controle do servidor de dublês (`/__mock__`).
 *
 * O contrato completo — formas de `RespostaProgramada`, semântica da fila, defaults — está
 * documentado no cabeçalho de `servidor-dubles.ts`. Este módulo só embrulha as chamadas HTTP
 * para que os cenários não repitam `fetch` cru.
 */

import { enderecoDubles } from './ambiente.ts'
import type { DiarioChamadas, RespostaProgramada } from './servidor-dubles.ts'

async function postar(caminho: string, corpo: unknown): Promise<void> {
  const resposta = await fetch(`${enderecoDubles()}${caminho}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(corpo),
  })
  if (!resposta.ok) {
    throw new Error(`Controle do dublê recusou ${caminho}: ${resposta.status}`)
  }
}

/** Limpa todas as filas programadas e o diário de chamadas. Chame no início de cada cenário. */
export async function resetarDubles(): Promise<void> {
  await postar('/__mock__/resetar', {})
}

/** Programa a fila de respostas do INMET para uma estação (ou para qualquer uma, se omitida). */
export async function programarInmet(
  respostas: RespostaProgramada[],
  estacao?: string,
): Promise<void> {
  await postar('/__mock__/programar-inmet', { estacao: estacao ?? null, respostas })
}

/**
 * Programa a fila de `POST /v1/chat/completions`.
 *
 * Sem `esquema`, programa a fila coringa, usada por qualquer agente sem fila própria.
 * Com `esquema` (`SaidaWhatsApp`/`SaidaSMS`/`SaidaEmail` para o redator,
 * `AvaliacaoEstruturada` para o crítico), programa só as chamadas daquele agente.
 */
export async function programarChatOpenAI(
  respostas: RespostaProgramada[],
  esquema?: string,
): Promise<void> {
  await postar('/__mock__/programar-openai', {
    endpoint: 'chat',
    esquema: esquema ?? null,
    respostas,
  })
}

/** Programa a fila de `GET /v1/models` (sonda de prontidão e preflight de IA). */
export async function programarModelosOpenAI(respostas: RespostaProgramada[]): Promise<void> {
  await postar('/__mock__/programar-openai', { endpoint: 'modelos', respostas })
}

/** Diário de tudo que chegou aos dublês desde o último `resetarDubles`. */
export async function chamadasRegistradas(): Promise<DiarioChamadas> {
  const resposta = await fetch(`${enderecoDubles()}/__mock__/chamadas`)
  if (!resposta.ok) throw new Error(`Não foi possível ler o diário do dublê: ${resposta.status}`)
  return (await resposta.json()) as DiarioChamadas
}
