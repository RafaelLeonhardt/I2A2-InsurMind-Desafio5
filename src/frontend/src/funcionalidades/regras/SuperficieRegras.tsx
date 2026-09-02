import { CheckCircleIcon, ClockCounterClockwiseIcon, FlaskIcon } from '@phosphor-icons/react'
import { useEffect, useState } from 'react'
import {
  ativarRegra,
  type DadosRegra,
  ErroRegras,
  getRegras,
  type Regra,
  testarRegra,
  type CasoTeste,
} from '../../api/regras'
import './SuperficieRegras.css'

type EstadoCarregamento = 'carregando' | 'disponivel' | 'indisponivel'

const ROTULOS_TIPO_EVENTO: Record<string, string> = {
  chuva_intensa: 'Chuva intensa',
  granizo: 'Granizo',
}

const ROTULOS_APOLICE: Record<string, string> = {
  residencial: 'Residencial',
  automovel: 'Automóvel',
}

const ROTULOS_CANAL: Record<string, string> = {
  whatsapp: 'WhatsApp',
  email: 'E-mail',
  sms: 'SMS',
}

/**
 * `severidade` não é um campo persistido (schema Épico 1) — é derivado do próprio critério
 * que o `AvaliadorRisco` aplica (2.3): chuva intensa compara o limiar em mm acumulados,
 * granizo é relevante por ocorrência, sem limiar adicional (AD-013).
 */
function descreverSeveridade(regra: Pick<Regra, 'eventoTipo' | 'limiarMeteorologico'>): string {
  if (regra.eventoTipo === 'chuva_intensa') {
    return `≥ ${regra.limiarMeteorologico} mm acumulados`
  }
  if (regra.eventoTipo === 'granizo') {
    return 'Por ocorrência (sem limiar adicional)'
  }
  return `${regra.limiarMeteorologico}`
}

function dadosDe(regra: Regra): DadosRegra {
  return {
    eventoTipo: regra.eventoTipo,
    limiarMeteorologico: regra.limiarMeteorologico,
    areaAplicavel: regra.areaAplicavel,
    apoliceTipo: regra.apoliceTipo,
    coberturaExigida: regra.coberturaExigida,
    antecedenciaHoras: regra.antecedenciaHoras,
    canal: regra.canal,
  }
}

function assinaturaDe(dados: DadosRegra): string {
  return JSON.stringify(dados)
}

/**
 * Superfície "Regras": tabela versionada, formulário de edição validado e painel de teste
 * determinístico antes da ativação (REGRA-01..15).
 *
 * `Ativar` só habilita depois de um `Testar` bem-sucedido para exatamente os valores atuais
 * do formulário — decisão de UX desta superfície, não uma garantia de segurança: o backend
 * sempre revalida e reexecuta o teste na própria chamada de ativação (`ServicoGestaoRegras`,
 * 2.4 T3), então essa trava do lado do cliente nunca é a única linha de defesa.
 */
export function SuperficieRegras() {
  const [estado, definirEstado] = useState<EstadoCarregamento>('carregando')
  const [regras, definirRegras] = useState<Regra[]>([])
  const [falha, definirFalha] = useState<ErroRegras | null>(null)
  const [versaoConsulta, definirVersaoConsulta] = useState(0)

  const [regraSelecionadaId, definirRegraSelecionadaId] = useState<string | null>(null)
  const [formulario, definirFormulario] = useState<DadosRegra | null>(null)
  const [errosCampo, definirErrosCampo] = useState<Record<string, string>>({})
  const [casosTeste, definirCasosTeste] = useState<CasoTeste[] | null>(null)
  const [assinaturaTestada, definirAssinaturaTestada] = useState<string | null>(null)
  const [processando, definirProcessando] = useState(false)
  const [falhaAcao, definirFalhaAcao] = useState<ErroRegras | null>(null)
  const [mensagemSucesso, definirMensagemSucesso] = useState<string | null>(null)

  useEffect(() => {
    let cancelado = false
    definirEstado('carregando')

    getRegras()
      .then((resultado) => {
        if (cancelado) return
        definirRegras(resultado)
        definirFalha(null)
        definirEstado('disponivel')
      })
      .catch((causa: unknown) => {
        if (cancelado) return
        definirFalha(causa instanceof ErroRegras ? causa : null)
        definirEstado('indisponivel')
      })

    return () => {
      cancelado = true
    }
  }, [versaoConsulta])

  const regraSelecionada = regras.find((regra) => regra.id === regraSelecionadaId) ?? null

  function iniciarEdicao(regra: Regra) {
    definirRegraSelecionadaId(regra.id)
    definirFormulario(dadosDe(regra))
    definirErrosCampo({})
    definirCasosTeste(null)
    definirAssinaturaTestada(null)
    definirFalhaAcao(null)
    definirMensagemSucesso(null)
  }

  function cancelarEdicao() {
    definirRegraSelecionadaId(null)
    definirFormulario(null)
    definirErrosCampo({})
    definirCasosTeste(null)
    definirAssinaturaTestada(null)
    definirFalhaAcao(null)
  }

  function atualizarCampo<Campo extends keyof DadosRegra>(campo: Campo, valor: DadosRegra[Campo]) {
    definirFormulario((atual) => (atual ? { ...atual, [campo]: valor } : atual))
    definirCasosTeste(null)
    definirAssinaturaTestada(null)
    definirMensagemSucesso(null)
  }

  function tratarFalha(causa: unknown) {
    if (causa instanceof ErroRegras) {
      definirFalhaAcao(causa)
      const porCampo: Record<string, string> = {}
      for (const erro of causa.erros) porCampo[erro.campo] = erro.motivo
      definirErrosCampo(porCampo)
    } else {
      definirFalhaAcao(null)
    }
  }

  async function testar() {
    if (!formulario || !regraSelecionadaId) return
    definirProcessando(true)
    definirFalhaAcao(null)
    definirErrosCampo({})
    try {
      const casos = await testarRegra(regraSelecionadaId, formulario)
      definirCasosTeste(casos)
      definirAssinaturaTestada(assinaturaDe(formulario))
    } catch (causa) {
      definirCasosTeste(null)
      definirAssinaturaTestada(null)
      tratarFalha(causa)
    } finally {
      definirProcessando(false)
    }
  }

  async function ativar() {
    if (!formulario || !regraSelecionada) return
    definirProcessando(true)
    definirFalhaAcao(null)
    definirErrosCampo({})
    try {
      await ativarRegra(regraSelecionada.id, regraSelecionada.versao, formulario)
      definirMensagemSucesso(
        `Nova versão ativada (v${regraSelecionada.versao + 1}). A versão anterior permanece consultável.`,
      )
      cancelarEdicao()
      definirVersaoConsulta((atual) => atual + 1)
    } catch (causa) {
      tratarFalha(causa)
    } finally {
      definirProcessando(false)
    }
  }

  const testeValidoParaFormularioAtual =
    formulario !== null && assinaturaTestada === assinaturaDe(formulario)
  const podeAtivar = testeValidoParaFormularioAtual && casosTeste !== null

  return (
    <main className="conteudo" id="conteudo-principal" tabIndex={-1}>
      <p className="rotulo-contexto">Regras</p>
      <h1>Regras</h1>
      <p className="introducao">
        Configure, teste deterministicamente contra cenários sintéticos e ative novas versões
        de regra preventiva. Uma configuração inválida ou não testada nunca é ativada.
      </p>

      {estado === 'carregando' && <p role="status">Carregando regras…</p>}

      {estado === 'indisponivel' && (
        <div role="alert">
          <p>
            <strong>Indisponível</strong>
          </p>
          <p>
            <strong>Ocorrência:</strong>{' '}
            {falha?.ocorrencia ?? 'Falha desconhecida ao consultar as regras.'}
          </p>
          <p>
            <strong>Impacto:</strong> {falha?.impacto ?? ''}
          </p>
          <p>
            <strong>Próxima ação:</strong> {falha?.proximaAcao ?? ''}
          </p>
        </div>
      )}

      {estado === 'disponivel' && (
        <>
          {mensagemSucesso && <p role="status">{mensagemSucesso}</p>}

          <section aria-labelledby="titulo-tabela-regras">
            <h2 id="titulo-tabela-regras">Versões de regra</h2>
            {regras.length === 0 ? (
              <p>Nenhuma regra configurada até o momento.</p>
            ) : (
              <table className="tabela-regras">
                <caption className="sr-only">
                  Versões de regra, com a versão ativa identificada por texto e ícone
                </caption>
                <thead>
                  <tr>
                    <th scope="col">Tipo de evento</th>
                    <th scope="col">Severidade</th>
                    <th scope="col">Limiar</th>
                    <th scope="col">Área</th>
                    <th scope="col">Apólice</th>
                    <th scope="col">Cobertura</th>
                    <th scope="col">Antecedência</th>
                    <th scope="col">Canal</th>
                    <th scope="col">Versão</th>
                    <th scope="col">Estado</th>
                    <th scope="col">Ação</th>
                  </tr>
                </thead>
                <tbody>
                  {regras.map((regra) => (
                    <tr aria-selected={regra.id === regraSelecionadaId} key={regra.id}>
                      <td>{ROTULOS_TIPO_EVENTO[regra.eventoTipo] ?? regra.eventoTipo}</td>
                      <td>{descreverSeveridade(regra)}</td>
                      <td>{regra.limiarMeteorologico}</td>
                      <td>{regra.areaAplicavel}</td>
                      <td>{ROTULOS_APOLICE[regra.apoliceTipo] ?? regra.apoliceTipo}</td>
                      <td>{regra.coberturaExigida}</td>
                      <td>{regra.antecedenciaHoras}h</td>
                      <td>{ROTULOS_CANAL[regra.canal] ?? regra.canal}</td>
                      <td>{regra.versao}</td>
                      <td>
                        <span
                          className={`regra-estado-badge regra-estado-badge--${regra.estado}`}
                          data-indicador={regra.estado}
                        >
                          {regra.estado === 'ativa' ? (
                            <CheckCircleIcon
                              aria-hidden="true"
                              data-icone-nome="check-circle"
                              size={16}
                              weight="fill"
                            />
                          ) : (
                            <ClockCounterClockwiseIcon
                              aria-hidden="true"
                              data-icone-nome="clock-counter-clockwise"
                              size={16}
                            />
                          )}
                          {regra.estado === 'ativa' ? 'Ativa' : 'Substituída'}
                        </span>
                      </td>
                      <td>
                        <button
                          disabled={regra.estado !== 'ativa'}
                          onClick={() => iniciarEdicao(regra)}
                          type="button"
                        >
                          Editar
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>

          {formulario && regraSelecionada && (
            <section aria-labelledby="titulo-edicao-regra">
              <h2 id="titulo-edicao-regra">
                Editar regra ({ROTULOS_TIPO_EVENTO[regraSelecionada.eventoTipo]}, v
                {regraSelecionada.versao})
              </h2>

              <form
                onSubmit={(evento) => {
                  evento.preventDefault()
                  testar()
                }}
              >
                <div className="campo-formulario">
                  <label htmlFor="campo-limiar">Limiar meteorológico</label>
                  <input
                    aria-describedby={errosCampo.limiar_meteorologico ? 'erro-limiar' : undefined}
                    aria-invalid={Boolean(errosCampo.limiar_meteorologico)}
                    id="campo-limiar"
                    onChange={(evento) =>
                      atualizarCampo('limiarMeteorologico', Number(evento.target.value))
                    }
                    step="0.1"
                    type="number"
                    value={formulario.limiarMeteorologico}
                  />
                  {errosCampo.limiar_meteorologico && (
                    <p id="erro-limiar" role="alert">
                      {errosCampo.limiar_meteorologico}
                    </p>
                  )}
                </div>

                <div className="campo-formulario">
                  <label htmlFor="campo-area">Área aplicável</label>
                  <input
                    aria-describedby={errosCampo.area_aplicavel ? 'erro-area' : undefined}
                    aria-invalid={Boolean(errosCampo.area_aplicavel)}
                    id="campo-area"
                    onChange={(evento) => atualizarCampo('areaAplicavel', evento.target.value)}
                    type="text"
                    value={formulario.areaAplicavel}
                  />
                  {errosCampo.area_aplicavel && (
                    <p id="erro-area" role="alert">
                      {errosCampo.area_aplicavel}
                    </p>
                  )}
                </div>

                <div className="campo-formulario">
                  <label htmlFor="campo-apolice">Tipo de apólice</label>
                  <select
                    aria-describedby={errosCampo.apolice_tipo ? 'erro-apolice' : undefined}
                    aria-invalid={Boolean(errosCampo.apolice_tipo)}
                    id="campo-apolice"
                    onChange={(evento) => atualizarCampo('apoliceTipo', evento.target.value)}
                    value={formulario.apoliceTipo}
                  >
                    <option value="residencial">Residencial</option>
                    <option value="automovel">Automóvel</option>
                  </select>
                  {errosCampo.apolice_tipo && (
                    <p id="erro-apolice" role="alert">
                      {errosCampo.apolice_tipo}
                    </p>
                  )}
                </div>

                <div className="campo-formulario">
                  <label htmlFor="campo-cobertura">Cobertura exigida</label>
                  <input
                    aria-describedby={
                      errosCampo.cobertura_exigida ? 'erro-cobertura' : undefined
                    }
                    aria-invalid={Boolean(errosCampo.cobertura_exigida)}
                    id="campo-cobertura"
                    onChange={(evento) => atualizarCampo('coberturaExigida', evento.target.value)}
                    type="text"
                    value={formulario.coberturaExigida}
                  />
                  {errosCampo.cobertura_exigida && (
                    <p id="erro-cobertura" role="alert">
                      {errosCampo.cobertura_exigida}
                    </p>
                  )}
                </div>

                <div className="campo-formulario">
                  <label htmlFor="campo-antecedencia">Antecedência (horas)</label>
                  <input
                    aria-describedby={
                      errosCampo.antecedencia_horas ? 'erro-antecedencia' : undefined
                    }
                    aria-invalid={Boolean(errosCampo.antecedencia_horas)}
                    id="campo-antecedencia"
                    onChange={(evento) =>
                      atualizarCampo('antecedenciaHoras', Number(evento.target.value))
                    }
                    type="number"
                    value={formulario.antecedenciaHoras}
                  />
                  {errosCampo.antecedencia_horas && (
                    <p id="erro-antecedencia" role="alert">
                      {errosCampo.antecedencia_horas}
                    </p>
                  )}
                </div>

                <div className="campo-formulario">
                  <label htmlFor="campo-canal">Canal</label>
                  <select
                    aria-describedby={errosCampo.canal ? 'erro-canal' : undefined}
                    aria-invalid={Boolean(errosCampo.canal)}
                    id="campo-canal"
                    onChange={(evento) => atualizarCampo('canal', evento.target.value)}
                    value={formulario.canal}
                  >
                    <option value="whatsapp">WhatsApp</option>
                    <option value="email">E-mail</option>
                    <option value="sms">SMS</option>
                  </select>
                  {errosCampo.canal && (
                    <p id="erro-canal" role="alert">
                      {errosCampo.canal}
                    </p>
                  )}
                </div>

                <div className="acoes-formulario-regra">
                  <button disabled={processando} type="submit">
                    <FlaskIcon aria-hidden="true" size={18} />
                    {processando ? 'Testando…' : 'Testar'}
                  </button>
                  <button
                    disabled={!podeAtivar || processando}
                    onClick={ativar}
                    type="button"
                  >
                    {processando ? 'Ativando…' : 'Ativar nova versão'}
                  </button>
                  <button disabled={processando} onClick={cancelarEdicao} type="button">
                    Cancelar
                  </button>
                </div>
              </form>

              {falhaAcao && Object.keys(errosCampo).length === 0 && (
                <p role="alert">
                  {falhaAcao.ocorrencia} {falhaAcao.proximaAcao}
                </p>
              )}

              {casosTeste && (
                <section aria-labelledby="titulo-resultado-teste">
                  <h3 id="titulo-resultado-teste">Resultado do teste determinístico</h3>
                  {casosTeste.length === 0 ? (
                    <p>Nenhum cenário sintético é aplicável a este tipo de evento.</p>
                  ) : (
                    casosTeste.map((caso) => (
                      <table className="tabela-caso-teste" key={caso.eventoId}>
                        <caption>
                          Cenário {caso.eventoId} —{' '}
                          {caso.relevante ? 'Relevante' : 'Não relevante'} ({caso.motivo})
                        </caption>
                        <thead>
                          <tr>
                            <th scope="col">Operando</th>
                            <th scope="col">Valor observado</th>
                            <th scope="col">Resultado</th>
                            <th scope="col">Justificativa</th>
                          </tr>
                        </thead>
                        <tbody>
                          {caso.criterios.map((criterio) => (
                            <tr key={criterio.operando}>
                              <td>{criterio.operando}</td>
                              <td>{criterio.valorObservado}</td>
                              <td>{criterio.atende ? 'Atende' : 'Não atende'}</td>
                              <td>{criterio.justificativa}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    ))
                  )}
                </section>
              )}
            </section>
          )}
        </>
      )}
    </main>
  )
}
