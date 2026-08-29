import { CalendarDotsIcon, CloudRainIcon } from '@phosphor-icons/react'

/** Visão geral do perfil Segurado: alerta, ações preventivas e painel contextual. */
export function VisaoGeralSegurado() {
  return (
    <>
      <main className="conteudo" id="conteudo-principal" tabIndex={-1}>
        <p className="rotulo-contexto">Visão geral preventiva</p>
        <h1>Há chuva forte prevista para sua região.</h1>
        <p className="introducao">
          Este cenário demonstrativo ajuda você a entender o risco previsto e as medidas
          preventivas antes de um possível sinistro.
        </p>
        <section className="alerta-principal" aria-labelledby="titulo-alerta">
          <div className="icone-alerta" aria-hidden="true">
            <CloudRainIcon size={32} weight="fill" />
          </div>
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
        <div>
          <p className="rotulo-contexto">Contexto demonstrativo</p>
          <h2 id="titulo-contexto">Por que este alerta é relevante?</h2>
        </div>
        <dl>
          <div>
            <dt>Localização sintética</dt>
            <dd>Campinas (SP), CEP 13000-000</dd>
          </div>
          <div>
            <dt>Apólice demonstrativa</dt>
            <dd>AUTO-DEMO-001</dd>
          </div>
          <div>
            <dt>Regra aplicada</dt>
            <dd>Chuva intensa na região informada</dd>
          </div>
        </dl>
        <div className="nota-dados">
          <CalendarDotsIcon size={24} aria-hidden="true" />
          <p>
            <strong>Dados sintéticos</strong>
            <br />
            Informações criadas somente para demonstração.
          </p>
        </div>
      </aside>
    </>
  )
}
