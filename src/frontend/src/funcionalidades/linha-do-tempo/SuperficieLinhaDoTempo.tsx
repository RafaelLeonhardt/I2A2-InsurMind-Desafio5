import type { FormEvent } from 'react'
import { useCallback, useEffect, useState } from 'react'
import {
  buscarExecucoes,
  type ExecucaoResumo,
  ErroLinhaDoTempo,
  getLinhaDoTempo,
  type LinhaDoTempo,
  type MarcoLinhaDoTempo,
} from '../../api/linhaDoTempo'
import './SuperficieLinhaDoTempo.css'

const ROTULOS_TIPO: Record<string, string> = {
  execucao: 'Execução',
  risco: 'Risco',
  elegibilidade: 'Elegibilidade',
  geracao: 'Geração',
  critica: 'Crítica',
  decisao_humana: 'Decisão humana',
  excecao: 'Exceção',
  simulacao: 'Simulação',
  visualizacao: 'Visualização',
}

function rotuloTipo(tipo: string): string {
  return ROTULOS_TIPO[tipo] ?? tipo
}

/** Localiza o timestamp UTC canônico para exibição, mantendo o valor original no `title`. */
function horarioLocalizado(timestampUtc: string): string {
  const data = new Date(timestampUtc)
  if (Number.isNaN(data.getTime())) return timestampUtc
  return data.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'medium' })
}

type GrupoMarco =
  | { tipo: 'solto'; marco: MarcoLinhaDoTempo; indice: number }
  | { tipo: 'grupo'; mensagemId: string; marcos: MarcoLinhaDoTempo[]; indice: number }

/** Agrupa marcos por `mensagemId`, mantendo a ordem cronológica geral entre grupos: a
 * posição de um grupo é a do seu primeiro marco (Tech Decision do design.md). */
function agruparPorMensagem(marcos: MarcoLinhaDoTempo[]): GrupoMarco[] {
  const grupos: GrupoMarco[] = []
  const mensagensVistas = new Set<string>()

  marcos.forEach((marco, indice) => {
    if (marco.mensagemId === null) {
      grupos.push({ tipo: 'solto', marco, indice })
      return
    }
    if (mensagensVistas.has(marco.mensagemId)) return
    mensagensVistas.add(marco.mensagemId)
    grupos.push({
      tipo: 'grupo',
      mensagemId: marco.mensagemId,
      marcos: marcos.filter((item) => item.mensagemId === marco.mensagemId),
      indice,
    })
  })

  return grupos
}

function MarcoItem({ marco }: { marco: MarcoLinhaDoTempo }) {
  return (
    <li data-tipo={marco.tipo}>
      <span className="linha-do-tempo__tipo">{rotuloTipo(marco.tipo)}</span>
      <span className="linha-do-tempo__acao">{marco.acao}</span>
      <span className="linha-do-tempo__resultado">{marco.resultado}</span>
      <time dateTime={marco.timestamp} title={marco.timestamp}>
        {horarioLocalizado(marco.timestamp)}
      </time>
    </li>
  )
}

function ListaMarcos({ linhaDoTempo }: { linhaDoTempo: LinhaDoTempo }) {
  const grupos = agruparPorMensagem(linhaDoTempo.marcos)

  return (
    <div
      aria-label="Linha do tempo"
      className="linha-do-tempo__rolagem"
      role="region"
      tabIndex={0}
    >
      <ol aria-live="polite" className="linha-do-tempo__lista">
        {grupos.length === 0 && <li>Nenhum marco registrado até o momento.</li>}
        {grupos.map((grupo) =>
          grupo.tipo === 'solto' ? (
            <MarcoItem key={grupo.indice} marco={grupo.marco} />
          ) : (
            <li data-grupo-mensagem={grupo.mensagemId} key={grupo.indice}>
              <details open>
                <summary>
                  Mensagem {grupo.mensagemId} — {grupo.marcos.length}{' '}
                  {grupo.marcos.length === 1 ? 'marco' : 'marcos'}
                </summary>
                <ol className="linha-do-tempo__lista">
                  {grupo.marcos.map((marco, indice) => (
                    <MarcoItem key={indice} marco={marco} />
                  ))}
                </ol>
              </details>
            </li>
          ),
        )}
      </ol>
    </div>
  )
}

type EstadoBusca = 'carregando' | 'disponivel' | 'indisponivel'
type EstadoDetalhe = 'nenhum' | 'carregando' | 'disponivel' | 'indisponivel'

/**
 * Superfície "Linha do tempo": busca de execuções por segurado/canal/estado (TIMELINE-08/09)
 * seguida da cronologia completa da execução escolhida, agrupada por mensagem (TIMELINE-02),
 * com horário localizado (valor UTC canônico em `title`) e navegação por teclado/leitor de
 * tela (TIMELINE-10/11).
 */
export function SuperficieLinhaDoTempo() {
  const [segurado, definirSegurado] = useState('')
  const [canal, definirCanal] = useState('')
  const [estado, definirEstado] = useState('')

  const [estadoBusca, definirEstadoBusca] = useState<EstadoBusca>('carregando')
  const [resultados, definirResultados] = useState<ExecucaoResumo[]>([])
  const [falhaBusca, definirFalhaBusca] = useState<ErroLinhaDoTempo | null>(null)

  const [execucaoSelecionadaId, definirExecucaoSelecionadaId] = useState<string | null>(null)
  const [estadoDetalhe, definirEstadoDetalhe] = useState<EstadoDetalhe>('nenhum')
  const [linhaDoTempo, definirLinhaDoTempo] = useState<LinhaDoTempo | null>(null)
  const [falhaDetalhe, definirFalhaDetalhe] = useState<ErroLinhaDoTempo | null>(null)

  const buscar = useCallback(async () => {
    definirEstadoBusca('carregando')
    try {
      const encontrados = await buscarExecucoes({
        segurado: segurado.trim(),
        canal: canal.trim(),
        estado: estado.trim(),
      })
      definirResultados(encontrados)
      definirFalhaBusca(null)
      definirEstadoBusca('disponivel')
    } catch (causa) {
      definirFalhaBusca(causa instanceof ErroLinhaDoTempo ? causa : null)
      definirEstadoBusca('indisponivel')
    }
  }, [segurado, canal, estado])

  useEffect(() => {
    void buscar()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function aoSubmeterBusca(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault()
    void buscar()
  }

  async function abrirLinhaDoTempo(execucaoId: string) {
    definirExecucaoSelecionadaId(execucaoId)
    definirEstadoDetalhe('carregando')
    definirLinhaDoTempo(null)
    try {
      const encontrada = await getLinhaDoTempo(execucaoId)
      definirLinhaDoTempo(encontrada)
      definirFalhaDetalhe(null)
      definirEstadoDetalhe('disponivel')
    } catch (causa) {
      definirFalhaDetalhe(causa instanceof ErroLinhaDoTempo ? causa : null)
      definirEstadoDetalhe('indisponivel')
    }
  }

  return (
    <main className="conteudo" id="conteudo-principal" tabIndex={-1}>
      <p className="rotulo-contexto">Linha do tempo</p>
      <h1>Linha do tempo ponta a ponta</h1>
      <p className="introducao">
        Busque uma execução por segurado sintético, canal ou estado, e abra sua cronologia
        completa — da coleta meteorológica até a visualização do comunicado.
      </p>

      <section aria-labelledby="titulo-busca-execucoes">
        <h2 id="titulo-busca-execucoes">Buscar execuções</h2>
        <form onSubmit={aoSubmeterBusca}>
          <div className="campo-formulario">
            <label htmlFor="campo-segurado">Segurado sintético</label>
            <input
              id="campo-segurado"
              onChange={(evento) => definirSegurado(evento.target.value)}
              type="text"
              value={segurado}
            />
          </div>
          <div className="campo-formulario">
            <label htmlFor="campo-canal">Canal</label>
            <select
              id="campo-canal"
              onChange={(evento) => definirCanal(evento.target.value)}
              value={canal}
            >
              <option value="">Qualquer canal</option>
              <option value="whatsapp">WhatsApp</option>
              <option value="email">E-mail</option>
              <option value="sms">SMS</option>
            </select>
          </div>
          <div className="campo-formulario">
            <label htmlFor="campo-estado">Estado</label>
            <input
              id="campo-estado"
              onChange={(evento) => definirEstado(evento.target.value)}
              type="text"
              value={estado}
            />
          </div>
          <button type="submit">Buscar</button>
        </form>

        {estadoBusca === 'carregando' && <p role="status">Buscando execuções…</p>}

        {estadoBusca === 'indisponivel' && (
          <div role="alert">
            <p>
              <strong>Ocorrência:</strong>{' '}
              {falhaBusca?.ocorrencia ?? 'Falha desconhecida ao buscar execuções.'}
            </p>
            <p>
              <strong>Impacto:</strong> {falhaBusca?.impacto ?? ''}
            </p>
          </div>
        )}

        {estadoBusca === 'disponivel' && resultados.length === 0 && (
          <p role="status">Nenhuma execução corresponde à busca informada.</p>
        )}

        {estadoBusca === 'disponivel' && resultados.length > 0 && (
          <ul className="linha-do-tempo__resultados">
            {resultados.map((resumo) => (
              <li key={resumo.execucaoId}>
                <button
                  aria-current={resumo.execucaoId === execucaoSelecionadaId}
                  onClick={() => void abrirLinhaDoTempo(resumo.execucaoId)}
                  type="button"
                >
                  Execução {resumo.execucaoId} — {resumo.estado}
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      {estadoDetalhe === 'carregando' && <p role="status">Carregando linha do tempo…</p>}

      {estadoDetalhe === 'indisponivel' && (
        <div role="alert">
          <p>
            <strong>Ocorrência:</strong>{' '}
            {falhaDetalhe?.ocorrencia ?? 'Falha desconhecida ao consultar a linha do tempo.'}
          </p>
          <p>
            <strong>Impacto:</strong> {falhaDetalhe?.impacto ?? ''}
          </p>
        </div>
      )}

      {estadoDetalhe === 'disponivel' && linhaDoTempo && (
        <section aria-labelledby="titulo-cronologia">
          <h2 id="titulo-cronologia">
            Cronologia da execução {linhaDoTempo.execucaoId} ({linhaDoTempo.estado})
          </h2>

          {linhaDoTempo.execucaoOrigemId && (
            <p>
              <strong>Origem:</strong> execução {linhaDoTempo.execucaoOrigemId}
            </p>
          )}
          {linhaDoTempo.retentativas.length > 0 && (
            <p>
              <strong>Retentativas:</strong> {linhaDoTempo.retentativas.join(', ')}
            </p>
          )}

          <ListaMarcos linhaDoTempo={linhaDoTempo} />
        </section>
      )}
    </main>
  )
}
