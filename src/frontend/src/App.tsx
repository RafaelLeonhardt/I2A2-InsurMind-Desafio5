import { type MouseEvent, useEffect, useState } from 'react'
import './App.css'
import { BarraContexto } from './componentes/BarraContexto'
import { ContextoInconsistente } from './componentes/ContextoInconsistente'
import { FaixaDemonstracao } from './componentes/FaixaDemonstracao'
import { NavegacaoLateral } from './componentes/NavegacaoLateral'
import { PerfilProvider, SUPERFICIES_TOPO_POR_PERFIL, usePerfilContexto } from './contexto/PerfilContexto'
import { RestaurarDemonstracao } from './funcionalidades/dados-sinteticos/RestaurarDemonstracao'
import { SuperficieDocumentacaoApi } from './funcionalidades/documentacao-api/SuperficieDocumentacaoApi'
import { SuperficieEventos } from './funcionalidades/eventos/SuperficieEventos'
import { SuperficieExecucao } from './funcionalidades/execucao/SuperficieExecucao'
import { SuperficieFonteMeteorologica } from './funcionalidades/fonte-meteorologica/SuperficieFonteMeteorologica'
import { SuperficieProntidao } from './funcionalidades/prontidao/SuperficieProntidao'
import { SuperficieRegras } from './funcionalidades/regras/SuperficieRegras'
import { PainelSegurado } from './funcionalidades/segurado/PainelSegurado'

/** Placeholder das superfícies de negócio do admin ainda não implementadas (Histórias 6.4–6.5). */
function EmConstrucao({ titulo }: { titulo: string }) {
  return (
    <main className="conteudo" id="conteudo-principal" tabIndex={-1}>
      <h1>{titulo}</h1>
      <p>Em construção — ver Histórias 6.2–6.7.</p>
    </main>
  )
}

function focarConteudoPrincipal(evento: MouseEvent<HTMLAnchorElement>) {
  evento.preventDefault()
  const conteudo = document.getElementById('conteudo-principal')
  conteudo?.focus()
  window.history.replaceState(null, '', '#conteudo-principal')
}

/** Renderiza a superfície ativa do perfil corrente, ou o bloqueio de contexto inconsistente. */
export function SuperficieAtiva() {
  const { perfil, superficieAtiva, superficieValida, selecionarSuperficie } = usePerfilContexto()

  if (!superficieValida) {
    return (
      <ContextoInconsistente
        perfil={perfil}
        aoVoltar={() => selecionarSuperficie(SUPERFICIES_TOPO_POR_PERFIL[perfil][0])}
      />
    )
  }

  switch (superficieAtiva.tipo) {
    case 'prontidao':
      return <SuperficieProntidao />
    case 'restaurar-dados-sinteticos':
      return <RestaurarDemonstracao />
    case 'documentacao-api':
      return <SuperficieDocumentacaoApi />
    case 'visao-geral':
      return <PainelSegurado />
    case 'evento-execucao':
      return <SuperficieExecucao execucaoId={superficieAtiva.execucaoId} />
    case 'eventos':
      return <SuperficieEventos />
    case 'regras':
      return <SuperficieRegras />
    case 'segurados':
      return <EmConstrucao titulo="Segurados" />
    case 'comunicacoes':
      return <EmConstrucao titulo="Comunicações" />
    case 'fontes-de-dados':
      return <SuperficieFonteMeteorologica />
  }
}

function ShellDemonstrativo() {
  const [viewportNaoSuportado, setViewportNaoSuportado] = useState(() => window.innerWidth < 1024)

  useEffect(() => {
    const atualizarViewport = () => setViewportNaoSuportado(window.innerWidth < 1024)
    window.addEventListener('resize', atualizarViewport)
    return () => window.removeEventListener('resize', atualizarViewport)
  }, [])

  return (
    <div className="aplicacao">
      <a className="pular-conteudo" href="#conteudo-principal" onClick={focarConteudoPrincipal}>
        Pular para o conteúdo principal
      </a>
      <NavegacaoLateral />
      <BarraContexto />
      {viewportNaoSuportado && (
        <div className="aviso-responsivo" role="note">
          Para uma visualização mais confortável, use uma tela com pelo menos 1024 px. Todas as
          funções permanecem disponíveis.
        </div>
      )}
      <SuperficieAtiva />
      <FaixaDemonstracao />
    </div>
  )
}

/** Shell real da Central Preventiva: contexto demonstrativo, navegação por perfil e superfícies. */
function App() {
  return (
    <PerfilProvider>
      <ShellDemonstrativo />
    </PerfilProvider>
  )
}

export default App
