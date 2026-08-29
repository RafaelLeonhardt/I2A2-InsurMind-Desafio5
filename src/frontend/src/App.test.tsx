import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useEffect } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App, { SuperficieAtiva } from './App'
import { CHAVE_ARMAZENAMENTO_PERFIL, PerfilProvider, usePerfilContexto } from './contexto/PerfilContexto'

const { getSeguradoPadraoMock, restaurarDadosSinteticosMock } = vi.hoisted(() => ({
  getSeguradoPadraoMock: vi.fn(),
  restaurarDadosSinteticosMock: vi.fn(),
}))

vi.mock('./api/contexto', async () => {
  const real = await vi.importActual<typeof import('./api/contexto')>('./api/contexto')
  return {
    ...real,
    getSeguradoPadrao: getSeguradoPadraoMock,
  }
})

vi.mock('./api/dadosSinteticos', async () => {
  const real = await vi.importActual<typeof import('./api/dadosSinteticos')>('./api/dadosSinteticos')
  return {
    ...real,
    restaurarDadosSinteticos: restaurarDadosSinteticosMock,
  }
})

function definirLargura(largura: number) {
  Object.defineProperty(window, 'innerWidth', { configurable: true, value: largura })
}

beforeEach(() => {
  getSeguradoPadraoMock.mockResolvedValue({
    id: '11111111-1111-4111-8111-111111111111',
    nome: 'Pessoa Segurada Sintética DEMO-001',
  })
  window.localStorage.clear()
})

afterEach(() => {
  cleanup()
  window.localStorage.clear()
  vi.clearAllMocks()
  definirLargura(1024)
})

describe('shell do contexto demonstrativo', () => {
  it('mantém os avisos persistentes da demonstração em qualquer perfil', () => {
    definirLargura(1440)
    const { container } = render(<App />)

    expect(container.textContent).toContain('Ambiente educacional')
    expect(screen.getAllByText('Dados sintéticos').length).toBeGreaterThan(0)
    expect(screen.getByText(/Sem envio real/)).toBeInTheDocument()
  })

  it('abre no perfil Administrador, com Prontidão e Restaurar dados sintéticos na navegação', () => {
    definirLargura(1440)
    render(<App />)

    expect(screen.getByRole('button', { name: 'Prontidão' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Restaurar dados sintéticos' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Visão geral' })).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Prontidão das dependências' })).toBeInTheDocument()
  })

  it('Administrador → Segurado: navegação mostra somente Visão geral', async () => {
    definirLargura(1440)
    const usuario = userEvent.setup()
    render(<App />)

    await usuario.click(screen.getByRole('button', { name: /Visualizar como Segurado/ }))

    expect(await screen.findByRole('button', { name: 'Visão geral' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Prontidão' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Restaurar dados sintéticos' })).not.toBeInTheDocument()
    expect(
      screen.getByRole('heading', { name: 'Chuva intensa e rajadas de vento' }),
    ).toBeInTheDocument()
  })

  it('Segurado → Administrador: navegação mostra Prontidão e Restaurar dados sintéticos', async () => {
    definirLargura(1440)
    window.localStorage.setItem(CHAVE_ARMAZENAMENTO_PERFIL, 'segurado')
    const usuario = userEvent.setup()
    render(<App />)

    await usuario.click(screen.getByRole('button', { name: /Visualizar como Administrador/ }))

    expect(await screen.findByRole('button', { name: 'Prontidão' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Restaurar dados sintéticos' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Visão geral' })).not.toBeInTheDocument()
  })

  it('nunca descreve a troca de perfil como login, autenticação, autorização ou elevação de privilégio', async () => {
    definirLargura(1440)
    const usuario = userEvent.setup()
    const { container } = render(<App />)

    await usuario.click(screen.getByRole('button', { name: /Visualizar como Segurado/ }))
    await screen.findByRole('button', { name: 'Visão geral' })

    const texto = container.textContent ?? ''
    for (const termo of ['login', 'Login', 'autenticaç', 'Autenticaç', 'autorizaç', 'Autorizaç', 'privilégio']) {
      expect(texto).not.toContain(termo)
    }
  })

  it('fecha o modal de restauração aberto ao trocar de perfil, sem chamar nenhuma mutação', async () => {
    definirLargura(1440)
    const usuario = userEvent.setup()
    render(<App />)

    await usuario.click(screen.getByRole('button', { name: 'Restaurar dados sintéticos' }))
    await usuario.click(screen.getByRole('button', { name: 'Restaurar demonstração' }))
    expect(screen.getByRole('dialog')).toBeInTheDocument()

    await usuario.click(screen.getByRole('button', { name: /Visualizar como Segurado/ }))

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(restaurarDadosSinteticosMock).not.toHaveBeenCalled()
  })

  it('persiste o perfil em localStorage e restaura no reload, com "administrador" como padrão', async () => {
    definirLargura(1440)
    const usuario = userEvent.setup()
    const primeira = render(<App />)

    await usuario.click(screen.getByRole('button', { name: /Visualizar como Segurado/ }))
    await screen.findByRole('button', { name: 'Visão geral' })
    expect(window.localStorage.getItem(CHAVE_ARMAZENAMENTO_PERFIL)).toBe('segurado')
    primeira.unmount()

    render(<App />)
    expect(await screen.findByRole('button', { name: 'Visão geral' })).toBeInTheDocument()
  })

  it('trata um valor corrompido em localStorage como ausência de preferência (padrão Administrador)', () => {
    window.localStorage.setItem(CHAVE_ARMAZENAMENTO_PERFIL, 'super-usuario')
    definirLargura(1440)
    render(<App />)

    expect(screen.getByRole('button', { name: 'Prontidão' })).toBeInTheDocument()
    expect(screen.getByText('Administrador')).toBeInTheDocument()
  })

  it('bloqueia contexto inconsistente e oferece o retorno à Visão geral do perfil ativo', async () => {
    // Nenhum fluxo de UI alcança uma superficieAtiva fora da lista do perfil ativo - a
    // NavegacaoLateral só oferece opções válidas (ver design.md). Este teste força a
    // combinação inconsistente diretamente pelo contexto para verificar a salvaguarda.
    function ForcarSuperficieInvalida() {
      const { selecionarSuperficie } = usePerfilContexto()
      useEffect(() => {
        selecionarSuperficie('visao-geral')
        // eslint-disable-next-line react-hooks/exhaustive-deps
      }, [])
      return null
    }

    definirLargura(1440)
    const usuario = userEvent.setup()
    render(
      <PerfilProvider>
        <ForcarSuperficieInvalida />
        <SuperficieAtiva />
      </PerfilProvider>,
    )

    expect(
      screen.getByRole('heading', { name: /não está disponível para o perfil Administrador/ }),
    ).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Restaurar demonstração' })).not.toBeInTheDocument()
    expect(screen.queryByText('Pessoa Segurada Sintética DEMO-001')).not.toBeInTheDocument()

    await usuario.click(screen.getByRole('button', { name: 'Voltar para a Visão geral' }))

    expect(screen.getByRole('heading', { name: 'Prontidão das dependências' })).toBeInTheDocument()
  })

  it('mantém navegação e seletor operáveis entre 1024 px e uma largura ampla', () => {
    for (const largura of [1024, 1279, 1920]) {
      cleanup()
      definirLargura(largura)
      render(<App />)

      expect(screen.queryByRole('note')).not.toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Prontidão' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /Visualizar como Segurado/ })).toBeInTheDocument()
    }
  })

  it('exibe o aviso de resolução não suportada abaixo de 1024 px, sem perder funções', () => {
    definirLargura(1024)
    render(<App />)
    expect(screen.queryByRole('note')).not.toBeInTheDocument()

    definirLargura(1023)
    fireEvent(window, new Event('resize'))

    expect(screen.getByRole('note')).toHaveTextContent('Todas as funções permanecem disponíveis')
    expect(screen.getByRole('button', { name: 'Prontidão' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Visualizar como Segurado/ })).toBeInTheDocument()
  })

  it('permite navegação e alternância só por teclado, com foco visível e anúncio aria-live', async () => {
    definirLargura(1440)
    const usuario = userEvent.setup()
    render(<App />)

    await usuario.tab()
    await usuario.tab()
    expect(screen.getByRole('button', { name: 'Prontidão' })).toHaveFocus()

    await usuario.keyboard('{Enter}')
    expect(screen.getByRole('button', { name: 'Prontidão' })).toHaveAttribute('aria-current', 'page')

    const seletor = screen.getByRole('button', { name: /Visualizar como Segurado/ })
    seletor.focus()
    expect(seletor).toHaveFocus()

    await usuario.keyboard('{Enter}')

    expect(await screen.findByRole('button', { name: 'Visão geral' })).toBeInTheDocument()
    await waitFor(() => {
      expect(
        screen.getByText('Visualizando como Segurado').closest('[aria-live="polite"]'),
      ).not.toBeNull()
    })
  })
})
