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

Elegibilidades pré-calculadas da demonstração, com casos elegíveis e não elegíveis.

| Coluna | Tipo | Restrições |
| --- | --- | --- |
| `id` | `UUID` | chave primária |
| `evento_id` | `UUID` | `NOT NULL`, chave estrangeira lógica para `eventos_meteorologicos(id)` |
| `regra_id` | `UUID` | `NOT NULL`, chave estrangeira lógica para `regras(id)` |
| `segurado_id` | `UUID` | `NOT NULL`, chave estrangeira lógica para `segurados(id)` |
| `apolice_id` | `UUID` | `NOT NULL`, chave estrangeira lógica para `apolices(id)` |
| `elegivel` | `BOOLEAN` | `NOT NULL` |
| `justificativa` | `VARCHAR` | `NOT NULL` |
| `criado_em` | `TIMESTAMP` | `NOT NULL`, timestamp, padrão `now()` |

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
