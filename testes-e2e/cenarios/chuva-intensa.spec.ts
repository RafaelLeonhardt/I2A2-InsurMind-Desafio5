/**
 * Cenário E2E-01 — chuva intensa residencial, da entrada meteorológica ao comunicado.
 *
 * Percorre o fluxo inteiro contra o backend real: coleta no INMET (dublado) → normalização →
 * relevância → elegibilidade → preflight de IA → geração e crítica (OpenAI dublada) → revisão
 * humana → simulação, e termina na interface real, com o comunicado aberto pelo segurado
 * elegível num navegador Chromium.
 *
 * As etapas administrativas são dirigidas pela API REST porque as superfícies de
 * Administrador dos Épicos 2–4 ainda não estão montadas em `App.tsx` (item aberto registrado
 * em `.specs/STATE.md`). A visualização final — que é o que o AC exige ver na interface —
 * acontece na tela real do perfil Segurado.
 */

import { expect, test } from '@playwright/test'
import {
  aguardarEstado,
  confirmarSimulacao,
  decidirLote,
  iniciarExecucao,
  obterAvaliacaoRisco,
  obterDetalheElegibilidade,
  obterElegibilidade,
  obterLoteRevisao,
  obterSimulacao,
  solicitarPreflight,
} from '../suporte/api.ts'
import { prepararCenario, abrirPainelSegurado, conteudoComTexto } from '../suporte/cenario.ts'
import { ESTACAO_CHUVA } from '../suporte/ambiente.ts'
import { programarInmet } from '../suporte/dubles-cliente.ts'
import {
  AREA_CHUVA_ID,
  NOME_SEGURADO_CHUVA_ELEGIVEL,
  NOME_SEGURADO_CHUVA_NAO_ELEGIVEL,
} from '../suporte/identificadores.ts'
import { CONTEUDO_PADRAO_DUBLE } from '../suporte/servidor-dubles.ts'

/** Acima do limiar de 50 mm da regra de chuva intensa semeada (`semeador.py`). */
const CHUVA_ACIMA_DO_LIMIAR_MM = 55.4

test.describe('E2E-01: chuva intensa residencial', () => {
  test('avanca da entrada meteorologica ate o comunicado do segurado elegivel', async ({
    page,
  }) => {
    await prepararCenario()
    await programarInmet([{ preset: 'chuva', milimetros: CHUVA_ACIMA_DO_LIMIAR_MM }], ESTACAO_CHUVA)

    const execucaoId = await iniciarExecucao(AREA_CHUVA_ID)
    const comPublico = await aguardarEstado(execucaoId, ['aguardando_geracao'])

    const risco = await obterAvaliacaoRisco(execucaoId)
    expect(risco.motivo).toBe('relevante')
    expect(risco.regra_id).not.toBeNull()

    expect(comPublico.publico_elegivel_total).toBe(1)
    expect(comPublico.publico_elegivel_previa).toEqual([
      { nome_segurado: NOME_SEGURADO_CHUVA_ELEGIVEL, canal: 'whatsapp' },
    ])

    const elegibilidade = await obterElegibilidade(execucaoId)
    expect(elegibilidade.incluidos).toBe(1)
    expect(elegibilidade.excluidos).toBe(1)

    const naoElegivel = elegibilidade.registros.find((registro) => !registro.elegivel)
    expect(naoElegivel?.nome_segurado).toBe(NOME_SEGURADO_CHUVA_NAO_ELEGIVEL)

    const explicacao = await obterDetalheElegibilidade(execucaoId, naoElegivel!.id)
    expect(explicacao.elegivel).toBe(false)
    const criterioReprovado = explicacao.criterios.find((criterio) => !criterio.atende)
    expect(criterioReprovado?.operando).toBe('situação da apólice')
    expect(criterioReprovado?.valor_observado).toBe('cancelada')
    expect(criterioReprovado?.justificativa).toBe('Apólice não está ativa (situação: cancelada).')

    await solicitarPreflight(execucaoId)
    await aguardarEstado(execucaoId, ['aguardando_revisao'])

    const lote = await obterLoteRevisao(execucaoId)
    expect(lote.evento?.tipo).toBe('chuva_intensa')
    expect(lote.evento?.proveniencia).toBe('real_inmet')
    expect(lote.itens).toHaveLength(1)
    const item = lote.itens[0]!
    expect(item.canal).toBe('whatsapp')
    expect(item.aprovada_pelo_critico).toBe(true)
    expect(item.em_excecao).toBe(false)
    expect(item.destinatario.nome_segurado).toBe(NOME_SEGURADO_CHUVA_ELEGIVEL)

    await decidirLote(execucaoId, [
      { mensagem_id: item.mensagem_id, versao_esperada: item.versao, resultado: 'aprovar' },
    ])
    const pronta = await aguardarEstado(execucaoId, ['aguardando_confirmacao'])
    expect(pronta.estado).toBe('aguardando_confirmacao')

    const resumo = await obterSimulacao(execucaoId)
    const confirmada = await confirmarSimulacao(execucaoId, resumo.versao)
    expect(confirmada.estado).toBe('concluida')
    expect(confirmada.entregas_criadas).toHaveLength(1)

    const simulada = await obterSimulacao(execucaoId)
    expect(simulada.entregas[0]?.canal).toBe('whatsapp')
    expect(simulada.entregas[0]?.rotulo).toBe('simulada')
    expect(simulada.entregas[0]?.corpo).toBe(CONTEUDO_PADRAO_DUBLE.whatsapp)

    await abrirPainelSegurado(page, NOME_SEGURADO_CHUVA_ELEGIVEL)

    const comunicados = conteudoComTexto(page, 'Seus comunicados')
    await expect(comunicados.getByRole('cell', { name: 'WhatsApp' })).toBeVisible()
    await comunicados.getByRole('button', { name: 'Ver detalhe' }).first().click()

    const detalhe = conteudoComTexto(page, 'Seu comunicado preventivo')
    await expect(detalhe.getByText(CONTEUDO_PADRAO_DUBLE.whatsapp)).toBeVisible()
  })
})
