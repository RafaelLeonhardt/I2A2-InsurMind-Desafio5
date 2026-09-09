import { useState } from 'react'
import { useSeguradoContexto } from '../../contexto/SeguradoContexto'
import './SeletorSegurado.css'

const ID_CAMPO = 'seletor-segurado-visualizar-como'

/**
 * Seletor demonstrativo "Visualizar como" (SELETOR-01, 07, 08): escolhe qual segurado
 * sintético o perfil Segurado exibe. Nunca descrito como login/autenticação — é puramente
 * uma preferência de demonstração local (ADR-0009).
 *
 * `<select>` nativo: rótulo, opção ativa, foco e navegação por teclado já são anunciados
 * pelo próprio agente de acessibilidade do navegador, sem exigir um widget ARIA customizado.
 * A região `aria-live` complementa com um anúncio explícito da troca concluída.
 */
export function SeletorSegurado() {
  const { seguradoAtivoId, segurados, estado, selecionar } = useSeguradoContexto()
  const [anuncio, definirAnuncio] = useState('')

  const semSegurados = segurados.length === 0
  const trocando = estado === 'trocando'
  const desabilitado = semSegurados || trocando

  function motivoDesabilitado(): string | null {
    if (semSegurados) {
      return 'Nenhum segurado sintético disponível: restaure os dados sintéticos e tente novamente.'
    }
    if (trocando) {
      return 'Contexto trocando: aguarde a troca em andamento terminar.'
    }
    return null
  }

  function aoTrocar(novoId: string) {
    selecionar(novoId)
    const escolhido = segurados.find((segurado) => segurado.id === novoId)
    definirAnuncio(escolhido ? `Visualizando como ${escolhido.nome}` : '')
  }

  const motivo = motivoDesabilitado()

  return (
    <div className="seletor-segurado faixa-toolbar">
      <label htmlFor={ID_CAMPO}>Visualizar como</label>
      <select
        aria-describedby={motivo ? `${ID_CAMPO}-motivo` : undefined}
        className="seletor-segurado-campo"
        disabled={desabilitado}
        id={ID_CAMPO}
        onChange={(evento) => aoTrocar(evento.target.value)}
        value={seguradoAtivoId ?? ''}
      >
        {segurados.map((segurado) => (
          <option key={segurado.id} value={segurado.id}>
            {segurado.nome}
          </option>
        ))}
      </select>
      {motivo && (
        <p id={`${ID_CAMPO}-motivo`} role="status">
          {motivo}
        </p>
      )}
      <p aria-live="polite" className="sr-only">
        {anuncio}
      </p>
    </div>
  )
}
