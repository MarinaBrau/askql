"""8 automated quality checks for generated SQL, based on gotchas from schemas."""

import re


def _normalize(sql):
    """Remove SQL comments and normalize whitespace for pattern matching."""
    # Remove single-line comments
    sql = re.sub(r"--.*$", "", sql, flags=re.MULTILINE)
    # Remove multi-line comments
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    return sql


# ---------------------------------------------------------------------------
# Individual checks — each returns (passed: bool, detail: str)
# ---------------------------------------------------------------------------

def check_table_suffix(sql, source):
    """Both GA4 and Google Ads wildcard tables require _TABLE_SUFFIX for date filtering."""
    norm = _normalize(sql)
    # Only applies if there's a wildcard table reference (table_*)
    if not re.search(r"\w+_\*", norm):
        return True, "No wildcard table found (check N/A)"
    has_suffix = bool(re.search(r"_TABLE_SUFFIX", norm, re.IGNORECASE))
    if has_suffix:
        return True, "Uses _TABLE_SUFFIX for date filtering"
    return False, "MISSING _TABLE_SUFFIX — wildcard table without partition filter causes full scan"


def check_unnest_event_params(sql, source):
    """GA4: queries accessing event_params must use UNNEST(event_params)."""
    if source != "ga4_bigquery":
        return True, "N/A (not GA4)"
    norm = _normalize(sql)
    # Check if query references event_params-related fields
    needs_unnest = bool(re.search(
        r"event_params|page_location|ga_session_id|ga_session_number|engagement_time|source.*medium|session_engaged",
        norm, re.IGNORECASE,
    ))
    if not needs_unnest:
        return True, "No event_params access detected"
    has_unnest = bool(re.search(r"UNNEST\s*\(\s*event_params\s*\)", norm, re.IGNORECASE))
    if has_unnest:
        return True, "Correctly uses UNNEST(event_params)"
    return False, "MISSING UNNEST(event_params) — event_params is ARRAY, requires UNNEST"


def check_unnest_items(sql, source):
    """GA4 e-commerce: queries accessing items must use UNNEST(items)."""
    if source != "ga4_bigquery":
        return True, "N/A (not GA4)"
    norm = _normalize(sql)
    needs_unnest = bool(re.search(
        r"item_name|item_category|item_revenue|item_id|item_brand|item\.|\bUNNEST\s*\(\s*items\s*\)",
        norm, re.IGNORECASE,
    ))
    if not needs_unnest:
        return True, "No items access detected"
    has_unnest = bool(re.search(r"UNNEST\s*\(\s*items\s*\)", norm, re.IGNORECASE))
    if has_unnest:
        return True, "Correctly uses UNNEST(items)"
    return False, "MISSING UNNEST(items) — items is ARRAY, requires UNNEST for e-commerce"


def check_user_pseudo_id(sql, source):
    """GA4: user counts should use user_pseudo_id, not invented user_id."""
    if source != "ga4_bigquery":
        return True, "N/A (not GA4)"
    norm = _normalize(sql)
    # Check if query seems to count users
    counts_users = bool(re.search(r"user|usuario|sessao|session", norm, re.IGNORECASE))
    if not counts_users:
        return True, "No user counting detected"
    has_pseudo = bool(re.search(r"user_pseudo_id", norm, re.IGNORECASE))
    if has_pseudo:
        return True, "Correctly uses user_pseudo_id"
    # It might not need user_pseudo_id for all user-related queries
    return False, "WARNING: user-related query without user_pseudo_id — may use invented field"


def check_ga_session_id_from_params(sql, source):
    """GA4: ga_session_id must be extracted from event_params, not accessed directly."""
    if source != "ga4_bigquery":
        return True, "N/A (not GA4)"
    norm = _normalize(sql)
    # Only check if session_id is mentioned
    if not re.search(r"ga_session_id|session_id", norm, re.IGNORECASE):
        return True, "No session_id reference detected"
    # Check it comes from UNNEST, not direct access
    correct = bool(re.search(
        r"UNNEST\s*\(\s*event_params\s*\).*ga_session_id|ga_session_id.*UNNEST\s*\(\s*event_params\s*\)",
        norm, re.IGNORECASE | re.DOTALL,
    ))
    # Also accept the subquery pattern: (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_id')
    correct_subquery = bool(re.search(
        r"FROM\s+UNNEST\s*\(\s*event_params\s*\).*key\s*=\s*'ga_session_id'",
        norm, re.IGNORECASE | re.DOTALL,
    ))
    if correct or correct_subquery:
        return True, "Correctly extracts ga_session_id from event_params"
    return False, "ga_session_id accessed directly — must extract from event_params via UNNEST"


def check_spend_no_micros(sql, source):
    """Meta Ads: spend must NOT be divided by 1000000 (already in real currency)."""
    if source != "meta_ads":
        return True, "N/A (not Meta Ads)"
    norm = _normalize(sql)
    if not re.search(r"\bspend\b", norm, re.IGNORECASE):
        return True, "No spend reference detected"
    divides_by_million = bool(re.search(
        r"spend\s*/\s*1[0_,.]?000[_,.]?000|spend\s*/\s*1e6|spend\s*\)\s*/\s*1[0_,.]?000[_,.]?000|spend\s*\)\s*/\s*1e6",
        norm, re.IGNORECASE,
    ))
    if divides_by_million:
        return False, "WRONG: dividing spend by 1M — Meta Ads spend is already in real currency!"
    return True, "Correctly uses spend without micros conversion"


def check_unnest_actions(sql, source):
    """Meta Ads: queries accessing conversions must use UNNEST(actions)."""
    if source != "meta_ads":
        return True, "N/A (not Meta Ads)"
    norm = _normalize(sql)
    # Check if query references conversion-related terms
    needs_unnest = bool(re.search(
        r"action_type|purchase|lead|add_to_cart|initiate_checkout|complete_registration|landing_page_view",
        norm, re.IGNORECASE,
    ))
    if not needs_unnest:
        return True, "No actions/conversions access detected"
    has_unnest = bool(re.search(r"UNNEST\s*\(\s*actions\s*\)|UNNEST\s*\(\s*action_values\s*\)", norm, re.IGNORECASE))
    if has_unnest:
        return True, "Correctly uses UNNEST(actions) or UNNEST(action_values)"
    return False, "MISSING UNNEST(actions) — actions is ARRAY, requires UNNEST for conversions"


def check_link_clicks_vs_clicks(sql, source):
    """Meta Ads: CTR should use link_clicks, not clicks (which includes likes/comments)."""
    if source != "meta_ads":
        return True, "N/A (not Meta Ads)"
    norm = _normalize(sql)
    # Only check if query calculates CTR
    calculates_ctr = bool(re.search(
        r"\bctr\b|click.*\/.*impress|click.*\*.*100.*impress",
        norm, re.IGNORECASE,
    ))
    if not calculates_ctr:
        return True, "No CTR calculation detected"
    has_link_clicks = bool(re.search(r"\blink_clicks\b", norm, re.IGNORECASE))
    if has_link_clicks:
        return True, "Correctly uses link_clicks for CTR"
    return False, "WARNING: CTR calculated with clicks (includes likes/comments) — consider using link_clicks"


def check_cost_micros_conversion(sql, source):
    """Google Ads: cost_micros must be divided by 1000000."""
    if source != "google_ads":
        return True, "N/A (not Google Ads)"
    norm = _normalize(sql)
    if not re.search(r"cost_micros", norm, re.IGNORECASE):
        return True, "No cost_micros reference detected"
    has_division = bool(re.search(
        r"cost_micros\s*/\s*1[0_,.]?000[_,.]?000|cost_micros\s*/\s*1e6|cost_micros\s*\)\s*/\s*1[0_,.]?000[_,.]?000|cost_micros\s*\)\s*/\s*1e6",
        norm, re.IGNORECASE,
    ))
    if has_division:
        return True, "Correctly divides cost_micros by 1000000"
    return False, "MISSING cost_micros conversion — values will be 1M times larger than real!"


def check_nullif_division(sql, source):
    """Google Ads / Meta Ads: CPA/ROAS/CTR calculations must use NULLIF to avoid division by zero."""
    if source not in ("google_ads", "meta_ads"):
        return True, "N/A (not Google Ads or Meta Ads)"
    norm = _normalize(sql)
    # Check if there's a division that looks like a ratio calculation
    has_ratio = bool(re.search(
        r"\b(CPA|ROAS|CTR|CPC|CPM|cpa|roas|ctr|cpc|cpm)\b|cost.*\/.*conver|conver.*\/.*cost|click.*\/.*impress|cost.*\/.*click",
        norm, re.IGNORECASE,
    ))
    if not has_ratio:
        return True, "No ratio calculation detected"
    has_nullif = bool(re.search(r"NULLIF\s*\(", norm, re.IGNORECASE))
    if has_nullif:
        return True, "Correctly uses NULLIF for safe division"
    return False, "MISSING NULLIF — ratio calculation without division-by-zero protection"


def check_row_number_dedup(sql, source):
    """Google Ads: JOINs with config tables (Campaign, AdGroup) must dedup with ROW_NUMBER."""
    if source != "google_ads":
        return True, "N/A (not Google Ads)"
    norm = _normalize(sql)
    # Check if query JOINs with a config table
    joins_config = bool(re.search(
        r"ads_Campaign_\*|ads_AdGroup_\*|ads_Campaign[^S]|ads_AdGroup[^S]",
        norm, re.IGNORECASE,
    ))
    if not joins_config:
        return True, "No config table JOIN detected"
    # Only require dedup if there's a JOIN (standalone config table queries don't need it)
    has_join = bool(re.search(r"\bJOIN\b", norm, re.IGNORECASE))
    if not has_join:
        return True, "Config table used without JOIN (standalone query)"
    has_dedup = bool(re.search(r"ROW_NUMBER\s*\(\s*\)", norm, re.IGNORECASE))
    if has_dedup:
        return True, "Correctly uses ROW_NUMBER to deduplicate config table"
    return False, "MISSING ROW_NUMBER dedup — JOIN with config table will inflate metrics!"


def check_join_key_match(sql, source):
    """Google Ads / Meta Ads: JOINs should use known join keys (campaign_id, ad_group_id, etc.)."""
    if source not in ("google_ads", "meta_ads"):
        return True, "N/A (not Google Ads or Meta Ads)"
    norm = _normalize(sql)
    # Find JOIN ... ON clauses
    # Use \b before terminators to avoid matching inside field names (e.g., ad_group_id contains "GROUP")
    joins = re.findall(r"JOIN\s+[`\w.*]+\s+\w+\s+ON\s+(.+?)(?:\bWHERE\b|\bGROUP\b|\bORDER\b|\bLIMIT\b|\bJOIN\b|\bLEFT\b|\bRIGHT\b|\bINNER\b|\bCROSS\b|$)", norm, re.IGNORECASE | re.DOTALL)
    if not joins:
        return True, "No JOIN detected"
    # Known valid join keys per source
    valid_keys = {
        "google_ads": {"campaign_id", "ad_group_id", "ad_id", "customer_id", "keyword_id"},
        "meta_ads": {"campaign_id", "adset_id", "ad_id", "account_id", "id"},
    }
    keys = valid_keys.get(source, set())
    for join_clause in joins:
        # Extract field names from ON clause (look for word.word or just word around = sign)
        on_fields = re.findall(r"(\w+)\.(\w+)", join_clause)
        field_names = {f[1] for f in on_fields}
        # Check if at least one known key is used
        if field_names and not field_names & keys:
            return False, f"JOIN uses unknown keys ({', '.join(field_names)}) — expected one of: {', '.join(sorted(keys))}"
    return True, "JOIN uses known join keys"


def check_join_dedup_required(sql, source):
    """Google Ads: JOINs with config tables (Campaign_*, AdGroup_*) must use ROW_NUMBER dedup."""
    if source != "google_ads":
        return True, "N/A (not Google Ads)"
    norm = _normalize(sql)
    # Config tables that require dedup
    config_tables = [
        (r"ads_Campaign_\*|ads_Campaign_[`\s]", "ads_Campaign_*"),
        (r"ads_AdGroup_\*|ads_AdGroup_[`\s]", "ads_AdGroup_*"),
    ]
    tables_found = []
    for pattern, name in config_tables:
        if re.search(pattern, norm, re.IGNORECASE):
            tables_found.append(name)
    if not tables_found:
        return True, "No config table reference detected"
    # Check if there's a JOIN (not just a standalone query on config table)
    has_join = bool(re.search(r"\bJOIN\b", norm, re.IGNORECASE))
    if not has_join:
        return True, "Config table used without JOIN (standalone query)"
    # Check if ROW_NUMBER is present for dedup
    has_dedup = bool(re.search(r"ROW_NUMBER\s*\(\s*\)", norm, re.IGNORECASE))
    if has_dedup:
        return True, f"Correctly deduplicates config table(s) with ROW_NUMBER: {', '.join(tables_found)}"
    return False, f"MISSING ROW_NUMBER dedup — JOIN with {', '.join(tables_found)} will inflate metrics (config tables have daily snapshots)"


def check_cross_source_date_alignment(sql, source):
    """Cross-source: queries combining sources must align date formats (PARSE_DATE, CAST AS DATE, etc.)."""
    norm = _normalize(sql)
    # Check if query references tables from multiple sources (heuristic: two different dataset patterns)
    has_ga4 = bool(re.search(r"events_\*|event_date|event_name", norm, re.IGNORECASE))
    has_gads = bool(re.search(r"ads_Campaign|ads_AdGroup|ads_Ad|ads_Keyword|segments_date", norm, re.IGNORECASE))
    has_meta = bool(re.search(r"meta_ads_|date_start", norm, re.IGNORECASE))

    source_count = sum([has_ga4, has_gads, has_meta])
    if source_count < 2:
        return True, "Single source detected (check N/A)"

    # If GA4 is not involved, both Google Ads and Meta Ads use YYYY-MM-DD — no alignment needed
    if not has_ga4:
        return True, "Non-GA4 sources use compatible date formats (YYYY-MM-DD)"

    # Check for date alignment functions (needed when GA4 YYYYMMDD is mixed with other sources)
    has_alignment = bool(re.search(
        r"PARSE_DATE|FORMAT_DATE|CAST\s*\(.+\s+AS\s+DATE\s*\)|DATE\s*\(",
        norm, re.IGNORECASE,
    ))
    if has_alignment:
        return True, "Correctly aligns date formats across sources"
    return False, "MISSING date alignment — cross-source query without PARSE_DATE/FORMAT_DATE/CAST AS DATE (GA4 uses YYYYMMDD, others use YYYY-MM-DD)"


def check_cross_source_currency(sql, source):
    """Cross-source: if query uses both cost_micros (Google Ads) and spend (Meta Ads), cost_micros must be normalized."""
    norm = _normalize(sql)
    has_cost_micros = bool(re.search(r"cost_micros", norm, re.IGNORECASE))
    has_spend = bool(re.search(r"\bspend\b", norm, re.IGNORECASE))

    if not (has_cost_micros and has_spend):
        return True, "Not mixing currency sources (check N/A)"

    # Check if cost_micros is divided by 1M
    has_conversion = bool(re.search(
        r"cost_micros\s*/\s*1[0_,.]?000[_,.]?000|cost_micros\s*/\s*1e6|cost_micros\s*\)\s*/\s*1[0_,.]?000[_,.]?000|cost_micros\s*\)\s*/\s*1e6",
        norm, re.IGNORECASE,
    ))
    if has_conversion:
        return True, "Correctly normalizes cost_micros to same currency as spend"
    return False, "MISSING currency normalization — cost_micros (Google Ads) and spend (Meta Ads) in same query without /1000000 conversion"


def check_vtex_dt_filter(sql, source):
    """VTEX: queries on VTEX tables must use `dt` column for partition pruning."""
    if source != "vtex":
        return True, "N/A (not VTEX)"
    norm = _normalize(sql)
    vtex_tables = [
        "orders_treated", "order_items_treated",
        "catalog_treated", "categories_treated", "coupons_treated",
    ]
    references_vtex_table = any(
        re.search(r"\b" + re.escape(t) + r"\b", norm, re.IGNORECASE)
        for t in vtex_tables
    )
    if not references_vtex_table:
        return True, "No VTEX table reference detected"
    has_dt_filter = bool(re.search(
        r"\bdt\b\s*(=|BETWEEN|>=|<=|>|<|IN\s*\()",
        norm, re.IGNORECASE,
    ))
    if has_dt_filter:
        return True, "Correctly uses `dt` column for partition pruning"
    return False, "MISSING `dt` filter — VTEX tables are partitioned by `dt`, omitting it causes full table scan"


def check_vtex_prices_not_divided(sql, source):
    """VTEX: total_value/price fields must NOT be divided by 100 (already in BRL)."""
    if source != "vtex":
        return True, "N/A (not VTEX)"
    norm = _normalize(sql)
    price_fields = ["total_value", "selling_price", "list_price", "base_price", "cost_price"]
    references_price = any(
        re.search(r"\b" + re.escape(f) + r"\b", norm, re.IGNORECASE)
        for f in price_fields
    )
    if not references_price:
        return True, "No VTEX price field reference detected"
    # Detect /100 anywhere in the SQL when a price field is also present.
    # Catches both `total_value / 100` and `SUM(total_value) / 100`.
    divides_by_100 = bool(re.search(r"/\s*100\b", norm, re.IGNORECASE))
    if divides_by_100:
        return False, "WRONG: dividing VTEX price field by 100 — prices are already in BRL (not centavos)!"
    return True, "Correctly uses VTEX price fields without /100 conversion"


def check_vtex_invoiced_status(sql, source):
    """VTEX: SUM(total_value) for revenue must filter status = 'invoiced'."""
    if source != "vtex":
        return True, "N/A (not VTEX)"
    norm = _normalize(sql)
    has_sum_total = bool(re.search(r"SUM\s*\(\s*total_value\s*\)", norm, re.IGNORECASE))
    if not has_sum_total:
        return True, "No SUM(total_value) detected"
    has_invoiced_filter = bool(re.search(
        r"status\s*=\s*'invoiced'",
        norm, re.IGNORECASE,
    ))
    if has_invoiced_filter:
        return True, "Correctly filters status = 'invoiced' before summing revenue"
    return False, "MISSING status = 'invoiced' filter — SUM(total_value) without invoiced filter includes cancelled/pending orders"


def check_shopify_dt_filter(sql, source):
    """Shopify: queries on Shopify tables must use `dt` column for partition pruning."""
    if source != "shopify":
        return True, "N/A (not Shopify)"
    norm = _normalize(sql)
    shopify_tables = [
        "orders_treated", "order_items_treated", "products_treated", "customers_treated",
    ]
    references_shopify_table = any(
        re.search(r"\b" + re.escape(t) + r"\b", norm, re.IGNORECASE)
        for t in shopify_tables
    )
    if not references_shopify_table:
        return True, "No Shopify table reference detected"
    has_dt_filter = bool(re.search(
        r"\bdt\b\s*(=|BETWEEN|>=|<=|>|<|IN\s*\()",
        norm, re.IGNORECASE,
    ))
    if has_dt_filter:
        return True, "Correctly uses `dt` column for partition pruning"
    return False, "MISSING `dt` filter — Shopify tables are partitioned by `dt`, omitting it causes full table scan"


def check_shopify_financial_status(sql, source):
    """Shopify: SUM(total_price) for revenue must filter financial_status = 'paid'."""
    if source != "shopify":
        return True, "N/A (not Shopify)"
    norm = _normalize(sql)
    has_sum_total = bool(re.search(r"SUM\s*\(\s*total_price\s*\)", norm, re.IGNORECASE))
    if not has_sum_total:
        return True, "No SUM(total_price) detected"
    has_paid_filter = bool(re.search(
        r"financial_status\s*=\s*'paid'",
        norm, re.IGNORECASE,
    ))
    if has_paid_filter:
        return True, "Correctly filters financial_status = 'paid' before summing revenue"
    return False, "MISSING financial_status = 'paid' filter — SUM(total_price) without paid filter includes pending/refunded orders"


# ---------------------------------------------------------------------------
# Registry: all checks with metadata
# ---------------------------------------------------------------------------

ALL_CHECKS = [
    {
        "id": "table_suffix",
        "name": "_TABLE_SUFFIX for date filtering",
        "applies_to": ["ga4_bigquery", "google_ads", "meta_ads"],
        "fn": check_table_suffix,
    },
    {
        "id": "unnest_event_params",
        "name": "UNNEST(event_params) for GA4",
        "applies_to": ["ga4_bigquery"],
        "fn": check_unnest_event_params,
    },
    {
        "id": "unnest_items",
        "name": "UNNEST(items) for GA4 e-commerce",
        "applies_to": ["ga4_bigquery"],
        "fn": check_unnest_items,
    },
    {
        "id": "user_pseudo_id",
        "name": "user_pseudo_id for GA4 users",
        "applies_to": ["ga4_bigquery"],
        "fn": check_user_pseudo_id,
    },
    {
        "id": "ga_session_id_from_params",
        "name": "ga_session_id from event_params",
        "applies_to": ["ga4_bigquery"],
        "fn": check_ga_session_id_from_params,
    },
    {
        "id": "cost_micros_conversion",
        "name": "cost_micros / 1000000",
        "applies_to": ["google_ads"],
        "fn": check_cost_micros_conversion,
    },
    {
        "id": "nullif_division",
        "name": "NULLIF for safe division",
        "applies_to": ["google_ads", "meta_ads"],
        "fn": check_nullif_division,
    },
    {
        "id": "spend_no_micros",
        "name": "spend NOT divided by 1M (Meta Ads)",
        "applies_to": ["meta_ads"],
        "fn": check_spend_no_micros,
    },
    {
        "id": "unnest_actions",
        "name": "UNNEST(actions) for Meta Ads conversions",
        "applies_to": ["meta_ads"],
        "fn": check_unnest_actions,
    },
    {
        "id": "link_clicks_vs_clicks",
        "name": "link_clicks for CTR (Meta Ads)",
        "applies_to": ["meta_ads"],
        "fn": check_link_clicks_vs_clicks,
    },
    {
        "id": "row_number_dedup",
        "name": "ROW_NUMBER dedup for config tables",
        "applies_to": ["google_ads"],
        "fn": check_row_number_dedup,
    },
    {
        "id": "join_key_match",
        "name": "JOIN uses known keys",
        "applies_to": ["google_ads", "meta_ads"],
        "skip_cross_source": True,
        "fn": check_join_key_match,
    },
    {
        "id": "join_dedup_required",
        "name": "JOIN with config table requires ROW_NUMBER dedup",
        "applies_to": ["google_ads"],
        "fn": check_join_dedup_required,
    },
    {
        "id": "cross_source_date_alignment",
        "name": "Cross-source date format alignment",
        "applies_to": ["cross_source"],
        "fn": check_cross_source_date_alignment,
    },
    {
        "id": "cross_source_currency",
        "name": "Cross-source currency normalization",
        "applies_to": ["cross_source"],
        "fn": check_cross_source_currency,
    },
    {
        "id": "vtex_dt_filter",
        "name": "VTEX `dt` partition filter",
        "applies_to": ["vtex"],
        "fn": check_vtex_dt_filter,
    },
    {
        "id": "vtex_prices_not_divided",
        "name": "VTEX prices NOT divided by 100",
        "applies_to": ["vtex"],
        "fn": check_vtex_prices_not_divided,
    },
    {
        "id": "vtex_invoiced_status",
        "name": "VTEX status='invoiced' for revenue",
        "applies_to": ["vtex"],
        "fn": check_vtex_invoiced_status,
    },
    {
        "id": "shopify_dt_filter",
        "name": "Shopify `dt` partition filter",
        "applies_to": ["shopify"],
        "fn": check_shopify_dt_filter,
    },
    {
        "id": "shopify_financial_status",
        "name": "Shopify financial_status='paid' for revenue",
        "applies_to": ["shopify"],
        "fn": check_shopify_financial_status,
    },
]


def run_checks(sql, source, is_cross_source=False):
    """
    Run all applicable quality checks on a generated SQL query.

    Args:
        sql: The generated SQL to validate
        source: Primary source name (e.g., 'google_ads')
        is_cross_source: If True, also runs cross_source checks

    Returns list of dicts: [{id, name, passed, detail}, ...]
    """
    results = []
    for check in ALL_CHECKS:
        applies = check["applies_to"]
        # Skip intra-source-only checks when running cross-source
        if is_cross_source and check.get("skip_cross_source", False):
            continue
        # Run if source matches, or if cross_source check and is_cross_source flag set
        if source in applies or (is_cross_source and "cross_source" in applies):
            passed, detail = check["fn"](sql, source)
            results.append({
                "id": check["id"],
                "name": check["name"],
                "passed": passed,
                "detail": detail,
            })
    return results
