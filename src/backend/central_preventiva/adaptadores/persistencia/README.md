# Persistência em DuckDB

Documento versionado do schema operacional da Central Preventiva e da estratégia de migração local.
O arquivo operacional fica fora do controle de versão (`var/central_preventiva.duckdb`, ignorado pelo
Git) e é integralmente recriável a partir das migrações e do seed versionados neste repositório.

## Estratégia de migração local

- Cada migração é um arquivo `migracoes/NNNN_descricao.sql`, numerado a partir de `0001`.
- A tabela `schema_migracoes` é o registro de migrações aplicadas: uma linha por versão aplicada.
- `ExecutorMigracoes.aplicar_pendentes()` aplica em ordem crescente somente as versões maiores que a
  maior versão registrada. Cada migração roda em sua própria transação (`BEGIN`/`COMMIT`), e o
  registro em `schema_migracoes` é gravado dentro da mesma transação da migração.
- Se uma migração falhar, ela é revertida por inteiro (o DuckDB suporta DDL transacional), não é
  registrada, e a execução para. As migrações anteriores permanecem aplicadas. A próxima execução
  retoma a partir da primeira migração pendente.
- Se a versão registrada for maior que a maior versão conhecida pelo código, a inicialização é
  recusada sem nenhuma mutação (`VersaoSchemaFutura`).
- Se o banco possuir tabelas mas não possuir um `schema_migracoes` íntegro, a inicialização é
  recusada em vez de presumir o estado do schema (`RegistroMigracoesInvalido`).
- Migrações aplicadas nunca são editadas. Uma correção entra como uma nova migração numerada.

## Convenções de colunas

- Identificadores de negócio usam `UUID` como chave primária.
- Colunas de timestamp usam `TIMESTAMP NOT NULL DEFAULT now()`: `criado_em` marca a inserção e
  `atualizado_em` marca a última alteração, presente apenas nas tabelas mutáveis.
- Domínios fechados são validados por restrições `CHECK` na própria tabela.
- As relações entre tabelas são documentadas aqui e no arquivo de migração, mas **não** são
  declaradas como `REFERENCES` no DuckDB.

  # SPEC_DEVIATION: o `design.md` declara `REFERENCES` nas tabelas de referência.
  # Motivo: o DuckDB não adia a verificação de chave estrangeira. Com `REFERENCES`, ele recusa
  # apagar uma tabela referenciada na mesma transação em que suas filhas foram apagadas, e
  # recusa até atualizar uma coluna `LIST` (`apolices.coberturas`) de uma tabela referenciada
  # (duckdb/duckdb#13819). Isso torna impossível a restauração transacional exigida por
  # SEED-09. As colunas de relacionamento continuam documentadas como chave estrangeira lógica
  # e a integridade é garantida pelo conjunto sintético versionado, único escritor destas
  # tabelas.

## Tabelas da migração `0001_schema_inicial`

### `schema_migracoes`

Registro das migrações aplicadas.

| Coluna | Tipo | Restrições |
| --- | --- | --- |
| `versao` | `INTEGER` | chave primária |
| `descricao` | `VARCHAR` | `NOT NULL` |
| `aplicada_em` | `TIMESTAMP` | `NOT NULL`, timestamp, padrão `now()` |

### `segurados`

Pessoas seguradas sintéticas da demonstração.

| Coluna | Tipo | Restrições |
| --- | --- | --- |
| `id` | `UUID` | chave primária |
| `nome` | `VARCHAR` | `NOT NULL` |
| `codigo_ibge_area` | `VARCHAR` | `NOT NULL` |
| `canal_preferido` | `VARCHAR` | `NOT NULL`, `CHECK` em `whatsapp`, `email`, `sms` |
| `participa_de_alertas` | `BOOLEAN` | `NOT NULL`, padrão `true` |
| `criado_em` | `TIMESTAMP` | `NOT NULL`, timestamp, padrão `now()` |
| `atualizado_em` | `TIMESTAMP` | `NOT NULL`, timestamp, padrão `now()` |

### `apolices`

Apólices sintéticas vinculadas a uma pessoa segurada.

| Coluna | Tipo | Restrições |
| --- | --- | --- |
| `id` | `UUID` | chave primária |
| `segurado_id` | `UUID` | `NOT NULL`, chave estrangeira lógica para `segurados(id)` |
| `numero` | `VARCHAR` | `NOT NULL` |
| `tipo` | `VARCHAR` | `NOT NULL`, `CHECK` em `residencial`, `automovel` |
| `situacao` | `VARCHAR` | `NOT NULL`, `CHECK` em `ativa`, `cancelada`, `suspensa` |
| `vigencia_inicio` | `DATE` | `NOT NULL` |
| `vigencia_fim` | `DATE` | `NOT NULL` |
| `coberturas` | `VARCHAR[]` | `NOT NULL` |
| `endereco_risco_sintetico` | `VARCHAR` | `NOT NULL` |
| `codigo_ibge_area` | `VARCHAR` | `NOT NULL` |
| `criado_em` | `TIMESTAMP` | `NOT NULL`, timestamp, padrão `now()` |
| `atualizado_em` | `TIMESTAMP` | `NOT NULL`, timestamp, padrão `now()` |

### `regras`

Regras objetivas de risco e elegibilidade, versionadas por substituição.

| Coluna | Tipo | Restrições |
| --- | --- | --- |
| `id` | `UUID` | chave primária |
| `evento_tipo` | `VARCHAR` | `NOT NULL`, `CHECK` em `chuva_intensa`, `granizo` |
| `limiar_meteorologico` | `DOUBLE` | `NOT NULL` |
| `area_aplicavel` | `VARCHAR` | `NOT NULL` |
| `apolice_tipo` | `VARCHAR` | `NOT NULL`, `CHECK` em `residencial`, `automovel` |
| `cobertura_exigida` | `VARCHAR` | `NOT NULL` |
| `antecedencia_horas` | `INTEGER` | `NOT NULL` |
| `canal` | `VARCHAR` | `NOT NULL` |
| `versao` | `INTEGER` | `NOT NULL`, padrão `1` |
| `estado` | `VARCHAR` | `NOT NULL`, `CHECK` em `ativa`, `substituida`, padrão `ativa` |
| `criado_em` | `TIMESTAMP` | `NOT NULL`, timestamp, padrão `now()` |

#### Limiares de relevância (`AvaliadorRisco`, História 2.3)

`limiar_meteorologico` é o único limiar numérico consumido pelo `AvaliadorRisco`
(`dominio/avaliador_risco.py`), lido da regra `ativa` de cada `evento_tipo` — nenhuma
constante paralela existe no código (a única fonte de verdade é esta tabela, semeada por
`semeador.py`).

| `evento_tipo` | Limiar padrão da demonstração | Fronteira | Justificativa |
| --- | --- | --- | --- |
| `chuva_intensa` | `50.0` mm acumulados no período do evento | **Inclusiva** (`intensidade >= limiar`) | Valor de referência de classificações meteorológicas públicas para "chuva forte/muito forte" em 24h; default de demonstração, não um valor operacional real |
| `granizo` | Nenhum (relevante por ocorrência do tipo) | Não se aplica — nenhuma fronteira exclusiva está configurada nesta demonstração | Estações automáticas do INMET não reportam severidade de granizo (AD-013); a ocorrência do tipo já é o gatilho, sujeito só ao critério de área aplicável |

**Exemplos no valor-limite de `chuva_intensa` (fronteira inclusiva):**

| Intensidade observada | Resultado | Por quê |
| --- | --- | --- |
| `49.9` mm | Não relevante | Abaixo do limiar |
| `50.0` mm | **Relevante** | No limiar exato — fronteira inclusiva |
| `50.1` mm | Relevante | Acima do limiar |

### `eventos_meteorologicos`

Eventos meteorológicos observados ou sintéticos.

| Coluna | Tipo | Restrições |
| --- | --- | --- |
| `id` | `UUID` | chave primária |
| `tipo` | `VARCHAR` | `NOT NULL`, `CHECK` em `chuva_intensa`, `granizo` |
| `area` | `VARCHAR` | `NOT NULL` |
| `periodo_inicio` | `TIMESTAMP` | `NOT NULL`, timestamp |
| `periodo_fim` | `TIMESTAMP` | `NOT NULL`, timestamp |
| `intensidade` | `DOUBLE` | `NOT NULL` |
| `proveniencia` | `VARCHAR` | `NOT NULL`, `CHECK` em `real_inmet`, `sintetico` |
| `instante_observado` | `TIMESTAMP` | `NOT NULL`, timestamp |
| `criado_em` | `TIMESTAMP` | `NOT NULL`, timestamp, padrão `now()` |

### `elegibilidades_historicas`

Elegibilidades pré-calculadas da demonstração, com casos elegíveis e não elegíveis. Ver a
tabela abaixo já atualizada com o estado pós-`0007` (colunas `execucao_id`, `criterios`,
`canal`, `nome_segurado`).

| Coluna | Tipo | Restrições |
| --- | --- | --- |
| `id` | `UUID` | chave primária |
| `execucao_id` | `UUID` | nulo identifica linha semeada de demonstração (migração `0006`); chave estrangeira lógica para `execucao_preventiva(id)` quando presente |
| `evento_id` | `UUID` | `NOT NULL`, chave estrangeira lógica para `eventos_meteorologicos(id)` |
| `regra_id` | `UUID` | `NOT NULL`, chave estrangeira lógica para `regras(id)` |
| `segurado_id` | `UUID` | `NOT NULL`, chave estrangeira lógica para `segurados(id)` |
| `apolice_id` | `UUID` | `NOT NULL`, chave estrangeira lógica para `apolices(id)` |
| `elegivel` | `BOOLEAN` | `NOT NULL` |
| `criterios` | `VARCHAR` | `NOT NULL`, JSON serializado com critério a critério, mesmo formato de `avaliacoes_risco.criterios` (migração `0006`); `[]` nas linhas semeadas de demonstração (corrigido em `0007` — o backfill original gravava um objeto JSON, incompatível com o parser de critérios) |
| `canal` | `VARCHAR` | `NOT NULL`, canal preferencial do segurado congelado no momento da avaliação — nunca referência viva a `segurados.canal_preferido` (AD-11, migração `0006`) |
| `nome_segurado` | `VARCHAR` | `NOT NULL`, nome do segurado congelado no momento da avaliação — nunca referência viva a `segurados.nome` (AD-11, migração `0007`) |
| `justificativa` | `VARCHAR` | `NOT NULL` |
| `criado_em` | `TIMESTAMP` | `NOT NULL`, timestamp, padrão `now()` |

`UNIQUE(execucao_id, evento_id, regra_id, segurado_id, apolice_id)` (migração `0006`) garante no
máximo um resultado por combinação (AD-10); linhas semeadas com `execucao_id NULL` nunca colidem
entre si. A área da apólice não é uma coluna própria — o repositório a deriva do critério
"área afetada", sempre o primeiro elemento de `criterios` (AD-11: evita tanto uma segunda
cópia armazenada quanto uma releitura ao vivo de `apolices.codigo_ibge_area`).

### `execucao_preventiva`

Casca mínima da execução preventiva. Existe nesta história apenas para tornar testável a guarda de
restauração; os épicos 2 e 3 estendem esta tabela e adicionam suas tabelas filhas.

| Coluna | Tipo | Restrições |
| --- | --- | --- |
| `id` | `UUID` | chave primária |
| `estado` | `VARCHAR` | `NOT NULL`, valores de `dominio.estados_execucao.EstadoExecucao` |
| `versao` | `INTEGER` | `NOT NULL`, padrão `1` |
| `criado_em` | `TIMESTAMP` | `NOT NULL`, timestamp, padrão `now()` |
| `atualizado_em` | `TIMESTAMP` | `NOT NULL`, timestamp, padrão `now()` |

### `chaves_idempotencia`

Armazenamento genérico de `Idempotency-Key`, reutilizável por qualquer `POST` mutável.

| Coluna | Tipo | Restrições |
| --- | --- | --- |
| `chave` | `VARCHAR` | `NOT NULL`, parte da chave primária composta |
| `operacao` | `VARCHAR` | `NOT NULL`, parte da chave primária composta |
| `hash_requisicao` | `VARCHAR` | `NOT NULL` |
| `resposta_status` | `INTEGER` | `NOT NULL` |
| `resposta_corpo` | `VARCHAR` | `NOT NULL` |
| `criado_em` | `TIMESTAMP` | `NOT NULL`, timestamp, padrão `now()` |

## Tabelas da migração `0002_meteorologia`

### `areas_monitoradas_inmet`

Mapeia uma estação/área real do INMET para o `codigo_ibge_area` sintético usado pela demonstração
(AD-007). Tabela de configuração versionada — faz parte da lista de exceções da restauração (AD-014).

| Coluna | Tipo | Restrições |
| --- | --- | --- |
| `id` | `UUID` | chave primária |
| `codigo_estacao_inmet` | `VARCHAR` | `NOT NULL`, código real da estação (`CD_ESTACAO`) |
| `nome_estacao` | `VARCHAR` | `NOT NULL` |
| `codigo_ibge_area` | `VARCHAR` | `NOT NULL`, chave estrangeira lógica para `segurados`/`apolices(codigo_ibge_area)` |
| `ativa` | `BOOLEAN` | `NOT NULL`, padrão `true` |
| `criado_em` | `TIMESTAMP` | `NOT NULL`, timestamp, padrão `now()` |

### `sincronizacoes_meteorologicas`

Histórico de cada tentativa de coleta meteorológica (manual ou automática).

| Coluna | Tipo | Restrições |
| --- | --- | --- |
| `id` | `UUID` | chave primária |
| `requisicao_id` | `UUID` | `NOT NULL`, correlação (AD-10) |
| `area_monitorada_id` | `UUID` | `NOT NULL`, chave estrangeira lógica para `areas_monitoradas_inmet(id)` |
| `origem` | `VARCHAR` | `NOT NULL`, `CHECK` em `automatica`, `manual` |
| `estado` | `VARCHAR` | `NOT NULL`, `CHECK` em `coletando`, `normalizando`, `concluido`, `falha` |
| `registros_validos` | `INTEGER` | `NOT NULL`, padrão `0` |
| `motivo_falha` | `VARCHAR` | nulo se `estado != 'falha'` |
| `iniciado_em` | `TIMESTAMP` | `NOT NULL`, timestamp, padrão `now()` |
| `finalizado_em` | `TIMESTAMP` | nulo enquanto em andamento |

## Tabelas da migração `0003_resiliencia_meteorologica`

### `eventos_meteorologicos` — `UNIQUE` de deduplicação (recreate-and-copy)

A migração `0003` adiciona `UNIQUE (tipo, area, periodo_inicio, periodo_fim)` a `eventos_meteorologicos`
recriando a tabela dentro da própria transação (AD-015): `CREATE TABLE eventos_meteorologicos_nova`
com a constraint declarada no `CREATE`, `INSERT INTO ... SELECT` preservando todas as linhas
existentes, `DROP TABLE`, `ALTER TABLE ... RENAME`. Necessário porque o DuckDB não suporta
`ALTER TABLE ADD CONSTRAINT`. A constraint de tabela (não um índice posterior) é o que garante a
semântica de `INSERT ... ON CONFLICT DO NOTHING` exigida pelo insert-or-noop de AD-010 — a coleta
real que recupera um evento já registrado sinteticamente (ou vice-versa) não duplica a linha.

### `tentativas_coleta_meteorologica`

Registra cada tentativa individual de uma coleta com retry (número, resultado, início e término).

| Coluna | Tipo | Restrições |
| --- | --- | --- |
| `id` | `UUID` | chave primária |
| `sincronizacao_id` | `UUID` | `NOT NULL`, chave estrangeira lógica para `sincronizacoes_meteorologicas(id)` |
| `numero_tentativa` | `INTEGER` | `NOT NULL`, `CHECK` entre 1 e 3 |
| `codigo_resultado` | `VARCHAR` | `NOT NULL`, `CHECK` em `sucesso`, `timeout`, `erro_transporte`, `status_erro` |
| `iniciado_em` | `TIMESTAMP` | `NOT NULL`, timestamp |
| `finalizado_em` | `TIMESTAMP` | `NOT NULL`, timestamp |

### `excecoes_operacionais`

Registra a exceção operacional (causa, tentativas, impacto) quando uma execução esgota as
tentativas e alcança `falhou_coleta`.

| Coluna | Tipo | Restrições |
| --- | --- | --- |
| `id` | `UUID` | chave primária |
| `execucao_id` | `UUID` | `NOT NULL`, chave estrangeira lógica para `execucao_preventiva(id)` |
| `causa` | `VARCHAR` | `NOT NULL` |
| `tentativas` | `INTEGER` | `NOT NULL` |
| `impacto` | `VARCHAR` | `NOT NULL` |
| `criado_em` | `TIMESTAMP` | `NOT NULL`, timestamp, padrão `now()` |

### `cenarios_sinteticos_ativados`

Rastreia quando/qual cenário sintético de contingência foi ativado, para a interface explicar a
origem sintética da coleta.

| Coluna | Tipo | Restrições |
| --- | --- | --- |
| `id` | `UUID` | chave primária |
| `sincronizacao_id` | `UUID` | `NOT NULL`, chave estrangeira lógica para `sincronizacoes_meteorologicas(id)` |
| `identificador_cenario` | `VARCHAR` | `NOT NULL`, id determinístico do cenário sintético do conjunto demonstrativo |
| `ativado_em` | `TIMESTAMP` | `NOT NULL`, timestamp, padrão `now()` |

## Tabelas da migração `0004_avaliacao_risco`

### `avaliacoes_risco`

Snapshot imutável da avaliação de relevância meteorológica (AD-5: decisão 100% determinística,
sem LLM; AD-11: uma mudança futura em `regras` nunca recalcula uma avaliação já feita — por isso
`regra_versao` é gravada como valor observado no momento, não como referência viva à tabela).

| Coluna | Tipo | Restrições |
| --- | --- | --- |
| `id` | `UUID` | chave primária |
| `execucao_id` | `UUID` | `NOT NULL`, chave estrangeira lógica para `execucao_preventiva(id)` |
| `evento_id` | `UUID` | `NOT NULL`, chave estrangeira lógica para `eventos_meteorologicos(id)` |
| `regra_id` | `UUID` | nulo se não havia regra ativa para o tipo do evento (migração `0005`); chave estrangeira lógica para `regras(id)` quando presente |
| `regra_versao` | `INTEGER` | nulo pelo mesmo motivo que `regra_id`; snapshot da versão da regra no momento da avaliação quando presente |
| `relevante` | `BOOLEAN` | `NOT NULL` |
| `criterios` | `VARCHAR` | `NOT NULL`, JSON serializado com operando/valor observado/resultado/justificativa por critério (vazio, `[]`, quando não havia regra ativa) |
| `motivo` | `VARCHAR` | `NOT NULL` |
| `criado_em` | `TIMESTAMP` | `NOT NULL`, timestamp, padrão `now()` |

## Tabelas da migração `0005_avaliacao_risco_sem_regra`

Nenhuma tabela nova — a migração relaxa `avaliacoes_risco.regra_id`/`regra_versao` de `NOT NULL`
para aceitar `NULL` (recreate-and-copy, AD-015: DuckDB não suporta `ALTER COLUMN DROP NOT NULL`),
para que o terminal `sem_risco` sem regra ativa (RISCO-09) fique persistido e explicável, em vez
de não gerar nenhuma linha. Ver a tabela `avaliacoes_risco` acima, já atualizada com o estado
pós-`0005`.

## Tabelas da migração `0006_elegibilidade`

Nenhuma tabela nova — a migração recria `elegibilidades_historicas` por recreate-and-copy
(AD-015: DuckDB não suporta `ALTER TABLE ADD COLUMN ... NOT NULL` nem `ADD CONSTRAINT` sobre uma
tabela com linhas existentes), acrescentando `execucao_id`, `criterios`, `canal` e a `UNIQUE`
de dedução (AD-10). As 4 linhas semeadas do Épico 1 recebem backfill determinístico:
`execucao_id = NULL`, `criterios = '{"origem": "seed_demonstrativo"}'` e `canal` lido de
`segurados.canal_preferido` via `JOIN` na própria migração. Ver a tabela `elegibilidades_historicas`
acima, já atualizada com o estado pós-`0007`.

## Tabelas da migração `0007_elegibilidade_correcoes`

Nenhuma tabela nova — corrige um defeito do backfill de `0006` e acrescenta uma coluna.
Recreate-and-copy (AD-015), na mesma tabela `elegibilidades_historicas`:

- **Correção do backfill de `criterios`**: `0006` gravou `'{"origem": "seed_demonstrativo"}'`
  (um objeto JSON) nas 4 linhas semeadas, mas o parser de critérios (`serializacao_criterios.py`)
  espera uma lista — qualquer leitura dessas linhas por `RepositorioElegibilidades` lançava
  `TypeError`, e o endpoint HTTP de detalhe devolvia `500` em vez de `404` (achado do
  Verificador). Corrigido para `'[]'`, mesma convenção de `avaliacoes_risco` (migração `0005`,
  2.3) para "nenhum critério real avaliado".
- **`nome_segurado` (nova coluna, `NOT NULL`)**: antes o nome do segurado era lido ao vivo de
  `segurados.nome` no momento da consulta (`JOIN`) — um nome alterado depois de uma avaliação
  concluída reescreveria a explicação histórica, violando ELEG-04.3 (AD-11). Passa a ser gravado
  como snapshot em `RepositorioElegibilidades.salvar`; as 4 linhas semeadas recebem backfill via
  `JOIN` em `segurados.nome` na própria migração (última vez que essa tabela é lida ao vivo para
  preencher esta coluna).

## Tabelas da migração `0008_marcos_execucao`

### `marcos_execucao`

Histórico de transições de uma execução preventiva, correlacionadas por `execucao_id`
(RUNNER-02, AD-10) — o `GerenciadorExecucoes` (2.6) grava um marco a cada etapa concluída
(`coleta_concluida`, `avaliacao_risco_concluida`, `publico_elegivel_formado`, ou o próprio
nome do estado terminal alcançado), permitindo que a reidratação (RUNNER-07) reconstrua o
que aconteceu sem recalcular nada.

| Coluna | Tipo | Restrições |
| --- | --- | --- |
| `id` | `UUID` | chave primária |
| `execucao_id` | `UUID` | `NOT NULL`, chave estrangeira lógica para `execucao_preventiva(id)` |
| `marco` | `VARCHAR` | `NOT NULL` |
| `causa` | `VARCHAR` | nulo quando não aplicável (marco de sucesso, não de falha) |
| `criado_em` | `TIMESTAMP` | `NOT NULL`, timestamp, padrão `now()` |

## Tabelas da migração `0009_preflight_ia`

A migração acrescenta uma coluna a `execucao_preventiva` e cria `contextos_agente`.

### Coluna nova em `execucao_preventiva`

| Coluna | Tipo | Restrições |
| --- | --- | --- |
| `execucao_origem_id` | `UUID` | nulo; presente só em execuções correlacionadas, onde aponta para a execução terminal que originou a nova tentativa (chave estrangeira lógica para `execucao_preventiva(id)`) |

A coluna entra por `ALTER TABLE ADD COLUMN`, não por recreate-and-copy: é nula, não declara
nenhuma restrição e não precisa de backfill (`NULL` já é o valor correto de toda execução
pré-existente, que não é correlacionada). O recreate-and-copy do AD-015 governa restrições novas
e colunas com backfill, e nenhum dos dois casos ocorre aqui.

### `contextos_agente`

Contexto mínimo montado para cada item do público elegível antes da geração de mensagens, e a
proveniência desse contexto: quais categorias de dados foram usadas e quais foram deliberadamente
deixadas de fora (PREFL-11..14). O conteúdo é o JSON dos cinco campos permitidos (evento,
localização aproximada, coberturas relevantes, canal, orientações de segurança) — nunca documento,
dado financeiro, dado de pagamento ou credencial.

| Coluna | Tipo | Restrições |
| --- | --- | --- |
| `id` | `UUID` | chave primária |
| `execucao_id` | `UUID` | `NOT NULL`, chave estrangeira lógica para `execucao_preventiva(id)` |
| `elegibilidade_id` | `UUID` | `NOT NULL`, `UNIQUE`, chave estrangeira lógica para `elegibilidades_historicas(id)` |
| `conteudo` | `VARCHAR` | `NOT NULL`, JSON serializado do contexto mínimo |
| `categorias_usadas` | `VARCHAR[]` | `NOT NULL` |
| `categorias_nao_usadas` | `VARCHAR[]` | `NOT NULL` |
| `criado_em` | `TIMESTAMP` | `NOT NULL`, timestamp, padrão `now()` |

A `UNIQUE (elegibilidade_id)` garante um contexto por item elegível. É essa restrição que torna
obrigatória a cópia das elegibilidades da origem em uma nova tentativa (AD-012): sem cópia, a
segunda execução colidiria com o contexto já gravado pela primeira.

## Tabelas da migração `0010_mensagens`

A migração cria as duas tabelas da produção de mensagens preventivas (História 3.2). O `design.md`
da história numera o arquivo como `0008_mensagens.sql`; `0008` e `0009` já haviam sido consumidos
pelas Histórias 2.6 e 3.1, então a migração entrou como `0010` — mesma renumeração já registrada
desde a 2.4.

### `mensagens`

Uma mensagem por combinação de item elegível e canal, com o estado de conteúdo do segundo diagrama
do AD-4 (`gerando`, `criticando`, `aguardando_revisao`, `aprovada`, `rejeitada`, `excluida`,
`simulada_entregue`, `falhou_conteudo`, `falhou_integracao_ia`).

| Coluna | Tipo | Restrições |
| --- | --- | --- |
| `id` | `UUID` | chave primária |
| `execucao_id` | `UUID` | `NOT NULL`, chave estrangeira lógica para `execucao_preventiva(id)` |
| `elegibilidade_id` | `UUID` | `NOT NULL`, chave estrangeira lógica para `elegibilidades_historicas(id)` |
| `canal` | `VARCHAR` | `NOT NULL`, `CHECK` em `whatsapp`, `email`, `sms` |
| `estado` | `VARCHAR` | `NOT NULL`, valores de `dominio.estados_mensagem.EstadoMensagem` |
| `tentativa_atual` | `INTEGER` | `NOT NULL`, padrão `1`, `CHECK` entre 1 e 3 |
| `versao` | `INTEGER` | `NOT NULL`, padrão `1` — concorrência otimista (AD-008) |
| `criado_em` | `TIMESTAMP` | `NOT NULL`, timestamp, padrão `now()` |
| `atualizado_em` | `TIMESTAMP` | `NOT NULL`, timestamp, padrão `now()` |

Restrição `UNIQUE (elegibilidade_id, canal)`: é a dedução de conteúdo do AD-010. Com ela, reinvocar
a geração de uma execução já processada é um no-op idempotente (`INSERT ... ON CONFLICT DO
NOTHING`), nunca uma segunda mensagem para o mesmo item e canal (GERAR-06, GERAR-11, GERAR-12).

### `versoes_mensagem`

Uma linha por tentativa de geração de uma mensagem, com o conteúdo estruturado devolvido pelo
agente redator, o veredito determinístico do `ValidadorSaidaCanal` e as métricas da chamada.

| Coluna | Tipo | Restrições |
| --- | --- | --- |
| `id` | `UUID` | chave primária |
| `mensagem_id` | `UUID` | `NOT NULL`, chave estrangeira lógica para `mensagens(id)` |
| `numero_tentativa` | `INTEGER` | `NOT NULL` |
| `conteudo` | `VARCHAR` | `NOT NULL`, JSON serializado (`{corpo}` ou `{assunto, corpo}`) |
| `valida` | `BOOLEAN` | `NOT NULL` |
| `motivo_invalidez` | `VARCHAR` | nulo quando `valida = true` |
| `duracao_ms` | `DOUBLE` | `NOT NULL` |
| `modelo` | `VARCHAR` | `NOT NULL` |
| `versao_prompt` | `VARCHAR` | `NOT NULL` |
| `tokens_entrada` | `INTEGER` | nulo se a chamada não devolveu métricas de uso |
| `tokens_saida` | `INTEGER` | nulo se a chamada não devolveu métricas de uso |
| `criado_em` | `TIMESTAMP` | `NOT NULL`, timestamp, padrão `now()` |

Uma versão inválida é registrada com `valida = false` e o `motivo_invalidez` persistido; a mensagem
permanece em `gerando` e nunca avança para `criticando` (GERAR-09). A política de nova tentativa de
conteúdo é da História 3.4, não desta.

## Tabelas da migração `0011_avaliacoes_criticas`

A migração cria a tabela da avaliação crítica de conteúdo (História 3.3). O `design.md` da história
numera o arquivo como `0009_avaliacoes_criticas.sql`; `0009` e `0010` já haviam sido consumidos
pelas Histórias 3.1 e 3.2, então a migração entrou como `0011` — mesma renumeração já registrada
desde a 2.4.

### `avaliacoes_criticas`

Uma linha por versão de mensagem avaliada pelo agente crítico, com a decisão, os motivos
estruturados por categoria fechada e a proveniência da chamada.

| Coluna | Tipo | Restrições |
| --- | --- | --- |
| `id` | `UUID` | chave primária |
| `versao_mensagem_id` | `UUID` | `NOT NULL`, chave estrangeira lógica para `versoes_mensagem(id)` |
| `aprovada` | `BOOLEAN` | `NOT NULL` — decisão textual do crítico, nunca a validação determinística |
| `motivos` | `VARCHAR` | `NOT NULL`, JSON serializado (lista de `{categoria, justificativa}`) |
| `agente` | `VARCHAR` | `NOT NULL`, padrão `'critico'` |
| `modelo` | `VARCHAR` | `NOT NULL` |
| `duracao_ms` | `DOUBLE` | `NOT NULL` |
| `criado_em` | `TIMESTAMP` | `NOT NULL`, timestamp, padrão `now()` |

Restrição `UNIQUE (versao_mensagem_id)`: é a dedução de conteúdo do AD-010 aplicada à avaliação —
uma versão de mensagem é avaliada uma única vez. Com ela, um replay idempotente da geração do lote
reaproveita a avaliação persistida (`INSERT ... ON CONFLICT DO NOTHING` seguido de leitura) em vez
de chamar a OpenAI de novo (terceiro Edge Case da 3.3).

Os valores de `motivos[].categoria` vêm do enum fechado `dominio.avaliacao_critica.CategoriaCritica`
(`tom`, `utilidade`, `clareza`, `seguranca`, `promessa_indevida`, `distincao_oficial`,
`adequacao_canal`) — os sete critérios do CRIT-03. Uma aprovação persiste `aprovada = true` com
`motivos = '[]'`.

A avaliação do crítico é textual e nunca sobrepõe a validação determinística de 3.2
(`versoes_mensagem.valida` / `motivo_invalidez`): uma saída estruturalmente inválida nunca sai de
`gerando` e, portanto, nunca chega a ter avaliação crítica (CRIT-04). Uma saída do crítico inválida
ou não interpretável não gera linha nenhuma nesta tabela: é falha da tentativa, nunca aprovação
(CRIT-07).
