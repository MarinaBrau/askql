# PRP: Evolucao de JOINs — Relacionamentos entre Tabelas

## Introducao

Os JOINs sao a maior dor de cabeca para quem tem conhecimento basico de SQL. O AskQL ja gera JOINs dentro de cada fonte (Google Ads stats + campaigns, por exemplo), mas sem metadata explicita de relacionamentos, sem validacao robusta e sem guia visual pro usuario. Alem disso, nao existe suporte para combinar dados de fontes diferentes (GA4 + Google Ads).

Este PRP cobre a evolucao completa: metadata de relacionamentos, validacao automatica de JOINs, UI para guiar o usuario, e suporte a cross-source queries.

## Goals

- Documentar explicitamente os relacionamentos entre tabelas (chaves, cardinalidade, armadilhas)
- Garantir que JOINs gerados pelo LLM sejam validados antes de serem mostrados
- Permitir que usuarios combinem dados de fontes diferentes (GA4 + Google Ads, Google Ads + Meta Ads)
- Guiar o usuario visualmente sobre quais combinacoes sao possiveis
- Funcionar para todos os niveis: marketers sem SQL, com SQL basico, e analistas

## User Stories

### US-001: Criar metadata de relacionamentos intra-source
**Descricao:** Como desenvolvedor, preciso documentar os relacionamentos entre tabelas dentro de cada fonte para que o LLM saiba exatamente quais campos conectam quais tabelas.

**Acceptance Criteria:**
- [ ] Criar `schemas/google_ads/relationships.yaml` com todos os JOINs possiveis (CampaignStats→Campaign, AdGroupStats→AdGroup, AdGroupStats→Campaign, KeywordStats→AdGroup, etc.)
- [ ] Criar `schemas/ga4_bigquery/relationships.yaml` (events→events_intraday se aplicavel)
- [ ] Criar `schemas/meta_ads/relationships.yaml` (insights_campaign→campaigns, insights_adset→campaigns, insights_ad→campaigns)
- [ ] Cada relacionamento documenta: tabela origem, tabela destino, campo de JOIN, cardinalidade (1:N, N:1), se precisa dedup, e armadilha comum
- [ ] Formato YAML validavel

### US-002: Criar metadata de relacionamentos cross-source
**Descricao:** Como desenvolvedor, preciso documentar como tabelas de fontes diferentes podem ser combinadas (GA4 + Google Ads, etc.) para suportar queries multi-fonte.

**Acceptance Criteria:**
- [ ] Criar `schemas/cross_source_relationships.yaml`
- [ ] Documentar relacao GA4 → Google Ads (via utm_campaign, gclid, date+channel)
- [ ] Documentar relacao GA4 → Meta Ads (via utm_source/medium, date+channel)
- [ ] Cada relacao documenta: confiabilidade (alta/media/baixa), pre-requisitos (UTMs configurados, etc.), conversao de tipos necessaria
- [ ] Documentar incompatibilidades (formatos de data, micros vs reais, etc.)

### US-003: Carregar relacionamentos no loader
**Descricao:** Como desenvolvedor, preciso que o `schemas/loader.py` carregue os relacionamentos e os disponibilize para o context_builder.

**Acceptance Criteria:**
- [ ] Funcao `load_relationships(source_name)` retorna lista de relacionamentos intra-source
- [ ] Funcao `load_cross_source_relationships()` retorna lista de relacionamentos cross-source
- [ ] Integrado ao dict retornado por `load_schema()` (novo campo `relationships`)
- [ ] Funciona mesmo se arquivo relationships.yaml nao existir (retorna lista vazia)

### US-004: Injetar relacionamentos no prompt do LLM
**Descricao:** Como desenvolvedor, preciso que o context_builder inclua informacoes de relacionamento no system prompt para que o LLM gere JOINs melhores.

**Acceptance Criteria:**
- [ ] Nova secao "## Table Relationships" no system prompt com: tabelas, chave de JOIN, cardinalidade, e se precisa ROW_NUMBER
- [ ] Inclui 1 exemplo correto de JOIN para cada relacionamento principal
- [ ] Para cross-source: inclui secao extra "## Cross-Source Relationships" com exemplos e caveats
- [ ] Prompt nao excede limite pratico (< 8k tokens de system prompt total)

### US-005: Suporte a multi-source no context_builder
**Descricao:** Como desenvolvedor, preciso que o `build_context` suporte receber mais de uma fonte para queries cross-source.

**Acceptance Criteria:**
- [ ] `build_context()` aceita parametro opcional `secondary_source` (nome da segunda fonte)
- [ ] Se `secondary_source` fornecido, inclui schema de ambas as fontes no prompt
- [ ] Inclui secao de cross-source relationships no prompt
- [ ] Inclui regras de alinhamento de data (YYYYMMDD vs YYYY-MM-DD) e unidades (micros vs reais)
- [ ] User prompt indica claramente que e uma query multi-fonte

### US-006: Suporte a multi-source no query_engine
**Descricao:** Como desenvolvedor, preciso que o `generate_query` aceite uma segunda fonte e passe isso pro context_builder.

**Acceptance Criteria:**
- [ ] `generate_query()` aceita parametro opcional `secondary_source` e `secondary_dataset`
- [ ] Passa parametros para `build_context()`
- [ ] QueryResult funciona normalmente (sql, explanation, is_safe)

### US-007: Validacao de JOINs — checks novos
**Descricao:** Como desenvolvedor, preciso de quality checks adicionais que validem se os JOINs gerados estao corretos.

**Acceptance Criteria:**
- [ ] Check `join_key_match`: verifica se JOIN usa campos documentados nos relationships (nao campos inventados)
- [ ] Check `join_dedup_required`: para qualquer JOIN que os relationships marcam como "precisa dedup", verifica se tem ROW_NUMBER
- [ ] Check `cross_source_date_alignment`: se query combina fontes, verifica se ha conversao de formato de data
- [ ] Check `cross_source_currency`: se query combina Google Ads + Meta Ads, verifica se custo foi normalizado (micros vs reais)
- [ ] Checks registrados em ALL_CHECKS com applies_to correto
- [ ] Checks rodam automaticamente via `run_checks()`

### US-008: Seletor de fontes na UI para cross-source
**Descricao:** Como usuario, quero poder selecionar duas fontes de dados para fazer perguntas que combinam dados de ambas.

**Acceptance Criteria:**
- [ ] Toggle ou checkbox "Combinar com outra fonte" na sidebar
- [ ] Quando ativado, mostra segundo selectbox para escolher a segunda fonte
- [ ] Mostra segundo campo de dataset para a segunda fonte
- [ ] Placeholder da pergunta muda para indicar que pode combinar (ex: "Qual a relacao entre sessoes do GA4 e gastos do Google Ads?")
- [ ] Quando desativado, comportamento identico ao atual (single source)

### US-009: Explicacao de relacionamentos na tab "O que posso perguntar?"
**Descricao:** Como usuario, quero ver na tab de capabilities quais perguntas de combinacao sao possiveis entre fontes.

**Acceptance Criteria:**
- [ ] Nova secao "Combinando fontes" no final da tab capabilities
- [ ] Mostra quais combinacoes sao possiveis (GA4 + Google Ads, GA4 + Meta Ads, etc.)
- [ ] Para cada combinacao, mostra 2-3 perguntas exemplo clicaveis
- [ ] Mostra nivel de confiabilidade da combinacao (ex: "Funciona melhor quando UTMs estao configurados")
- [ ] Botao "Perguntar →" ativa automaticamente o modo cross-source e pre-seleciona as fontes

### US-010: Templates de JOIN prontos
**Descricao:** Como usuario, quero ter templates de consultas prontas que usam JOINs, tanto intra-source quanto cross-source.

**Acceptance Criteria:**
- [ ] Adicionar 3+ templates com JOIN no `google_ads/common_queries.yaml` (ja tem alguns, adicionar mais: por ad group, por keyword com nome da campanha, por tipo de campanha)
- [ ] Adicionar 2+ templates com JOIN no `meta_ads/common_queries.yaml` (insights_campaign + campaigns para nome e objetivo)
- [ ] Adicionar 2+ templates cross-source num novo `schemas/cross_source/common_queries.yaml` (GA4 sessions vs Google Ads spend, GA4 conversions vs Meta Ads spend)
- [ ] Templates aparecem na tab "Consultas prontas" com categoria "Combinando fontes"

## Functional Requirements

- FR-1: O sistema deve documentar relacionamentos entre tabelas em formato YAML padronizado
- FR-2: O LLM deve receber informacoes de relacionamento no prompt, incluindo chaves, cardinalidade e necessidade de dedup
- FR-3: O sistema deve validar automaticamente JOINs gerados contra os relacionamentos documentados
- FR-4: O sistema deve suportar queries que combinam dados de duas fontes diferentes
- FR-5: A UI deve guiar o usuario sobre quais combinacoes sao possiveis e como usa-las
- FR-6: Templates de JOIN devem estar disponiveis para uso imediato sem digitacao
- FR-7: Todas as validacoes existentes (11 checks) devem continuar funcionando sem regressao

## Non-Goals

- Nao suportaremos JOINs entre 3+ fontes simultaneamente (apenas 2 por vez)
- Nao criaremos views materializadas no BigQuery — tudo via queries ad-hoc
- Nao faremos auto-discovery de relacionamentos — tudo documentado manualmente
- Nao suportaremos JOINs com fontes que nao estao no AskQL (ex: CRM, ERP)
- Nao faremos cache de resultados de JOIN

## Technical Considerations

- O prompt do LLM tem limite pratico. Multi-source duplica a quantidade de schema. Manter conciso.
- Cross-source requer dois datasets (possivelmente no mesmo projeto GCP, possivelmente em projetos diferentes)
- Formato de data difere entre fontes: GA4 usa `event_date` (YYYYMMDD), Google Ads usa `segments_date` (YYYY-MM-DD), Meta usa `date_start` (YYYY-MM-DD)
- Unidades monetarias diferem: Google Ads em micros (/1M), Meta Ads em reais. Normalizacao necessaria em cross-source
- ROW_NUMBER dedup e obrigatorio para config tables do Google Ads. Meta Ads campaigns table nao tem esse problema
- `build_context()` hoje aceita um unico source. Precisa ser estendido sem quebrar a interface existente

## Design Considerations

- O seletor de cross-source deve ser opt-in (toggle) para nao confundir usuarios que so querem single-source
- Explicacoes de JOIN devem ser em linguagem de marketing: "combina dados de campanhas com estatisticas" ao inves de "JOIN com deduplicacao via ROW_NUMBER"
- Na tab capabilities, a secao cross-source deve ser visualmente distinta (badge "Avancado" ou similar)

## Success Metrics

- JOINs intra-source gerados corretamente em 95%+ dos casos (validados pelos quality checks)
- Cross-source queries executam sem erro de SQL em 80%+ dos casos
- Usuario consegue gerar query cross-source em menos de 3 cliques
- Zero regressao nos 11 quality checks existentes

## Open Questions

1. O usuario pode ter GA4 e Google Ads em projetos GCP diferentes? Se sim, precisa de dois campos de project_id
2. Para cross-source, as datas devem ser alinhadas automaticamente (intersecao dos periodos) ou o usuario escolhe?
3. Devemos mostrar um aviso de "resultado experimental" para queries cross-source?
4. A tab "Consultas prontas" deve ter filtro por "Combinando fontes" como categoria?
