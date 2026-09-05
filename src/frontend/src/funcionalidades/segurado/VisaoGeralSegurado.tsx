import { CalendarDotsIcon, CloudRainIcon, FlaskIcon, WarningIcon } from '@phosphor-icons/react'
import { useCallback, useEffect, useRef, useState } from 'react'
import {
  type AlertaSegurado,
  ErroAlertaSegurado,
  getAlertaMaisRelevante,
} from '../../api/alertaSegurado'
import { ErroContexto, getSeguradoPadrao } from '../../api/contexto'
import { calcularIdade } from '../fonte-meteorologica/SuperficieFonteMeteorologica'

type EstadoVisaoGeral = 'carregando' | 'alerta' | 'sem_alerta' | 'contexto_trocando' | 'erro'

type FalhaVisaoGeral = {
  ocorrencia: string
  impacto: string
  proximaAcao: string
}

type PropriedadesVisaoGeralSegurado = {
  /** Segurado a exibir. Ausente hoje: resolve o segurado padrão internamente (não há
   * ainda alternância de segurado sintético, História 5.7). Presente: usado direto, sem
   * consultar o padrão — o seam que a 5.7 vai usar para trocar de contexto. */
  seguradoId?: string
}

const ROTULOS_EVENTO: Record<string, string> = {
  chuva_intensa: 'Chuva intensa',
  granizo: 'Granizo',
}

const ROTULOS_ORIGEM: Record<string, string> = {
  real_inmet: 'Observação real (INMET)',
  sintetico: 'Cenário demonstrativo (sintético)',
}

function rotuloEvento(tipo: string): string {
  return ROTULOS_EVENTO[tipo] ?? tipo
}

function rotuloOrigem(origem: string): string {
  return ROTULOS_ORIGEM[origem] ?? origem
}

function falhaDe(causa: unknown): FalhaVisaoGeral {
  if (causa instanceof ErroAlertaSegurado || causa instanceof ErroContexto) {
    return { ocorrencia: causa.ocorrencia, impacto: causa.impacto, proximaAcao: causa.proximaAcao }
  }
  return {
    ocorrencia: 'Falha desconhecida ao consultar o alerta.',
    impacto: 'A Visão geral pode estar desatualizada.',
    proximaAcao: 'Verifique se o backend local está disponível e tente novamente.',
  }
}

/**
 * Visão geral do perfil Segurado: o alerta mais relevante, com origem, horário,
 * impactos e recomendações reais (VISAO-01..08).
 *
 * Distingue cinco estados (`Carregando`, `Alerta`, `Sem alerta`, `Contexto trocando`,
 * `Erro`, VISAO-06): uma falha preserva o último alerta/estado vazio já exibido em vez de
 * apagá-lo — só a mensagem de erro aparece por cima, nunca substitui o conteúdo válido.
 */
export function VisaoGeralSegurado({ seguradoId }: PropriedadesVisaoGeralSegurado) {
  const [estado, definirEstado] = useState<EstadoVisaoGeral>('carregando')
  const [alerta, definirAlerta] = useState<AlertaSegurado | null>(null)
  const [falha, definirFalha] = useState<FalhaVisaoGeral | null>(null)
  const [resolvidoAoMenosUmaVez, definirResolvidoAoMenosUmaVez] = useState(false)
  const contextoResolvidoRef = useRef<string | null>(null)
  const requisicaoAtualRef = useRef(0)

  const carregar = useCallback(async () => {
    const requisicao = ++requisicaoAtualRef.current
    definirEstado(contextoResolvidoRef.current === null ? 'carregando' : 'contexto_trocando')
    definirFalha(null)
    try {
      const idSegurado = seguradoId ?? (await getSeguradoPadrao()).id
      const encontrado = await getAlertaMaisRelevante(idSegurado)
      // Uma requisição mais recente já pode ter chegado primeiro (troca de contexto rápida,
      // VISAO edge case) — nunca sobrescrever o dado do segurado novo com o do anterior.
      if (requisicao !== requisicaoAtualRef.current) return
      contextoResolvidoRef.current = idSegurado
      definirAlerta(encontrado)
      definirResolvidoAoMenosUmaVez(true)
      definirEstado(encontrado ? 'alerta' : 'sem_alerta')
    } catch (causa) {
      if (requisicao !== requisicaoAtualRef.current) return
      definirFalha(falhaDe(causa))
      definirEstado('erro')
    }
  }, [seguradoId])

  useEffect(() => {
    void carregar()
  }, [carregar])

  return (
    <>
      <main className="conteudo" id="conteudo-principal" tabIndex={-1}>
        <p className="rotulo-contexto">Visão geral preventiva</p>

        {estado === 'carregando' && <p role="status">Carregando alerta…</p>}
        {estado === 'contexto_trocando' && <p role="status">Contexto trocando…</p>}

        {estado === 'erro' && (
          <div role="alert">
            {resolvidoAoMenosUmaVez ? (
              <p>
                <strong>Não foi possível atualizar seu alerta.</strong>
              </p>
            ) : (
              <h1>Não foi possível carregar seu alerta</h1>
            )}
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
        )}

        {(estado === 'sem_alerta' ||
          (estado === 'erro' && resolvidoAoMenosUmaVez && !alerta)) && (
          <>
            <h1>Nenhum alerta relevante no momento</h1>
            <p className="introducao">
              Não há nenhum evento meteorológico relevante associado à sua apólice no
              momento. Apólice, Comunicados e Meus Dados continuam disponíveis pela
              navegação.
            </p>
          </>
        )}

        {(estado === 'alerta' || (estado === 'erro' && resolvidoAoMenosUmaVez)) && alerta && (
          <>
            <h1>Alerta preventivo para sua área</h1>
            <p className="introducao">
              Este é um comunicado preventivo privado: não substitui as autoridades
              competentes e não confirma cobertura ou indenização.
            </p>

            {alerta.fonteDegradada && (
              <p className="aviso-fonte-degradada" role="status">
                <WarningIcon aria-hidden="true" size={20} weight="fill" />
                Fonte meteorológica degradada: este é o último dado disponível,{' '}
                {calcularIdade(alerta.instanteObservado)}, apenas informativo — nenhum
                alerta novo foi produzido a partir dele.
              </p>
            )}

            <section aria-labelledby="titulo-alerta" className="alerta-principal">
              <div aria-hidden="true" className="icone-alerta">
                <CloudRainIcon size={32} weight="fill" />
              </div>
              <div>
                <span className="nivel-risco">
                  {alerta.origem === 'sintetico' && (
                    <FlaskIcon aria-hidden="true" size={16} weight="fill" />
                  )}
                  {rotuloOrigem(alerta.origem)}
                </span>
                <h2 id="titulo-alerta">{rotuloEvento(alerta.eventoTipo)}</h2>
                <p>{alerta.severidade}</p>
                <p>
                  Previsto entre {alerta.periodoInicio} e {alerta.periodoFim} em{' '}
                  {alerta.localizacao}.
                </p>
              </div>
            </section>

            <section aria-labelledby="titulo-impactos">
              <h2 id="titulo-impactos">Impactos esperados</h2>
              <ul>
                {alerta.impactosEsperados.map((impacto) => (
                  <li key={impacto}>{impacto}</li>
                ))}
              </ul>
            </section>

            <section aria-labelledby="titulo-acoes">
              <h2 id="titulo-acoes">Como se prevenir</h2>
              <ul className="acoes-preventivas">
                {alerta.recomendacoes.map((recomendacao) => (
                  <li key={recomendacao}>{recomendacao}</li>
                ))}
              </ul>
            </section>
          </>
        )}
      </main>

      {(estado === 'alerta' || (estado === 'erro' && resolvidoAoMenosUmaVez)) && alerta && (
        <aside aria-labelledby="titulo-contexto" className="painel-contextual">
          <div>
            <p className="rotulo-contexto">Contexto do alerta</p>
            <h2 id="titulo-contexto">Por que este alerta é relevante?</h2>
          </div>
          <dl>
            <div>
              <dt>Localização</dt>
              <dd>{alerta.localizacao}</dd>
            </div>
            <div>
              <dt>Origem do dado</dt>
              <dd>{rotuloOrigem(alerta.origem)}</dd>
            </div>
            <div>
              <dt>Horário do dado</dt>
              <dd>{alerta.instanteObservado}</dd>
            </div>
          </dl>
          <div className="nota-dados">
            <CalendarDotsIcon aria-hidden="true" size={24} />
            <p>
              <strong>
                {alerta.origem === 'sintetico' ? 'Dados sintéticos' : 'Dados reais (INMET)'}
              </strong>
              <br />
              {alerta.origem === 'sintetico'
                ? 'Informações criadas somente para demonstração.'
                : 'Observação real da estação meteorológica monitorada.'}
            </p>
          </div>
        </aside>
      )}
    </>
  )
}
