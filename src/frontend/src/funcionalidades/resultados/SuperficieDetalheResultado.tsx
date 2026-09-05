import type { KeyboardEvent } from 'react'
import { useEffect, useId, useRef, useState } from 'react'
import {
  type DetalheResultado,
  ErroDetalheResultado,
  getDetalheResultado,
} from '../../api/detalheResultado'
import './SuperficieDetalheResultado.css'

const SELETOR_FOCAVEIS = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(', ')

const ROTULOS_CANAL: Record<string, string> = {
  whatsapp: 'WhatsApp',
  email: 'E-mail',
  sms: 'SMS',
}

function rotuloCanal(canal: string): string {
  return ROTULOS_CANAL[canal] ?? canal
}

const AVISO_PREVIA = 'Prévia da simulação — nenhuma comunicação real foi enviada.'

type PrevisaoDeConteudo = { assunto: string | null; corpo: string; rotulada: boolean }

/** Prefere a apresentação já simulada; sem ela, cai na última versão gerada (se houver). */
function conteudoParaPrevia(detalhe: DetalheResultado): PrevisaoDeConteudo | null {
  if (detalhe.apresentacaoSimulada) {
    return {
      assunto: detalhe.apresentacaoSimulada.assunto,
      corpo: detalhe.apresentacaoSimulada.corpo,
      rotulada: true,
    }
  }
  const ultima = detalhe.versoes.at(-1)
  if (!ultima) return null
  return { assunto: ultima.assunto, corpo: ultima.corpo, rotulada: false }
}

type EstadoCarregamento = 'carregando' | 'disponivel' | 'nao-encontrado' | 'indisponivel'

type PropriedadesSuperficieDetalheResultado = {
  /** Controla a presença do drawer no documento. */
  aberto: boolean
  execucaoId: string
  mensagemId: string
  /** Fecha o drawer e devolve o foco à origem. */
  onFechar: () => void
}

/**
 * Drawer de detalhe individual do resultado de uma mensagem simulada (DETALHE-01..08).
 *
 * Só leitura: abrir o drawer não reavalia nada e não aciona a OpenAI. Foco preso na camada
 * ativa e `Esc` devolvendo o foco à origem seguem o mesmo mecanismo do `Modal` (Épico 1) —
 * reimplementado aqui porque este drawer não tem ação de confirmar/cancelar, só fechar.
 */
export function SuperficieDetalheResultado({
  aberto,
  execucaoId,
  mensagemId,
  onFechar,
}: PropriedadesSuperficieDetalheResultado) {
  const identificador = useId()
  const idTitulo = `${identificador}-titulo`
  const referenciaDrawer = useRef<HTMLDivElement>(null)

  const [estadoCarregamento, definirEstadoCarregamento] =
    useState<EstadoCarregamento>('carregando')
  const [detalhe, definirDetalhe] = useState<DetalheResultado | null>(null)
  const [falha, definirFalha] = useState<ErroDetalheResultado | null>(null)

  useEffect(() => {
    if (!aberto) return
    let cancelado = false
    definirEstadoCarregamento('carregando')
    definirDetalhe(null)
    definirFalha(null)

    getDetalheResultado(execucaoId, mensagemId)
      .then((encontrado) => {
        if (cancelado) return
        definirDetalhe(encontrado)
        definirEstadoCarregamento('disponivel')
      })
      .catch((causa: unknown) => {
        if (cancelado) return
        const erro = causa instanceof ErroDetalheResultado ? causa : null
        definirFalha(erro)
        definirEstadoCarregamento(erro?.status === 404 ? 'nao-encontrado' : 'indisponivel')
      })

    return () => {
      cancelado = true
    }
  }, [aberto, execucaoId, mensagemId])

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

  const titulo =
    estadoCarregamento === 'disponivel' && detalhe
      ? `Detalhe do resultado — ${detalhe.nomeSegurado}`
      : 'Detalhe do resultado'

  return (
    <div className="detalhe-resultado-fundo">
      <div
        aria-labelledby={idTitulo}
        aria-modal="true"
        className="detalhe-resultado-drawer"
        onKeyDown={aoTeclar}
        ref={referenciaDrawer}
        role="dialog"
      >
        <h2 id={idTitulo}>{titulo}</h2>

        {estadoCarregamento === 'carregando' && <p role="status">Carregando detalhe…</p>}

        {estadoCarregamento === 'nao-encontrado' && (
          <div role="alert">
            <p>
              <strong>Não encontrado</strong>
            </p>
            <p>Esta mensagem não existe ou não pertence à execução consultada.</p>
          </div>
        )}

        {estadoCarregamento === 'indisponivel' && (
          <div role="alert">
            <p>
              <strong>Ocorrência:</strong>{' '}
              {falha?.ocorrencia ?? 'Falha desconhecida ao consultar o detalhe.'}
            </p>
            <p>
              <strong>Impacto:</strong> {falha?.impacto ?? ''}
            </p>
            <p>
              <strong>Próxima ação:</strong> {falha?.proximaAcao ?? ''}
            </p>
          </div>
        )}

        {estadoCarregamento === 'disponivel' && detalhe && (
          <ConteudoDetalhe detalhe={detalhe} />
        )}

        <div className="detalhe-resultado-acoes">
          <button onClick={onFechar} type="button">
            Fechar
          </button>
        </div>
      </div>
    </div>
  )
}

function ConteudoDetalhe({ detalhe }: { detalhe: DetalheResultado }) {
  const previa = conteudoParaPrevia(detalhe)
  const ultimaVersao = detalhe.versoes.at(-1) ?? null

  return (
    <>
      <dl className="detalhe-resultado-identidade">
        <div>
          <dt>Segurado</dt>
          <dd>{detalhe.nomeSegurado}</dd>
        </div>
        <div>
          <dt>Apólice</dt>
          <dd>{detalhe.apoliceId}</dd>
        </div>
        <div>
          <dt>Canal</dt>
          <dd>{rotuloCanal(detalhe.canal)}</dd>
        </div>
        <div>
          <dt>Estado</dt>
          <dd>{detalhe.estado}</dd>
        </div>
        <div>
          <dt>Criada em</dt>
          <dd>{detalhe.criadoEm}</dd>
        </div>
        <div>
          <dt>Atualizada em</dt>
          <dd>{detalhe.atualizadoEm}</dd>
        </div>
        <div>
          <dt>Evento</dt>
          <dd>
            {detalhe.evento
              ? `${detalhe.evento.tipo} na área ${detalhe.evento.area}`
              : 'Sem evento associado'}
          </dd>
        </div>
        <div>
          <dt>Regra aplicada</dt>
          <dd>
            {detalhe.regraId} (versão {detalhe.regraVersao})
          </dd>
        </div>
      </dl>

      {ultimaVersao && (
        <dl className="detalhe-resultado-aprovacoes" data-secao="aprovacoes">
          <div>
            <dt>Aprovação agêntica</dt>
            <dd>
              {ultimaVersao.avaliacaoCritica === null
                ? 'Ainda não avaliada pelo agente crítico.'
                : ultimaVersao.avaliacaoCritica.aprovada
                  ? 'Aprovada pelo agente crítico.'
                  : 'Reprovada pelo agente crítico.'}
            </dd>
          </div>
          <div>
            <dt>Decisão humana</dt>
            <dd>
              {ultimaVersao.decisoesHumanas.length === 0
                ? 'Nenhuma decisão humana registrada ainda.'
                : `${ultimaVersao.decisoesHumanas.at(-1)?.resultado} por ` +
                  `${ultimaVersao.decisoesHumanas.at(-1)?.perfilResponsavel}.`}
            </dd>
          </div>
        </dl>
      )}

      {detalhe.excecao && (
        <div className="detalhe-resultado-excecao" data-secao="excecao" role="alert">
          <p>
            <strong>Exceção técnica registrada.</strong>
          </p>
          <p>
            <strong>Causa:</strong> {detalhe.excecao.causa}
          </p>
          <p>
            <strong>Tentativas:</strong> {detalhe.excecao.tentativas}
          </p>
          <p>
            <strong>Impacto:</strong> {detalhe.excecao.impacto}
          </p>
        </div>
      )}

      <section aria-labelledby="titulo-previa-canal" data-secao="previa-canal">
        <h3 id="titulo-previa-canal">Prévia do canal</h3>
        <p className="detalhe-resultado-aviso-simulacao">{AVISO_PREVIA}</p>
        {previa === null ? (
          <p>Nenhum conteúdo foi gerado ainda para esta mensagem.</p>
        ) : detalhe.canal === 'email' ? (
          <dl>
            <div>
              <dt>Assunto</dt>
              <dd>{previa.assunto}</dd>
            </div>
            <div>
              <dt>Corpo</dt>
              <dd>{previa.corpo}</dd>
            </div>
            <div>
              <dt>Limite do canal</dt>
              <dd>
                {detalhe.limiteCanalAssunto} caracteres (assunto), {detalhe.limiteCanalCorpo}{' '}
                caracteres (corpo)
              </dd>
            </div>
          </dl>
        ) : (
          <dl>
            <div>
              <dt>Corpo</dt>
              <dd>{previa.corpo}</dd>
            </div>
            <div>
              <dt>Limite do canal</dt>
              <dd>{detalhe.limiteCanalCorpo} caracteres</dd>
            </div>
          </dl>
        )}
      </section>

      <section aria-labelledby="titulo-versoes" data-secao="versoes">
        <h3 id="titulo-versoes">Versões</h3>
        {detalhe.versoes.length === 0 ? (
          <p>Nenhuma versão gerada ainda.</p>
        ) : (
          <ol>
            {detalhe.versoes.map((versao) => (
              <li data-tentativa={versao.numeroTentativa} key={versao.numeroTentativa}>
                <p>
                  <strong>Tentativa {versao.numeroTentativa}</strong> —{' '}
                  {versao.valida ? 'válida' : `inválida (${versao.motivoInvalidez})`}
                </p>
                <p>
                  Crítico:{' '}
                  {versao.avaliacaoCritica === null
                    ? 'ainda não avaliada'
                    : versao.avaliacaoCritica.aprovada
                      ? 'aprovada'
                      : `reprovada (${versao.avaliacaoCritica.motivos.join(', ')})`}
                </p>
                {versao.decisoesHumanas.length === 0 ? (
                  <p>Nenhuma decisão humana registrada ainda.</p>
                ) : (
                  <ul>
                    {versao.decisoesHumanas.map((decisao, indice) => (
                      <li key={`${versao.numeroTentativa}-${indice}`}>
                        {decisao.resultado} por {decisao.perfilResponsavel}
                        {decisao.justificativa ? `: ${decisao.justificativa}` : ''}
                      </li>
                    ))}
                  </ul>
                )}
              </li>
            ))}
          </ol>
        )}
      </section>
    </>
  )
}
