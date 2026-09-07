/**
 * Identificadores determinísticos da demonstração, derivados do mesmo namespace do backend.
 *
 * Porta TypeScript de `dominio/identificadores_demonstracao.py`: `uuid5` sobre o namespace
 * `uuid5(NAMESPACE_URL, 'https://central-preventiva.invalid/demonstracao')`. A suíte precisa
 * disso porque não existe endpoint que liste as áreas monitoradas, e `POST /execucoes` exige
 * um `area_id`.
 */

import { createHash } from 'node:crypto'

const NAMESPACE_URL = '6ba7b811-9dad-11d1-80b4-00c04fd430c8'

function bytesDoUuid(uuid: string): Buffer {
  return Buffer.from(uuid.replace(/-/g, ''), 'hex')
}

/** Deriva um UUID versão 5 (SHA-1) de um namespace e um nome, como `uuid.uuid5` do Python. */
export function uuid5(namespace: string, nome: string): string {
  const resumo = createHash('sha1')
    .update(bytesDoUuid(namespace))
    .update(Buffer.from(nome, 'utf8'))
    .digest()
  const bytes = Buffer.from(resumo.subarray(0, 16))
  bytes[6] = ((bytes[6] as number) & 0x0f) | 0x50
  bytes[8] = ((bytes[8] as number) & 0x3f) | 0x80
  const hex = bytes.toString('hex')
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
}

const NAMESPACE_DEMONSTRACAO = uuid5(NAMESPACE_URL, 'https://central-preventiva.invalid/demonstracao')

/** Equivalente de `identificador_demonstracao(nome)` do backend. */
export function identificadorDemonstracao(nome: string): string {
  return uuid5(NAMESPACE_DEMONSTRACAO, nome)
}

/** Áreas monitoradas semeadas por `testes-e2e/suporte/preparar_banco.py`. */
export const AREA_CHUVA_ID = identificadorDemonstracao('area-monitorada/chuva')
export const AREA_GRANIZO_ID = identificadorDemonstracao('area-monitorada/granizo')

/** Segurados sintéticos do conjunto canônico (`semeador.py`). */
export const SEGURADO_CHUVA_ELEGIVEL_ID = identificadorDemonstracao('segurado/chuva-elegivel')
export const SEGURADO_CHUVA_NAO_ELEGIVEL_ID = identificadorDemonstracao(
  'segurado/chuva-nao-elegivel',
)
export const SEGURADO_GRANIZO_ELEGIVEL_ID = identificadorDemonstracao('segurado/granizo-elegivel')
export const SEGURADO_GRANIZO_NAO_ELEGIVEL_ID = identificadorDemonstracao(
  'segurado/granizo-nao-elegivel',
)

/** Nomes exibidos na interface para cada segurado sintético (`semeador.py`). */
export const NOME_SEGURADO_CHUVA_ELEGIVEL = 'Pessoa Segurada Sintética DEMO-001'
export const NOME_SEGURADO_CHUVA_NAO_ELEGIVEL = 'Pessoa Segurada Sintética DEMO-002'
export const NOME_SEGURADO_GRANIZO_ELEGIVEL = 'Pessoa Segurada Sintética DEMO-003'
export const NOME_SEGURADO_GRANIZO_NAO_ELEGIVEL = 'Pessoa Segurada Sintética DEMO-004'
