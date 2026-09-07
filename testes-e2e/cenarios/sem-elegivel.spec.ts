/**
 * Cenário E2E-03 (metade "sem público elegível") — evento relevante, ninguém elegível.
 *
 * Diferente do cenário `sem_risco`, aqui o evento **é** relevante: a regra de chuva intensa é
 * atingida e a avaliação de elegibilidade roda. O que falta é público. O conjunto sintético
 * traz um segurado que já não é elegível (apólice cancelada); o outro sai do público pela
 * própria superfície de preferências, desligando a participação em alertas (PREFS) — nenhuma
 * edição de arquivo ou de banco, só a API real.
 *
 * O encerramento é `sem_elegiveis`, com o motivo de exclusão de cada registro consultável, e
 * de novo sem nenhuma chamada à OpenAI, mensagem ou simulação.
 */

import { expect, test } from '@playwright/test'
import { ESTACAO_CHUVA } from '../suporte/ambiente.ts'
import {
  aguardarEstado,
  atualizarPreferencias,
  iniciarExecucao,
  obterAvaliacaoRisco,
  obterDetalheElegibilidade,
  obterElegibilidade,
  obterMensagens,
  obterPreferencias,
  obterResultados,
  obterSimulacao,
} from '../suporte/api.ts'
import { prepararCenario } from '../suporte/cenario.ts'
import { chamadasRegistradas, programarInmet } from '../suporte/dubles-cliente.ts'
import {
  AREA_CHUVA_ID,
  NOME_SEGURADO_CHUVA_ELEGIVEL,
  NOME_SEGURADO_CHUVA_NAO_ELEGIVEL,
  SEGURADO_CHUVA_ELEGIVEL_ID,
} from '../suporte/identificadores.ts'

/** Acima do limiar de 50 mm da regra de chuva intensa semeada (`semeador.py`). */
const CHUVA_ACIMA_DO_LIMIAR_MM = 55.4

test.describe('E2E-03: evento relevante sem público elegível', () => {
  test('encerra em sem_elegiveis com motivo consultavel e sem nenhuma chamada a OpenAI', async () => {
    await prepararCenario()
    await programarInmet([{ preset: 'chuva', milimetros: CHUVA_ACIMA_DO_LIMIAR_MM }], ESTACAO_CHUVA)

    const preferencias = await obterPreferencias(SEGURADO_CHUVA_ELEGIVEL_ID)
    const atualizadas = await atualizarPreferencias(SEGURADO_CHUVA_ELEGIVEL_ID, {
      canal_preferido: preferencias.canal_preferido,
      participa_de_alertas: false,
      versao_esperada: preferencias.versao,
    })
    expect(atualizadas.participa_de_alertas).toBe(false)

    const execucaoId = await iniciarExecucao(AREA_CHUVA_ID)
    const terminal = await aguardarEstado(execucaoId, ['sem_elegiveis'])

    expect(terminal.estado).toBe('sem_elegiveis')
    expect(terminal.marcos.map((marco) => marco.marco)).toContain(
      'avaliacao_elegibilidade_concluida',
    )
    expect(terminal.marcos.map((marco) => marco.marco)).toContain('sem_elegiveis')

    const risco = await obterAvaliacaoRisco(execucaoId)
    expect(risco.motivo).toBe('relevante')

    const elegibilidade = await obterElegibilidade(execucaoId)
    expect(elegibilidade.incluidos).toBe(0)
    expect(elegibilidade.excluidos).toBe(2)
    expect(elegibilidade.registros.every((registro) => !registro.elegivel)).toBe(true)

    const porAlertas = elegibilidade.registros.find(
      (registro) => registro.nome_segurado === NOME_SEGURADO_CHUVA_ELEGIVEL,
    )
    const explicacaoAlertas = await obterDetalheElegibilidade(execucaoId, porAlertas!.id)
    const criterioAlertas = explicacaoAlertas.criterios.find((criterio) => !criterio.atende)
    expect(criterioAlertas?.operando).toBe('participação em alertas')
    expect(criterioAlertas?.justificativa).toBe(
      'Segurado optou por não participar de alertas preventivos.',
    )

    const porApolice = elegibilidade.registros.find(
      (registro) => registro.nome_segurado === NOME_SEGURADO_CHUVA_NAO_ELEGIVEL,
    )
    const explicacaoApolice = await obterDetalheElegibilidade(execucaoId, porApolice!.id)
    const criterioApolice = explicacaoApolice.criterios.find((criterio) => !criterio.atende)
    expect(criterioApolice?.operando).toBe('situação da apólice')
    expect(criterioApolice?.justificativa).toBe('Apólice não está ativa (situação: cancelada).')

    const mensagens = await obterMensagens(execucaoId)
    expect(mensagens.registros).toEqual([])

    const simulacao = await obterSimulacao(execucaoId)
    expect(simulacao.entregas).toEqual([])

    const resultados = await obterResultados(execucaoId)
    expect(resultados.totais_por_estado).toEqual([])

    const chamadas = await chamadasRegistradas()
    expect(chamadas.openaiChat).toEqual([])
    expect(chamadas.openaiModelos).toEqual([])
  })
})
