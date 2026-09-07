/**
 * Cenário E2E-04 — regeneração automática e esgotamento das três tentativas.
 *
 * Mesma entrada do cenário de chuva intensa, com uma diferença: o dublê do agente crítico
 * reprova toda avaliação. Como o crítico e o redator compartilham a rota
 * `POST /v1/chat/completions` e se distinguem pelo `response_format.json_schema.name`, a
 * reprovação é programada só na fila do esquema `AvaliacaoEstruturada` — o redator segue
 * respondendo normalmente, e cada reprovação devolve a mensagem ao redator (REGEN-01).
 *
 * O cenário comprova as duas metades do AC: o ciclo reprova→regenera acontece até a terceira
 * tentativa, e a terceira reprovação fecha a mensagem em `falhou_conteudo` com uma `Exceção`
 * própria, mantendo-a fora do lote simulável — nada do que ela gerou chega ao segurado.
 */

import { expect, test } from '@playwright/test'
import { ESTACAO_CHUVA } from '../suporte/ambiente.ts'
import {
  aguardarEstado,
  decidirLote,
  iniciarExecucao,
  listarComunicados,
  obterDetalheMensagem,
  obterLoteRevisao,
  obterMensagens,
  obterResultados,
  obterSimulacao,
  solicitarPreflight,
} from '../suporte/api.ts'
import { abrirPainelSegurado, conteudoComTexto, prepararCenario } from '../suporte/cenario.ts'
import { chamadasRegistradas, programarChatOpenAI, programarInmet } from '../suporte/dubles-cliente.ts'
import { AREA_CHUVA_ID, NOME_SEGURADO_CHUVA_ELEGIVEL, SEGURADO_CHUVA_ELEGIVEL_ID } from '../suporte/identificadores.ts'

/** Acima do limiar de 50 mm da regra de chuva intensa semeada (`semeador.py`). */
const CHUVA_ACIMA_DO_LIMIAR_MM = 55.4

/** Esquema da saída estruturada do agente crítico (`adaptadores/ia/agente_critico.py`). */
const ESQUEMA_CRITICO = 'AvaliacaoEstruturada'

/** Esquema da saída estruturada do redator no canal WhatsApp (`agente_redator.py`). */
const ESQUEMA_REDATOR_WHATSAPP = 'SaidaWhatsApp'

/** Categoria fechada usada na reprovação (`dominio/avaliacao_critica.py`). */
const CATEGORIA_REPROVADA = 'tom'

const JUSTIFICATIVA_REPROVACAO = 'O texto soa alarmista e não preventivo.'

/** Máximo de tentativas de conteúdo por mensagem (`MAXIMO_TENTATIVAS_MENSAGEM`, REGEN-02). */
const MAXIMO_TENTATIVAS_MENSAGEM = 3

/** Impacto registrado na `Exceção` de esgotamento (`IMPACTO_ITEM_FORA_DO_LOTE`, REGEN-04). */
const IMPACTO_ITEM_FORA_DO_LOTE =
  'Este item não integra o lote simulável; os demais seguem normalmente.'

/** Motivo legível de uma mensagem que nunca vira entrega (`MOTIVOS_NAO_SIMULAVEL`). */
const MOTIVO_NAO_SIMULAVEL = 'esgotou as tentativas de geração de conteúdo válido'

test.describe('E2E-04: regeneração e esgotamento de tentativas', () => {
  test('regenera ate a terceira tentativa e esgota em falhou_conteudo com excecao', async ({
    page,
  }) => {
    await prepararCenario()
    await programarInmet([{ preset: 'chuva', milimetros: CHUVA_ACIMA_DO_LIMIAR_MM }], ESTACAO_CHUVA)
    await programarChatOpenAI(
      [
        {
          conteudo: {
            aprovada: false,
            motivos: [
              { categoria: CATEGORIA_REPROVADA, justificativa: JUSTIFICATIVA_REPROVACAO },
            ],
          },
        },
      ],
      ESQUEMA_CRITICO,
    )

    const execucaoId = await iniciarExecucao(AREA_CHUVA_ID)
    await aguardarEstado(execucaoId, ['aguardando_geracao'])

    await solicitarPreflight(execucaoId)
    await aguardarEstado(execucaoId, ['aguardando_revisao'])

    const lote = await obterLoteRevisao(execucaoId)
    expect(lote.itens).toHaveLength(1)
    const item = lote.itens[0]!
    expect(item.destinatario.nome_segurado).toBe(NOME_SEGURADO_CHUVA_ELEGIVEL)

    // Ciclo reprova→regenera visível até a 3ª tentativa: três versões registradas, todas
    // reprovadas pelo crítico com o motivo específico devolvido ao redator (REGEN-01/02/03).
    expect(item.limite_tentativas).toBe(MAXIMO_TENTATIVAS_MENSAGEM)
    expect(item.tentativa_atual).toBe(MAXIMO_TENTATIVAS_MENSAGEM)
    expect(item.versoes.map((versao) => versao.numero_tentativa)).toEqual([1, 2, 3])
    expect(item.versoes.every((versao) => versao.valida)).toBe(true)
    for (const versao of item.versoes) {
      expect(versao.avaliacao_critica?.aprovada).toBe(false)
      expect(versao.avaliacao_critica?.motivos).toEqual([
        { categoria: CATEGORIA_REPROVADA, justificativa: JUSTIFICATIVA_REPROVACAO },
      ])
    }

    // Esgotamento: terminal de conteúdo, não decidível, sem nova tentativa disponível.
    expect(item.estado).toBe('falhou_conteudo')
    expect(item.em_excecao).toBe(true)
    expect(item.decidivel).toBe(false)
    expect(item.pode_regenerar).toBe(false)
    expect(item.reprovacao_historica).toBe(true)
    expect(item.aprovada_pelo_critico).toBe(false)
    expect(lote.itens_em_excecao).toBe(1)
    expect(lote.aprovacoes_agenticas).toBe(0)

    const mensagens = await obterMensagens(execucaoId)
    expect(mensagens.registros.map((registro) => registro.estado)).toEqual(['falhou_conteudo'])

    // A `Exceção` própria do item: causa sanitizada com a categoria reprovada, impacto
    // operacional e as três tentativas consumidas (REGEN-04).
    const detalhe = await obterDetalheMensagem(execucaoId, item.mensagem_id)
    expect(detalhe.estado).toBe('falhou_conteudo')
    expect(detalhe.excecao?.causa).toContain('falhou_conteudo:')
    expect(detalhe.excecao?.causa).toContain(CATEGORIA_REPROVADA)
    expect(detalhe.excecao?.impacto).toBe(IMPACTO_ITEM_FORA_DO_LOTE)
    expect(detalhe.excecao?.tentativas).toBe(MAXIMO_TENTATIVAS_MENSAGEM)

    // Exatamente 3 gerações e 3 críticas, alternadas: nenhuma tentativa extra, nenhuma
    // chamada de crítica sem geração correspondente.
    const chamadas = await chamadasRegistradas()
    expect(chamadas.openaiChat.map((chamada) => chamada.esquema)).toEqual([
      ESQUEMA_REDATOR_WHATSAPP,
      ESQUEMA_CRITICO,
      ESQUEMA_REDATOR_WHATSAPP,
      ESQUEMA_CRITICO,
      ESQUEMA_REDATOR_WHATSAPP,
      ESQUEMA_CRITICO,
    ])

    // Reconhecimento do lote sem nenhuma decisão: nada aprovado, nada a simular.
    const decidido = await decidirLote(execucaoId, [])
    expect(decidido.estado).toBe('concluida')
    expect(decidido.mensagens_aprovadas).toEqual([])

    const resultados = await obterResultados(execucaoId)
    expect(resultados.concluido).toBe(true)
    expect(resultados.nao_simulaveis).toEqual([
      {
        mensagem_id: item.mensagem_id,
        canal: 'whatsapp',
        estado: 'falhou_conteudo',
        motivo: MOTIVO_NAO_SIMULAVEL,
      },
    ])

    const simulacao = await obterSimulacao(execucaoId)
    expect(simulacao.entregas).toEqual([])

    const comunicados = await listarComunicados(SEGURADO_CHUVA_ELEGIVEL_ID)
    expect(comunicados.comunicados).toEqual([])

    // A mensagem afetada nunca entra na simulação: o segurado elegível vê o estado vazio,
    // não um comunicado gerado a partir de conteúdo reprovado.
    await abrirPainelSegurado(page, NOME_SEGURADO_CHUVA_ELEGIVEL)
    const painelComunicados = conteudoComTexto(page, 'Nenhum comunicado no momento')
    await expect(painelComunicados).toBeVisible()
  })
})
