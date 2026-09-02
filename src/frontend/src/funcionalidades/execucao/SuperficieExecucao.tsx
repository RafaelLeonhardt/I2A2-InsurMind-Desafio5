import {
  CheckCircleIcon,
  CircleNotchIcon,
  FlagCheckeredIcon,
  WarningIcon,
} from '@phosphor-icons/react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { type Execucao, ErroExecucao, getExecucao } from '../../api/execucao'
import { SuperficieEventoDecisao } from '../evento-decisao/SuperficieEventoDecisao'
import './SuperficieExecucao.css'

const INTERVALO_POLLING_MS = 1500

const ESTADOS_EM_ANDAMENTO: ReadonlySet<string> = new Set(['coletando', 'avaliando_elegibilidade'])

function estaEmAndamento(estado: string): boolean {
  return ESTADOS_EM_ANDAMENTO.has(estado)
}

type Categoria = 'concluida' | 'corrente' | 'encerramento' | 'excecao'

type Etapa = {
  chave: string
  rotulo: string
  categoria: Categoria
  causa: string | null
}

const SEQUENCIA_PROGRESSO: readonly string[] = [
  'coleta_concluida',
  'avaliacao_risco_concluida',
  'avaliacao_elegibilidade_concluida',
  'publico_elegivel_formado',
]

const ROTULOS_PROGRESSO: Record<string, string> = {
  coleta_concluida: 'Coleta meteorológica concluída',
  avaliacao_risco_concluida: 'Avaliação de risco concluída',
  avaliacao_elegibilidade_concluida: 'Avaliação de elegibilidade concluída',
  publico_elegivel_formado: 'Público elegível formado',
}

const ROTULOS_ENCERRAMENTO: Record<string, string> = {
  sem_risco: 'Encerrado — evento sem risco relevante',
  sem_elegiveis: 'Encerrado — nenhum segurado elegível',
  aguardando_geracao: 'Aguardando geração de mensagens',
}

const ROTULO_EXCECAO = 'Falha técnica não recuperável'

/**
 * Deriva a etapa "corrente" (em andamento) a partir dos marcos já persistidos.
 *
 * Nunca recalcula um resultado: só traduz para português quais marcos já concluíram
 * (RISCO-13/ELEG equivalente para esta história) — a próxima etapa lógica é sempre
 * determinística a partir do que já está confirmado.
 */
function rotuloCorrente(nomesMarcos: ReadonlySet<string>): string {
  if (nomesMarcos.has('avaliacao_risco_concluida')) return 'Avaliação de elegibilidade em andamento…'
  if (nomesMarcos.has('coleta_concluida')) return 'Avaliação de risco em andamento…'
  return 'Coletando dados meteorológicos…'
}

/** Monta a trilha de etapas exibida, só a partir de `marcos`/`estado` já persistidos. */
function construirEtapas(execucao: Execucao): Etapa[] {
  const nomesMarcos = new Set(execucao.marcos.map((marco) => marco.marco))
  const etapas: Etapa[] = []

  for (const chave of SEQUENCIA_PROGRESSO) {
    if (nomesMarcos.has(chave)) {
      etapas.push({ chave, rotulo: ROTULOS_PROGRESSO[chave], categoria: 'concluida', causa: null })
    }
  }

  if (!estaEmAndamento(execucao.estado)) {
    const ultimoMarco = execucao.marcos.at(-1) ?? null
    if (execucao.estado === 'falhou_coleta') {
      etapas.push({
        chave: 'falhou_coleta',
        rotulo: ROTULO_EXCECAO,
        categoria: 'excecao',
        causa: ultimoMarco?.causa ?? null,
      })
    } else {
      etapas.push({
        chave: execucao.estado,
        rotulo: ROTULOS_ENCERRAMENTO[execucao.estado] ?? execucao.estado,
        categoria: 'encerramento',
        causa: null,
      })
    }
  } else {
    etapas.push({
      chave: 'corrente',
      rotulo: rotuloCorrente(nomesMarcos),
      categoria: 'corrente',
      causa: null,
    })
  }

  return etapas
}

function IconeEtapa({ categoria }: { categoria: Categoria }) {
  if (categoria === 'concluida') {
    return <CheckCircleIcon aria-hidden="true" data-icone-nome="check-circle" size={18} weight="fill" />
  }
  if (categoria === 'corrente') {
    return <CircleNotchIcon aria-hidden="true" data-icone-nome="circle-notch" size={18} />
  }
  if (categoria === 'excecao') {
    return <WarningIcon aria-hidden="true" data-icone-nome="warning" size={18} weight="fill" />
  }
  return <FlagCheckeredIcon aria-hidden="true" data-icone-nome="flag-checkered" size={18} weight="fill" />
}

type EstadoCarregamento = 'carregando' | 'disponivel' | 'indisponivel'

type PropriedadesSuperficieExecucao = {
  execucaoId: string
}

/**
 * Superfície de acompanhamento da execução preventiva: progresso real (marcos), etapa
 * corrente, encerramento ou exceção — sempre a partir do que a API já persistiu
 * (RUNNER-01..09, RUNNER-12), nunca recalculado nesta tela.
 */
export function SuperficieExecucao({ execucaoId }: PropriedadesSuperficieExecucao) {
  const [estadoCarregamento, definirEstadoCarregamento] = useState<EstadoCarregamento>('carregando')
  const [execucao, definirExecucao] = useState<Execucao | null>(null)
  const [falha, definirFalha] = useState<ErroExecucao | null>(null)
  const idIntervalo = useRef<number | null>(null)

  const consultar = useCallback(async () => {
    try {
      const resultado = await getExecucao(execucaoId)
      definirExecucao(resultado)
      definirFalha(null)
      definirEstadoCarregamento('disponivel')
    } catch (causa) {
      definirFalha(causa instanceof ErroExecucao ? causa : null)
      definirEstadoCarregamento('indisponivel')
    }
  }, [execucaoId])

  useEffect(() => {
    definirEstadoCarregamento('carregando')
    definirExecucao(null)
    void consultar()
  }, [consultar])

  useEffect(() => {
    if (execucao === null || estaEmAndamento(execucao.estado)) {
      if (idIntervalo.current === null) {
        idIntervalo.current = window.setInterval(() => {
          void consultar()
        }, INTERVALO_POLLING_MS)
      }
    } else if (idIntervalo.current !== null) {
      window.clearInterval(idIntervalo.current)
      idIntervalo.current = null
    }

    return () => {
      if (idIntervalo.current !== null) {
        window.clearInterval(idIntervalo.current)
        idIntervalo.current = null
      }
    }
  }, [execucao, consultar])

  const etapas = execucao ? construirEtapas(execucao) : []
  const emGeracao = execucao?.estado === 'aguardando_geracao'

  return (
    <main className="conteudo" id="conteudo-principal" tabIndex={-1}>
      <p className="rotulo-contexto">Acompanhamento da execução</p>
      <h1>Acompanhamento da execução</h1>
      <p className="introducao">
        Progresso real da orquestração de coleta, avaliação de risco e avaliação de
        elegibilidade, sem nenhum clique manual intermediário.
      </p>

      {estadoCarregamento === 'carregando' && <p role="status">Carregando execução…</p>}

      {estadoCarregamento === 'indisponivel' && (
        <div role="alert">
          <p>
            <strong>Indisponível</strong>
          </p>
          <p>
            <strong>Ocorrência:</strong>{' '}
            {falha?.ocorrencia ?? 'Falha desconhecida ao consultar a execução.'}
          </p>
          <p>
            <strong>Impacto:</strong> {falha?.impacto ?? ''}
          </p>
          <p>
            <strong>Próxima ação:</strong> {falha?.proximaAcao ?? ''}
          </p>
        </div>
      )}

      {estadoCarregamento === 'disponivel' && execucao && (
        <section aria-labelledby="titulo-progresso-execucao">
          <h2 id="titulo-progresso-execucao">Progresso</h2>
          <ol aria-live="polite" className="trilha-execucao">
            {etapas.length === 0 && <li>Nenhuma etapa registrada até o momento.</li>}
            {etapas.map((etapa) => (
              <li
                className={`etapa-execucao etapa-execucao--${etapa.categoria}`}
                data-categoria={etapa.categoria}
                data-icone={etapa.categoria}
                key={etapa.chave}
              >
                <IconeEtapa categoria={etapa.categoria} />
                <span>{etapa.rotulo}</span>
                {etapa.causa && <p className="causa-etapa-execucao">{etapa.causa}</p>}
              </li>
            ))}
          </ol>
        </section>
      )}

      {emGeracao && <SuperficieEventoDecisao embutido execucaoId={execucaoId} />}
    </main>
  )
}
