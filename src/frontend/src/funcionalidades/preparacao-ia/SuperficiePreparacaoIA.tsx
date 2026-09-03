import { ArrowsClockwiseIcon, CheckCircleIcon, ProhibitIcon } from '@phosphor-icons/react'
import { useCallback, useEffect, useState } from 'react'
import { type Execucao, ErroExecucao, getExecucao } from '../../api/execucao'
import {
  type Preflight,
  ErroPreparacaoIa,
  prepararExecucao,
  solicitarNovaTentativaIa,
} from '../../api/preparacaoIa'
import './SuperficiePreparacaoIA.css'

const MARCO_BLOQUEIO = 'falhou_preparacao_ia'

const TEXTO_SEM_SUBSTITUTO =
  'Nenhuma mensagem foi gerada e nada foi escrito no lugar dela: no modo conectado ' +
  'obrigatório do MVP, a Central Preventiva não substitui uma resposta indisponível da ' +
  'OpenAI por texto fixo, simulador de modelo ou outro provedor.'

const IMPACTO_BLOQUEIO =
  'Nenhuma mensagem preventiva é gerada nesta execução. A coleta, a avaliação de risco e o ' +
  'público elegível já produzidos permanecem consultáveis.'

const PROXIMA_ACAO_BLOQUEIO =
  'Restabelecida a integração com a OpenAI, solicite uma nova tentativa: ela cria uma ' +
  'execução correlacionada nova, sem reabrir nem alterar esta.'

type EstadoCarregamento = 'carregando' | 'disponivel' | 'indisponivel'

type PropriedadesSuperficiePreparacaoIA = {
  execucaoId: string
  aoNavegar?: (execucaoId: string) => void
}

/** Causa sanitizada do bloqueio, lida do marco persistido — nunca um texto inventado. */
function causaDoBloqueio(execucao: Execucao | null, preflight: Preflight | null): string | null {
  if (preflight?.causa) return preflight.causa
  const marco = execucao?.marcos.find((item) => item.marco === MARCO_BLOQUEIO)
  return marco?.causa ?? null
}

function estadoCorrente(execucao: Execucao | null, preflight: Preflight | null): string | null {
  return preflight?.estado ?? execucao?.estado ?? null
}

/**
 * Superfície da preparação agêntica: dispara o preflight de disponibilidade da OpenAI,
 * explica um bloqueio com causa, impacto e próxima ação segura, e navega entre a execução
 * de origem e suas novas tentativas (PREFL-16, PREFL-17).
 *
 * Nenhum conteúdo é exibido como se fosse uma mensagem gerada: quando a OpenAI está
 * indisponível, a tela mostra o bloqueio, nunca um substituto.
 */
export function SuperficiePreparacaoIA({
  execucaoId,
  aoNavegar,
}: PropriedadesSuperficiePreparacaoIA) {
  const [estadoCarregamento, definirEstadoCarregamento] = useState<EstadoCarregamento>('carregando')
  const [execucao, definirExecucao] = useState<Execucao | null>(null)
  const [preflight, definirPreflight] = useState<Preflight | null>(null)
  const [falha, definirFalha] = useState<ErroExecucao | ErroPreparacaoIa | null>(null)
  const [ocupado, definirOcupado] = useState(false)
  const [novaExecucaoId, definirNovaExecucaoId] = useState<string | null>(null)

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
    definirPreflight(null)
    definirNovaExecucaoId(null)
    void consultar()
  }, [consultar])

  async function preparar() {
    definirOcupado(true)
    definirFalha(null)
    try {
      definirPreflight(await prepararExecucao(execucaoId))
      await consultar()
    } catch (causa) {
      definirFalha(causa instanceof ErroPreparacaoIa ? causa : null)
    } finally {
      definirOcupado(false)
    }
  }

  async function novaTentativa() {
    definirOcupado(true)
    definirFalha(null)
    try {
      const criada = await solicitarNovaTentativaIa(execucaoId)
      definirNovaExecucaoId(criada.execucaoId)
      await consultar()
    } catch (causa) {
      definirFalha(causa instanceof ErroPreparacaoIa ? causa : null)
    } finally {
      definirOcupado(false)
    }
  }

  const estado = estadoCorrente(execucao, preflight)
  const bloqueada = estado === 'falhou_preparacao_ia'
  const preparada = estado === 'processando_mensagens'
  const preparavel = estado === 'aguardando_geracao'
  const causa = causaDoBloqueio(execucao, preflight)
  const retentativas = execucao?.retentativas ?? []
  const origemId = execucao?.execucaoOrigemId ?? null

  return (
    <section aria-labelledby="titulo-preparacao-ia" className="preparacao-ia">
      <h2 id="titulo-preparacao-ia">Preparação da produção de mensagens</h2>

      {estadoCarregamento === 'carregando' && <p role="status">Carregando execução…</p>}

      {estadoCarregamento === 'indisponivel' && (
        <div role="alert">
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

      {estadoCarregamento === 'disponivel' && preparavel && (
        <>
          <p>
            A verificação da integração com a OpenAI acontece antes de qualquer mensagem ser
            gerada.
          </p>
          <button disabled={ocupado} onClick={() => void preparar()} type="button">
            Preparar produção de mensagens
          </button>
        </>
      )}

      {estadoCarregamento === 'disponivel' && preparada && (
        <p className="preparacao-ia__preparada" data-estado="processando_mensagens" role="status">
          <CheckCircleIcon aria-hidden="true" data-icone-nome="check-circle" size={18} weight="fill" />
          <span>
            Integração com a OpenAI confirmada. A execução seguiu para a produção de mensagens.
          </span>
        </p>
      )}

      {estadoCarregamento === 'disponivel' && bloqueada && (
        <div className="preparacao-ia__bloqueio" data-estado="falhou_preparacao_ia" role="alert">
          <p className="preparacao-ia__titulo-bloqueio">
            <ProhibitIcon aria-hidden="true" data-icone-nome="prohibit" size={18} weight="fill" />
            <strong>Produção de mensagens bloqueada</strong>
          </p>
          <p>
            <strong>Causa:</strong>{' '}
            {causa ?? 'A verificação de disponibilidade da OpenAI não foi concluída.'}
          </p>
          <p>
            <strong>Impacto:</strong> {IMPACTO_BLOQUEIO}
          </p>
          <p>
            <strong>Próxima ação:</strong> {PROXIMA_ACAO_BLOQUEIO}
          </p>
          <p className="preparacao-ia__sem-substituto">{TEXTO_SEM_SUBSTITUTO}</p>
          <button disabled={ocupado} onClick={() => void novaTentativa()} type="button">
            <ArrowsClockwiseIcon aria-hidden="true" data-icone-nome="arrows-clockwise" size={18} />
            <span>Solicitar nova tentativa</span>
          </button>
        </div>
      )}

      {falha !== null && estadoCarregamento === 'disponivel' && (
        <div role="alert">
          <p>
            <strong>Ocorrência:</strong> {falha.ocorrencia}
          </p>
          <p>
            <strong>Próxima ação:</strong> {falha.proximaAcao}
          </p>
        </div>
      )}

      {novaExecucaoId !== null && (
        <p className="preparacao-ia__criada" role="status">
          Nova tentativa criada. Esta execução permanece encerrada, com o histórico preservado.
        </p>
      )}

      {(origemId !== null || retentativas.length > 0) && (
        <nav aria-label="Execuções correlacionadas" className="preparacao-ia__correlacoes">
          {origemId !== null && (
            <button
              onClick={() => aoNavegar?.(origemId)}
              type="button"
            >
              Ver execução de origem
            </button>
          )}
          {retentativas.map((retentativa, indice) => (
            <button key={retentativa} onClick={() => aoNavegar?.(retentativa)} type="button">
              Ver nova tentativa {indice + 1}
            </button>
          ))}
        </nav>
      )}
    </section>
  )
}
