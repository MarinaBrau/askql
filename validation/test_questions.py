"""22 test questions for validating AskQL SQL generation quality."""

# Each question has: id, source, category, question, description
# source must match schema source_name (ga4_bigquery or google_ads)

QUESTIONS = [
    # =====================================================================
    # GA4 BigQuery — Acquisition (3)
    # =====================================================================
    {
        "id": "ga4_acq_01",
        "source": "ga4_bigquery",
        "category": "acquisition",
        "question": "Quais sao as top 10 fontes de trafego por numero de sessoes?",
        "description": "Deve usar UNNEST(event_params) para source/medium e CONCAT(user_pseudo_id + ga_session_id) para sessoes unicas",
    },
    {
        "id": "ga4_acq_02",
        "source": "ga4_bigquery",
        "category": "acquisition",
        "question": "Quais campanhas geraram mais sessoes no ultimo mes?",
        "description": "Deve extrair campaign de event_params via UNNEST",
    },
    {
        "id": "ga4_acq_03",
        "source": "ga4_bigquery",
        "category": "acquisition",
        "question": "Qual a proporcao de usuarios novos vs recorrentes?",
        "description": "Deve usar ga_session_number de event_params (int_value) para distinguir novos (=1) vs recorrentes (>1)",
    },
    # =====================================================================
    # GA4 BigQuery — Engagement (3)
    # =====================================================================
    {
        "id": "ga4_eng_01",
        "source": "ga4_bigquery",
        "category": "engagement",
        "question": "Quais sao as 10 paginas mais acessadas do meu site?",
        "description": "Deve usar UNNEST(event_params) para page_location e filtrar event_name = 'page_view'",
    },
    {
        "id": "ga4_eng_02",
        "source": "ga4_bigquery",
        "category": "engagement",
        "question": "Qual o tempo medio de engajamento por pagina?",
        "description": "Deve extrair engagement_time_msec de event_params (int_value) e converter para segundos",
    },
    {
        "id": "ga4_eng_03",
        "source": "ga4_bigquery",
        "category": "engagement",
        "question": "Qual a taxa de bounce por pagina de entrada?",
        "description": "Deve calcular bounce rate usando session_engaged de event_params",
    },
    # =====================================================================
    # GA4 BigQuery — E-commerce (3)
    # =====================================================================
    {
        "id": "ga4_ecom_01",
        "source": "ga4_bigquery",
        "category": "ecommerce",
        "question": "Como esta meu funil de conversao? (visualizacao -> carrinho -> checkout -> compra)",
        "description": "Deve contar eventos view_item, add_to_cart, begin_checkout, purchase",
    },
    {
        "id": "ga4_ecom_02",
        "source": "ga4_bigquery",
        "category": "ecommerce",
        "question": "Quais sao os 10 produtos que mais geram receita?",
        "description": "Deve usar UNNEST(items) para acessar item_name e item_revenue",
    },
    {
        "id": "ga4_ecom_03",
        "source": "ga4_bigquery",
        "category": "ecommerce",
        "question": "Qual fonte de trafego gera mais receita de compras?",
        "description": "Deve combinar UNNEST(event_params) para source com ecommerce.purchase_revenue",
    },
    # =====================================================================
    # GA4 BigQuery — Audience (2)
    # =====================================================================
    {
        "id": "ga4_aud_01",
        "source": "ga4_bigquery",
        "category": "audience",
        "question": "Como meus usuarios se distribuem por tipo de dispositivo?",
        "description": "Deve usar device.category (campo direto, nao precisa UNNEST)",
    },
    {
        "id": "ga4_aud_02",
        "source": "ga4_bigquery",
        "category": "audience",
        "question": "De quais estados do Brasil vem meus usuarios?",
        "description": "Deve usar geo.region (campo direto)",
    },
    # =====================================================================
    # GA4 BigQuery — Edge Cases (3)
    # =====================================================================
    {
        "id": "ga4_edge_01",
        "source": "ga4_bigquery",
        "category": "edge_case",
        "question": "Quantos eventos custom 'form_submit' aconteceram por dia?",
        "description": "Deve filtrar event_name = 'form_submit' e agrupar por event_date com _TABLE_SUFFIX",
    },
    {
        "id": "ga4_edge_02",
        "source": "ga4_bigquery",
        "category": "edge_case",
        "question": "Qual a tendencia diaria de sessoes nos ultimos 30 dias?",
        "description": "Deve usar _TABLE_SUFFIX para filtro de data e CONCAT para sessoes unicas por dia",
    },
    {
        "id": "ga4_edge_03",
        "source": "ga4_bigquery",
        "category": "edge_case",
        "question": "What is the average number of pages per session?",
        "description": "Pergunta em ingles — deve responder corretamente, usando page_view events e sessoes unicas",
    },
    # =====================================================================
    # Google Ads — Performance (3)
    # =====================================================================
    {
        "id": "gads_perf_01",
        "source": "google_ads",
        "category": "performance",
        "question": "Qual o CPA de cada campanha?",
        "description": "Deve usar cost_micros / 1000000.0 e NULLIF para divisao segura",
    },
    {
        "id": "gads_perf_02",
        "source": "google_ads",
        "category": "performance",
        "question": "Qual o ROAS de cada campanha?",
        "description": "Deve usar conversions_value / NULLIF(cost, 0) com conversao de micros",
    },
    {
        "id": "gads_perf_03",
        "source": "google_ads",
        "category": "performance",
        "question": "Compare o desempenho de campanhas Search vs Display (custo, cliques, conversoes)",
        "description": "Deve fazer JOIN com ads_Campaign para obter campaign_advertising_channel_type e deduplicar com ROW_NUMBER",
    },
    # =====================================================================
    # Google Ads — Budget (2)
    # =====================================================================
    {
        "id": "gads_budget_01",
        "source": "google_ads",
        "category": "budget",
        "question": "Como esta a tendencia de gasto diario nos ultimos 30 dias?",
        "description": "Deve usar segments_date para agrupamento e cost_micros / 1e6 para conversao",
    },
    {
        "id": "gads_budget_02",
        "source": "google_ads",
        "category": "budget",
        "question": "Qual o gasto total mensal por campanha?",
        "description": "Deve agrupar segments_date por mes e fazer JOIN com Campaign para nome",
    },
    # =====================================================================
    # Google Ads — Keywords (2)
    # =====================================================================
    {
        "id": "gads_kw_01",
        "source": "google_ads",
        "category": "keywords",
        "question": "Quais keywords geram mais conversoes?",
        "description": "Deve usar ads_KeywordStats e converter cost_micros",
    },
    {
        "id": "gads_kw_02",
        "source": "google_ads",
        "category": "keywords",
        "question": "Quais keywords tem o melhor CPA (menor custo por conversao)?",
        "description": "Deve calcular CPA com NULLIF e ordenar por CPA ascendente",
    },
    # =====================================================================
    # Google Ads — Edge Case (1)
    # =====================================================================
    {
        "id": "gads_edge_01",
        "source": "google_ads",
        "category": "edge_case",
        "question": "Qual o CTR e CPC medio por ad group?",
        "description": "Deve usar ads_AdGroupStats, calcular CTR = clicks/impressions com NULLIF, CPC = cost/clicks com NULLIF",
    },
    # =====================================================================
    # Meta Ads — Performance (2)
    # =====================================================================
    {
        "id": "meta_perf_01",
        "source": "meta_ads",
        "category": "performance",
        "question": "Qual o CPA de cada campanha no Meta Ads?",
        "description": "Deve usar UNNEST(actions) para extrair purchases e NULLIF para divisao segura. spend ja esta em moeda real (NAO dividir por 1M)",
    },
    {
        "id": "meta_perf_02",
        "source": "meta_ads",
        "category": "performance",
        "question": "Qual o ROAS de cada campanha no Meta?",
        "description": "Deve usar UNNEST(action_values) para valor de purchases e NULLIF(spend, 0) no denominador",
    },
    # =====================================================================
    # Meta Ads — Budget (1)
    # =====================================================================
    {
        "id": "meta_budget_01",
        "source": "meta_ads",
        "category": "budget",
        "question": "Como esta a tendencia de gasto diario no Meta Ads?",
        "description": "Deve usar date_start para agrupamento e _TABLE_SUFFIX para filtro. spend direto sem conversao de micros",
    },
    # =====================================================================
    # Meta Ads — Alcance (1)
    # =====================================================================
    {
        "id": "meta_alcance_01",
        "source": "meta_ads",
        "category": "alcance",
        "question": "Qual o alcance e a frequencia media de cada campanha?",
        "description": "Deve usar reach para alcance unico e calcular frequencia como impressions/reach com NULLIF",
    },
    # =====================================================================
    # Meta Ads — Conversoes (1)
    # =====================================================================
    {
        "id": "meta_conv_01",
        "source": "meta_ads",
        "category": "conversoes",
        "question": "Quais tipos de conversao estao acontecendo nas minhas campanhas do Meta?",
        "description": "Deve usar CROSS JOIN UNNEST(actions) para expandir todos os action_types",
    },
    # =====================================================================
    # Meta Ads — Edge Case (1)
    # =====================================================================
    {
        "id": "meta_edge_01",
        "source": "meta_ads",
        "category": "edge_case",
        "question": "Qual o CTR de link vs CTR total por campanha no Meta?",
        "description": "Deve usar link_clicks para CTR de link e clicks para CTR total, ambos com NULLIF. Deve distinguir os dois campos",
    },
    # =====================================================================
    # Cross-Source (3)
    # =====================================================================
    {
        "id": "cross_ga4_gads_01",
        "source": "ga4_bigquery",
        "secondary_source": "google_ads",
        "secondary_dataset": "google_ads_transfer",
        "category": "cross_source",
        "question": "Qual a relacao entre sessoes do GA4 e gastos do Google Ads por dia?",
        "description": "Deve usar CTEs separadas, PARSE_DATE para alinhar datas (YYYYMMDD vs YYYY-MM-DD), e cost_micros / 1e6",
    },
    {
        "id": "cross_ga4_meta_01",
        "source": "ga4_bigquery",
        "secondary_source": "meta_ads",
        "secondary_dataset": "meta_ads_data",
        "category": "cross_source",
        "question": "Compare sessoes do GA4 com investimento do Meta Ads por dia",
        "description": "Deve usar CTEs separadas, PARSE_DATE para alinhar datas, spend direto (sem /1M)",
    },
    {
        "id": "cross_gads_meta_01",
        "source": "google_ads",
        "secondary_source": "meta_ads",
        "secondary_dataset": "meta_ads_data",
        "category": "cross_source",
        "question": "Compare investimento Google Ads vs Meta Ads por semana",
        "description": "Deve usar CTEs separadas, normalizar cost_micros / 1e6, agrupar por semana com DATE_TRUNC",
    },
]


def get_questions(source=None):
    """Return questions, optionally filtered by source."""
    if source is None:
        return QUESTIONS
    return [q for q in QUESTIONS if q["source"] == source]


def get_sources():
    """Return unique sources from questions."""
    return sorted(set(q["source"] for q in QUESTIONS))
