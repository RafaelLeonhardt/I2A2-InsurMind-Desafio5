import {
  ArrowClockwiseIcon,
  CheckCircleIcon,
  CircleNotchIcon,
  FlaskIcon,
  WarningIcon,
  XCircleIcon,
} from '@phosphor-icons/react'
import { useEffect, useState } from 'react'
import {
  ativarCenarioSintetico,
  ErroMeteorologia,
  type EventoMeteorologico,
  getEventos,
  getSincronizacoes,
  type HistoricoSincronizacoes,
  IDENTIFICADOR_CENARIO_GRANIZO,
  solicitarNovaTentativa,
} from '../../api/meteorologia'
import './SuperficieFonteMeteorologica.css'

type EstadoCarregamento = 'carregando' | 'disponivel' | 'indisponivel'

/**
 * Os seis estados visíveis da fonte meteorológica (RESIL-15), derivados só de dados já
 * persistidos (`GET /eventos` + `GET /sincronizacoes`) — nunca inferidos de suposições:
 *
 * - `em_tentativa`: a última sincronização ainda está `coletando` (RESIL-05).
 * - `indisponivel`: a última sincronização esgotou as tentativas (`falha`, RESIL-09).
 * - `sintetica`: o evento mais recente tem proveniência `sintetico` (RESIL-13).
 * - `recuperada`: a última sincronização concluiu com sucesso logo após uma que falhou
 *   (RESIL-14) — um instante depois vira `operacional` de novo.
 * - `degradada`: a última sincronização concluiu, mas precisou de mais de uma tentativa.
 * - `operacional`: nenhuma das condições acima — inclui "nenhuma coleta ainda".
 */
export type EstadoFonte =
  | 'operacional'
  | 'em_tentativa'
  | 'degradada'
  | 'indisponivel'
  | 'sintetica'
  | 'recuperada'

export function calcularEstadoFonte(
  historico: HistoricoSincronizacoes,
  eventos: EventoMeteorologico[],
): EstadoFonte {
  const ultima = historico.ultimaTentativa
  if (ultima === null) return 'operacional'
  if (ultima.estado === 'coletando') return 'em_tentativa'
  if (ultima.estado === 'falha') return 'indisponivel'

  if (eventos[0]?.proveniencia === 'sintetico') return 'sintetica'

  const anterior = historico.resultadosAnteriores[1]
  if (anterior?.estado === 'falha') return 'recuperada'

  if (ultima.tentativas.length > 1) return 'degradada'

  return 'operacional'
}

const ROTULOS_ESTADO_FONTE: Record<EstadoFonte, string> = {
  operacional: 'Operacional',
  em_tentativa: 'Em tentativa',
  degradada: 'Degradada',
  indisponivel: 'Indisponível',
  sintetica: 'Sintética',
  recuperada: 'Recuperada',
}

function IconeEstadoFonte({ estado }: { estado: EstadoFonte }) {
  if (estado === 'operacional') return <CheckCircleIcon aria-hidden="true" size={18} weight="fill" />
  if (estado === 'em_tentativa') return <CircleNotchIcon aria-hidden="true" size={18} />
  if (estado === 'degradada') return <WarningIcon aria-hidden="true" size={18} weight="fill" />
  if (estado === 'indisponivel') return <XCircleIcon aria-hidden="true" size={18} weight="fill" />
  if (estado === 'sintetica') return <FlaskIcon aria-hidden="true" size={18} weight="fill" />
  return <ArrowClockwiseIcon aria-hidden="true" size={18} weight="fill" />
}

const ROTULOS_TIPO: Record<string, string> = {
  chuva_intensa: 'Chuva intensa',
  granizo: 'Granizo',
}

const ROTULOS_ORIGEM_EVENTO: Record<string, string> = {
  real_inmet: 'INMET (real)',
  sintetico: 'Sintético',
}

const ROTULOS_ORIGEM_SINCRONIZACAO: Record<string, string> = {
  automatica: 'Automática',
  manual: 'Manual',
}

const ROTULOS_ESTADO_SINCRONIZACAO: Record<string, string> = {
  coletando: 'Coletando',
  normalizando: 'Normalizando',
  concluido: 'Concluído',
  falha: 'Falha',
}

/**
 * Superfície "Fonte meteorológica": eventos normalizados, histórico de sincronização e o
 * estado atual da fonte, com ações seguras de contingência por estado (RESIL-15, RESIL-16).
 *
 * A seleção de um evento é feita por uma lista/tabela operável por teclado e leitor de
 * tela (botão nativo por linha), sem depender de um mapa (fora do MVP — spec.md).
 */
export function SuperficieFonteMeteorologica() {
  const [estado, definirEstado] = useState<EstadoCarregamento>('carregando')
  const [eventos, definirEventos] = useState<EventoMeteorologico[]>([])
  const [historico, definirHistorico] = useState<HistoricoSincronizacoes | null>(null)
  const [falha, definirFalha] = useState<ErroMeteorologia | null>(null)
  const [idSelecionado, definirIdSelecionado] = useState<string | null>(null)
  const [executandoAcao, definirExecutandoAcao] = useState(false)
  const [falhaAcao, definirFalhaAcao] = useState<ErroMeteorologia | null>(null)
  const [versaoConsulta, definirVersaoConsulta] = useState(0)

  useEffect(() => {
    let cancelado = false
    definirEstado('carregando')

    Promise.all([getEventos(), getSincronizacoes()])
      .then(([eventosResultado, historicoResultado]) => {
        if (cancelado) return
        definirEventos(eventosResultado)
        definirHistorico(historicoResultado)
        definirFalha(null)
        definirEstado('disponivel')
      })
      .catch((causa: unknown) => {
        if (cancelado) return
        definirFalha(causa instanceof ErroMeteorologia ? causa : null)
        definirEstado('indisponivel')
      })

    return () => {
      cancelado = true
    }
  }, [versaoConsulta])

  async function executarAcao(acao: () => Promise<unknown>) {
    definirExecutandoAcao(true)
    definirFalhaAcao(null)
    try {
      await acao()
      definirVersaoConsulta((atual) => atual + 1)
    } catch (causa) {
      definirFalhaAcao(causa instanceof ErroMeteorologia ? causa : null)
    } finally {
      definirExecutandoAcao(false)
    }
  }

  const estadoFonte = historico ? calcularEstadoFonte(historico, eventos) : null

  return (
    <main className="conteudo" id="conteudo-principal" tabIndex={-1}>
      <p className="rotulo-contexto">Fonte meteorológica</p>
      <h1>Fonte meteorológica</h1>
      <p className="introducao">
        Eventos meteorológicos normalizados do INMET e o histórico de sincronização, com uma
        lista operável por teclado e leitor de tela equivalente à seleção por mapa.
      </p>

      {estado === 'carregando' && <p role="status">Carregando eventos meteorológicos…</p>}

      {estado === 'indisponivel' && (
        <div role="alert">
          <p>
            <strong>Indisponível</strong>
          </p>
          <p>
            <strong>Ocorrência:</strong>{' '}
            {falha?.ocorrencia ?? 'Falha desconhecida ao consultar a fonte meteorológica.'}
          </p>
          <p>
            <strong>Impacto:</strong> {falha?.impacto ?? ''}
          </p>
          <p>
            <strong>Próxima ação:</strong> {falha?.proximaAcao ?? ''}
          </p>
        </div>
      )}

      {estado === 'disponivel' && historico && estadoFonte && (
        <>
          <section aria-labelledby="titulo-estado-fonte">
            <h2 id="titulo-estado-fonte">Estado da fonte</h2>
            <p
              className={`estado-fonte-badge estado-fonte-badge--${estadoFonte}`}
              data-icone={estadoFonte}
            >
              <IconeEstadoFonte estado={estadoFonte} />
              {ROTULOS_ESTADO_FONTE[estadoFonte]}
            </p>
            {estadoFonte === 'em_tentativa' && historico.ultimaTentativa && (
              <p>
                Tentativa {historico.ultimaTentativa.tentativas.length + 1} de{' '}
                {historico.ultimaTentativa.limiteTentativas}
              </p>
            )}
            <div className="acoes-fonte-meteorologica">
              {(estadoFonte === 'indisponivel' || estadoFonte === 'sintetica') &&
                historico.ultimaTentativa && (
                  <button
                    disabled={executandoAcao}
                    onClick={() =>
                      executarAcao(() => solicitarNovaTentativa(historico.ultimaTentativa!.id))
                    }
                    type="button"
                  >
                    {executandoAcao ? 'Solicitando…' : 'Solicitar nova tentativa'}
                  </button>
                )}
              {estadoFonte === 'indisponivel' && historico.ultimaTentativa && (
                <button
                  disabled={executandoAcao}
                  onClick={() =>
                    executarAcao(() =>
                      ativarCenarioSintetico(
                        IDENTIFICADOR_CENARIO_GRANIZO,
                        historico.ultimaTentativa!.areaMonitoradaId,
                      ),
                    )
                  }
                  type="button"
                >
                  {executandoAcao ? 'Ativando…' : 'Ativar cenário sintético'}
                </button>
              )}
            </div>
            {falhaAcao && (
              <p role="alert">
                {falhaAcao.ocorrencia} {falhaAcao.proximaAcao}
              </p>
            )}
          </section>

          <section aria-labelledby="titulo-eventos-meteorologicos">
            <h2 id="titulo-eventos-meteorologicos">Eventos meteorológicos</h2>
            {eventos.length === 0 ? (
              <p>Nenhum evento meteorológico normalizado até o momento.</p>
            ) : (
              <table className="tabela-eventos-meteorologicos">
                <caption className="sr-only">
                  Eventos meteorológicos normalizados, com seleção operável por teclado
                </caption>
                <thead>
                  <tr>
                    <th scope="col">Tipo</th>
                    <th scope="col">Local</th>
                    <th scope="col">Período</th>
                    <th scope="col">Intensidade</th>
                    <th scope="col">Origem</th>
                    <th scope="col">Horário</th>
                    <th scope="col">Seleção</th>
                  </tr>
                </thead>
                <tbody>
                  {eventos.map((evento) => {
                    const selecionado = idSelecionado === evento.id
                    return (
                      <tr aria-selected={selecionado} key={evento.id}>
                        <td>{ROTULOS_TIPO[evento.tipo] ?? evento.tipo}</td>
                        <td>{evento.area}</td>
                        <td>
                          {evento.periodoInicio} — {evento.periodoFim}
                        </td>
                        <td>{evento.intensidade}</td>
                        <td>{ROTULOS_ORIGEM_EVENTO[evento.proveniencia] ?? evento.proveniencia}</td>
                        <td>{evento.instanteObservado}</td>
                        <td>
                          <button
                            aria-pressed={selecionado}
                            onClick={() => definirIdSelecionado(evento.id)}
                            type="button"
                          >
                            {selecionado ? 'Selecionado' : 'Selecionar'}
                          </button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            )}
          </section>

          <section aria-labelledby="titulo-historico-sincronizacao">
            <h2 id="titulo-historico-sincronizacao">Histórico de sincronização</h2>
            <dl>
              <dt>Última tentativa</dt>
              <dd>
                {historico.ultimaTentativa
                  ? `${ROTULOS_ORIGEM_SINCRONIZACAO[historico.ultimaTentativa.origem] ?? historico.ultimaTentativa.origem} — ${ROTULOS_ESTADO_SINCRONIZACAO[historico.ultimaTentativa.estado] ?? historico.ultimaTentativa.estado} — ${historico.ultimaTentativa.iniciadoEm}`
                  : '—'}
              </dd>
              <dt>Última atualização válida</dt>
              <dd>{historico.ultimaValida?.finalizadoEm ?? '—'}</dd>
              <dt>Próxima consulta</dt>
              <dd>{historico.proximaConsulta ?? '—'}</dd>
            </dl>
            <h3>Resultados anteriores</h3>
            {historico.resultadosAnteriores.length > 0 ? (
              <ul>
                {historico.resultadosAnteriores.map((sincronizacao) => (
                  <li key={sincronizacao.id}>
                    {ROTULOS_ORIGEM_SINCRONIZACAO[sincronizacao.origem] ?? sincronizacao.origem} —{' '}
                    {ROTULOS_ESTADO_SINCRONIZACAO[sincronizacao.estado] ?? sincronizacao.estado} —
                    iniciado em {sincronizacao.iniciadoEm}
                    {sincronizacao.motivoFalha ? ` — motivo: ${sincronizacao.motivoFalha}` : ''}
                  </li>
                ))}
              </ul>
            ) : (
              <p>Nenhuma sincronização registrada até o momento.</p>
            )}
          </section>
        </>
      )}
    </main>
  )
}
