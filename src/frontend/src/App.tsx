import {
  BellRingingIcon,
  CalendarDotsIcon,
  CloudRainIcon,
  HouseIcon,
  IdentificationCardIcon,
  ShieldCheckIcon,
} from '@phosphor-icons/react'
import { type MouseEvent, useEffect, useState } from 'react'
import './App.css'

const itensNavegacao = [
  { rotulo: 'Visão geral', Icone: HouseIcon, ativo: true, destino: 'conteudo-principal' },
  { rotulo: 'Alertas', Icone: BellRingingIcon, ativo: false, destino: 'titulo-alerta' },
  { rotulo: 'Minha apólice', Icone: IdentificationCardIcon, ativo: false, destino: 'titulo-contexto' },
]

function focarConteudoPrincipal(evento: MouseEvent<HTMLAnchorElement>) {
  evento.preventDefault()
  const conteudo = document.getElementById('conteudo-principal')
  conteudo?.focus()
  window.history.replaceState(null, '', '#conteudo-principal')
}

/** Exibe a shell estática e educacional da Central Preventiva. */
function App() {
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
      <nav className="navegacao" aria-label="Navegação principal">
        <div className="marca">
          <ShieldCheckIcon size={30} weight="fill" aria-hidden="true" />
          <span>Central Preventiva</span>
        </div>
        <p className="rotulo-contexto">Área do segurado</p>
        <ul>
          {itensNavegacao.map(({ rotulo, Icone, ativo, destino }) => (
            <li key={rotulo}>
              <a
                aria-current={ativo ? 'page' : undefined}
                className={ativo ? 'item-navegacao ativo' : 'item-navegacao'}
                data-rotulo={rotulo}
                href={`#${destino}`}
              >
                <Icone size={21} aria-hidden="true" />
                {rotulo}
              </a>
            </li>
          ))}
        </ul>
        <div className="selo-lateral">
          <CloudRainIcon size={26} aria-hidden="true" />
          <strong>Ambiente educacional</strong>
          <span>Nenhuma ação afeta sistemas reais.</span>
        </div>
      </nav>
      <header className="barra-contexto">
        <div><span className="rotulo-contexto">Perfil de acesso</span><strong>Segurado</strong></div>
        <div><span className="rotulo-contexto">Segurado ativo</span><strong>Marina Costa — perfil sintético</strong></div>
        <div><span className="rotulo-contexto">Data e hora de referência</span><strong>28 ago 2026, 10:30</strong></div>
      </header>
      <main id="conteudo-principal" className="conteudo" tabIndex={-1}>
        {viewportNaoSuportado && (
          <div className="aviso-responsivo" role="note">
            Para uma visualização mais confortável, use uma tela com pelo menos 1024 px. Todas as funções permanecem disponíveis.
          </div>
        )}
        <p className="rotulo-contexto">Visão geral preventiva</p>
        <h1>Olá, Marina. Há chuva forte prevista para sua região.</h1>
        <p className="introducao">Este cenário demonstrativo ajuda você a entender o risco previsto e as medidas preventivas antes de um possível sinistro.</p>
        <section className="alerta-principal" aria-labelledby="titulo-alerta">
          <div className="icone-alerta" aria-hidden="true"><CloudRainIcon size={32} weight="fill" /></div>
          <div>
            <span className="nivel-risco">Atenção · risco alto</span>
            <h2 id="titulo-alerta">Chuva intensa e rajadas de vento</h2>
            <p>Previsto entre 28 ago, 18:00 e 29 ago, 06:00 em Campinas (SP).</p>
          </div>
        </section>
        <section aria-labelledby="titulo-acoes">
          <h2 id="titulo-acoes">Como se prevenir</h2>
          <ul className="acoes-preventivas">
            <li>Evite estacionar o veículo próximo a árvores e estruturas frágeis.</li>
            <li>Recolha objetos soltos de áreas externas antes do período previsto.</li>
            <li>Acompanhe as atualizações oficiais da Defesa Civil da sua região.</li>
          </ul>
        </section>
      </main>
      <aside className="painel-contextual" aria-labelledby="titulo-contexto">
        <div><p className="rotulo-contexto">Contexto demonstrativo</p><h2 id="titulo-contexto">Por que este alerta é relevante?</h2></div>
        <dl>
          <div><dt>Localização sintética</dt><dd>Campinas (SP), CEP 13000-000</dd></div>
          <div><dt>Apólice demonstrativa</dt><dd>AUTO-DEMO-001</dd></div>
          <div><dt>Regra aplicada</dt><dd>Chuva intensa na região informada</dd></div>
        </dl>
        <div className="nota-dados">
          <CalendarDotsIcon size={24} aria-hidden="true" />
          <p><strong>Dados sintéticos</strong><br />Informações criadas somente para demonstração.</p>
        </div>
      </aside>
      <footer className="faixa-simulacao">
        <span><strong>Dados sintéticos</strong> · Ambiente educacional</span>
        <span><strong>Sem envio real</strong> · Simulação local</span>
      </footer>
    </div>
  )
}

export default App
