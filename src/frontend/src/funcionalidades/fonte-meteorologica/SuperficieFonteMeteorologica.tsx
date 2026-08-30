import { useEffect, useState } from 'react'
import {
  ErroMeteorologia,
  type EventoMeteorologico,
  getEventos,
  getSincronizacoes,
  type HistoricoSincronizacoes,
} from '../../api/meteorologia'

type EstadoCarregamento = 'carregando' | 'disponivel' | 'indisponivel'

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

/**
 * Superfície "Fonte meteorológica": eventos normalizados e histórico de sincronização.
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
  }, [])

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

      {estado === 'disponivel' && (
        <>
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
                {historico?.ultimaTentativa
                  ? `${ROTULOS_ORIGEM_SINCRONIZACAO[historico.ultimaTentativa.origem] ?? historico.ultimaTentativa.origem} — ${historico.ultimaTentativa.estado} — ${historico.ultimaTentativa.iniciadoEm}`
                  : '—'}
              </dd>
              <dt>Última atualização válida</dt>
              <dd>{historico?.ultimaValida?.finalizadoEm ?? '—'}</dd>
              <dt>Próxima consulta</dt>
              <dd>{historico?.proximaConsulta ?? '—'}</dd>
            </dl>
            <h3>Resultados anteriores</h3>
            {historico && historico.resultadosAnteriores.length > 0 ? (
              <ul>
                {historico.resultadosAnteriores.map((sincronizacao) => (
                  <li key={sincronizacao.id}>
                    {ROTULOS_ORIGEM_SINCRONIZACAO[sincronizacao.origem] ?? sincronizacao.origem} —{' '}
                    {sincronizacao.estado} — iniciado em {sincronizacao.iniciadoEm}
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
