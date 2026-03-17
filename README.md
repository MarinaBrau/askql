# AskQL — AI SQL Assistant for Marketers

> **Phase 0: Validation Prototype**

## What is AskQL

AskQL is an AI tool that helps marketing professionals write SQL queries for BigQuery using natural language. The user asks a question like "What are the top 10 most visited pages?" and AskQL generates a ready-to-run SQL query with an accessible explanation.

What sets AskQL apart is that it's not a generic LLM wrapper. The system loads source-specific schemas (GA4, Google Ads) and injects **critical gotchas** directly into the prompts — pitfalls like the need for `UNNEST` on `event_params`, converting `cost_micros / 1,000,000`, and deduplicating config tables with `ROW_NUMBER`. This ensures the generated SQL is **correct by construction**, avoiding the most common mistakes even experienced analysts make when working with these sources in BigQuery.

---

## How It Works

The interface is a Streamlit application with 3 tabs:

### Tab 1: Ask
The user selects a data source in the sidebar (GA4 BigQuery Export, Google Ads, or Meta Ads), enters the BigQuery Project ID and Dataset, and types a natural language question. The system generates the SQL query with an explanation and optionally estimates processing cost via a BigQuery dry-run. Example question buttons facilitate first use.

### Tab 2: Templates
Displays ready-made query templates filtered by category (acquisition, engagement, ecommerce, performance, budget, keywords). Each template shows the title, natural language question, full SQL with substituted placeholders, and a detailed explanation. Date, project, and dataset placeholders are automatically filled from sidebar values.

### Tab 3: Explore Schema
Interactive schema browser for each data source. Shows gotchas (critical tips) at the top, followed by the list of tables with all fields, types, and descriptions. `STRUCT` fields display indented sub-fields, and `ARRAY` fields indicate the need for `UNNEST`.

---

## Features

- SQL generation via Claude Sonnet from natural language (PT-BR/EN)
- 15 pre-built templates (10 GA4 + 5 Google Ads)
- Browsable schema explorer with fields, types, and descriptions
- Security validation (blocks DDL/DML: DELETE, DROP, CREATE, INSERT, etc.)
- Cost estimation via BigQuery dry-run (US$ 5/TB)
- Critical gotchas embedded in prompts (UNNEST, `_TABLE_SUFFIX`, `cost_micros`, ROW_NUMBER deduplication, NULLIF for divisions, etc.)
- Automatic SQL formatting (indentation + uppercase keywords)
- Multilingual support: responds in the same language as the question

---

## Quick Start

### 1. Clone the repository

```bash
git clone <repo-url> askql
cd askql
```

### 2. Create virtual environment and install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit the `.env` file and add your Claude API key:

```
ANTHROPIC_API_KEY=sk-ant-...
GCP_PROJECT_ID=your-gcp-project  # optional, for dry-run
```

### 4. Run the application

```bash
streamlit run app.py
```

The application opens in the browser at `http://localhost:8501`.

---

## Architecture

### Directory Structure

```
askql/
|-- app.py                          # Streamlit interface (3 tabs)
|-- requirements.txt                # Python dependencies
|-- .env.example                    # Environment variables template
|
|-- core/                           # SQL generation engine
|   |-- query_engine.py             # Pipeline orchestrator NL -> SQL
|   |-- context_builder.py          # Builds system prompt with schema + gotchas
|   |-- claude_client.py            # Claude API wrapper (Anthropic)
|   |-- sql_validator.py            # Security validation (blocks DDL/DML)
|   |-- bigquery_runner.py          # Cost estimation via dry-run
|
|-- schemas/                        # Knowledge base per data source
|   |-- loader.py                   # Dynamic YAML schema loader
|   |-- ga4_bigquery/
|   |   |-- schema.yaml             # GA4 BigQuery Export tables and fields
|   |   |-- gotchas.yaml            # 8 critical GA4 gotchas
|   |   |-- prompt_context.md       # Specialized system prompt for GA4
|   |   |-- common_queries.yaml     # 10 GA4 query templates
|   |-- google_ads/
|   |   |-- schema.yaml             # Google Ads Transfer tables and fields
|   |   |-- gotchas.yaml            # 7 critical Google Ads gotchas
|   |   |-- prompt_context.md       # Specialized system prompt for Google Ads
|   |   |-- common_queries.yaml     # 5 Google Ads query templates
|   |-- meta_ads/
|       |-- schema.yaml             # Placeholder schema (in development)
|       |-- prompt_context.md       # Placeholder prompt context
|
|-- templates/
|   |-- template_library.py         # Template management and filtering
|
|-- utils/
    |-- formatters.py               # SQL formatting (sqlparse)
```

### SQL Generation Pipeline

Complete flow from user question to final result:

```
User question (natural language)
         |
         v
  context_builder.py
  |- Loads schema.yaml (tables and fields)
  |- Loads gotchas.yaml (critical pitfalls)
  |- Loads prompt_context.md (base instructions)
  |- Substitutes placeholders ({project_id}, {dataset})
  |- Builds system_prompt + user_prompt
         |
         v
  claude_client.py
  |- Sends system_prompt + user_prompt to Claude Sonnet
  |- Receives JSON response with "sql" and "explanation" fields
  |- Parses JSON (with fallback for plain text)
         |
         v
  sql_validator.py
  |- Checks for blocked keywords (DELETE, DROP, CREATE, etc.)
  |- Strips comments before checking
  |- Returns (is_safe, message)
         |
         v
  formatters.py
  |- Formats SQL with sqlparse (indentation, uppercase keywords)
         |
         v
  QueryResult (sql, explanation, is_safe, validation_message)
```

### Schema Knowledge Base

Each data source is organized as a directory inside `schemas/`, containing 3-4 YAML/Markdown files that form the knowledge base:

| File | Purpose |
|------|---------|
| `schema.yaml` | Defines tables, fields, types, and descriptions. Includes sub-fields for STRUCTs and element_fields for ARRAYs |
| `gotchas.yaml` | List of critical pitfalls with correct and incorrect examples. Injected into the prompt as numbered rules |
| `prompt_context.md` | Complete system prompt with mandatory rules, response format, and examples. The main document guiding Claude |
| `common_queries.yaml` | Ready-made query templates with title, category, SQL, natural language question, and explanation |

### Coverage by Source

| Source | Tables | Gotchas | Templates | Status |
|--------|--------|---------|-----------|--------|
| GA4 BigQuery Export | 2 (`events_*`, `events_intraday_*`) | 8 | 10 | Complete |
| Google Ads (Data Transfer) | 6 (4 Stats + 2 Config) | 7 | 5 | Complete |
| Meta Ads | 1 (placeholder) | 0 | 0 | Placeholder |

---

## Available Templates

### GA4 BigQuery Export (10 templates)

| Title | Category | Natural Language Question |
|-------|----------|--------------------------|
| Top Sources/Mediums | acquisition | What are the main traffic sources for my site? |
| Campaign Performance | acquisition | How are my marketing campaigns performing? |
| New vs Returning Users | acquisition | What's the ratio of new vs returning users? |
| Top Pages by Views | engagement | What are the most visited pages on my site? |
| Average Engagement Time by Page | engagement | What's the average engagement time per page? |
| Purchase Funnel | ecommerce | How is my conversion funnel? (view -> cart -> checkout -> purchase) |
| Top Products by Revenue | ecommerce | Which products generate the most revenue? |
| Revenue by Traffic Source | ecommerce | Which traffic source generates the most revenue? |
| Users by Device Category | audience | How are my users distributed by device type? |
| Users by Geography | audience | Where do my users come from? |

### Google Ads (5 templates)

| Title | Category | Natural Language Question |
|-------|----------|--------------------------|
| Campaign CPA | performance | What's the CPA (cost per acquisition) for each campaign? |
| ROAS by Campaign | performance | What's the ROAS for each campaign? |
| Daily Spend Trend | budget | What's the daily spend trend? |
| Top Keywords by Conversions | keywords | Which keywords generate the most conversions? |
| Keyword CPA Analysis | keywords | Which keywords have the best and worst CPA? |

---

## Embedded Gotchas

Gotchas are critical pitfalls that AskQL injects directly into the prompts sent to Claude, ensuring the generated SQL avoids the most common errors for each data source.

### GA4 BigQuery Export (8 gotchas)

| # | Title | Severity |
|---|-------|----------|
| 1 | Efficient date filter with `_TABLE_SUFFIX` | CRITICAL |
| 2 | `event_params` is ARRAY — requires UNNEST with subquery | CRITICAL |
| 3 | `items` is ARRAY — requires CROSS JOIN UNNEST for e-commerce | CRITICAL |
| 4 | Revenue: `ecommerce.purchase_revenue` vs event_param 'value' | IMPORTANT |
| 5 | `ga_session_id` is in `event_params`, not a direct field | CRITICAL |
| 6 | Unique session = `user_pseudo_id` + `ga_session_id` | IMPORTANT |
| 7 | Correct `_TABLE_SUFFIX` syntax with wildcard tables | CRITICAL |
| 8 | `event_params` values have multiple types — use the correct one | IMPORTANT |

### Google Ads (7 gotchas)

| # | Title | Severity |
|---|-------|----------|
| 1 | `cost_micros` must be divided by 1,000,000 | CRITICAL |
| 2 | Use `_TABLE_SUFFIX` to filter dates in wildcard tables | CRITICAL |
| 3 | `segments_date` is the record date field (YYYY-MM-DD) | IMPORTANT |
| 4 | CPA: use NULLIF to avoid division by zero | CRITICAL |
| 5 | ROAS: use NULLIF on denominator (cost) | CRITICAL |
| 6 | JOIN stats with config tables using `campaign_id` / `ad_group_id` | IMPORTANT |
| 7 | Config tables have multiple `_DATA_DATE` — deduplicate with ROW_NUMBER | CRITICAL |

---

## Tech Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Language | Python | 3.11+ |
| Web Interface | Streamlit | 1.41.1 |
| AI / LLM | Claude Sonnet (Anthropic SDK) | anthropic 0.49.0 |
| BigQuery (dry-run) | google-cloud-bigquery | 3.27.0 |
| Schemas | PyYAML | 6.0.2 |
| SQL Formatting | sqlparse | 0.5.3 |
| Environment Variables | python-dotenv | 1.0.1 |

---

## Configuration

### Environment Variables

Create a `.env` file at the project root (use `.env.example` as a base):

```bash
# Required: Claude API key (Anthropic)
ANTHROPIC_API_KEY=sk-ant-...

# Optional: GCP project for cost dry-run
GCP_PROJECT_ID=your-gcp-project
```

The `ANTHROPIC_API_KEY` is required for SQL generation to work. Without it, the system displays an error message guiding the user through configuration.

### BigQuery Dry-Run (optional)

To enable query cost estimation in BigQuery:

1. Install and configure Google Cloud SDK:
   ```bash
   gcloud auth application-default login
   ```

2. Or set the environment variable pointing to a Service Account:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa-key.json
   ```

3. In the AskQL interface, enable the "Estimate cost on BigQuery" toggle in the sidebar.

The dry-run **never executes the query** — it only calculates the bytes that would be processed and estimates the cost at US$ 5/TB (BigQuery on-demand pricing).

---

## Limitations (Phase 0)

- **Does not execute queries on BigQuery** — only generates SQL + dry-run for cost estimation
- **Meta Ads is placeholder only** — minimal schema with no gotchas or templates
- **No query history** — each session is independent; generated queries are not persisted
- **No user authentication** — anyone with access to the URL can use it
- **Local deployment only** — no cloud deployment infrastructure configured
- **No feedback loop** — no mechanism for users to rate generated SQL quality
- **No response caching** — each question generates a new Claude API call

---

## Next Steps

- [ ] Complete Meta Ads schema (tables, gotchas, templates)
- [ ] Deploy to Streamlit Cloud or Cloud Run
- [ ] Query history per session/user
- [ ] Support for more sources (full Facebook Ads, TikTok Ads)
- [ ] Prompt fine-tuning based on user feedback
- [ ] Response caching for similar questions
- [ ] Real query execution on BigQuery (with cost controls)
- [ ] User authentication (OAuth / API key)
- [ ] Automated tests for generated SQL quality

---

## License

All rights reserved.
