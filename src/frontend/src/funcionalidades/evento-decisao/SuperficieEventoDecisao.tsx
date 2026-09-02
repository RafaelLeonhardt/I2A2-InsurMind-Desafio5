import {
  CheckCircleIcon,
  CircleNotchIcon,
  WarningIcon,
  XCircleIcon,
} from '@phosphor-icons/react'
import { useEffect, useState } from 'react'
import {
  type AvaliacaoRisco,
  ErroAvaliacaoRisco,
  getAvaliacaoRisco,
} from '../../api/avaliacaoRisco'
import {
  type DetalheElegibilidade,
  type Elegibilidade,
  ErroElegibilidade,
  getDetalheElegibilidade,
  getElegibilidade,
} from '../../api/elegibilidade'
import './SuperficieEventoDecisao.css'

type EstadoCarregamento = 'carregando' | 'aguardando' | 'disponivel' | 'indisponivel'

/**
 * As três categorias distinguíveis da decisão de risco (RISCO-12), derivadas só do
 * `motivo` já persistido pelo backend — nunca recalculadas no frontend (RISCO-13):
 *
 * - `dado_invalido`: o evento não era de um tipo suportado (`tipo_nao_suportado`).
 * - `relevante`: `AvaliacaoRisco.relevante === true`.
 * - `sem_risco`: `relevante === false` por qualquer outro motivo (limiar, área, sem regra).
 */
type CategoriaDecisao = 'relevante' | 'sem_risco' | 'dado_invalido'

function calcularCategoria(avaliacao: AvaliacaoRisco): CategoriaDecisao {
  if (avaliacao.motivo === 'tipo_nao_suportado') return 'dado_invalido'
  return avaliacao.relevante ? 'relevante' : 'sem_risco'
}

const ROTULOS_CATEGORIA: Record<CategoriaDecisao, string> = {
  relevante: 'Relevante',
  sem_risco: 'Sem risco',
  dado_invalido: 'Dado inválido',
}

function IconeCategoria({ categoria }: { categoria: CategoriaDecisao }) {
  if (categoria === 'relevante') {
    return (
      <WarningIcon aria-hidden="true" data-icone-nome="warning" size={18} weight="fill" />
    )
  }
  if (categoria === 'dado_invalido') {
    return (
      <XCircleIcon aria-hidden="true" data-icone-nome="x-circle" size={18} weight="fill" />
    )
  }
  return (
    <CheckCircleIcon aria-hidden="true" data-icone-nome="check-circle" size={18} weight="fill" />
  )
}

const ROTULOS_MOTIVO: Record<string, string> = {
  relevante: 'Critérios da regra ativa atendidos.',
  abaixo_do_limiar: 'Intensidade observada abaixo do limiar da regra ativa.',
  area_nao_aplicavel: 'Área do evento não corresponde à área aplicável da regra ativa.',
  tipo_nao_suportado: 'Tipo de evento não suportado (somente chuva intensa e granizo).',
  sem_regra_ativa: 'Nenhuma regra ativa para este tipo de evento.',
}

type EstadoElegibilidade = 'carregando' | 'disponivel' | 'indisponivel'

function IconeResultadoElegibilidade({ elegivel }: { elegivel: boolean }) {
  if (elegivel) {
    return (
      <CheckCircleIcon aria-hidden="true" data-icone-nome="check-circle" size={16} weight="fill" />
    )
  }
  return <XCircleIcon aria-hidden="true" data-icone-nome="x-circle" size={16} weight="fill" />
}

type PropriedadesSuperficieEventoDecisao = {
  execucaoId: string
}

/**
 * Superfície "Evento e decisão": detalhe da decisão de risco de uma execução, por critério.
 *
 * Sem avaliação ainda persistida (execução não chegou nessa etapa), mostra o progresso real
 * da máquina de estados — nunca antecipa ou recalcula um resultado (RISCO-13).
 */
export function SuperficieEventoDecisao({ execucaoId }: PropriedadesSuperficieEventoDecisao) {
  const [estado, definirEstado] = useState<EstadoCarregamento>('carregando')
  const [avaliacao, definirAvaliacao] = useState<AvaliacaoRisco | null>(null)
  const [falha, definirFalha] = useState<ErroAvaliacaoRisco | null>(null)

  const [estadoElegibilidade, definirEstadoElegibilidade] =
    useState<EstadoElegibilidade>('carregando')
  const [elegibilidade, definirElegibilidade] = useState<Elegibilidade | null>(null)
  const [falhaElegibilidade, definirFalhaElegibilidade] = useState<ErroElegibilidade | null>(null)
  const [registroSelecionadoId, definirRegistroSelecionadoId] = useState<string | null>(null)
  const [detalheSelecionado, definirDetalheSelecionado] = useState<DetalheElegibilidade | null>(
    null,
  )
  const [carregandoDetalhe, definirCarregandoDetalhe] = useState(false)

  useEffect(() => {
    let cancelado = false
    definirEstado('carregando')

    getAvaliacaoRisco(execucaoId)
      .then((resultado) => {
        if (cancelado) return
        definirAvaliacao(resultado)
        definirFalha(null)
        definirEstado(resultado === null ? 'aguardando' : 'disponivel')
      })
      .catch((causa: unknown) => {
        if (cancelado) return
        definirFalha(causa instanceof ErroAvaliacaoRisco ? causa : null)
        definirEstado('indisponivel')
      })

    return () => {
      cancelado = true
    }
  }, [execucaoId])

  useEffect(() => {
    let cancelado = false
    definirEstadoElegibilidade('carregando')
    definirRegistroSelecionadoId(null)
    definirDetalheSelecionado(null)

    getElegibilidade(execucaoId)
      .then((resultado) => {
        if (cancelado) return
        definirElegibilidade(resultado)
        definirFalhaElegibilidade(null)
        definirEstadoElegibilidade('disponivel')
      })
      .catch((causa: unknown) => {
        if (cancelado) return
        definirFalhaElegibilidade(causa instanceof ErroElegibilidade ? causa : null)
        definirEstadoElegibilidade('indisponivel')
      })

    return () => {
      cancelado = true
    }
  }, [execucaoId])

  async function abrirCriterios(registroId: string) {
    if (registroSelecionadoId === registroId) {
      definirRegistroSelecionadoId(null)
      definirDetalheSelecionado(null)
      return
    }
    definirRegistroSelecionadoId(registroId)
    definirCarregandoDetalhe(true)
    definirDetalheSelecionado(null)
    try {
      const detalhe = await getDetalheElegibilidade(execucaoId, registroId)
      definirDetalheSelecionado(detalhe)
    } catch {
      definirDetalheSelecionado(null)
    } finally {
      definirCarregandoDetalhe(false)
    }
  }

  const categoria = avaliacao ? calcularCategoria(avaliacao) : null

  return (
    <main className="conteudo" id="conteudo-principal" tabIndex={-1}>
      <p className="rotulo-contexto">Evento e decisão</p>
      <h1>Evento e decisão</h1>
      <p className="introducao">
        Detalhe da decisão de risco: operando, valor observado, resultado e justificativa de
        cada critério aplicado pela regra ativa, sem nenhum recálculo nesta tela.
      </p>

      {estado === 'carregando' && <p role="status">Carregando decisão de risco…</p>}

      {estado === 'aguardando' && (
        <p role="status">
          <CircleNotchIcon aria-hidden="true" size={18} /> Em processamento — a execução ainda
          não alcançou a etapa de avaliação de risco.
        </p>
      )}

      {estado === 'indisponivel' && (
        <div role="alert">
          <p>
            <strong>Indisponível</strong>
          </p>
          <p>
            <strong>Ocorrência:</strong>{' '}
            {falha?.ocorrencia ?? 'Falha desconhecida ao consultar a decisão de risco.'}
          </p>
          <p>
            <strong>Impacto:</strong> {falha?.impacto ?? ''}
          </p>
          <p>
            <strong>Próxima ação:</strong> {falha?.proximaAcao ?? ''}
          </p>
        </div>
      )}

      {estado === 'disponivel' && avaliacao && categoria && (
        <section aria-labelledby="titulo-decisao-risco">
          <h2 id="titulo-decisao-risco">Decisão de risco</h2>
          <p
            className={`categoria-decisao-badge categoria-decisao-badge--${categoria}`}
            data-icone={categoria}
          >
            <IconeCategoria categoria={categoria} />
            {ROTULOS_CATEGORIA[categoria]}
          </p>
          <p>{ROTULOS_MOTIVO[avaliacao.motivo] ?? avaliacao.motivo}</p>

          <table className="tabela-criterios-decisao">
            <caption className="sr-only">Critérios avaliados na decisão de risco</caption>
            <thead>
              <tr>
                <th scope="col">Operando</th>
                <th scope="col">Valor observado</th>
                <th scope="col">Resultado</th>
                <th scope="col">Justificativa</th>
              </tr>
            </thead>
            <tbody>
              {avaliacao.criterios.map((criterio) => (
                <tr key={criterio.operando}>
                  <td>{criterio.operando}</td>
                  <td>{criterio.valorObservado}</td>
                  <td>{criterio.atende ? 'Atende' : 'Não atende'}</td>
                  <td>{criterio.justificativa}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {estadoElegibilidade === 'carregando' && (
        <p role="status">Carregando público elegível…</p>
      )}

      {estadoElegibilidade === 'indisponivel' && (
        <div role="alert">
          <p>
            <strong>Indisponível</strong>
          </p>
          <p>
            <strong>Ocorrência:</strong>{' '}
            {falhaElegibilidade?.ocorrencia ?? 'Falha desconhecida ao consultar a elegibilidade.'}
          </p>
          <p>
            <strong>Impacto:</strong> {falhaElegibilidade?.impacto ?? ''}
          </p>
          <p>
            <strong>Próxima ação:</strong> {falhaElegibilidade?.proximaAcao ?? ''}
          </p>
        </div>
      )}

      {estadoElegibilidade === 'disponivel' && elegibilidade && (
        <section aria-labelledby="titulo-publico-elegivel">
          <h2 id="titulo-publico-elegivel">Público elegível</h2>
          <p>
            <strong>{elegibilidade.incluidos}</strong> incluído
            {elegibilidade.incluidos === 1 ? '' : 's'} — <strong>{elegibilidade.excluidos}</strong>{' '}
            excluído{elegibilidade.excluidos === 1 ? '' : 's'}
          </p>

          {elegibilidade.registros.length === 0 ? (
            <p>Nenhum segurado avaliado até o momento.</p>
          ) : (
            <table className="tabela-publico-elegivel">
              <caption className="sr-only">
                Público elegível avaliado, com explicação por linha sem depender de hover
              </caption>
              <thead>
                <tr>
                  <th scope="col">Segurado</th>
                  <th scope="col">Apólice</th>
                  <th scope="col">Localização</th>
                  <th scope="col">Canal</th>
                  <th scope="col">Resultado</th>
                  <th scope="col">Explicação</th>
                </tr>
              </thead>
              <tbody>
                {elegibilidade.registros.map((registro) => (
                  <tr key={registro.id}>
                    <td>{registro.nomeSegurado}</td>
                    <td>{registro.apoliceId}</td>
                    <td>{registro.codigoIbgeArea}</td>
                    <td>{registro.canal}</td>
                    <td>
                      <span
                        className={`resultado-elegibilidade-badge resultado-elegibilidade-badge--${registro.elegivel ? 'incluido' : 'excluido'}`}
                        data-indicador={registro.elegivel ? 'incluido' : 'excluido'}
                      >
                        <IconeResultadoElegibilidade elegivel={registro.elegivel} />
                        {registro.elegivel ? 'Incluído' : 'Excluído'}
                      </span>
                    </td>
                    <td>
                      <button
                        aria-expanded={registroSelecionadoId === registro.id}
                        onClick={() => abrirCriterios(registro.id)}
                        type="button"
                      >
                        {registroSelecionadoId === registro.id ? 'Ocultar critérios' : 'Ver critérios'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {registroSelecionadoId && carregandoDetalhe && (
            <p role="status">Carregando explicação…</p>
          )}

          {registroSelecionadoId && !carregandoDetalhe && detalheSelecionado && (
            <section aria-labelledby="titulo-explicacao-elegibilidade">
              <h3 id="titulo-explicacao-elegibilidade">
                Explicação — {detalheSelecionado.nomeSegurado} (regra v{detalheSelecionado.regraVersao})
              </h3>
              <p>{detalheSelecionado.justificativa}</p>
              <table className="tabela-criterios-elegibilidade">
                <caption className="sr-only">
                  Critérios avaliados na decisão de elegibilidade
                </caption>
                <thead>
                  <tr>
                    <th scope="col">Operando</th>
                    <th scope="col">Valor observado</th>
                    <th scope="col">Resultado</th>
                    <th scope="col">Justificativa</th>
                  </tr>
                </thead>
                <tbody>
                  {detalheSelecionado.criterios.map((criterio) => (
                    <tr key={criterio.operando}>
                      <td>{criterio.operando}</td>
                      <td>{criterio.valorObservado}</td>
                      <td>{criterio.atende ? 'Atende' : 'Não atende'}</td>
                      <td>{criterio.justificativa}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          )}
        </section>
      )}
    </main>
  )
}
