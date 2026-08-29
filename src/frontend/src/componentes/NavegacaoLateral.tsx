import { ArrowsLeftRightIcon, CheckCircleIcon, HouseIcon, ShieldCheckIcon } from '@phosphor-icons/react'
import { SUPERFICIES_POR_PERFIL, type Superficie, usePerfilContexto } from '../contexto/PerfilContexto'

const ROTULOS: Record<Superficie, string> = {
  prontidao: 'Prontidão',
  'restaurar-dados-sinteticos': 'Restaurar dados sintéticos',
  'visao-geral': 'Visão geral',
}

function IconeSuperficie({ superficie }: { superficie: Superficie }) {
  if (superficie === 'prontidao') {
    return <CheckCircleIcon aria-hidden="true" size={21} />
  }
  if (superficie === 'restaurar-dados-sinteticos') {
    return <ArrowsLeftRightIcon aria-hidden="true" size={21} />
  }
  return <HouseIcon aria-hidden="true" size={21} />
}

/** Navegação lateral: lista as superfícies do perfil ativo e aciona `selecionarSuperficie`. */
export function NavegacaoLateral() {
  const { perfil, superficieAtiva, selecionarSuperficie } = usePerfilContexto()
  const superficies = SUPERFICIES_POR_PERFIL[perfil]

  return (
    <nav className="navegacao" aria-label="Navegação principal">
      <div className="marca">
        <ShieldCheckIcon size={30} weight="fill" aria-hidden="true" />
        <span>Central Preventiva</span>
      </div>
      <ul>
        {superficies.map((superficie) => (
          <li key={superficie}>
            <button
              aria-current={superficie === superficieAtiva ? 'page' : undefined}
              className={superficie === superficieAtiva ? 'item-navegacao ativo' : 'item-navegacao'}
              onClick={() => selecionarSuperficie(superficie)}
              type="button"
            >
              <IconeSuperficie superficie={superficie} />
              {ROTULOS[superficie]}
            </button>
          </li>
        ))}
      </ul>
    </nav>
  )
}
