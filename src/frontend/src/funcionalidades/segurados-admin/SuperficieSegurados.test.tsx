import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  ErroListaSeguradosAdmin,
  type SeguradoDetalhado,
} from '../../api/listaSeguradosAdmin'
import { SuperficieSegurados } from './SuperficieSegurados'

const { getSeguradosDetalhadoMock } = vi.hoisted(() => ({
  getSeguradosDetalhadoMock: vi.fn(),
}))

vi.mock('../../api/listaSeguradosAdmin', async () => {
  const real =
    await vi.importActual<typeof import('../../api/listaSeguradosAdmin')>(
      '../../api/listaSeguradosAdmin',
    )
  return { ...real, getSeguradosDetalhado: getSeguradosDetalhadoMock }
})

vi.mock('../segurado/SuperficieApolice', () => ({
  SuperficieApolice: (props: { seguradoId?: string; comoSecao?: boolean }) => (
    <section data-como-secao={String(props.comoSecao)} data-segurado-id={props.seguradoId}>
      Apólice mock
    </section>
  ),
}))

vi.mock('../segurado/SuperficieAlertas', () => ({
  SuperficieAlertas: (props: { seguradoId?: string; comoSecao?: boolean }) => (
    <section data-como-secao={String(props.comoSecao)} data-segurado-id={props.seguradoId}>
      Alertas mock
    </section>
  ),
}))

vi.mock('../segurado/SuperficieComunicados', () => ({
  SuperficieComunicados: (props: { seguradoId?: string; comoSecao?: boolean }) => (
    <section data-como-secao={String(props.comoSecao)} data-segurado-id={props.seguradoId}>
      Comunicados mock
    </section>
  ),
}))

const SEGURADO_A: SeguradoDetalhado = {
  id: '11111111-1111-1111-1111-111111111111',
  nome: 'Ana Sintética',
  codigoIbgeArea: '9990001',
  apoliceNumero: 'RES-0001',
  canalPreferido: 'whatsapp',
}

const SEGURADO_B: SeguradoDetalhado = {
  id: '22222222-2222-2222-2222-222222222222',
  nome: 'Beto Sintético',
  codigoIbgeArea: '9990002',
  apoliceNumero: null,
  canalPreferido: 'sms',
}

afterEach(() => {
  vi.clearAllMocks()
})

describe('SuperficieSegurados', () => {
  it('mostra o estado de carregamento antes da resposta da API', () => {
    getSeguradosDetalhadoMock.mockReturnValue(new Promise(() => {}))

    render(<SuperficieSegurados />)

    expect(screen.getByRole('status')).toHaveTextContent('Carregando segurados…')
  })

  it('exibe nome, localização, apólice e canal traduzido de cada segurado (LISTASEG-01)', async () => {
    getSeguradosDetalhadoMock.mockResolvedValue([SEGURADO_A, SEGURADO_B])

    render(<SuperficieSegurados />)

    expect(await screen.findByText('Ana Sintética')).toBeInTheDocument()
    const linhaA = screen.getByText('Ana Sintética').closest('tr')
    expect(linhaA).not.toBeNull()
    expect(linhaA).toHaveTextContent('9990001')
    expect(linhaA).toHaveTextContent('RES-0001')
    expect(linhaA).toHaveTextContent('WhatsApp')

    const linhaB = screen.getByText('Beto Sintético').closest('tr')
    expect(linhaB).not.toBeNull()
    expect(linhaB).toHaveTextContent('SMS')
    expect(linhaB).toHaveTextContent('—')
  })

  it('diferencia dois segurados com o mesmo nome por id, em duas linhas distintas', async () => {
    const homonimoA: SeguradoDetalhado = { ...SEGURADO_A, nome: 'Pessoa Homônima' }
    const homonimoB: SeguradoDetalhado = { ...SEGURADO_B, nome: 'Pessoa Homônima' }
    getSeguradosDetalhadoMock.mockResolvedValue([homonimoA, homonimoB])

    render(<SuperficieSegurados />)

    const linhas = await screen.findAllByText('Pessoa Homônima')
    expect(linhas).toHaveLength(2)
  })

  it('mostra o estado vazio explícito quando a API devolve lista vazia (LISTASEG-02)', async () => {
    getSeguradosDetalhadoMock.mockResolvedValue([])

    render(<SuperficieSegurados />)

    expect(await screen.findByText('Nenhum segurado sintético cadastrado.')).toBeInTheDocument()
  })

  it('mostra erro explícito com "Tentar novamente" quando a API falha (LISTASEG-03)', async () => {
    getSeguradosDetalhadoMock.mockRejectedValueOnce(
      new ErroListaSeguradosAdmin({
        ocorrencia: 'Falha simulada.',
        impacto: 'Impacto simulado.',
        proximaAcao: 'Ação simulada.',
        status: 500,
      }),
    )
    const usuario = userEvent.setup()

    render(<SuperficieSegurados />)

    expect(await screen.findByRole('alert')).toHaveTextContent('Falha simulada.')
    expect(screen.getByRole('alert')).toHaveTextContent('Impacto simulado.')
    expect(screen.getByRole('alert')).toHaveTextContent('Ação simulada.')

    getSeguradosDetalhadoMock.mockResolvedValueOnce([SEGURADO_A])
    await usuario.click(screen.getByRole('button', { name: 'Tentar novamente' }))

    expect(await screen.findByText('Ana Sintética')).toBeInTheDocument()
    expect(getSeguradosDetalhadoMock).toHaveBeenCalledTimes(2)
  })

  it('filtra por localização (LISTASEG-04)', async () => {
    getSeguradosDetalhadoMock.mockResolvedValue([SEGURADO_A, SEGURADO_B])
    const usuario = userEvent.setup()

    render(<SuperficieSegurados />)
    await screen.findByText('Ana Sintética')

    await usuario.type(
      screen.getByLabelText('Buscar por nome ou localização'),
      '9990002',
    )

    expect(screen.queryByText('Ana Sintética')).not.toBeInTheDocument()
    expect(screen.getByText('Beto Sintético')).toBeInTheDocument()
  })

  it('filtra por nome sem diferenciar maiúsculas/minúsculas (LISTASEG-04)', async () => {
    getSeguradosDetalhadoMock.mockResolvedValue([SEGURADO_A, SEGURADO_B])
    const usuario = userEvent.setup()

    render(<SuperficieSegurados />)
    await screen.findByText('Ana Sintética')

    await usuario.type(screen.getByLabelText('Buscar por nome ou localização'), 'BETO')

    expect(screen.queryByText('Ana Sintética')).not.toBeInTheDocument()
    expect(screen.getByText('Beto Sintético')).toBeInTheDocument()
  })

  it('mostra mensagem de "nenhum resultado" distinta da lista vazia quando a busca não bate (LISTASEG-05)', async () => {
    getSeguradosDetalhadoMock.mockResolvedValue([SEGURADO_A, SEGURADO_B])
    const usuario = userEvent.setup()

    render(<SuperficieSegurados />)
    await screen.findByText('Ana Sintética')

    await usuario.type(
      screen.getByLabelText('Buscar por nome ou localização'),
      'termo-inexistente',
    )

    expect(
      await screen.findByText('Nenhum segurado encontrado para "termo-inexistente".'),
    ).toBeInTheDocument()
    expect(screen.queryByText('Nenhum segurado sintético cadastrado.')).not.toBeInTheDocument()
  })

  it('abre o contexto somente leitura do segurado selecionado, com o seguradoId correto (LISTASEG-06)', async () => {
    getSeguradosDetalhadoMock.mockResolvedValue([SEGURADO_A, SEGURADO_B])
    const usuario = userEvent.setup()

    render(<SuperficieSegurados />)
    await screen.findByText('Ana Sintética')

    await usuario.click(document.getElementById(`botao-contexto-${SEGURADO_B.id}`) as HTMLElement)

    expect(screen.queryByText('Ana Sintética')).not.toBeInTheDocument()
    await waitFor(() => {
      expect(screen.getByText('Apólice mock').getAttribute('data-segurado-id')).toBe(SEGURADO_B.id)
    })
    expect(screen.getByText('Apólice mock').getAttribute('data-como-secao')).toBe('true')
    expect(screen.getByText('Alertas mock').getAttribute('data-segurado-id')).toBe(SEGURADO_B.id)
    expect(screen.getByText('Comunicados mock').getAttribute('data-segurado-id')).toBe(
      SEGURADO_B.id,
    )
  })

  it('fecha o contexto pelo botão "Voltar" e devolve o foco ao "Ver contexto" da linha', async () => {
    getSeguradosDetalhadoMock.mockResolvedValue([SEGURADO_A, SEGURADO_B])
    const usuario = userEvent.setup()

    render(<SuperficieSegurados />)
    await screen.findByText('Ana Sintética')

    const botaoContextoA = document.getElementById(
      `botao-contexto-${SEGURADO_A.id}`,
    ) as HTMLElement
    await usuario.click(botaoContextoA)

    expect(await screen.findByRole('button', { name: 'Voltar' })).toHaveFocus()

    await usuario.click(screen.getByRole('button', { name: 'Voltar' }))

    expect(await screen.findByText('Ana Sintética')).toBeInTheDocument()
    expect(document.getElementById(`botao-contexto-${SEGURADO_A.id}`)).toHaveFocus()
  })

  it('nenhuma ação de edição fica disponível no contexto aberto (apenas leitura)', async () => {
    getSeguradosDetalhadoMock.mockResolvedValue([SEGURADO_A])
    const usuario = userEvent.setup()

    render(<SuperficieSegurados />)
    await screen.findByText('Ana Sintética')

    await usuario.click(document.getElementById(`botao-contexto-${SEGURADO_A.id}`) as HTMLElement)
    await screen.findByText('Apólice mock')

    expect(screen.queryByRole('textbox')).not.toBeInTheDocument()
    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Ver contexto' })).not.toBeInTheDocument()
  })
})
