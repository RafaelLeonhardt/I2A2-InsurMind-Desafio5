import type { Perfil } from '../contexto/PerfilContexto'

const ROTULOS_PERFIL: Record<Perfil, string> = {
  administrador: 'Administrador',
  segurado: 'Segurado',
}

/** Bloqueia a apresentação quando o contexto está ausente ou incompatível com o perfil ativo. */
export function ContextoInconsistente({
  perfil,
  aoVoltar,
}: {
  perfil: Perfil
  aoVoltar: () => void
}) {
  return (
    <main className="conteudo" id="conteudo-principal" tabIndex={-1}>
      <p className="rotulo-contexto">Contexto inconsistente</p>
      <h1>Esta superfície não está disponível para o perfil {ROTULOS_PERFIL[perfil]}</h1>
      <p className="introducao">
        O contexto solicitado está ausente ou não é compatível com o perfil ativo no momento.
      </p>
      <button onClick={aoVoltar} type="button">
        Voltar para a Visão geral
      </button>
    </main>
  )
}
