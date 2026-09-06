import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from 'react'
import { ErroListaSegurados, getListaSegurados, type SeguradoListado } from '../api/listaSegurados'

export const CHAVE_ARMAZENAMENTO_SEGURADO_ATIVO = 'central-preventiva.segurado-ativo'

export type EstadoSeguradoContexto = 'ocioso' | 'trocando' | 'erro'

export type FalhaSeguradoContexto = {
  ocorrencia: string
  impacto: string
  proximaAcao: string
}

type SeguradoContextoValor = {
  /** Segurado sintético ativo, ou `null` enquanto nenhum ainda foi resolvido (lista ainda
   * carregando ou seed ausente). */
  seguradoAtivoId: string | null
  /** Todos os segurados sintéticos disponíveis para o seletor "Visualizar como" (SELETOR-01). */
  segurados: SeguradoListado[]
  estado: EstadoSeguradoContexto
  falha: FalhaSeguradoContexto | null
  /** Troca o segurado ativo. Mesmo id já ativo: operação válida sem efeito (edge case). */
  selecionar: (novoId: string) => void
}

const SeguradoContexto = createContext<SeguradoContextoValor | null>(null)

const FALHA_SEGURADO_INEXISTENTE: FalhaSeguradoContexto = {
  ocorrencia: 'O segurado selecionado não está mais entre os segurados sintéticos disponíveis.',
  impacto: 'A troca de segurado não foi concluída; o contexto anterior permanece ativo.',
  proximaAcao: 'Escolha novamente um segurado da lista atual no seletor "Visualizar como".',
}

function falhaDe(causa: unknown): FalhaSeguradoContexto {
  if (causa instanceof ErroListaSegurados) {
    return { ocorrencia: causa.ocorrencia, impacto: causa.impacto, proximaAcao: causa.proximaAcao }
  }
  return FALHA_SEGURADO_INEXISTENTE
}

function lerSeguradoArmazenado(): string | null {
  try {
    return window.localStorage.getItem(CHAVE_ARMAZENAMENTO_SEGURADO_ATIVO)
  } catch {
    return null
  }
}

function gravarSeguradoArmazenado(id: string): void {
  try {
    window.localStorage.setItem(CHAVE_ARMAZENAMENTO_SEGURADO_ATIVO, id)
  } catch {
    // Armazenamento indisponível: a troca continua válida só nesta sessão.
  }
}

/**
 * Fonte única de verdade do segurado sintético ativo no perfil Segurado (SELETOR-02..04,
 * 06): lista de segurados disponíveis, id ativo persistido em `localStorage`, e o estado de
 * transição (`ocioso`/`trocando`/`erro`) que as cinco superfícies de 5.1–5.6 consultam para
 * saber qual `segurado_id` usar.
 *
 * Cada troca revalida o id contra a lista corrente de segurados sintéticos (mesma fonte que
 * alimenta o seletor); uma resposta tardia de uma troca já superada por outra mais recente é
 * descartada por comparação de token, nunca aplicada ao estado.
 *
 * SPEC_DEVIATION: `design.md` ilustra o fluxo como o contexto disparando as requisições das
 * cinco superfícies e aguardando todas antes de confirmar a troca. Cada uma dessas cinco
 * superfícies (5.1–5.6) já implementa seu próprio ciclo de carregamento/erro/descarte de
 * resposta tardia sobre a prop `seguradoId` (o seam construído para esta história) — repetir
 * essa orquestração aqui duplicaria lógica já correta. `SeguradoContexto` garante a mesma
 * garantia central (nenhuma mistura de dado, reversão em falha) na única parte que só ele
 * pode garantir: o próprio id ativo nunca aponta para um segurado que deixou de existir na
 * lista sintética, e nunca é sobrescrito por uma troca já superada.
 */
export function SeguradoProvider({ children }: { children: ReactNode }) {
  const [segurados, definirSegurados] = useState<SeguradoListado[]>([])
  const [seguradoAtivoId, definirSeguradoAtivoId] = useState<string | null>(null)
  const [estado, definirEstado] = useState<EstadoSeguradoContexto>('trocando')
  const [falha, definirFalha] = useState<FalhaSeguradoContexto | null>(null)
  const tokenAtualRef = useRef(0)

  useEffect(() => {
    const token = ++tokenAtualRef.current
    getListaSegurados()
      .then((lista) => {
        if (token !== tokenAtualRef.current) return
        definirSegurados(lista)
        const armazenado = lerSeguradoArmazenado()
        const inicial = lista.find((segurado) => segurado.id === armazenado) ?? lista[0]
        definirSeguradoAtivoId(inicial ? inicial.id : null)
        definirEstado('ocioso')
        definirFalha(null)
      })
      .catch((causa: unknown) => {
        if (token !== tokenAtualRef.current) return
        definirEstado('erro')
        definirFalha(falhaDe(causa))
      })
  }, [])

  const selecionar = useCallback(
    (novoId: string) => {
      if (novoId === seguradoAtivoId) return

      const token = ++tokenAtualRef.current
      definirEstado('trocando')
      definirFalha(null)
      getListaSegurados()
        .then((lista) => {
          if (token !== tokenAtualRef.current) return
          const encontrado = lista.find((segurado) => segurado.id === novoId)
          if (!encontrado) {
            definirEstado('erro')
            definirFalha(FALHA_SEGURADO_INEXISTENTE)
            return
          }
          definirSegurados(lista)
          definirSeguradoAtivoId(novoId)
          gravarSeguradoArmazenado(novoId)
          definirEstado('ocioso')
          definirFalha(null)
        })
        .catch((causa: unknown) => {
          if (token !== tokenAtualRef.current) return
          definirEstado('erro')
          definirFalha(falhaDe(causa))
        })
    },
    [seguradoAtivoId],
  )

  return (
    <SeguradoContexto.Provider value={{ seguradoAtivoId, segurados, estado, falha, selecionar }}>
      {children}
    </SeguradoContexto.Provider>
  )
}

/** Hook de acesso ao segurado sintético ativo e à troca de contexto. */
export function useSeguradoContexto(): SeguradoContextoValor {
  const valor = useContext(SeguradoContexto)
  if (!valor) {
    throw new Error('useSeguradoContexto deve ser usado dentro de um SeguradoProvider')
  }
  return valor
}
