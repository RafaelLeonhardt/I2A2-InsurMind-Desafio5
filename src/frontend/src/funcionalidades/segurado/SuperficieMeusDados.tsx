import type { FormEvent } from 'react'
import { useCallback, useEffect, useState } from 'react'
import { ErroContexto, getSeguradoPadrao } from '../../api/contexto'
import {
  atualizarPreferencias,
  ErroPreferenciasSegurado,
  getPreferencias,
  type PreferenciasSegurado,
} from '../../api/preferenciasSegurado'
import './SuperficieMeusDados.css'

type EstadoCarregamento = 'carregando' | 'pronto' | 'erro'
type EstadoSalvamento = 'ocioso' | 'salvando' | 'salvo' | 'erro'

type FormularioPreferencias = {
  canalPreferido: string
  participaDeAlertas: boolean
}

type FalhaPreferencias = {
  ocorrencia: string
  impacto: string
  proximaAcao: string
}

type PropriedadesSuperficieMeusDados = {
  /** Segurado a exibir. Ausente hoje: resolve o segurado padrão internamente (mesmo
   * seam de SuperficieApolice, 5.3). */
  seguradoId?: string
}

const ROTULOS_CANAL: Record<string, string> = {
  whatsapp: 'WhatsApp',
  email: 'E-mail',
  sms: 'SMS',
}

function falhaDe(causa: unknown): FalhaPreferencias {
  if (causa instanceof ErroPreferenciasSegurado || causa instanceof ErroContexto) {
    return { ocorrencia: causa.ocorrencia, impacto: causa.impacto, proximaAcao: causa.proximaAcao }
  }
  return {
    ocorrencia: 'Falha desconhecida ao consultar suas preferências.',
    impacto: 'O canal preferencial e a participação em alertas podem estar desatualizados.',
    proximaAcao: 'Verifique se o backend local está disponível e tente novamente.',
  }
}

/**
 * Superfície "Meus Dados" do perfil Segurado: única mutação legítima do MVP — canal
 * preferencial e participação em alertas, sob concorrência otimista e idempotência
 * (PREFS-01..07, 5.6).
 *
 * Uma falha ou conflito ao salvar nunca sobrescreve os valores editados no formulário
 * (o estado `formulario` só muda por ação do usuário ou por um salvamento bem-sucedido) —
 * garante que Carlos nunca perde a edição em curso, mesmo com um `409` de versão.
 */
export function SuperficieMeusDados({ seguradoId }: PropriedadesSuperficieMeusDados) {
  const [estado, definirEstado] = useState<EstadoCarregamento>('carregando')
  const [falha, definirFalha] = useState<FalhaPreferencias | null>(null)
  const [preferencias, definirPreferencias] = useState<PreferenciasSegurado | null>(null)
  const [formulario, definirFormulario] = useState<FormularioPreferencias | null>(null)

  const [estadoSalvamento, definirEstadoSalvamento] = useState<EstadoSalvamento>('ocioso')
  const [falhaSalvamento, definirFalhaSalvamento] = useState<FalhaPreferencias | null>(null)

  const carregar = useCallback(async () => {
    definirEstado('carregando')
    definirFalha(null)
    try {
      const idSegurado = seguradoId ?? (await getSeguradoPadrao()).id
      const encontradas = await getPreferencias(idSegurado)
      definirPreferencias(encontradas)
      definirFormulario({
        canalPreferido: encontradas.canalPreferido,
        participaDeAlertas: encontradas.participaDeAlertas,
      })
      definirEstado('pronto')
    } catch (causa) {
      definirFalha(falhaDe(causa))
      definirEstado('erro')
    }
  }, [seguradoId])

  useEffect(() => {
    void carregar()
  }, [carregar])

  function atualizarCampo<Campo extends keyof FormularioPreferencias>(
    campo: Campo,
    valor: FormularioPreferencias[Campo],
  ) {
    definirFormulario((atual) => (atual ? { ...atual, [campo]: valor } : atual))
    definirEstadoSalvamento('ocioso')
    definirFalhaSalvamento(null)
  }

  async function salvar(evento: FormEvent) {
    evento.preventDefault()
    if (!formulario || !preferencias) return
    definirEstadoSalvamento('salvando')
    definirFalhaSalvamento(null)
    try {
      const atualizadas = await atualizarPreferencias(
        preferencias.seguradoId,
        preferencias.versao,
        formulario.canalPreferido,
        formulario.participaDeAlertas,
      )
      definirPreferencias(atualizadas)
      definirEstadoSalvamento('salvo')
    } catch (causa) {
      definirFalhaSalvamento(falhaDe(causa))
      definirEstadoSalvamento('erro')
    }
  }

  if (estado === 'carregando') {
    return (
      <main className="conteudo" id="conteudo-principal" tabIndex={-1}>
        <p role="status">Carregando suas preferências…</p>
      </main>
    )
  }

  if (estado === 'erro') {
    return (
      <main className="conteudo" id="conteudo-principal" tabIndex={-1}>
        <div role="alert">
          <h1>Não foi possível carregar suas preferências</h1>
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

  if (!formulario) return null

  return (
    <main className="conteudo" id="conteudo-principal" tabIndex={-1}>
      <h1>Meus dados</h1>
      <p className="introducao">
        Altere seu canal preferencial de comunicação e sua participação em alertas. Nenhum
        outro cadastro é editável nesta versão.
      </p>

      <form onSubmit={salvar}>
        <div className="campo-formulario">
          <label htmlFor="campo-canal-preferido">Canal preferencial</label>
          <select
            id="campo-canal-preferido"
            onChange={(evento) => atualizarCampo('canalPreferido', evento.target.value)}
            value={formulario.canalPreferido}
          >
            {Object.entries(ROTULOS_CANAL).map(([valor, rotulo]) => (
              <option key={valor} value={valor}>
                {rotulo}
              </option>
            ))}
          </select>
        </div>

        <div className="campo-formulario campo-formulario--participacao">
          <span className="campo-checkbox">
            <input
              aria-describedby={
                !formulario.participaDeAlertas ? 'ajuda-participa-de-alertas' : undefined
              }
              checked={formulario.participaDeAlertas}
              id="campo-participa-de-alertas"
              onChange={(evento) => atualizarCampo('participaDeAlertas', evento.target.checked)}
              type="checkbox"
            />
            <label htmlFor="campo-participa-de-alertas">Participar de alertas</label>
          </span>
          {!formulario.participaDeAlertas && (
            <p id="ajuda-participa-de-alertas">
              Desativar a participação vale só para alertas futuros: comunicados e alertas já
              registrados continuam disponíveis para consulta.
            </p>
          )}
        </div>

        <button disabled={estadoSalvamento === 'salvando'} type="submit">
          {estadoSalvamento === 'salvando' ? 'Salvando…' : 'Salvar'}
        </button>
      </form>

      {estadoSalvamento === 'salvando' && <p role="status">Salvando…</p>}
      {estadoSalvamento === 'salvo' && <p role="status">Salvo</p>}

      {estadoSalvamento === 'erro' && falhaSalvamento && (
        <div role="alert">
          <p>
            <strong>Ocorrência:</strong> {falhaSalvamento.ocorrencia}
          </p>
          <p>
            <strong>Impacto:</strong> {falhaSalvamento.impacto}
          </p>
          <p>
            <strong>Próxima ação:</strong> {falhaSalvamento.proximaAcao}
          </p>
        </div>
      )}
    </main>
  )
}
