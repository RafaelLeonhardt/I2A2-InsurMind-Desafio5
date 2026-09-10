import {
  CaretDownIcon,
  CaretUpIcon,
  CheckCircleIcon,
  HourglassIcon,
  ProhibitIcon,
  ThumbsDownIcon,
  ThumbsUpIcon,
  WarningIcon,
} from '@phosphor-icons/react'
import type { CSSProperties, ReactNode } from 'react'
import { useCallback, useEffect, useState } from 'react'
import {
  ErroResultados,
  getResultados,
  type MensagemNaoSimulavel,
  type ResultadosConsolidados,
  type TotalPorChave,
} from '../../api/resultados'
import './SuperficieResultados.css'

const ROTULOS_CANAL: Record<string, string> = {
  whatsapp: 'WhatsApp',
  email: 'E-mail',
  sms: 'SMS',
}

function rotuloCanal(canal: string): string {
  return ROTULOS_CANAL[canal] ?? canal
}

type AparenciaEstado = {
  rotulo: string
  cor: string
  icone: typeof CheckCircleIcon
  nomeIcone: string
}

/**
 * Rótulo por extenso, ícone e cor de cada estado de mensagem exibido nos totais.
 *
 * `simulada_entregue` é sempre "Enviada — simulação": nunca deve ser lida como confirmação
 * de um provedor externo real (RESULT-01, RESULT-08..10). A cor mora aqui, e não só na folha de
 * estilo, porque a distinção entre estados é o próprio requisito (L-024): assim ela é
 * observável no elemento renderizado, aplicada como propriedade CSS.
 */
const APARENCIA_ESTADO: Record<string, AparenciaEstado> = {
  simulada_entregue: {
    rotulo: 'Enviada — simulação',
    cor: 'var(--green)',
    icone: CheckCircleIcon,
    nomeIcone: 'check-circle',
  },
  aprovada: {
    rotulo: 'Aprovada',
    cor: 'var(--teal)',
    icone: ThumbsUpIcon,
    nomeIcone: 'thumbs-up',
  },
  rejeitada: {
    rotulo: 'Rejeitada',
    cor: 'var(--red)',
    icone: ThumbsDownIcon,
    nomeIcone: 'thumbs-down',
  },
  excluida: {
    rotulo: 'Excluída',
    cor: 'var(--muted)',
    icone: ProhibitIcon,
    nomeIcone: 'prohibit',
  },
  falhou_conteudo: {
    rotulo: 'Falha de conteúdo',
    cor: 'var(--amber)',
    icone: WarningIcon,
    nomeIcone: 'warning',
  },
  falhou_integracao_ia: {
    rotulo: 'Falha de integração com a IA',
    cor: 'var(--orange)',
    icone: WarningIcon,
    nomeIcone: 'warning',
  },
}

const APARENCIA_PADRAO: AparenciaEstado = {
  rotulo: '',
  cor: 'var(--muted)',
  icone: HourglassIcon,
  nomeIcone: 'hourglass',
}

const ESTADOS_FALHA = new Set(['falhou_conteudo', 'falhou_integracao_ia'])
const ESTADO_ENTREGUE = 'simulada_entregue'

/** Total processado = soma de todos os estados — nenhum campo "processada" é persistido. */
function totalProcessado(totais: TotalPorChave[]): number {
  return totais.reduce((soma, item) => soma + item.total, 0)
}

/** Total entregue = soma dos itens no estado `simulada_entregue` (0 se ausente). */
function totalEntregue(totais: TotalPorChave[]): number {
  return totais
    .filter((item) => item.chave === ESTADO_ENTREGUE)
    .reduce((soma, item) => soma + item.total, 0)
}

/** Total com falha = soma dos estados de falha (`falhou_conteudo`, `falhou_integracao_ia`). */
function totalComFalha(totais: TotalPorChave[]): number {
  return totais
    .filter((item) => ESTADOS_FALHA.has(item.chave))
    .reduce((soma, item) => soma + item.total, 0)
}

function aparenciaDe(estado: string): AparenciaEstado {
  const aparencia = APARENCIA_ESTADO[estado]
  if (aparencia) return aparencia
  return { ...APARENCIA_PADRAO, rotulo: estado }
}

/** Selo do estado de mensagem, distinto em texto, ícone e cor (L-024). */
function SeloEstado({ estado }: { estado: string }) {
  const aparencia = aparenciaDe(estado)
  const Icone = aparencia.icone
  return (
    <span
      className="resultados__selo-estado"
      data-estado={estado}
      style={{ '--cor-estado': aparencia.cor } as CSSProperties}
    >
      <Icone aria-hidden="true" data-icone-nome={aparencia.nomeIcone} size={16} weight="fill" />
      {aparencia.rotulo}
    </span>
  )
}

type Direcao = 'asc' | 'desc'
type Coluna = 'chave' | 'total'
type Ordenacao = { coluna: Coluna; direcao: Direcao }

/** `null` é o estado inicial: nenhuma coluna foi ativada, itens na ordem recebida da API. */
function ordenarTotais(itens: TotalPorChave[], ordenacao: Ordenacao | null): TotalPorChave[] {
  if (ordenacao === null) return itens
  const sinal = ordenacao.direcao === 'asc' ? 1 : -1
  return [...itens].sort((a, b) => {
    if (ordenacao.coluna === 'total') return (a.total - b.total) * sinal
    return a.chave.localeCompare(b.chave) * sinal
  })
}

function alternar(ordenacao: Ordenacao | null, coluna: Coluna): Ordenacao {
  if (ordenacao === null || ordenacao.coluna !== coluna) return { coluna, direcao: 'asc' }
  return { coluna, direcao: ordenacao.direcao === 'asc' ? 'desc' : 'asc' }
}

/** Cabeçalho ordenável, com `aria-sort` no `<th>` e nome acessível no botão (RESULT-08..10). */
function CabecalhoOrdenavel({
  coluna,
  ordenacao,
  onOrdenar,
  rotulo,
}: {
  coluna: Coluna
  ordenacao: Ordenacao | null
  onOrdenar: (coluna: Coluna) => void
  rotulo: string
}) {
  const ativa = ordenacao !== null && ordenacao.coluna === coluna ? ordenacao : null
  const ariaSort = ativa === null ? 'none' : ativa.direcao === 'asc' ? 'ascending' : 'descending'
  return (
    <th aria-sort={ariaSort} scope="col">
      <button onClick={() => onOrdenar(coluna)} type="button">
        {rotulo}
        {ativa &&
          (ativa.direcao === 'asc' ? (
            <CaretUpIcon aria-hidden="true" data-icone-nome="caret-up" size={14} />
          ) : (
            <CaretDownIcon aria-hidden="true" data-icone-nome="caret-down" size={14} />
          ))}
      </button>
    </th>
  )
}

function TabelaTotais({
  chaveRotulo,
  itens,
  renderizarChave,
  titulo,
  tituloId,
}: {
  chaveRotulo: string
  itens: TotalPorChave[]
  renderizarChave: (chave: string) => ReactNode
  titulo: string
  tituloId: string
}) {
  const [ordenacao, definirOrdenacao] = useState<Ordenacao | null>(null)

  return (
    <section aria-labelledby={tituloId}>
      <h3 id={tituloId}>{titulo}</h3>
      {itens.length === 0 ? (
        <p>Nenhuma mensagem nesta categoria.</p>
      ) : (
        <table className="tabela-totais">
          <caption className="sr-only">{titulo}, ordenável por coluna</caption>
          <thead>
            <tr>
              <CabecalhoOrdenavel
                coluna="chave"
                onOrdenar={(coluna) => definirOrdenacao((atual) => alternar(atual, coluna))}
                ordenacao={ordenacao}
                rotulo={chaveRotulo}
              />
              <CabecalhoOrdenavel
                coluna="total"
                onOrdenar={(coluna) => definirOrdenacao((atual) => alternar(atual, coluna))}
                ordenacao={ordenacao}
                rotulo="Quantidade"
              />
            </tr>
          </thead>
          <tbody>
            {ordenarTotais(itens, ordenacao).map((item) => (
              <tr key={item.chave}>
                <td>{renderizarChave(item.chave)}</td>
                <td>{item.total}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}

const TODOS = ''

/** Valores distintos presentes nos itens, na ordem em que aparecem — sem lista fixa. */
function valoresDistintos(itens: MensagemNaoSimulavel[], campo: 'canal' | 'estado'): string[] {
  const vistos = new Set<string>()
  const valores: string[] = []
  for (const item of itens) {
    if (!vistos.has(item[campo])) {
      vistos.add(item[campo])
      valores.push(item[campo])
    }
  }
  return valores
}

/** Filtra por canal/estado quando um valor diferente de "Todos" (`''`) está selecionado. */
function filtrarNaoSimulaveis(
  itens: MensagemNaoSimulavel[],
  filtroCanal: string,
  filtroEstado: string,
): MensagemNaoSimulavel[] {
  return itens.filter(
    (item) =>
      (filtroCanal === TODOS || item.canal === filtroCanal) &&
      (filtroEstado === TODOS || item.estado === filtroEstado),
  )
}

function TabelaNaoSimulaveis({
  todosItens,
  filtroCanal,
  filtroEstado,
  aoMudarFiltroCanal,
  aoMudarFiltroEstado,
}: {
  todosItens: MensagemNaoSimulavel[]
  filtroCanal: string
  filtroEstado: string
  aoMudarFiltroCanal: (valor: string) => void
  aoMudarFiltroEstado: (valor: string) => void
}) {
  const itens = filtrarNaoSimulaveis(todosItens, filtroCanal, filtroEstado)
  const canais = valoresDistintos(todosItens, 'canal')
  const estados = valoresDistintos(todosItens, 'estado')

  return (
    <section aria-labelledby="titulo-nao-simulaveis">
      <h3 id="titulo-nao-simulaveis">Mensagens não simuladas</h3>
      <p>
        Rejeitadas, excluídas ou em exceção técnica: nunca contam como entrega simulada, mas
        seguem contabilizadas aqui para explicar a diferença.
      </p>

      {todosItens.length > 0 && (
        <div className="resultados__filtros">
          <label htmlFor="filtro-canal-nao-simuladas">Canal</label>
          <select
            id="filtro-canal-nao-simuladas"
            onChange={(evento) => aoMudarFiltroCanal(evento.target.value)}
            value={filtroCanal}
          >
            <option value={TODOS}>Todos</option>
            {canais.map((canal) => (
              <option key={canal} value={canal}>
                {rotuloCanal(canal)}
              </option>
            ))}
          </select>

          <label htmlFor="filtro-estado-nao-simuladas">Estado</label>
          <select
            id="filtro-estado-nao-simuladas"
            onChange={(evento) => aoMudarFiltroEstado(evento.target.value)}
            value={filtroEstado}
          >
            <option value={TODOS}>Todos</option>
            {estados.map((estado) => (
              <option key={estado} value={estado}>
                {aparenciaDe(estado).rotulo || estado}
              </option>
            ))}
          </select>
        </div>
      )}

      {todosItens.length === 0 ? (
        <p>Nenhuma mensagem do lote ficou fora da simulação.</p>
      ) : itens.length === 0 ? (
        <p>Nenhuma mensagem corresponde ao filtro selecionado.</p>
      ) : (
        <table className="tabela-nao-simulaveis">
          <caption className="sr-only">Mensagens não simuladas, com o motivo</caption>
          <thead>
            <tr>
              <th scope="col">Canal</th>
              <th scope="col">Estado</th>
              <th scope="col">Motivo</th>
            </tr>
          </thead>
          <tbody>
            {itens.map((item) => (
              <tr key={item.mensagemId}>
                <td>{rotuloCanal(item.canal)}</td>
                <td>
                  <SeloEstado estado={item.estado} />
                </td>
                <td>{item.motivo}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}

function BlocoDivergencia({ resultados }: { resultados: ResultadosConsolidados }) {
  const divergencia = resultados.divergencia
  if (divergencia === null) return null
  return (
    <div className="resultados__divergencia" data-estado="totais_divergentes" role="alert">
      <p>
        <strong>Divergência detectada nos totais.</strong>
      </p>
      <p>
        <strong>Correlação:</strong> execução {divergencia.execucaoId}
      </p>
      <p>
        Mensagens em "Enviada — simulação": {divergencia.mensagensSimuladaEntregue}. Entregas
        simuladas persistidas: {divergencia.entregasPersistidas}.
      </p>
      <p>
        <strong>Impacto:</strong> os totais acima refletem exatamente o que está persistido;
        nenhum valor foi corrigido ou ocultado automaticamente.
      </p>
    </div>
  )
}

type EstadoCarregamento = 'carregando' | 'disponivel' | 'indisponivel'

type PropriedadesSuperficieResultados = {
  execucaoId: string
}

/**
 * Superfície "Resultados": totais reconciliáveis por canal e por estado, mensagens não
 * simuladas com motivo, e divergência consultável quando detectada (RESULT-01..10).
 *
 * Consulta somente leitura: reabrir a página nunca repete transição nem cria entrega — os
 * totais são sempre reconstruídos do que está persistido (RESULT-06/07).
 */
export function SuperficieResultados({ execucaoId }: PropriedadesSuperficieResultados) {
  const [estadoCarregamento, definirEstadoCarregamento] =
    useState<EstadoCarregamento>('carregando')
  const [resultados, definirResultados] = useState<ResultadosConsolidados | null>(null)
  const [falha, definirFalha] = useState<ErroResultados | null>(null)
  const [filtroCanal, definirFiltroCanal] = useState(TODOS)
  const [filtroEstado, definirFiltroEstado] = useState(TODOS)

  const consultar = useCallback(async () => {
    try {
      const encontrado = await getResultados(execucaoId)
      definirResultados(encontrado)
      definirFalha(null)
      definirEstadoCarregamento('disponivel')
    } catch (causa) {
      definirFalha(causa instanceof ErroResultados ? causa : null)
      definirEstadoCarregamento('indisponivel')
    }
  }, [execucaoId])

  useEffect(() => {
    definirEstadoCarregamento('carregando')
    definirResultados(null)
    void consultar()
  }, [consultar])

  return (
    <main className="conteudo" id="conteudo-principal" tabIndex={-1}>
      <p className="rotulo-contexto">Resultados</p>
      <h1>Resultados da simulação</h1>
      <p className="introducao">
        Totais reconciliáveis por canal e por estado do lote simulado. Nenhuma comunicação real
        foi enviada: cada "Enviada — simulação" é uma apresentação local, não uma confirmação de
        provedor externo.
      </p>

      {estadoCarregamento === 'carregando' && <p role="status">Carregando resultados…</p>}

      {estadoCarregamento === 'indisponivel' && (
        <div role="alert">
          <p>
            <strong>Ocorrência:</strong>{' '}
            {falha?.ocorrencia ?? 'Falha desconhecida ao consultar os resultados.'}
          </p>
          <p>
            <strong>Impacto:</strong> {falha?.impacto ?? ''}
          </p>
          <p>
            <strong>Próxima ação:</strong> {falha?.proximaAcao ?? ''}
          </p>
        </div>
      )}

      {estadoCarregamento === 'disponivel' && resultados && !resultados.concluido && (
        <p role="status">
          A simulação desta execução ainda está em "{resultados.estado}". Os totais aparecerão
          quando a simulação terminar — nenhum total parcial é exibido como final.
        </p>
      )}

      {estadoCarregamento === 'disponivel' && resultados && resultados.concluido && (
        <>
          <section aria-labelledby="titulo-resumo">
            <h2 id="titulo-resumo">Resumo</h2>
            <dl className="resultados__resumo">
              <div>
                <dt>Total processado</dt>
                <dd>{totalProcessado(resultados.totaisPorEstado)}</dd>
              </div>
              <div>
                <dt>Total entregue</dt>
                <dd>{totalEntregue(resultados.totaisPorEstado)}</dd>
              </div>
              <div>
                <dt>Total com falha</dt>
                <dd>{totalComFalha(resultados.totaisPorEstado)}</dd>
              </div>
            </dl>
          </section>

          <BlocoDivergencia resultados={resultados} />

          <TabelaTotais
            chaveRotulo="Canal"
            itens={resultados.totaisPorCanal}
            renderizarChave={(chave) => rotuloCanal(chave)}
            titulo="Totais por canal"
            tituloId="titulo-totais-canal"
          />

          <TabelaTotais
            chaveRotulo="Estado"
            itens={resultados.totaisPorEstado}
            renderizarChave={(chave) => <SeloEstado estado={chave} />}
            titulo="Totais por estado"
            tituloId="titulo-totais-estado"
          />

          <TabelaNaoSimulaveis
            aoMudarFiltroCanal={definirFiltroCanal}
            aoMudarFiltroEstado={definirFiltroEstado}
            filtroCanal={filtroCanal}
            filtroEstado={filtroEstado}
            todosItens={resultados.naoSimulaveis}
          />
        </>
      )}
    </main>
  )
}
