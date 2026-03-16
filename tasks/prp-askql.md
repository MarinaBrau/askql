# PRP: AskQL — AI SQL Assistant for Marketers (Fase 0)

## Introduction

AskQL e um assistente AI que permite marketers gerarem queries SQL para BigQuery usando linguagem natural. O diferencial e o conhecimento profundo de schemas especificos de marketing (GA4 BigQuery exports, Google Ads Data Transfer) embutido nos prompts, gerando SQL otimizado com explicacoes em linguagem simples.

Esta Fase 0 e um prototipo de validacao: um Streamlit app local para testar internamente antes de investir em um SaaS completo.

## Goals

- Gerar SQL BigQuery correto a partir de perguntas em linguagem natural (PT-BR ou EN)
- Cobrir schemas GA4 BigQuery Export e Google Ads Data Transfer com gotchas criticos
- Oferecer 15 templates pre-construidos (10 GA4 + 5 Google Ads) para acelerar o uso
- Validar SQL gerado (bloquear DDL/DML) e estimar custo via dry-run no BigQuery
- UI funcional em PT-BR para demonstracao a clientes

## Decisoes (Fase 0)

| Decisao | Escolha |
|---|---|
| Meta Ads | Placeholder apenas (estrutura sem conteudo real) |
| Execucao BigQuery | Dry-run para estimar custo (sem exibir resultados) |
| Idioma UI | PT-BR |
| Templates | 10 GA4 + 5 Google Ads |
| Deploy | Local only (`streamlit run app.py`) |

---

## User Stories

### US-001: Scaffolding do projeto e dependencias
**Descricao:** Como desenvolvedor, preciso da estrutura de diretorios, requirements.txt e .env.example para iniciar o desenvolvimento.

**Acceptance Criteria:**
- [ ] Estrutura de diretorios criada conforme arquitetura definida (core/, schemas/, templates/, utils/)
- [ ] `requirements.txt` com: streamlit, anthropic, google-cloud-bigquery, pyyaml, sqlparse
- [ ] `.env.example` com ANTHROPIC_API_KEY e GCP_PROJECT_ID (opcional)
- [ ] Todos os `__init__.py` criados
- [ ] `python -c "import yaml, sqlparse, anthropic, streamlit"` executa sem erro

### US-002: Schema GA4 BigQuery Export
**Descricao:** Como sistema, preciso do schema completo do GA4 BigQuery Export com gotchas e prompt context para gerar SQL correto.

**Acceptance Criteria:**
- [ ] `schemas/ga4_bigquery/schema.yaml` com todas as tabelas e campos (events_*, user_pseudo_id, event_params, items, device, geo, traffic_source, ecommerce, etc.)
- [ ] `schemas/ga4_bigquery/gotchas.yaml` com os 7+ gotchas criticos (UNNEST, _TABLE_SUFFIX, ga_session_id, cost, etc.)
- [ ] `schemas/ga4_bigquery/prompt_context.md` com system prompt otimizado para Claude gerar SQL GA4
- [ ] Schema loader consegue carregar todos os arquivos sem erro
- [ ] Typecheck passes

### US-003: Schema Google Ads Data Transfer
**Descricao:** Como sistema, preciso do schema do Google Ads BigQuery Transfer com gotchas para gerar SQL correto.

**Acceptance Criteria:**
- [ ] `schemas/google_ads/schema.yaml` com tabelas principais (CampaignStats, AdGroupStats, AdStats, KeywordStats, Campaign, AdGroup)
- [ ] `schemas/google_ads/gotchas.yaml` com gotchas (cost_micros, _TABLE_SUFFIX, segments_date, CPA, ROAS)
- [ ] `schemas/google_ads/prompt_context.md` com system prompt para Claude
- [ ] Schema loader consegue carregar sem erro
- [ ] Typecheck passes

### US-004: Schema Meta Ads (placeholder) + Schema Loader
**Descricao:** Como sistema, preciso do placeholder de Meta Ads e do loader que carrega qualquer schema.

**Acceptance Criteria:**
- [ ] `schemas/meta_ads/schema.yaml` com estrutura basica (tabelas placeholder, campos TBD)
- [ ] `schemas/meta_ads/prompt_context.md` com nota "Schema em desenvolvimento"
- [ ] `schemas/loader.py` carrega schema.yaml, gotchas.yaml, prompt_context.md de qualquer source
- [ ] Loader retorna dict estruturado com tabelas, campos, gotchas e prompt context
- [ ] Loader levanta erro claro se source nao existe
- [ ] Typecheck passes

### US-005: Claude client + SQL validator + formatters
**Descricao:** Como sistema, preciso dos modulos utilitarios: wrapper Claude API, validador SQL e formatador.

**Acceptance Criteria:**
- [ ] `core/claude_client.py`: wrapper que recebe system prompt + user message, retorna resposta do Claude Sonnet
- [ ] `core/claude_client.py`: usa ANTHROPIC_API_KEY de env var, levanta erro claro se nao configurada
- [ ] `core/sql_validator.py`: bloqueia queries com DELETE, UPDATE, DROP, CREATE, ALTER, INSERT, MERGE, TRUNCATE (case-insensitive)
- [ ] `core/sql_validator.py`: retorna (is_safe: bool, reason: str)
- [ ] `utils/formatters.py`: formata SQL com sqlparse (indent, uppercase keywords)
- [ ] Typecheck passes

### US-006: Context builder (prompt engineering)
**Descricao:** Como sistema, preciso do modulo que monta o prompt contextualizado com schema + gotchas + pergunta do usuario.

**Acceptance Criteria:**
- [ ] `core/context_builder.py`: recebe source_name, project_id, dataset, pergunta do usuario
- [ ] Monta system prompt com: dialeto BigQuery, schema completo, gotchas como regras, instrucoes para nao inventar campos, incluir comentarios, otimizar com _TABLE_SUFFIX
- [ ] Monta user prompt separado com a pergunta + project_id + dataset para referencias corretas
- [ ] System prompt instrui Claude a retornar JSON com campos `sql` e `explanation`
- [ ] Explanation deve usar linguagem de marketing, 3-5 frases, mencionar custo se relevante
- [ ] Typecheck passes

### US-007: BigQuery dry-run
**Descricao:** Como usuario, quero ver uma estimativa de custo antes de rodar a query no BigQuery.

**Acceptance Criteria:**
- [ ] `core/bigquery_runner.py`: recebe SQL, executa dry-run no BigQuery
- [ ] Retorna bytes estimados e custo aproximado em USD ($5/TB)
- [ ] Funciona com credenciais GCP do ambiente (Application Default Credentials)
- [ ] Retorna erro amigavel se credenciais nao configuradas
- [ ] Nunca executa a query de verdade (apenas dry_run=True)
- [ ] Typecheck passes

### US-008: Query engine (orquestrador)
**Descricao:** Como sistema, preciso do pipeline completo: pergunta → context → Claude → validacao → resultado.

**Acceptance Criteria:**
- [ ] `core/query_engine.py`: recebe source_name, project_id, dataset, pergunta
- [ ] Chama context_builder para montar prompt
- [ ] Chama claude_client para gerar SQL + explicacao
- [ ] Chama sql_validator para validar SQL gerado
- [ ] Se SQL inseguro, retorna erro com motivo
- [ ] Retorna dataclass/dict com: sql, explanation, is_safe, validation_message
- [ ] Typecheck passes

### US-009: Templates GA4 (10 templates)
**Descricao:** Como usuario marketer, quero templates prontos de GA4 para resolver perguntas comuns sem precisar digitar.

**Acceptance Criteria:**
- [ ] `schemas/ga4_bigquery/common_queries.yaml` com 10 templates
- [ ] Categorias cobertas: Acquisition (3), Engagement (2), E-commerce (3), Audience (2)
- [ ] Cada template tem: title, category, description, natural_language, sql (com placeholders {project_id}, {dataset}, {date_start}, {date_end}), explanation
- [ ] SQL dos templates usa gotchas corretos (UNNEST, _TABLE_SUFFIX, etc.)
- [ ] YAML carrega sem erro

### US-010: Templates Google Ads (5 templates) + Template Library
**Descricao:** Como usuario, quero templates de Google Ads e um gerenciador que carrega e filtra templates.

**Acceptance Criteria:**
- [ ] `schemas/google_ads/common_queries.yaml` com 5 templates
- [ ] Categorias: Performance (2), Budget (1), Keywords (2)
- [ ] Cada template segue mesmo formato do GA4
- [ ] `templates/template_library.py`: carrega templates de qualquer source, filtra por categoria, busca por texto
- [ ] Retorna lista de templates com metadados para exibicao
- [ ] Typecheck passes

### US-011: Streamlit — Sidebar + Tab "Perguntar"
**Descricao:** Como usuario, quero abrir o app, selecionar minha source, fazer uma pergunta e receber SQL + explicacao.

**Acceptance Criteria:**
- [ ] Sidebar com: seletor de source (GA4, Google Ads, Meta Ads), campos project_id e dataset, toggle "Estimar custo no BigQuery"
- [ ] Tab "Perguntar" com text area grande e placeholder contextual
- [ ] 3-4 exemplos de perguntas clicaveis que mudam conforme source selecionada
- [ ] Botao "Gerar Query" chama query_engine e exibe resultado
- [ ] SQL exibido com syntax highlighting (st.code) + botao copiar
- [ ] Explicacao exibida em st.info ou card estilizado
- [ ] Se toggle BQ ativo: mostra estimativa de custo via dry-run
- [ ] Se SQL inseguro: mostra alerta com motivo
- [ ] Spinner durante geracao
- [ ] `streamlit run app.py` executa sem erro

### US-012: Streamlit — Tab "Templates"
**Descricao:** Como usuario, quero navegar templates pre-construidos, filtrar por categoria e usar um template como ponto de partida.

**Acceptance Criteria:**
- [ ] Tab "Templates" com filtro de categoria (dropdown ou radio buttons)
- [ ] Cards/expanders mostrando cada template: titulo, descricao, pergunta natural
- [ ] Ao expandir: mostra SQL completo com syntax highlighting + explicacao
- [ ] Campos para preencher placeholders (project_id, dataset, date_start, date_end)
- [ ] SQL atualiza em tempo real conforme placeholders preenchidos
- [ ] Botao copiar SQL
- [ ] Templates mudam conforme source selecionada na sidebar
- [ ] `streamlit run app.py` executa sem erro

### US-013: Streamlit — Tab "Explorar Schema"
**Descricao:** Como usuario, quero visualizar a estrutura do schema da source selecionada para entender meus dados.

**Acceptance Criteria:**
- [ ] Tab "Explorar Schema" mostra tabelas da source selecionada
- [ ] Cada tabela expandivel mostra campos com tipos
- [ ] Campos STRUCT e ARRAY mostram sub-campos
- [ ] Gotchas da source exibidos como dicas/avisos
- [ ] Schema muda conforme source selecionada na sidebar
- [ ] `streamlit run app.py` executa sem erro

---

## Functional Requirements

- FR-1: O sistema deve aceitar perguntas em PT-BR e ingles e gerar SQL BigQuery Standard valido
- FR-2: O sistema deve incluir schema completo + gotchas no prompt para cada source
- FR-3: O sistema deve NUNCA gerar SQL com DDL/DML (DELETE, DROP, CREATE, UPDATE, INSERT, ALTER, MERGE, TRUNCATE)
- FR-4: O sistema deve retornar SQL formatado + explicacao em linguagem de marketing
- FR-5: O sistema deve suportar dry-run no BigQuery para estimar custo (bytes processados + USD)
- FR-6: O sistema deve oferecer 15 templates pre-construidos (10 GA4 + 5 Google Ads)
- FR-7: O sistema deve permitir navegacao do schema de cada source
- FR-8: O SQL gerado deve usar placeholders {project_id} e {dataset} substituidos pelo input do usuario
- FR-9: A API key do Claude deve ser carregada via .env, nunca hardcoded

## Non-Goals (Out of Scope — Fase 0)

- Execucao real de queries no BigQuery (apenas dry-run)
- Exibicao de resultados de queries
- Autenticacao de usuarios / multi-tenancy
- Schema do Meta Ads completo (apenas placeholder)
- Deploy em cloud (Streamlit Cloud, Cloud Run, etc.)
- Historico de queries / conversas
- Fine-tuning de modelos
- Suporte a outros bancos (Snowflake, Redshift, etc.)
- Edicao de SQL pelo usuario com re-validacao
- Internacionalizacao (apenas PT-BR nesta fase)

## Technical Considerations

- **LLM:** Claude Sonnet via anthropic SDK Python — model_id `claude-sonnet-4-5-20250929`
- **Prompt engineering:** System prompt com schema + gotchas como regras; response em JSON {sql, explanation}
- **Schema storage:** Arquivos YAML carregados em runtime (sem banco de dados)
- **BigQuery:** google-cloud-bigquery SDK com dry_run=True; Application Default Credentials
- **SQL formatting:** sqlparse para indent e uppercase de keywords
- **Streamlit:** Tabs para organizar, st.code para SQL, session_state para manter contexto entre interacoes

## Success Metrics

- SQL gerado para GA4 usa UNNEST corretamente em 100% dos casos que envolvem event_params
- SQL gerado para Google Ads converte cost_micros em 100% dos casos
- Validador bloqueia 100% das tentativas de DDL/DML
- Templates carregam e renderizam sem erro
- App Streamlit inicia e todas as 3 tabs funcionam sem crash
- Dry-run retorna estimativa de custo quando credenciais GCP configuradas

## Open Questions

- Qual model_id exato do Claude usar? (Sonnet mais recente: `claude-sonnet-4-5-20250929`)
- Limitar tamanho da resposta do Claude para controlar custo?
- Adicionar rate limiting no cliente para evitar gastos acidentais?
- Qual formato de data usar nos templates? (YYYYMMDD como _TABLE_SUFFIX ou YYYY-MM-DD para UX?)
