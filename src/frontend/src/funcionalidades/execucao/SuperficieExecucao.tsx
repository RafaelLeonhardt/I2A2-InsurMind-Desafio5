import {
  CheckCircleIcon,
  CircleNotchIcon,
  FlagCheckeredIcon,
  WarningIcon,
} from '@phosphor-icons/react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { type Execucao, ErroExecucao, getExecucao } from '../../api/execucao'
import { usePerfilContexto } from '../../contexto/PerfilContexto'
import { SuperficieEventoDecisao } from '../evento-decisao/SuperficieEventoDecisao'
import { SuperficieGeracaoMensagens } from '../geracao-mensagens/SuperficieGeracaoMensagens'
import { SuperficiePreparacaoIA } from '../preparacao-ia/SuperficiePreparacaoIA'
import { SuperficieRevisaoLote } from '../revisao-lote/SuperficieRevisaoLote'
import { SuperficieSimulacao } from '../simulacao/SuperficieSimulacao'
import './SuperficieExecucao.css'

const ESTADOS_SIMULACAO: ReadonlySet<string> = new Set([
  'aguardando_confirmacao',
  'simulando',
  'falhou_simulacao',
])

const ESTADOS_PREPARACAO_IA: ReadonlySet<string> = new Set([
  'aguardando_geracao',
  'falhou_preparacao_ia',
])

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
  concluida: 'Concluída — resultado disponível',
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
    if (execucao.estado.startsWith('falhou_')) {
      etapas.push({
        chave: execucao.estado,
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
  const { selecionarSuperficie } = usePerfilContexto()
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

  const abrirExecucao = useCallback(
    (outroExecucaoId: string) => {
      selecionarSuperficie({
        tipo: 'evento-execucao',
        execucaoId: outroExecucaoId,
        perfilPai: 'administrador',
      })
    },
    [selecionarSuperficie],
  )

  const abrirResultado = useCallback(() => {
    selecionarSuperficie({
      tipo: 'resultado-execucao',
      execucaoId,
      perfilPai: 'administrador',
    })
  }, [selecionarSuperficie, execucaoId])

  const etapas = execucao ? construirEtapas(execucao) : []
  // A decisão de risco/elegibilidade (SuperficieEventoDecisao) pode já estar persistida a
  // partir do momento em que a coleta termina — mostrada mesmo em sem_risco/sem_elegiveis
  // para explicar a decisão (PAINELEXEC-02, edge case "por que o evento foi sem risco"),
  // não só quando a execução chega em aguardando_geracao.
  const mostrarDecisaoDeRisco =
    execucao !== null && execucao.estado !== 'coletando' && execucao.estado !== 'falhou_coleta'
  const mostrarPreparacaoIa = execucao !== null && ESTADOS_PREPARACAO_IA.has(execucao.estado)
  const mostrarGeracaoMensagens = execucao !== null && execucao.estado === 'processando_mensagens'
  const mostrarRevisaoLote = execucao !== null && execucao.estado === 'aguardando_revisao'
  const mostrarSimulacao = execucao !== null && ESTADOS_SIMULACAO.has(execucao.estado)
  const mostrarResultado = execucao !== null && execucao.estado === 'concluida'

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

      {execucao &&
        !mostrarPreparacaoIa &&
        (execucao.execucaoOrigemId !== null || execucao.retentativas.length > 0) && (
        <section aria-labelledby="titulo-execucoes-correlacionadas">
          <h2 id="titulo-execucoes-correlacionadas">Execuções correlacionadas</h2>
          {execucao.execucaoOrigemId !== null && (
            <p>
              Esta é uma nova tentativa da execução{' '}
              <button
                className="btn secondary"
                onClick={() => abrirExecucao(execucao.execucaoOrigemId as string)}
                type="button"
              >
                {execucao.execucaoOrigemId}
              </button>
              .
            </p>
          )}
          {execucao.retentativas.length > 0 && (
            <div>
              <p>Novas tentativas criadas a partir desta execução:</p>
              <ul>
                {execucao.retentativas.map((retentativaId) => (
                  <li key={retentativaId}>
                    <button
                      className="btn secondary"
                      onClick={() => abrirExecucao(retentativaId)}
                      type="button"
                    >
                      {retentativaId}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>
      )}

      {mostrarDecisaoDeRisco && <SuperficieEventoDecisao embutido execucaoId={execucaoId} />}

      {mostrarPreparacaoIa && (
        <SuperficiePreparacaoIA aoNavegar={abrirExecucao} execucaoId={execucaoId} />
      )}

      {mostrarGeracaoMensagens && <SuperficieGeracaoMensagens embutido execucaoId={execucaoId} />}

      {mostrarRevisaoLote && <SuperficieRevisaoLote embutido execucaoId={execucaoId} />}

      {mostrarSimulacao && <SuperficieSimulacao embutido execucaoId={execucaoId} />}

      {mostrarResultado && (
        <button onClick={abrirResultado} type="button">
          Ver resultado consolidado
        </button>
      )}
    </main>
  )
}
