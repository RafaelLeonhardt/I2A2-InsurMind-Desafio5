/**
 * Cenário E2E-03 (metade "sem risco") — evento que não atinge nenhuma regra.
 *
 * Uma leitura real de chuva abaixo do limiar da regra ativa encerra a execução em
 * `sem_risco`, com motivo tipado e critérios consultáveis. O ponto do AC é o que **não**
 * acontece a partir daí: nenhuma chamada à OpenAI, nenhuma mensagem gerada e nenhuma
 * simulação registrada. O diário do servidor de dublês é a evidência direta disso — ele
 * registra toda requisição que chegaria à OpenAI, e as duas listas precisam estar vazias.
 */

import { expect, test } from '@playwright/test'
import { ESTACAO_CHUVA } from '../suporte/ambiente.ts'
import {
  aguardarEstado,
  iniciarExecucao,
  obterAvaliacaoRisco,
  obterMensagens,
  obterResultados,
  obterSimulacao,
} from '../suporte/api.ts'
import { prepararCenario } from '../suporte/cenario.ts'
import { chamadasRegistradas, programarInmet } from '../suporte/dubles-cliente.ts'
import { AREA_CHUVA_ID } from '../suporte/identificadores.ts'

/** Abaixo do limiar de 50 mm da regra de chuva intensa semeada (`semeador.py`). */
const CHUVA_ABAIXO_DO_LIMIAR_MM = 12.4

test.describe('E2E-03: evento sem risco', () => {
  test('encerra em sem_risco com motivo consultavel e sem nenhuma chamada a OpenAI', async () => {
    await prepararCenario()
    await programarInmet([{ preset: 'chuva', milimetros: CHUVA_ABAIXO_DO_LIMIAR_MM }], ESTACAO_CHUVA)

    const execucaoId = await iniciarExecucao(AREA_CHUVA_ID)
    const terminal = await aguardarEstado(execucaoId, ['sem_risco'])

    expect(terminal.estado).toBe('sem_risco')
    expect(terminal.marcos.map((marco) => marco.marco)).toContain('sem_risco')

    const risco = await obterAvaliacaoRisco(execucaoId)
    expect(risco.motivo).toBe('abaixo_do_limiar')
    const criterioIntensidade = risco.criterios.find((criterio) =>
      criterio.operando.startsWith('intensidade'),
    )
    expect(criterioIntensidade?.atende).toBe(false)
    expect(criterioIntensidade?.valor_observado).toBe(`${CHUVA_ABAIXO_DO_LIMIAR_MM} mm`)
    expect(criterioIntensidade?.justificativa).toBe(
      'Intensidade observada fica abaixo do limiar de 50.0 mm.',
    )

    const mensagens = await obterMensagens(execucaoId)
    expect(mensagens.registros).toEqual([])

    const simulacao = await obterSimulacao(execucaoId)
    expect(simulacao.entregas).toEqual([])

    const resultados = await obterResultados(execucaoId)
    expect(resultados.totais_por_estado).toEqual([])

    const chamadas = await chamadasRegistradas()
    expect(chamadas.openaiChat).toEqual([])
    expect(chamadas.openaiModelos).toEqual([])
    expect(chamadas.inmet.map((chamada) => chamada.estacao)).toEqual([ESTACAO_CHUVA])
  })
})
