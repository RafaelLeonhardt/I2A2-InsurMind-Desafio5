type PropriedadesSuperficieFAQ = {
  /** Quando true, renderiza como `<section>` sem `id`/foco próprios em vez de `<main>`
   * (5.7, `PainelSegurado`): evita landmark e id duplicados ao compor esta superfície
   * junto de outras na mesma página. Ausente/false preserva o comportamento original. */
  comoSecao?: boolean
}

type ItemFAQ = {
  pergunta: string
  resposta: string
}

const ITENS_FAQ: ItemFAQ[] = [
  {
    pergunta: 'Por que recebi este alerta?',
    resposta:
      'Você recebe um alerta quando um evento meteorológico — real ou de um cenário ' +
      'sintético demonstrativo — corresponde a uma regra preventiva configurada para a ' +
      'sua apólice sintética. Nenhum alerta nasce de um sinistro real: é uma simulação ' +
      'educacional de como a comunicação preventiva funcionaria.',
  },
  {
    pergunta: 'A mensagem foi realmente enviada?',
    resposta:
      'Não. Todo o ambiente é uma simulação: nenhuma mensagem real é enviada por ' +
      'WhatsApp, e-mail ou SMS. O que você vê como "comunicado" é uma prévia exata de ' +
      'como a mensagem apareceria no canal, registrada só para fins de demonstração.',
  },
  {
    pergunta: 'Quais dados a IA utiliza?',
    resposta:
      'Somente os dados sintéticos já cadastrados para o segurado simulado — apólice, ' +
      'cobertura, localização — e o evento meteorológico identificado, nunca dados reais ' +
      'de terceiros. Você pode conferir exatamente quais categorias de dado foram usadas ' +
      'em cada mensagem na seção "Como esta mensagem foi criada".',
  },
  {
    pergunta: 'Como trocar o segurado simulado?',
    resposta:
      'Use o seletor "Visualizar como" no topo do seu painel para alternar entre os ' +
      'segurados sintéticos disponíveis. Trocar o segurado atualiza todas as seções — ' +
      'alertas, comunicados, apólice — para o novo contexto.',
  },
]

/**
 * Superfície "Dúvidas frequentes" do perfil Segurado (FAQ-01..04, 6.9): conteúdo
 * educacional estático, sem chamada de API. Cada pergunta é um `<details>` nativo,
 * aberto por padrão — satisfaz FAQ-01 (respostas visíveis ao acessar a seção) e o
 * expandir/recolher independente de FAQ-03/04 vem de graça do comportamento nativo do
 * elemento, sem estado React algum.
 */
export function SuperficieFAQ({ comoSecao }: PropriedadesSuperficieFAQ) {
  const ElementoRaiz: 'main' | 'section' = comoSecao ? 'section' : 'main'
  const atributosRaiz = comoSecao ? {} : { id: 'conteudo-principal', tabIndex: -1 }

  return (
    <ElementoRaiz className="conteudo" {...atributosRaiz}>
      <h1>Dúvidas frequentes</h1>
      <p className="introducao">
        Ambiente educacional. Dados sintéticos. Nenhum envio real de mensagens é realizado.
      </p>
      <div className="faq">
        {ITENS_FAQ.map((item) => (
          <details key={item.pergunta} open>
            <summary>{item.pergunta}</summary>
            <p>{item.resposta}</p>
          </details>
        ))}
      </div>
    </ElementoRaiz>
  )
}
