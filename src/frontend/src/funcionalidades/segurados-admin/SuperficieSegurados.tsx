import { useCallback, useEffect, useRef, useState } from 'react'
import {
  ErroListaSeguradosAdmin,
  getSeguradosDetalhado,
  type SeguradoDetalhado,
} from '../../api/listaSeguradosAdmin'
import { SuperficieAlertas } from '../segurado/SuperficieAlertas'
import { SuperficieApolice } from '../segurado/SuperficieApolice'
import { SuperficieComunicados } from '../segurado/SuperficieComunicados'

type Estado = 'carregando' | 'disponivel' | 'vazio' | 'erro'

type FalhaSegurados = {
  ocorrencia: string
  impacto: string
  proximaAcao: string
}

const ROTULOS_CANAL: Record<string, string> = {
  whatsapp: 'WhatsApp',
  email: 'E-mail',
  sms: 'SMS',
}

function rotuloCanal(canal: string): string {
  return ROTULOS_CANAL[canal] ?? canal
}

function falhaDe(causa: unknown): FalhaSegurados {
  if (causa instanceof ErroListaSeguradosAdmin) {
    return { ocorrencia: causa.ocorrencia, impacto: causa.impacto, proximaAcao: causa.proximaAcao }
  }
  return {
    ocorrencia: 'Falha desconhecida ao consultar os segurados sintéticos.',
    impacto: 'A lista de segurados não pode ser exibida no momento.',
    proximaAcao: 'Verifique se o backend local está disponível e tente novamente.',
  }
}

function correspondeAoTermo(segurado: SeguradoDetalhado, termoNormalizado: string): boolean {
  return (
    segurado.nome.toLowerCase().includes(termoNormalizado) ||
    segurado.codigoIbgeArea.toLowerCase().includes(termoNormalizado)
  )
}

/**
 * Superfície "Segurados" do perfil Administrador (História 6.4): lista os segurados
 * sintéticos com nome, localização, apólice e canal preferencial (LISTASEG-01..03), com
 * busca client-side por nome ou localização (LISTASEG-04/05) e abertura do contexto de
 * leitura de um segurado a partir da lista (LISTASEG-06).
 *
 * O contexto aberto reusa, sem alteração, as três superfícies somente-leitura já
 * construídas para o perfil Segurado (`SuperficieApolice`/`SuperficieAlertas`/
 * `SuperficieComunicados`, 5.2/5.3/5.5), passando o `seguradoId` selecionado e `comoSecao`
 * — mesmo mecanismo de composição de `PainelSegurado` (5.7). Nenhuma delas expõe ação de
 * edição, então a perspectiva administrativa de auditoria nunca oferece uma.
 */
export function SuperficieSegurados() {
  const [estado, definirEstado] = useState<Estado>('carregando')
  const [segurados, definirSegurados] = useState<SeguradoDetalhado[]>([])
  const [falha, definirFalha] = useState<FalhaSegurados | null>(null)
  const [termoBusca, definirTermoBusca] = useState('')
  const [seguradoContextoId, definirSeguradoContextoId] = useState<string | null>(null)

  const botaoVoltarRef = useRef<HTMLButtonElement>(null)
  const ultimaSelecaoIdRef = useRef<string | null>(null)

  const carregar = useCallback(async () => {
    definirEstado('carregando')
    definirFalha(null)
    try {
      const encontrados = await getSeguradosDetalhado()
      definirSegurados(encontrados)
      definirEstado(encontrados.length === 0 ? 'vazio' : 'disponivel')
    } catch (causa) {
      definirFalha(falhaDe(causa))
      definirEstado('erro')
    }
  }, [])

  useEffect(() => {
    void carregar()
  }, [carregar])

  const abrirContexto = useCallback((seguradoId: string) => {
    ultimaSelecaoIdRef.current = seguradoId
    definirSeguradoContextoId(seguradoId)
  }, [])

  useEffect(() => {
    if (seguradoContextoId !== null) {
      botaoVoltarRef.current?.focus()
    }
  }, [seguradoContextoId])

  useEffect(() => {
    if (seguradoContextoId === null && ultimaSelecaoIdRef.current !== null) {
      const idParaFocar = ultimaSelecaoIdRef.current
      ultimaSelecaoIdRef.current = null
      document.getElementById(`botao-contexto-${idParaFocar}`)?.focus()
    }
  }, [seguradoContextoId])

  const fecharContexto = useCallback(() => {
    definirSeguradoContextoId(null)
  }, [])

  if (estado === 'carregando') {
    return (
      <main className="conteudo" id="conteudo-principal" tabIndex={-1}>
        <p className="caixa-status" role="status">
          Carregando segurados…
        </p>
      </main>
    )
  }

  if (estado === 'erro') {
    return (
      <main className="conteudo" id="conteudo-principal" tabIndex={-1}>
        <div className="caixa-status" role="alert">
          <h1>Não foi possível carregar os segurados</h1>
          <p>
            <strong>Ocorrência:</strong> {falha?.ocorrencia}
          </p>
          <p>
            <strong>Impacto:</strong> {falha?.impacto}
          </p>
          <p>
            <strong>Próxima ação:</strong> {falha?.proximaAcao}
          </p>
          <button className="btn secondary" onClick={() => void carregar()} type="button">
            Tentar novamente
          </button>
        </div>
      </main>
    )
  }

  if (estado === 'vazio') {
    return (
      <main className="conteudo" id="conteudo-principal" tabIndex={-1}>
        <h1>Segurados</h1>
        <p className="introducao">Nenhum segurado sintético cadastrado.</p>
      </main>
    )
  }

  if (seguradoContextoId !== null) {
    return (
      <main className="conteudo" id="conteudo-principal" tabIndex={-1}>
        <h1>Segurados</h1>
        <button className="btn secondary" onClick={fecharContexto} ref={botaoVoltarRef} type="button">
          Voltar
        </button>
        <SuperficieApolice comoSecao seguradoId={seguradoContextoId} />
        <SuperficieAlertas comoSecao seguradoId={seguradoContextoId} />
        <SuperficieComunicados comoSecao seguradoId={seguradoContextoId} />
      </main>
    )
  }

  const termoNormalizado = termoBusca.trim().toLowerCase()
  const seguradosFiltrados =
    termoNormalizado === ''
      ? segurados
      : segurados.filter((segurado) => correspondeAoTermo(segurado, termoNormalizado))

  return (
    <main className="conteudo" id="conteudo-principal" tabIndex={-1}>
      <h1>Segurados</h1>
      <div className="campo-formulario">
        <label htmlFor="campo-busca-segurados">Buscar por nome ou localização</label>
        <input
          id="campo-busca-segurados"
          onChange={(evento) => definirTermoBusca(evento.target.value)}
          type="text"
          value={termoBusca}
        />
      </div>

      {seguradosFiltrados.length === 0 ? (
        <p className="introducao">Nenhum segurado encontrado para "{termoBusca}".</p>
      ) : (
        <table className="tabela">
          <caption className="sr-only">Lista de segurados sintéticos</caption>
          <thead>
            <tr>
              <th scope="col">Nome</th>
              <th scope="col">Localização</th>
              <th scope="col">Apólice</th>
              <th scope="col">Canal</th>
              <th scope="col">Ação</th>
            </tr>
          </thead>
          <tbody>
            {seguradosFiltrados.map((segurado) => (
              <tr key={segurado.id}>
                <td>{segurado.nome}</td>
                <td>{segurado.codigoIbgeArea}</td>
                <td>{segurado.apoliceNumero ?? '—'}</td>
                <td>{rotuloCanal(segurado.canalPreferido)}</td>
                <td>
                  <button
                    className="btn secondary"
                    id={`botao-contexto-${segurado.id}`}
                    onClick={() => abrirContexto(segurado.id)}
                    type="button"
                  >
                    Ver contexto
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  )
}
