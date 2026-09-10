import { CheckCircleIcon, HourglassIcon, WarningIcon } from '@phosphor-icons/react'
import { useCallback, useEffect, useState } from 'react'
import {
  type Comunicado,
  ErroComunicado,
  getComunicado,
  registrarVisualizacaoComunicado,
  type VisualizacaoComunicado,
} from '../../api/comunicado'
import { SuperficieExplicacaoComunicado } from './SuperficieExplicacaoComunicado'
import './SuperficieComunicado.css'

const ROTULOS_CANAL: Record<string, string> = {
  whatsapp: 'WhatsApp',
  email: 'E-mail',
  sms: 'SMS',
}

function rotuloCanal(canal: string): string {
  return ROTULOS_CANAL[canal] ?? canal
}

type EstadoCarregamento = 'carregando' | 'disponivel' | 'indisponivel'
type EstadoVisualizacao = 'pendente' | 'registrando' | 'confirmada' | 'erro'

type PropriedadesSuperficieComunicado = {
  seguradoId: string
  entregaSimuladaId: string
  /** Quando true, renderiza como `<section>` sem `id`/foco próprios em vez de `<main>`
   * (5.7, `PainelSegurado`): evita landmark e id duplicados ao compor esta superfície
   * junto de outras na mesma página. Ausente/false preserva o comportamento original. */
  comoSecao?: boolean
}

/**
 * Superfície "Comunicado" do perfil Segurado (VISU-01, 02, 05, 06, 07).
 *
 * Só leitura de conteúdo: nenhuma ação administrativa aparece aqui — "Ver como esta mensagem
 * foi criada" (6.8) abre `SuperficieExplicacaoComunicado` (5.4), também só leitura. O `POST`
 * de visualização dispara num efeito separado, depois que o comunicado já renderizou com
 * sucesso — nunca no `GET` inicial (Tech Decision do design). Enquanto a confirmação do
 * backend não chega, a tela nunca mostra "Visualizada no portal" como se já tivesse
 * acontecido.
 */
export function SuperficieComunicado({
  seguradoId,
  entregaSimuladaId,
  comoSecao,
}: PropriedadesSuperficieComunicado) {
  const ElementoRaiz: 'main' | 'section' = comoSecao ? 'section' : 'main'
  const atributosRaiz = comoSecao ? {} : { id: 'conteudo-principal', tabIndex: -1 }
  const [estadoCarregamento, definirEstadoCarregamento] =
    useState<EstadoCarregamento>('carregando')
  const [comunicado, definirComunicado] = useState<Comunicado | null>(null)
  const [falhaComunicado, definirFalhaComunicado] = useState<ErroComunicado | null>(null)

  const [estadoVisualizacao, definirEstadoVisualizacao] = useState<EstadoVisualizacao>('pendente')
  const [visualizacaoAtual, definirVisualizacaoAtual] =
    useState<VisualizacaoComunicado | null>(null)
  const [falhaVisualizacao, definirFalhaVisualizacao] = useState<ErroComunicado | null>(null)

  const [explicacaoAberta, definirExplicacaoAberta] = useState(false)

  // Trocar de segurado ativo (5.7) nunca deve deixar a explicação de um segurado anterior
  // aberta sobre o contexto do novo (Edge Case da spec de 6.8).
  useEffect(() => {
    definirExplicacaoAberta(false)
  }, [seguradoId])

  useEffect(() => {
    let cancelado = false
    definirEstadoCarregamento('carregando')
    definirComunicado(null)
    definirFalhaComunicado(null)

    getComunicado(seguradoId, entregaSimuladaId)
      .then((encontrado) => {
        if (cancelado) return
        definirComunicado(encontrado)
        definirVisualizacaoAtual(encontrado.visualizacao)
        definirEstadoVisualizacao(encontrado.visualizacao ? 'confirmada' : 'pendente')
        definirEstadoCarregamento('disponivel')
      })
      .catch((causa: unknown) => {
        if (cancelado) return
        definirFalhaComunicado(causa instanceof ErroComunicado ? causa : null)
        definirEstadoCarregamento('indisponivel')
      })

    return () => {
      cancelado = true
    }
  }, [seguradoId, entregaSimuladaId])

  const registrarAbertura = useCallback(async () => {
    definirEstadoVisualizacao('registrando')
    definirFalhaVisualizacao(null)
    try {
      const visualizacao = await registrarVisualizacaoComunicado(seguradoId, entregaSimuladaId)
      definirVisualizacaoAtual(visualizacao)
      definirEstadoVisualizacao('confirmada')
    } catch (causa) {
      definirFalhaVisualizacao(causa instanceof ErroComunicado ? causa : null)
      definirEstadoVisualizacao('erro')
    }
  }, [seguradoId, entregaSimuladaId])

  // Dispara só depois que o comunicado já renderizou com sucesso (estadoCarregamento
  // 'disponivel'), nunca junto do GET que busca o conteúdo.
  useEffect(() => {
    if (estadoCarregamento !== 'disponivel' || visualizacaoAtual !== null) {
      return
    }
    void registrarAbertura()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [estadoCarregamento])

  return (
    <ElementoRaiz className="conteudo" {...atributosRaiz}>
      <p className="rotulo-contexto">Comunicado</p>
      <h1>Seu comunicado preventivo</h1>

      {estadoCarregamento === 'carregando' && (
        <p className="caixa-status" role="status">
          Carregando comunicado…
        </p>
      )}

      {estadoCarregamento === 'indisponivel' && (
        <div className="caixa-status" role="alert">
          <p>
            <strong>Ocorrência:</strong>{' '}
            {falhaComunicado?.ocorrencia ?? 'Falha desconhecida ao consultar o comunicado.'}
          </p>
          <p>
            <strong>Impacto:</strong> {falhaComunicado?.impacto ?? ''}
          </p>
          <p>
            <strong>Próxima ação:</strong> {falhaComunicado?.proximaAcao ?? ''}
          </p>
        </div>
      )}

      {estadoCarregamento === 'disponivel' && comunicado && (
        <>
          <p className="comunicado__aviso-simulacao">
            Comunicado simulado — nenhuma comunicação real foi enviada a você.
          </p>

          <section aria-labelledby="titulo-conteudo-comunicado">
            <h2 id="titulo-conteudo-comunicado">
              {rotuloCanal(comunicado.canal)} · {comunicado.rotulo === 'simulada' ? 'Simulação' : comunicado.rotulo}
            </h2>
            {comunicado.assunto && (
              <p className="comunicado__assunto">
                <strong>Assunto:</strong> {comunicado.assunto}
              </p>
            )}
            <p className="comunicado__corpo">{comunicado.corpo}</p>
          </section>

          <section aria-labelledby="titulo-linha-do-tempo">
            <h2 id="titulo-linha-do-tempo">Linha do tempo</h2>
            <dl className="comunicado__linha-do-tempo">
              <div>
                <dt>Criado</dt>
                <dd>{comunicado.criadoEm}</dd>
              </div>
              <div>
                <dt>Visualização</dt>
                <dd>
                  <SeloVisualizacao
                    estado={estadoVisualizacao}
                    visualizadaEm={visualizacaoAtual?.visualizadaEm ?? null}
                  />
                </dd>
              </div>
            </dl>
          </section>

          {estadoVisualizacao === 'erro' && (
            <div className="comunicado__erro-visualizacao" role="alert">
              <p>
                <strong>Não foi possível confirmar sua visualização.</strong>
              </p>
              <p>
                <strong>Ocorrência:</strong>{' '}
                {falhaVisualizacao?.ocorrencia ?? 'Falha local ao registrar a visualização.'}
              </p>
              <p>
                <strong>Impacto:</strong>{' '}
                {falhaVisualizacao?.impacto ?? 'A visualização ainda não está confirmada.'}
              </p>
              <button className="btn secondary" onClick={() => void registrarAbertura()} type="button">
                Tentar novamente
              </button>
            </div>
          )}

          <button
            className="btn secondary"
            id={`botao-explicacao-${entregaSimuladaId}`}
            onClick={() => definirExplicacaoAberta(true)}
            type="button"
          >
            Ver como esta mensagem foi criada
          </button>
        </>
      )}

      <SuperficieExplicacaoComunicado
        aberto={explicacaoAberta}
        entregaSimuladaId={entregaSimuladaId}
        onFechar={() => definirExplicacaoAberta(false)}
        seguradoId={seguradoId}
      />
    </ElementoRaiz>
  )
}

function SeloVisualizacao({
  estado,
  visualizadaEm,
}: {
  estado: EstadoVisualizacao
  visualizadaEm: string | null
}) {
  if (estado === 'confirmada' && visualizadaEm) {
    return (
      <span className="comunicado__selo-visualizacao" data-estado="confirmada">
        <CheckCircleIcon aria-hidden="true" data-icone-nome="check-circle" size={16} weight="fill" />
        Visualizada no portal em {visualizadaEm}
      </span>
    )
  }
  if (estado === 'erro') {
    return (
      <span className="comunicado__selo-visualizacao" data-estado="erro">
        <WarningIcon aria-hidden="true" data-icone-nome="warning" size={16} />
        Não confirmada
      </span>
    )
  }
  return (
    <span className="comunicado__selo-visualizacao" data-estado="pendente">
      <HourglassIcon aria-hidden="true" data-icone-nome="hourglass" size={16} />
      Confirmando visualização…
    </span>
  )
}
