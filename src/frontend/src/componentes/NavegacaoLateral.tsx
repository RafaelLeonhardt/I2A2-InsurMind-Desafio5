import {
  ArrowsLeftRightIcon,
  BookOpenTextIcon,
  CheckCircleIcon,
  CloudRainIcon,
  DatabaseIcon,
  HouseIcon,
  PaperPlaneTiltIcon,
  ShieldCheckIcon,
  UsersIcon,
} from '@phosphor-icons/react'
import {
  SUPERFICIES_TOPO_POR_PERFIL,
  type SuperficieTopo,
  usePerfilContexto,
} from '../contexto/PerfilContexto'

const ROTULOS: Record<SuperficieTopo['tipo'], string> = {
  prontidao: 'Prontidão',
  'restaurar-dados-sinteticos': 'Restaurar dados sintéticos',
  'documentacao-api': 'Documentação da API',
  eventos: 'Eventos climáticos',
  regras: 'Regras de negócio',
  segurados: 'Segurados',
  comunicacoes: 'Comunicações',
  'fontes-de-dados': 'Fontes de dados',
  'visao-geral': 'Visão geral',
}

function IconeSuperficie({ tipo }: { tipo: SuperficieTopo['tipo'] }) {
  if (tipo === 'prontidao') {
    return <CheckCircleIcon aria-hidden="true" size={21} />
  }
  if (tipo === 'restaurar-dados-sinteticos') {
    return <ArrowsLeftRightIcon aria-hidden="true" size={21} />
  }
  if (tipo === 'documentacao-api') {
    return <BookOpenTextIcon aria-hidden="true" size={21} />
  }
  if (tipo === 'eventos') {
    return <CloudRainIcon aria-hidden="true" size={21} />
  }
  if (tipo === 'regras') {
    return <ShieldCheckIcon aria-hidden="true" size={21} />
  }
  if (tipo === 'segurados') {
    return <UsersIcon aria-hidden="true" size={21} />
  }
  if (tipo === 'comunicacoes') {
    return <PaperPlaneTiltIcon aria-hidden="true" size={21} />
  }
  if (tipo === 'fontes-de-dados') {
    return <DatabaseIcon aria-hidden="true" size={21} />
  }
  return <HouseIcon aria-hidden="true" size={21} />
}

/** Navegação lateral: lista as superfícies de topo do perfil ativo e aciona `selecionarSuperficie`. */
export function NavegacaoLateral() {
  const { perfil, superficieAtiva, selecionarSuperficie } = usePerfilContexto()
  const superficies = SUPERFICIES_TOPO_POR_PERFIL[perfil]

  return (
    <nav className="navegacao" aria-label="Navegação principal">
      <div className="marca">
        <ShieldCheckIcon size={30} weight="fill" aria-hidden="true" />
        <span>Central Preventiva</span>
      </div>
      <ul>
        {superficies.map((superficie) => {
          const ativo = superficie.tipo === superficieAtiva.tipo
          return (
            <li key={superficie.tipo}>
              <button
                aria-current={ativo ? 'page' : undefined}
                className={ativo ? 'item-navegacao ativo' : 'item-navegacao'}
                onClick={() => selecionarSuperficie(superficie)}
                type="button"
              >
                <IconeSuperficie tipo={superficie.tipo} />
                {ROTULOS[superficie.tipo]}
              </button>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}
