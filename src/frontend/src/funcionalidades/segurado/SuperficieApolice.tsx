import { useCallback, useEffect, useRef, useState } from 'react'
import {
  type ApoliceSegurado,
  ErroApoliceSegurado,
  type ExplicacaoApolice,
  getApolice,
  getExplicacaoApolice,
} from '../../api/apoliceSegurado'
import { ErroContexto, getSeguradoPadrao } from '../../api/contexto'

type EstadoApolice = 'carregando' | 'pronta' | 'nao_encontrada' | 'erro'
type EstadoExplicacao = 'carregando' | 'pronta' | 'nao_encontrada' | 'erro'

type FalhaApolice = {
  ocorrencia: string
  impacto: string
  proximaAcao: string
}

type PropriedadesSuperficieApolice = {
  /** Segurado a exibir. Ausente hoje: resolve o segurado padrão internamente (mesmo
   * seam de VisaoGeralSegurado, 5.1). */
  seguradoId?: string
  /** Quando informado, mostra também a explicação de critérios desta elegibilidade
   * (APOLICE-02) — normalmente aberta a partir do detalhe de um alerta (5.2). */
  elegibilidadeIdExplicacao?: string
}

const ROTULOS_TIPO: Record<string, string> = {
  residencial: 'Residencial',
  automovel: 'Automóvel',
}

const ROTULOS_ESTADO_OBJETIVO: Record<string, string> = {
  ativa: 'Ativa',
  cancelada: 'Cancelada',
  suspensa: 'Suspensa',
  expirada: 'Expirada',
}

const ROTULOS_CANAL: Record<string, string> = {
  whatsapp: 'WhatsApp',
  email: 'E-mail',
  sms: 'SMS',
}

function rotuloTipo(tipo: string): string {
  return ROTULOS_TIPO[tipo] ?? tipo
}

function rotuloEstadoObjetivo(estado: string): string {
  return ROTULOS_ESTADO_OBJETIVO[estado] ?? estado
}

function rotuloCanal(canal: string): string {
  return ROTULOS_CANAL[canal] ?? canal
}

function falhaDe(causa: unknown): FalhaApolice {
  if (causa instanceof ErroApoliceSegurado || causa instanceof ErroContexto) {
    return { ocorrencia: causa.ocorrencia, impacto: causa.impacto, proximaAcao: causa.proximaAcao }
  }
  return {
    ocorrencia: 'Falha desconhecida ao consultar a apólice.',
    impacto: 'Os dados da apólice podem estar desatualizados.',
    proximaAcao: 'Verifique se o backend local está disponível e tente novamente.',
  }
}

/**
 * Superfície "Apólice" do perfil Segurado: dados cadastrais, estado objetivo e a
 * explicação de como uma execução comparou os critérios relevantes à apólice
 * (APOLICE-01..06, 5.3).
 *
 * O estado objetivo (`cancelada`/`suspensa`/`expirada`) é sempre apresentado como texto
 * informativo comum — nunca com `role="alert"` nem aparência de falha técnica
 * (APOLICE-03): uma apólice inativa é uma condição normal do domínio, não um erro.
 */
export function SuperficieApolice({
  seguradoId,
  elegibilidadeIdExplicacao,
}: PropriedadesSuperficieApolice) {
  const [estado, definirEstado] = useState<EstadoApolice>('carregando')
  const [apolice, definirApolice] = useState<ApoliceSegurado | null>(null)
  const [falha, definirFalha] = useState<FalhaApolice | null>(null)

  const [estadoExplicacao, definirEstadoExplicacao] = useState<EstadoExplicacao>('carregando')
  const [explicacao, definirExplicacao] = useState<ExplicacaoApolice | null>(null)
  const [falhaExplicacao, definirFalhaExplicacao] = useState<FalhaApolice | null>(null)

  const requisicaoApoliceAtualRef = useRef(0)
  const requisicaoExplicacaoAtualRef = useRef(0)

  const carregar = useCallback(async () => {
    const requisicao = ++requisicaoApoliceAtualRef.current
    definirEstado('carregando')
    definirFalha(null)
    try {
      const idSegurado = seguradoId ?? (await getSeguradoPadrao()).id
      const encontrada = await getApolice(idSegurado)
      // Uma requisição mais recente já pode ter chegado primeiro (troca de segurado
      // rápida, 5.7) — nunca sobrescrever a apólice do segurado novo com a do anterior.
      if (requisicao !== requisicaoApoliceAtualRef.current) return
      definirApolice(encontrada)
      definirEstado('pronta')
    } catch (causa) {
      if (requisicao !== requisicaoApoliceAtualRef.current) return
      if (causa instanceof ErroApoliceSegurado && causa.status === 404) {
        definirEstado('nao_encontrada')
        return
      }
      definirFalha(falhaDe(causa))
      definirEstado('erro')
    }
  }, [seguradoId])

  useEffect(() => {
    void carregar()
  }, [carregar])

  const carregarExplicacao = useCallback(async () => {
    if (!elegibilidadeIdExplicacao) return
    const requisicao = ++requisicaoExplicacaoAtualRef.current
    definirEstadoExplicacao('carregando')
    definirFalhaExplicacao(null)
    try {
      const idSegurado = seguradoId ?? (await getSeguradoPadrao()).id
      const encontrada = await getExplicacaoApolice(idSegurado, elegibilidadeIdExplicacao)
      if (requisicao !== requisicaoExplicacaoAtualRef.current) return
      definirExplicacao(encontrada)
      definirEstadoExplicacao('pronta')
    } catch (causa) {
      if (requisicao !== requisicaoExplicacaoAtualRef.current) return
      if (causa instanceof ErroApoliceSegurado && causa.status === 404) {
        definirEstadoExplicacao('nao_encontrada')
        return
      }
      definirFalhaExplicacao(falhaDe(causa))
      definirEstadoExplicacao('erro')
    }
  }, [seguradoId, elegibilidadeIdExplicacao])

  useEffect(() => {
    void carregarExplicacao()
  }, [carregarExplicacao])

  if (estado === 'carregando') {
    return (
      <main className="conteudo" id="conteudo-principal" tabIndex={-1}>
        <p role="status">Carregando apólice…</p>
      </main>
    )
  }

  if (estado === 'nao_encontrada') {
    return (
      <main className="conteudo" id="conteudo-principal" tabIndex={-1}>
        <h1>Não encontrada</h1>
        <p>Esta apólice não existe ou não pertence a você.</p>
      </main>
    )
  }

  if (estado === 'erro') {
    return (
      <main className="conteudo" id="conteudo-principal" tabIndex={-1}>
        <div role="alert">
          <h1>Não foi possível carregar sua apólice</h1>
          <p>
            <strong>Ocorrência:</strong> {falha?.ocorrencia}
          </p>
          <p>
            <strong>Impacto:</strong> {falha?.impacto}
          </p>
          <p>
            <strong>Próxima ação:</strong> {falha?.proximaAcao}
          </p>
          <button onClick={() => void carregar()} type="button">
            Tentar novamente
          </button>
        </div>
      </main>
    )
  }

  if (!apolice) return null

  return (
    <main className="conteudo" id="conteudo-principal" tabIndex={-1}>
      <h1>Sua apólice</h1>
      <p className="introducao">
        Situação atual: <strong>{rotuloEstadoObjetivo(apolice.estadoObjetivo)}</strong>
      </p>

      <dl>
        <div>
          <dt>Número</dt>
          <dd>{apolice.numero}</dd>
        </div>
        <div>
          <dt>Tipo</dt>
          <dd>{rotuloTipo(apolice.tipo)}</dd>
        </div>
        <div>
          <dt>Vigência</dt>
          <dd>
            {apolice.vigenciaInicio} a {apolice.vigenciaFim}
          </dd>
        </div>
        <div>
          <dt>Endereço do risco</dt>
          <dd>{apolice.enderecoRiscoSintetico}</dd>
        </div>
      </dl>

      <section aria-labelledby="titulo-coberturas-apolice">
        <h2 id="titulo-coberturas-apolice">Coberturas</h2>
        <ul>
          {apolice.coberturas.map((cobertura) => (
            <li key={cobertura}>{cobertura}</li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="titulo-preferencias-apolice">
        <h2 id="titulo-preferencias-apolice">Preferências de comunicação</h2>
        <dl>
          <div>
            <dt>Canal preferencial</dt>
            <dd>{rotuloCanal(apolice.canalPreferido)}</dd>
          </div>
          <div>
            <dt>Participação em alertas</dt>
            <dd>{apolice.participaDeAlertas ? 'Participando' : 'Não participando'}</dd>
          </div>
        </dl>
        <p className="aviso-efeito-futuro">
          Alterações nestas preferências afetam apenas decisões futuras — comunicações já
          enviadas não são refeitas.
        </p>
      </section>

      {elegibilidadeIdExplicacao && (
        <section aria-labelledby="titulo-explicacao-apolice">
          <h2 id="titulo-explicacao-apolice">Como sua apólice participou desta decisão</h2>

          {estadoExplicacao === 'carregando' && <p role="status">Carregando explicação…</p>}

          {estadoExplicacao === 'nao_encontrada' && (
            <p>Esta explicação não existe ou não pertence a você.</p>
          )}

          {estadoExplicacao === 'erro' && (
            <div role="alert">
              <p>
                <strong>Ocorrência:</strong> {falhaExplicacao?.ocorrencia}
              </p>
              <p>
                <strong>Próxima ação:</strong> {falhaExplicacao?.proximaAcao}
              </p>
            </div>
          )}

          {estadoExplicacao === 'pronta' && explicacao && (
            <>
              <p className="aviso-sem-promessa-cobertura">
                Esta explicação mostra como cada critério foi comparado; ela não confirma
                cobertura, indenização nem decisão de sinistro.
              </p>
              <ul>
                {explicacao.criterios.map((criterio) => (
                  <li key={criterio.operando}>
                    <strong>{criterio.operando}:</strong> {criterio.justificativa}
                  </li>
                ))}
              </ul>
            </>
          )}
        </section>
      )}
    </main>
  )
}
