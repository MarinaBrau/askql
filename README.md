# AskQL -- AI SQL Assistant for Marketers

> **Fase 0: Prototipo de Validacao**

## O que e o AskQL

AskQL e uma ferramenta de IA que ajuda profissionais de marketing a escrever queries SQL para BigQuery usando linguagem natural. O usuario faz uma pergunta em portugues (ou ingles) -- como "Quais sao as 10 paginas mais acessadas?" -- e o AskQL gera uma query SQL pronta para execucao, com explicacao em linguagem acessivel.

O diferencial do AskQL e que ele nao e um wrapper generico de LLM. O sistema carrega schemas especificos de cada fonte de dados (GA4, Google Ads) e injeta **gotchas criticos** diretamente nos prompts -- armadilhas como a necessidade de `UNNEST` para `event_params`, a conversao de `cost_micros / 1.000.000`, e a deduplicacao de config tables com `ROW_NUMBER`. Isso garante que o SQL gerado seja **correto por construcao**, evitando os erros mais comuns que ate analistas experientes cometem ao trabalhar com essas fontes no BigQuery.

---

## Como Funciona

A interface e uma aplicacao Streamlit com 3 abas:

### Aba 1: Perguntar
O usuario seleciona a fonte de dados na sidebar (GA4 BigQuery Export, Google Ads ou Meta Ads), informa o Project ID e Dataset do BigQuery, e digita uma pergunta em linguagem natural. O sistema gera a query SQL com explicacao e, opcionalmente, estima o custo de processamento via dry-run no BigQuery. Botoes com perguntas de exemplo facilitam o primeiro uso.

### Aba 2: Templates
Exibe templates de queries prontas, filtradas por categoria (acquisition, engagement, ecommerce, performance, budget, keywords). Cada template mostra o titulo, a pergunta em linguagem natural, o SQL completo com placeholders substituidos, e uma explicacao detalhada. Os placeholders de data, projeto e dataset sao preenchidos automaticamente com os valores da sidebar.

### Aba 3: Explorar Schema
Navegador interativo do schema de cada fonte de dados. Mostra as gotchas (dicas criticas) no topo, seguido pela lista de tabelas com todos os campos, tipos e descricoes. Campos `STRUCT` mostram sub-campos indentados, e campos `ARRAY` indicam a necessidade de `UNNEST`.

---

## Funcionalidades

- Geracao de SQL via Claude Sonnet a partir de linguagem natural (PT-BR/EN)
- 15 templates pre-construidos (10 GA4 + 5 Google Ads)
- Schema explorer navegavel com campos, tipos e descricoes
- Validacao de seguranca (bloqueia DDL/DML: DELETE, DROP, CREATE, INSERT, etc.)
- Estimativa de custo via dry-run no BigQuery (US$ 5/TB)
- Gotchas criticos embutidos nos prompts (UNNEST, `_TABLE_SUFFIX`, `cost_micros`, deduplicacao com ROW_NUMBER, NULLIF em divisoes, etc.)
- Formatacao automatica do SQL gerado (indentacao + keywords em maiusculo)
- Suporte multilingue: responde no mesmo idioma da pergunta

---

## Quick Start

### 1. Clonar o repositorio

```bash
git clone <repo-url> askql
cd askql
```

### 2. Criar ambiente virtual e instalar dependencias

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configurar variaveis de ambiente

```bash
cp .env.example .env
```

Edite o arquivo `.env` e adicione sua API key do Claude:

```
ANTHROPIC_API_KEY=sk-ant-...
GCP_PROJECT_ID=seu-projeto-gcp  # opcional, para dry-run
```

### 4. Executar a aplicacao

```bash
streamlit run app.py
```

A aplicacao abre no navegador em `http://localhost:8501`.

---

## Arquitetura

### Estrutura de Diretorios

```
askql/
|-- app.py                          # Interface Streamlit (3 abas)
|-- requirements.txt                # Dependencias Python
|-- .env.example                    # Template de variaveis de ambiente
|
|-- core/                           # Engine de geracao de SQL
|   |-- query_engine.py             # Orquestrador do pipeline NL -> SQL
|   |-- context_builder.py          # Monta system prompt com schema + gotchas
|   |-- claude_client.py            # Wrapper da API do Claude (Anthropic)
|   |-- sql_validator.py            # Validacao de seguranca (bloqueia DDL/DML)
|   |-- bigquery_runner.py          # Estimativa de custo via dry-run
|
|-- schemas/                        # Knowledge base por fonte de dados
|   |-- loader.py                   # Carregador dinamico de schemas YAML
|   |-- ga4_bigquery/
|   |   |-- schema.yaml             # Tabelas e campos do GA4 BigQuery Export
|   |   |-- gotchas.yaml            # 8 gotchas criticos do GA4
|   |   |-- prompt_context.md       # System prompt especializado para GA4
|   |   |-- common_queries.yaml     # 10 templates de queries GA4
|   |-- google_ads/
|   |   |-- schema.yaml             # Tabelas e campos do Google Ads Transfer
|   |   |-- gotchas.yaml            # 7 gotchas criticos do Google Ads
|   |   |-- prompt_context.md       # System prompt especializado para Google Ads
|   |   |-- common_queries.yaml     # 5 templates de queries Google Ads
|   |-- meta_ads/
|       |-- schema.yaml             # Schema placeholder (em desenvolvimento)
|       |-- prompt_context.md       # Prompt context placeholder
|
|-- templates/
|   |-- template_library.py         # Gerenciamento e filtro de templates
|
|-- utils/
    |-- formatters.py               # Formatacao de SQL (sqlparse)
```

### Pipeline de Geracao de SQL

O fluxo completo desde a pergunta do usuario ate o resultado final:

```
Pergunta do usuario (linguagem natural)
         |
         v
  context_builder.py
  |- Carrega schema.yaml (tabelas e campos)
  |- Carrega gotchas.yaml (armadilhas criticas)
  |- Carrega prompt_context.md (instrucoes base)
  |- Substitui placeholders ({project_id}, {dataset})
  |- Monta system_prompt + user_prompt
         |
         v
  claude_client.py
  |- Envia system_prompt + user_prompt para Claude Sonnet
  |- Recebe resposta JSON com campos "sql" e "explanation"
  |- Faz parse do JSON (com fallback para texto puro)
         |
         v
  sql_validator.py
  |- Verifica keywords bloqueadas (DELETE, DROP, CREATE, etc.)
  |- Remove comentarios antes da verificacao
  |- Retorna (is_safe, mensagem)
         |
         v
  formatters.py
  |- Formata SQL com sqlparse (indentacao, keywords maiusculo)
         |
         v
  QueryResult (sql, explanation, is_safe, validation_message)
```

### Schema Knowledge Base

Cada fonte de dados e organizada como um diretorio dentro de `schemas/`, contendo 3-4 arquivos YAML/Markdown que formam a knowledge base:

| Arquivo | Funcao |
|---------|--------|
| `schema.yaml` | Define tabelas, campos, tipos e descricoes. Inclui sub-campos para STRUCTs e element_fields para ARRAYs |
| `gotchas.yaml` | Lista de armadilhas criticas com exemplos corretos e incorretos. Injetadas no prompt como regras numeradas |
| `prompt_context.md` | System prompt completo com regras obrigatorias, formato de resposta e exemplos. E o documento principal que guia o Claude |
| `common_queries.yaml` | Templates de queries prontas com titulo, categoria, SQL, pergunta em linguagem natural e explicacao |

### Cobertura por Fonte

| Fonte | Tabelas | Gotchas | Templates | Status |
|-------|---------|---------|-----------|--------|
| GA4 BigQuery Export | 2 (`events_*`, `events_intraday_*`) | 8 | 10 | Completo |
| Google Ads (Data Transfer) | 6 (4 Stats + 2 Config) | 7 | 5 | Completo |
| Meta Ads | 1 (placeholder) | 0 | 0 | Placeholder |

---

## Modulos

### `core/query_engine.py` -- Orquestrador

Modulo central que orquestra o pipeline completo de geracao de SQL. Recebe a pergunta do usuario e os parametros de configuracao (source, project_id, dataset), coordena as chamadas ao `context_builder`, `claude_client`, `sql_validator` e `format_sql`, e retorna um `QueryResult` com o SQL formatado, explicacao, status de seguranca e mensagem de validacao. Funciona como o ponto de entrada unico para toda geracao de queries.

### `core/context_builder.py` -- Engenharia de Prompts

Nucleo de prompt engineering do AskQL. Monta o system prompt completo que sera enviado ao Claude, combinando tres fontes de conhecimento: (1) o `prompt_context.md` com regras obrigatorias e formato de resposta, (2) o schema completo formatado como tabela Markdown, e (3) os gotchas formatados como regras numeradas com exemplos de codigo correto e incorreto. Tambem constroi o user prompt com a pergunta, configuracao (project_id, dataset, source) e instrucao de formato JSON.

### `core/claude_client.py` -- Cliente da API Claude

Wrapper da API da Anthropic que encapsula a comunicacao com o Claude Sonnet. Gerencia a inicializacao do cliente com a API key (via variavel de ambiente), envia a mensagem com system prompt e user message, e faz parse da resposta JSON. Inclui tratamento para respostas que venham envoltas em code fences Markdown e fallback para tratar a resposta inteira como SQL caso o parse JSON falhe.

### `core/sql_validator.py` -- Validacao de Seguranca

Camada de seguranca que garante que apenas queries SELECT sejam geradas. Bloqueia 10 keywords perigosas de DDL/DML: `DELETE`, `UPDATE`, `DROP`, `CREATE`, `ALTER`, `INSERT`, `MERGE`, `TRUNCATE`, `GRANT`, `REVOKE`. A verificacao e feita apos remocao de comentarios SQL (para evitar falsos positivos) e usa regex para detectar keywords no inicio de statements.

### `core/bigquery_runner.py` -- Estimativa de Custo

Modulo de estimativa de custo que executa um dry-run (sem processar dados reais) no BigQuery para calcular quantos bytes a query processaria e qual seria o custo estimado (a US$ 5/TB). Retorna um dicionario com bytes processados formatados (ex: "1.5 GB"), custo estimado formatado (ex: "US$ 0.0075"), e mensagens amigaveis para erros comuns (credenciais nao configuradas, permissao negada, projeto nao encontrado).

### `schemas/loader.py` -- Carregador Dinamico de Schemas

Carrega os arquivos YAML e Markdown de cada fonte de dados de forma dinamica. Descobre automaticamente as fontes disponiveis listando os subdiretorios de `schemas/` que contem um `schema.yaml`. Retorna um dicionario unificado com tabelas, gotchas e prompt context prontos para uso pelo `context_builder`.

### `templates/template_library.py` -- Biblioteca de Templates

Gerencia a colecao de templates de queries prontas. Carrega os templates de `common_queries.yaml` para cada fonte, oferece filtragem por categoria, e inclui busca textual por titulo, descricao ou pergunta em linguagem natural. Utiliza cache interno para evitar releitura dos arquivos YAML.

---

## Templates Disponiveis

### GA4 BigQuery Export (10 templates)

| Titulo | Categoria | Pergunta em Linguagem Natural |
|--------|-----------|-------------------------------|
| Top Sources/Mediums | acquisition | Quais sao as principais fontes de trafego do meu site? |
| Campaign Performance | acquisition | Como estao performando minhas campanhas de marketing? |
| New vs Returning Users | acquisition | Qual a proporcao de usuarios novos vs recorrentes? |
| Top Pages by Views | engagement | Quais sao as paginas mais acessadas do meu site? |
| Average Engagement Time by Page | engagement | Qual o tempo medio de engajamento por pagina? |
| Purchase Funnel | ecommerce | Como esta meu funil de conversao? (visualizacao -> carrinho -> checkout -> compra) |
| Top Products by Revenue | ecommerce | Quais sao os produtos que mais geram receita? |
| Revenue by Traffic Source | ecommerce | Qual fonte de trafego gera mais receita? |
| Users by Device Category | audience | Como meus usuarios se distribuem por tipo de dispositivo? |
| Users by Geography | audience | De quais regioes vem meus usuarios? |

### Google Ads (5 templates)

| Titulo | Categoria | Pergunta em Linguagem Natural |
|--------|-----------|-------------------------------|
| Campaign CPA | performance | Qual o CPA (custo por aquisicao) de cada campanha? |
| ROAS by Campaign | performance | Qual o ROAS de cada campanha? |
| Daily Spend Trend | budget | Como esta a tendencia de gasto diario? |
| Top Keywords by Conversions | keywords | Quais keywords geram mais conversoes? |
| Keyword CPA Analysis | keywords | Quais keywords tem o melhor e pior CPA? |

---

## Gotchas Embutidos

Os gotchas sao armadilhas criticas que o AskQL injeta diretamente nos prompts enviados ao Claude, garantindo que o SQL gerado evite os erros mais comuns dessas fontes de dados.

### GA4 BigQuery Export (8 gotchas)

| # | Titulo | Severidade |
|---|--------|------------|
| 1 | Filtro de data eficiente com `_TABLE_SUFFIX` | CRITICO |
| 2 | `event_params` e ARRAY -- requer UNNEST com subquery | CRITICO |
| 3 | `items` e ARRAY -- requer CROSS JOIN UNNEST para e-commerce | CRITICO |
| 4 | Receita: `ecommerce.purchase_revenue` vs event_param 'value' | IMPORTANTE |
| 5 | `ga_session_id` esta em `event_params`, nao e campo direto | CRITICO |
| 6 | Sessao unica = `user_pseudo_id` + `ga_session_id` | IMPORTANTE |
| 7 | Sintaxe correta de `_TABLE_SUFFIX` com wildcard tables | CRITICO |
| 8 | `event_params` values tem multiplos tipos -- usar o tipo correto | IMPORTANTE |

### Google Ads (7 gotchas)

| # | Titulo | Severidade |
|---|--------|------------|
| 1 | `cost_micros` deve ser dividido por 1.000.000 | CRITICO |
| 2 | Usar `_TABLE_SUFFIX` para filtrar datas nas tabelas wildcard | CRITICO |
| 3 | `segments_date` e o campo de data do registro (YYYY-MM-DD) | IMPORTANTE |
| 4 | CPA: usar NULLIF para evitar divisao por zero | CRITICO |
| 5 | ROAS: usar NULLIF no denominador (custo) | CRITICO |
| 6 | JOIN stats com config tables usando `campaign_id` / `ad_group_id` | IMPORTANTE |
| 7 | Config tables tem multiplos `_DATA_DATE` -- deduplicar com ROW_NUMBER | CRITICO |

---

## Stack Tecnica

| Componente | Tecnologia | Versao |
|------------|-----------|--------|
| Linguagem | Python | 3.11+ |
| Interface Web | Streamlit | 1.41.1 |
| IA / LLM | Claude Sonnet (Anthropic SDK) | anthropic 0.49.0 |
| BigQuery (dry-run) | google-cloud-bigquery | 3.27.0 |
| Schemas | PyYAML | 6.0.2 |
| Formatacao SQL | sqlparse | 0.5.3 |
| Variaveis de ambiente | python-dotenv | 1.0.1 |

---

## Configuracao

### Variaveis de Ambiente

Crie um arquivo `.env` na raiz do projeto (use `.env.example` como base):

```bash
# Obrigatorio: API key do Claude (Anthropic)
ANTHROPIC_API_KEY=sk-ant-...

# Opcional: projeto GCP para dry-run de custo
GCP_PROJECT_ID=seu-projeto-gcp
```

A `ANTHROPIC_API_KEY` e obrigatoria para o funcionamento da geracao de SQL. Sem ela, o sistema exibe uma mensagem de erro orientando a configuracao.

### BigQuery Dry-Run (opcional)

Para habilitar a estimativa de custo de queries no BigQuery:

1. Instale e configure o Google Cloud SDK:
   ```bash
   gcloud auth application-default login
   ```

2. Ou defina a variavel de ambiente apontando para uma Service Account:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS=/caminho/para/sa-key.json
   ```

3. Na interface do AskQL, ative o toggle "Estimar custo no BigQuery" na sidebar.

O dry-run **nunca executa a query** -- apenas calcula os bytes que seriam processados e estima o custo a US$ 5/TB (precificacao on-demand do BigQuery).

---

## Limitacoes (Fase 0)

- **Nao executa queries no BigQuery** -- apenas gera SQL + dry-run para estimativa de custo
- **Meta Ads e apenas placeholder** -- schema minimo sem gotchas ou templates
- **Sem historico de queries** -- cada sessao e independente; queries geradas nao sao persistidas
- **Sem autenticacao de usuarios** -- qualquer pessoa com acesso a URL pode usar
- **Deploy local apenas** -- sem infraestrutura de deploy em nuvem configurada
- **Sem feedback loop** -- nao ha mecanismo para o usuario avaliar a qualidade do SQL gerado
- **Sem cache de respostas** -- cada pergunta gera uma nova chamada a API do Claude

---

## Proximos Passos

- [ ] Meta Ads schema completo (tabelas, gotchas, templates)
- [ ] Deploy em Streamlit Cloud ou Cloud Run
- [ ] Historico de queries por sessao/usuario
- [ ] Suporte a mais fontes (Facebook Ads completo, TikTok Ads)
- [ ] Fine-tuning de prompts baseado em feedback dos usuarios
- [ ] Cache de respostas para perguntas similares
- [ ] Execucao real de queries no BigQuery (com controle de custo)
- [ ] Autenticacao de usuarios (OAuth / API key)
- [ ] Testes automatizados de qualidade do SQL gerado

---

## Licenca

Todos os direitos reservados.
