"""Testes para core/context_builder.py — build_context() (le schemas reais, nao chama API)."""

import pytest
from core.context_builder import build_context


class TestBuildContextSingleSource:
    def test_returns_dict_with_keys(self):
        ctx = build_context("ga4_bigquery", "my-project", "my_dataset", "quantas sessoes?")
        assert "system_prompt" in ctx
        assert "user_prompt" in ctx

    def test_system_prompt_contains_source_name(self):
        ctx = build_context("ga4_bigquery", "my-project", "my_dataset", "quantas sessoes?")
        assert "GA4" in ctx["system_prompt"] or "ga4" in ctx["system_prompt"].lower()

    def test_system_prompt_contains_table_names(self):
        ctx = build_context("ga4_bigquery", "my-project", "my_dataset", "quantas sessoes?")
        # GA4 schema must mention events table
        assert "events" in ctx["system_prompt"].lower()

    def test_system_prompt_contains_gotchas(self):
        ctx = build_context("ga4_bigquery", "my-project", "my_dataset", "quantas sessoes?")
        # Should have Critical Rules section
        assert "Gotcha" in ctx["system_prompt"] or "Rule" in ctx["system_prompt"]

    def test_user_prompt_contains_question(self):
        question = "quantas sessoes tivemos ontem?"
        ctx = build_context("ga4_bigquery", "my-project", "my_dataset", question)
        assert question in ctx["user_prompt"]

    def test_user_prompt_contains_project_id(self):
        ctx = build_context("ga4_bigquery", "test-project-123", "my_dataset", "teste")
        assert "test-project-123" in ctx["user_prompt"]

    def test_user_prompt_contains_dataset(self):
        ctx = build_context("ga4_bigquery", "my-project", "analytics_dataset", "teste")
        assert "analytics_dataset" in ctx["user_prompt"]

    def test_google_ads_relationships_in_prompt(self):
        ctx = build_context("google_ads", "my-project", "my_dataset", "custo por campanha")
        # Google Ads has relationships, should appear in system prompt
        assert "Relationship" in ctx["system_prompt"] or "relationship" in ctx["system_prompt"].lower()


class TestBuildContextCrossSource:
    def test_cross_source_has_both_sources(self):
        ctx = build_context(
            "ga4_bigquery", "my-project", "ga4_dataset", "sessoes vs custo",
            secondary_source="google_ads", secondary_dataset="gads_dataset",
        )
        # Should mention both sources
        assert "GA4" in ctx["system_prompt"] or "ga4" in ctx["system_prompt"].lower()
        assert "Google Ads" in ctx["system_prompt"] or "google_ads" in ctx["system_prompt"].lower()

    def test_cross_source_has_alignment_rules(self):
        ctx = build_context(
            "ga4_bigquery", "my-project", "ga4_dataset", "sessoes vs custo",
            secondary_source="google_ads", secondary_dataset="gads_dataset",
        )
        # Should mention alignment/date format
        assert "Alignment" in ctx["system_prompt"] or "alignment" in ctx["system_prompt"].lower() or "Date" in ctx["system_prompt"]

    def test_cross_source_user_prompt_mentions_both(self):
        ctx = build_context(
            "ga4_bigquery", "my-project", "ga4_dataset", "sessoes vs custo",
            secondary_source="google_ads", secondary_dataset="gads_dataset",
        )
        assert "ga4_bigquery" in ctx["user_prompt"]
        assert "google_ads" in ctx["user_prompt"]


class TestBuildContextEdgeCases:
    def test_nonexistent_source_raises(self):
        with pytest.raises(FileNotFoundError):
            build_context("fonte_inexistente", "p", "d", "q")

    def test_empty_question(self):
        # Should not crash with empty question
        ctx = build_context("ga4_bigquery", "my-project", "my_dataset", "")
        assert "system_prompt" in ctx
        assert "user_prompt" in ctx
