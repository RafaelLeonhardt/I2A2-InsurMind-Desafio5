import {
  ArrowsClockwiseIcon,
  CheckCircleIcon,
  CircleNotchIcon,
  HourglassIcon,
  ProhibitIcon,
  ThumbsUpIcon,
  WarningIcon,
} from '@phosphor-icons/react'
import { useCallback, useEffect, useState } from 'react'
import { type Mensagem, ErroMensagens, getMensagens } from '../../api/mensagens'
import './SuperficieGeracaoMensagens.css'

type Categoria = 'aprovada' | 'gerada' | 'gerando' | 'nova-tentativa' | 'reprovada' | 'excecao'

type ItemGeracao = {
  id: string
  canal: string
  categoria: Categoria
  rotulo: string
  tentativa: string
  motivo: string | null
}

const ROTULOS_CANAL: Record<string, string> = {
  whatsapp: 'WhatsApp',
  email: 'E-mail',
  sms: 'SMS',
}

const ROTULOS_CATEGORIA: Record<Categoria, string> = {
  aprovada: 'Aprovada pelo crítico — aguardando revisão',
  gerada: 'Mensagem gerada — em avaliação',
  gerando: 'Gerando mensagem…',
  'nova-tentativa': 'Aguardando nova tentativa',
  reprovada: 'Reprovada em todas as tentativas',
  excecao: 'Falha de integração com a OpenAI',
}

const CORES_CATEGORIA: Record<Categoria, string> = {
  aprovada: '#166534',
  gerada: '#15803d',
  gerando: '#1d4ed8',
  'nova-tentativa': '#a16207',
  reprovada: '#9a3412',
  excecao: '#b91c1c',
}

/**
 * Classifica uma mensagem só pelo que a API já persistiu.
 *
 * As seis categorias são deliberadamente distintas: uma aprovação do crítico não pode ser
 * lida como uma mensagem ainda em avaliação, e a reprovação de conteúdo depois das três
 * tentativas (`falhou_conteudo`) não pode ser lida como uma falha de integração com a OpenAI
 * (`falhou_integracao_ia`) — as duas são exceções, mas de causas diferentes (REGEN-05).
 */
function classificar(mensagem: Mensagem): Categoria {
  if (mensagem.estado === 'falhou_integracao_ia') return 'excecao'
  if (mensagem.estado === 'falhou_conteudo') return 'reprovada'
  if (mensagem.estado === 'aguardando_revisao' || mensagem.estado === 'aprovada') {
    return 'aprovada'
  }
  if (mensagem.estado === 'gerando') {
    return mensagem.versaoAtual !== null && !mensagem.versaoAtual.valida
      ? 'nova-tentativa'
      : 'gerando'
  }
  return 'gerada'
}

function paraItem(mensagem: Mensagem): ItemGeracao {
  const categoria = classificar(mensagem)
  return {
    id: mensagem.id,
    canal: ROTULOS_CANAL[mensagem.canal] ?? mensagem.canal,
    categoria,
    rotulo: ROTULOS_CATEGORIA[categoria],
    tentativa: `Tentativa ${mensagem.tentativaAtual} de ${mensagem.limiteTentativas}`,
    motivo: mensagem.versaoAtual?.valida === false ? mensagem.versaoAtual.motivoInvalidez : null,
  }
}

function IconeCategoria({ categoria }: { categoria: Categoria }) {
  if (categoria === 'aprovada') {
    return <ThumbsUpIcon aria-hidden="true" data-icone-nome="thumbs-up" size={18} weight="fill" />
  }
  if (categoria === 'gerada') {
    return (
      <CheckCircleIcon aria-hidden="true" data-icone-nome="check-circle" size={18} weight="fill" />
    )
  }
  if (categoria === 'gerando') {
    return <CircleNotchIcon aria-hidden="true" data-icone-nome="circle-notch" size={18} />
  }
  if (categoria === 'nova-tentativa') {
    return <HourglassIcon aria-hidden="true" data-icone-nome="hourglass" size={18} weight="fill" />
  }
  if (categoria === 'reprovada') {
    return <ProhibitIcon aria-hidden="true" data-icone-nome="prohibit" size={18} weight="fill" />
  }
  return <WarningIcon aria-hidden="true" data-icone-nome="warning" size={18} weight="fill" />
}

type EstadoCarregamento = 'carregando' | 'disponivel' | 'indisponivel'

type PropriedadesSuperficieGeracaoMensagens = {
  execucaoId: string
  embutido?: boolean
}

/**
 * Superfície de acompanhamento da geração de mensagens (GERAR-11, GERAR-12; REGEN-11, 12).
 *
 * Reconstrói etapa e progresso inteiramente da API a cada montagem, a partir do que está
 * persistido. É só leitura: nenhuma ação desta tela inicia ou reenvia geração — quem aciona
 * o agente redator é o backend, ao entrar em `processando_mensagens`. Recarregar a página,
 * portanto, nunca duplica mensagem.
 *
 * Cada item mostra etapa, tentativa atual e limite, aprovações e exceções (REGEN-11). Toda
 * mudança de estado é comunicada por texto, ícone e cor ao mesmo tempo, nunca só por cor, e
 * chega ao leitor de tela por `aria-live="polite"`: a região se anuncia sem roubar o foco do
 * teclado, que permanece onde Marina o deixou (REGEN-12).
 */
export function SuperficieGeracaoMensagens({
  execucaoId,
  embutido = false,
}: PropriedadesSuperficieGeracaoMensagens) {
  const [estadoCarregamento, definirEstadoCarregamento] = useState<EstadoCarregamento>('carregando')
  const [mensagens, definirMensagens] = useState<Mensagem[]>([])
  const [falha, definirFalha] = useState<ErroMensagens | null>(null)

  const consultar = useCallback(async () => {
    try {
      const resultado = await getMensagens(execucaoId)
      definirMensagens(resultado)
      definirFalha(null)
      definirEstadoCarregamento('disponivel')
    } catch (causa) {
      definirFalha(causa instanceof ErroMensagens ? causa : null)
      definirEstadoCarregamento('indisponivel')
    }
  }, [execucaoId])

  useEffect(() => {
    definirEstadoCarregamento('carregando')
    definirMensagens([])
    void consultar()
  }, [consultar])

  const itens = mensagens.map(paraItem)
  const geradas = itens.filter(
    (item) => item.categoria === 'gerada' || item.categoria === 'aprovada'
  ).length
  const aprovadas = itens.filter((item) => item.categoria === 'aprovada').length
  const excecoes = itens.filter(
    (item) => item.categoria === 'excecao' || item.categoria === 'reprovada'
  ).length

  const conteudo = (
    <section aria-labelledby="titulo-geracao-mensagens" className="geracao-mensagens">
      <h2 id="titulo-geracao-mensagens">Geração de mensagens</h2>
      <p>
        O progresso abaixo vem inteiramente do que o backend já registrou. A geração é
        automática por item elegível: esta tela apenas acompanha, nunca dispara nem repete.
      </p>

      {estadoCarregamento === 'carregando' && <p role="status">Carregando mensagens…</p>}

      {estadoCarregamento === 'indisponivel' && (
        <div role="alert">
          <p>
            <strong>Ocorrência:</strong>{' '}
            {falha?.ocorrencia ?? 'Falha desconhecida ao consultar as mensagens.'}
          </p>
          <p>
            <strong>Impacto:</strong> {falha?.impacto ?? ''}
          </p>
          <p>
            <strong>Próxima ação:</strong> {falha?.proximaAcao ?? ''}
          </p>
        </div>
      )}

      {estadoCarregamento === 'disponivel' && (
        <>
          <p className="geracao-mensagens__resumo" role="status">
            {geradas} de {itens.length} mensagens geradas
          </p>
          <p className="geracao-mensagens__resumo">
            {aprovadas} aprovadas pelo crítico, {excecoes} em exceção
          </p>
          <ul aria-live="polite" className="geracao-mensagens__lista">
            {itens.length === 0 && <li>Nenhuma mensagem registrada até o momento.</li>}
            {itens.map((item) => (
              <li
                className={`geracao-mensagens__item geracao-mensagens__item--${item.categoria}`}
                data-categoria={item.categoria}
                key={item.id}
                style={{ '--cor-categoria': CORES_CATEGORIA[item.categoria] } as React.CSSProperties}
              >
                <IconeCategoria categoria={item.categoria} />
                <span className="geracao-mensagens__canal">{item.canal}</span>
                <span>{item.rotulo}</span>
                <span className="geracao-mensagens__tentativa">{item.tentativa}</span>
                {item.motivo && <p className="geracao-mensagens__motivo">{item.motivo}</p>}
              </li>
            ))}
          </ul>
          <button onClick={() => void consultar()} type="button">
            <ArrowsClockwiseIcon aria-hidden="true" data-icone-nome="arrows-clockwise" size={18} />
            <span>Atualizar progresso</span>
          </button>
        </>
      )}
    </section>
  )

  if (embutido) return conteudo

  return (
    <main className="conteudo" id="conteudo-principal" tabIndex={-1}>
      <p className="rotulo-contexto">Produção de mensagens</p>
      <h1>Produção de mensagens</h1>
      {conteudo}
    </main>
  )
}
