import { CheckCircleIcon, CircleNotchIcon, WarningIcon, XCircleIcon } from '@phosphor-icons/react'
import { useCallback, useEffect, useRef, useState } from 'react'
import {
  type EstadoDependencia,
  ErroProntidao,
  getDependencias,
  type NomeDependencia,
  solicitarNovaVerificacao,
} from '../../api/prontidao'
import './SuperficieProntidao.css'

const INTERVALO_POLLING_MS = 2000

const ORDEM_DEPENDENCIAS: readonly NomeDependencia[] = ['backend', 'banco_dados', 'inmet', 'openai']

const ROTULOS: Record<NomeDependencia, string> = {
  backend: 'Backend',
  banco_dados: 'Banco de dados',
  inmet: 'INMET',
  openai: 'OpenAI',
}

const ROTULOS_ESTADO: Record<EstadoDependencia['estado'], string> = {
  verificando: 'Verificando',
  disponivel: 'Disponível',
  degradada: 'Degradada',
  indisponivel: 'Indisponível',
}

const DEPENDENCIAS_REVERIFICAVEIS: ReadonlySet<NomeDependencia> = new Set(['inmet', 'openai'])

function ehTerminal(estado: EstadoDependencia['estado']): boolean {
  return estado !== 'verificando'
}

function linhaPlaceholder(nome: NomeDependencia): EstadoDependencia {
  return {
    nome,
    estado: 'verificando',
    verificadoEm: null,
    causa: null,
    impacto: 'Verificação em andamento.',
    acaoDisponivel: 'Aguarde a conclusão ou consulte novamente em instantes.',
  }
}

function IconeEstado({ estado }: { estado: EstadoDependencia['estado'] }) {
  if (estado === 'disponivel') {
    return <CheckCircleIcon aria-hidden="true" size={18} weight="fill" />
  }
  if (estado === 'degradada') {
    return <WarningIcon aria-hidden="true" size={18} weight="fill" />
  }
  if (estado === 'indisponivel') {
    return <XCircleIcon aria-hidden="true" size={18} weight="fill" />
  }
  return <CircleNotchIcon aria-hidden="true" size={18} />
}

/** Superfície de prontidão: 4 linhas, polling e re-verificação por dependência. */
export function SuperficieProntidao() {
  const [dependencias, definirDependencias] = useState<EstadoDependencia[]>(() =>
    ORDEM_DEPENDENCIAS.map(linhaPlaceholder),
  )
  const [falhaCarregamento, definirFalhaCarregamento] = useState<ErroProntidao | null>(null)
  const [reverificando, definirReverificando] = useState<ReadonlySet<NomeDependencia>>(new Set())
  const [falhasReverificacao, definirFalhasReverificacao] = useState<
    Partial<Record<NomeDependencia, ErroProntidao>>
  >({})

  const idIntervalo = useRef<number | null>(null)

  const consultar = useCallback(async () => {
    try {
      const resultado = await getDependencias()
      definirDependencias(resultado)
      definirFalhaCarregamento(null)
    } catch (causa) {
      definirFalhaCarregamento(causa instanceof ErroProntidao ? causa : null)
    }
  }, [])

  useEffect(() => {
    void consultar()
  }, [consultar])

  useEffect(() => {
    const algumaNaoTerminal = dependencias.some((dependencia) => !ehTerminal(dependencia.estado))

    if (!algumaNaoTerminal) {
      if (idIntervalo.current !== null) {
        window.clearInterval(idIntervalo.current)
        idIntervalo.current = null
      }
      return
    }

    if (idIntervalo.current === null) {
      idIntervalo.current = window.setInterval(() => {
        void consultar()
      }, INTERVALO_POLLING_MS)
    }

    return () => {
      if (idIntervalo.current !== null) {
        window.clearInterval(idIntervalo.current)
        idIntervalo.current = null
      }
    }
  }, [dependencias, consultar])

  async function reverificar(nome: NomeDependencia) {
    definirReverificando((atual) => new Set(atual).add(nome))
    setFalhaReverificacao(nome, null)
    try {
      await solicitarNovaVerificacao(nome)
      await consultar()
    } catch (causa) {
      setFalhaReverificacao(nome, causa instanceof ErroProntidao ? causa : null)
    } finally {
      definirReverificando((atual) => {
        const novo = new Set(atual)
        novo.delete(nome)
        return novo
      })
    }
  }

  function setFalhaReverificacao(nome: NomeDependencia, falha: ErroProntidao | null) {
    definirFalhasReverificacao((atual) => {
      const proxima = { ...atual }
      if (falha) {
        proxima[nome] = falha
      } else {
        delete proxima[nome]
      }
      return proxima
    })
  }

  const porNome = new Map(dependencias.map((dependencia) => [dependencia.nome, dependencia]))

  return (
    <main className="conteudo" id="conteudo-principal" tabIndex={-1}>
      <p className="rotulo-contexto">Prontidão</p>
      <h1>Prontidão das dependências</h1>
      <p className="introducao">
        Verifica se backend, banco de dados, INMET e OpenAI estão prontos antes e durante uma
        demonstração.
      </p>
      {falhaCarregamento && (
        <div className="caixa-status" role="alert">
          <p>
            <strong>Ocorrência:</strong> {falhaCarregamento.ocorrencia}
          </p>
          <p>
            <strong>Impacto:</strong> {falhaCarregamento.impacto}
          </p>
          <p>
            <strong>Próxima ação:</strong> {falhaCarregamento.proximaAcao}
          </p>
        </div>
      )}
      <div aria-label="Prontidão das 4 dependências" className="tabela-prontidao-rolagem" role="region">
        <table className="tabela-prontidao">
          <caption className="sr-only">Prontidão das 4 dependências</caption>
        <thead>
          <tr>
            <th scope="col">Dependência</th>
            <th scope="col">Estado</th>
            <th scope="col">Última verificação</th>
            <th scope="col">Causa conhecida</th>
            <th scope="col">Impacto esperado</th>
            <th scope="col">Ação</th>
          </tr>
        </thead>
        <tbody>
          {ORDEM_DEPENDENCIAS.map((nome) => {
            const dependencia = porNome.get(nome) ?? linhaPlaceholder(nome)
            const emVerificacao = dependencia.estado === 'verificando'
            const falha = falhasReverificacao[nome]

            return (
              <tr key={nome}>
                <th scope="row">{ROTULOS[nome]}</th>
                <td aria-live={emVerificacao ? 'polite' : undefined}>
                  <span
                    className={`estado-badge estado-badge--${dependencia.estado}`}
                    data-icone={dependencia.estado}
                  >
                    <IconeEstado estado={dependencia.estado} />
                    {ROTULOS_ESTADO[dependencia.estado]}
                  </span>
                </td>
                <td>{dependencia.verificadoEm ?? '—'}</td>
                <td>{dependencia.causa ?? '—'}</td>
                <td>{dependencia.impacto}</td>
                <td>
                  {DEPENDENCIAS_REVERIFICAVEIS.has(nome) ? (
                    <>
                      <button
                        aria-label={`Verificar novamente: ${ROTULOS[nome]}`}
                        className="botao-reverificar"
                        disabled={reverificando.has(nome)}
                        onClick={() => reverificar(nome)}
                        type="button"
                      >
                        {reverificando.has(nome) ? 'Verificando…' : 'Verificar novamente'}
                      </button>
                      {falha && (
                        <p role="alert">
                          {falha.ocorrencia} {falha.proximaAcao}
                        </p>
                      )}
                    </>
                  ) : (
                    dependencia.acaoDisponivel
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
        </table>
      </div>
    </main>
  )
}
