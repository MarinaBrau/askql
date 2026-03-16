"""Testes para schemas/loader.py — load_schema(), list_sources(), cross-source functions."""

import pytest
from schemas.loader import (
    load_schema,
    list_sources,
    load_cross_source_relationships,
    load_cross_source_alignment_rules,
)


class TestLoadSchema:
    def test_ga4_returns_dict(self):
        schema = load_schema("ga4_bigquery")
        assert isinstance(schema, dict)

    def test_ga4_has_required_keys(self):
        schema = load_schema("ga4_bigquery")
        for key in ("source_name", "tables", "gotchas", "prompt_context"):
            assert key in schema, f"Missing key: {key}"

    def test_ga4_tables_not_empty(self):
        schema = load_schema("ga4_bigquery")
        assert len(schema["tables"]) > 0

    def test_google_ads_has_relationships(self):
        schema = load_schema("google_ads")
        assert len(schema["relationships"]) > 0

    def test_meta_ads_has_relationships(self):
        schema = load_schema("meta_ads")
        assert len(schema["relationships"]) > 0

    def test_google_ads_has_required_keys(self):
        schema = load_schema("google_ads")
        for key in ("source_name", "tables", "gotchas", "prompt_context"):
            assert key in schema

    def test_meta_ads_has_required_keys(self):
        schema = load_schema("meta_ads")
        for key in ("source_name", "tables", "gotchas", "prompt_context"):
            assert key in schema

    def test_nonexistent_source_raises(self):
        with pytest.raises(FileNotFoundError):
            load_schema("fonte_inexistente")

    def test_prompt_context_is_string(self):
        schema = load_schema("ga4_bigquery")
        assert isinstance(schema["prompt_context"], str)
        assert len(schema["prompt_context"]) > 0


class TestListSources:
    def test_returns_list(self):
        sources = list_sources()
        assert isinstance(sources, list)

    def test_contains_known_sources(self, source_names):
        sources = list_sources()
        for name in source_names:
            assert name in sources, f"Missing source: {name}"

    def test_sorted(self):
        sources = list_sources()
        assert sources == sorted(sources)


class TestLoadCrossSourceRelationships:
    def test_ga4_google_ads_returns_list(self):
        rels = load_cross_source_relationships("ga4_bigquery", "google_ads")
        assert isinstance(rels, list)
        assert len(rels) > 0

    def test_symmetric_lookup(self):
        ab = load_cross_source_relationships("ga4_bigquery", "google_ads")
        ba = load_cross_source_relationships("google_ads", "ga4_bigquery")
        assert len(ab) == len(ba)
        # Same relationship IDs
        ab_names = {r.get("name", "") for r in ab}
        ba_names = {r.get("name", "") for r in ba}
        assert ab_names == ba_names

    def test_nonexistent_pair_returns_empty(self):
        rels = load_cross_source_relationships("ga4_bigquery", "fonte_inexistente")
        assert rels == []


class TestLoadCrossSourceAlignmentRules:
    def test_returns_dict(self):
        rules = load_cross_source_alignment_rules()
        assert isinstance(rules, dict)

    def test_has_date_formats(self):
        rules = load_cross_source_alignment_rules()
        assert "date_formats" in rules

    def test_has_currency(self):
        rules = load_cross_source_alignment_rules()
        assert "currency" in rules
