import type { KeyboardEvent } from 'react'
import { useEffect, useId, useRef, useState } from 'react'
import {
  type ExplicacaoComunicado,
  ErroExplicacaoComunicado,
  getExplicacaoComunicado,
  type Tentativa,
} from '../../api/explicacaoComunicado'
import './SuperficieExplicacaoComunicado.css'

const SELETOR_FOCAVEIS = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(', ')

const ROTULOS_ORIGEM_REGENERACAO: Record<string, string> = {
  primeira_tentativa: 'Primeira tentativa',
  automatica: 'Nova tentativa automática, após reprovação do agente crítico',
  humana: 'Nova tentativa solicitada por decisão humana',
}

function rotuloOrigemRegeneracao(origem: string): string {
  return ROTULOS_ORIGEM_REGENERACAO[origem] ?? origem
}

const AVISO_PREVIA =
  'Prévia privada e simulada — esta comunicação não foi enviada e não constitui um ' +
  'alerta oficial.'

type EstadoCarregamento = 'carregando' | 'disponivel' | 'nao-encontrado' | 'indisponivel'

type PropriedadesSuperficieExplicacaoComunicado = {
  /** Controla a presença do drawer no documento. */
  aberto: boolean
  seguradoId: string
  entregaSimuladaId: string
  /** Fecha o drawer e devolve o foco à origem. */
  onFechar: () => void
}

/**
 * Drawer "Como esta mensagem foi criada" (EXPLICACAO-01..07).
 *
 * Só leitura: abrir o drawer não reavalia nada e não aciona a OpenAI. Foco preso na camada
 * ativa e `Esc` devolvendo o foco à origem seguem o mesmo mecanismo do `Modal` (Épico 1) e
 * de `SuperficieDetalheResultado` (4.2) — reimplementado aqui porque este drawer não tem
 * ação de confirmar/cancelar, só fechar, e nunca abre uma segunda camada modal.
 */
export function SuperficieExplicacaoComunicado({
  aberto,
  seguradoId,
  entregaSimuladaId,
  onFechar,
}: PropriedadesSuperficieExplicacaoComunicado) {
  const identificador = useId()
  const idTitulo = `${identificador}-titulo`
  const referenciaDrawer = useRef<HTMLDivElement>(null)

  const [estadoCarregamento, definirEstadoCarregamento] =
    useState<EstadoCarregamento>('carregando')
  const [explicacao, definirExplicacao] = useState<ExplicacaoComunicado | null>(null)
  const [falha, definirFalha] = useState<ErroExplicacaoComunicado | null>(null)

  useEffect(() => {
    if (!aberto) return
    let cancelado = false
    definirEstadoCarregamento('carregando')
    definirExplicacao(null)
    definirFalha(null)

    getExplicacaoComunicado(seguradoId, entregaSimuladaId)
      .then((encontrada) => {
        if (cancelado) return
        definirExplicacao(encontrada)
        definirEstadoCarregamento('disponivel')
      })
      .catch((causa: unknown) => {
        if (cancelado) return
        const erro = causa instanceof ErroExplicacaoComunicado ? causa : null
        definirFalha(erro)
        definirEstadoCarregamento(erro?.status === 404 ? 'nao-encontrado' : 'indisponivel')
      })

    return () => {
      cancelado = true
    }
  }, [aberto, seguradoId, entregaSimuladaId])

  useEffect(() => {
    if (!aberto) return

    const origemDoFoco = document.activeElement as HTMLElement | null
    const primeiroFocavel = referenciaDrawer.current?.querySelector<HTMLElement>(SELETOR_FOCAVEIS)
    primeiroFocavel?.focus()

    return () => {
      origemDoFoco?.focus()
    }
  }, [aberto])

  if (!aberto) {
    return null
  }

  function aoTeclar(evento: KeyboardEvent<HTMLDivElement>) {
    if (evento.key === 'Escape') {
      evento.preventDefault()
      onFechar()
      return
    }

    if (evento.key !== 'Tab') {
      return
    }

    const focaveis = Array.from(
      referenciaDrawer.current?.querySelectorAll<HTMLElement>(SELETOR_FOCAVEIS) ?? [],
    )
    if (focaveis.length === 0) {
      return
    }

    const primeiro = focaveis[0]
    const ultimo = focaveis[focaveis.length - 1]

    if (evento.shiftKey && document.activeElement === primeiro) {
      evento.preventDefault()
      ultimo.focus()
      return
    }

    if (!evento.shiftKey && document.activeElement === ultimo) {
      evento.preventDefault()
      primeiro.focus()
    }
  }

  return (
    <div className="explicacao-comunicado-fundo">
      <div
        aria-labelledby={idTitulo}
        aria-modal="true"
        className="explicacao-comunicado-drawer"
        onKeyDown={aoTeclar}
        ref={referenciaDrawer}
        role="dialog"
      >
        <h2 id={idTitulo}>Como esta mensagem foi criada</h2>

        {estadoCarregamento === 'carregando' && <p role="status">Carregando explicação…</p>}

        {estadoCarregamento === 'nao-encontrado' && (
          <div role="alert">
            <p>
              <strong>Não encontrada</strong>
            </p>
            <p>Este comunicado não existe ou não pertence a você.</p>
          </div>
        )}

        {estadoCarregamento === 'indisponivel' && (
          <div role="alert">
            <p>
              <strong>Ocorrência:</strong>{' '}
              {falha?.ocorrencia ?? 'Falha desconhecida ao consultar a explicação.'}
            </p>
            <p>
              <strong>Impacto:</strong> {falha?.impacto ?? ''}
            </p>
            <p>
              <strong>Próxima ação:</strong> {falha?.proximaAcao ?? ''}
            </p>
          </div>
        )}

        {estadoCarregamento === 'disponivel' && explicacao && (
          <ConteudoExplicacao explicacao={explicacao} />
        )}

        <div className="explicacao-comunicado-acoes">
          <button onClick={onFechar} type="button">
            Fechar
          </button>
        </div>
      </div>
    </div>
  )
}

function ConteudoExplicacao({ explicacao }: { explicacao: ExplicacaoComunicado }) {
  return (
    <>
      {explicacao.execucaoOrigemId && (
        <p role="note">
          Este comunicado pertence a uma nova tentativa, correlacionada à execução original{' '}
          {explicacao.execucaoOrigemId}.
        </p>
      )}

      <section aria-labelledby="titulo-evento-regra" data-secao="evento-regra">
        <span className="explicacao-comunicado-origem" data-origem="deterministica">
          Determinístico
        </span>
        <h3 id="titulo-evento-regra">Evento e regra aplicada</h3>
        <dl>
          <div>
            <dt>Evento</dt>
            <dd>
              {explicacao.eventoERegra.evento
                ? `${explicacao.eventoERegra.evento.tipo} na área ${explicacao.eventoERegra.evento.area}`
                : 'Sem evento associado.'}
            </dd>
          </div>
          <div>
            <dt>Regra preventiva</dt>
            <dd>Versão {explicacao.eventoERegra.regraVersao}</dd>
          </div>
        </dl>
      </section>

      <section aria-labelledby="titulo-contexto" data-secao="contexto">
        <h3 id="titulo-contexto">Dados usados na sua mensagem</h3>
        {explicacao.contexto ? (
          <dl>
            <div>
              <dt>Usados</dt>
              <dd>{explicacao.contexto.categoriasUsadas.join(', ')}</dd>
            </div>
            <div>
              <dt>Não usados</dt>
              <dd>{explicacao.contexto.categoriasNaoUsadas.join(', ')}</dd>
            </div>
          </dl>
        ) : (
          <p className="explicacao-comunicado-parcial">
            Procedência parcial — as categorias de dado usadas ainda não estão disponíveis.
          </p>
        )}
      </section>

      <section aria-labelledby="titulo-agente" data-secao="agente">
        <span className="explicacao-comunicado-origem" data-origem="agente">
          Inteligência artificial
        </span>
        <h3 id="titulo-agente">Como a mensagem foi gerada</h3>

        {explicacao.agente.status === 'excecao' && (
          <div className="explicacao-comunicado-excecao" role="alert">
            <p>
              <strong>Exceção registrada.</strong>
            </p>
            <p>A geração desta mensagem não foi concluída pelos agentes.</p>
            <p>
              <strong>Causa:</strong> {explicacao.agente.causaExcecao}
            </p>
          </div>
        )}

        {explicacao.agente.status === 'parcial' && (
          <p className="explicacao-comunicado-parcial">
            Procedência parcial — parte da avaliação do agente crítico não está disponível.
          </p>
        )}

        {explicacao.agente.tentativas.length === 0 ? (
          <p>Nenhuma tentativa de geração registrada.</p>
        ) : (
          <ol>
            {explicacao.agente.tentativas.map((tentativa) => (
              <TentativaExplicada key={tentativa.numeroTentativa} tentativa={tentativa} />
            ))}
          </ol>
        )}
      </section>

      <section aria-labelledby="titulo-previa" data-secao="previa">
        <h3 id="titulo-previa">Prévia da mensagem final</h3>
        <p className="explicacao-comunicado-aviso-simulacao">{AVISO_PREVIA}</p>
        {explicacao.apresentacaoSimulada ? (
          <dl>
            {explicacao.apresentacaoSimulada.assunto && (
              <div>
                <dt>Assunto</dt>
                <dd>{explicacao.apresentacaoSimulada.assunto}</dd>
              </div>
            )}
            <div>
              <dt>Corpo</dt>
              <dd>{explicacao.apresentacaoSimulada.corpo}</dd>
            </div>
          </dl>
        ) : (
          <p>Esta mensagem ainda não foi simulada.</p>
        )}
      </section>
    </>
  )
}

function TentativaExplicada({ tentativa }: { tentativa: Tentativa }) {
  return (
    <li className="explicacao-comunicado-tentativa" data-tentativa={tentativa.numeroTentativa}>
      <p>
        <strong>Tentativa {tentativa.numeroTentativa}</strong> —{' '}
        {rotuloOrigemRegeneracao(tentativa.origemRegeneracao)}
      </p>
      <p>Redator: agente de IA, modelo {tentativa.modeloRedator}.</p>
      <p>
        Crítico:{' '}
        {tentativa.avaliacaoCritica === null
          ? 'ainda não avaliada'
          : tentativa.avaliacaoCritica.aprovada
            ? 'aprovada pelo agente crítico'
            : `reprovada pelo agente crítico (${tentativa.avaliacaoCritica.motivos.join(', ')})`}
      </p>
      {tentativa.decisoesHumanas.length === 0 ? (
        <p>Nenhuma aprovação humana registrada ainda para esta tentativa.</p>
      ) : (
        <ul>
          {tentativa.decisoesHumanas.map((decisao, indice) => (
            <li key={`${tentativa.numeroTentativa}-${indice}`}>
              Aprovação humana: {decisao.resultado}
              {decisao.justificativa ? ` (${decisao.justificativa})` : ''}
            </li>
          ))}
        </ul>
      )}
    </li>
  )
}
