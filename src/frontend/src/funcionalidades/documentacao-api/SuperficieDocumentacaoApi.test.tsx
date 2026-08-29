import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ErroDocumentacaoApi } from '../../api/documentacaoApi'
import { SuperficieDocumentacaoApi } from './SuperficieDocumentacaoApi'

const { verificarDocumentacaoApi } = vi.hoisted(() => ({
  verificarDocumentacaoApi: vi.fn(),
}))

vi.mock('../../api/documentacaoApi', async (importarOriginal) => ({
  ...(await importarOriginal<typeof import('../../api/documentacaoApi')>()),
  verificarDocumentacaoApi,
}))

function deferido<T>() {
  let resolver!: (valor: T) => void
  let rejeitar!: (causa: unknown) => void
  const promessa = new Promise<T>((res, rej) => {
    resolver = res
    rejeitar = rej
  })
  return { promessa, resolver, rejeitar }
}

beforeEach(() => {
  verificarDocumentacaoApi.mockReset()
})

describe('SuperficieDocumentacaoApi', () => {
  it('mostra estado de carregamento até a primeira resposta', () => {
    const { promessa } = deferido()
    verificarDocumentacaoApi.mockReturnValue(promessa)

    render(<SuperficieDocumentacaoApi />)

    expect(screen.getByRole('status')).toHaveTextContent('Verificando disponibilidade')
    expect(screen.queryByText('Disponível')).not.toBeInTheDocument()
    expect(screen.queryByText('Indisponível')).not.toBeInTheDocument()
  })

  it('mostra "Disponível" com os dois endereços e um link para /docs em nova aba, sem valor fixo antes da resposta', async () => {
    verificarDocumentacaoApi.mockResolvedValue({
      estado: 'disponivel',
      enderecoSwaggerUi: 'http://127.0.0.1:8000/docs',
      enderecoOpenApi: 'http://127.0.0.1:8000/openapi.json',
    })

    render(<SuperficieDocumentacaoApi />)

    expect(await screen.findByText('Disponível')).toBeInTheDocument()
    const link = screen.getByRole('link', { name: 'http://127.0.0.1:8000/docs' })
    expect(link).toHaveAttribute('href', 'http://127.0.0.1:8000/docs')
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', 'noopener noreferrer')
    expect(
      screen.getByText((_, elemento) => elemento?.textContent === 'Contrato OpenAPI: http://127.0.0.1:8000/openapi.json'),
    ).toBeInTheDocument()
  })

  it('mostra "Indisponível" com causa, impacto, próxima ação e endereço esperado quando a verificação falha', async () => {
    verificarDocumentacaoApi.mockRejectedValue(
      new ErroDocumentacaoApi({
        causa: 'Não foi possível falar com o backend local da Central Preventiva.',
        impacto: 'A documentação da API não pode ser confirmada como disponível.',
        proximaAcao: 'Confirme que o backend está em execução em 127.0.0.1:8000 e tente de novo.',
        enderecoEsperado: 'http://127.0.0.1:8000/docs',
      }),
    )

    render(<SuperficieDocumentacaoApi />)

    expect(await screen.findByText('Indisponível')).toBeInTheDocument()
    const alerta = screen.getByRole('alert')
    expect(alerta).toHaveTextContent(
      'Causa: Não foi possível falar com o backend local da Central Preventiva.',
    )
    expect(alerta).toHaveTextContent(
      'Impacto: A documentação da API não pode ser confirmada como disponível.',
    )
    expect(alerta).toHaveTextContent(
      'Próxima ação: Confirme que o backend está em execução em 127.0.0.1:8000 e tente de novo.',
    )
    expect(alerta).toHaveTextContent('Endereço esperado: http://127.0.0.1:8000/docs')
    expect(screen.queryByText('Disponível')).not.toBeInTheDocument()
  })
})
