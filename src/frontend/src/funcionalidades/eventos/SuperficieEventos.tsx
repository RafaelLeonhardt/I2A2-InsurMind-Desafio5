import { useCallback, useEffect, useState } from 'react'
import { ErroMeteorologia, type EventoMeteorologico, getEventos } from '../../api/meteorologia'
import { usePerfilContexto } from '../../contexto/PerfilContexto'

type EstadoLista = 'carregando' | 'pronta' | 'erro'

type FalhaEventos = {
  ocorrencia: string
  impacto: string
  proximaAcao: string
}

function falhaDe(causa: unknown): FalhaEventos {
  if (causa instanceof ErroMeteorologia) {
    return { ocorrencia: causa.ocorrencia, impacto: causa.impacto, proximaAcao: causa.proximaAcao }
  }
  return {
    ocorrencia: 'Falha desconhecida ao consultar os eventos climáticos.',
    impacto: 'A lista de eventos pode estar desatualizada.',
    proximaAcao: 'Verifique se o backend local está disponível e tente novamente.',
  }
}

function rotuloTipo(evento: EventoMeteorologico): string {
  return evento.tipo === 'chuva_intensa' ? 'Chuva intensa' : 'Granizo'
}

/**
 * Severidade derivada de `intensidade`, sem persistir um valor novo (ADMNAV-04).
 *
 * Segue a mesma leitura do critério aplicado por `AvaliadorRisco` (2.3, AD-013):
 * chuva intensa é medida em mm acumulados; granizo é relevante por ocorrência, sem uma
 * escala de magnitude adicional — por isso não exibe um número de intensidade para ele.
 */
function severidadeDerivada(evento: EventoMeteorologico): string {
  return evento.tipo === 'chuva_intensa'
    ? `${evento.intensidade.toFixed(1)} mm`
    : 'Ocorrência de granizo'
}

/**
 * Reduz o estado bruto da execução (`EstadoExecucao`, 13 valores no backend) às 4
 * categorias que ADMNAV-04 exige: não iniciada, em andamento, concluída, com falha.
 * `null` (sem execução) é tratado à parte, fora desta função (ver `'Sem execução iniciada'`).
 */
function rotuloEstadoExecucao(estado: string): string {
  if (estado === 'concluida') return 'Concluída'
  if (estado.startsWith('falhou_')) return 'Com falha'
  return 'Em andamento'
}

/**
 * Superfície "Eventos climáticos" do perfil Administrador (História 6.1): lista os eventos
 * meteorológicos identificados com o status da execução preventiva associada, quando houver
 * (`execucaoId`/`execucaoEstado`, ADMNAV-04/05/06/07).
 *
 * Selecionar um evento com execução associada navega para `SuperficieExecucao` via
 * `selecionarSuperficie` (AD-016) — esta superfície não monta a execução ela mesma.
 */
export function SuperficieEventos() {
  const { selecionarSuperficie } = usePerfilContexto()
  const [estado, definirEstado] = useState<EstadoLista>('carregando')
  const [eventos, definirEventos] = useState<EventoMeteorologico[]>([])
  const [falha, definirFalha] = useState<FalhaEventos | null>(null)

  const carregar = useCallback(async () => {
    definirEstado('carregando')
    definirFalha(null)
    try {
      const encontrados = await getEventos()
      definirEventos(encontrados)
      definirEstado('pronta')
    } catch (causa) {
      definirFalha(falhaDe(causa))
      definirEstado('erro')
    }
  }, [])

  useEffect(() => {
    void carregar()
  }, [carregar])

  const abrirExecucao = useCallback(
    (execucaoId: string) => {
      selecionarSuperficie({ tipo: 'evento-execucao', execucaoId, perfilPai: 'administrador' })
    },
    [selecionarSuperficie],
  )

  if (estado === 'carregando') {
    return (
      <main className="conteudo" id="conteudo-principal" tabIndex={-1}>
        <p className="caixa-status" role="status">
          Carregando eventos climáticos…
        </p>
      </main>
    )
  }

  if (estado === 'erro') {
    return (
      <main className="conteudo" id="conteudo-principal" tabIndex={-1}>
        <div className="caixa-status" role="alert">
          <h1>Não foi possível carregar os eventos climáticos</h1>
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

  if (eventos.length === 0) {
    return (
      <main className="conteudo" id="conteudo-principal" tabIndex={-1}>
        <h1>Nenhum evento climático identificado</h1>
        <p className="introducao">
          Nenhum evento meteorológico relevante foi identificado no cenário sintético ativo.
        </p>
        <button className="btn secondary" onClick={() => void carregar()} type="button">
          Atualizar
        </button>
      </main>
    )
  }

  return (
    <main className="conteudo" id="conteudo-principal" tabIndex={-1}>
      <h1>Eventos climáticos</h1>
      <table className="tabela">
        <caption className="sr-only">Lista de eventos climáticos identificados</caption>
        <thead>
          <tr>
            <th scope="col">Tipo</th>
            <th scope="col">Área</th>
            <th scope="col">Severidade</th>
            <th scope="col">Execução</th>
            <th scope="col">Ação</th>
          </tr>
        </thead>
        <tbody>
          {eventos.map((evento) => (
            <tr key={evento.id}>
              <td>{rotuloTipo(evento)}</td>
              <td>{evento.area}</td>
              <td>{severidadeDerivada(evento)}</td>
              <td>
                {evento.execucaoEstado === null
                  ? 'Sem execução iniciada'
                  : rotuloEstadoExecucao(evento.execucaoEstado)}
              </td>
              <td>
                {evento.execucaoId !== null && (
                  <button
                    className="btn secondary"
                    onClick={() => abrirExecucao(evento.execucaoId as string)}
                    type="button"
                  >
                    Ver execução
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  )
}
