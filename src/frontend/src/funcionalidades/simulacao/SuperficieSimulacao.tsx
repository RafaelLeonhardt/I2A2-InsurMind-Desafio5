import {
  ArrowsClockwiseIcon,
  CheckCircleIcon,
  HourglassIcon,
  PlayIcon,
  ProhibitIcon,
  WarningIcon,
} from '@phosphor-icons/react'
import type { CSSProperties } from 'react'
import { useCallback, useEffect, useState } from 'react'
import {
  ErroSimulacao,
  type ResumoSimulacao,
  confirmarSimulacao,
  getResumoSimulacao,
  solicitarNovaTentativaSimulacao,
} from '../../api/simulacao'
import { Modal } from '../../componentes/Modal'
import './SuperficieSimulacao.css'

/** Os cinco estados de progresso que a simulação exibe (SIMUL-12). */
export type EstadoProgresso = 'bloqueada' | 'pronta' | 'simulando' | 'concluida' | 'falha-local'

type Aparencia = {
  rotulo: string
  explicacao: string
  cor: string
  icone: typeof PlayIcon
  nomeIcone: string
}

/**
 * Rótulo, explicação, ícone e cor de cada estado de progresso.
 *
 * A cor mora aqui, e não só na folha de estilo, porque a distinção entre os cinco estados é
 * exigida pelo próprio requisito (SIMUL-12) e precisa ser verificável, não incidental.
 */
const APARENCIA: Record<EstadoProgresso, Aparencia> = {
  bloqueada: {
    rotulo: 'Bloqueada',
    explicacao:
      'A simulação ainda não está liberada: o lote precisa ser revisado e decidido antes.',
    cor: '#6b7280',
    icone: ProhibitIcon,
    nomeIcone: 'prohibit',
  },
  pronta: {
    rotulo: 'Pronta',
    explicacao: 'O lote foi decidido e aguarda a sua confirmação para ser simulado.',
    cor: '#1d4ed8',
    icone: PlayIcon,
    nomeIcone: 'play',
  },
  simulando: {
    rotulo: 'Simulando',
    explicacao: 'A simulação local está em andamento. Nenhuma comunicação real é enviada.',
    cor: '#b45309',
    icone: HourglassIcon,
    nomeIcone: 'hourglass',
  },
  concluida: {
    rotulo: 'Concluída',
    explicacao: 'A simulação terminou. Cada entrega abaixo é simulada, nunca uma entrega real.',
    cor: '#15803d',
    icone: CheckCircleIcon,
    nomeIcone: 'check-circle',
  },
  'falha-local': {
    rotulo: 'Falha local',
    explicacao:
      'Uma falha local interrompeu a simulação. Nenhuma entrega foi registrada e as ' +
      'mensagens aprovadas continuam aprovadas. Nenhum provedor de canal esteve envolvido.',
    cor: '#b91c1c',
    icone: WarningIcon,
    nomeIcone: 'warning',
  },
}

const AVISO_SIMULACAO =
  'Esta operação é uma simulação: nenhuma comunicação real é enviada aos segurados.'

const ROTULOS_CANAL: Record<string, string> = {
  whatsapp: 'WhatsApp',
  email: 'E-mail',
  sms: 'SMS',
}

/** Traduz o estado agregado da execução no estado de progresso exibido (SIMUL-12). */
export function progressoDe(estado: string): EstadoProgresso {
  if (estado === 'aguardando_confirmacao') {
    return 'pronta'
  }
  if (estado === 'simulando') {
    return 'simulando'
  }
  if (estado === 'concluida') {
    return 'concluida'
  }
  if (estado === 'falhou_simulacao') {
    return 'falha-local'
  }
  return 'bloqueada'
}

function rotuloCanal(canal: string): string {
  return ROTULOS_CANAL[canal] ?? canal
}

function periodoDe(resumo: ResumoSimulacao): string {
  if (resumo.evento === null) {
    return 'Sem período registrado'
  }
  return `${resumo.evento.periodoInicio} até ${resumo.evento.periodoFim}`
}

function distribuicaoDe(resumo: ResumoSimulacao): string {
  return resumo.distribuicaoPorCanal
    .map((entrada) => `${rotuloCanal(entrada.canal)}: ${entrada.total}`)
    .join(', ')
}

type EstadoCarregamento = 'carregando' | 'disponivel' | 'indisponivel'

type PropriedadesSuperficieSimulacao = {
  execucaoId: string
  embutido?: boolean
}

/** Selo do estado de progresso, distinto em texto, ícone e cor (SIMUL-12). */
function SeloProgresso({ progresso }: { progresso: EstadoProgresso }) {
  const aparencia = APARENCIA[progresso]
  const Icone = aparencia.icone
  return (
    <p
      className="simulacao__progresso"
      data-progresso={progresso}
      style={{ '--cor-progresso': aparencia.cor } as CSSProperties}
    >
      <Icone aria-hidden="true" data-icone-nome={aparencia.nomeIcone} size={20} weight="fill" />
      <strong>{aparencia.rotulo}</strong>
      <span className="simulacao__progresso-explicacao">{aparencia.explicacao}</span>
    </p>
  )
}

/**
 * Superfície da confirmação e do acompanhamento da simulação (SIMUL-01, 03, 06, 11, 12).
 *
 * A aprovação do conteúdo (3.5) e a confirmação da simulação são gates separados: esta tela
 * não decide mensagem nenhuma, e a ação principal só existe quando a execução já chegou a
 * `aguardando_confirmacao`. O caráter simulado fica visível o tempo todo — antes, durante e
 * depois da operação.
 */
export function SuperficieSimulacao({
  execucaoId,
  embutido = false,
}: PropriedadesSuperficieSimulacao) {
  const [execucaoAtual, definirExecucaoAtual] = useState(execucaoId)
  const [estadoCarregamento, definirEstadoCarregamento] = useState<EstadoCarregamento>('carregando')
  const [resumo, definirResumo] = useState<ResumoSimulacao | null>(null)
  const [falha, definirFalha] = useState<ErroSimulacao | null>(null)
  const [modalAberto, definirModalAberto] = useState(false)
  const [reconhecido, definirReconhecido] = useState(false)
  const [enviando, definirEnviando] = useState(false)

  const consultar = useCallback(async () => {
    try {
      const encontrado = await getResumoSimulacao(execucaoAtual)
      definirResumo(encontrado)
      definirFalha(null)
      definirEstadoCarregamento('disponivel')
    } catch (causa) {
      definirFalha(causa instanceof ErroSimulacao ? causa : null)
      definirEstadoCarregamento('indisponivel')
    }
  }, [execucaoAtual])

  useEffect(() => {
    definirExecucaoAtual(execucaoId)
  }, [execucaoId])

  useEffect(() => {
    definirEstadoCarregamento('carregando')
    definirResumo(null)
    void consultar()
  }, [consultar])

  function navegarPara(destino: string) {
    definirModalAberto(false)
    definirReconhecido(false)
    definirExecucaoAtual(destino)
  }

  async function confirmar() {
    if (resumo === null || !reconhecido) {
      return
    }
    definirEnviando(true)
    try {
      await confirmarSimulacao(resumo.execucaoId, resumo.versao)
      definirModalAberto(false)
      definirReconhecido(false)
      await consultar()
    } catch (causa) {
      definirFalha(causa instanceof ErroSimulacao ? causa : null)
      definirEstadoCarregamento('indisponivel')
    } finally {
      definirEnviando(false)
    }
  }

  async function novaTentativa() {
    if (resumo === null) {
      return
    }
    definirEnviando(true)
    try {
      const nova = await solicitarNovaTentativaSimulacao(resumo.execucaoId)
      navegarPara(nova)
    } catch (causa) {
      definirFalha(causa instanceof ErroSimulacao ? causa : null)
      definirEstadoCarregamento('indisponivel')
    } finally {
      definirEnviando(false)
    }
  }

  const progresso = resumo === null ? 'bloqueada' : progressoDe(resumo.estado)

  const conteudo = (
    <section aria-labelledby="titulo-simulacao" className="simulacao">
      <h2 id="titulo-simulacao">Simulação da comunicação preventiva</h2>
      <p className="simulacao__aviso">{AVISO_SIMULACAO}</p>

      {estadoCarregamento === 'carregando' && <p role="status">Carregando a simulação…</p>}

      {estadoCarregamento === 'indisponivel' && (
        <div role="alert">
          <p>
            <strong>Ocorrência:</strong>{' '}
            {falha?.ocorrencia ?? 'Falha desconhecida ao consultar a simulação.'}
          </p>
          <p>
            <strong>Impacto:</strong> {falha?.impacto ?? ''}
          </p>
          <p>
            <strong>Próxima ação:</strong> {falha?.proximaAcao ?? ''}
          </p>
        </div>
      )}

      {estadoCarregamento === 'disponivel' && resumo && (
        <>
          <SeloProgresso progresso={progresso} />

          <dl className="simulacao__resumo">
            <div>
              <dt>Execução</dt>
              <dd>{resumo.execucaoId}</dd>
            </div>
            <div>
              <dt>Evento</dt>
              <dd>
                {resumo.evento
                  ? `${resumo.evento.tipo} na área ${resumo.evento.area}`
                  : 'Sem evento associado'}
              </dd>
            </div>
            <div>
              <dt>Regra aplicada</dt>
              <dd>
                {resumo.regraId
                  ? `${resumo.regraId} (versão ${resumo.regraVersao})`
                  : 'Sem regra'}
              </dd>
            </div>
            <div>
              <dt>Período</dt>
              <dd>{periodoDe(resumo)}</dd>
            </div>
            <div>
              <dt>Destinatários</dt>
              <dd>{resumo.totalDestinatarios}</dd>
            </div>
            <div>
              <dt>Distribuição por canal</dt>
              <dd>{distribuicaoDe(resumo)}</dd>
            </div>
          </dl>

          {progresso === 'pronta' && (
            <button
              className="simulacao__acao"
              onClick={() => {
                definirReconhecido(false)
                definirModalAberto(true)
              }}
              type="button"
            >
              Confirmar simulação
            </button>
          )}

          {progresso === 'falha-local' && (
            <button
              className="simulacao__acao"
              disabled={enviando}
              onClick={() => void novaTentativa()}
              type="button"
            >
              <ArrowsClockwiseIcon
                aria-hidden="true"
                data-icone-nome="arrows-clockwise"
                size={16}
                weight="fill"
              />
              Solicitar nova tentativa de simulação
            </button>
          )}

          {resumo.entregas.length > 0 && (
            <section
              aria-labelledby="titulo-entregas"
              className="simulacao__entregas"
              data-secao="entregas"
            >
              <h3 id="titulo-entregas">Entregas simuladas</h3>
              <p className="simulacao__entregas-aviso">
                Cada item mostra como o conteúdo apareceria no canal. Nenhuma confirmação nem
                falha de provedor externo é registrada, porque nada foi enviado de verdade.
              </p>
              <ul>
                {resumo.entregas.map((entrega) => (
                  <li data-canal={entrega.canal} data-entrega={entrega.id} key={entrega.id}>
                    <span className="simulacao__entrega-rotulo">
                      {rotuloCanal(entrega.canal)} — entrega {entrega.rotulo}
                    </span>
                    {entrega.assunto && (
                      <p className="simulacao__entrega-assunto">Assunto: {entrega.assunto}</p>
                    )}
                    <p className="simulacao__entrega-corpo">{entrega.corpo}</p>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <section
            aria-labelledby="titulo-correlacionadas"
            className="simulacao__correlacionadas"
            data-secao="correlacionadas"
          >
            <h3 id="titulo-correlacionadas">Execuções correlacionadas</h3>
            {resumo.execucaoOrigemId === null && resumo.retentativas.length === 0 ? (
              <p>Esta execução não está correlacionada a nenhuma outra.</p>
            ) : (
              <ul>
                {resumo.execucaoOrigemId && (
                  <li data-correlacao="origem">
                    <button
                      onClick={() => navegarPara(resumo.execucaoOrigemId as string)}
                      type="button"
                    >
                      Ver a execução de origem {resumo.execucaoOrigemId}
                    </button>
                  </li>
                )}
                {resumo.retentativas.map((retentativa) => (
                  <li data-correlacao="retentativa" key={retentativa}>
                    <button onClick={() => navegarPara(retentativa)} type="button">
                      Ver a nova tentativa {retentativa}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <Modal
            aberto={modalAberto}
            confirmacaoDesabilitada={!reconhecido || enviando}
            impacto={
              `${resumo.totalDestinatarios} destinatários teriam a comunicação apresentada ` +
              `(${distribuicaoDe(resumo)}). Nenhuma comunicação real será enviada.`
            }
            objeto={`Simulação do lote da execução ${resumo.execucaoId}`}
            onConfirmar={() => void confirmar()}
            onFechar={() => {
              definirModalAberto(false)
              definirReconhecido(false)
            }}
            rotuloConfirmar="Confirmar simulação"
            titulo="Confirmar a simulação do lote"
          >
            <dl className="simulacao__modal-resumo">
              <div>
                <dt>Evento</dt>
                <dd>
                  {resumo.evento
                    ? `${resumo.evento.tipo} na área ${resumo.evento.area}`
                    : 'Sem evento associado'}
                </dd>
              </div>
              <div>
                <dt>Regra aplicada</dt>
                <dd>
                  {resumo.regraId
                    ? `${resumo.regraId} (versão ${resumo.regraVersao})`
                    : 'Sem regra'}
                </dd>
              </div>
              <div>
                <dt>Período</dt>
                <dd>{periodoDe(resumo)}</dd>
              </div>
              <div>
                <dt>Destinatários</dt>
                <dd>{resumo.totalDestinatarios}</dd>
              </div>
              <div>
                <dt>Distribuição por canal</dt>
                <dd>{distribuicaoDe(resumo)}</dd>
              </div>
            </dl>
            <p className="simulacao__modal-aviso">
              A aprovação do conteúdo já aconteceu na revisão do lote. Esta é uma decisão
              separada: {AVISO_SIMULACAO}
            </p>
            <label className="simulacao__reconhecimento" htmlFor="reconhecimento-simulacao">
              <input
                checked={reconhecido}
                id="reconhecimento-simulacao"
                onChange={(evento) => definirReconhecido(evento.target.checked)}
                type="checkbox"
              />
              Reconheço que esta operação é uma simulação e que nenhuma comunicação real será
              enviada.
            </label>
          </Modal>
        </>
      )}
    </section>
  )

  return embutido ? conteudo : <main>{conteudo}</main>
}
