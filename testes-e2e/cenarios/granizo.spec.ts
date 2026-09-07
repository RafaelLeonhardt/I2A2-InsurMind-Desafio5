/**
 * Cenário E2E-02 — granizo automóvel, da entrada sintética rotulada ao comunicado.
 *
 * Mesma forma do cenário de chuva intensa, com uma diferença que o AD-013 impõe: granizo não
 * existe nas leituras horárias de estação automática do INMET, então a entrada meteorológica
 * vem do cenário sintético rotulado — ativado explicitamente por
 * `POST /meteorologia/cenarios-sinteticos/granizo-demonstrativo/ativar` e servido pelo dublê
 * do INMET no mesmo formato de payload que `AdaptadorCenarioSintetico` produz. O evento
 * resultante carrega `proveniencia = sintetico` do começo ao fim do fluxo.
 *
 * O cenário confirma o que é específico deste evento: a regra de granizo (limiar, tipo de
 * apólice, cobertura exigida, canal), a apólice de automóvel do segurado incluído, o canal SMS
 * e as recomendações preventivas de granizo apresentadas ao segurado.
 */

import { expect, test } from '@playwright/test'
import { ESTACAO_GRANIZO } from '../suporte/ambiente.ts'
import {
  aguardarEstado,
  ativarCenarioSintetico,
  confirmarSimulacao,
  decidirLote,
  iniciarExecucao,
  listarEventos,
  obterAlertaMaisRelevante,
  obterAvaliacaoRisco,
  obterElegibilidade,
  obterLoteRevisao,
  obterRegra,
  obterSimulacao,
  solicitarPreflight,
} from '../suporte/api.ts'
import { abrirPainelSegurado, prepararCenario } from '../suporte/cenario.ts'
import { programarInmet } from '../suporte/dubles-cliente.ts'
import {
  AREA_GRANIZO_ID,
  identificadorDemonstracao,
  NOME_SEGURADO_GRANIZO_ELEGIVEL,
  NOME_SEGURADO_GRANIZO_NAO_ELEGIVEL,
  SEGURADO_GRANIZO_ELEGIVEL_ID,
} from '../suporte/identificadores.ts'
import { CONTEUDO_PADRAO_DUBLE } from '../suporte/servidor-dubles.ts'

/** Identificador do único cenário sintético do MVP (`adaptador_cenario_sintetico.py`). */
const CENARIO_GRANIZO = 'granizo-demonstrativo'

/** Acima do limiar de 20 mm da regra de granizo semeada (`semeador.py`). */
const GRANIZO_ACIMA_DO_LIMIAR = 31

const REGRA_GRANIZO_ID = identificadorDemonstracao('regra/granizo')
const APOLICE_GRANIZO_ELEGIVEL_ID = identificadorDemonstracao('apolice/granizo-elegivel')

const RECOMENDACOES_GRANIZO = [
  'Recolha o veículo a um local coberto antes do início do granizo.',
  'Afaste-se de janelas, claraboias e telhas translúcidas.',
  'Não suba ao telhado durante nem logo após a queda de granizo.',
]

test.describe('E2E-02: granizo automóvel', () => {
  test('avanca do cenario sintetico rotulado ate o comunicado do segurado elegivel', async ({
    page,
  }) => {
    await prepararCenario()
    await programarInmet(
      [{ preset: 'granizo-sintetico', intensidade: GRANIZO_ACIMA_DO_LIMIAR }],
      ESTACAO_GRANIZO,
    )

    await ativarCenarioSintetico(CENARIO_GRANIZO, AREA_GRANIZO_ID)
    const aposAtivacao = await listarEventos()
    const granizoAtivado = aposAtivacao.eventos.find((evento) => evento.tipo === 'granizo')
    expect(granizoAtivado?.proveniencia).toBe('sintetico')

    const execucaoId = await iniciarExecucao(AREA_GRANIZO_ID)
    const comPublico = await aguardarEstado(execucaoId, ['aguardando_geracao'])

    const risco = await obterAvaliacaoRisco(execucaoId)
    expect(risco.motivo).toBe('relevante')
    expect(risco.regra_id).toBe(REGRA_GRANIZO_ID)

    const regra = await obterRegra(REGRA_GRANIZO_ID)
    expect(regra.evento_tipo).toBe('granizo')
    expect(regra.limiar_meteorologico).toBe(20)
    expect(regra.apolice_tipo).toBe('automovel')
    expect(regra.cobertura_exigida).toBe('granizo')
    expect(regra.canal).toBe('sms')

    expect(comPublico.publico_elegivel_total).toBe(1)
    expect(comPublico.publico_elegivel_previa).toEqual([
      { nome_segurado: NOME_SEGURADO_GRANIZO_ELEGIVEL, canal: 'sms' },
    ])

    const elegibilidade = await obterElegibilidade(execucaoId)
    expect(elegibilidade.incluidos).toBe(1)
    expect(elegibilidade.excluidos).toBe(1)
    const excluido = elegibilidade.registros.find((registro) => !registro.elegivel)
    expect(excluido?.nome_segurado).toBe(NOME_SEGURADO_GRANIZO_NAO_ELEGIVEL)

    await solicitarPreflight(execucaoId)
    await aguardarEstado(execucaoId, ['aguardando_revisao'])

    const lote = await obterLoteRevisao(execucaoId)
    expect(lote.evento?.tipo).toBe('granizo')
    expect(lote.evento?.proveniencia).toBe('sintetico')
    expect(lote.regra_id).toBe(REGRA_GRANIZO_ID)
    expect(lote.itens).toHaveLength(1)

    const item = lote.itens[0]!
    expect(item.canal).toBe('sms')
    expect(item.aprovada_pelo_critico).toBe(true)
    expect(item.destinatario.nome_segurado).toBe(NOME_SEGURADO_GRANIZO_ELEGIVEL)
    expect(item.destinatario.apolice_id).toBe(APOLICE_GRANIZO_ELEGIVEL_ID)
    expect(item.origem.regra_id).toBe(REGRA_GRANIZO_ID)

    await decidirLote(execucaoId, [
      { mensagem_id: item.mensagem_id, versao_esperada: item.versao, resultado: 'aprovar' },
    ])
    await aguardarEstado(execucaoId, ['aguardando_confirmacao'])

    const resumo = await obterSimulacao(execucaoId)
    const confirmada = await confirmarSimulacao(execucaoId, resumo.versao)
    expect(confirmada.estado).toBe('concluida')

    const simulada = await obterSimulacao(execucaoId)
    expect(simulada.entregas[0]?.canal).toBe('sms')
    expect(simulada.entregas[0]?.corpo).toBe(CONTEUDO_PADRAO_DUBLE.sms)

    const alerta = await obterAlertaMaisRelevante(SEGURADO_GRANIZO_ELEGIVEL_ID)
    expect(alerta.alerta?.evento_tipo).toBe('granizo')
    expect(alerta.alerta?.origem).toBe('sintetico')
    expect(alerta.alerta?.impactos_esperados).toContain('granizo')
    expect(alerta.alerta?.recomendacoes).toEqual(RECOMENDACOES_GRANIZO)

    await abrirPainelSegurado(page, NOME_SEGURADO_GRANIZO_ELEGIVEL)

    const visaoGeral = page.getByRole('main').filter({ hasText: 'Impactos esperados' })
    await expect(visaoGeral.getByText('Granizo', { exact: true })).toBeVisible()
    await expect(visaoGeral.getByText('Cenário demonstrativo (sintético)').first()).toBeVisible()
    for (const recomendacao of RECOMENDACOES_GRANIZO) {
      await expect(visaoGeral.getByText(recomendacao)).toBeVisible()
    }

    const apolice = page.getByRole('main').filter({ hasText: 'Sua apólice' })
    await expect(apolice.getByText('DEMO-AUT-0003')).toBeVisible()
    await expect(apolice.getByText('Automóvel', { exact: true })).toBeVisible()

    const comunicados = page.getByRole('main').filter({ hasText: 'Seus comunicados' })
    await expect(comunicados.getByRole('cell', { name: 'SMS' })).toBeVisible()
    await comunicados.getByRole('button', { name: 'Ver detalhe' }).first().click()

    const detalhe = page.getByRole('main').filter({ hasText: 'Seu comunicado preventivo' })
    await expect(detalhe.getByText(CONTEUDO_PADRAO_DUBLE.sms)).toBeVisible()
  })
})
