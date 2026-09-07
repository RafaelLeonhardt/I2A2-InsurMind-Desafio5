/**
 * Cenário E2E-05 — contingência do INMET: indisponibilidade controlada e cenário sintético.
 *
 * O cenário tem três atos. Primeiro uma coleta bem-sucedida, que deixa um snapshot válido no
 * histórico. Depois o INMET é derrubado (todas as respostas seguram a conexão até o cliente
 * desistir): a superfície de Prontidão real passa a exibir o INMET como indisponível, e uma
 * execução preventiva iniciada nesse estado esgota as três tentativas e termina em
 * `falhou_coleta` — com o snapshot anterior permanecendo consultável, mas sem nenhuma
 * avaliação de risco nova a partir dele (RESIL-06/07). Por fim o cenário sintético rotulado é
 * ativado explicitamente e leva o fluxo até o comunicado, com `proveniencia = sintetico`
 * visível do evento normalizado até a tela do segurado (AD-013).
 *
 * As etapas administrativas de coleta/execução são dirigidas pela API REST porque as
 * superfícies de Administrador dos Épicos 2–4 ainda não estão montadas em `App.tsx` (item
 * aberto registrado em `.specs/STATE.md`). As duas superfícies montadas que o cenário exige
 * ver — Prontidão e o painel do Segurado — são exercitadas na interface real.
 */

import { expect, test } from '@playwright/test'
import { ESTACAO_CHUVA, ESTACAO_GRANIZO } from '../suporte/ambiente.ts'
import {
  aguardarEstado,
  ativarCenarioSintetico,
  confirmarSimulacao,
  decidirLote,
  iniciarExecucao,
  listarEventos,
  obterAlertaMaisRelevante,
  obterLinhaDoTempo,
  obterLoteRevisao,
  obterSimulacao,
  obterSincronizacoes,
  solicitarColeta,
  solicitarPreflight,
} from '../suporte/api.ts'
import { abrirPainelSegurado, abrirProntidao, prepararCenario } from '../suporte/cenario.ts'
import { programarInmet, programarSondaInmet } from '../suporte/dubles-cliente.ts'
import {
  AREA_CHUVA_ID,
  AREA_GRANIZO_ID,
  NOME_SEGURADO_GRANIZO_ELEGIVEL,
  SEGURADO_GRANIZO_ELEGIVEL_ID,
} from '../suporte/identificadores.ts'

/** Identificador do único cenário sintético do MVP (`adaptador_cenario_sintetico.py`). */
const CENARIO_GRANIZO = 'granizo-demonstrativo'

/** Abaixo do limiar de 50 mm da regra de chuva: snapshot válido, porém sem risco. */
const CHUVA_INFORMATIVA_MM = 12.5

/** Acima do limiar de 20 mm da regra de granizo semeada (`semeador.py`). */
const GRANIZO_ACIMA_DO_LIMIAR = 31

/** Número total de tentativas de uma coleta (`MAXIMO_TENTATIVAS_COLETA`, RESIL-01). */
const MAXIMO_TENTATIVAS_COLETA = 3

/** Motivo tipado da sincronização que esgotou as tentativas (`MOTIVO_RETENTATIVAS_ESGOTADAS`). */
const MOTIVO_RETENTATIVAS_ESGOTADAS = 'retentativas_esgotadas'

/** Causa e impacto que a Prontidão exibe com o INMET fora do ar (`aplicacao/prontidao.py`). */
const CAUSA_TIMEOUT_INMET = 'Tempo limite excedido ao consultar o INMET.'
const IMPACTO_INMET_INDISPONIVEL =
  'Funcionalidades que dependem de dados meteorológicos do INMET ficam bloqueadas.'

test.describe('E2E-05: contingência do INMET', () => {
  test('esgota tentativas, preserva o snapshot e segue pelo cenario sintetico rotulado', async ({
    page,
  }) => {
    await prepararCenario()

    // Ato 1 — um snapshot válido antes da queda, para provar depois que ele sobrevive.
    await programarInmet([{ preset: 'chuva', milimetros: CHUVA_INFORMATIVA_MM }], ESTACAO_CHUVA)
    const coleta = await solicitarColeta(AREA_CHUVA_ID)
    expect(coleta.estado).toBe('concluido')
    expect(coleta.registros_validos).toBe(1)

    const antesDaQueda = await obterSincronizacoes()
    const snapshotValido = antesDaQueda.ultima_valida
    expect(snapshotValido?.id).toBe(coleta.id)

    // Ato 2 — INMET indisponível: coleta e ping de prontidão seguram a conexão até o timeout.
    await programarInmet([{ falha: 'timeout' }], ESTACAO_CHUVA)
    await programarSondaInmet([{ falha: 'timeout' }])

    await abrirProntidao(page)
    const linhaInmet = page.getByRole('row').filter({ has: page.getByRole('rowheader', { name: 'INMET' }) })
    await linhaInmet.getByRole('button', { name: 'Verificar novamente: INMET' }).click()
    await expect(linhaInmet.getByText('Indisponível')).toBeVisible()
    await expect(linhaInmet.getByText(CAUSA_TIMEOUT_INMET)).toBeVisible()
    await expect(linhaInmet.getByText(IMPACTO_INMET_INDISPONIVEL)).toBeVisible()

    // Timeout e tentativas: a execução esgota as 3 tentativas e termina em `falhou_coleta`.
    const execucaoFalha = await iniciarExecucao(AREA_CHUVA_ID)
    const terminal = await aguardarEstado(execucaoFalha, ['falhou_coleta'])
    expect(terminal.estado).toBe('falhou_coleta')

    const aposQueda = await obterSincronizacoes()
    const falhada = aposQueda.ultima_tentativa
    expect(falhada?.estado).toBe('falha')
    expect(falhada?.motivo_falha).toBe(MOTIVO_RETENTATIVAS_ESGOTADAS)
    expect(falhada?.limite_tentativas).toBe(MAXIMO_TENTATIVAS_COLETA)
    expect(falhada?.tentativas.map((tentativa) => tentativa.numero_tentativa)).toEqual([1, 2, 3])
    expect(falhada?.tentativas.map((tentativa) => tentativa.codigo_resultado)).toEqual([
      'timeout',
      'timeout',
      'timeout',
    ])

    // Snapshot apenas informativo: o último válido continua consultável, e nenhuma avaliação
    // de risco nova foi iniciada a partir dele — a execução parou em `falhou_coleta`.
    expect(aposQueda.ultima_valida?.id).toBe(snapshotValido?.id)
    expect(aposQueda.ultima_valida?.registros_validos).toBe(1)
    expect(terminal.marcos.map((marco) => marco.marco)).toEqual(['falhou_coleta'])

    const cronologia = await obterLinhaDoTempo(execucaoFalha)
    const excecao = cronologia.marcos.find((marco) => marco.tipo === 'excecao')
    expect(excecao?.acao).toBe('exceção técnica da execução')
    expect(excecao?.resultado).toContain('Timeout')

    // Ato 3 — ativação explícita do cenário sintético rotulado (AD-013).
    await programarInmet(
      [{ preset: 'granizo-sintetico', intensidade: GRANIZO_ACIMA_DO_LIMIAR }],
      ESTACAO_GRANIZO,
    )
    await ativarCenarioSintetico(CENARIO_GRANIZO, AREA_GRANIZO_ID)

    const eventos = await listarEventos()
    const granizo = eventos.eventos.find((evento) => evento.tipo === 'granizo')
    expect(granizo?.proveniencia).toBe('sintetico')

    const execucaoSintetica = await iniciarExecucao(AREA_GRANIZO_ID)
    await aguardarEstado(execucaoSintetica, ['aguardando_geracao'])
    await solicitarPreflight(execucaoSintetica)
    await aguardarEstado(execucaoSintetica, ['aguardando_revisao'])

    // Origem sintética visível em cada etapa seguinte, nunca substituída por `real_inmet`.
    const lote = await obterLoteRevisao(execucaoSintetica)
    expect(lote.evento?.proveniencia).toBe('sintetico')
    const item = lote.itens[0]!

    await decidirLote(execucaoSintetica, [
      { mensagem_id: item.mensagem_id, versao_esperada: item.versao, resultado: 'aprovar' },
    ])
    await aguardarEstado(execucaoSintetica, ['aguardando_confirmacao'])

    const resumo = await obterSimulacao(execucaoSintetica)
    const confirmada = await confirmarSimulacao(execucaoSintetica, resumo.versao)
    expect(confirmada.estado).toBe('concluida')

    const alerta = await obterAlertaMaisRelevante(SEGURADO_GRANIZO_ELEGIVEL_ID)
    expect(alerta.alerta?.origem).toBe('sintetico')

    // Fim do fluxo: o segurado vê o comunicado com a origem sintética rotulada na tela.
    await abrirPainelSegurado(page, NOME_SEGURADO_GRANIZO_ELEGIVEL)
    const visaoGeral = page.getByRole('main').filter({ hasText: 'Impactos esperados' })
    await expect(visaoGeral.getByText('Cenário demonstrativo (sintético)').first()).toBeVisible()

    const comunicados = page.getByRole('main').filter({ hasText: 'Seus comunicados' })
    await expect(comunicados.getByRole('cell', { name: 'SMS' })).toBeVisible()
  })
})
