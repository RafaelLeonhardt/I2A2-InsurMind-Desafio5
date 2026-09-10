import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  CHAVE_ARMAZENAMENTO_PERFIL,
  PerfilProvider,
  SUPERFICIES_TOPO_POR_PERFIL,
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
    expect(result.current.superficieAtiva).toEqual({ tipo: 'prontidao' })
  })

  it('restaura o perfil "segurado" salvo em localStorage', () => {
    window.localStorage.setItem(CHAVE_ARMAZENAMENTO_PERFIL, 'segurado')

    const { result } = renderizarPerfilContexto()

    expect(result.current.perfil).toBe('segurado')
    expect(result.current.superficieAtiva).toEqual({ tipo: 'visao-geral' })
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
      result.current.selecionarSuperficie({ tipo: 'restaurar-dados-sinteticos' })
    })
    expect(result.current.superficieAtiva).toEqual({ tipo: 'restaurar-dados-sinteticos' })

    act(() => {
      result.current.alternarPerfil('segurado')
    })

    expect(result.current.perfil).toBe('segurado')
    expect(result.current.superficieAtiva).toEqual({ tipo: 'visao-geral' })
  })

  it('alternarPerfil de segurado para administrador redefine superficieAtiva para "prontidao"', () => {
    window.localStorage.setItem(CHAVE_ARMAZENAMENTO_PERFIL, 'segurado')
    const { result } = renderizarPerfilContexto()
    expect(result.current.superficieAtiva).toEqual({ tipo: 'visao-geral' })

    act(() => {
      result.current.alternarPerfil('administrador')
    })

    expect(result.current.perfil).toBe('administrador')
    expect(result.current.superficieAtiva).toEqual({ tipo: 'prontidao' })
  })

  it('selecionarSuperficie aceita um valor presente na lista do perfil ativo', () => {
    const { result } = renderizarPerfilContexto()

    act(() => {
      result.current.selecionarSuperficie({ tipo: 'restaurar-dados-sinteticos' })
    })

    expect(result.current.superficieAtiva).toEqual({ tipo: 'restaurar-dados-sinteticos' })
    expect(result.current.superficieValida).toBe(true)
  })

  it('selecionarSuperficie com um valor fora da lista do perfil ativo torna superficieValida falso', () => {
    const { result } = renderizarPerfilContexto()

    act(() => {
      result.current.selecionarSuperficie({ tipo: 'visao-geral' })
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
    expect(result.current.superficieAtiva).toEqual({ tipo: 'visao-geral' })
    expect(window.localStorage.getItem(CHAVE_ARMAZENAMENTO_PERFIL)).toBe('segurado')
  })

  it('"documentacao-api" está presente só nas superfícies do perfil administrador', () => {
    expect(SUPERFICIES_TOPO_POR_PERFIL.administrador.map((s) => s.tipo)).toContain(
      'documentacao-api',
    )
    expect(SUPERFICIES_TOPO_POR_PERFIL.segurado.map((s) => s.tipo)).not.toContain(
      'documentacao-api',
    )
  })

  it('lista os 5 itens de negócio do administrador em SUPERFICIES_TOPO_POR_PERFIL', () => {
    const tipos = SUPERFICIES_TOPO_POR_PERFIL.administrador.map((s) => s.tipo)

    expect(tipos).toEqual(
      expect.arrayContaining([
        'eventos',
        'regras',
        'segurados',
        'comunicacoes',
        'fontes-de-dados',
      ]),
    )
  })

  it('superficieValida é true para uma superfície de detalhe cujo perfilPai bate com o perfil ativo', () => {
    const { result } = renderizarPerfilContexto()

    act(() => {
      result.current.selecionarSuperficie({
        tipo: 'evento-execucao',
        execucaoId: 'exec-1',
        perfilPai: 'administrador',
      })
    })

    expect(result.current.superficieValida).toBe(true)
  })

  it('superficieValida vira false para uma superfície de detalhe que sobrevive à troca de perfil', () => {
    const { result } = renderizarPerfilContexto()

    act(() => {
      result.current.selecionarSuperficie({
        tipo: 'evento-execucao',
        execucaoId: 'exec-1',
        perfilPai: 'administrador',
      })
    })
    expect(result.current.superficieValida).toBe(true)

    act(() => {
      result.current.alternarPerfil('segurado')
      // alternarPerfil já redefine superficieAtiva; força de volta a superfície de detalhe
      // "antiga" para simular uma referência que sobreviveu à troca (ex.: callback assíncrono).
      result.current.selecionarSuperficie({
        tipo: 'evento-execucao',
        execucaoId: 'exec-1',
        perfilPai: 'administrador',
      })
    })

    expect(result.current.perfil).toBe('segurado')
    expect(result.current.superficieValida).toBe(false)
  })

  it('superficieValida é true para "resultado-execucao" quando o perfilPai bate com o perfil ativo', () => {
    const { result } = renderizarPerfilContexto()

    act(() => {
      result.current.selecionarSuperficie({
        tipo: 'resultado-execucao',
        execucaoId: 'exec-1',
        perfilPai: 'administrador',
      })
    })

    expect(result.current.superficieValida).toBe(true)
  })

  it('superficieValida vira false para "resultado-execucao" após trocar para o perfil segurado', () => {
    const { result } = renderizarPerfilContexto()

    act(() => {
      result.current.selecionarSuperficie({
        tipo: 'resultado-execucao',
        execucaoId: 'exec-1',
        perfilPai: 'administrador',
      })
    })
    expect(result.current.superficieValida).toBe(true)

    act(() => {
      result.current.alternarPerfil('segurado')
      result.current.selecionarSuperficie({
        tipo: 'resultado-execucao',
        execucaoId: 'exec-1',
        perfilPai: 'administrador',
      })
    })

    expect(result.current.perfil).toBe('segurado')
    expect(result.current.superficieValida).toBe(false)
  })
})
