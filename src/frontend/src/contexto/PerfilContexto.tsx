import { createContext, type ReactNode, useCallback, useContext, useState } from 'react'

export type Perfil = 'administrador' | 'segurado'

export type Superficie =
  | 'prontidao'
  | 'restaurar-dados-sinteticos'
  | 'documentacao-api'
  | 'visao-geral'

export const CHAVE_ARMAZENAMENTO_PERFIL = 'central-preventiva.perfil'

export const SUPERFICIES_POR_PERFIL: Record<Perfil, readonly Superficie[]> = {
  administrador: ['prontidao', 'restaurar-dados-sinteticos', 'documentacao-api'],
  segurado: ['visao-geral'],
}

type PerfilContextoValor = {
  perfil: Perfil
  superficieAtiva: Superficie
  alternarPerfil: (novoPerfil: Perfil) => void
  selecionarSuperficie: (superficie: Superficie) => void
  superficieValida: boolean
}

const PerfilContexto = createContext<PerfilContextoValor | null>(null)

function ehPerfilValido(valor: unknown): valor is Perfil {
  return valor === 'administrador' || valor === 'segurado'
}

function lerPerfilArmazenado(): Perfil {
  let valor: string | null = null
  try {
    valor = window.localStorage.getItem(CHAVE_ARMAZENAMENTO_PERFIL)
  } catch {
    valor = null
  }
  return ehPerfilValido(valor) ? valor : 'administrador'
}

/** Fonte única de verdade do perfil demonstrativo ativo e da superfície ativa. */
export function PerfilProvider({ children }: { children: ReactNode }) {
  const [perfil, definirPerfil] = useState<Perfil>(lerPerfilArmazenado)
  const [superficieAtiva, definirSuperficieAtiva] = useState<Superficie>(
    () => SUPERFICIES_POR_PERFIL[lerPerfilArmazenado()][0],
  )

  const alternarPerfil = useCallback((novoPerfil: Perfil) => {
    try {
      window.localStorage.setItem(CHAVE_ARMAZENAMENTO_PERFIL, novoPerfil)
    } catch {
      // Armazenamento indisponível: a alternância continua válida só nesta sessão.
    }
    definirPerfil(novoPerfil)
    definirSuperficieAtiva(SUPERFICIES_POR_PERFIL[novoPerfil][0])
  }, [])

  const selecionarSuperficie = useCallback((superficie: Superficie) => {
    definirSuperficieAtiva(superficie)
  }, [])

  const superficieValida = SUPERFICIES_POR_PERFIL[perfil].includes(superficieAtiva)

  return (
    <PerfilContexto.Provider
      value={{ perfil, superficieAtiva, alternarPerfil, selecionarSuperficie, superficieValida }}
    >
      {children}
    </PerfilContexto.Provider>
  )
}

/** Hook de acesso ao perfil demonstrativo ativo e à superfície ativa. */
export function usePerfilContexto(): PerfilContextoValor {
  const valor = useContext(PerfilContexto)
  if (!valor) {
    throw new Error('usePerfilContexto deve ser usado dentro de um PerfilProvider')
  }
  return valor
}
