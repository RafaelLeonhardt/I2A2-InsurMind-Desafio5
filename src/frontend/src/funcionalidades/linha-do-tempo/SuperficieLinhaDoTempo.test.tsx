import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { LinhaDoTempo } from '../../api/linhaDoTempo'
import { SuperficieLinhaDoTempo } from './SuperficieLinhaDoTempo'

const { buscarExecucoes, getLinhaDoTempo } = vi.hoisted(() => ({
  buscarExecucoes: vi.fn(),
  getLinhaDoTempo: vi.fn(),
}))

vi.mock('../../api/linhaDoTempo', async (importarOriginal) => ({
  ...(await importarOriginal<typeof import('../../api/linhaDoTempo')>()),
  buscarExecucoes,
  getLinhaDoTempo,
}))

const EXECUCAO_ID = '11111111-1111-1111-1111-111111111111'
const MENSAGEM_A = '22222222-2222-2222-2222-222222222222'
const MENSAGEM_B = '33333333-3333-3333-3333-333333333333'

function linhaDoTempo(sobrescritas: Partial<LinhaDoTempo> = {}): LinhaDoTempo {
  return {
    execucaoId: EXECUCAO_ID,
    estado: 'concluida',
    execucaoOrigemId: null,
    retentativas: [],
    marcos: [
      {
        timestamp: '2026-09-01T08:00:00+00:00',
        ator: 'sistema',
        acao: 'coleta_concluida',
        resultado: 'concluído',
        correlacao: EXECUCAO_ID,
        tipo: 'execucao',
        mensagemId: null,
      },
      {
        timestamp: '2026-09-01T08:05:00+00:00',
        ator: 'ia',
        acao: 'geração — tentativa 1',
        resultado: 'válida',
        correlacao: MENSAGEM_A,
        tipo: 'geracao',
        mensagemId: MENSAGEM_A,
      },
      {
        timestamp: '2026-09-01T08:06:00+00:00',
        ator: 'ia',
        acao: 'crítica',
        resultado: 'aprovada',
        correlacao: MENSAGEM_A,
        tipo: 'critica',
        mensagemId: MENSAGEM_A,
      },
      {
        timestamp: '2026-09-01T08:10:00+00:00',
        ator: 'ia',
        acao: 'geração — tentativa 1',
        resultado: 'válida',
        correlacao: MENSAGEM_B,
        tipo: 'geracao',
        mensagemId: MENSAGEM_B,
      },
    ],
    ...sobrescritas,
  }
}

function renderizar() {
  return render(<SuperficieLinhaDoTempo />)
}

beforeEach(() => {
  vi.clearAllMocks()
  buscarExecucoes.mockResolvedValue([{ execucaoId: EXECUCAO_ID, estado: 'concluida' }])
  getLinhaDoTempo.mockResolvedValue(linhaDoTempo())
})

async function abrirLinhaDoTempo() {
  const usuario = userEvent.setup()
  renderizar()
  await usuario.click(
    await screen.findByRole('button', { name: new RegExp(EXECUCAO_ID) }),
  )
  return usuario
}

describe('agrupamento por mensagem (TIMELINE-02)', () => {
  it('agrupa os marcos de cada mensagem, mantendo a ordem cronológica geral entre grupos', async () => {
    await abrirLinhaDoTempo()

    const regiao = await screen.findByRole('region', { name: 'Linha do tempo' })
    const grupos = within(regiao).getAllByRole('group')
    expect(grupos).toHaveLength(2)
    expect(within(grupos[0]).getByText(new RegExp(MENSAGEM_A))).toBeInTheDocument()
    expect(within(grupos[1]).getByText(new RegExp(MENSAGEM_B))).toBeInTheDocument()

    // O marco solto "coleta_concluida" (sem mensagem) aparece antes do grupo A, e o grupo A
    // (08:05) aparece antes do grupo B (08:10) — a ordem cronológica geral é preservada.
    const textoRegiao = regiao.textContent ?? ''
    const indiceColeta = textoRegiao.indexOf('coleta_concluida')
    const indiceGrupoA = textoRegiao.indexOf(MENSAGEM_A)
    const indiceGrupoB = textoRegiao.indexOf(MENSAGEM_B)
    expect(indiceColeta).toBeLessThan(indiceGrupoA)
    expect(indiceGrupoA).toBeLessThan(indiceGrupoB)
  })

  it('mantém as duas críticas/gerações da mesma mensagem dentro do mesmo grupo', async () => {
    await abrirLinhaDoTempo()

    const regiao = await screen.findByRole('region', { name: 'Linha do tempo' })
    const grupos = within(regiao).getAllByRole('group')
    const grupoA = within(grupos[0])
    expect(grupoA.getByText('geração — tentativa 1')).toBeInTheDocument()
    expect(grupoA.getByText('crítica')).toBeInTheDocument()
  })
})

describe('horário localizado (TIMELINE-10)', () => {
  it('mostra o horário localizado mantendo o valor UTC canônico acessível em title', async () => {
    await abrirLinhaDoTempo()

    const regiao = await screen.findByRole('region', { name: 'Linha do tempo' })
    const elementoHorario = within(regiao).getAllByText((_, elemento) =>
      elemento?.tagName === 'TIME' && elemento.getAttribute('title') === '2026-09-01T08:00:00+00:00',
    )[0]

    expect(elementoHorario).toBeInTheDocument()
    expect(elementoHorario.textContent).not.toBe('2026-09-01T08:00:00+00:00')
  })
})

describe('navegação por teclado e estado expandido (TIMELINE-11)', () => {
  it('cada grupo de mensagem é um <details> nativamente acessível, expandido por padrão', async () => {
    await abrirLinhaDoTempo()

    const regiao = await screen.findByRole('region', { name: 'Linha do tempo' })
    const grupos = within(regiao).getAllByRole('group')
    for (const grupo of grupos) {
      expect(grupo.tagName).toBe('DETAILS')
      expect(grupo).toHaveAttribute('open')
    }
  })

  it('permite recolher um grupo alcançado pelo teclado e o estado expandido muda de fato', async () => {
    const usuario = await abrirLinhaDoTempo()

    const regiao = await screen.findByRole('region', { name: 'Linha do tempo' })
    const resumo = within(regiao).getAllByRole('group')[0].querySelector('summary')
    expect(resumo).not.toBeNull()

    ;(resumo as HTMLElement).focus()
    expect(resumo).toHaveFocus()
    await usuario.click(resumo as HTMLElement)

    const grupoAposFechar = within(regiao).getAllByRole('group')[0]
    expect(grupoAposFechar).not.toHaveAttribute('open')
  })

  it('a rolagem interna da linha do tempo tem nome acessível e é alcançável pelo teclado', async () => {
    await abrirLinhaDoTempo()

    const regiao = await screen.findByRole('region', { name: 'Linha do tempo' })
    expect(regiao).toHaveAttribute('tabindex', '0')
  })
})

describe('busca de execuções (TIMELINE-08/09)', () => {
  it('explica por texto quando nenhuma execução corresponde à busca', async () => {
    buscarExecucoes.mockResolvedValue([])
    renderizar()

    expect(
      await screen.findByText('Nenhuma execução corresponde à busca informada.'),
    ).toBeInTheDocument()
  })

  it('busca novamente com os filtros informados ao submeter o formulário', async () => {
    const usuario = userEvent.setup()
    renderizar()
    await screen.findByRole('button', { name: new RegExp(EXECUCAO_ID) })
    buscarExecucoes.mockClear()

    await usuario.type(screen.getByLabelText('Segurado sintético'), 'Marina')
    await usuario.selectOptions(screen.getByLabelText('Canal'), 'sms')
    await usuario.click(screen.getByRole('button', { name: 'Buscar' }))

    expect(buscarExecucoes).toHaveBeenCalledWith(
      expect.objectContaining({ segurado: 'Marina', canal: 'sms' }),
    )
  })
})
