import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ErroContexto } from '../api/contexto'
import { CHAVE_ARMAZENAMENTO_PERFIL, PerfilProvider } from '../contexto/PerfilContexto'
import { BarraContexto } from './BarraContexto'

const { getSeguradoPadraoMock } = vi.hoisted(() => ({
  getSeguradoPadraoMock: vi.fn(),
}))

vi.mock('../api/contexto', async () => {
  const real = await vi.importActual<typeof import('../api/contexto')>('../api/contexto')
  return {
    ...real,
    getSeguradoPadrao: getSeguradoPadraoMock,
  }
})

function renderizarComPerfil(perfil: 'administrador' | 'segurado') {
  window.localStorage.setItem(CHAVE_ARMAZENAMENTO_PERFIL, perfil)
  return render(
    <PerfilProvider>
      <BarraContexto />
    </PerfilProvider>,
  )
}

afterEach(() => {
  window.localStorage.clear()
  vi.clearAllMocks()
})

describe('BarraContexto', () => {
  it('mostra o perfil Administrador e a data/hora de referência', () => {
    renderizarComPerfil('administrador')

    expect(screen.getByText('Administrador')).toBeInTheDocument()
    expect(screen.getByText('Data e hora de referência')).toBeInTheDocument()
  })

  it('busca e mostra o nome do segurado padrão no perfil Segurado', async () => {
    getSeguradoPadraoMock.mockResolvedValue({
      id: '11111111-1111-4111-8111-111111111111',
      nome: 'Pessoa Segurada Sintética DEMO-001',
    })

    renderizarComPerfil('segurado')

    expect(await screen.findByText('Pessoa Segurada Sintética DEMO-001')).toBeInTheDocument()
    expect(getSeguradoPadraoMock).toHaveBeenCalledTimes(1)
  })

  it('mostra estado de indisponibilidade com causa e nova tentativa quando a busca falhar', async () => {
    getSeguradoPadraoMock.mockRejectedValue(
      new ErroContexto({
        codigo: 'segurado_padrao_ausente',
        correlacaoId: null,
        ocorrencia: 'Os dados sintéticos ainda não foram restaurados.',
        impacto: 'Nenhum segurado ativo pode ser exibido.',
        proximaAcao: 'Execute a restauração dos dados sintéticos e tente novamente.',
        status: 503,
      }),
    )

    renderizarComPerfil('segurado')

    expect(await screen.findByText('Segurado ativo indisponível')).toBeInTheDocument()
    expect(
      screen.getByText('Os dados sintéticos ainda não foram restaurados.'),
    ).toBeInTheDocument()
    expect(screen.queryByText('Pessoa Segurada Sintética DEMO-001')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Tentar novamente' })).toBeInTheDocument()
  })

  it('ativar "Visualizar como" chama alternarPerfil com o perfil oposto', async () => {
    getSeguradoPadraoMock.mockResolvedValue({ id: '1', nome: 'Pessoa Segurada Sintética DEMO-001' })
    const usuario = userEvent.setup()
    renderizarComPerfil('administrador')

    await usuario.click(screen.getByRole('button', { name: /Visualizar como Segurado/ }))

    expect(screen.getByText('Segurado')).toBeInTheDocument()
    expect(window.localStorage.getItem(CHAVE_ARMAZENAMENTO_PERFIL)).toBe('segurado')
  })

  it('anuncia a troca de perfil em uma região aria-live="polite"', async () => {
    getSeguradoPadraoMock.mockResolvedValue({ id: '1', nome: 'Pessoa Segurada Sintética DEMO-001' })
    const usuario = userEvent.setup()
    renderizarComPerfil('administrador')

    await usuario.click(screen.getByRole('button', { name: /Visualizar como Segurado/ }))

    await waitFor(() => {
      expect(screen.getByText('Visualizando como Segurado').closest('[aria-live="polite"]')).not.toBeNull()
    })
  })

  it('comunica o perfil ativo por texto e ícone, não só por cor', () => {
    const { container } = renderizarComPerfil('administrador')

    expect(screen.getByText('Administrador')).toBeInTheDocument()
    expect(container.querySelector('svg')).not.toBeNull()
  })
})
