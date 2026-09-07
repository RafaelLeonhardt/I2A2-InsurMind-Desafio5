/**
 * `globalSetup` da suíte E2E: dublês → banco → backend real → frontend real (História 5.8).
 *
 * A ordem importa. O dublê precisa existir antes do backend, porque o backend recebe a porta
 * dele por variável de ambiente e já consulta o INMET no `lifespan`. O banco precisa estar
 * migrado e semeado antes do backend subir, porque o DuckDB aceita um único processo escritor
 * (README). Daqui em diante a restauração entre cenários usa o endpoint REST ao vivo
 * (`POST /api/v1/dados-sinteticos/restauracoes`), nunca o CLI: ele abriria um segundo
 * escritor sobre o mesmo arquivo.
 */

import { MODELO_OPENAI_E2E, PORTA_BACKEND, PORTA_FRONTEND, VARIAVEL_PORTA_DUBLES } from './ambiente.ts'
import {
  exigirPortaLivre,
  iniciarBackend,
  iniciarFrontend,
  prepararBanco,
  type ProcessoGerenciado,
} from './processos.ts'
import { iniciarServidorDubles, type ServidorDubles } from './servidor-dubles.ts'

/** Handles compartilhados entre `globalSetup` e `globalTeardown` (mesmo processo Node). */
export type AmbienteE2E = {
  dubles: ServidorDubles
  backend: ProcessoGerenciado
  frontend: ProcessoGerenciado
}

const CHAVE_AMBIENTE = Symbol.for('central-preventiva.e2e.ambiente')

/** Recupera o ambiente iniciado pelo `globalSetup`, ou `undefined` se nada subiu. */
export function ambienteAtivo(): AmbienteE2E | undefined {
  return (globalThis as Record<symbol, unknown>)[CHAVE_AMBIENTE] as AmbienteE2E | undefined
}

export default async function globalSetup(): Promise<void> {
  await exigirPortaLivre(PORTA_BACKEND, 'backend')
  await exigirPortaLivre(PORTA_FRONTEND, 'frontend')

  const dubles = await iniciarServidorDubles([MODELO_OPENAI_E2E])
  process.env[VARIAVEL_PORTA_DUBLES] = String(dubles.porta)

  await prepararBanco(dubles.porta)
  const backend = await iniciarBackend(dubles.porta)
  const frontend = await iniciarFrontend()

  ;(globalThis as Record<symbol, unknown>)[CHAVE_AMBIENTE] = {
    dubles,
    backend,
    frontend,
  } satisfies AmbienteE2E
}
