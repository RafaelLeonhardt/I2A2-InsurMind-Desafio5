import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ErroPreferenciasSegurado, type PreferenciasSegurado } from '../../api/preferenciasSegurado'
import { SuperficieMeusDados } from './SuperficieMeusDados'

const { getPreferenciasMock, atualizarPreferenciasMock } = vi.hoisted(() => ({
  getPreferenciasMock: vi.fn(),
  atualizarPreferenciasMock: vi.fn(),
}))

vi.mock('../../api/preferenciasSegurado', async (importarOriginal) => ({
  ...(await importarOriginal<typeof import('../../api/preferenciasSegurado')>()),
  getPreferencias: getPreferenciasMock,
  atualizarPreferencias: atualizarPreferenciasMock,
}))

const SEGURADO_ID = '11111111-1111-1111-1111-111111111111'

function preferenciasBase(sobrescritas: Partial<PreferenciasSegurado> = {}): PreferenciasSegurado {
  return {
    seguradoId: SEGURADO_ID,
    canalPreferido: 'whatsapp',
    participaDeAlertas: true,
    versao: 1,
    ...sobrescritas,
  }
}

beforeEach(() => {
  getPreferenciasMock.mockReset()
  atualizarPreferenciasMock.mockReset()
})

describe('superfície de meus dados', () => {
  it('mostra o estado de carregamento até a primeira resposta real', () => {
    getPreferenciasMock.mockReturnValue(new Promise(() => {}))

    render(<SuperficieMeusDados seguradoId={SEGURADO_ID} />)

    expect(screen.getByRole('status')).toHaveTextContent('Carregando suas preferências…')
  })

  it('exibe o canal preferencial atual e a participação em alertas, sem outro cadastro', async () => {
    getPreferenciasMock.mockResolvedValue(preferenciasBase())

    render(<SuperficieMeusDados seguradoId={SEGURADO_ID} />)

    expect(await screen.findByRole('combobox', { name: 'Canal preferencial' })).toHaveValue(
      'whatsapp',
    )
    expect(screen.getByRole('checkbox', { name: 'Participar de alertas' })).toBeChecked()
    expect(screen.queryByLabelText(/endereço/i)).not.toBeInTheDocument()
    expect(screen.queryByLabelText(/nome/i)).not.toBeInTheDocument()
  })

  it('mostra Indisponível com ocorrência, impacto e próxima ação quando a consulta falha', async () => {
    getPreferenciasMock.mockRejectedValue(new TypeError('Failed to fetch'))

    render(<SuperficieMeusDados seguradoId={SEGURADO_ID} />)

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Não foi possível carregar suas preferências',
    )
  })

  it('apresenta Salvando e, ao concluir, Salvo (PREFS-02)', async () => {
    const usuario = userEvent.setup()
    getPreferenciasMock.mockResolvedValue(preferenciasBase())
    let resolverAtualizacao: (valor: PreferenciasSegurado) => void = () => {}
    atualizarPreferenciasMock.mockReturnValue(
      new Promise<PreferenciasSegurado>((resolver) => {
        resolverAtualizacao = resolver
      }),
    )

    render(<SuperficieMeusDados seguradoId={SEGURADO_ID} />)
    await screen.findByRole('combobox', { name: 'Canal preferencial' })

    await usuario.click(screen.getByRole('button', { name: 'Salvar' }))

    expect(screen.getAllByText('Salvando…').length).toBeGreaterThan(0)

    resolverAtualizacao(preferenciasBase({ canalPreferido: 'sms', versao: 2 }))

    const salvo = await screen.findByText('Salvo')
    expect(salvo).toHaveAttribute('role', 'status')
    expect(atualizarPreferenciasMock).toHaveBeenCalledWith(SEGURADO_ID, 1, 'whatsapp', true)
  })

  it('em falha ao salvar, preserva os valores editados e explica o erro sem indicar Salvo', async () => {
    const usuario = userEvent.setup()
    getPreferenciasMock.mockResolvedValue(preferenciasBase())
    atualizarPreferenciasMock.mockRejectedValue(
      new ErroPreferenciasSegurado({
        codigo: 'conflito_versao',
        correlacaoId: null,
        ocorrencia: 'A versão esperada não corresponde à versão corrente do segurado.',
        impacto: 'Nenhuma preferência foi atualizada.',
        proximaAcao: 'Recarregue as preferências atuais e tente salvar de novo.',
        status: 409,
      }),
    )

    render(<SuperficieMeusDados seguradoId={SEGURADO_ID} />)
    const seletorCanal = await screen.findByRole('combobox', { name: 'Canal preferencial' })

    await usuario.selectOptions(seletorCanal, 'sms')
    await usuario.click(screen.getByRole('button', { name: 'Salvar' }))

    const erro = await screen.findByRole('alert')
    expect(erro).toHaveTextContent(
      'A versão esperada não corresponde à versão corrente do segurado.',
    )
    expect(screen.queryByText('Salvo')).not.toBeInTheDocument()
    expect(seletorCanal).toHaveValue('sms')
  })

  it('ao desativar a participação, explica que o efeito vale só para alertas futuros', async () => {
    const usuario = userEvent.setup()
    getPreferenciasMock.mockResolvedValue(preferenciasBase({ participaDeAlertas: true }))

    render(<SuperficieMeusDados seguradoId={SEGURADO_ID} />)
    const caixaParticipacao = await screen.findByRole('checkbox', { name: 'Participar de alertas' })
    expect(screen.queryByText(/vale só para alertas futuros/)).not.toBeInTheDocument()

    await usuario.click(caixaParticipacao)

    expect(screen.getByText(/vale só para alertas futuros/)).toBeInTheDocument()
    expect(screen.getByText(/comunicados e alertas já registrados continuam disponíveis/)).toBeInTheDocument()
  })

  it('permite editar canal e participação inteiramente por teclado, com foco visível', async () => {
    const usuario = userEvent.setup()
    getPreferenciasMock.mockResolvedValue(preferenciasBase())
    atualizarPreferenciasMock.mockResolvedValue(preferenciasBase({ canalPreferido: 'sms', versao: 2 }))

    render(<SuperficieMeusDados seguradoId={SEGURADO_ID} />)
    const seletorCanal = await screen.findByRole('combobox', { name: 'Canal preferencial' })
    const caixaParticipacao = screen.getByRole('checkbox', { name: 'Participar de alertas' })
    const botaoSalvar = screen.getByRole('button', { name: 'Salvar' })

    await usuario.tab()
    expect(seletorCanal).toHaveFocus()

    await usuario.selectOptions(seletorCanal, 'sms')
    expect(seletorCanal).toHaveValue('sms')

    await usuario.tab()
    expect(caixaParticipacao).toHaveFocus()

    await usuario.keyboard(' ')
    expect(caixaParticipacao).not.toBeChecked()

    await usuario.tab()
    expect(botaoSalvar).toHaveFocus()

    await usuario.keyboard('{Enter}')

    const salvo = await screen.findByText('Salvo')
    expect(salvo).toHaveAttribute('role', 'status')
    expect(atualizarPreferenciasMock).toHaveBeenCalledWith(SEGURADO_ID, 1, 'sms', false)
  })
})
