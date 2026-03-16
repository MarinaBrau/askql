"""Fixtures compartilhadas para todos os testes."""

import pytest
from schemas.loader import (
    load_schema,
    list_sources,
    load_cross_source_alignment_rules,
    _load_cross_source_relationships_cached,
)


@pytest.fixture(autouse=True)
def clear_loader_caches():
    """Limpa caches do loader entre testes."""
    load_schema.cache_clear()
    list_sources.cache_clear()
    load_cross_source_alignment_rules.cache_clear()
    _load_cross_source_relationships_cached.cache_clear()
    yield
    load_schema.cache_clear()
    list_sources.cache_clear()
    load_cross_source_alignment_rules.cache_clear()
    _load_cross_source_relationships_cached.cache_clear()


@pytest.fixture
def source_names():
    """Lista de fontes validas no projeto."""
    return ["ga4_bigquery", "google_ads", "meta_ads"]


@pytest.fixture
def sample_safe_sql():
    """SQL SELECT simples para testes de validacao."""
    return """
    SELECT
        event_date,
        COUNT(*) AS total_events
    FROM `project.dataset.events_*`
    WHERE _TABLE_SUFFIX BETWEEN '20240101' AND '20240131'
    GROUP BY event_date
    ORDER BY event_date
    """


@pytest.fixture
def sample_unsafe_sql_delete():
    return "DELETE FROM `project.dataset.events_*` WHERE event_date = '20240101'"


@pytest.fixture
def sample_unsafe_sql_drop():
    return "DROP TABLE `project.dataset.events_20240101`"


@pytest.fixture
def sample_unsafe_sql_update():
    return "UPDATE `project.dataset.events_20240101` SET event_name = 'test'"


@pytest.fixture
def sample_unsafe_sql_insert():
    return "INSERT INTO `project.dataset.events_20240101` (event_name) VALUES ('test')"


@pytest.fixture
def sample_ga4_sql_with_unnest():
    """SQL GA4 completo com UNNEST(event_params)."""
    return """
    SELECT
        event_date,
        (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'page_location') AS page_location,
        COUNT(*) AS pageviews
    FROM `project.dataset.events_*`
    WHERE _TABLE_SUFFIX BETWEEN '20240101' AND '20240131'
      AND event_name = 'page_view'
    GROUP BY 1, 2
    ORDER BY pageviews DESC
    """


@pytest.fixture
def sample_google_ads_sql():
    """SQL Google Ads com cost_micros e NULLIF."""
    return """
    SELECT
        segments_date,
        campaign_name,
        metrics_impressions,
        metrics_clicks,
        metrics_cost_micros / 1000000 AS cost,
        SAFE_DIVIDE(metrics_clicks, NULLIF(metrics_impressions, 0)) AS ctr
    FROM `project.dataset.ads_CampaignStats_*`
    WHERE _TABLE_SUFFIX BETWEEN '20240101' AND '20240131'
    """


@pytest.fixture
def sample_meta_ads_sql():
    """SQL Meta Ads com spend e UNNEST(actions)."""
    return """
    SELECT
        date_start,
        campaign_name,
        spend,
        impressions,
        act.value AS purchases
    FROM `project.dataset.meta_ads_campaigns`
    LEFT JOIN UNNEST(actions) AS act ON act.action_type = 'purchase'
    WHERE date_start BETWEEN '2024-01-01' AND '2024-01-31'
    """
