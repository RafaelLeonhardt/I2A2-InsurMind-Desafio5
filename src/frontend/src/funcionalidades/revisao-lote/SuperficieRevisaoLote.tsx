import {
  ArrowsClockwiseIcon,
  ProhibitIcon,
  RobotIcon,
  ThumbsUpIcon,
  UserIcon,
  WarningIcon,
} from '@phosphor-icons/react'
import { useCallback, useEffect, useState } from 'react'
import {
  type DecisaoEnviada,
  ErroRevisaoLote,
  type ItemLote,
  type LoteRevisao,
  type ResultadoDecisao,
  decidirLote,
  getLoteRevisao,
} from '../../api/revisaoLote'
import './SuperficieRevisaoLote.css'

/** Rótulo acessível de cada decisão possível (REVISAO-05). Não existe "editar". */
const ROTULOS_DECISAO: Record<ResultadoDecisao, string> = {
  aprovar: 'Aprovar',
  rejeitar: 'Rejeitar',
  excluir: 'Excluir do lote',
  regenerar: 'Solicitar nova geração',
}

const DECISOES: ResultadoDecisao[] = ['aprovar', 'rejeitar', 'excluir', 'regenerar']

/** Decisões que só são aceitas com justificativa (REVISAO-06). */
const EXIGEM_JUSTIFICATIVA: ResultadoDecisao[] = ['rejeitar', 'excluir', 'regenerar']

const MENSAGEM_JUSTIFICATIVA_OBRIGATORIA =
  'Escreva a justificativa antes de confirmar esta decisão.'

const ROTULOS_ESTADO: Record<string, string> = {
  aguardando_revisao: 'Aguardando sua revisão',
  aprovada: 'Aprovada por você',
  rejeitada: 'Rejeitada por você',
  excluida: 'Excluída do lote por você',
  gerando: 'Gerando nova versão',
  criticando: 'Em avaliação do agente crítico',
  falhou_conteudo: 'Exceção: conteúdo não aprovado em três tentativas',
  falhou_integracao_ia: 'Exceção: falha de integração com a IA',
}

function rotuloEstado(estado: string): string {
  return ROTULOS_ESTADO[estado] ?? estado
}

function explicacaoRegeneracaoIndisponivel(item: ItemLote): string {
  return (
    `Esta mensagem já usou as ${item.limiteTentativas} tentativas de geração permitidas. ` +
    'Aprovar, rejeitar e excluir do lote continuam disponíveis.'
  )
}

type EstadoCarregamento = 'carregando' | 'disponivel' | 'indisponivel'

type PropriedadesSuperficieRevisaoLote = {
  execucaoId: string
  embutido?: boolean
}

/** Sinal de atenção do item, distinto em texto e ícone (REVISAO-02). */
function SinalDeAtencao({ item }: { item: ItemLote }) {
  if (item.emExcecao) {
    return (
      <span className="revisao-lote__sinal" data-sinal="excecao">
        <WarningIcon aria-hidden="true" data-icone-nome="warning" size={16} weight="fill" />
        Exige atenção: exceção
      </span>
    )
  }
  if (item.reprovacaoHistorica) {
    return (
      <span className="revisao-lote__sinal" data-sinal="reprovacao-historica">
        <ArrowsClockwiseIcon
          aria-hidden="true"
          data-icone-nome="arrows-clockwise"
          size={16}
          weight="fill"
        />
        Exige atenção: reprovada em tentativa anterior
      </span>
    )
  }
  return (
    <span className="revisao-lote__sinal" data-sinal="aprovacao-limpa">
      <ThumbsUpIcon aria-hidden="true" data-icone-nome="thumbs-up" size={16} weight="fill" />
      Aprovada pelo agente crítico sem ressalvas
    </span>
  )
}

/**
 * Superfície da revisão humana do lote de comunicação (REVISAO-02..06, REVISAO-09).
 *
 * O texto gerado é exibido, nunca editável: em nenhum estado da interface existe campo de
 * entrada com o conteúdo da mensagem (AD-5/AD-6). O único campo editável é a justificativa
 * da decisão, e o rascunho dela sobrevive à navegação entre itens até a conclusão ou o
 * descarte consciente.
 */
export function SuperficieRevisaoLote({
  execucaoId,
  embutido = false,
}: PropriedadesSuperficieRevisaoLote) {
  const [estadoCarregamento, definirEstadoCarregamento] = useState<EstadoCarregamento>('carregando')
  const [lote, definirLote] = useState<LoteRevisao | null>(null)
  const [falha, definirFalha] = useState<ErroRevisaoLote | null>(null)
  const [mensagemAberta, definirMensagemAberta] = useState<string | null>(null)
  const [selecionadas, definirSelecionadas] = useState<string[]>([])
  const [resultado, definirResultado] = useState<ResultadoDecisao>('aprovar')
  const [rascunhos, definirRascunhos] = useState<Record<string, string>>({})
  const [erroValidacao, definirErroValidacao] = useState<string | null>(null)
  const [enviando, definirEnviando] = useState(false)

  const consultar = useCallback(async () => {
    try {
      const encontrado = await getLoteRevisao(execucaoId)
      definirLote(encontrado)
      definirFalha(null)
      definirEstadoCarregamento('disponivel')
    } catch (causa) {
      definirFalha(causa instanceof ErroRevisaoLote ? causa : null)
      definirEstadoCarregamento('indisponivel')
    }
  }, [execucaoId])

  useEffect(() => {
    definirEstadoCarregamento('carregando')
    definirLote(null)
    void consultar()
  }, [consultar])

  const item = lote?.itens.find((candidato) => candidato.mensagemId === mensagemAberta) ?? null
  const justificativa = mensagemAberta ? (rascunhos[mensagemAberta] ?? '') : ''
  const alvos = item
    ? [item.mensagemId, ...selecionadas.filter((id) => id !== item.mensagemId)]
    : selecionadas

  function alternarSelecao(mensagemId: string) {
    definirSelecionadas((atuais) =>
      atuais.includes(mensagemId)
        ? atuais.filter((id) => id !== mensagemId)
        : [...atuais, mensagemId],
    )
  }

  function escreverJustificativa(texto: string) {
    if (mensagemAberta === null) {
      return
    }
    definirRascunhos((atuais) => ({ ...atuais, [mensagemAberta]: texto }))
    definirErroValidacao(null)
  }

  function descartarRascunho() {
    if (mensagemAberta === null) {
      return
    }
    definirRascunhos((atuais) => ({ ...atuais, [mensagemAberta]: '' }))
    definirErroValidacao(null)
  }

  async function confirmar() {
    if (lote === null || alvos.length === 0) {
      return
    }
    if (EXIGEM_JUSTIFICATIVA.includes(resultado) && justificativa.trim() === '') {
      definirErroValidacao(MENSAGEM_JUSTIFICATIVA_OBRIGATORIA)
      return
    }

    const porId = new Map(lote.itens.map((candidato) => [candidato.mensagemId, candidato]))
    const decisoes: DecisaoEnviada[] = alvos.flatMap((mensagemId) => {
      const alvo = porId.get(mensagemId)
      return alvo === undefined
        ? []
        : [
            {
              mensagemId,
              versaoEsperada: alvo.versao,
              resultado,
              justificativa: justificativa.trim() === '' ? null : justificativa.trim(),
            },
          ]
    })

    definirEnviando(true)
    try {
      await decidirLote(lote.execucaoId, decisoes)
      definirRascunhos((atuais) => {
        const restantes = { ...atuais }
        for (const mensagemId of alvos) {
          delete restantes[mensagemId]
        }
        return restantes
      })
      definirSelecionadas([])
      definirMensagemAberta(null)
      definirErroValidacao(null)
      await consultar()
    } catch (causa) {
      definirFalha(causa instanceof ErroRevisaoLote ? causa : null)
      definirEstadoCarregamento('indisponivel')
    } finally {
      definirEnviando(false)
    }
  }

  const conteudo = (
    <section aria-labelledby="titulo-revisao-lote" className="revisao-lote">
      <h2 id="titulo-revisao-lote">Revisão do lote de comunicação</h2>
      <p>
        Revise cada mensagem antes de qualquer simulação. Você pode aprovar, rejeitar,
        excluir do lote ou pedir uma nova geração — o texto gerado nunca é editado à mão.
      </p>

      {estadoCarregamento === 'carregando' && <p role="status">Carregando o lote…</p>}

      {estadoCarregamento === 'indisponivel' && (
        <div role="alert">
          <p>
            <strong>Ocorrência:</strong>{' '}
            {falha?.ocorrencia ?? 'Falha desconhecida ao consultar o lote.'}
          </p>
          <p>
            <strong>Impacto:</strong> {falha?.impacto ?? ''}
          </p>
          <p>
            <strong>Próxima ação:</strong> {falha?.proximaAcao ?? ''}
          </p>
        </div>
      )}

      {estadoCarregamento === 'disponivel' && lote && (
        <>
          <dl className="revisao-lote__resumo">
            <div>
              <dt>Situação da execução</dt>
              <dd>{rotuloEstado(lote.estado)}</dd>
            </div>
            <div>
              <dt>Evento</dt>
              <dd>
                {lote.evento
                  ? `${lote.evento.tipo} na área ${lote.evento.area}`
                  : 'Sem evento associado'}
              </dd>
            </div>
            <div>
              <dt>Regra aplicada</dt>
              <dd>
                {lote.regraId ? `${lote.regraId} (versão ${lote.regraVersao})` : 'Sem regra'}
              </dd>
            </div>
            <div>
              <dt>Público elegível</dt>
              <dd>{lote.totalPublicoIncluido} pessoas</dd>
            </div>
            <div>
              <dt>Distribuição por canal</dt>
              <dd>
                {lote.distribuicaoPorCanal
                  .map((entrada) => `${entrada.canal}: ${entrada.total}`)
                  .join(', ') || 'Nenhuma mensagem'}
              </dd>
            </div>
            <div>
              <dt>Aprovações do agente crítico</dt>
              <dd>{lote.aprovacoesAgenticas}</dd>
            </div>
            <div>
              <dt>Exceções</dt>
              <dd>{lote.itensEmExcecao}</dd>
            </div>
          </dl>

          <h3>Mensagens do lote</h3>
          <p className="revisao-lote__ordem">
            Os itens que exigem atenção aparecem primeiro: exceções, depois reprovações em
            alguma tentativa anterior, depois as aprovações sem ressalvas.
          </p>
          <ul className="revisao-lote__itens">
            {lote.itens.map((candidato) => (
              <li
                className="revisao-lote__item"
                data-canal={candidato.canal}
                data-estado={candidato.estado}
                key={candidato.mensagemId}
              >
                <SinalDeAtencao item={candidato} />
                <span className="revisao-lote__item-destinatario">
                  {candidato.destinatario.nomeSegurado}
                </span>
                <span className="revisao-lote__item-estado">
                  {rotuloEstado(candidato.estado)}
                </span>
                {candidato.decidivel && (
                  <label className="revisao-lote__item-selecao">
                    <input
                      checked={selecionadas.includes(candidato.mensagemId)}
                      onChange={() => alternarSelecao(candidato.mensagemId)}
                      type="checkbox"
                    />
                    Incluir na decisão em lote
                  </label>
                )}
                <button
                  onClick={() => {
                    definirMensagemAberta(candidato.mensagemId)
                    definirErroValidacao(null)
                  }}
                  type="button"
                >
                  Abrir revisor de {candidato.destinatario.nomeSegurado}
                </button>
              </li>
            ))}
          </ul>

          {item && (
            <article aria-labelledby="titulo-revisor" className="revisao-lote__revisor">
              <h3 id="titulo-revisor">
                Revisor da mensagem de {item.destinatario.nomeSegurado}
              </h3>

              <section
                aria-labelledby="titulo-destinatario"
                className="revisao-lote__secao"
                data-secao="destinatario"
              >
                <h4 id="titulo-destinatario">
                  <UserIcon aria-hidden="true" data-icone-nome="user" size={18} weight="fill" />
                  Destinatário sintético
                </h4>
                <dl>
                  <div>
                    <dt>Nome</dt>
                    <dd>{item.destinatario.nomeSegurado}</dd>
                  </div>
                  <div>
                    <dt>Área</dt>
                    <dd>{item.destinatario.codigoIbgeArea}</dd>
                  </div>
                  <div>
                    <dt>Canal</dt>
                    <dd>{item.destinatario.canal}</dd>
                  </div>
                  <div>
                    <dt>Apólice</dt>
                    <dd>{item.destinatario.apoliceId}</dd>
                  </div>
                </dl>
              </section>

              <section
                aria-labelledby="titulo-conteudo"
                className="revisao-lote__secao"
                data-secao="conteudo-versionamento"
              >
                <h4 id="titulo-conteudo">Conteúdo e versões</h4>
                <p className="revisao-lote__aviso-edicao">
                  O conteúdo é exibido como foi gerado e não pode ser editado aqui.
                </p>
                {item.versoes.length === 0 ? (
                  <p>Nenhuma versão foi gerada para esta mensagem.</p>
                ) : (
                  <ol className="revisao-lote__versoes">
                    {item.versoes.map((versao) => (
                      <li data-tentativa={versao.numeroTentativa} key={versao.id}>
                        <span className="revisao-lote__versao-titulo">
                          {versao.numeroTentativa}ª tentativa
                        </span>
                        {versao.assunto && (
                          <p className="revisao-lote__versao-assunto">
                            Assunto: {versao.assunto}
                          </p>
                        )}
                        <p className="revisao-lote__versao-corpo">{versao.corpo}</p>
                        <p className="revisao-lote__versao-verificacao">
                          Verificação determinística:{' '}
                          {versao.valida
                            ? 'aprovada'
                            : `reprovada (${versao.motivoInvalidez ?? 'sem motivo registrado'})`}
                        </p>
                      </li>
                    ))}
                  </ol>
                )}
                <p className="revisao-lote__tentativas">
                  Tentativa {item.tentativaAtual} de {item.limiteTentativas}
                </p>
              </section>

              <section
                aria-labelledby="titulo-contexto-ia"
                className="revisao-lote__secao"
                data-secao="contexto-ia"
              >
                <h4 id="titulo-contexto-ia">
                  <RobotIcon aria-hidden="true" data-icone-nome="robot" size={18} weight="fill" />
                  Contexto de IA, origem e proveniência
                </h4>
                <ul className="revisao-lote__avaliacoes">
                  {item.versoes.map((versao) => (
                    <li data-avaliacao-tentativa={versao.numeroTentativa} key={versao.id}>
                      {versao.numeroTentativa}ª tentativa:{' '}
                      {versao.avaliacaoCritica === null
                        ? 'sem avaliação do agente crítico'
                        : versao.avaliacaoCritica.aprovada
                          ? 'aprovada pelo agente crítico'
                          : `reprovada pelo agente crítico (${versao.avaliacaoCritica.motivos
                              .map((motivo) => motivo.categoria)
                              .join(', ')})`}{' '}
                      — modelo {versao.modelo}, prompt {versao.versaoPrompt}
                    </li>
                  ))}
                </ul>
                <p className="revisao-lote__origem">
                  Origem: evento {item.origem.eventoId}, regra {item.origem.regraId} (versão{' '}
                  {item.origem.regraVersao}). {item.origem.justificativa}
                </p>
                <ul className="revisao-lote__criterios">
                  {item.origem.criterios.map((criterio) => (
                    <li data-criterio={criterio.operando} key={criterio.operando}>
                      {criterio.operando}: {criterio.valorObservado} —{' '}
                      {criterio.atende ? 'atende' : 'não atende'}
                    </li>
                  ))}
                </ul>
                {item.proveniencia && (
                  <p className="revisao-lote__proveniencia">
                    Dados usados pelo agente: {item.proveniencia.categoriasUsadas.join(', ')}.
                    Deixados de fora: {item.proveniencia.categoriasNaoUsadas.join(', ')}.
                  </p>
                )}
              </section>

              {item.decidivel ? (
                <section
                  aria-labelledby="titulo-decisao"
                  className="revisao-lote__secao"
                  data-secao="decisao"
                >
                  <h4 id="titulo-decisao">Sua decisão</h4>
                  <fieldset>
                    <legend>Resultado da revisão</legend>
                    {DECISOES.map((opcao) => {
                      const indisponivel = opcao === 'regenerar' && !item.podeRegenerar
                      return (
                        <label key={opcao}>
                          <input
                            aria-describedby={
                              indisponivel ? 'explicacao-regenerar-indisponivel' : undefined
                            }
                            checked={resultado === opcao}
                            disabled={indisponivel}
                            name="resultado-decisao"
                            onChange={() => {
                              definirResultado(opcao)
                              definirErroValidacao(null)
                            }}
                            type="radio"
                            value={opcao}
                          />
                          {ROTULOS_DECISAO[opcao]}
                        </label>
                      )
                    })}
                  </fieldset>
                  {!item.podeRegenerar && (
                    <p
                      className="revisao-lote__indisponivel"
                      id="explicacao-regenerar-indisponivel"
                    >
                      <ProhibitIcon
                        aria-hidden="true"
                        data-icone-nome="prohibit"
                        size={16}
                        weight="fill"
                      />
                      {explicacaoRegeneracaoIndisponivel(item)}
                    </p>
                  )}

                  <label htmlFor="justificativa-decisao">
                    Justificativa da decisão
                    {EXIGEM_JUSTIFICATIVA.includes(resultado) ? ' (obrigatória)' : ' (opcional)'}
                  </label>
                  <textarea
                    aria-describedby={erroValidacao ? 'erro-justificativa' : undefined}
                    aria-invalid={erroValidacao !== null}
                    id="justificativa-decisao"
                    onChange={(evento) => escreverJustificativa(evento.target.value)}
                    value={justificativa}
                  />
                  {erroValidacao && (
                    <p className="revisao-lote__erro" id="erro-justificativa" role="alert">
                      {erroValidacao}
                    </p>
                  )}

                  <button disabled={enviando} onClick={() => void confirmar()} type="button">
                    Confirmar decisão ({alvos.length}{' '}
                    {alvos.length === 1 ? 'mensagem' : 'mensagens'})
                  </button>
                  <button onClick={descartarRascunho} type="button">
                    Descartar justificativa
                  </button>
                </section>
              ) : (
                <p className="revisao-lote__sem-decisao">
                  Esta mensagem não aguarda decisão: {rotuloEstado(item.estado)}.
                </p>
              )}

              {item.decisoes.length > 0 && (
                <ul className="revisao-lote__decisoes">
                  {item.decisoes.map((decisao) => (
                    <li key={`${decisao.versaoMensagemId}-${decisao.criadoEm}`}>
                      {ROTULOS_DECISAO[decisao.resultado as ResultadoDecisao] ??
                        decisao.resultado}{' '}
                      por {decisao.perfilResponsavel}
                      {decisao.justificativa ? `: ${decisao.justificativa}` : ''}
                    </li>
                  ))}
                </ul>
              )}
            </article>
          )}
        </>
      )}
    </section>
  )

  return embutido ? conteudo : <main>{conteudo}</main>
}
