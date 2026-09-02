import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Regra } from '../../api/regras'
import { ErroRegras } from '../../api/regras'
import { SuperficieRegras } from './SuperficieRegras'

const { getRegras, testarRegra, ativarRegra } = vi.hoisted(() => ({
  getRegras: vi.fn(),
  testarRegra: vi.fn(),
  ativarRegra: vi.fn(),
}))

vi.mock('../../api/regras', async (importarOriginal) => ({
  ...(await importarOriginal<typeof import('../../api/regras')>()),
  getRegras,
  testarRegra,
  ativarRegra,
}))

const REGRA_ATIVA: Regra = {
  id: '11111111-1111-1111-1111-111111111111',
  eventoTipo: 'chuva_intensa',
  limiarMeteorologico: 50,
  areaAplicavel: '9990001',
  apoliceTipo: 'residencial',
  coberturaExigida: 'alagamento',
  antecedenciaHoras: 24,
  canal: 'whatsapp',
  versao: 1,
  estado: 'ativa',
}

const REGRA_SUBSTITUIDA: Regra = {
  ...REGRA_ATIVA,
  id: '22222222-2222-2222-2222-222222222222',
  versao: 0,
  estado: 'substituida',
}

beforeEach(() => {
  getRegras.mockReset()
  testarRegra.mockReset()
  ativarRegra.mockReset()
})

describe('superfície de regras', () => {
  it('mostra o estado de carregamento até a primeira resposta real', () => {
    getRegras.mockReturnValue(new Promise(() => {}))

    render(<SuperficieRegras />)

    expect(screen.getByRole('status')).toHaveTextContent('Carregando regras…')
  })

  it('mostra Indisponível com ocorrência, impacto e próxima ação quando a consulta falha', async () => {
    getRegras.mockRejectedValue(new TypeError('Failed to fetch'))

    render(<SuperficieRegras />)

    expect(await screen.findByRole('alert')).toHaveTextContent('Indisponível')
  })

  it('lista as regras com a versão ativa identificada por texto e ícone', async () => {
    getRegras.mockResolvedValue([REGRA_ATIVA, REGRA_SUBSTITUIDA])

    render(<SuperficieRegras />)

    await screen.findByRole('table')
    const linhas = screen.getAllByRole('row')
    const linhaAtiva = linhas.find((linha) => within(linha).queryByText('Ativa'))
    const linhaSubstituida = linhas.find((linha) => within(linha).queryByText('Substituída'))

    expect(linhaAtiva).toBeDefined()
    expect(linhaSubstituida).toBeDefined()
    expect(within(linhaAtiva!).getByText('Ativa').closest('span')?.querySelector('svg')).toBeTruthy()
  })

  it('só permite editar a versão ativa', async () => {
    getRegras.mockResolvedValue([REGRA_ATIVA, REGRA_SUBSTITUIDA])

    render(<SuperficieRegras />)

    await screen.findByRole('table')
    const botoesEditar = screen.getAllByRole('button', { name: 'Editar' })
    expect(botoesEditar[0]).not.toBeDisabled()
    expect(botoesEditar[1]).toBeDisabled()
  })

  it('abre o formulário pré-preenchido e mantém Ativar desabilitado antes de testar', async () => {
    getRegras.mockResolvedValue([REGRA_ATIVA])
    const usuario = userEvent.setup()

    render(<SuperficieRegras />)

    await usuario.click(await screen.findByRole('button', { name: 'Editar' }))

    expect(screen.getByLabelText('Limiar meteorológico')).toHaveValue(50)
    expect(screen.getByLabelText('Área aplicável')).toHaveValue('9990001')
    expect(screen.getByRole('button', { name: /Ativar nova versão/ })).toBeDisabled()
  })

  it('testa a configuração e exibe operando, valor observado, resultado e justificativa', async () => {
    getRegras.mockResolvedValue([REGRA_ATIVA])
    testarRegra.mockResolvedValue([
      {
        eventoId: '33333333-3333-3333-3333-333333333333',
        relevante: true,
        motivo: 'relevante',
        criterios: [
          {
            operando: 'área aplicável',
            valorObservado: '9990001',
            atende: true,
            justificativa: 'Área do evento corresponde à área aplicável da regra.',
          },
        ],
      },
    ])
    const usuario = userEvent.setup()

    render(<SuperficieRegras />)
    await usuario.click(await screen.findByRole('button', { name: 'Editar' }))
    await usuario.click(screen.getByRole('button', { name: 'Testar' }))

    const resultado = await screen.findByRole('region', { name: /Resultado do teste/ })
    expect(within(resultado).getByText('área aplicável')).toBeInTheDocument()
    expect(within(resultado).getByText('9990001')).toBeInTheDocument()
    expect(within(resultado).getByText('Atende')).toBeInTheDocument()
    expect(
      within(resultado).getByText('Área do evento corresponde à área aplicável da regra.'),
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Ativar nova versão/ })).not.toBeDisabled()
  })

  it('erro de validação aparece junto ao campo sem descartar os demais valores digitados', async () => {
    getRegras.mockResolvedValue([REGRA_ATIVA])
    testarRegra.mockRejectedValue(
      new ErroRegras({
        codigo: 'configuracao_invalida',
        correlacaoId: null,
        ocorrencia: 'A configuração de regra proposta é inválida.',
        impacto: 'Nenhum teste foi executado.',
        proximaAcao: 'Corrija os campos indicados e tente testar de novo.',
        status: 422,
        erros: [
          { campo: 'limiar_meteorologico', motivo: 'Limiar meteorológico deve ser maior que zero.' },
        ],
      }),
    )
    const usuario = userEvent.setup()

    render(<SuperficieRegras />)
    await usuario.click(await screen.findByRole('button', { name: 'Editar' }))
    const campoLimiar = screen.getByLabelText('Limiar meteorológico')
    await usuario.clear(campoLimiar)
    await usuario.type(campoLimiar, '-1')
    const campoCobertura = screen.getByLabelText('Cobertura exigida')
    await usuario.clear(campoCobertura)
    await usuario.type(campoCobertura, 'cobertura-customizada')

    await usuario.click(screen.getByRole('button', { name: 'Testar' }))

    expect(
      await screen.findByText('Limiar meteorológico deve ser maior que zero.'),
    ).toBeInTheDocument()
    expect(campoLimiar).toHaveAttribute('aria-invalid', 'true')
    expect(screen.getByLabelText('Cobertura exigida')).toHaveValue('cobertura-customizada')
    expect(screen.getByRole('button', { name: /Ativar nova versão/ })).toBeDisabled()
  })

  it('ativa a nova versão depois de testar e mostra a mensagem de sucesso', async () => {
    getRegras.mockResolvedValue([REGRA_ATIVA])
    testarRegra.mockResolvedValue([
      {
        eventoId: '33333333-3333-3333-3333-333333333333',
        relevante: true,
        motivo: 'relevante',
        criterios: [],
      },
    ])
    ativarRegra.mockResolvedValue({ ...REGRA_ATIVA, versao: 2 })
    const usuario = userEvent.setup()

    render(<SuperficieRegras />)
    await usuario.click(await screen.findByRole('button', { name: 'Editar' }))
    await usuario.click(screen.getByRole('button', { name: 'Testar' }))
    await screen.findByText(/Resultado do teste determinístico/)
    await usuario.click(screen.getByRole('button', { name: /Ativar nova versão/ }))

    expect(await screen.findByRole('status')).toHaveTextContent('Nova versão ativada')
    expect(ativarRegra).toHaveBeenCalledWith(
      REGRA_ATIVA.id,
      REGRA_ATIVA.versao,
      expect.objectContaining({ limiarMeteorologico: 50 }),
    )
  })

  it('reinvalida o teste quando o formulário é editado depois de testar', async () => {
    getRegras.mockResolvedValue([REGRA_ATIVA])
    testarRegra.mockResolvedValue([
      {
        eventoId: '33333333-3333-3333-3333-333333333333',
        relevante: true,
        motivo: 'relevante',
        criterios: [],
      },
    ])
    const usuario = userEvent.setup()

    render(<SuperficieRegras />)
    await usuario.click(await screen.findByRole('button', { name: 'Editar' }))
    await usuario.click(screen.getByRole('button', { name: 'Testar' }))
    await screen.findByText(/Resultado do teste determinístico/)
    expect(screen.getByRole('button', { name: /Ativar nova versão/ })).not.toBeDisabled()

    const campoLimiar = screen.getByLabelText('Limiar meteorológico')
    await usuario.clear(campoLimiar)
    await usuario.type(campoLimiar, '60')

    expect(screen.getByRole('button', { name: /Ativar nova versão/ })).toBeDisabled()
  })
})
