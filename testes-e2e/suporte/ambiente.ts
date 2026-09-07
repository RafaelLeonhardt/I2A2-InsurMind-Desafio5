/** Endereços, caminhos e variáveis compartilhados por toda a suíte E2E (História 5.8). */

import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

/** Raiz do repositório, resolvida a partir deste arquivo (`testes-e2e/suporte/`). */
export const RAIZ_PROJETO = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..')

/** Porta da API real. Fixa em `composicao/servidor.py` (`PORTA_API = 8000`). */
export const PORTA_BACKEND = 8000

/** Porta do frontend real. Fixa em `src/frontend/vite.config.ts` (`strictPort`). */
export const PORTA_FRONTEND = 5173

/** Endereço da API real. */
export const ENDERECO_BACKEND = `http://127.0.0.1:${PORTA_BACKEND}`

/** Endereço do frontend real. */
export const ENDERECO_FRONTEND = `http://127.0.0.1:${PORTA_FRONTEND}`

/**
 * Banco DuckDB exclusivo da suíte E2E.
 *
 * Deliberadamente separado do banco de desenvolvimento: a restauração apaga todas as tabelas
 * fora da lista de exceções (AD-014), e a suíte restaura antes de cada cenário.
 */
export const CAMINHO_BANCO_E2E = 'var/e2e/central_preventiva.duckdb'

/** Modelo esperado pelo preflight de IA; precisa estar no catálogo devolvido pelo dublê. */
export const MODELO_OPENAI_E2E = 'gpt-4o-mini'

/** Credencial de fachada: não vale nada, mas evita o curto-circuito "credencial ausente". */
export const CHAVE_OPENAI_E2E = 'sk-dublê-e2e-sem-valor-real'

/** Nome da variável de ambiente pela qual o `globalSetup` publica a porta do dublê. */
export const VARIAVEL_PORTA_DUBLES = 'CENTRAL_PREVENTIVA_E2E_PORTA_DUBLES'

/** Endereço base do servidor de dublês desta execução. */
export function enderecoDubles(): string {
  const porta = process.env[VARIAVEL_PORTA_DUBLES]
  if (!porta) {
    throw new Error(
      `${VARIAVEL_PORTA_DUBLES} não está definida: o globalSetup da suíte E2E não rodou.`,
    )
  }
  return `http://127.0.0.1:${porta}`
}

/** Estações do INMET mapeadas para as áreas sintéticas da demonstração (AD-007). */
export const ESTACAO_CHUVA = 'A701'
export const ESTACAO_GRANIZO = 'A702'
