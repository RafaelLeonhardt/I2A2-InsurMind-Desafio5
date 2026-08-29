import { useState } from 'react'
import {
  ErroRestauracao,
  type ResultadoRestauracao,
  restaurarDadosSinteticos,
} from '../../api/dadosSinteticos'
import { Modal } from '../../componentes/Modal'

type EstadoRestauracao = 'inicial' | 'confirmacao' | 'restaurando' | 'concluido' | 'falha'

const OBJETO = 'Dados sintéticos da demonstração'
const IMPACTO = 'As alterações locais feitas nos dados de referência serão perdidas.'

const FALHA_DESCONHECIDA = new ErroRestauracao({
  codigo: 'falha_inesperada',
  correlacaoId: null,
  ocorrencia: 'A restauração não pôde ser concluída.',
  impacto: 'O conjunto de dados anterior foi preservado e continua consultável.',
  proximaAcao: 'Tente novamente; se persistir, verifique o backend local.',
  status: null,
})

/** Superfície administrativa que restaura os dados sintéticos da demonstração. */
export function RestaurarDemonstracao() {
  const [estado, definirEstado] = useState<EstadoRestauracao>('inicial')
  const [falha, definirFalha] = useState<ErroRestauracao | null>(null)
  const [resultado, definirResultado] = useState<ResultadoRestauracao | null>(null)

  async function confirmar() {
    definirEstado('restaurando')
    definirFalha(null)
    try {
      definirResultado(await restaurarDadosSinteticos())
      definirEstado('concluido')
    } catch (causa) {
      definirFalha(causa instanceof ErroRestauracao ? causa : FALHA_DESCONHECIDA)
      definirEstado('falha')
    }
  }

  function fechar() {
    definirEstado('inicial')
  }

  const emProcessamento = estado === 'restaurando'
  const encerrado = estado === 'concluido' || estado === 'falha'

  return (
    <main className="conteudo" id="conteudo-principal" tabIndex={-1}>
      <p className="rotulo-contexto">Área administrativa</p>
      <h1>Restaurar demonstração</h1>
      <p className="introducao">
        Repõe o conjunto sintético versionado da demonstração para repetir os cenários a partir de
        um estado conhecido.
      </p>
      <dl>
        <div>
          <dt>Objeto da restauração</dt>
          <dd>{OBJETO}</dd>
        </div>
        <div>
          <dt>Origem dos dados</dt>
          <dd>Conjunto sintético versionado no repositório, sem qualquer dado real.</dd>
        </div>
      </dl>
      <button onClick={() => definirEstado('confirmacao')} type="button">
        Restaurar demonstração
      </button>

      <Modal
        aberto={estado !== 'inicial'}
        confirmacaoDesabilitada={emProcessamento}
        impacto={IMPACTO}
        objeto={OBJETO}
        onConfirmar={encerrado ? fechar : confirmar}
        onFechar={fechar}
        podeFechar={!emProcessamento}
        rotuloCancelar={encerrado ? 'Fechar' : 'Cancelar'}
        rotuloConfirmar={rotuloDaConfirmacao(estado)}
        titulo="Restaurar demonstração"
      >
        {emProcessamento && <p role="status">Restaurando os dados sintéticos…</p>}
        {estado === 'concluido' && (
          <p role="status">
            Dados sintéticos restaurados
            {resultado ? ` em ${resultado.restauradoEm}` : ''}.
          </p>
        )}
        {estado === 'falha' && falha && (
          <div role="alert">
            <p>
              <strong>Ocorrência:</strong> {falha.ocorrencia}
            </p>
            <p>
              <strong>Impacto:</strong> {falha.impacto}
            </p>
            <p>
              <strong>Próxima ação:</strong> {falha.proximaAcao}
            </p>
          </div>
        )}
      </Modal>
    </main>
  )
}

function rotuloDaConfirmacao(estado: EstadoRestauracao) {
  if (estado === 'restaurando') {
    return 'Restaurando…'
  }
  if (estado === 'concluido') {
    return 'Concluir'
  }
  if (estado === 'falha') {
    return 'Fechar aviso'
  }
  return 'Confirmar restauração'
}
