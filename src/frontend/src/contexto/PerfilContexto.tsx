import { createContext, type ReactNode, useCallback, useContext, useState } from 'react'

export type Perfil = 'administrador' | 'segurado'

/**
 * Superfícies "de topo": alcançáveis pela navegação lateral, sem payload (AD-016).
 * `eventos`, `regras`, `segurados`, `comunicacoes` e `fontes-de-dados` são os 5 itens de
 * negócio do Administrador (História 6.1) — suas telas chegam nas Histórias 6.2–6.7;
 * até lá, `App.tsx` monta um placeholder para elas.
 */
export type SuperficieTopo =
  | { tipo: 'prontidao' }
  | { tipo: 'restaurar-dados-sinteticos' }
  | { tipo: 'documentacao-api' }
  | { tipo: 'eventos' }
  | { tipo: 'regras' }
  | { tipo: 'segurados' }
  | { tipo: 'comunicacoes' }
  | { tipo: 'fontes-de-dados' }
  | { tipo: 'visao-geral' }

/**
 * Superfícies "de detalhe": parametrizadas por id, nunca listadas na navegação lateral —
 * só alcançáveis por uma ação dentro da superfície de topo correspondente (AD-016).
 */
export type SuperficieDetalhe =
  | { tipo: 'evento-execucao'; execucaoId: string; perfilPai: 'administrador' }
  | { tipo: 'resultado-execucao'; execucaoId: string; perfilPai: 'administrador' }

export type Superficie = SuperficieTopo | SuperficieDetalhe

export const CHAVE_ARMAZENAMENTO_PERFIL = 'central-preventiva.perfil'

export const SUPERFICIES_TOPO_POR_PERFIL: Record<Perfil, readonly SuperficieTopo[]> = {
  administrador: [
    { tipo: 'prontidao' },
    { tipo: 'restaurar-dados-sinteticos' },
    { tipo: 'documentacao-api' },
    { tipo: 'eventos' },
    { tipo: 'regras' },
    { tipo: 'segurados' },
    { tipo: 'comunicacoes' },
    { tipo: 'fontes-de-dados' },
  ],
  segurado: [{ tipo: 'visao-geral' }],
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
    () => SUPERFICIES_TOPO_POR_PERFIL[lerPerfilArmazenado()][0],
  )

  const alternarPerfil = useCallback((novoPerfil: Perfil) => {
    try {
      window.localStorage.setItem(CHAVE_ARMAZENAMENTO_PERFIL, novoPerfil)
    } catch {
      // Armazenamento indisponível: a alternância continua válida só nesta sessão.
    }
    definirPerfil(novoPerfil)
    definirSuperficieAtiva(SUPERFICIES_TOPO_POR_PERFIL[novoPerfil][0])
  }, [])

  const selecionarSuperficie = useCallback((superficie: Superficie) => {
    definirSuperficieAtiva(superficie)
  }, [])

  const superficieValida =
    'perfilPai' in superficieAtiva
      ? superficieAtiva.perfilPai === perfil
      : SUPERFICIES_TOPO_POR_PERFIL[perfil].some((s) => s.tipo === superficieAtiva.tipo)

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
