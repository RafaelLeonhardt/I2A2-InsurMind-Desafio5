/** Sobe e derruba os processos reais (backend, frontend) usados pela suíte E2E (5.8). */

import { spawn, type ChildProcess } from 'node:child_process'
import { mkdirSync } from 'node:fs'
import { createServer } from 'node:net'
import { dirname, resolve } from 'node:path'
import {
  CAMINHO_BANCO_E2E,
  CHAVE_OPENAI_E2E,
  ENDERECO_BACKEND,
  ENDERECO_FRONTEND,
  MODELO_OPENAI_E2E,
  RAIZ_PROJETO,
} from './ambiente.ts'

/** Processo em execução, com o encerramento limpo já preparado. */
export type ProcessoGerenciado = { encerrar: () => Promise<void> }

/**
 * Variáveis que redirecionam toda integração externa do backend para o dublê local.
 *
 * `OPENAI_BASE_URL` cobre o SDK usado por `langchain_openai.ChatOpenAI` (redator e crítico);
 * `CENTRAL_PREVENTIVA_URL_BASE_OPENAI` cobre as duas chamadas `GET /v1/models` feitas
 * direto por `httpx` (sonda de prontidão e preflight de IA). Uma credencial de fachada é
 * obrigatória: sem ela o preflight termina em "credencial ausente" antes de qualquer
 * chamada, e nenhum cenário de sucesso conseguiria rodar.
 */
export function ambienteBackend(portaDubles: number): NodeJS.ProcessEnv {
  const enderecoDubles = `http://127.0.0.1:${portaDubles}`
  return {
    ...process.env,
    CENTRAL_PREVENTIVA_HOST_API: '127.0.0.1',
    CENTRAL_PREVENTIVA_ORIGEM_FRONTEND: ENDERECO_FRONTEND,
    CENTRAL_PREVENTIVA_CAMINHO_BANCO: CAMINHO_BANCO_E2E,
    CENTRAL_PREVENTIVA_URL_BASE_INMET: enderecoDubles,
    CENTRAL_PREVENTIVA_URL_BASE_OPENAI: enderecoDubles,
    OPENAI_BASE_URL: `${enderecoDubles}/v1`,
    OPENAI_API_KEY: CHAVE_OPENAI_E2E,
    CENTRAL_PREVENTIVA_MODELO_OPENAI: MODELO_OPENAI_E2E,
  }
}

/** Código de saída de um processo encerrado por `SIGTERM` (128 + 15), esperado no teardown. */
const CODIGO_SIGTERM = 143

function gerenciar(processo: ChildProcess, nome: string): ProcessoGerenciado {
  let encerrando = false
  processo.on('exit', (codigo, sinal) => {
    const esperado = encerrando && (sinal !== null || codigo === CODIGO_SIGTERM || codigo === 0)
    if (!esperado && codigo !== 0) {
      console.error(`[e2e] ${nome} terminou inesperadamente com código ${codigo}.`)
    }
  })
  return {
    encerrar: () =>
      new Promise<void>((resolver) => {
        encerrando = true
        if (processo.exitCode !== null || processo.signalCode !== null) {
          resolver()
          return
        }
        processo.once('exit', () => resolver())
        processo.kill('SIGTERM')
        setTimeout(() => processo.kill('SIGKILL'), 8_000).unref()
      }),
  }
}

/**
 * Espera um endereço HTTP responder `200` com um corpo reconhecível da própria aplicação.
 *
 * A conferência do corpo não é preciosismo: outro processo pode estar escutando no curinga
 * da mesma porta (`*:5173`) e responder no lugar do servidor esperado até que o nosso termine
 * de subir. Sem essa checagem a suíte seguiria contra a aplicação errada.
 */
export async function aguardarDisponivel(
  endereco: string,
  nome: string,
  marcaEsperada: string,
  limiteMs = 120_000,
): Promise<void> {
  const limite = Date.now() + limiteMs
  let ultimaFalha = 'nenhuma tentativa concluída'
  while (Date.now() < limite) {
    try {
      const resposta = await fetch(endereco)
      const corpo = await resposta.text()
      if (resposta.status === 200 && corpo.includes(marcaEsperada)) return
      ultimaFalha = `status ${resposta.status} sem a marca "${marcaEsperada}"`
    } catch (causa) {
      ultimaFalha = causa instanceof Error ? causa.message : String(causa)
    }
    await new Promise((resolver) => setTimeout(resolver, 300))
  }
  throw new Error(`${nome} não ficou disponível em ${endereco} (${limiteMs}ms): ${ultimaFalha}`)
}

/**
 * Recusa iniciar se `127.0.0.1:<porta>` já estiver ocupada — evita rodar contra um servidor
 * alheio e transformar uma colisão de porta em falha obscura de cenário.
 *
 * A verificação é um `bind` de teste no mesmo endereço específico que backend e frontend
 * usam, não uma requisição HTTP: um processo qualquer escutando no curinga (`*:porta`) não
 * impede o `bind` em `127.0.0.1` e não deve bloquear a suíte.
 */
export async function exigirPortaLivre(porta: number, nome: string): Promise<void> {
  await new Promise<void>((resolver, rejeitar) => {
    const sonda = createServer()
    sonda.once('error', (causa: NodeJS.ErrnoException) => {
      rejeitar(
        new Error(
          `A porta 127.0.0.1:${porta} já está ocupada (${causa.code}). Pare o ${nome} em ` +
            'execução antes de rodar a suíte E2E: ela precisa dirigir os processos que inicia.',
        ),
      )
    })
    sonda.listen(porta, '127.0.0.1', () => sonda.close(() => resolver()))
  })
}

/** Prepara o banco exclusivo da suíte, com o servidor ainda parado (DuckDB é escritor único). */
export async function prepararBanco(portaDubles: number): Promise<void> {
  const caminho = resolve(RAIZ_PROJETO, CAMINHO_BANCO_E2E)
  mkdirSync(dirname(caminho), { recursive: true })
  const script = resolve(RAIZ_PROJETO, 'testes-e2e', 'suporte', 'preparar_banco.py')
  await new Promise<void>((resolver, rejeitar) => {
    const processo = spawn(
      'uv',
      ['run', '--directory', 'src/backend', 'python', script],
      { cwd: RAIZ_PROJETO, env: ambienteBackend(portaDubles), stdio: 'inherit' },
    )
    processo.on('error', rejeitar)
    processo.on('exit', (codigo) =>
      codigo === 0
        ? resolver()
        : rejeitar(new Error(`preparar_banco.py terminou com código ${codigo}.`)),
    )
  })
}

/** Sobe a API real e espera a saúde mínima responder. */
export async function iniciarBackend(portaDubles: number): Promise<ProcessoGerenciado> {
  const processo = spawn(
    'uv',
    ['run', '--directory', 'src/backend', 'python', '-m', 'central_preventiva.composicao.servidor'],
    { cwd: RAIZ_PROJETO, env: ambienteBackend(portaDubles), stdio: 'inherit' },
  )
  const gerenciado = gerenciar(processo, 'backend')
  await aguardarDisponivel(`${ENDERECO_BACKEND}/api/v1/saude`, 'backend', '"status":"disponivel"')
  return gerenciado
}

/** Sobe o servidor de desenvolvimento do frontend e espera a raiz responder. */
export async function iniciarFrontend(): Promise<ProcessoGerenciado> {
  const processo = spawn('npm', ['run', 'dev', '--prefix', 'src/frontend'], {
    cwd: RAIZ_PROJETO,
    env: process.env,
    stdio: 'inherit',
  })
  const gerenciado = gerenciar(processo, 'frontend')
  await aguardarDisponivel(ENDERECO_FRONTEND, 'frontend', '/src/main.tsx')
  return gerenciado
}
