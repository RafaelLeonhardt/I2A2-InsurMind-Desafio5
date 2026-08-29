import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  CHAVE_ARMAZENAMENTO_PERFIL,
  PerfilProvider,
  SUPERFICIES_POR_PERFIL,
  usePerfilContexto,
} from './PerfilContexto'

beforeEach(() => {
  window.localStorage.clear()
})

afterEach(() => {
  window.localStorage.clear()
  vi.unstubAllGlobals()
})

function renderizarPerfilContexto() {
  return renderHook(() => usePerfilContexto(), { wrapper: PerfilProvider })
}

describe('PerfilProvider / usePerfilContexto', () => {
  it('inicia com perfil "administrador" quando não há valor salvo em localStorage', () => {
    const { result } = renderizarPerfilContexto()

    expect(result.current.perfil).toBe('administrador')
    expect(result.current.superficieAtiva).toBe('prontidao')
  })

  it('restaura o perfil "segurado" salvo em localStorage', () => {
    window.localStorage.setItem(CHAVE_ARMAZENAMENTO_PERFIL, 'segurado')

    const { result } = renderizarPerfilContexto()

    expect(result.current.perfil).toBe('segurado')
    expect(result.current.superficieAtiva).toBe('visao-geral')
  })

  it('restaura o perfil "administrador" salvo em localStorage', () => {
    window.localStorage.setItem(CHAVE_ARMAZENAMENTO_PERFIL, 'administrador')

    const { result } = renderizarPerfilContexto()

    expect(result.current.perfil).toBe('administrador')
  })

  it('trata um valor corrompido em localStorage como ausência de preferência', () => {
    window.localStorage.setItem(CHAVE_ARMAZENAMENTO_PERFIL, 'super-usuario')

    const { result } = renderizarPerfilContexto()

    expect(result.current.perfil).toBe('administrador')
  })

  it('alternarPerfil grava o novo valor em localStorage e nunca chama fetch', () => {
    const buscar = vi.fn()
    vi.stubGlobal('fetch', buscar)
    const { result } = renderizarPerfilContexto()

    act(() => {
      result.current.alternarPerfil('segurado')
    })

    expect(window.localStorage.getItem(CHAVE_ARMAZENAMENTO_PERFIL)).toBe('segurado')
    expect(buscar).not.toHaveBeenCalled()
  })

  it('alternarPerfil de administrador para segurado redefine superficieAtiva para "visao-geral"', () => {
    const { result } = renderizarPerfilContexto()

    act(() => {
      result.current.selecionarSuperficie('restaurar-dados-sinteticos')
    })
    expect(result.current.superficieAtiva).toBe('restaurar-dados-sinteticos')

    act(() => {
      result.current.alternarPerfil('segurado')
    })

    expect(result.current.perfil).toBe('segurado')
    expect(result.current.superficieAtiva).toBe('visao-geral')
  })

  it('alternarPerfil de segurado para administrador redefine superficieAtiva para "prontidao"', () => {
    window.localStorage.setItem(CHAVE_ARMAZENAMENTO_PERFIL, 'segurado')
    const { result } = renderizarPerfilContexto()
    expect(result.current.superficieAtiva).toBe('visao-geral')

    act(() => {
      result.current.alternarPerfil('administrador')
    })

    expect(result.current.perfil).toBe('administrador')
    expect(result.current.superficieAtiva).toBe('prontidao')
  })

  it('selecionarSuperficie aceita um valor presente na lista do perfil ativo', () => {
    const { result } = renderizarPerfilContexto()

    act(() => {
      result.current.selecionarSuperficie('restaurar-dados-sinteticos')
    })

    expect(result.current.superficieAtiva).toBe('restaurar-dados-sinteticos')
    expect(result.current.superficieValida).toBe(true)
  })

  it('selecionarSuperficie com um valor fora da lista do perfil ativo torna superficieValida falso', () => {
    const { result } = renderizarPerfilContexto()

    act(() => {
      result.current.selecionarSuperficie('visao-geral')
    })

    expect(result.current.superficieValida).toBe(false)
  })

  it('reflete sempre a última alternância em sequência rápida, sem estado intermediário', () => {
    const { result } = renderizarPerfilContexto()

    act(() => {
      result.current.alternarPerfil('segurado')
      result.current.alternarPerfil('administrador')
      result.current.alternarPerfil('segurado')
    })

    expect(result.current.perfil).toBe('segurado')
    expect(result.current.superficieAtiva).toBe('visao-geral')
    expect(window.localStorage.getItem(CHAVE_ARMAZENAMENTO_PERFIL)).toBe('segurado')
  })

  it('"documentacao-api" está presente só nas superfícies do perfil administrador', () => {
    expect(SUPERFICIES_POR_PERFIL.administrador).toContain('documentacao-api')
    expect(SUPERFICIES_POR_PERFIL.segurado).not.toContain('documentacao-api')
  })
})
