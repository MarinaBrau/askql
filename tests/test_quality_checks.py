"""Testes para validation/quality_checks.py — 15 check functions + run_checks()."""

from validation.quality_checks import (
    check_table_suffix,
    check_unnest_event_params,
    check_unnest_items,
    check_user_pseudo_id,
    check_ga_session_id_from_params,
    check_spend_no_micros,
    check_unnest_actions,
    check_link_clicks_vs_clicks,
    check_cost_micros_conversion,
    check_nullif_division,
    check_row_number_dedup,
    check_join_key_match,
    check_join_dedup_required,
    check_cross_source_date_alignment,
    check_cross_source_currency,
    check_vtex_dt_filter,
    check_vtex_prices_not_divided,
    check_vtex_invoiced_status,
    check_shopify_dt_filter,
    check_shopify_financial_status,
    run_checks,
)


# ── GA4 checks ──────────────────────────────────────────────────────────────

class TestCheckTableSuffix:
    def test_pass_with_suffix(self):
        sql = "SELECT * FROM `p.d.events_*` WHERE _TABLE_SUFFIX BETWEEN '20240101' AND '20240131'"
        passed, _ = check_table_suffix(sql, "ga4_bigquery")
        assert passed is True

    def test_fail_without_suffix(self):
        sql = "SELECT * FROM `p.d.events_*`"
        passed, _ = check_table_suffix(sql, "ga4_bigquery")
        assert passed is False

    def test_na_no_wildcard(self):
        sql = "SELECT * FROM `p.d.some_table` WHERE 1=1"
        passed, detail = check_table_suffix(sql, "ga4_bigquery")
        assert passed is True
        assert "N/A" in detail


class TestCheckUnnestEventParams:
    def test_pass_with_unnest(self, sample_ga4_sql_with_unnest):
        passed, _ = check_unnest_event_params(sample_ga4_sql_with_unnest, "ga4_bigquery")
        assert passed is True

    def test_fail_without_unnest(self):
        sql = "SELECT event_date, page_location FROM `p.d.events_*`"
        passed, _ = check_unnest_event_params(sql, "ga4_bigquery")
        assert passed is False

    def test_na_not_ga4(self):
        sql = "SELECT * FROM table"
        passed, detail = check_unnest_event_params(sql, "google_ads")
        assert passed is True
        assert "N/A" in detail

    def test_na_no_params_access(self):
        sql = "SELECT event_date, event_name FROM `p.d.events_*`"
        passed, _ = check_unnest_event_params(sql, "ga4_bigquery")
        assert passed is True


class TestCheckUnnestItems:
    def test_pass_with_unnest(self):
        sql = """
        SELECT item_name, COUNT(*) FROM `p.d.events_*`,
        UNNEST(items) AS item WHERE event_name = 'purchase'
        GROUP BY 1
        """
        passed, _ = check_unnest_items(sql, "ga4_bigquery")
        assert passed is True

    def test_fail_without_unnest(self):
        sql = "SELECT item_name FROM `p.d.events_*` WHERE event_name = 'purchase'"
        passed, _ = check_unnest_items(sql, "ga4_bigquery")
        assert passed is False

    def test_na_not_ga4(self):
        passed, detail = check_unnest_items("SELECT * FROM t", "meta_ads")
        assert passed is True
        assert "N/A" in detail


class TestCheckUserPseudoId:
    def test_pass_with_pseudo_id(self):
        sql = "SELECT COUNT(DISTINCT user_pseudo_id) AS users FROM `p.d.events_*`"
        passed, _ = check_user_pseudo_id(sql, "ga4_bigquery")
        assert passed is True

    def test_fail_without_pseudo_id(self):
        sql = "SELECT COUNT(DISTINCT user_id) AS users FROM `p.d.events_*`"
        passed, _ = check_user_pseudo_id(sql, "ga4_bigquery")
        assert passed is False

    def test_na_not_ga4(self):
        passed, _ = check_user_pseudo_id("SELECT * FROM t", "google_ads")
        assert passed is True


class TestCheckGaSessionIdFromParams:
    def test_pass_subquery_pattern(self):
        sql = """
        SELECT (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_id') AS session_id
        FROM `p.d.events_*`
        """
        passed, _ = check_ga_session_id_from_params(sql, "ga4_bigquery")
        assert passed is True

    def test_fail_direct_access(self):
        sql = "SELECT ga_session_id FROM `p.d.events_*`"
        passed, _ = check_ga_session_id_from_params(sql, "ga4_bigquery")
        assert passed is False

    def test_na_no_session_ref(self):
        sql = "SELECT event_date, event_name FROM `p.d.events_*`"
        passed, _ = check_ga_session_id_from_params(sql, "ga4_bigquery")
        assert passed is True


# ── Meta Ads checks ─────────────────────────────────────────────────────────

class TestCheckSpendNoMicros:
    def test_pass_no_division(self):
        sql = "SELECT date_start, spend FROM `p.d.meta_ads_campaigns`"
        passed, _ = check_spend_no_micros(sql, "meta_ads")
        assert passed is True

    def test_fail_divides_by_million(self):
        sql = "SELECT date_start, spend / 1000000 AS cost FROM `p.d.meta_ads_campaigns`"
        passed, _ = check_spend_no_micros(sql, "meta_ads")
        assert passed is False

    def test_na_not_meta(self):
        passed, _ = check_spend_no_micros("SELECT spend FROM t", "google_ads")
        assert passed is True


class TestCheckUnnestActions:
    def test_pass_with_unnest(self, sample_meta_ads_sql):
        passed, _ = check_unnest_actions(sample_meta_ads_sql, "meta_ads")
        assert passed is True

    def test_fail_without_unnest(self):
        sql = "SELECT date_start, purchase FROM `p.d.meta_ads_campaigns`"
        passed, _ = check_unnest_actions(sql, "meta_ads")
        assert passed is False

    def test_na_no_actions(self):
        sql = "SELECT date_start, spend FROM `p.d.meta_ads_campaigns`"
        passed, _ = check_unnest_actions(sql, "meta_ads")
        assert passed is True


class TestCheckLinkClicksVsClicks:
    def test_pass_with_link_clicks(self):
        sql = "SELECT link_clicks / impressions AS ctr FROM `p.d.meta_ads_campaigns`"
        passed, _ = check_link_clicks_vs_clicks(sql, "meta_ads")
        assert passed is True

    def test_fail_with_generic_clicks(self):
        sql = "SELECT clicks / impressions AS ctr FROM `p.d.meta_ads_campaigns`"
        passed, _ = check_link_clicks_vs_clicks(sql, "meta_ads")
        assert passed is False

    def test_na_no_ctr(self):
        sql = "SELECT date_start, spend FROM `p.d.meta_ads_campaigns`"
        passed, _ = check_link_clicks_vs_clicks(sql, "meta_ads")
        assert passed is True


# ── Google Ads checks ───────────────────────────────────────────────────────

class TestCheckCostMicrosConversion:
    def test_pass_with_division(self, sample_google_ads_sql):
        passed, _ = check_cost_micros_conversion(sample_google_ads_sql, "google_ads")
        assert passed is True

    def test_fail_without_division(self):
        sql = "SELECT segments_date, metrics_cost_micros FROM `p.d.ads_CampaignStats_*`"
        passed, _ = check_cost_micros_conversion(sql, "google_ads")
        assert passed is False

    def test_na_no_cost_micros(self):
        sql = "SELECT segments_date, metrics_impressions FROM `p.d.ads_CampaignStats_*`"
        passed, _ = check_cost_micros_conversion(sql, "google_ads")
        assert passed is True


class TestCheckNullifDivision:
    def test_pass_with_nullif(self, sample_google_ads_sql):
        passed, _ = check_nullif_division(sample_google_ads_sql, "google_ads")
        assert passed is True

    def test_fail_without_nullif(self):
        sql = "SELECT metrics_clicks / metrics_impressions AS ctr FROM `p.d.ads_CampaignStats_*`"
        passed, _ = check_nullif_division(sql, "google_ads")
        assert passed is False

    def test_na_not_ads_source(self):
        passed, _ = check_nullif_division("SELECT ctr FROM t", "ga4_bigquery")
        assert passed is True


class TestCheckRowNumberDedup:
    def test_pass_with_row_number(self):
        sql = """
        WITH campaign_latest AS (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY campaign_id ORDER BY _TABLE_SUFFIX DESC) AS rn
            FROM `p.d.ads_Campaign_*`
        )
        SELECT * FROM campaign_latest WHERE rn = 1
        """
        passed, _ = check_row_number_dedup(sql, "google_ads")
        assert passed is True

    def test_fail_without_row_number(self):
        sql = """
        SELECT s.*, c.campaign_name
        FROM `p.d.ads_CampaignStats_*` s
        JOIN `p.d.ads_Campaign_*` c ON s.campaign_id = c.campaign_id
        """
        passed, _ = check_row_number_dedup(sql, "google_ads")
        assert passed is False

    def test_na_no_config_table(self):
        sql = "SELECT * FROM `p.d.ads_CampaignStats_*`"
        passed, _ = check_row_number_dedup(sql, "google_ads")
        assert passed is True


# ── JOIN checks (Fase A) ───────────────────────────────────────────────────

class TestCheckJoinKeyMatch:
    def test_pass_known_key(self):
        sql = """
        SELECT s.*, c.campaign_name
        FROM `p.d.ads_CampaignStats_*` s
        JOIN `p.d.ads_Campaign_*` c ON s.campaign_id = c.campaign_id
        """
        passed, _ = check_join_key_match(sql, "google_ads")
        assert passed is True

    def test_fail_unknown_key(self):
        sql = """
        SELECT s.*, c.campaign_name
        FROM `p.d.ads_CampaignStats_*` s
        JOIN `p.d.ads_Campaign_*` c ON s.foo_id = c.foo_id
        """
        passed, _ = check_join_key_match(sql, "google_ads")
        assert passed is False

    def test_na_no_join(self):
        sql = "SELECT * FROM `p.d.ads_CampaignStats_*`"
        passed, _ = check_join_key_match(sql, "google_ads")
        assert passed is True

    def test_na_not_ads(self):
        passed, _ = check_join_key_match("SELECT * FROM t", "ga4_bigquery")
        assert passed is True


class TestCheckJoinDedupRequired:
    def test_pass_with_dedup(self):
        sql = """
        WITH campaign_latest AS (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY campaign_id ORDER BY _TABLE_SUFFIX DESC) AS rn
            FROM `p.d.ads_Campaign_*`
        )
        SELECT s.*, c.campaign_name
        FROM `p.d.ads_CampaignStats_*` s
        JOIN campaign_latest c ON s.campaign_id = c.campaign_id
        WHERE c.rn = 1
        """
        passed, _ = check_join_dedup_required(sql, "google_ads")
        assert passed is True

    def test_fail_without_dedup(self):
        sql = """
        SELECT s.*, c.campaign_name
        FROM `p.d.ads_CampaignStats_*` s
        JOIN `p.d.ads_Campaign_*` c ON s.campaign_id = c.campaign_id
        """
        passed, _ = check_join_dedup_required(sql, "google_ads")
        assert passed is False

    def test_na_standalone_query(self):
        sql = "SELECT * FROM `p.d.ads_Campaign_*` WHERE _TABLE_SUFFIX = '20240101'"
        passed, detail = check_join_dedup_required(sql, "google_ads")
        assert passed is True

    def test_na_no_config_table(self):
        sql = "SELECT * FROM `p.d.ads_CampaignStats_*`"
        passed, _ = check_join_dedup_required(sql, "google_ads")
        assert passed is True


# ── Cross-source checks (Fase B) ──────────────────────────────────────────

class TestCheckCrossSourceDateAlignment:
    def test_pass_with_parse_date(self):
        sql = """
        WITH ga4 AS (
            SELECT PARSE_DATE('%Y%m%d', event_date) AS dt FROM `p.d.events_*`
        ),
        gads AS (
            SELECT segments_date AS dt FROM `p.d.ads_CampaignStats_*`
        )
        SELECT * FROM ga4 JOIN gads ON ga4.dt = gads.dt
        """
        passed, _ = check_cross_source_date_alignment(sql, "ga4_bigquery")
        assert passed is True

    def test_fail_no_alignment(self):
        sql = """
        SELECT e.event_date, s.segments_date
        FROM `p.d.events_*` e
        JOIN `p.d.ads_CampaignStats_*` s ON e.event_date = s.segments_date
        """
        passed, _ = check_cross_source_date_alignment(sql, "ga4_bigquery")
        assert passed is False

    def test_na_single_source(self):
        sql = "SELECT * FROM `p.d.events_*`"
        passed, detail = check_cross_source_date_alignment(sql, "ga4_bigquery")
        assert passed is True
        assert "Single source" in detail


class TestCheckCrossSourceCurrency:
    def test_pass_cost_micros_normalized(self):
        sql = """
        SELECT
            metrics_cost_micros / 1000000 AS gads_cost,
            spend AS meta_cost
        FROM gads JOIN meta ON gads.dt = meta.dt
        """
        passed, _ = check_cross_source_currency(sql, "google_ads")
        assert passed is True

    def test_fail_not_normalized(self):
        sql = """
        SELECT
            metrics_cost_micros AS gads_cost,
            spend AS meta_cost
        FROM gads JOIN meta ON gads.dt = meta.dt
        """
        passed, _ = check_cross_source_currency(sql, "google_ads")
        assert passed is False

    def test_na_single_currency_source(self):
        sql = "SELECT spend FROM `p.d.meta_ads_campaigns`"
        passed, detail = check_cross_source_currency(sql, "meta_ads")
        assert passed is True
        assert "N/A" in detail


# ── run_checks() orchestrator ──────────────────────────────────────────────

class TestRunChecks:
    def test_returns_list_of_dicts(self, sample_safe_sql):
        results = run_checks(sample_safe_sql, "ga4_bigquery")
        assert isinstance(results, list)
        assert len(results) > 0
        for r in results:
            assert "id" in r
            assert "name" in r
            assert "passed" in r
            assert "detail" in r

    def test_filters_by_source_ga4(self, sample_safe_sql):
        results = run_checks(sample_safe_sql, "ga4_bigquery")
        ids = {r["id"] for r in results}
        # GA4 checks should be present
        assert "unnest_event_params" in ids
        # Google Ads-only checks should NOT be present
        assert "cost_micros_conversion" not in ids
        # Meta Ads-only checks should NOT be present
        assert "spend_no_micros" not in ids

    def test_filters_by_source_google_ads(self, sample_google_ads_sql):
        results = run_checks(sample_google_ads_sql, "google_ads")
        ids = {r["id"] for r in results}
        assert "cost_micros_conversion" in ids
        assert "unnest_event_params" not in ids

    def test_cross_source_includes_cross_checks(self):
        sql = """
        SELECT PARSE_DATE('%Y%m%d', event_date) AS dt, spend, metrics_cost_micros / 1000000 AS cost
        FROM `p.d.events_*` e
        JOIN `p.d.meta_ads_campaigns` m ON 1=1
        """
        results = run_checks(sql, "ga4_bigquery", is_cross_source=True)
        ids = {r["id"] for r in results}
        assert "cross_source_date_alignment" in ids
        assert "cross_source_currency" in ids

    def test_cross_source_skips_skip_cross_source(self):
        sql = """
        SELECT * FROM `p.d.events_*` e
        JOIN `p.d.ads_CampaignStats_*` s ON e.campaign_id = s.campaign_id
        """
        results = run_checks(sql, "ga4_bigquery", is_cross_source=True)
        ids = {r["id"] for r in results}
        # join_key_match has skip_cross_source=True
        assert "join_key_match" not in ids


# ── VTEX checks ───────────────────────────────────────────────────────────────

class TestCheckVtexDtFilter:
    def test_pass_with_dt_filter(self):
        sql = "SELECT SUM(total_value) FROM `p.vtex_treated.orders_treated` WHERE dt >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY) AND status = 'invoiced'"
        passed, _ = check_vtex_dt_filter(sql, "vtex")
        assert passed is True

    def test_fail_without_dt_filter(self):
        sql = "SELECT SUM(total_value) FROM `p.vtex_treated.orders_treated` WHERE status = 'invoiced'"
        passed, msg = check_vtex_dt_filter(sql, "vtex")
        assert passed is False
        assert "dt" in msg

    def test_na_other_source(self):
        sql = "SELECT * FROM orders_treated WHERE dt >= '2024-01-01'"
        passed, detail = check_vtex_dt_filter(sql, "shopify")
        assert passed is True
        assert "N/A" in detail

    def test_pass_dt_between(self):
        sql = "SELECT * FROM `p.vtex_treated.order_items_treated` WHERE dt BETWEEN '2024-01-01' AND '2024-01-31'"
        passed, _ = check_vtex_dt_filter(sql, "vtex")
        assert passed is True


class TestCheckVtexPricesNotDivided:
    def test_pass_no_division(self):
        sql = "SELECT SUM(total_value) AS receita FROM `p.vtex_treated.orders_treated` WHERE status = 'invoiced'"
        passed, _ = check_vtex_prices_not_divided(sql, "vtex")
        assert passed is True

    def test_fail_divided_by_100(self):
        sql = "SELECT SUM(total_value) / 100 AS receita FROM `p.vtex_treated.orders_treated`"
        passed, msg = check_vtex_prices_not_divided(sql, "vtex")
        assert passed is False
        assert "100" in msg

    def test_na_other_source(self):
        sql = "SELECT total_value / 100 FROM t"
        passed, detail = check_vtex_prices_not_divided(sql, "shopify")
        assert passed is True
        assert "N/A" in detail

    def test_na_no_price_field(self):
        sql = "SELECT order_id, status FROM `p.vtex_treated.orders_treated`"
        passed, detail = check_vtex_prices_not_divided(sql, "vtex")
        assert passed is True
        assert "No VTEX price field" in detail


class TestCheckVtexInvoicedStatus:
    def test_pass_with_invoiced(self):
        sql = "SELECT SUM(total_value) FROM orders_treated WHERE status = 'invoiced' AND dt >= '2024-01-01'"
        passed, _ = check_vtex_invoiced_status(sql, "vtex")
        assert passed is True

    def test_fail_without_invoiced(self):
        sql = "SELECT SUM(total_value) FROM orders_treated WHERE dt >= '2024-01-01'"
        passed, msg = check_vtex_invoiced_status(sql, "vtex")
        assert passed is False
        assert "invoiced" in msg

    def test_na_no_sum(self):
        sql = "SELECT order_id, total_value FROM orders_treated WHERE status = 'invoiced'"
        passed, detail = check_vtex_invoiced_status(sql, "vtex")
        assert passed is True
        assert "No SUM" in detail

    def test_na_other_source(self):
        sql = "SELECT SUM(total_value) FROM t"
        passed, detail = check_vtex_invoiced_status(sql, "ga4_bigquery")
        assert passed is True
        assert "N/A" in detail


# ── Shopify checks ───────────────────────────────────────────────────────────

class TestCheckShopifyDtFilter:
    def test_pass_with_dt_filter(self):
        sql = "SELECT SUM(total_price) FROM `p.shopify_treated.orders_treated` WHERE dt >= '2024-01-01' AND financial_status = 'paid'"
        passed, _ = check_shopify_dt_filter(sql, "shopify")
        assert passed is True

    def test_fail_without_dt_filter(self):
        sql = "SELECT SUM(total_price) FROM `p.shopify_treated.orders_treated` WHERE financial_status = 'paid'"
        passed, msg = check_shopify_dt_filter(sql, "shopify")
        assert passed is False
        assert "dt" in msg

    def test_na_other_source(self):
        sql = "SELECT * FROM orders_treated WHERE financial_status = 'paid'"
        passed, detail = check_shopify_dt_filter(sql, "vtex")
        assert passed is True
        assert "N/A" in detail

    def test_pass_dt_equals(self):
        sql = "SELECT * FROM `p.shopify_treated.customers_treated` WHERE dt = (SELECT MAX(dt) FROM `p.shopify_treated.customers_treated`)"
        passed, _ = check_shopify_dt_filter(sql, "shopify")
        assert passed is True


class TestCheckShopifyFinancialStatus:
    def test_pass_with_paid_filter(self):
        sql = "SELECT SUM(total_price) FROM orders_treated WHERE financial_status = 'paid' AND dt >= '2024-01-01'"
        passed, _ = check_shopify_financial_status(sql, "shopify")
        assert passed is True

    def test_fail_without_paid_filter(self):
        sql = "SELECT SUM(total_price) FROM orders_treated WHERE dt >= '2024-01-01'"
        passed, msg = check_shopify_financial_status(sql, "shopify")
        assert passed is False
        assert "paid" in msg

    def test_na_no_sum(self):
        sql = "SELECT order_id, total_price FROM orders_treated WHERE financial_status = 'paid'"
        passed, detail = check_shopify_financial_status(sql, "shopify")
        assert passed is True
        assert "No SUM" in detail

    def test_na_other_source(self):
        sql = "SELECT SUM(total_price) FROM t"
        passed, detail = check_shopify_financial_status(sql, "vtex")
        assert passed is True
        assert "N/A" in detail
