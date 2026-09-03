import {
  ArrowsClockwiseIcon,
  CheckCircleIcon,
  CircleNotchIcon,
  HourglassIcon,
  WarningIcon,
} from '@phosphor-icons/react'
import { useCallback, useEffect, useState } from 'react'
import { type Mensagem, ErroMensagens, getMensagens } from '../../api/mensagens'
import './SuperficieGeracaoMensagens.css'

type Categoria = 'gerada' | 'gerando' | 'nova-tentativa' | 'excecao'

type ItemGeracao = {
  id: string
  canal: string
  categoria: Categoria
  rotulo: string
  motivo: string | null
}

const ROTULOS_CANAL: Record<string, string> = {
  whatsapp: 'WhatsApp',
  email: 'E-mail',
  sms: 'SMS',
}

const ROTULOS_CATEGORIA: Record<Categoria, string> = {
  gerada: 'Mensagem gerada — em avaliação',
  gerando: 'Gerando mensagem…',
  'nova-tentativa': 'Aguardando nova tentativa',
  excecao: 'Falha de integração com a OpenAI',
}

/**
 * Classifica uma mensagem só pelo que a API já persistiu.
 *
 * Uma mensagem em `gerando` cuja versão atual foi recusada pela validação determinística
 * não está mais em andamento: ela aguarda a política de nova tentativa (História 3.4).
 */
function classificar(mensagem: Mensagem): Categoria {
  if (mensagem.estado === 'falhou_integracao_ia' || mensagem.estado === 'falhou_conteudo') {
    return 'excecao'
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
    motivo: mensagem.versaoAtual?.valida === false ? mensagem.versaoAtual.motivoInvalidez : null,
  }
}

function IconeCategoria({ categoria }: { categoria: Categoria }) {
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
  return <WarningIcon aria-hidden="true" data-icone-nome="warning" size={18} weight="fill" />
}

type EstadoCarregamento = 'carregando' | 'disponivel' | 'indisponivel'

type PropriedadesSuperficieGeracaoMensagens = {
  execucaoId: string
  embutido?: boolean
}

/**
 * Superfície de acompanhamento da geração de mensagens (GERAR-11, GERAR-12).
 *
 * Reconstrói etapa e progresso inteiramente da API a cada montagem, a partir do que está
 * persistido. É só leitura: nenhuma ação desta tela inicia ou reenvia geração — quem aciona
 * o agente redator é o backend, ao entrar em `processando_mensagens`. Recarregar a página,
 * portanto, nunca duplica mensagem.
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
  const geradas = itens.filter((item) => item.categoria === 'gerada').length

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
          <ul aria-live="polite" className="geracao-mensagens__lista">
            {itens.length === 0 && <li>Nenhuma mensagem registrada até o momento.</li>}
            {itens.map((item) => (
              <li
                className={`geracao-mensagens__item geracao-mensagens__item--${item.categoria}`}
                data-categoria={item.categoria}
                key={item.id}
              >
                <IconeCategoria categoria={item.categoria} />
                <span className="geracao-mensagens__canal">{item.canal}</span>
                <span>{item.rotulo}</span>
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
