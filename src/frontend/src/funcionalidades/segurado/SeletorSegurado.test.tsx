import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { SeguradoProvider } from '../../contexto/SeguradoContexto'
import { SeletorSegurado } from './SeletorSegurado'

const { getListaSeguradosMock } = vi.hoisted(() => ({ getListaSeguradosMock: vi.fn() }))

vi.mock('../../api/listaSegurados', async (importarOriginal) => {
  const original = await importarOriginal<typeof import('../../api/listaSegurados')>()
  return { ...original, getListaSegurados: getListaSeguradosMock }
})

const SEGURADO_A = { id: '11111111-1111-1111-1111-111111111111', nome: 'Pessoa Sintética DEMO-001' }
const SEGURADO_B = { id: '22222222-2222-2222-2222-222222222222', nome: 'Pessoa Sintética DEMO-002' }

function renderizar() {
  return render(
    <SeguradoProvider>
      <SeletorSegurado />
    </SeguradoProvider>,
  )
}

beforeEach(() => {
  window.localStorage.clear()
  getListaSeguradosMock.mockReset()
})

afterEach(() => {
  window.localStorage.clear()
})

describe('SeletorSegurado', () => {
  it('rótulo "Visualizar como" e nenhum texto renderizado sugere login/senha/entrar', async () => {
    getListaSeguradosMock.mockResolvedValue([SEGURADO_A, SEGURADO_B])
    const { container } = renderizar()

    const campo = await screen.findByRole('combobox', { name: 'Visualizar como' })
    expect(campo).toBeInTheDocument()

    const textoRenderizado = container.textContent ?? ''
    expect(textoRenderizado).not.toMatch(/login|senha|entrar/i)
  })

  it('lista somente os segurados sintéticos disponíveis, com a opção ativa selecionada', async () => {
    getListaSeguradosMock.mockResolvedValue([SEGURADO_A, SEGURADO_B])
    renderizar()

    const campo = await screen.findByRole<HTMLSelectElement>('combobox', {
      name: 'Visualizar como',
    })
    expect(screen.getAllByRole('option').map((opcao) => opcao.textContent)).toEqual([
      SEGURADO_A.nome,
      SEGURADO_B.nome,
    ])
    expect(campo.value).toBe(SEGURADO_A.id)
  })

  it('é alcançável por teclado (Tab) e opera por teclado, anunciando a mudança', async () => {
    getListaSeguradosMock.mockResolvedValue([SEGURADO_A, SEGURADO_B])
    const usuario = userEvent.setup()
    renderizar()
    const campo = await screen.findByRole<HTMLSelectElement>('combobox', {
      name: 'Visualizar como',
    })

    await usuario.tab()
    expect(campo).toHaveFocus()

    await usuario.selectOptions(campo, SEGURADO_B.id)

    expect(campo.value).toBe(SEGURADO_B.id)
    await waitFor(() =>
      expect(screen.getByText(`Visualizando como ${SEGURADO_B.nome}`)).toBeInTheDocument(),
    )
  })

  it('cancelar com Escape sem confirmar mantém o segurado ativo inalterado', async () => {
    getListaSeguradosMock.mockResolvedValue([SEGURADO_A, SEGURADO_B])
    const usuario = userEvent.setup()
    renderizar()
    const campo = await screen.findByRole<HTMLSelectElement>('combobox', {
      name: 'Visualizar como',
    })

    await usuario.click(campo)
    await usuario.keyboard('{Escape}')

    expect(campo.value).toBe(SEGURADO_A.id)
  })

  it('carrega a classe do alvo mínimo de 44×44 px no campo', async () => {
    getListaSeguradosMock.mockResolvedValue([SEGURADO_A, SEGURADO_B])
    renderizar()

    const campo = await screen.findByRole('combobox', { name: 'Visualizar como' })

    // A classe `seletor-segurado-campo` define min-width/min-height de 44px em
    // SeletorSegurado.css. jsdom não layouta a página, então esta verificação confirma a
    // presença da classe que codifica o alvo mínimo, não um pixel medido (mesmo padrão de
    // SuperficieProntidao.test.tsx).
    expect(campo).toHaveClass('seletor-segurado-campo')
  })

  it('desabilita com motivo textual quando não há nenhum segurado sintético disponível', async () => {
    getListaSeguradosMock.mockResolvedValue([])
    renderizar()

    const campo = await screen.findByRole<HTMLSelectElement>('combobox', {
      name: 'Visualizar como',
    })
    expect(campo).toBeDisabled()
    expect(
      screen.getByText(
        'Nenhum segurado sintético disponível: restaure os dados sintéticos e tente novamente.',
      ),
    ).toBeInTheDocument()
  })

  it('desabilita com motivo textual enquanto o contexto está trocando', async () => {
    getListaSeguradosMock.mockResolvedValueOnce([SEGURADO_A, SEGURADO_B])
    const usuario = userEvent.setup()
    renderizar()
    const campo = await screen.findByRole<HTMLSelectElement>('combobox', {
      name: 'Visualizar como',
    })

    let resolverTroca: (valor: (typeof SEGURADO_A)[]) => void = () => {}
    getListaSeguradosMock.mockReturnValueOnce(
      new Promise((resolver) => {
        resolverTroca = resolver
      }),
    )

    await usuario.selectOptions(campo, SEGURADO_B.id)

    expect(campo).toBeDisabled()
    expect(
      screen.getByText('Contexto trocando: aguarde a troca em andamento terminar.'),
    ).toBeInTheDocument()

    resolverTroca([SEGURADO_A, SEGURADO_B])
    await waitFor(() => expect(campo).not.toBeDisabled())
  })
})
