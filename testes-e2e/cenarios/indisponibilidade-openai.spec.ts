/**
 * Cenário E2E-06 — produção agêntica alcançada com a OpenAI indisponível ou mal configurada.
 *
 * O fluxo determinístico (coleta, normalização, relevância, elegibilidade) roda inteiro e
 * chega a `aguardando_geracao`. Só então o preflight de IA é acionado: as três tentativas
 * falham, a execução termina em `falhou_preparacao_ia` e nenhuma chamada de geração chega a
 * acontecer. O que o AC exige provar é o negativo — nenhum texto fixo substituindo a resposta
 * da IA, nenhum modelo alternativo — e o positivo, que todo o trabalho determinístico anterior
 * continua consultável.
 *
 * Dois desfechos de bloqueio são cobertos, ambos terminando em `falhou_preparacao_ia` com
 * causas distintas: OpenAI inalcançável (falha de transporte) e modelo configurado ausente do
 * catálogo (configuração inconsistente).
 *
 * SPEC_DEVIATION: a variante literal "`OPENAI_API_KEY` ausente" não é exercitada aqui. O
 * backend real da suíte é iniciado uma única vez pelo `globalSetup`, com porta fixa e um único
 * escritor DuckDB; derrubá-lo e reiniciá-lo sem credencial no meio de um cenário deixaria os
 * demais arquivos de teste sem backend caso a reinicialização falhasse. O AC é disjuntivo
 * ("indisponibilidade **ou** configuração ausente") e as duas causas cobertas aqui atravessam
 * exatamente o mesmo caminho de código do curto-circuito por credencial ausente
 * (`VerificadorDisponibilidadeOpenAI.verificar` → `_preparar_agora` → `falhou_preparacao_ia`).
 * A causa `CAUSA_CREDENCIAL_AUSENTE` em si já tem cobertura de integração no backend, em
 * `src/backend/testes/test_preflight_ia_api.py`.
 */

import { expect, test } from '@playwright/test'
import { ESTACAO_CHUVA, MODELO_OPENAI_E2E } from '../suporte/ambiente.ts'
import {
  aguardarEstado,
  iniciarExecucao,
  listarComunicados,
  listarEventos,
  obterAvaliacaoRisco,
  obterDetalheElegibilidade,
  obterElegibilidade,
  obterMensagens,
  obterSimulacao,
  obterSincronizacoes,
  solicitarPreflight,
} from '../suporte/api.ts'
import { abrirPainelSegurado, abrirProntidao, prepararCenario } from '../suporte/cenario.ts'
import {
  chamadasRegistradas,
  programarInmet,
  programarModelosOpenAI,
} from '../suporte/dubles-cliente.ts'
import {
  AREA_CHUVA_ID,
  NOME_SEGURADO_CHUVA_ELEGIVEL,
  NOME_SEGURADO_CHUVA_NAO_ELEGIVEL,
  SEGURADO_CHUVA_ELEGIVEL_ID,
} from '../suporte/identificadores.ts'

/** Acima do limiar de 50 mm da regra de chuva intensa semeada (`semeador.py`). */
const CHUVA_ACIMA_DO_LIMIAR_MM = 55.4

/** Tentativas do preflight de disponibilidade (`MAXIMO_TENTATIVAS`, AD-8). */
const MAXIMO_TENTATIVAS_PREFLIGHT = 3

/** Causas sanitizadas do verificador (`verificador_disponibilidade_openai.py`). */
const CAUSA_CONEXAO = 'Falha de conexão ao consultar a OpenAI.'
const CAUSA_MODELO_AUSENTE = `O modelo configurado ('${MODELO_OPENAI_E2E}') não está no catálogo da OpenAI.`

/** Textos que a Prontidão exibe com a OpenAI fora do ar (`aplicacao/prontidao.py`). */
const IMPACTO_OPENAI_INDISPONIVEL = 'Produção agêntica indisponível.'

test.describe('E2E-06: indisponibilidade da OpenAI', () => {
  test('termina em falhou_preparacao_ia sem texto fixo e preserva o trabalho deterministico', async ({
    page,
  }) => {
    await prepararCenario()
    await programarInmet([{ preset: 'chuva', milimetros: CHUVA_ACIMA_DO_LIMIAR_MM }], ESTACAO_CHUVA)
    await programarModelosOpenAI([{ falha: 'conexao' }])

    const execucaoId = await iniciarExecucao(AREA_CHUVA_ID)
    const comPublico = await aguardarEstado(execucaoId, ['aguardando_geracao'])
    expect(comPublico.publico_elegivel_total).toBe(1)

    const preflight = await solicitarPreflight(execucaoId)
    expect(preflight.estado).toBe('falhou_preparacao_ia')
    expect(preflight.causa).toBe(CAUSA_CONEXAO)
    expect(preflight.contextos_montados).toBe(0)

    const terminal = await aguardarEstado(execucaoId, ['falhou_preparacao_ia'])
    expect(terminal.estado).toBe('falhou_preparacao_ia')
    const marcoBloqueio = terminal.marcos.find((marco) => marco.marco === 'falhou_preparacao_ia')
    expect(marcoBloqueio?.causa).toBe(CAUSA_CONEXAO)

    // Sem resposta fixa e sem modelo alternativo: as 3 tentativas de disponibilidade
    // aconteceram e nenhuma chamada de geração foi feita (PREFL-03).
    const chamadas = await chamadasRegistradas()
    expect(chamadas.openaiModelos).toHaveLength(MAXIMO_TENTATIVAS_PREFLIGHT)
    expect(chamadas.openaiChat).toEqual([])

    const mensagens = await obterMensagens(execucaoId)
    expect(mensagens.registros).toEqual([])
    const simulacao = await obterSimulacao(execucaoId)
    expect(simulacao.entregas).toEqual([])
    const comunicados = await listarComunicados(SEGURADO_CHUVA_ELEGIVEL_ID)
    expect(comunicados.comunicados).toEqual([])

    // Trabalho determinístico anterior (2.1–2.6) permanece consultável depois do bloqueio.
    const sincronizacoes = await obterSincronizacoes()
    expect(sincronizacoes.ultima_valida?.registros_validos).toBe(1)

    const eventos = await listarEventos()
    expect(eventos.eventos.some((evento) => evento.tipo === 'chuva_intensa')).toBe(true)

    const risco = await obterAvaliacaoRisco(execucaoId)
    expect(risco.motivo).toBe('relevante')
    expect(risco.regra_id).not.toBeNull()

    const elegibilidade = await obterElegibilidade(execucaoId)
    expect(elegibilidade.incluidos).toBe(1)
    expect(elegibilidade.excluidos).toBe(1)

    const naoElegivel = elegibilidade.registros.find((registro) => !registro.elegivel)
    expect(naoElegivel?.nome_segurado).toBe(NOME_SEGURADO_CHUVA_NAO_ELEGIVEL)
    const explicacao = await obterDetalheElegibilidade(execucaoId, naoElegivel!.id)
    expect(explicacao.criterios.find((criterio) => !criterio.atende)?.justificativa).toBe(
      'Apólice não está ativa (situação: cancelada).',
    )

    expect(terminal.marcos.map((marco) => marco.marco)).toEqual([
      'coleta_concluida',
      'avaliacao_risco_concluida',
      'avaliacao_elegibilidade_concluida',
      'publico_elegivel_formado',
      'aguardando_geracao',
      'falhou_preparacao_ia',
    ])

    // A interface real não inventa conteúdo: o segurado elegível não recebe comunicado.
    await abrirPainelSegurado(page, NOME_SEGURADO_CHUVA_ELEGIVEL)
    await expect(
      page.getByRole('main').filter({ hasText: 'Nenhum comunicado no momento' }),
    ).toBeVisible()

    // E a Prontidão explica a causa em vez de escondê-la.
    await abrirProntidao(page)
    const linhaOpenAI = page
      .getByRole('row')
      .filter({ has: page.getByRole('rowheader', { name: 'OpenAI' }) })
    await linhaOpenAI.getByRole('button', { name: 'Verificar novamente: OpenAI' }).click()
    await expect(linhaOpenAI.getByText('Indisponível', { exact: true })).toBeVisible()
    await expect(linhaOpenAI.getByText(CAUSA_CONEXAO)).toBeVisible()
    await expect(linhaOpenAI.getByText(IMPACTO_OPENAI_INDISPONIVEL)).toBeVisible()
  })

  test('termina em falhou_preparacao_ia quando o modelo configurado nao esta no catalogo', async () => {
    await prepararCenario()
    await programarInmet([{ preset: 'chuva', milimetros: CHUVA_ACIMA_DO_LIMIAR_MM }], ESTACAO_CHUVA)
    await programarModelosOpenAI([{ modelos: [] }])

    const execucaoId = await iniciarExecucao(AREA_CHUVA_ID)
    await aguardarEstado(execucaoId, ['aguardando_geracao'])

    const preflight = await solicitarPreflight(execucaoId)
    expect(preflight.estado).toBe('falhou_preparacao_ia')
    expect(preflight.causa).toBe(CAUSA_MODELO_AUSENTE)

    const chamadas = await chamadasRegistradas()
    expect(chamadas.openaiChat).toEqual([])

    const mensagens = await obterMensagens(execucaoId)
    expect(mensagens.registros).toEqual([])

    const elegibilidade = await obterElegibilidade(execucaoId)
    expect(elegibilidade.incluidos).toBe(1)
  })
})
