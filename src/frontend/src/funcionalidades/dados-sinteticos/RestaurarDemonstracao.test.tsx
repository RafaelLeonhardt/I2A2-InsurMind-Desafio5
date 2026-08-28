import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ErroRestauracao } from '../../api/dadosSinteticos'
import { RestaurarDemonstracao } from './RestaurarDemonstracao'

const { restaurar } = vi.hoisted(() => ({ restaurar: vi.fn() }))

vi.mock('../../api/dadosSinteticos', async (importarOriginal) => ({
  ...(await importarOriginal<typeof import('../../api/dadosSinteticos')>()),
  restaurarDadosSinteticos: restaurar,
}))

const RESTAURADO_EM = '2026-03-10T12:30:45+00:00'

const FALHA = new ErroRestauracao({
  codigo: 'execucao_ativa_impede_restauracao',
  correlacaoId: 'c0rr3la-0000-0000-0000-000000000000',
  ocorrencia: 'Há uma execução preventiva ativa em estado não terminal.',
  impacto: 'Nenhuma restauração foi executada e os dados permanecem como estavam.',
  proximaAcao: 'Aguarde a conclusão da execução em andamento e tente de novo.',
  status: 409,
})

beforeEach(() => {
  restaurar.mockReset()
})

async function abrirConfirmacao() {
  const usuario = userEvent.setup()
  render(<RestaurarDemonstracao />)
  await usuario.click(screen.getByRole('button', { name: 'Restaurar demonstração' }))
  return usuario
}

describe('superfície de restauração da demonstração', () => {
  it('abre o modal no estado de confirmação sem chamar a API', async () => {
    await abrirConfirmacao()

    const dialogo = screen.getByRole('dialog', { name: 'Restaurar demonstração' })
    expect(within(dialogo).getByText('Dados sintéticos da demonstração')).toBeInTheDocument()
    expect(
      within(dialogo).getByText(
        'As alterações locais feitas nos dados de referência serão perdidas.',
      ),
    ).toBeInTheDocument()
    expect(within(dialogo).getByRole('button', { name: 'Confirmar restauração' })).toBeInTheDocument()
    expect(restaurar).not.toHaveBeenCalled()
  })

  it('apresenta o estado Restaurando e desabilita a ação enquanto processa', async () => {
    let concluir: (valor: unknown) => void = () => {}
    restaurar.mockReturnValue(
      new Promise((resolver) => {
        concluir = resolver
      }),
    )
    const usuario = await abrirConfirmacao()

    await usuario.click(screen.getByRole('button', { name: 'Confirmar restauração' }))

    expect(screen.getByRole('status')).toHaveTextContent('Restaurando os dados sintéticos')
    expect(screen.getByRole('button', { name: 'Restaurando…' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Cancelar' })).toBeDisabled()
    expect(restaurar).toHaveBeenCalledTimes(1)

    concluir({ status: 'restaurado', restauradoEm: RESTAURADO_EM })
    expect(await screen.findByText(/Dados sintéticos restaurados/)).toBeInTheDocument()
  })

  it('apresenta o estado Concluído após uma resposta bem-sucedida', async () => {
    restaurar.mockResolvedValue({ status: 'restaurado', restauradoEm: RESTAURADO_EM })
    const usuario = await abrirConfirmacao()

    await usuario.click(screen.getByRole('button', { name: 'Confirmar restauração' }))

    expect(await screen.findByRole('status')).toHaveTextContent(
      `Dados sintéticos restaurados em ${RESTAURADO_EM}.`,
    )
    expect(screen.getByRole('button', { name: 'Concluir' })).toBeEnabled()
  })

  it('apresenta o estado Falha com ocorrência, impacto e próxima ação', async () => {
    restaurar.mockRejectedValue(FALHA)
    const usuario = await abrirConfirmacao()

    await usuario.click(screen.getByRole('button', { name: 'Confirmar restauração' }))

    const aviso = await screen.findByRole('alert')
    expect(aviso).toHaveTextContent(`Ocorrência: ${FALHA.ocorrencia}`)
    expect(aviso).toHaveTextContent(`Impacto: ${FALHA.impacto}`)
    expect(aviso).toHaveTextContent(`Próxima ação: ${FALHA.proximaAcao}`)
    expect(
      screen.getByRole('heading', { level: 1, name: 'Restaurar demonstração' }),
    ).toBeInTheDocument()
    expect(screen.getByText('Área administrativa')).toBeInTheDocument()
  })

  it('devolve o foco ao controle de origem ao fechar o modal', async () => {
    const usuario = await abrirConfirmacao()
    const acionador = screen.getByRole('button', { name: 'Restaurar demonstração' })

    await usuario.click(screen.getByRole('button', { name: 'Cancelar' }))

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(acionador).toHaveFocus()
  })
})
