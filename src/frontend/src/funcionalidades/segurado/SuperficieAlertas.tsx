import {
  CalendarDotsIcon,
  ClockCounterClockwiseIcon,
  DatabaseIcon,
  FlaskIcon,
  HourglassIcon,
  MapPinIcon,
  WarningIcon,
} from '@phosphor-icons/react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { ErroContexto, getSeguradoPadrao } from '../../api/contexto'
import {
  type ClassificacaoAlerta,
  type DetalheAlerta,
  ErroListaAlertas,
  getDetalheAlerta,
  getListaAlertas,
  type ItemAlerta,
} from '../../api/listaAlertasSegurado'
import { SuperficieExplicacaoComunicado } from './SuperficieExplicacaoComunicado'

type EstadoLista = 'carregando' | 'pronta' | 'erro'
type EstadoDetalhe = 'carregando' | 'pronto' | 'nao_encontrado' | 'erro'

type FalhaAlertas = {
  ocorrencia: string
  impacto: string
  proximaAcao: string
}

type PropriedadesSuperficieAlertas = {
  /** Segurado a exibir. Ausente hoje: resolve o segurado padrão internamente (mesmo
   * seam de VisaoGeralSegurado, 5.1 — 5.7 ainda não gerencia a troca). */
  seguradoId?: string
  /** Abre direto no detalhe deste alerta, simulando acesso direto ao endereço
   * (ALERTAS-05, Independent Test) — sem ele, a superfície abre na lista. */
  elegibilidadeIdInicial?: string
  /** Quando true, renderiza como `<section>` sem `id`/foco próprios em vez de `<main>`
   * (5.7, `PainelSegurado`): evita landmark e id duplicados ao compor esta superfície
   * junto de outras na mesma página. Ausente/false preserva o comportamento original. */
  comoSecao?: boolean
}

const ROTULOS_EVENTO: Record<string, string> = {
  chuva_intensa: 'Chuva intensa',
  granizo: 'Granizo',
}

const ROTULOS_ORIGEM: Record<string, string> = {
  real_inmet: 'Observação real (INMET)',
  sintetico: 'Cenário demonstrativo (sintético)',
}

const ROTULOS_CLASSIFICACAO: Record<ClassificacaoAlerta, string> = {
  ativo: 'Ativo',
  anterior: 'Anterior',
  ainda_nao_simulado: 'Ainda não simulado',
}

function rotuloEvento(tipo: string): string {
  return ROTULOS_EVENTO[tipo] ?? tipo
}

function rotuloOrigem(origem: string): string {
  return ROTULOS_ORIGEM[origem] ?? origem
}

function IconeClassificacao({ classificacao }: { classificacao: ClassificacaoAlerta }) {
  if (classificacao === 'ativo') {
    return (
      <WarningIcon aria-hidden="true" data-icone-nome="warning" size={16} weight="fill" />
    )
  }
  if (classificacao === 'ainda_nao_simulado') {
    return <HourglassIcon aria-hidden="true" data-icone-nome="hourglass" size={16} />
  }
  return (
    <ClockCounterClockwiseIcon
      aria-hidden="true"
      data-icone-nome="clock-counter-clockwise"
      size={16}
    />
  )
}

const TONS_CLASSIFICACAO: Record<ClassificacaoAlerta, 'alto' | 'medio' | 'neutro'> = {
  ativo: 'alto',
  ainda_nao_simulado: 'medio',
  anterior: 'neutro',
}

function falhaDe(causa: unknown): FalhaAlertas {
  if (causa instanceof ErroListaAlertas || causa instanceof ErroContexto) {
    return { ocorrencia: causa.ocorrencia, impacto: causa.impacto, proximaAcao: causa.proximaAcao }
  }
  return {
    ocorrencia: 'Falha desconhecida ao consultar os alertas.',
    impacto: 'A lista de alertas pode estar desatualizada.',
    proximaAcao: 'Verifique se o backend local está disponível e tente novamente.',
  }
}

/**
 * Superfície "Alertas" do perfil Segurado: lista completa (ativos e anteriores) e
 * detalhe de cada alerta (ALERTAS-01..06, 5.2).
 *
 * Não existe nenhum componente de mapa no projeto (mesma decisão de 2.1) — a "equivalência
 * de mapa e lista" do AC é satisfeita porque a única representação é a lista/tabela
 * acessível, operável por teclado e leitor de tela desde o início.
 */
export function SuperficieAlertas({
  seguradoId,
  elegibilidadeIdInicial,
  comoSecao,
}: PropriedadesSuperficieAlertas) {
  const ElementoRaiz: 'main' | 'section' = comoSecao ? 'section' : 'main'
  const atributosRaiz = comoSecao ? {} : { id: 'conteudo-principal', tabIndex: -1 }
  const [estadoLista, definirEstadoLista] = useState<EstadoLista>('carregando')
  const [itens, definirItens] = useState<ItemAlerta[]>([])
  const [falhaLista, definirFalhaLista] = useState<FalhaAlertas | null>(null)

  const [elegibilidadeSelecionada, definirElegibilidadeSelecionada] = useState<string | null>(
    elegibilidadeIdInicial ?? null,
  )
  const [estadoDetalhe, definirEstadoDetalhe] = useState<EstadoDetalhe>('carregando')
  const [detalhe, definirDetalhe] = useState<DetalheAlerta | null>(null)
  const [falhaDetalhe, definirFalhaDetalhe] = useState<FalhaAlertas | null>(null)
  const [anuncio, definirAnuncio] = useState('')
  const [explicacaoAberta, definirExplicacaoAberta] = useState(false)

  const idSeguradoResolvidoRef = useRef<string | null>(null)
  const tituloDetalheRef = useRef<HTMLHeadingElement>(null)
  const ultimaSelecaoIdRef = useRef<string | null>(null)
  const requisicaoListaAtualRef = useRef(0)

  const carregarLista = useCallback(async () => {
    const requisicao = ++requisicaoListaAtualRef.current
    definirEstadoLista('carregando')
    definirFalhaLista(null)
    try {
      const idSegurado = seguradoId ?? (await getSeguradoPadrao()).id
      const encontrados = await getListaAlertas(idSegurado)
      // Uma requisição mais recente já pode ter chegado primeiro (troca de segurado
      // rápida, 5.7) — nunca sobrescrever a lista do segurado novo com a do anterior.
      if (requisicao !== requisicaoListaAtualRef.current) return
      idSeguradoResolvidoRef.current = idSegurado
      definirItens(encontrados)
      definirEstadoLista('pronta')
    } catch (causa) {
      if (requisicao !== requisicaoListaAtualRef.current) return
      definirFalhaLista(falhaDe(causa))
      definirEstadoLista('erro')
    }
  }, [seguradoId])

  useEffect(() => {
    void carregarLista()
  }, [carregarLista])

  const abrirDetalhe = useCallback(
    async (elegibilidadeId: string) => {
      ultimaSelecaoIdRef.current = elegibilidadeId
      definirElegibilidadeSelecionada(elegibilidadeId)
      definirEstadoDetalhe('carregando')
      definirFalhaDetalhe(null)
      definirAnuncio('Alerta selecionado. Mostrando detalhe.')
      try {
        const idSegurado = idSeguradoResolvidoRef.current ?? seguradoId ?? (await getSeguradoPadrao()).id
        idSeguradoResolvidoRef.current = idSegurado
        const encontrado = await getDetalheAlerta(idSegurado, elegibilidadeId)
        definirDetalhe(encontrado)
        definirEstadoDetalhe('pronto')
      } catch (causa) {
        if (causa instanceof ErroListaAlertas && causa.status === 404) {
          definirEstadoDetalhe('nao_encontrado')
          return
        }
        definirFalhaDetalhe(falhaDe(causa))
        definirEstadoDetalhe('erro')
      }
    },
    [seguradoId],
  )

  useEffect(() => {
    if (elegibilidadeIdInicial) {
      void abrirDetalhe(elegibilidadeIdInicial)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (elegibilidadeSelecionada !== null) {
      tituloDetalheRef.current?.focus()
    }
  }, [elegibilidadeSelecionada, estadoDetalhe])

  useEffect(() => {
    if (elegibilidadeSelecionada === null && ultimaSelecaoIdRef.current !== null) {
      const idParaFocar = ultimaSelecaoIdRef.current
      ultimaSelecaoIdRef.current = null
      document.getElementById(`botao-detalhe-${idParaFocar}`)?.focus()
    }
  }, [elegibilidadeSelecionada, estadoLista])

  const voltarParaLista = useCallback(() => {
    definirElegibilidadeSelecionada(null)
    definirDetalhe(null)
    definirAnuncio('')
    definirExplicacaoAberta(false)
  }, [])

  // Trocar de segurado ativo (5.7) nunca deve deixar a explicação de um segurado anterior
  // aberta sobre o contexto do novo (Edge Case da spec de 6.8).
  useEffect(() => {
    definirExplicacaoAberta(false)
  }, [seguradoId])

  if (estadoLista === 'carregando') {
    return (
      <ElementoRaiz className="conteudo" {...atributosRaiz}>
        <p className="caixa-status" role="status">
          Carregando alertas…
        </p>
      </ElementoRaiz>
    )
  }

  if (estadoLista === 'erro') {
    return (
      <ElementoRaiz className="conteudo" {...atributosRaiz}>
        <div className="caixa-status" role="alert">
          <h1>Não foi possível carregar seus alertas</h1>
          <p>
            <strong>Ocorrência:</strong> {falhaLista?.ocorrencia}
          </p>
          <p>
            <strong>Impacto:</strong> {falhaLista?.impacto}
          </p>
          <p>
            <strong>Próxima ação:</strong> {falhaLista?.proximaAcao}
          </p>
          <button className="btn secondary" onClick={() => void carregarLista()} type="button">
            Tentar novamente
          </button>
        </div>
      </ElementoRaiz>
    )
  }

  if (elegibilidadeSelecionada !== null) {
    return (
      <ElementoRaiz className="conteudo" {...atributosRaiz}>
        <p aria-live="polite" className="sr-only">
          {anuncio}
        </p>
        <button className="btn secondary" onClick={voltarParaLista} type="button">
          Voltar à lista
        </button>

        {estadoDetalhe === 'carregando' && (
          <p className="caixa-status" role="status">
            Carregando detalhe…
          </p>
        )}

        {estadoDetalhe === 'nao_encontrado' && (
          <div className="caixa-status" role="alert">
            <h1 ref={tituloDetalheRef} tabIndex={-1}>
              Não encontrado
            </h1>
            <p>Este alerta não existe ou não pertence a você.</p>
          </div>
        )}

        {estadoDetalhe === 'erro' && (
          <div className="caixa-status" role="alert">
            <h1 ref={tituloDetalheRef} tabIndex={-1}>
              Não foi possível carregar o detalhe
            </h1>
            <p>
              <strong>Ocorrência:</strong> {falhaDetalhe?.ocorrencia}
            </p>
            <p>
              <strong>Impacto:</strong> {falhaDetalhe?.impacto}
            </p>
            <p>
              <strong>Próxima ação:</strong> {falhaDetalhe?.proximaAcao}
            </p>
          </div>
        )}

        {estadoDetalhe === 'pronto' && detalhe && (
          <>
            <h1 ref={tituloDetalheRef} tabIndex={-1}>
              {rotuloEvento(detalhe.alerta.eventoTipo)}
            </h1>
            <p className="nivel-risco badge" data-tom={TONS_CLASSIFICACAO[detalhe.classificacao]}>
              <IconeClassificacao classificacao={detalhe.classificacao} />
              {ROTULOS_CLASSIFICACAO[detalhe.classificacao]}
            </p>

            {detalhe.classificacao === 'ainda_nao_simulado' && (
              <p className="caixa-status" role="status">
                Ainda não simulado — nenhum comunicado foi produzido para este alerta.
              </p>
            )}

            <dl>
              <div className="cartao-contexto">
                <i aria-hidden="true">
                  {detalhe.alerta.origem === 'sintetico' ? (
                    <FlaskIcon size={22} weight="fill" />
                  ) : (
                    <DatabaseIcon size={22} />
                  )}
                </i>
                <div>
                  <dt>Origem</dt>
                  <dd>{rotuloOrigem(detalhe.alerta.origem)}</dd>
                </div>
              </div>
              <div className="cartao-contexto">
                <i aria-hidden="true">
                  <CalendarDotsIcon size={22} />
                </i>
                <div>
                  <dt>Período</dt>
                  <dd>
                    {detalhe.alerta.periodoInicio} a {detalhe.alerta.periodoFim}
                  </dd>
                </div>
              </div>
              <div className="cartao-contexto">
                <i aria-hidden="true">
                  <MapPinIcon size={22} />
                </i>
                <div>
                  <dt>Localização</dt>
                  <dd>{detalhe.alerta.localizacao}</dd>
                </div>
              </div>
            </dl>

            <section aria-labelledby="titulo-impactos-alerta" className="secao-alerta">
              <h2 id="titulo-impactos-alerta">Impactos esperados</h2>
              <ul className="grade-icones">
                {detalhe.alerta.impactosEsperados.map((impacto) => (
                  <li key={impacto}>{impacto}</li>
                ))}
              </ul>
            </section>

            <section aria-labelledby="titulo-recomendacoes-alerta" className="secao-alerta">
              <h2 id="titulo-recomendacoes-alerta">Recomendações</h2>
              <ul className="lista-marcada">
                {detalhe.alerta.recomendacoes.map((recomendacao) => (
                  <li key={recomendacao}>{recomendacao}</li>
                ))}
              </ul>
            </section>

            <section aria-labelledby="titulo-contexto-apolice" className="secao-alerta">
              <h2 id="titulo-contexto-apolice">Contexto da apólice</h2>
              <p>{detalhe.justificativa}</p>
            </section>

            <section aria-labelledby="titulo-linha-do-tempo-alerta" className="secao-alerta">
              <h2 id="titulo-linha-do-tempo-alerta">Linha do tempo</h2>
              {detalhe.linhaDoTempo.length === 0 ? (
                <p>Nenhum marco disponível para este alerta.</p>
              ) : (
                <ul className="linha-do-tempo">
                  {detalhe.linhaDoTempo.map((marco, indice) => (
                    <li key={`${marco.timestamp}-${indice}`}>
                      {marco.timestamp} — {marco.acao}: {marco.resultado}
                    </li>
                  ))}
                </ul>
              )}
            </section>

            {detalhe.alerta.entregaSimuladaId && (
              <button
                className="btn secondary"
                id={`botao-explicacao-${detalhe.alerta.elegibilidadeId}`}
                onClick={() => definirExplicacaoAberta(true)}
                type="button"
              >
                Ver como esta mensagem foi criada
              </button>
            )}
          </>
        )}

        {detalhe?.alerta.entregaSimuladaId && (
          <SuperficieExplicacaoComunicado
            aberto={explicacaoAberta}
            entregaSimuladaId={detalhe.alerta.entregaSimuladaId}
            onFechar={() => definirExplicacaoAberta(false)}
            seguradoId={idSeguradoResolvidoRef.current ?? seguradoId ?? ''}
          />
        )}
      </ElementoRaiz>
    )
  }

  if (itens.length === 0) {
    return (
      <ElementoRaiz className="conteudo" {...atributosRaiz}>
        <h1>Nenhum alerta no momento</h1>
        <p className="introducao">Você ainda não tem nenhum alerta ativo ou anterior.</p>
        <button className="btn secondary" onClick={() => void carregarLista()} type="button">
          Atualizar
        </button>
      </ElementoRaiz>
    )
  }

  return (
    <ElementoRaiz className="conteudo" {...atributosRaiz}>
      <h1>Seus alertas</h1>
      <table className="tabela">
        <caption className="sr-only">Lista de alertas ativos e anteriores</caption>
        <thead>
          <tr>
            <th scope="col">Evento</th>
            <th scope="col">Severidade</th>
            <th scope="col">Período</th>
            <th scope="col">Localização</th>
            <th scope="col">Origem</th>
            <th scope="col">Estado</th>
            <th scope="col">Seleção</th>
          </tr>
        </thead>
        <tbody>
          {itens.map((item) => (
            <tr key={item.alerta.elegibilidadeId}>
              <td>{rotuloEvento(item.alerta.eventoTipo)}</td>
              <td>{item.alerta.severidade}</td>
              <td>
                {item.alerta.periodoInicio} a {item.alerta.periodoFim}
              </td>
              <td>{item.alerta.localizacao}</td>
              <td>{rotuloOrigem(item.alerta.origem)}</td>
              <td>
                <span className="nivel-risco badge" data-tom={TONS_CLASSIFICACAO[item.classificacao]}>
                  <IconeClassificacao classificacao={item.classificacao} />
                  {ROTULOS_CLASSIFICACAO[item.classificacao]}
                </span>
              </td>
              <td>
                <button
                  className="btn secondary"
                  id={`botao-detalhe-${item.alerta.elegibilidadeId}`}
                  onClick={() => void abrirDetalhe(item.alerta.elegibilidadeId)}
                  type="button"
                >
                  Ver detalhe
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </ElementoRaiz>
  )
}
