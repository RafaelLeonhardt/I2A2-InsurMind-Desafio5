# Adaptador meteorológico do INMET

Documento de contrato da integração real com o INMET (`ADR-0013`), seguindo o mesmo padrão de
documentação de `adaptadores/persistencia/README.md`.

## Endpoint escolhido

- **Base**: `https://apitempo.inmet.gov.br` (lido de `Configuracao.url_base_inmet`,
  `CENTRAL_PREVENTIVA_URL_BASE_INMET`).
- **Catálogo de estações**: `GET /estacoes/T` — confirmado por sondagem direta no Design desta
  história (`design.md`, seção Research): serviço público, sem autenticação, JSON, campos
  `CD_ESTACAO`, `DC_NOME`, `VL_LATITUDE`, `VL_LONGITUDE`, `VL_ALTITUDE`, `SG_ESTADO`,
  `TP_ESTACAO`, `CD_SITUACAO`, `DT_INICIO_OPERACAO`, `DT_FIM_OPERACAO`.
- **Leitura horária por estação**: `GET /estacao/dados/{data}/{codigo_estacao}` (formato
  `AAAA-MM-DD`) — endpoint de leitura horária das estações automáticas do INMET.

## ⚠️ Status da prova desta task (T4)

Esta sessão de implementação rodou em um ambiente **sem egresso de rede** para
`apitempo.inmet.gov.br` (confirmado por tentativa de `curl` que não completou nenhuma conexão).
Não foi possível, portanto, executar a prova limitada ao vivo exigida pelo AC `INMET-01`/`INMET-02`
nesta sessão. Isso já era um risco aceito e registrado em `.specs/STATE.md` (Handoff): "campos de
leitura horária do INMET não confirmados ao vivo".

A amostra `leitura_chuva_valida.json` e `leitura_campo_ausente.json` abaixo são uma
**reconstrução de melhor esforço**, não uma captura ao vivo: os nomes de campo usados
(`CHUVA`, `TEM_INS`, `UMD_INS`, `PRE_INS`, `VEN_VEL`, `VEN_DIR`, `RAD_GLO`, `CD_ESTACAO`,
`DT_MEDICAO`, `HR_MEDICAO`) seguem a nomenclatura pública e amplamente documentada do INMET para
leituras horárias de estações automáticas (mesmo vocabulário usado nos arquivos de exportação do
BDMEP/INMET), mas **não foram confirmados por uma chamada HTTP real nesta sessão**. Qualquer
implementação do `NormalizadorInmet` (T5) que dependa destes nomes de campo deve ser revalidada
contra uma captura ao vivo assim que houver acesso de rede — isso não bloqueia o restante desta
história porque os testes de parsing usam exclusivamente estas amostras congeladas, mas é uma
dívida explícita a fechar antes de operar contra o INMET real em produção.

## Campos consumidos, unidades e normalização

| Campo INMET | Significado | Unidade | Mapeamento para `EventoMeteorologico` |
| --- | --- | --- | --- |
| `CD_ESTACAO` | Código da estação automática | — | Resolve `area` via `RepositorioAreasMonitoradas.buscar_por_codigo_estacao` (AD-007); ausência de mapeamento → rejeição "geografia não reconhecida" |
| `CHUVA` | Precipitação acumulada na hora | mm | `intensidade` (evento `chuva_intensa`); campo ausente ou não numérico → rejeição "campo ausente"/"medida inválida" |
| `DT_MEDICAO` + `HR_MEDICAO` | Data e hora da medição | `AAAA-MM-DD` + `HHMM` | Combinados em `instante_observado`; também usados para `periodo_inicio`/`periodo_fim` (janela de 1 hora da leitura) |
| `TEM_INS`, `UMD_INS`, `PRE_INS`, `VEN_VEL`, `VEN_DIR`, `RAD_GLO` | Temperatura, umidade, pressão, vento (velocidade/direção), radiação | °C, %, hPa, m/s, graus, kJ/m² | Não normalizados nesta história (fora do escopo de `EventoMeteorologico`, que só modela `chuva_intensa`/`granizo`); consumidos apenas para confirmar que a leitura é uma resposta válida da estação |

`tipo` é sempre `chuva_intensa` para leituras reais (AD-013 — leituras de estação automática não
têm campo de granizo). `proveniencia` é sempre `real_inmet` para respostas normalizadas a partir
deste endpoint.

## Cenário sintético de granizo (AD-013)

As leituras horárias de estações automáticas do INMET **não contêm nenhum campo de granizo**.
Por isso, `tipo = granizo` entra no MVP exclusivamente pelo cenário sintético de contingência (História
2.2, `AdaptadorCenarioSintetico`), nunca por uma resposta real do endpoint acima. A fixture
`cenario_sintetico_granizo.json` não segue o formato de leitura de estação real — é rotulada
(`"_sintetico": true`) e usa um payload próprio do cenário sintético, derivado dos valores do
conjunto demonstrativo (`semeador.py`, `evento/granizo`: intensidade `31.0`, período
`2026-03-12 14h–20h`). O `NormalizadorInmet` (T5) normaliza esta fixture para
`EventoMeteorologico(tipo=granizo)`; a proveniência final `sintetico` é atribuída pelo caminho do
cenário sintético da História 2.2, não por este adaptador.

## Amostras congeladas (`testes/fixtures/inmet/`)

| Arquivo | Descrição | Dado pessoal/sensível? |
| --- | --- | --- |
| `leitura_chuva_valida.json` | Leitura horária real (reconstrução de melhor esforço) com precipitação — normaliza para `EventoMeteorologico(tipo=chuva_intensa, proveniencia=real_inmet)` | Não — dado meteorológico público (`ADR-0013`) |
| `leitura_campo_ausente.json` | Mesma estrutura, sem o campo obrigatório `CHUVA` — deve ser rejeitada sem criar evento | Não |
| `cenario_sintetico_granizo.json` | Payload sintético do cenário de contingência (AD-013), rotulado `_sintetico` — normaliza para `EventoMeteorologico(tipo=granizo)` | Não — dado sintético |

Nenhuma amostra contém nome, endereço, identificador de segurado/apólice ou qualquer outro dado
pessoal — apenas leituras meteorológicas de estação (públicas) e um cenário sintético de
contingência.

## Resiliência da coleta (`ColetorComRetry`, História 2.2)

| Parâmetro | Valor padrão | Onde | Justificativa |
| --- | --- | --- | --- |
| Timeout por tentativa | 5s (`ClienteInmet.TIMEOUT_SEGUNDOS`) | `cliente_inmet.py` | Já fixado na História 2.1 — maior que o timeout de 3s da sonda de prontidão, pois a coleta real processa um payload maior que um simples ping de saúde |
| Número total de tentativas | 3 (`ColetorComRetry.MAXIMO_TENTATIVAS_COLETA`, em `aplicacao/coleta_meteorologica.py`) | `aplicacao/coleta_meteorologica.py` | AD-8: teto fixo evita que uma indisponibilidade momentânea trave a demonstração, sem introduzir um circuit breaker adaptativo fora do escopo do MVP |
| Backoff entre tentativas | 1s, depois 2s (`ColetorComRetry.BACKOFF_SEGUNDOS_COLETA`) | `aplicacao/coleta_meteorologica.py` | Backoff exponencial simples, suficiente para absorver uma falha de rede transitória sem alongar demais a demonstração (pior caso: 5s timeout × 3 + 1s + 2s ≈ 18s até `falhou_coleta`) |

**Comportamento observável por tipo de falha:**

- **Timeout** (`httpx.TimeoutException`, tentativa não respondeu em 5s) — tentativa registrada com `codigo_resultado = timeout`; retenta após o backoff.
- **Erro de transporte** (`httpx.TransportError`, ex. conexão recusada) — tentativa registrada com `codigo_resultado = erro_transporte`; retenta após o backoff.
- **Status HTTP de erro** (resposta recebida, `status_code != 200`) — tentativa registrada com `codigo_resultado = status_erro`; retenta após o backoff. Nunca é tratado como sucesso, mesmo que o corpo pareça válido.
- **3 tentativas esgotadas** (qualquer combinação das falhas acima) — `ColetorComRetry` levanta `RetentativasEsgotadas`; o caso de uso transiciona a execução para `falhou_coleta` e registra uma `Exceção` operacional (causa, número de tentativas, impacto), sem travar em estado intermediário.
- **Sucesso HTTP (`status_code == 200`) em qualquer tentativa** — `ColetorComRetry` devolve a resposta imediatamente, sem mais tentativas; o conteúdo, se malformado, é rejeitado pelo `NormalizadorInmet` (2.1) como um evento inválido — essa rejeição de conteúdo não é um caso de retry desta camada, nem transiciona a execução para `falhou_coleta`.

Os três parâmetros acima são constantes nomeadas no código (não variáveis de ambiente), seguindo o
mesmo precedente de `INTERVALO_SEGUNDOS_COLETA` (2.1): valores exatos, documentados e
constructor-injetáveis para teste, sem a complexidade adicional de configuração externa que nenhuma
história pediu explicitamente.
