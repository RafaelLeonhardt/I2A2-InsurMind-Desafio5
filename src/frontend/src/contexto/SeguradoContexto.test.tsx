import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ErroListaSegurados } from '../api/listaSegurados'
import {
  CHAVE_ARMAZENAMENTO_SEGURADO_ATIVO,
  SeguradoProvider,
  useSeguradoContexto,
} from './SeguradoContexto'

const { getListaSeguradosMock } = vi.hoisted(() => ({ getListaSeguradosMock: vi.fn() }))

vi.mock('../api/listaSegurados', async (importarOriginal) => {
  const original = await importarOriginal<typeof import('../api/listaSegurados')>()
  return { ...original, getListaSegurados: getListaSeguradosMock }
})

const SEGURADO_A = { id: '11111111-1111-1111-1111-111111111111', nome: 'Pessoa Sintética DEMO-001' }
const SEGURADO_B = { id: '22222222-2222-2222-2222-222222222222', nome: 'Pessoa Sintética DEMO-002' }
const SEGURADO_C = { id: '33333333-3333-3333-3333-333333333333', nome: 'Pessoa Sintética DEMO-003' }

type Resolucao<T> = { resolver: (valor: T) => void; rejeitar: (causa: unknown) => void }

function deferir<T>(): [Promise<T>, Resolucao<T>] {
  let resolver!: (valor: T) => void
  let rejeitar!: (causa: unknown) => void
  const promessa = new Promise<T>((res, rej) => {
    resolver = res
    rejeitar = rej
  })
  return [promessa, { resolver, rejeitar }]
}

function renderizarSeguradoContexto() {
  return renderHook(() => useSeguradoContexto(), { wrapper: SeguradoProvider })
}

beforeEach(() => {
  window.localStorage.clear()
  getListaSeguradosMock.mockReset()
})

afterEach(() => {
  window.localStorage.clear()
})

describe('SeguradoProvider / useSeguradoContexto', () => {
  it('carrega a lista e resolve o primeiro segurado quando nada está salvo', async () => {
    getListaSeguradosMock.mockResolvedValue([SEGURADO_A, SEGURADO_B])

    const { result } = renderizarSeguradoContexto()

    await waitFor(() => expect(result.current.estado).toBe('ocioso'))
    expect(result.current.seguradoAtivoId).toBe(SEGURADO_A.id)
    expect(result.current.segurados).toEqual([SEGURADO_A, SEGURADO_B])
  })

  it('restaura o segurado salvo em localStorage ao recarregar', async () => {
    window.localStorage.setItem(CHAVE_ARMAZENAMENTO_SEGURADO_ATIVO, SEGURADO_B.id)
    getListaSeguradosMock.mockResolvedValue([SEGURADO_A, SEGURADO_B])

    const { result } = renderizarSeguradoContexto()

    await waitFor(() => expect(result.current.estado).toBe('ocioso'))
    expect(result.current.seguradoAtivoId).toBe(SEGURADO_B.id)
  })

  it('trocar de segurado persiste a escolha em localStorage', async () => {
    getListaSeguradosMock.mockResolvedValue([SEGURADO_A, SEGURADO_B])
    const { result } = renderizarSeguradoContexto()
    await waitFor(() => expect(result.current.estado).toBe('ocioso'))

    act(() => {
      result.current.selecionar(SEGURADO_B.id)
    })
    expect(result.current.estado).toBe('trocando')

    await waitFor(() => expect(result.current.estado).toBe('ocioso'))
    expect(result.current.seguradoAtivoId).toBe(SEGURADO_B.id)
    expect(window.localStorage.getItem(CHAVE_ARMAZENAMENTO_SEGURADO_ATIVO)).toBe(SEGURADO_B.id)
  })

  it('selecionar o mesmo segurado já ativo é uma operação válida sem efeito', async () => {
    getListaSeguradosMock.mockResolvedValue([SEGURADO_A, SEGURADO_B])
    const { result } = renderizarSeguradoContexto()
    await waitFor(() => expect(result.current.estado).toBe('ocioso'))

    act(() => {
      result.current.selecionar(SEGURADO_A.id)
    })

    expect(result.current.estado).toBe('ocioso')
    expect(result.current.seguradoAtivoId).toBe(SEGURADO_A.id)
    expect(getListaSeguradosMock).toHaveBeenCalledTimes(1)
  })

  it('falha simulada durante a troca reverte ao seguradoAtivoId anterior, com causa/impacto/próxima ação', async () => {
    getListaSeguradosMock.mockResolvedValueOnce([SEGURADO_A, SEGURADO_B])
    const { result } = renderizarSeguradoContexto()
    await waitFor(() => expect(result.current.estado).toBe('ocioso'))

    const erro = new ErroListaSegurados({
      ocorrencia: 'Falha sintética ao revalidar a lista.',
      impacto: 'A troca não pôde ser concluída.',
      proximaAcao: 'Tente selecionar o segurado novamente.',
    })
    getListaSeguradosMock.mockRejectedValueOnce(erro)

    act(() => {
      result.current.selecionar(SEGURADO_B.id)
    })

    await waitFor(() => expect(result.current.estado).toBe('erro'))
    expect(result.current.seguradoAtivoId).toBe(SEGURADO_A.id)
    expect(result.current.falha).toEqual({
      ocorrencia: 'Falha sintética ao revalidar a lista.',
      impacto: 'A troca não pôde ser concluída.',
      proximaAcao: 'Tente selecionar o segurado novamente.',
    })
  })

  it('resposta tardia de uma troca já superada por outra mais recente é descartada', async () => {
    getListaSeguradosMock.mockResolvedValueOnce([SEGURADO_A, SEGURADO_B, SEGURADO_C])
    const { result } = renderizarSeguradoContexto()
    await waitFor(() => expect(result.current.estado).toBe('ocioso'))
    expect(result.current.seguradoAtivoId).toBe(SEGURADO_A.id)

    const [promessaParaB, resolucaoParaB] = deferir<(typeof SEGURADO_A)[]>()
    const [promessaParaC, resolucaoParaC] = deferir<(typeof SEGURADO_A)[]>()
    getListaSeguradosMock.mockReturnValueOnce(promessaParaB)
    getListaSeguradosMock.mockReturnValueOnce(promessaParaC)

    // Troca para B disparada primeiro, depois já superada por uma troca para C — ambas
    // ainda não resolvidas nesse ponto (nenhuma das duas é o segurado hoje ativo, A).
    act(() => {
      result.current.selecionar(SEGURADO_B.id)
    })
    act(() => {
      result.current.selecionar(SEGURADO_C.id)
    })

    // A troca mais recente (para C) resolve primeiro.
    act(() => {
      resolucaoParaC.resolver([SEGURADO_A, SEGURADO_B, SEGURADO_C])
    })
    await waitFor(() => expect(result.current.estado).toBe('ocioso'))
    expect(result.current.seguradoAtivoId).toBe(SEGURADO_C.id)

    // A resposta tardia da troca para B, já superada, é descartada — não reaplica B.
    act(() => {
      resolucaoParaB.resolver([SEGURADO_A, SEGURADO_B, SEGURADO_C])
    })

    expect(result.current.seguradoAtivoId).toBe(SEGURADO_C.id)
    expect(result.current.estado).toBe('ocioso')
  })

  it('lista vazia (seed ausente): estado ocioso sem nenhum segurado ativo', async () => {
    getListaSeguradosMock.mockResolvedValue([])

    const { result } = renderizarSeguradoContexto()

    await waitFor(() => expect(result.current.estado).toBe('ocioso'))
    expect(result.current.seguradoAtivoId).toBeNull()
    expect(result.current.segurados).toEqual([])
  })

  it('falha ao carregar a lista inicial expõe causa/impacto/próxima ação', async () => {
    const erro = new ErroListaSegurados({
      ocorrencia: 'Falha sintética inicial.',
      impacto: 'A lista de segurados não pôde ser carregada.',
      proximaAcao: 'Verifique o backend e tente novamente.',
    })
    getListaSeguradosMock.mockRejectedValue(erro)

    const { result } = renderizarSeguradoContexto()

    await waitFor(() => expect(result.current.estado).toBe('erro'))
    expect(result.current.seguradoAtivoId).toBeNull()
    expect(result.current.falha?.ocorrencia).toBe('Falha sintética inicial.')
  })
})
