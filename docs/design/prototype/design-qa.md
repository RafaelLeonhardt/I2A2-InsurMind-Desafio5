# Design QA — Central Preventiva

## Escopo

- Tela de referência: `docs/mockups/images/00-visao-geral-segurado.png`
- Implementação validada: `prototype/central-preventiva`
- Captura da implementação: `implementation-home-1440x1024.png`
- Estado comparado: perfil **Segurado**, segurado ativo **Carlos Eduardo Ferreira**, tela **Visão geral**

## Evidências de comparação

| Evidência | Dimensões | Observação |
| --- | ---: | --- |
| Referência visual | 1487 × 1058 px | Imagem 1 escolhida como direção principal |
| Implementação | 1440 × 1024 px | Captura no navegador integrado, escala 1× |

A comparação lado a lado confirmou a mesma estrutura visual principal: menu lateral escuro com ambientação de chuva, barra superior com seletores, conteúdo preventivo central, painel contextual à direita, linha do tempo de comunicações e chamadas para simulação e explicabilidade.

## Verificação visual

- Hierarquia e composição: aprovadas.
- Paleta, contraste e atmosfera: aprovados.
- Tipografia e densidade: aprovadas, com pequenas diferenças naturais de renderização entre a imagem gerada e o navegador.
- Alinhamento e espaçamento: aprovados para a resolução validada.
- Conteúdo principal e estados visuais: aprovados.
- Ativos rasterizados: carregados corretamente.

## Interações verificadas

- Alternância entre os perfis Administrador e Segurado.
- Seleção do segurado ativo e atualização de cidade, endereço, apólice, canal e nível de risco.
- Abertura e fechamento do painel “Como esta mensagem foi criada”.
- Fluxo administrativo: evento climático → análise da regra → geração de mensagens → aprovação → confirmação → resultado da simulação.
- Edição, salvamento e validação de regra de negócio.
- Recuperação simulada da fonte meteorológica em estado degradado.
- Navegação pelas telas auxiliares do segurado e do administrador.
- Verificação de erros e avisos no console: nenhum encontrado.

## Verificação técnica

- `npm run build`: aprovado.
- `npm run test:sites`: 4 testes aprovados.
- Aplicação carregada e exercitada no navegador integrado.

## Histórico de iteração

1. Implementação inicial baseada na imagem escolhida e nos mockups documentados.
2. Ajuste da área de validação para conferir ações posicionadas abaixo da primeira dobra.
3. Comparação visual final em 1440 × 1024 e repetição dos fluxos críticos.

## Resultado final

passed
