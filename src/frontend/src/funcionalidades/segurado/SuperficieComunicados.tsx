import { useCallback, useEffect, useRef, useState } from 'react'
import { ErroContexto, getSeguradoPadrao } from '../../api/contexto'
import { ErroListaComunicados, getListaComunicados, type ItemComunicado } from '../../api/listaComunicados'
import { SuperficieComunicado } from './SuperficieComunicado'

type EstadoLista = 'carregando' | 'pronta' | 'erro'

type FalhaComunicados = {
  ocorrencia: string
  impacto: string
  proximaAcao: string
}

type PropriedadesSuperficieComunicados = {
  /** Segurado a exibir. Ausente hoje: resolve o segurado padrão internamente (mesmo seam de
   * SuperficieAlertas, 5.2 — 5.7 ainda não gerencia a troca). */
  seguradoId?: string
}

const ROTULOS_CANAL: Record<string, string> = {
  whatsapp: 'WhatsApp',
  email: 'E-mail',
  sms: 'SMS',
}

function rotuloCanal(canal: string): string {
  return ROTULOS_CANAL[canal] ?? canal
}

function rotuloEstado(item: ItemComunicado): string {
  return item.visualizacao ? 'Visualizada no portal' : 'Enviada — simulação'
}

function falhaDe(causa: unknown): FalhaComunicados {
  if (causa instanceof ErroListaComunicados || causa instanceof ErroContexto) {
    return { ocorrencia: causa.ocorrencia, impacto: causa.impacto, proximaAcao: causa.proximaAcao }
  }
  return {
    ocorrencia: 'Falha desconhecida ao consultar os comunicados.',
    impacto: 'A lista de comunicados pode estar desatualizada.',
    proximaAcao: 'Verifique se o backend local está disponível e tente novamente.',
  }
}

/**
 * Superfície "Comunicados" do perfil Segurado: lista completa e detalhe de cada comunicado
 * (COMUNICADOS-01..06, 5.5).
 *
 * O detalhe reusa `SuperficieComunicado` (4.3) sem alteração: conteúdo, prévia do canal e o
 * registro idempotente da primeira visualização continuam exatamente os mesmos, nunca
 * duplicados aqui — esta superfície só agrega a lista e a navegação entre lista e detalhe.
 */
export function SuperficieComunicados({ seguradoId }: PropriedadesSuperficieComunicados) {
  const [estadoLista, definirEstadoLista] = useState<EstadoLista>('carregando')
  const [itens, definirItens] = useState<ItemComunicado[]>([])
  const [falhaLista, definirFalhaLista] = useState<FalhaComunicados | null>(null)

  const [entregaSelecionada, definirEntregaSelecionada] = useState<string | null>(null)
  const [anuncio, definirAnuncio] = useState('')
  const [idSeguradoResolvido, definirIdSeguradoResolvido] = useState<string | null>(null)

  const botaoVoltarRef = useRef<HTMLButtonElement>(null)
  const ultimaSelecaoIdRef = useRef<string | null>(null)

  const carregarLista = useCallback(async () => {
    definirEstadoLista('carregando')
    definirFalhaLista(null)
    try {
      const idSegurado = seguradoId ?? (await getSeguradoPadrao()).id
      definirIdSeguradoResolvido(idSegurado)
      const encontrados = await getListaComunicados(idSegurado)
      definirItens(encontrados)
      definirEstadoLista('pronta')
    } catch (causa) {
      definirFalhaLista(falhaDe(causa))
      definirEstadoLista('erro')
    }
  }, [seguradoId])

  useEffect(() => {
    void carregarLista()
  }, [carregarLista])

  const abrirDetalhe = useCallback((entregaSimuladaId: string) => {
    ultimaSelecaoIdRef.current = entregaSimuladaId
    definirEntregaSelecionada(entregaSimuladaId)
    definirAnuncio('Comunicado selecionado. Mostrando detalhe.')
  }, [])

  useEffect(() => {
    if (entregaSelecionada !== null) {
      botaoVoltarRef.current?.focus()
    }
  }, [entregaSelecionada])

  useEffect(() => {
    if (entregaSelecionada === null && ultimaSelecaoIdRef.current !== null) {
      const idParaFocar = ultimaSelecaoIdRef.current
      ultimaSelecaoIdRef.current = null
      document.getElementById(`botao-detalhe-${idParaFocar}`)?.focus()
    }
  }, [entregaSelecionada, estadoLista])

  const voltarParaLista = useCallback(() => {
    definirEntregaSelecionada(null)
    definirAnuncio('')
  }, [])

  if (estadoLista === 'carregando') {
    return (
      <main className="conteudo" id="conteudo-principal" tabIndex={-1}>
        <p role="status">Carregando comunicados…</p>
      </main>
    )
  }

  if (estadoLista === 'erro') {
    return (
      <main className="conteudo" id="conteudo-principal" tabIndex={-1}>
        <div role="alert">
          <h1>Não foi possível carregar seus comunicados</h1>
          <p>
            <strong>Ocorrência:</strong> {falhaLista?.ocorrencia}
          </p>
          <p>
            <strong>Impacto:</strong> {falhaLista?.impacto}
          </p>
          <p>
            <strong>Próxima ação:</strong> {falhaLista?.proximaAcao}
          </p>
          <button onClick={() => void carregarLista()} type="button">
            Tentar novamente
          </button>
        </div>
      </main>
    )
  }

  if (entregaSelecionada !== null) {
    const idSegurado = seguradoId ?? idSeguradoResolvido ?? ''
    return (
      <>
        <p aria-live="polite" className="sr-only">
          {anuncio}
        </p>
        <button onClick={voltarParaLista} ref={botaoVoltarRef} type="button">
          Voltar à lista
        </button>
        <SuperficieComunicado entregaSimuladaId={entregaSelecionada} seguradoId={idSegurado} />
      </>
    )
  }

  if (itens.length === 0) {
    return (
      <main className="conteudo" id="conteudo-principal" tabIndex={-1}>
        <h1>Nenhum comunicado no momento</h1>
        <p className="introducao">
          Você ainda não tem nenhum comunicado simulado. Enquanto isso, você pode consultar
          Alertas, Apólice ou Meus Dados no menu lateral.
        </p>
        <button onClick={() => void carregarLista()} type="button">
          Atualizar
        </button>
      </main>
    )
  }

  return (
    <main className="conteudo" id="conteudo-principal" tabIndex={-1}>
      <h1>Seus comunicados</h1>
      <table>
        <caption className="sr-only">Lista de comunicados simulados</caption>
        <thead>
          <tr>
            <th scope="col">Canal</th>
            <th scope="col">Assunto ou resumo</th>
            <th scope="col">Data</th>
            <th scope="col">Estado</th>
            <th scope="col">Seleção</th>
          </tr>
        </thead>
        <tbody>
          {itens.map((item) => (
            <tr key={item.entregaSimuladaId}>
              <td>{rotuloCanal(item.canal)}</td>
              <td>{item.assuntoOuResumo}</td>
              <td>{item.criadoEm}</td>
              <td>{rotuloEstado(item)}</td>
              <td>
                <button
                  id={`botao-detalhe-${item.entregaSimuladaId}`}
                  onClick={() => abrirDetalhe(item.entregaSimuladaId)}
                  type="button"
                >
                  Ver detalhe
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  )
}
