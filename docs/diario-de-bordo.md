# Diario de Bordo — AskQL Fase 0

## 2026-02-15 — Dia 1: Concepcao e Implementacao Completa

### Contexto
Projeto para validar a ideia de um AI SQL Assistant para marketers.
O objetivo e permitir que profissionais de marketing gerem queries BigQuery usando linguagem natural,
sem precisar saber SQL.

### Decisoes Tomadas

| Decisao | Escolha | Motivo |
|---|---|---|
| Meta Ads | Placeholder apenas | Focar nas sources que ja dominamos (GA4 + Google Ads) |
| Execucao BigQuery | Dry-run apenas (estimar custo) | Evitar riscos de custo acidental no prototipo |
| Idioma UI | PT-BR | Foco no mercado brasileiro |
| Templates | 10 GA4 + 5 Google Ads | Volume suficiente para validar sem gastar tempo demais |
| Deploy | Local only | Prototipo rapido, sem overhead de infra |
| LLM | Claude Sonnet | Melhor custo-beneficio para geracao de SQL |

### O que foi construido

**Feature 1 — Schema Knowledge Base**
- Schema completo do GA4 BigQuery Export (events_*, events_intraday_*)
- Schema completo do Google Ads Data Transfer (6 tabelas: CampaignStats, AdGroupStats, AdStats, KeywordStats, Campaign, AdGroup)
- Schema placeholder do Meta Ads (1 tabela basica)
- 8 gotchas criticos do GA4 (UNNEST, _TABLE_SUFFIX, ga_session_id, revenue, etc.)
- 7 gotchas criticos do Google Ads (cost_micros, NULLIF, ROW_NUMBER dedup, etc.)
- Prompt context otimizado para cada source (GA4: 26k chars, Google Ads: 20k chars)
- Schema loader dinamico que carrega qualquer source

**Feature 2 — Core Engine**
- Claude client wrapper (Sonnet, JSON response parsing)
- SQL validator (bloqueia 10 keywords DDL/DML, ignora comentarios)
- Context builder (monta system prompt de ~26k chars com schema + gotchas + regras)
- BigQuery dry-run (estima bytes processados e custo em USD)
- Query engine orquestrador (pergunta → context → Claude → validacao → formatacao)

**Feature 3 — Template Library**
- 10 templates GA4: Acquisition (3), Engagement (2), E-commerce (3), Audience (2)
- 5 templates Google Ads: Performance (2), Budget (1), Keywords (2)
- Template library com filtro por categoria e busca por texto

**Feature 4 — Streamlit UI**
- Sidebar: seletor de source, project_id, dataset, toggle dry-run
- Tab "Perguntar": input de pergunta, exemplos clicaveis, geracao com spinner, SQL + explicacao
- Tab "Templates": filtro por categoria, expanders, placeholders editaveis
- Tab "Explorar Schema": tabelas expandiveis com campos e tipos, gotchas como avisos

### Testes Realizados

1. **GA4 — "Quais sao as 10 paginas mais acessadas?"**
   - SQL gerado corretamente com UNNEST para event_params
   - _TABLE_SUFFIX usado para filtro de data
   - CONCAT(user_pseudo_id + ga_session_id) para sessoes unicas
   - Explicacao em PT-BR, linguagem de marketing

2. **Google Ads — "Qual o CPA e ROAS de cada campanha?"**
   - cost_micros / 1000000.0 aplicado
   - ROW_NUMBER para deduplicar ads_Campaign antes do JOIN
   - NULLIF no CPA e ROAS
   - Explicacao clara sobre interpretacao de metricas

### Numeros

| Metrica | Valor |
|---|---|
| Arquivos criados | 25 |
| Schemas | 3 sources (GA4, Google Ads, Meta Ads) |
| Gotchas documentados | 15 (8 GA4 + 7 Google Ads) |
| Templates | 15 (10 GA4 + 5 Google Ads) |
| System prompt GA4 | ~26.000 caracteres |
| System prompt Google Ads | ~20.000 caracteres |
| Tempo de implementacao | ~1 sessao |

### Problemas Encontrados
- API key Anthropic sem creditos inicialmente — resolvido adicionando creditos no console
- dotenv nao carrega automaticamente fora do Streamlit — resolvido com export manual para testes CLI

### Proximos Passos
- [ ] Trocar API key (foi exposta em chat)
- [ ] Testar com perguntas mais complexas e edge cases
- [ ] Meta Ads schema completo quando tiver dados
- [ ] Deploy para compartilhar com clientes
- [ ] Historico de queries
- [ ] Cloud Scheduler para atualizacao automatica

---

## 2026-02-17 — Nivel 1: Quick Wins de Resiliencia

### Contexto
App funcional como prototipo mas sem resiliencia basica. Implementadas 4 melhorias sem mudar funcionalidade.

### O que foi feito

| Mudanca | Arquivo | Detalhe |
|---|---|---|
| Timeout + retry Claude API | `core/claude_client.py` | `timeout=120.0`, retry 1x para erros transientes (`APIConnectionError`, `APITimeoutError`, `InternalServerError`) com log |
| Cache de schemas | `schemas/loader.py` | `functools.lru_cache` em 4 funcoes — elimina releitura de YAMLs a cada query |
| Validacao startup | `app.py` | `_validate_config()` checa `ANTHROPIC_API_KEY` com `st.error()+st.stop()` imediato |
| Cache TemplateLibrary | `app.py` | `@st.cache_resource` via `_get_template_library()` — instancia unica |
| Erros BQ pt-BR | `core/bigquery_runner.py` | `_translate_bq_error()` centralizada — 7 padroes traduzidos |
| Limpeza cache testes | `tests/conftest.py` | `autouse` fixture limpa `lru_cache` entre testes |

### Numeros

| Metrica | Valor |
|---|---|
| Arquivos modificados | 5 |
| Linhas adicionadas | 99 |
| Linhas removidas | 41 |
| Testes passando | 174 (zero regressao) |
| Commit | `0bba3e9` |

---

## 2026-02-18 — VTEX, Shopify, Cross-Source completo e Testes Abrangentes

### Contexto
App ja com GA4, Google Ads, Meta Ads funcionando. Objetivo desta sessao: adicionar VTEX e Shopify como fontes, completar todos os pares cross-source possiveis, e rodar uma bateria completa de testes.

### O que foi feito

#### 1. VTEX como nova fonte
- 5 arquivos criados em `schemas/vtex/`: schema.yaml (5 tabelas), relationships.yaml, gotchas.yaml, common_queries.yaml, prompt_context.md
- Tabelas: orders_treated, order_items_treated, catalog_treated, categories_treated, coupons_treated
- Dataset: `vtex_treated`, particao por coluna `dt` (DATE)
- Gotchas criticos: precos JA em BRL (nao /100), `applied_promotions` e STRING JSON (JSON_EXTRACT_ARRAY + UNNEST), `status = 'invoiced'` para receita

#### 2. Shopify como nova fonte
- 5 arquivos criados em `schemas/shopify/`: idem
- Tabelas: orders_treated, order_items_treated, products_treated, customers_treated
- Dataset: `shopify_treated`, particao por coluna `dt` (DATE)
- Gotchas criticos: `financial_status = 'paid'`, campos derivados prontos (is_on_sale, stock_level, customer_segment, frequency_segment), PII ja mascarado

#### 3. Cross-source completo (todos os 10 pares)
C(5,2) = 10 combinacoes, todas implementadas em `schemas/cross_source/relationships.yaml`:
- Pares existentes: GA4↔GAds, GA4↔Meta, GAds↔Meta
- Novos pares: VTEX↔GAds, VTEX↔Meta, Shopify↔GAds, Shopify↔Meta, GA4↔VTEX, GA4↔Shopify, VTEX↔Shopify
- Estrategias: date-based (alta confianca) e UTM-based (media confianca)

#### 4. Fix sql_validator.py
- **Bug:** regex anterior so detectava DDL/DML no inicio de statement (`^` ou apos `;`)
- **Fix:** `_strip_sql()` remove comentarios E string literals antes de checar; pattern `\bKEYWORD\b` pega em qualquer posicao
- Evita falso positivo: `WHERE status = 'DELETED'` nao dispara; `DELETED` != `DELETE` (word boundary)

#### 5. Suite de testes abrangentes (validation/)
- `validation/test_questions_extended.py`: 31 perguntas (VTEX x6, Shopify x6, edge cases x10, security x9)
- `validation/comprehensive_test.py`: runner com report detalhado em Markdown
- `validation/utils.py`: `call_with_retry()` com backoff exponencial para rate limiting (429)

#### 6. Quality checks para VTEX e Shopify
- VTEX: vtex_dt_filter, vtex_prices_not_divided, vtex_invoiced_status
- Shopify: shopify_dt_filter, shopify_financial_status
- VTEX/Shopify passam de 0/0 checks para 3/3 e 2/2 respectivamente

### Numeros finais

| Metrica | Antes | Depois |
|---|---|---|
| Fontes | 3 | 5 |
| Pares cross-source | 3 | 10 |
| Quality checks | 15 | 20 |
| pytest testes | 174 | 207 |
| Test questions (API real) | 31 | 62 |
| Pass rate (API real) | 93.5% | 93.5% |
| Quality check pass rate | 99.4% | 99.3% |

### Commits
| Hash | Descricao |
|---|---|
| `f3cfe36` | Quality checks VTEX/Shopify + retry + expectativas corrigidas |
| `9febf89` | Fix sql_validator: detectar DDL/DML em qualquer posicao |
| `24fec21` | VTEX + Shopify + cross-source completo (10 pares) |

### Decisoes tecnicas
- **VTEX ↔ Shopify:** join mais simples de todos — ambos usam `dt` DATE em YYYY-MM-DD e precos em BRL, zero conversao necessaria
- **Retry backoff:** 60s → 120s → 240s em erros 429; nao faz retry em credito insuficiente (402)
- **Expectativas de seguranca:** sec_drop_01 e sec_update_01 com `expect_safe: True` — Claude retornar SELECT com explicacao e mais util do que simplesmente bloquear
