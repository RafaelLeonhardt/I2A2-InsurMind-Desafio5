import { ArrowsLeftRightIcon, UserCircleIcon, UserGearIcon } from '@phosphor-icons/react'
import { useCallback, useEffect, useState } from 'react'
import { ErroContexto, getSeguradoPadrao, type SeguradoPadrao } from '../api/contexto'
import { type Perfil, usePerfilContexto } from '../contexto/PerfilContexto'

const ROTULOS_PERFIL: Record<Perfil, string> = {
  administrador: 'Administrador',
  segurado: 'Segurado',
}

const PERFIL_OPOSTO: Record<Perfil, Perfil> = {
  administrador: 'segurado',
  segurado: 'administrador',
}

function IconePerfil({ perfil }: { perfil: Perfil }) {
  if (perfil === 'administrador') {
    return <UserGearIcon aria-hidden="true" size={20} weight="fill" />
  }
  return <UserCircleIcon aria-hidden="true" size={20} weight="fill" />
}

function formatarDataHoraReferencia(data: Date): string {
  return new Intl.DateTimeFormat('pt-BR', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(data)
}

/** Barra de contexto: perfil ativo, segurado ativo (quando Segurado) e o seletor "Visualizar como". */
export function BarraContexto() {
  const { perfil, alternarPerfil } = usePerfilContexto()
  const [segurado, definirSegurado] = useState<SeguradoPadrao | null>(null)
  const [falhaSegurado, definirFalhaSegurado] = useState<ErroContexto | null>(null)
  const [carregandoSegurado, definirCarregandoSegurado] = useState(false)
  const [anuncioPerfil, definirAnuncioPerfil] = useState('')

  const buscarSeguradoPadrao = useCallback(async () => {
    definirCarregandoSegurado(true)
    definirFalhaSegurado(null)
    try {
      definirSegurado(await getSeguradoPadrao())
    } catch (causa) {
      definirFalhaSegurado(causa instanceof ErroContexto ? causa : null)
    } finally {
      definirCarregandoSegurado(false)
    }
  }, [])

  useEffect(() => {
    if (perfil === 'segurado') {
      void buscarSeguradoPadrao()
    }
  }, [perfil, buscarSeguradoPadrao])

  function trocarPerfil() {
    const novoPerfil = PERFIL_OPOSTO[perfil]
    alternarPerfil(novoPerfil)
    definirAnuncioPerfil(`Visualizando como ${ROTULOS_PERFIL[novoPerfil]}`)
  }

  const dataHoraReferencia = formatarDataHoraReferencia(new Date())

  return (
    <header className="barra-contexto">
      <div>
        <span className="rotulo-contexto">Perfil visualizado</span>
        <strong>
          <IconePerfil perfil={perfil} />
          {ROTULOS_PERFIL[perfil]}
        </strong>
      </div>
      {perfil === 'segurado' && (
        <div>
          <span className="rotulo-contexto">Segurado ativo</span>
          {carregandoSegurado && <strong>Carregando…</strong>}
          {!carregandoSegurado && segurado && <strong>{segurado.nome}</strong>}
          {!carregandoSegurado && !segurado && falhaSegurado && (
            <div role="alert">
              <strong>Segurado ativo indisponível</strong>
              <p>{falhaSegurado.ocorrencia}</p>
              <button onClick={() => void buscarSeguradoPadrao()} type="button">
                Tentar novamente
              </button>
            </div>
          )}
        </div>
      )}
      <div>
        <span className="rotulo-contexto">Data e hora de referência</span>
        <strong>{dataHoraReferencia}</strong>
      </div>
      <button className="seletor-demonstrativo" onClick={trocarPerfil} type="button">
        <ArrowsLeftRightIcon aria-hidden="true" size={18} />
        Visualizar como {ROTULOS_PERFIL[PERFIL_OPOSTO[perfil]]}
      </button>
      <p aria-live="polite" className="sr-only">
        {anuncioPerfil}
      </p>
    </header>
  )
}
