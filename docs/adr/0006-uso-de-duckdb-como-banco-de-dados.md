# ADR 0006: Uso de DuckDB como banco de dados

- **Status:** Aceito
- **Data:** 22/08/2026

## Contexto

A prova de conceito precisa armazenar e consultar dados estruturados, como segurados, apólices, regras, eventos meteorológicos e registros das notificações simuladas. O volume esperado nesta etapa é limitado e não justifica a implantação e a administração de um servidor de banco de dados dedicado.

O time precisa de uma solução simples de configurar, fácil de distribuir com o projeto e adequada a consultas analíticas e relacionais durante as demonstrações.

## Decisão

DuckDB será utilizado como banco de dados da prova de conceito.

O banco será executado de forma embarcada no backend e persistido em arquivo local quando a persistência entre execuções for necessária. O esquema e os dados de demonstração deverão ser inicializados de maneira reproduzível por scripts ou migrações versionados no repositório.

Esta decisão se restringe à prova de conceito. Antes de um eventual uso em produção, os requisitos de concorrência, disponibilidade, segurança, operação, crescimento do volume de dados e recuperação deverão ser reavaliados.

## Consequências

### Positivas

- Não é necessário provisionar ou administrar um servidor de banco de dados separado.
- O ambiente local e as demonstrações podem ser configurados com poucas etapas.
- O banco pode ser integrado diretamente ao processo Python do backend.
- Consultas SQL facilitam a exploração e a análise dos dados da prova de conceito.

### Negativas e riscos

- O uso embarcado e baseado em arquivo não atende, por si só, a cenários de alta disponibilidade ou múltiplas instâncias de escrita.
- O arquivo do banco exige cuidados para evitar perda, corrupção ou inclusão indevida no controle de versão.
- Capacidades operacionais esperadas em um banco servidor podem demandar soluções adicionais.
- Uma futura migração para outro banco poderá exigir ajustes no esquema, nas consultas e no acesso a dados.

## Medidas de controle

- Manter esquema, dados de exemplo e inicialização do banco reproduzíveis e versionados.
- Não armazenar dados pessoais reais ou credenciais no arquivo usado pela prova de conceito.
- Encapsular o acesso a dados para reduzir o impacto de uma eventual substituição do banco.
- Definir no repositório quais arquivos de banco podem ser versionados e quais devem ser ignorados.
- Reavaliar esta decisão antes de ampliar o uso para produção ou para acesso concorrente relevante.
