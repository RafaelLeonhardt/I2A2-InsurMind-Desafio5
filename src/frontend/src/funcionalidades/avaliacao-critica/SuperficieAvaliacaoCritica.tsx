import {
  HourglassIcon,
  RobotIcon,
  RulerIcon,
  ThumbsDownIcon,
  ThumbsUpIcon,
  UserIcon,
} from '@phosphor-icons/react'
import { useCallback, useEffect, useState } from 'react'
import {
  type AvaliacaoCritica,
  ErroAvaliacaoCritica,
  getAvaliacaoCritica,
} from '../../api/avaliacaoCritica'
import './SuperficieAvaliacaoCritica.css'

/** Nome acessível de cada um dos sete critérios fechados avaliados pelo crítico. */
const ROTULOS_CRITERIO: Record<string, string> = {
  tom: 'Tom preventivo, não alarmista',
  utilidade: 'Utilidade da orientação',
  clareza: 'Clareza do texto',
  seguranca: 'Segurança da orientação',
  promessa_indevida: 'Ausência de promessa de cobertura',
  distincao_oficial: 'Distinção de um alerta oficial',
  adequacao_canal: 'Adequação ao canal',
}

function rotuloCriterio(categoria: string): string {
  return ROTULOS_CRITERIO[categoria] ?? categoria
}

/**
 * Cor de cada origem de decisão, aplicada como propriedade CSS do próprio elemento.
 *
 * A cor mora aqui, e não só na folha de estilo, porque a distinção entre a aprovação do
 * agente e a decisão humana é um requisito (CRIT-05), não um detalhe de tema: assim ela é
 * observável no elemento renderizado e não pode ser colapsada sem quebrar o teste.
 */
const CORES_ORIGEM: Record<string, string> = {
  agente_ia: '#6b21a8',
  regras_deterministicas: '#15803d',
  decisao_humana: '#a16207',
}

function duracaoLegivel(duracaoMs: number): string {
  return `${Math.round(duracaoMs)} ms`
}

type EstadoCarregamento = 'carregando' | 'disponivel' | 'indisponivel'

type PropriedadesSuperficieAvaliacaoCritica = {
  mensagemId: string
  versaoId: string
  embutido?: boolean
}

/**
 * Origem de uma decisão sobre a mesma versão de mensagem.
 *
 * As três são deliberadamente distintas em rótulo, ícone e cor: a decisão do agente de IA
 * nunca deve ser lida como a validação determinística que a antecede, nem como a decisão
 * humana que ainda não aconteceu (CRIT-05, CRIT-09).
 */
function Origem({
  origem,
  rotulo,
  veredito,
  detalhe,
  children,
}: {
  origem: string
  rotulo: string
  veredito: string
  detalhe?: string | null
  children: React.ReactNode
}) {
  return (
    <li
      className={`avaliacao-critica__origem avaliacao-critica__origem--${origem}`}
      data-origem={origem}
      style={{ '--cor-origem': CORES_ORIGEM[origem] } as React.CSSProperties}
    >
      {children}
      <span className="avaliacao-critica__origem-rotulo">{rotulo}</span>
      <span className="avaliacao-critica__origem-veredito">{veredito}</span>
      {detalhe && <p className="avaliacao-critica__origem-detalhe">{detalhe}</p>}
    </li>
  )
}

/**
 * Superfície do detalhe de uma avaliação crítica (CRIT-08, CRIT-09).
 *
 * Só leitura: abrir o detalhe não reavalia nada e não aciona a OpenAI. O texto explica a
 * decisão em linguagem acessível sem esconder de onde ela veio — a decisão do agente de IA
 * aparece separada da validação por regras fixas e da decisão humana ainda pendente.
 */
export function SuperficieAvaliacaoCritica({
  mensagemId,
  versaoId,
  embutido = false,
}: PropriedadesSuperficieAvaliacaoCritica) {
  const [estadoCarregamento, definirEstadoCarregamento] = useState<EstadoCarregamento>('carregando')
  const [avaliacao, definirAvaliacao] = useState<AvaliacaoCritica | null>(null)
  const [falha, definirFalha] = useState<ErroAvaliacaoCritica | null>(null)

  const consultar = useCallback(async () => {
    try {
      const resultado = await getAvaliacaoCritica(mensagemId, versaoId)
      definirAvaliacao(resultado)
      definirFalha(null)
      definirEstadoCarregamento('disponivel')
    } catch (causa) {
      definirFalha(causa instanceof ErroAvaliacaoCritica ? causa : null)
      definirEstadoCarregamento('indisponivel')
    }
  }, [mensagemId, versaoId])

  useEffect(() => {
    definirEstadoCarregamento('carregando')
    definirAvaliacao(null)
    void consultar()
  }, [consultar])

  const conteudo = (
    <section aria-labelledby="titulo-avaliacao-critica" className="avaliacao-critica">
      <h2 id="titulo-avaliacao-critica">Avaliação da mensagem</h2>
      <p>
        Um agente de IA avaliou o conteúdo desta versão da mensagem contra critérios de
        qualidade e segurança. Essa avaliação é separada da validação por regras fixas, que
        já havia conferido campos obrigatórios e tamanho, e não substitui a decisão humana.
      </p>

      {estadoCarregamento === 'carregando' && <p role="status">Carregando avaliação…</p>}

      {estadoCarregamento === 'indisponivel' && (
        <div role="alert">
          <p>
            <strong>Ocorrência:</strong>{' '}
            {falha?.ocorrencia ?? 'Falha desconhecida ao consultar a avaliação.'}
          </p>
          <p>
            <strong>Impacto:</strong> {falha?.impacto ?? ''}
          </p>
          <p>
            <strong>Próxima ação:</strong> {falha?.proximaAcao ?? ''}
          </p>
        </div>
      )}

      {estadoCarregamento === 'disponivel' && avaliacao && (
        <>
          <ul className="avaliacao-critica__origens">
            <Origem
              origem="agente_ia"
              rotulo="Decisão do agente de IA"
              veredito={
                avaliacao.aprovada
                  ? 'Aprovada pelo agente de IA'
                  : 'Reprovada pelo agente de IA'
              }
            >
              <RobotIcon aria-hidden="true" data-icone-nome="robot" size={18} weight="fill" />
            </Origem>
            <Origem
              origem="regras_deterministicas"
              rotulo="Validação por regras fixas"
              veredito={
                avaliacao.validacaoDeterministica.valida
                  ? 'Aprovada pelas regras fixas'
                  : 'Reprovada pelas regras fixas'
              }
              detalhe={avaliacao.validacaoDeterministica.motivoInvalidez}
            >
              <RulerIcon aria-hidden="true" data-icone-nome="ruler" size={18} weight="fill" />
            </Origem>
            <Origem
              origem="decisao_humana"
              rotulo="Decisão humana"
              veredito="Ainda não tomada"
              detalhe="Nenhuma pessoa revisou esta mensagem até agora."
            >
              <UserIcon aria-hidden="true" data-icone-nome="user" size={18} weight="fill" />
            </Origem>
          </ul>

          <dl className="avaliacao-critica__identificacao">
            <div>
              <dt>Versão avaliada</dt>
              <dd>{avaliacao.versaoMensagemId}</dd>
            </div>
            <div>
              <dt>Tentativa de geração</dt>
              <dd>{avaliacao.numeroTentativa}ª tentativa</dd>
            </div>
            <div>
              <dt>Agente</dt>
              <dd>{avaliacao.agente}</dd>
            </div>
            <div>
              <dt>Modelo</dt>
              <dd>{avaliacao.modelo}</dd>
            </div>
            <div>
              <dt>Duração da avaliação</dt>
              <dd>{duracaoLegivel(avaliacao.duracaoMs)}</dd>
            </div>
          </dl>

          <h3>Critérios avaliados</h3>
          <ul className="avaliacao-critica__criterios">
            {avaliacao.criterios.map((criterio) => (
              <li data-criterio={criterio} key={criterio}>
                {rotuloCriterio(criterio)}
              </li>
            ))}
          </ul>

          <h3>Motivos da decisão</h3>
          {avaliacao.motivos.length === 0 ? (
            <p className="avaliacao-critica__sem-motivos">
              <ThumbsUpIcon
                aria-hidden="true"
                data-icone-nome="thumbs-up"
                size={18}
                weight="fill"
              />
              <span>
                O agente de IA não registrou nenhum motivo de reprovação para esta versão.
              </span>
            </p>
          ) : (
            <ul className="avaliacao-critica__motivos">
              {avaliacao.motivos.map((motivo) => (
                <li data-categoria={motivo.categoria} key={motivo.categoria}>
                  <ThumbsDownIcon
                    aria-hidden="true"
                    data-icone-nome="thumbs-down"
                    size={18}
                    weight="fill"
                  />
                  <span className="avaliacao-critica__motivo-categoria">
                    {rotuloCriterio(motivo.categoria)}
                  </span>
                  <p className="avaliacao-critica__motivo-justificativa">
                    {motivo.justificativa}
                  </p>
                </li>
              ))}
            </ul>
          )}

          <p className="avaliacao-critica__nota">
            <HourglassIcon
              aria-hidden="true"
              data-icone-nome="hourglass"
              size={18}
              weight="fill"
            />
            <span>
              A aprovação acima é do agente de IA, não de uma pessoa. A revisão humana
              continua pendente e pode decidir de outra forma.
            </span>
          </p>
        </>
      )}
    </section>
  )

  if (embutido) return conteudo

  return (
    <main className="conteudo" id="conteudo-principal" tabIndex={-1}>
      <p className="rotulo-contexto">Produção de mensagens</p>
      <h1>Detalhe da avaliação</h1>
      {conteudo}
    </main>
  )
}
