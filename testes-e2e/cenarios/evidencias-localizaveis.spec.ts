/**
 * Cenário E2E-08 — toda evidência de um cenário executado é localizável, e o contrato bate.
 *
 * Executa o cenário de chuva intensa até a conclusão e percorre, sobre esse mesmo dado, as
 * sete evidências que o AC exige: prontidão, evento e decisão, supervisão, resultados,
 * comunicado, explicação e linha do tempo. Nenhuma delas exige editar arquivo ou banco: tudo
 * é alcançado por navegação na interface ou por leitura (`GET`) da API pública. A única
 * mutação do cenário é a restauração inicial, feita pelo endpoint público de demonstração.
 *
 * Divisão entre interface e API, e por quê: as superfícies de Administrador dos Épicos 2–4
 * (evento e decisão, supervisão, resultados, linha do tempo) e a gaveta de explicação do
 * comunicado (`SuperficieExplicacaoComunicado`) existem e são testadas em `vitest`, mas ainda
 * não estão montadas em `App.tsx` — item aberto já registrado em `.specs/STATE.md`. As
 * evidências dessas quatro superfícies são alcançadas aqui pela API REST real, que é o mesmo
 * contrato que elas consomem. O que **está** montado é exercitado na interface real:
 * Prontidão, Documentação da API, e, no perfil Segurado, alertas (com explicação e linha do
 * tempo do alerta) e comunicados.
 *
 * A segunda metade do AC — "OpenAPI/Swagger UI correspondem à API realmente utilizada" —
 * compara o documento servido pelo processo em execução com o instantâneo versionado em
 * `composicao/openapi.json` e confirma que toda rota exercitada pela suíte está documentada.
 * O `pytest` já garante que o instantâneo não diverge do app montado
 * (`src/backend/testes/test_openapi_sincronizado.py`); aqui a checagem é sobre o processo
 * realmente no ar, que é o que o AC pede.
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { expect, test } from '@playwright/test'
import { ENDERECO_BACKEND, ESTACAO_CHUVA, RAIZ_PROJETO } from '../suporte/ambiente.ts'
import {
  aguardarEstado,
  confirmarSimulacao,
  decidirLote,
  iniciarExecucao,
  listarComunicados,
  listarEventos,
  obterAvaliacaoRisco,
  obterDetalheElegibilidade,
  obterDetalheMensagem,
  obterElegibilidade,
  obterExplicacaoComunicado,
  obterLinhaDoTempo,
  obterLoteRevisao,
  obterResultados,
  obterSimulacao,
  solicitarPreflight,
} from '../suporte/api.ts'
import { abrirPainelSegurado, abrirProntidao, conteudoComTexto, prepararCenario } from '../suporte/cenario.ts'
import { programarInmet } from '../suporte/dubles-cliente.ts'
import {
  AREA_CHUVA_ID,
  NOME_SEGURADO_CHUVA_ELEGIVEL,
  NOME_SEGURADO_CHUVA_NAO_ELEGIVEL,
  SEGURADO_CHUVA_ELEGIVEL_ID,
} from '../suporte/identificadores.ts'
import { CONTEUDO_PADRAO_DUBLE } from '../suporte/servidor-dubles.ts'

/** Acima do limiar de 50 mm da regra de chuva intensa semeada (`semeador.py`). */
const CHUVA_ACIMA_DO_LIMIAR_MM = 55.4

/** Instantâneo versionado do contrato, exportado por `composicao/openapi_export.py`. */
const CAMINHO_SNAPSHOT_OPENAPI = resolve(
  RAIZ_PROJETO,
  'src/backend/central_preventiva/composicao/openapi.json',
)

type DocumentoOpenApi = { info: { title: string }; paths: Record<string, Record<string, unknown>> }

/** Operações `método caminho` de um documento OpenAPI, ordenadas. */
function operacoes(documento: DocumentoOpenApi): string[] {
  return Object.entries(documento.paths)
    .flatMap(([caminho, metodos]) =>
      Object.keys(metodos).map((metodo) => `${metodo.toUpperCase()} ${caminho}`),
    )
    .sort()
}

/** Rotas que esta suíte E2E de fato exercita contra o processo em execução. */
const ROTAS_EXERCITADAS: readonly string[] = [
  'POST /api/v1/dados-sinteticos/restauracoes',
  'GET /api/v1/execucoes',
  'POST /api/v1/execucoes',
  'GET /api/v1/execucoes/{execucao_id}',
  'GET /api/v1/execucoes/{execucao_id}/avaliacao-risco',
  'POST /api/v1/execucoes/{execucao_id}/confirmar-simulacao',
  'GET /api/v1/execucoes/{execucao_id}/elegibilidade',
  'GET /api/v1/execucoes/{execucao_id}/elegibilidade/{registro_id}',
  'GET /api/v1/execucoes/{execucao_id}/linha-do-tempo',
  'GET /api/v1/execucoes/{execucao_id}/mensagens',
  'GET /api/v1/execucoes/{execucao_id}/mensagens/{mensagem_id}/detalhe',
  'POST /api/v1/execucoes/{execucao_id}/preflight',
  'GET /api/v1/execucoes/{execucao_id}/resultados',
  'GET /api/v1/execucoes/{execucao_id}/revisao',
  'POST /api/v1/execucoes/{execucao_id}/revisao/decisoes',
  'GET /api/v1/execucoes/{execucao_id}/simulacao',
  'POST /api/v1/execucoes/{execucao_origem_id}/nova-tentativa-ia',
  'POST /api/v1/meteorologia/cenarios-sinteticos/{identificador}/ativar',
  'POST /api/v1/meteorologia/coletas',
  'GET /api/v1/meteorologia/eventos',
  'GET /api/v1/meteorologia/sincronizacoes',
  'GET /api/v1/prontidao/dependencias',
  'POST /api/v1/prontidao/dependencias/{nome}/verificacoes',
  'GET /api/v1/regras/{regra_id}',
  'GET /api/v1/saude',
  'GET /api/v1/segurados',
  'GET /api/v1/segurados/padrao',
  'GET /api/v1/segurados/{segurado_id}/alerta-mais-relevante',
  'GET /api/v1/segurados/{segurado_id}/alertas',
  'GET /api/v1/segurados/{segurado_id}/alertas/{elegibilidade_id}',
  'GET /api/v1/segurados/{segurado_id}/apolice',
  'GET /api/v1/segurados/{segurado_id}/comunicados',
  'GET /api/v1/segurados/{segurado_id}/comunicados/{entrega_simulada_id}',
  'GET /api/v1/segurados/{segurado_id}/comunicados/{entrega_simulada_id}/explicacao',
  'POST /api/v1/segurados/{segurado_id}/comunicados/{entrega_simulada_id}/visualizacao',
  'GET /api/v1/segurados/{segurado_id}/preferencias',
  'PUT /api/v1/segurados/{segurado_id}/preferencias',
]

test.describe('E2E-08: evidências localizáveis e contrato de API fiel', () => {
  test('localiza prontidao, evento, supervisao, resultados, comunicado, explicacao e linha do tempo', async ({
    page,
  }) => {
    await prepararCenario()
    await programarInmet([{ preset: 'chuva', milimetros: CHUVA_ACIMA_DO_LIMIAR_MM }], ESTACAO_CHUVA)

    const execucaoId = await iniciarExecucao(AREA_CHUVA_ID)
    await aguardarEstado(execucaoId, ['aguardando_geracao'])
    await solicitarPreflight(execucaoId)
    await aguardarEstado(execucaoId, ['aguardando_revisao'])
    const loteInicial = await obterLoteRevisao(execucaoId)
    const item = loteInicial.itens[0]!
    await decidirLote(execucaoId, [
      { mensagem_id: item.mensagem_id, versao_esperada: item.versao, resultado: 'aprovar' },
    ])
    await aguardarEstado(execucaoId, ['aguardando_confirmacao'])
    const resumo = await obterSimulacao(execucaoId)
    const confirmada = await confirmarSimulacao(execucaoId, resumo.versao)
    expect(confirmada.estado).toBe('concluida')

    // 1. Prontidão — superfície real, montada no perfil Administrador.
    await abrirProntidao(page)
    const tabelaProntidao = page.getByRole('table', { name: 'Prontidão das 4 dependências' })
    for (const dependencia of ['Backend', 'Banco de dados', 'INMET', 'OpenAI']) {
      await expect(tabelaProntidao.getByRole('rowheader', { name: dependencia })).toBeVisible()
    }

    // 2. Evento e decisão — o evento normalizado e a regra que decidiu a relevância.
    const eventos = await listarEventos()
    const evento = eventos.eventos.find((registro) => registro.tipo === 'chuva_intensa')
    expect(evento?.proveniencia).toBe('real_inmet')

    const risco = await obterAvaliacaoRisco(execucaoId)
    expect(risco.evento_id).toBe(evento?.id)
    expect(risco.motivo).toBe('relevante')
    expect(risco.regra_id).not.toBeNull()
    expect(risco.criterios.every((criterio) => criterio.justificativa !== '')).toBe(true)

    // 3. Supervisão — o lote de revisão humana com destinatário, origem e decisão registrada.
    const lote = await obterLoteRevisao(execucaoId)
    expect(lote.total_publico_incluido).toBe(1)
    expect(lote.itens[0]?.destinatario.nome_segurado).toBe(NOME_SEGURADO_CHUVA_ELEGIVEL)
    expect(lote.itens[0]?.origem.regra_id).toBe(risco.regra_id)

    const elegibilidade = await obterElegibilidade(execucaoId)
    const excluido = elegibilidade.registros.find((registro) => !registro.elegivel)
    expect(excluido?.nome_segurado).toBe(NOME_SEGURADO_CHUVA_NAO_ELEGIVEL)
    const explicacaoExclusao = await obterDetalheElegibilidade(execucaoId, excluido!.id)
    expect(explicacaoExclusao.criterios.find((criterio) => !criterio.atende)?.operando).toBe(
      'situação da apólice',
    )

    // 4. Resultados — totais consolidados e o detalhe da mensagem que os produziu.
    const resultados = await obterResultados(execucaoId)
    expect(resultados.concluido).toBe(true)
    expect(resultados.totais_por_estado).toEqual([{ chave: 'simulada_entregue', total: 1 }])
    expect(resultados.nao_simulaveis).toEqual([])

    const detalheMensagem = await obterDetalheMensagem(execucaoId, item.mensagem_id)
    expect(detalheMensagem.estado).toBe('simulada_entregue')
    expect(detalheMensagem.versoes[0]?.avaliacao_critica?.aprovada).toBe(true)

    // 7. Linha do tempo — a cronologia completa, com os três atores presentes.
    const cronologia = await obterLinhaDoTempo(execucaoId)
    const tipos = new Set(cronologia.marcos.map((marco) => marco.tipo))
    expect(tipos.has('execucao')).toBe(true)
    expect(tipos.has('risco')).toBe(true)
    expect(tipos.has('elegibilidade')).toBe(true)
    expect(tipos.has('geracao')).toBe(true)
    expect(tipos.has('critica')).toBe(true)
    expect(tipos.has('decisao_humana')).toBe(true)
    expect(tipos.has('simulacao')).toBe(true)

    // 5 e 6 na interface real do Segurado: comunicado, explicação do alerta e linha do
    // tempo do alerta, todos alcançáveis por navegação.
    await abrirPainelSegurado(page, NOME_SEGURADO_CHUVA_ELEGIVEL)

    const alertas = conteudoComTexto(page, 'Seus alertas')
    await alertas.getByRole('button', { name: 'Ver detalhe' }).first().click()
    const detalheAlerta = conteudoComTexto(page, 'Contexto da apólice')
    await expect(detalheAlerta.getByRole('heading', { name: 'Contexto da apólice' })).toBeVisible()
    await expect(detalheAlerta.getByRole('heading', { name: 'Linha do tempo' })).toBeVisible()

    const comunicados = conteudoComTexto(page, 'Seus comunicados')
    await comunicados.getByRole('button', { name: 'Ver detalhe' }).first().click()
    const detalheComunicado = conteudoComTexto(page, 'Seu comunicado preventivo')
    await expect(detalheComunicado.getByText(CONTEUDO_PADRAO_DUBLE.whatsapp)).toBeVisible()
    await expect(
      detalheComunicado.getByRole('heading', { name: 'Linha do tempo' }),
    ).toBeVisible()

    // 6. Explicação do comunicado — determinística e agêntica, separadas por origem.
    const lista = await listarComunicados(SEGURADO_CHUVA_ELEGIVEL_ID)
    const entregaId = lista.comunicados[0]!.entrega_simulada_id
    const explicacao = await obterExplicacaoComunicado(SEGURADO_CHUVA_ELEGIVEL_ID, entregaId)
    expect(explicacao.execucao_id).toBe(execucaoId)
    expect(explicacao.evento_e_regra.origem).toBe('deterministica')
    expect(explicacao.evento_e_regra.regra_id).toBe(risco.regra_id)
    expect(explicacao.evento_e_regra.evento?.tipo).toBe('chuva_intensa')
    expect(explicacao.agente.origem).toBe('agente')
    expect(explicacao.agente.status).toBe('completa')
    expect(explicacao.agente.tentativas).toHaveLength(1)
    expect(explicacao.contexto?.categorias_usadas.length).toBeGreaterThan(0)
    expect(explicacao.contexto?.categorias_nao_usadas.length).toBeGreaterThan(0)
  })

  test('openapi servido pelo processo corresponde ao contrato versionado e a suite usada', async ({
    page,
    request,
  }) => {
    const respostaAoVivo = await request.get(`${ENDERECO_BACKEND}/openapi.json`)
    expect(respostaAoVivo.status()).toBe(200)
    const aoVivo = (await respostaAoVivo.json()) as DocumentoOpenApi

    const versionado = JSON.parse(
      readFileSync(CAMINHO_SNAPSHOT_OPENAPI, 'utf8'),
    ) as DocumentoOpenApi

    expect(operacoes(aoVivo)).toEqual(operacoes(versionado))
    expect(aoVivo.info.title).toBe(versionado.info.title)

    // Toda rota que a suíte E2E realmente exercita está no contrato publicado.
    const publicadas = new Set(operacoes(aoVivo))
    const ausentes = ROTAS_EXERCITADAS.filter((rota) => !publicadas.has(rota))
    expect(ausentes).toEqual([])

    // Swagger UI real, alcançável a partir da superfície de Documentação da API.
    await page.goto('/')
    await page.getByRole('button', { name: 'Documentação da API' }).click()
    const superficie = conteudoComTexto(page, 'Documentação da API')
    await expect(superficie.getByText('Disponível', { exact: true })).toBeVisible()
    const enlaceSwagger = superficie.getByRole('link', { name: `${ENDERECO_BACKEND}/docs` })
    await expect(enlaceSwagger).toBeVisible()

    await page.goto(`${ENDERECO_BACKEND}/docs`)
    await expect(page.getByRole('heading', { name: versionado.info.title })).toBeVisible()
  })
})
