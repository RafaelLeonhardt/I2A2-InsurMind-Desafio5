import { defineConfig, devices } from '@playwright/test'
import { ENDERECO_FRONTEND } from './suporte/ambiente.ts'

/**
 * Configuração da suíte E2E da Central Preventiva (História 5.8).
 *
 * O backend real, o frontend real e o servidor de dublês são iniciados pelo `globalSetup`
 * (não por `webServer`): o backend só pode subir depois que o dublê existe, porque recebe a
 * porta dele por variável de ambiente, e o banco precisa estar migrado antes disso.
 *
 * `workers: 1` é obrigatório, não uma preferência de desempenho: o DuckDB aceita um único
 * escritor, cada cenário restaura o banco inteiro (AD-014) e backend/frontend usam portas
 * fixas. Rodar cenários em paralelo destruiria o estado um do outro.
 */
export default defineConfig({
  testDir: '.',
  testMatch: '**/*.spec.ts',
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: 0,
  timeout: 120_000,
  expect: { timeout: 15_000 },
  globalSetup: './suporte/global-setup.ts',
  globalTeardown: './suporte/global-teardown.ts',
  reporter: [['list'], ['html', { outputFolder: 'relatorios/html', open: 'never' }]],
  outputDir: 'relatorios/artefatos',
  use: {
    baseURL: ENDERECO_FRONTEND,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'off',
    viewport: { width: 1440, height: 1024 },
    locale: 'pt-BR',
    timezoneId: 'America/Sao_Paulo',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
})
