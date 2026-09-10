import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  ErroRevisaoLote,
  type ItemLote,
  type LoteRevisao,
  type VersaoRevisada,
} from '../../api/revisaoLote'
import { SuperficieRevisaoLote } from './SuperficieRevisaoLote'

const { getLoteRevisao, decidirLote } = vi.hoisted(() => ({
  getLoteRevisao: vi.fn(),
  decidirLote: vi.fn(),
}))

const { getAvaliacaoCritica } = vi.hoisted(() => ({
  getAvaliacaoCritica: vi.fn(),
}))

vi.mock('../../api/revisaoLote', async (importarOriginal) => ({
  ...(await importarOriginal<typeof import('../../api/revisaoLote')>()),
  getLoteRevisao,
  decidirLote,
}))

vi.mock('../../api/avaliacaoCritica', async (importarOriginal) => ({
  ...(await importarOriginal<typeof import('../../api/avaliacaoCritica')>()),
  getAvaliacaoCritica,
}))

const EXECUCAO_ID = '11111111-1111-1111-1111-111111111111'
const CORPO_GERADO = 'Chuva forte hoje na sua região. Evite áreas alagadas.'

function versao(sobrescritas: Partial<VersaoRevisada> = {}): VersaoRevisada {
  return {
    id: '22222222-2222-2222-2222-222222222222',
    numeroTentativa: 1,
    assunto: null,
    corpo: CORPO_GERADO,
    valida: true,
    motivoInvalidez: null,
    modelo: 'gpt-4o-mini',
    versaoPrompt: 'v1',
    duracaoMs: 742.5,
    criadoEm: '2026-09-04T19:00:00Z',
    avaliacaoCritica: {
      aprovada: true,
      motivos: [],
      agente: 'critico',
      modelo: 'gpt-4o-mini',
      duracaoMs: 90,
    },
    ...sobrescritas,
  }
}

function item(sobrescritas: Partial<ItemLote> = {}): ItemLote {
  return {
    mensagemId: '33333333-3333-3333-3333-333333333333',
    canal: 'sms',
    estado: 'aguardando_revisao',
    tentativaAtual: 1,
    limiteTentativas: 3,
    versao: 2,
    destinatario: {
      elegibilidadeId: '44444444-4444-4444-4444-444444444444',
      seguradoId: '55555555-5555-5555-5555-555555555555',
      nomeSegurado: 'Marina Teste',
      apoliceId: '66666666-6666-6666-6666-666666666666',
      codigoIbgeArea: '9990001',
      canal: 'sms',
    },
    origem: {
      eventoId: '77777777-7777-7777-7777-777777777777',
      regraId: '88888888-8888-8888-8888-888888888888',
      regraVersao: 2,
      justificativa: 'Atende integralmente aos critérios da regra ativa.',
      criterios: [
        {
          operando: 'área afetada',
          valorObservado: '9990001',
          atende: true,
          justificativa: 'Área corresponde.',
        },
      ],
    },
    proveniencia: {
      categoriasUsadas: ['evento', 'canal'],
      categoriasNaoUsadas: ['documentos', 'dados_financeiros'],
    },
    versoes: [versao()],
    decisoes: [],
    aprovadaPeloCritico: true,
    reprovacaoHistorica: false,
    emExcecao: false,
    decidivel: true,
    podeRegenerar: true,
    ...sobrescritas,
  }
}

function lote(itens: ItemLote[]): LoteRevisao {
  return {
    execucaoId: EXECUCAO_ID,
    estado: 'aguardando_revisao',
    evento: {
      id: '77777777-7777-7777-7777-777777777777',
      tipo: 'chuva_intensa',
      area: '9990001',
      intensidade: 62.5,
      proveniencia: 'real_inmet',
      periodoInicio: '2026-09-04T12:00:00Z',
      periodoFim: '2026-09-04T18:00:00Z',
    },
    regraId: '88888888-8888-8888-8888-888888888888',
    regraVersao: 2,
    totalPublicoIncluido: itens.length,
    distribuicaoPorCanal: [{ canal: 'sms', total: itens.length }],
    aprovacoesAgenticas: itens.filter((candidato) => candidato.aprovadaPeloCritico).length,
    itensEmExcecao: itens.filter((candidato) => candidato.emExcecao).length,
    itens,
  }
}

function avaliacaoCritica(sobrescritas: Partial<Record<string, unknown>> = {}) {
  return {
    mensagemId: item().mensagemId,
    versaoMensagemId: 'versao-2',
    numeroTentativa: 2,
    origem: 'decisao_humana',
    criterios: ['tom', 'utilidade', 'clareza', 'seguranca', 'promessa_indevida', 'distincao_oficial', 'adequacao_canal'],
    aprovada: true,
    motivos: [],
    agente: 'critico',
    modelo: 'gpt-4o-mini',
    duracaoMs: 90,
    criadoEm: '2026-09-04T19:00:00Z',
    validacaoDeterministica: {
      origem: 'regras_deterministicas',
      valida: true,
      motivoInvalidez: null,
    },
    ...sobrescritas,
  }
}

function renderizar() {
  return render(<SuperficieRevisaoLote execucaoId={EXECUCAO_ID} />)
}

async function abrirRevisorDe(nome: string) {
  await userEvent.click(
    await screen.findByRole('button', { name: `Abrir revisor de ${nome}` }),
  )
}

describe('SuperficieRevisaoLote', () => {
  beforeEach(() => {
    getLoteRevisao.mockReset()
    decidirLote.mockReset()
    getAvaliacaoCritica.mockReset()
    getAvaliacaoCritica.mockResolvedValue(avaliacaoCritica())
    decidirLote.mockResolvedValue({
      execucaoId: EXECUCAO_ID,
      estado: 'aguardando_confirmacao',
      aplicadas: [],
      recusadas: [],
      mensagensAprovadas: [],
      regeneracoesAtivas: [],
    })
  })

  it('lista os itens na ordem recebida, com o sinal de atenção de cada um', async () => {
    getLoteRevisao.mockResolvedValue(
      lote([
        item({
          mensagemId: 'excecao',
          estado: 'falhou_conteudo',
          emExcecao: true,
          decidivel: false,
          podeRegenerar: false,
          aprovadaPeloCritico: false,
          destinatario: { ...item().destinatario, nomeSegurado: 'Com exceção' },
        }),
        item({
          mensagemId: 'historica',
          reprovacaoHistorica: true,
          destinatario: { ...item().destinatario, nomeSegurado: 'Com histórico' },
        }),
        item({
          mensagemId: 'limpa',
          destinatario: { ...item().destinatario, nomeSegurado: 'Sem ressalvas' },
        }),
      ]),
    )

    renderizar()

    const itens = await screen.findAllByRole('listitem')
    const sinais = document.querySelectorAll('[data-sinal]')
    expect([...sinais].map((sinal) => sinal.getAttribute('data-sinal'))).toEqual([
      'excecao',
      'reprovacao-historica',
      'aprovacao-limpa',
    ])
    expect(itens[0]).toHaveTextContent('Com exceção')
    expect(within(itens[0] as HTMLElement).getByText(/Exige atenção: exceção/)).toBeVisible()
    expect(
      within(itens[1] as HTMLElement).getByText(/reprovada em tentativa anterior/),
    ).toBeVisible()
  })

  it('separa destinatário, conteúdo/versionamento e contexto de IA em seções próprias', async () => {
    getLoteRevisao.mockResolvedValue(lote([item()]))

    renderizar()
    await abrirRevisorDe('Marina Teste')

    const destinatario = document.querySelector('[data-secao="destinatario"]')
    const conteudo = document.querySelector('[data-secao="conteudo-versionamento"]')
    const contextoIa = document.querySelector('[data-secao="contexto-ia"]')
    expect(destinatario).not.toBeNull()
    expect(conteudo).not.toBeNull()
    expect(contextoIa).not.toBeNull()
    expect(destinatario).toHaveTextContent('Marina Teste')
    expect(destinatario).toHaveTextContent('9990001')
    expect(destinatario).not.toHaveTextContent(CORPO_GERADO)
    expect(conteudo).toHaveTextContent(CORPO_GERADO)
    expect(conteudo).toHaveTextContent('Verificação determinística: aprovada')
    expect(conteudo).not.toHaveTextContent('gpt-4o-mini')
    expect(contextoIa).toHaveTextContent('aprovada pelo agente crítico')
    expect(contextoIa).toHaveTextContent('gpt-4o-mini')
    expect(contextoIa).toHaveTextContent('Dados usados pelo agente: evento, canal')
    expect(contextoIa).toHaveTextContent('Deixados de fora: documentos, dados_financeiros')
  })

  it('mostra as duas versões de uma mensagem regenerada, com o veredito de cada uma', async () => {
    getLoteRevisao.mockResolvedValue(
      lote([
        item({
          tentativaAtual: 2,
          reprovacaoHistorica: true,
          versoes: [
            versao({
              id: 'versao-1',
              corpo: 'Primeira formulação.',
              avaliacaoCritica: {
                aprovada: false,
                motivos: [{ categoria: 'tom', justificativa: 'Tom alarmista.' }],
                agente: 'critico',
                modelo: 'gpt-4o-mini',
                duracaoMs: 90,
              },
            }),
            versao({ id: 'versao-2', numeroTentativa: 2, corpo: 'Segunda formulação.' }),
          ],
        }),
      ]),
    )

    renderizar()
    await abrirRevisorDe('Marina Teste')

    const conteudo = document.querySelector('[data-secao="conteudo-versionamento"]')
    expect(conteudo).toHaveTextContent('Primeira formulação.')
    expect(conteudo).toHaveTextContent('Segunda formulação.')
    expect(conteudo).toHaveTextContent('Tentativa 2 de 3')
    const contextoIa = document.querySelector('[data-secao="contexto-ia"]')
    expect(contextoIa).toHaveTextContent('reprovada pelo agente crítico (tom)')
    expect(contextoIa).toHaveTextContent('2ª tentativa: aprovada pelo agente crítico')
  })

  it('não oferece nenhum campo de edição do texto da mensagem', async () => {
    getLoteRevisao.mockResolvedValue(lote([item()]))

    renderizar()
    await abrirRevisorDe('Marina Teste')

    const editaveis = [
      ...document.querySelectorAll('textarea'),
      ...document.querySelectorAll('input'),
      ...document.querySelectorAll('[contenteditable="true"]'),
    ]
    for (const campo of editaveis) {
      expect((campo as HTMLInputElement | HTMLTextAreaElement).value ?? '').not.toContain(
        CORPO_GERADO,
      )
    }
    const textareas = document.querySelectorAll('textarea')
    expect(textareas).toHaveLength(1)
    expect(textareas[0]).toHaveAttribute('id', 'justificativa-decisao')
    expect(screen.getByText(CORPO_GERADO).tagName).toBe('P')
  })

  it.each(['Rejeitar', 'Excluir do lote', 'Solicitar nova geração'])(
    'bloqueia %s sem justificativa com erro inline e sem chamar a API',
    async (rotulo) => {
      getLoteRevisao.mockResolvedValue(lote([item()]))

      renderizar()
      await abrirRevisorDe('Marina Teste')
      await userEvent.click(screen.getByRole('radio', { name: rotulo }))
      await userEvent.click(
        screen.getByRole('button', { name: /Confirmar decisão/ }),
      )

      const erro = await screen.findByRole('alert')
      expect(erro).toHaveTextContent('Escreva a justificativa antes de confirmar esta decisão.')
      expect(screen.getByLabelText(/Justificativa da decisão/)).toHaveAttribute(
        'aria-invalid',
        'true',
      )
      expect(decidirLote).not.toHaveBeenCalled()
    },
  )

  it('aceita aprovar sem justificativa e envia a decisão com a versão esperada', async () => {
    getLoteRevisao.mockResolvedValue(lote([item()]))

    renderizar()
    await abrirRevisorDe('Marina Teste')
    await userEvent.click(screen.getByRole('button', { name: /Confirmar decisão/ }))

    await waitFor(() => expect(decidirLote).toHaveBeenCalledTimes(1))
    expect(decidirLote).toHaveBeenCalledWith(EXECUCAO_ID, [
      {
        mensagemId: '33333333-3333-3333-3333-333333333333',
        versaoEsperada: 2,
        resultado: 'aprovar',
        justificativa: null,
      },
    ])
  })

  it('envia a decisão com a justificativa preenchida e recarrega o lote', async () => {
    getLoteRevisao.mockResolvedValue(lote([item()]))

    renderizar()
    await abrirRevisorDe('Marina Teste')
    await userEvent.click(screen.getByRole('radio', { name: 'Rejeitar' }))
    await userEvent.type(
      screen.getByLabelText(/Justificativa da decisão/),
      'Não distingue do alerta oficial.',
    )
    await userEvent.click(screen.getByRole('button', { name: /Confirmar decisão/ }))

    await waitFor(() => expect(decidirLote).toHaveBeenCalledTimes(1))
    expect(decidirLote).toHaveBeenCalledWith(EXECUCAO_ID, [
      {
        mensagemId: '33333333-3333-3333-3333-333333333333',
        versaoEsperada: 2,
        resultado: 'rejeitar',
        justificativa: 'Não distingue do alerta oficial.',
      },
    ])
    expect(getLoteRevisao).toHaveBeenCalledTimes(2)
  })

  it('preserva o rascunho da justificativa ao navegar entre itens sem confirmar', async () => {
    getLoteRevisao.mockResolvedValue(
      lote([
        item({ mensagemId: 'primeira' }),
        item({
          mensagemId: 'segunda',
          destinatario: { ...item().destinatario, nomeSegurado: 'Outra Pessoa' },
        }),
      ]),
    )

    renderizar()
    await abrirRevisorDe('Marina Teste')
    await userEvent.type(
      screen.getByLabelText(/Justificativa da decisão/),
      'Rascunho em andamento',
    )
    await abrirRevisorDe('Outra Pessoa')
    expect(screen.getByLabelText(/Justificativa da decisão/)).toHaveValue('')
    await abrirRevisorDe('Marina Teste')

    expect(screen.getByLabelText(/Justificativa da decisão/)).toHaveValue(
      'Rascunho em andamento',
    )
    expect(decidirLote).not.toHaveBeenCalled()
  })

  it('descarta o rascunho apenas quando o descarte é pedido conscientemente', async () => {
    getLoteRevisao.mockResolvedValue(lote([item()]))

    renderizar()
    await abrirRevisorDe('Marina Teste')
    await userEvent.type(screen.getByLabelText(/Justificativa da decisão/), 'Rascunho')
    await userEvent.click(screen.getByRole('button', { name: 'Descartar justificativa' }))

    expect(screen.getByLabelText(/Justificativa da decisão/)).toHaveValue('')
  })

  it('deixa a regeneração indisponível com explicação acessível no limite de tentativas', async () => {
    getLoteRevisao.mockResolvedValue(
      lote([item({ tentativaAtual: 3, podeRegenerar: false })]),
    )

    renderizar()
    await abrirRevisorDe('Marina Teste')

    const regenerar = screen.getByRole('radio', { name: 'Solicitar nova geração' })
    expect(regenerar).toBeDisabled()
    const explicacao = document.getElementById(
      regenerar.getAttribute('aria-describedby') ?? '',
    )
    expect(explicacao).toHaveTextContent(
      'Esta mensagem já usou as 3 tentativas de geração permitidas.',
    )
    expect(explicacao).toHaveTextContent(
      'Aprovar, rejeitar e excluir do lote continuam disponíveis.',
    )
    expect(screen.getByRole('radio', { name: 'Aprovar' })).toBeEnabled()
    expect(screen.getByRole('radio', { name: 'Rejeitar' })).toBeEnabled()
    expect(screen.getByRole('radio', { name: 'Excluir do lote' })).toBeEnabled()
  })

  it('decide em lote as mensagens selecionadas junto com a aberta', async () => {
    getLoteRevisao.mockResolvedValue(
      lote([
        item({ mensagemId: 'primeira', versao: 2 }),
        item({
          mensagemId: 'segunda',
          versao: 5,
          destinatario: { ...item().destinatario, nomeSegurado: 'Outra Pessoa' },
        }),
      ]),
    )

    renderizar()
    await abrirRevisorDe('Marina Teste')
    const selecoes = await screen.findAllByRole('checkbox', {
      name: 'Incluir na decisão em lote',
    })
    await userEvent.click(selecoes[1])
    await userEvent.click(screen.getByRole('button', { name: 'Confirmar decisão (2 mensagens)' }))

    await waitFor(() => expect(decidirLote).toHaveBeenCalledTimes(1))
    expect(decidirLote).toHaveBeenCalledWith(EXECUCAO_ID, [
      {
        mensagemId: 'primeira',
        versaoEsperada: 2,
        resultado: 'aprovar',
        justificativa: null,
      },
      { mensagemId: 'segunda', versaoEsperada: 5, resultado: 'aprovar', justificativa: null },
    ])
  })

  it('não oferece decisão para item que não aguarda revisão', async () => {
    getLoteRevisao.mockResolvedValue(
      lote([
        item({
          estado: 'falhou_conteudo',
          emExcecao: true,
          decidivel: false,
          podeRegenerar: false,
        }),
      ]),
    )

    renderizar()
    await abrirRevisorDe('Marina Teste')

    expect(screen.queryByRole('radio', { name: 'Aprovar' })).toBeNull()
    expect(
      screen.getByText(/Exceção: conteúdo não aprovado em três tentativas/, {
        selector: '.revisao-lote__sem-decisao',
      }),
    ).toBeVisible()
  })

  it('explica a falha com ocorrência, impacto e próxima ação', async () => {
    getLoteRevisao.mockRejectedValue(
      new ErroRevisaoLote({
        codigo: 'execucao_inexistente',
        correlacaoId: null,
        ocorrencia: "A execução '11111111' não existe.",
        impacto: 'Nenhum lote de revisão pode ser exibido.',
        proximaAcao: 'Consulte a execução pelo identificador UUID retornado pela API.',
        status: 404,
      }),
    )

    renderizar()

    const alerta = await screen.findByRole('alert')
    expect(alerta).toHaveTextContent("A execução '11111111' não existe.")
    expect(alerta).toHaveTextContent('Nenhum lote de revisão pode ser exibido.')
    expect(alerta).toHaveTextContent(
      'Consulte a execução pelo identificador UUID retornado pela API.',
    )
  })

  it('abre a avaliação crítica completa de uma tentativa e fecha ao clicar novamente', async () => {
    getLoteRevisao.mockResolvedValue(lote([item()]))
    renderizar()
    await abrirRevisorDe('Marina Teste')

    expect(screen.queryByText('Critérios avaliados')).not.toBeInTheDocument()

    await userEvent.click(
      await screen.findByRole('button', { name: 'Ver avaliação crítica completa' }),
    )

    await waitFor(() => expect(getAvaliacaoCritica).toHaveBeenCalledWith(item().mensagemId, versao().id))
    expect(
      await screen.findByRole('button', { name: 'Fechar avaliação crítica' }),
    ).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Fechar avaliação crítica' }))
    expect(
      screen.queryByRole('button', { name: 'Fechar avaliação crítica' }),
    ).not.toBeInTheDocument()
  })

  it('mostra tentativas e origem final (agente/humana) ao abrir a avaliação de uma mensagem regenerada', async () => {
    getLoteRevisao.mockResolvedValue(
      lote([
        item({
          tentativaAtual: 2,
          reprovacaoHistorica: true,
          versoes: [
            versao({ id: 'versao-1', numeroTentativa: 1, corpo: 'Primeira formulação.' }),
            versao({ id: 'versao-2', numeroTentativa: 2, corpo: 'Segunda formulação.' }),
          ],
        }),
      ]),
    )
    getAvaliacaoCritica.mockResolvedValue(
      avaliacaoCritica({ numeroTentativa: 2, origem: 'decisao_humana' }),
    )
    renderizar()
    await abrirRevisorDe('Marina Teste')

    const [, botaoSegundaTentativa] = await screen.findAllByRole('button', {
      name: 'Ver avaliação crítica completa',
    })
    await userEvent.click(botaoSegundaTentativa)

    await waitFor(() =>
      expect(getAvaliacaoCritica).toHaveBeenCalledWith(item().mensagemId, 'versao-2'),
    )
    const detalheAvaliacao = await screen.findByRole('heading', { name: 'Avaliação da mensagem' })
    const secaoAvaliacao = detalheAvaliacao.closest('section') as HTMLElement
    expect(within(secaoAvaliacao).getByText('2ª tentativa')).toBeInTheDocument()
    expect(secaoAvaliacao.querySelector('[data-origem="decisao_humana"]')).not.toBeNull()
  })

  it('abrir a avaliação crítica de outra tentativa fecha a anterior (só uma aberta por vez)', async () => {
    getLoteRevisao.mockResolvedValue(
      lote([
        item({
          tentativaAtual: 2,
          versoes: [
            versao({ id: 'versao-1', numeroTentativa: 1 }),
            versao({ id: 'versao-2', numeroTentativa: 2 }),
          ],
        }),
      ]),
    )
    renderizar()
    await abrirRevisorDe('Marina Teste')

    const [primeiraAba, segundaAba] = await screen.findAllByRole('button', {
      name: 'Ver avaliação crítica completa',
    })
    await userEvent.click(primeiraAba)
    await screen.findByRole('button', { name: 'Fechar avaliação crítica' })

    await userEvent.click(segundaAba)
    expect(await screen.findAllByRole('button', { name: 'Fechar avaliação crítica' })).toHaveLength(1)
    expect(
      screen.getAllByRole('button', { name: 'Ver avaliação crítica completa' }),
    ).toHaveLength(1)
  })

  it('trocar de item do lote fecha qualquer avaliação crítica aberta', async () => {
    getLoteRevisao.mockResolvedValue(
      lote([
        item({ mensagemId: 'item-a', destinatario: { ...item().destinatario, nomeSegurado: 'Item A' } }),
        item({ mensagemId: 'item-b', destinatario: { ...item().destinatario, nomeSegurado: 'Item B' } }),
      ]),
    )
    renderizar()
    await abrirRevisorDe('Item A')
    await userEvent.click(
      await screen.findByRole('button', { name: 'Ver avaliação crítica completa' }),
    )
    await screen.findByRole('button', { name: 'Fechar avaliação crítica' })

    await abrirRevisorDe('Item B')
    expect(
      screen.queryByRole('button', { name: 'Fechar avaliação crítica' }),
    ).not.toBeInTheDocument()
  })
})
