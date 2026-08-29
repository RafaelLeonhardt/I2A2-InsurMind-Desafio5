#!/usr/bin/env node
// Regenera os tipos da API a partir do backend em execução e falha se o
// arquivo versionado (`src/api/tipos-gerados.ts`) divergir do que a
// regeneração produz agora. Requer o backend rodando em 127.0.0.1:8000.

import { execFileSync } from 'node:child_process'
import { mkdtempSync, readFileSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'

const raizFrontend = fileURLToPath(new URL('..', import.meta.url))
const caminhoVersionado = join(raizFrontend, 'src/api/tipos-gerados.ts')
const diretorioTemporario = mkdtempSync(join(tmpdir(), 'verificar-tipos-api-'))
const caminhoRegenerado = join(diretorioTemporario, 'tipos-gerados.ts')

try {
  execFileSync(
    'npx',
    ['openapi-typescript', 'http://127.0.0.1:8000/openapi.json', '-o', caminhoRegenerado],
    { cwd: raizFrontend, stdio: 'inherit' }
  )

  const versionado = readFileSync(caminhoVersionado, 'utf-8')
  const regenerado = readFileSync(caminhoRegenerado, 'utf-8')

  if (versionado !== regenerado) {
    console.error(
      'src/api/tipos-gerados.ts está desatualizado em relação ao contrato OpenAPI do backend em execução. ' +
        'Rode `npm run gerar-tipos-api` e commite o resultado.'
    )
    process.exit(1)
  }

  console.log('src/api/tipos-gerados.ts está sincronizado com o contrato OpenAPI do backend em execução.')
} finally {
  rmSync(diretorioTemporario, { recursive: true, force: true })
}
