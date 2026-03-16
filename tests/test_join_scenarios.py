"""
30+ cenarios realistas de JOIN que um analista de marketing faria.
Cada teste roda o SQL pelas check functions via run_checks() e valida
que os checks detectam corretamente problemas (ou aprovam SQL correto).
"""

import pytest
from validation.quality_checks import run_checks


def _check_ids(results):
    """Helper: retorna set de IDs dos checks que falharam."""
    return {r["id"] for r in results if not r["passed"]}


def _all_passed(results):
    """Helper: retorna True se todos os checks passaram."""
    return all(r["passed"] for r in results)


# ═══════════════════════════════════════════════════════════════════════════
# GOOGLE ADS — JOINs com config tables
# ═══════════════════════════════════════════════════════════════════════════

class TestGoogleAdsCampaignJoins:
    """CampaignStats + Campaign — o JOIN mais comum."""

    def test_01_campaign_stats_join_campaign_correct(self):
        """Custo por campanha com dedup + cost_micros/1M + NULLIF — tudo certo."""
        sql = """
        WITH campaign_latest AS (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY campaign_id ORDER BY _TABLE_SUFFIX DESC) AS rn
            FROM `proj.ds.ads_Campaign_*`
            WHERE _TABLE_SUFFIX BETWEEN '20240101' AND '20240131'
        )
        SELECT
            c.campaign_name,
            SUM(s.metrics_impressions) AS impressions,
            SUM(s.metrics_clicks) AS clicks,
            SUM(s.metrics_cost_micros) / 1000000 AS cost,
            SAFE_DIVIDE(SUM(s.metrics_clicks), NULLIF(SUM(s.metrics_impressions), 0)) AS ctr
        FROM `proj.ds.ads_CampaignStats_*` s
        JOIN campaign_latest c ON s.campaign_id = c.campaign_id AND c.rn = 1
        WHERE _TABLE_SUFFIX BETWEEN '20240101' AND '20240131'
        GROUP BY 1
        ORDER BY cost DESC
        """
        results = run_checks(sql, "google_ads")
        assert _all_passed(results), f"Falhas: {_check_ids(results)}"

    def test_02_campaign_stats_join_campaign_no_dedup(self):
        """JOIN Campaign sem ROW_NUMBER — deve falhar dedup checks."""
        sql = """
        SELECT
            c.campaign_name,
            SUM(s.metrics_impressions) AS impressions,
            SUM(s.metrics_cost_micros) / 1000000 AS cost,
            SAFE_DIVIDE(SUM(s.metrics_clicks), NULLIF(SUM(s.metrics_impressions), 0)) AS ctr
        FROM `proj.ds.ads_CampaignStats_*` s
        JOIN `proj.ds.ads_Campaign_*` c ON s.campaign_id = c.campaign_id
        WHERE _TABLE_SUFFIX BETWEEN '20240101' AND '20240131'
        GROUP BY 1
        """
        failed = _check_ids(run_checks(sql, "google_ads"))
        assert "row_number_dedup" in failed
        assert "join_dedup_required" in failed

    def test_03_campaign_stats_no_cost_conversion(self):
        """cost_micros sem dividir por 1M — deve falhar."""
        sql = """
        WITH campaign_latest AS (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY campaign_id ORDER BY _TABLE_SUFFIX DESC) AS rn
            FROM `proj.ds.ads_Campaign_*`
        )
        SELECT
            c.campaign_name,
            SUM(s.metrics_cost_micros) AS cost
        FROM `proj.ds.ads_CampaignStats_*` s
        JOIN campaign_latest c ON s.campaign_id = c.campaign_id AND c.rn = 1
        WHERE _TABLE_SUFFIX BETWEEN '20240101' AND '20240131'
        GROUP BY 1
        """
        failed = _check_ids(run_checks(sql, "google_ads"))
        assert "cost_micros_conversion" in failed

    def test_04_campaign_cpa_no_nullif(self):
        """CPA calculado sem NULLIF — deve falhar."""
        sql = """
        WITH campaign_latest AS (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY campaign_id ORDER BY _TABLE_SUFFIX DESC) AS rn
            FROM `proj.ds.ads_Campaign_*`
        )
        SELECT
            c.campaign_name,
            SUM(s.metrics_cost_micros) / 1000000 / SUM(s.metrics_conversions) AS cpa
        FROM `proj.ds.ads_CampaignStats_*` s
        JOIN campaign_latest c ON s.campaign_id = c.campaign_id AND c.rn = 1
        WHERE _TABLE_SUFFIX BETWEEN '20240101' AND '20240131'
        GROUP BY 1
        """
        failed = _check_ids(run_checks(sql, "google_ads"))
        assert "nullif_division" in failed


class TestGoogleAdsAdGroupJoins:
    """AdGroupStats + AdGroup — segundo JOIN mais comum."""

    def test_05_adgroup_stats_join_correct(self):
        """Metricas por ad group com dedup correto."""
        sql = """
        WITH adgroup_latest AS (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY ad_group_id ORDER BY _TABLE_SUFFIX DESC) AS rn
            FROM `proj.ds.ads_AdGroup_*`
            WHERE _TABLE_SUFFIX BETWEEN '20240101' AND '20240131'
        )
        SELECT
            ag.ad_group_name,
            SUM(s.metrics_impressions) AS impressions,
            SUM(s.metrics_clicks) AS clicks,
            SUM(s.metrics_cost_micros) / 1000000 AS cost,
            SAFE_DIVIDE(SUM(s.metrics_cost_micros) / 1000000, NULLIF(SUM(s.metrics_clicks), 0)) AS cpc
        FROM `proj.ds.ads_AdGroupStats_*` s
        JOIN adgroup_latest ag ON s.ad_group_id = ag.ad_group_id AND ag.rn = 1
        WHERE _TABLE_SUFFIX BETWEEN '20240101' AND '20240131'
        GROUP BY 1
        ORDER BY cost DESC
        """
        results = run_checks(sql, "google_ads")
        assert _all_passed(results), f"Falhas: {_check_ids(results)}"

    def test_06_adgroup_stats_join_no_dedup(self):
        """AdGroupStats + AdGroup sem dedup — deve falhar."""
        sql = """
        SELECT
            ag.ad_group_name,
            SUM(s.metrics_cost_micros) / 1000000 AS cost,
            SAFE_DIVIDE(SUM(s.metrics_clicks), NULLIF(SUM(s.metrics_impressions), 0)) AS ctr
        FROM `proj.ds.ads_AdGroupStats_*` s
        JOIN `proj.ds.ads_AdGroup_*` ag ON s.ad_group_id = ag.ad_group_id
        WHERE _TABLE_SUFFIX BETWEEN '20240101' AND '20240131'
        GROUP BY 1
        """
        failed = _check_ids(run_checks(sql, "google_ads"))
        assert "row_number_dedup" in failed or "join_dedup_required" in failed

    def test_07_adgroup_join_wrong_key(self):
        """AdGroup JOIN com chave inventada — deve falhar join_key_match."""
        sql = """
        SELECT ag.ad_group_name, SUM(s.metrics_clicks) AS clicks
        FROM `proj.ds.ads_AdGroupStats_*` s
        JOIN `proj.ds.ads_AdGroup_*` ag ON s.some_random_key = ag.some_random_key
        WHERE _TABLE_SUFFIX BETWEEN '20240101' AND '20240131'
        GROUP BY 1
        """
        failed = _check_ids(run_checks(sql, "google_ads"))
        assert "join_key_match" in failed


class TestGoogleAdsMultiJoin:
    """JOINs com 3+ tabelas."""

    def test_08_three_way_join_correct(self):
        """AdGroupStats + AdGroup + Campaign — 3-way JOIN com dedup correto."""
        sql = """
        WITH campaign_latest AS (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY campaign_id ORDER BY _TABLE_SUFFIX DESC) AS rn
            FROM `proj.ds.ads_Campaign_*`
        ),
        adgroup_latest AS (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY ad_group_id ORDER BY _TABLE_SUFFIX DESC) AS rn
            FROM `proj.ds.ads_AdGroup_*`
        )
        SELECT
            c.campaign_name,
            ag.ad_group_name,
            SUM(s.metrics_impressions) AS impressions,
            SUM(s.metrics_cost_micros) / 1000000 AS cost,
            SAFE_DIVIDE(SUM(s.metrics_clicks), NULLIF(SUM(s.metrics_impressions), 0)) AS ctr
        FROM `proj.ds.ads_AdGroupStats_*` s
        JOIN adgroup_latest ag ON s.ad_group_id = ag.ad_group_id AND ag.rn = 1
        JOIN campaign_latest c ON s.campaign_id = c.campaign_id AND c.rn = 1
        WHERE _TABLE_SUFFIX BETWEEN '20240101' AND '20240131'
        GROUP BY 1, 2
        ORDER BY cost DESC
        """
        results = run_checks(sql, "google_ads")
        assert _all_passed(results), f"Falhas: {_check_ids(results)}"

    def test_09_keyword_stats_join_adgroup_correct(self):
        """KeywordStats + AdGroup com dedup."""
        sql = """
        WITH adgroup_latest AS (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY ad_group_id ORDER BY _TABLE_SUFFIX DESC) AS rn
            FROM `proj.ds.ads_AdGroup_*`
        )
        SELECT
            ag.ad_group_name,
            s.metrics_search_term AS keyword,
            SUM(s.metrics_impressions) AS impressions,
            SUM(s.metrics_cost_micros) / 1000000 AS cost,
            SAFE_DIVIDE(SUM(s.metrics_clicks), NULLIF(SUM(s.metrics_impressions), 0)) AS ctr
        FROM `proj.ds.ads_KeywordStats_*` s
        JOIN adgroup_latest ag ON s.ad_group_id = ag.ad_group_id AND ag.rn = 1
        WHERE _TABLE_SUFFIX BETWEEN '20240101' AND '20240131'
        GROUP BY 1, 2
        """
        results = run_checks(sql, "google_ads")
        assert _all_passed(results), f"Falhas: {_check_ids(results)}"

    def test_10_ad_stats_join_campaign_correct(self):
        """AdStats + Campaign com dedup — analise de performance por anuncio."""
        sql = """
        WITH campaign_latest AS (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY campaign_id ORDER BY _TABLE_SUFFIX DESC) AS rn
            FROM `proj.ds.ads_Campaign_*`
        )
        SELECT
            c.campaign_name,
            s.ad_id,
            SUM(s.metrics_impressions) AS impressions,
            SUM(s.metrics_clicks) AS clicks,
            SUM(s.metrics_cost_micros) / 1000000 AS cost,
            SAFE_DIVIDE(SUM(s.metrics_cost_micros) / 1000000, NULLIF(SUM(s.metrics_conversions), 0)) AS cpa
        FROM `proj.ds.ads_AdStats_*` s
        JOIN campaign_latest c ON s.campaign_id = c.campaign_id AND c.rn = 1
        WHERE _TABLE_SUFFIX BETWEEN '20240101' AND '20240131'
        GROUP BY 1, 2
        ORDER BY cost DESC
        """
        results = run_checks(sql, "google_ads")
        assert _all_passed(results), f"Falhas: {_check_ids(results)}"


class TestGoogleAdsStandalone:
    """Queries Google Ads sem JOIN (so stats table)."""

    def test_11_campaign_stats_standalone_correct(self):
        """CampaignStats sem JOIN — nao precisa dedup."""
        sql = """
        SELECT
            segments_date,
            campaign_id,
            SUM(metrics_impressions) AS impressions,
            SUM(metrics_cost_micros) / 1000000 AS cost,
            SAFE_DIVIDE(SUM(metrics_clicks), NULLIF(SUM(metrics_impressions), 0)) AS ctr
        FROM `proj.ds.ads_CampaignStats_*`
        WHERE _TABLE_SUFFIX BETWEEN '20240101' AND '20240131'
        GROUP BY 1, 2
        """
        results = run_checks(sql, "google_ads")
        assert _all_passed(results), f"Falhas: {_check_ids(results)}"

    def test_12_campaign_config_standalone(self):
        """Campaign config table sozinha — sem JOIN, nao precisa dedup."""
        sql = """
        SELECT campaign_id, campaign_name, campaign_status
        FROM `proj.ds.ads_Campaign_*`
        WHERE _TABLE_SUFFIX = '20240131'
        """
        results = run_checks(sql, "google_ads")
        assert _all_passed(results), f"Falhas: {_check_ids(results)}"


# ═══════════════════════════════════════════════════════════════════════════
# META ADS — JOINs e patterns
# ═══════════════════════════════════════════════════════════════════════════

class TestMetaAdsCampaignJoins:
    """Meta Ads insights + config table."""

    def test_13_campaign_insights_correct(self):
        """Spend por campanha com nome — JOIN correto."""
        sql = """
        SELECT
            c.name AS campaign_name,
            SUM(i.spend) AS total_spend,
            SUM(i.impressions) AS total_impressions
        FROM `proj.ds.meta_ads_insights_campaign_*` i
        JOIN `proj.ds.meta_ads_campaigns` c ON i.campaign_id = c.id
        WHERE _TABLE_SUFFIX BETWEEN '20240101' AND '20240131'
        GROUP BY 1
        ORDER BY total_spend DESC
        """
        results = run_checks(sql, "meta_ads")
        assert _all_passed(results), f"Falhas: {_check_ids(results)}"

    def test_14_campaign_insights_spend_divided_by_million(self):
        """Meta Ads spend dividido por 1M — ERRADO, spend ja e real."""
        sql = """
        SELECT
            c.name AS campaign_name,
            SUM(i.spend) / 1000000 AS total_spend
        FROM `proj.ds.meta_ads_insights_campaign_*` i
        JOIN `proj.ds.meta_ads_campaigns` c ON i.campaign_id = c.id
        WHERE _TABLE_SUFFIX BETWEEN '20240101' AND '20240131'
        GROUP BY 1
        """
        failed = _check_ids(run_checks(sql, "meta_ads"))
        assert "spend_no_micros" in failed

    def test_15_adset_insights_with_conversions_correct(self):
        """Conversoes por ad set com UNNEST(actions)."""
        sql = """
        SELECT
            i.adset_id,
            SUM(i.spend) AS spend,
            SUM(CAST(act.value AS FLOAT64)) AS purchases
        FROM `proj.ds.meta_ads_insights_adset_*` i
        LEFT JOIN UNNEST(actions) AS act ON act.action_type = 'purchase'
        WHERE _TABLE_SUFFIX BETWEEN '20240101' AND '20240131'
        GROUP BY 1
        """
        results = run_checks(sql, "meta_ads")
        assert _all_passed(results), f"Falhas: {_check_ids(results)}"

    def test_16_ad_insights_no_unnest_actions(self):
        """Referencia purchase sem UNNEST(actions) — deve falhar."""
        sql = """
        SELECT
            ad_id,
            spend,
            purchase AS conversions
        FROM `proj.ds.meta_ads_insights_ad_*`
        WHERE _TABLE_SUFFIX BETWEEN '20240101' AND '20240131'
        """
        failed = _check_ids(run_checks(sql, "meta_ads"))
        assert "unnest_actions" in failed

    def test_17_campaign_ctr_with_link_clicks_correct(self):
        """CTR com link_clicks — correto para Meta Ads."""
        sql = """
        SELECT
            campaign_id,
            SUM(spend) AS spend,
            SUM(impressions) AS impressions,
            SAFE_DIVIDE(SUM(link_clicks), NULLIF(SUM(impressions), 0)) AS ctr
        FROM `proj.ds.meta_ads_insights_campaign_*`
        WHERE _TABLE_SUFFIX BETWEEN '20240101' AND '20240131'
        GROUP BY 1
        """
        results = run_checks(sql, "meta_ads")
        assert _all_passed(results), f"Falhas: {_check_ids(results)}"

    def test_18_campaign_ctr_with_clicks_wrong(self):
        """CTR com clicks generico — deve avisar pra usar link_clicks."""
        sql = """
        SELECT
            campaign_id,
            SUM(spend) AS spend,
            SAFE_DIVIDE(SUM(clicks), NULLIF(SUM(impressions), 0)) AS ctr
        FROM `proj.ds.meta_ads_insights_campaign_*`
        WHERE _TABLE_SUFFIX BETWEEN '20240101' AND '20240131'
        GROUP BY 1
        """
        failed = _check_ids(run_checks(sql, "meta_ads"))
        assert "link_clicks_vs_clicks" in failed

    def test_19_meta_roas_without_nullif(self):
        """ROAS sem NULLIF — deve falhar."""
        sql = """
        SELECT
            campaign_id,
            SUM(CAST(act.value AS FLOAT64)) / SUM(spend) AS roas
        FROM `proj.ds.meta_ads_insights_campaign_*` i
        LEFT JOIN UNNEST(actions) AS act ON act.action_type = 'purchase'
        WHERE _TABLE_SUFFIX BETWEEN '20240101' AND '20240131'
        GROUP BY 1
        """
        failed = _check_ids(run_checks(sql, "meta_ads"))
        assert "nullif_division" in failed


# ═══════════════════════════════════════════════════════════════════════════
# GA4 — UNNEST patterns (funciona como JOIN)
# ═══════════════════════════════════════════════════════════════════════════

class TestGA4UnnestJoins:
    """GA4 UNNEST patterns — tecnicamente sao JOINs com arrays."""

    def test_20_sessions_by_source_correct(self):
        """Sessoes por source/medium com UNNEST + user_pseudo_id."""
        sql = """
        SELECT
            (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'source') AS source,
            (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'medium') AS medium,
            COUNT(DISTINCT user_pseudo_id) AS users,
            COUNT(DISTINCT CONCAT(user_pseudo_id, CAST((SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_id') AS STRING))) AS sessions
        FROM `proj.ds.events_*`
        WHERE _TABLE_SUFFIX BETWEEN '20240101' AND '20240131'
            AND event_name = 'session_start'
        GROUP BY 1, 2
        ORDER BY sessions DESC
        """
        results = run_checks(sql, "ga4_bigquery")
        assert _all_passed(results), f"Falhas: {_check_ids(results)}"

    def test_21_pageviews_no_unnest(self):
        """page_location sem UNNEST(event_params) — deve falhar."""
        sql = """
        SELECT
            event_date,
            page_location,
            COUNT(*) AS pageviews
        FROM `proj.ds.events_*`
        WHERE _TABLE_SUFFIX BETWEEN '20240101' AND '20240131'
            AND event_name = 'page_view'
        GROUP BY 1, 2
        """
        failed = _check_ids(run_checks(sql, "ga4_bigquery"))
        assert "unnest_event_params" in failed

    def test_22_ecommerce_with_unnest_items_correct(self):
        """E-commerce: revenue por produto com UNNEST(items)."""
        sql = """
        SELECT
            item.item_name,
            item.item_category,
            COUNT(*) AS purchases,
            SUM(item.item_revenue) AS revenue
        FROM `proj.ds.events_*`,
        UNNEST(items) AS item
        WHERE _TABLE_SUFFIX BETWEEN '20240101' AND '20240131'
            AND event_name = 'purchase'
        GROUP BY 1, 2
        ORDER BY revenue DESC
        """
        results = run_checks(sql, "ga4_bigquery")
        assert _all_passed(results), f"Falhas: {_check_ids(results)}"

    def test_23_ecommerce_no_unnest_items(self):
        """item_name sem UNNEST(items) — deve falhar."""
        sql = """
        SELECT
            item_name,
            COUNT(*) AS purchases
        FROM `proj.ds.events_*`
        WHERE _TABLE_SUFFIX BETWEEN '20240101' AND '20240131'
            AND event_name = 'purchase'
        GROUP BY 1
        """
        failed = _check_ids(run_checks(sql, "ga4_bigquery"))
        assert "unnest_items" in failed

    def test_24_user_count_without_pseudo_id(self):
        """Contagem de usuarios com user_id inventado — deve falhar."""
        sql = """
        SELECT
            event_date,
            COUNT(DISTINCT user_id) AS users
        FROM `proj.ds.events_*`
        WHERE _TABLE_SUFFIX BETWEEN '20240101' AND '20240131'
        GROUP BY 1
        """
        failed = _check_ids(run_checks(sql, "ga4_bigquery"))
        assert "user_pseudo_id" in failed

    def test_25_session_id_direct_access(self):
        """ga_session_id acessado diretamente — deve falhar."""
        sql = """
        SELECT
            event_date,
            ga_session_id,
            COUNT(*) AS events
        FROM `proj.ds.events_*`
        WHERE _TABLE_SUFFIX BETWEEN '20240101' AND '20240131'
        GROUP BY 1, 2
        """
        failed = _check_ids(run_checks(sql, "ga4_bigquery"))
        assert "ga_session_id_from_params" in failed

    def test_26_ga4_no_table_suffix(self):
        """Wildcard table sem _TABLE_SUFFIX — deve falhar."""
        sql = """
        SELECT event_date, COUNT(*) AS events
        FROM `proj.ds.events_*`
        GROUP BY 1
        """
        failed = _check_ids(run_checks(sql, "ga4_bigquery"))
        assert "table_suffix" in failed


# ═══════════════════════════════════════════════════════════════════════════
# CROSS-SOURCE — JOINs entre fontes diferentes
# ═══════════════════════════════════════════════════════════════════════════

class TestCrossSourceJoins:
    """Queries combinando dados de fontes diferentes."""

    def test_27_ga4_google_ads_by_date_correct(self):
        """GA4 + Google Ads por data — PARSE_DATE + cost_micros/1M."""
        sql = """
        WITH ga4_daily AS (
            SELECT
                PARSE_DATE('%Y%m%d', event_date) AS dt,
                COUNT(DISTINCT user_pseudo_id) AS users,
                COUNT(DISTINCT CONCAT(user_pseudo_id, CAST((SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_id') AS STRING))) AS sessions
            FROM `proj.ds_ga4.events_*`
            WHERE _TABLE_SUFFIX BETWEEN '20240101' AND '20240131'
            GROUP BY 1
        ),
        gads_daily AS (
            SELECT
                segments_date AS dt,
                SUM(metrics_impressions) AS impressions,
                SUM(metrics_clicks) AS clicks,
                SUM(metrics_cost_micros) / 1000000 AS cost
            FROM `proj.ds_gads.ads_CampaignStats_*`
            WHERE _TABLE_SUFFIX BETWEEN '20240101' AND '20240131'
            GROUP BY 1
        )
        SELECT
            g.dt,
            g.users,
            g.sessions,
            a.impressions,
            a.clicks,
            a.cost,
            SAFE_DIVIDE(a.cost, NULLIF(g.sessions, 0)) AS cost_per_session
        FROM ga4_daily g
        JOIN gads_daily a ON g.dt = a.dt
        ORDER BY g.dt
        """
        results = run_checks(sql, "ga4_bigquery", is_cross_source=True)
        assert _all_passed(results), f"Falhas: {_check_ids(results)}"

    def test_28_ga4_google_ads_no_date_alignment(self):
        """GA4 + Google Ads sem PARSE_DATE — deve falhar date alignment."""
        sql = """
        WITH ga4_daily AS (
            SELECT event_date AS dt, COUNT(*) AS events
            FROM `proj.ds_ga4.events_*`
            WHERE _TABLE_SUFFIX BETWEEN '20240101' AND '20240131'
            GROUP BY 1
        ),
        gads_daily AS (
            SELECT segments_date AS dt, SUM(metrics_cost_micros) / 1000000 AS cost
            FROM `proj.ds_gads.ads_CampaignStats_*`
            WHERE _TABLE_SUFFIX BETWEEN '20240101' AND '20240131'
            GROUP BY 1
        )
        SELECT g.dt, g.events, a.cost
        FROM ga4_daily g JOIN gads_daily a ON g.dt = a.dt
        """
        failed = _check_ids(run_checks(sql, "ga4_bigquery", is_cross_source=True))
        assert "cross_source_date_alignment" in failed

    def test_29_ga4_meta_ads_by_date_correct(self):
        """GA4 + Meta Ads por data — PARSE_DATE correto."""
        sql = """
        WITH ga4_daily AS (
            SELECT
                PARSE_DATE('%Y%m%d', event_date) AS dt,
                COUNT(DISTINCT user_pseudo_id) AS users
            FROM `proj.ds_ga4.events_*`
            WHERE _TABLE_SUFFIX BETWEEN '20240101' AND '20240131'
            GROUP BY 1
        ),
        meta_daily AS (
            SELECT
                date_start AS dt,
                SUM(spend) AS spend,
                SUM(impressions) AS impressions
            FROM `proj.ds_meta.meta_ads_insights_campaign_*`
            WHERE _TABLE_SUFFIX BETWEEN '20240101' AND '20240131'
            GROUP BY 1
        )
        SELECT g.dt, g.users, m.spend, m.impressions
        FROM ga4_daily g
        JOIN meta_daily m ON g.dt = m.dt
        ORDER BY g.dt
        """
        results = run_checks(sql, "ga4_bigquery", is_cross_source=True)
        assert _all_passed(results), f"Falhas: {_check_ids(results)}"

    def test_30_google_ads_meta_ads_currency_correct(self):
        """Google Ads + Meta Ads — cost_micros/1M + spend lado a lado."""
        sql = """
        WITH gads AS (
            SELECT
                segments_date AS dt,
                SUM(metrics_cost_micros) / 1000000 AS cost
            FROM `proj.ds_gads.ads_CampaignStats_*`
            WHERE _TABLE_SUFFIX BETWEEN '20240101' AND '20240131'
            GROUP BY 1
        ),
        meta AS (
            SELECT
                date_start AS dt,
                SUM(spend) AS cost
            FROM `proj.ds_meta.meta_ads_insights_campaign_*`
            WHERE _TABLE_SUFFIX BETWEEN '20240101' AND '20240131'
            GROUP BY 1
        )
        SELECT
            COALESCE(g.dt, m.dt) AS dt,
            g.cost AS gads_cost,
            m.cost AS meta_cost,
            COALESCE(g.cost, 0) + COALESCE(m.cost, 0) AS total_cost
        FROM gads g
        FULL OUTER JOIN meta m ON g.dt = m.dt
        ORDER BY dt
        """
        results = run_checks(sql, "google_ads", is_cross_source=True)
        assert _all_passed(results), f"Falhas: {_check_ids(results)}"

    def test_31_google_ads_meta_ads_currency_not_normalized(self):
        """Google Ads + Meta Ads — cost_micros sem /1M com spend — deve falhar."""
        sql = """
        WITH gads AS (
            SELECT segments_date AS dt, SUM(metrics_cost_micros) AS cost
            FROM `proj.ds_gads.ads_CampaignStats_*`
            WHERE _TABLE_SUFFIX BETWEEN '20240101' AND '20240131'
            GROUP BY 1
        ),
        meta AS (
            SELECT date_start AS dt, SUM(spend) AS cost
            FROM `proj.ds_meta.meta_ads_insights_campaign_*`
            WHERE _TABLE_SUFFIX BETWEEN '20240101' AND '20240131'
            GROUP BY 1
        )
        SELECT g.dt, g.cost AS gads_cost, m.cost AS meta_cost
        FROM gads g JOIN meta m ON g.dt = m.dt
        """
        failed = _check_ids(run_checks(sql, "google_ads", is_cross_source=True))
        assert "cross_source_currency" in failed

    def test_32_ga4_google_ads_full_dashboard_correct(self):
        """Dashboard completo: GA4 sessoes + Google Ads custo + conversoes, tudo alinhado."""
        sql = """
        WITH ga4_daily AS (
            SELECT
                PARSE_DATE('%Y%m%d', event_date) AS dt,
                COUNT(DISTINCT user_pseudo_id) AS users,
                COUNT(DISTINCT CONCAT(user_pseudo_id, CAST((SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_id') AS STRING))) AS sessions,
                COUNTIF(event_name = 'purchase') AS ga4_purchases
            FROM `proj.ds_ga4.events_*`
            WHERE _TABLE_SUFFIX BETWEEN '20240101' AND '20240131'
            GROUP BY 1
        ),
        gads_daily AS (
            SELECT
                segments_date AS dt,
                SUM(metrics_impressions) AS impressions,
                SUM(metrics_clicks) AS clicks,
                SUM(metrics_cost_micros) / 1000000 AS cost,
                SUM(metrics_conversions) AS conversions
            FROM `proj.ds_gads.ads_CampaignStats_*`
            WHERE _TABLE_SUFFIX BETWEEN '20240101' AND '20240131'
            GROUP BY 1
        )
        SELECT
            g.dt,
            g.users,
            g.sessions,
            a.impressions,
            a.clicks,
            a.cost,
            a.conversions AS gads_conversions,
            g.ga4_purchases,
            SAFE_DIVIDE(a.cost, NULLIF(a.conversions, 0)) AS cpa,
            SAFE_DIVIDE(a.clicks, NULLIF(a.impressions, 0)) AS ctr
        FROM ga4_daily g
        JOIN gads_daily a ON g.dt = a.dt
        ORDER BY g.dt
        """
        results = run_checks(sql, "ga4_bigquery", is_cross_source=True)
        assert _all_passed(results), f"Falhas: {_check_ids(results)}"

    def test_33_cross_source_skips_join_key_match(self):
        """Cross-source: join_key_match deve ser pulado (skip_cross_source=True)."""
        sql = """
        SELECT e.event_date, s.segments_date
        FROM `proj.ds.events_*` e
        JOIN `proj.ds.ads_CampaignStats_*` s ON e.event_date = s.segments_date
        """
        results = run_checks(sql, "ga4_bigquery", is_cross_source=True)
        ids = {r["id"] for r in results}
        assert "join_key_match" not in ids


# ═══════════════════════════════════════════════════════════════════════════
# CENARIOS COMBINADOS — multiplos erros em uma query
# ═══════════════════════════════════════════════════════════════════════════

class TestMultipleErrorScenarios:
    """Queries com multiplos problemas simultaneos."""

    def test_34_google_ads_all_wrong(self):
        """Google Ads: JOIN sem dedup + cost sem conversao + CPA sem NULLIF + chave errada."""
        sql = """
        SELECT
            c.campaign_name,
            SUM(s.metrics_cost_micros) AS cost,
            SUM(s.metrics_cost_micros) / SUM(s.metrics_conversions) AS cpa
        FROM `proj.ds.ads_CampaignStats_*` s
        JOIN `proj.ds.ads_Campaign_*` c ON s.random_field = c.random_field
        GROUP BY 1
        """
        failed = _check_ids(run_checks(sql, "google_ads"))
        assert "cost_micros_conversion" in failed
        assert "nullif_division" in failed
        assert "join_key_match" in failed
        assert "table_suffix" in failed  # wildcard sem _TABLE_SUFFIX

    def test_35_meta_ads_all_wrong(self):
        """Meta Ads: spend/1M + purchase sem UNNEST + clicks generico pra CTR."""
        sql = """
        SELECT
            campaign_id,
            SUM(spend) / 1000000 AS cost,
            purchase AS conversions,
            clicks / impressions AS ctr
        FROM `proj.ds.meta_ads_insights_campaign_*`
        GROUP BY 1
        """
        failed = _check_ids(run_checks(sql, "meta_ads"))
        assert "spend_no_micros" in failed
        assert "unnest_actions" in failed
        assert "link_clicks_vs_clicks" in failed

    def test_36_ga4_all_wrong(self):
        """GA4: page_location sem UNNEST + user_id inventado + sem _TABLE_SUFFIX."""
        sql = """
        SELECT
            event_date,
            page_location,
            COUNT(DISTINCT user_id) AS users
        FROM `proj.ds.events_*`
        GROUP BY 1, 2
        """
        failed = _check_ids(run_checks(sql, "ga4_bigquery"))
        assert "unnest_event_params" in failed
        assert "user_pseudo_id" in failed
        assert "table_suffix" in failed
