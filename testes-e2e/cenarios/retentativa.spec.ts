/**
 * Cenário E2E-07 — retentativa correlacionada a partir de uma falha terminal, sem duplicação.
 *
 * A execução de origem é levada a `falhou_preparacao_ia` derrubando a OpenAI durante o
 * preflight (mesmo caminho de E2E-06). Com a OpenAI de volta, a nova tentativa é pedida pelo
 * comando real: ela cria uma execução nova, correlacionada por `execucao_origem_id`, com
 * cópias próprias das linhas de elegibilidade da origem (AD-012) — a origem nunca é reaberta
 * nem mutada (AD-009).
 *
 * A segunda metade do AC é a idempotência: repetir o comando com a mesma `Idempotency-Key`
 * devolve a execução já criada, sem criar uma segunda nem duplicar o efeito (AD-002).
 *
 * As etapas são dirigidas pela API REST porque as superfícies de Administrador dos Épicos 2–4
 * ainda não estão montadas em `App.tsx` (item aberto registrado em `.specs/STATE.md`).
 */

import { randomUUID } from 'node:crypto'
import { expect, test } from '@playwright/test'
import { ESTACAO_CHUVA, MODELO_OPENAI_E2E } from '../suporte/ambiente.ts'
import {
  aguardarEstado,
  buscarExecucoes,
  iniciarExecucao,
  obterElegibilidade,
  obterExecucao,
  obterLinhaDoTempo,
  solicitarNovaTentativaIA,
  solicitarPreflight,
} from '../suporte/api.ts'
import { prepararCenario } from '../suporte/cenario.ts'
import { programarInmet, programarModelosOpenAI } from '../suporte/dubles-cliente.ts'
import { AREA_CHUVA_ID, NOME_SEGURADO_CHUVA_ELEGIVEL } from '../suporte/identificadores.ts'

/** Acima do limiar de 50 mm da regra de chuva intensa semeada (`semeador.py`). */
const CHUVA_ACIMA_DO_LIMIAR_MM = 55.4

test.describe('E2E-07: retentativa correlacionada', () => {
  test('cria execucao correlacionada com snapshots validos e nao duplica ao repetir', async () => {
    await prepararCenario()
    await programarInmet([{ preset: 'chuva', milimetros: CHUVA_ACIMA_DO_LIMIAR_MM }], ESTACAO_CHUVA)
    await programarModelosOpenAI([{ falha: 'conexao' }])

    const origemId = await iniciarExecucao(AREA_CHUVA_ID)
    await aguardarEstado(origemId, ['aguardando_geracao'])
    await solicitarPreflight(origemId)
    await aguardarEstado(origemId, ['falhou_preparacao_ia'])

    const elegibilidadeOrigem = await obterElegibilidade(origemId)
    expect(elegibilidadeOrigem.incluidos).toBe(1)
    expect(elegibilidadeOrigem.excluidos).toBe(1)

    // OpenAI de volta: a nova tentativa parte de um terreno em que ela pode ter sucesso.
    await programarModelosOpenAI([{ modelos: [MODELO_OPENAI_E2E] }])

    const chaveRetentativa = randomUUID()
    const criada = await solicitarNovaTentativaIA(origemId, chaveRetentativa)
    expect(criada.execucao_origem_id).toBe(origemId)
    expect(criada.execucao_id).not.toBe(origemId)

    const nova = await obterExecucao(criada.execucao_id)
    expect(nova.estado).toBe('aguardando_geracao')
    expect(nova.execucao_origem_id).toBe(origemId)

    // A origem permanece terminal e passa a apontar a correlacionada, sem reabrir.
    const origemDepois = await obterExecucao(origemId)
    expect(origemDepois.estado).toBe('falhou_preparacao_ia')
    expect(origemDepois.retentativas).toEqual([criada.execucao_id])

    // Snapshots imutáveis válidos: cópias próprias, mesmo conteúdo, identificadores novos.
    const elegibilidadeNova = await obterElegibilidade(criada.execucao_id)
    expect(elegibilidadeNova.incluidos).toBe(1)
    expect(elegibilidadeNova.excluidos).toBe(1)
    const conteudoDe = (registros: typeof elegibilidadeOrigem.registros) =>
      registros
        .map((registro) => ({
          nome_segurado: registro.nome_segurado,
          apolice_id: registro.apolice_id,
          codigo_ibge_area: registro.codigo_ibge_area,
          canal: registro.canal,
          elegivel: registro.elegivel,
        }))
        .sort((a, b) => a.nome_segurado.localeCompare(b.nome_segurado))

    expect(conteudoDe(elegibilidadeNova.registros)).toEqual(
      conteudoDe(elegibilidadeOrigem.registros),
    )
    const idsOrigem = new Set(elegibilidadeOrigem.registros.map((registro) => registro.id))
    expect(elegibilidadeNova.registros.some((registro) => idsOrigem.has(registro.id))).toBe(false)

    // Idempotência: repetir o comando devolve a mesma execução, sem criar outra nem
    // duplicar as linhas de elegibilidade copiadas.
    const repetida = await solicitarNovaTentativaIA(origemId, chaveRetentativa)
    expect(repetida.execucao_id).toBe(criada.execucao_id)
    expect(repetida.execucao_origem_id).toBe(origemId)

    const origemAposRepetir = await obterExecucao(origemId)
    expect(origemAposRepetir.estado).toBe('falhou_preparacao_ia')
    expect(origemAposRepetir.retentativas).toEqual([criada.execucao_id])

    const aguardando = await buscarExecucoes('aguardando_geracao')
    expect(aguardando.resultados.map((resultado) => resultado.execucao_id)).toEqual([
      criada.execucao_id,
    ])

    const elegibilidadeAposRepetir = await obterElegibilidade(criada.execucao_id)
    expect(elegibilidadeAposRepetir.registros).toHaveLength(
      elegibilidadeNova.registros.length,
    )

    // Cada execução guarda a própria cronologia, sem mesclar marcos.
    const cronologiaOrigem = await obterLinhaDoTempo(origemId)
    expect(cronologiaOrigem.execucao_origem_id).toBeNull()
    expect(cronologiaOrigem.retentativas).toEqual([criada.execucao_id])
    const cronologiaNova = await obterLinhaDoTempo(criada.execucao_id)
    expect(cronologiaNova.execucao_origem_id).toBe(origemId)
    expect(cronologiaNova.retentativas).toEqual([])

    // Os snapshots copiados são utilizáveis: a nova execução avança até a revisão humana.
    await solicitarPreflight(criada.execucao_id)
    const emRevisao = await aguardarEstado(criada.execucao_id, ['aguardando_revisao'])
    expect(emRevisao.estado).toBe('aguardando_revisao')

    const origemAoFinal = await obterExecucao(origemId)
    expect(origemAoFinal.estado).toBe('falhou_preparacao_ia')
    expect(
      elegibilidadeNova.registros.some(
        (registro) => registro.elegivel && registro.nome_segurado === NOME_SEGURADO_CHUVA_ELEGIVEL,
      ),
    ).toBe(true)
  })
})
