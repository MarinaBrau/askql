"""Testes para core/query_engine.py — generate_query() com mock do Claude."""

from unittest.mock import patch
from core.query_engine import generate_query, QueryResult


class TestGenerateQuerySafe:
    @patch("core.query_engine.call_claude")
    def test_safe_sql_returns_safe_result(self, mock_claude):
        mock_claude.return_value = {
            "sql": "SELECT event_date, COUNT(*) AS cnt FROM `p.d.events_*` GROUP BY 1",
            "explanation": "Conta eventos por dia",
            "raw_response": '{"sql": "...", "explanation": "..."}',
        }
        result = generate_query("ga4_bigquery", "p", "d", "quantos eventos?")

        assert isinstance(result, QueryResult)
        assert result.is_safe is True
        assert result.sql  # formatted SQL present
        assert result.explanation == "Conta eventos por dia"
        assert result.validation_message == "Query segura"

    @patch("core.query_engine.call_claude")
    def test_formatted_sql_has_uppercase_keywords(self, mock_claude):
        mock_claude.return_value = {
            "sql": "select event_date from `p.d.events_*` where 1=1",
            "explanation": "teste",
            "raw_response": "",
        }
        result = generate_query("ga4_bigquery", "p", "d", "teste")
        assert "SELECT" in result.sql
        assert "FROM" in result.sql


class TestGenerateQueryUnsafe:
    @patch("core.query_engine.call_claude")
    def test_drop_returns_unsafe(self, mock_claude):
        mock_claude.return_value = {
            "sql": "DROP TABLE `p.d.events_20240101`",
            "explanation": "Deletar tabela",
            "raw_response": "",
        }
        result = generate_query("ga4_bigquery", "p", "d", "delete table")
        assert result.is_safe is False
        assert "DROP" in result.validation_message

    @patch("core.query_engine.call_claude")
    def test_unsafe_preserves_raw_sql(self, mock_claude):
        raw_sql = "DELETE FROM `p.d.events_*`"
        mock_claude.return_value = {
            "sql": raw_sql,
            "explanation": "Deletar dados",
            "raw_response": "",
        }
        result = generate_query("ga4_bigquery", "p", "d", "delete")
        assert result.sql == raw_sql  # raw, not formatted


class TestGenerateQueryError:
    @patch("core.query_engine.call_claude")
    def test_claude_error_propagates(self, mock_claude):
        mock_claude.side_effect = Exception("API error")
        try:
            generate_query("ga4_bigquery", "p", "d", "teste")
            assert False, "Should have raised"
        except Exception as e:
            assert "API error" in str(e)


class TestGenerateQueryCrossSource:
    @patch("core.query_engine.call_claude")
    def test_cross_source_passes_secondary(self, mock_claude):
        mock_claude.return_value = {
            "sql": "SELECT 1",
            "explanation": "teste cross",
            "raw_response": "",
        }
        result = generate_query(
            "ga4_bigquery", "p", "d", "sessoes vs custo",
            secondary_source="google_ads", secondary_dataset="gads",
        )
        assert result.is_safe is True
        # Verify build_context was called with secondary params
        call_args = mock_claude.call_args
        assert call_args is not None


class TestQueryResultDataclass:
    def test_has_all_fields(self):
        r = QueryResult(
            sql="SELECT 1",
            explanation="teste",
            is_safe=True,
            validation_message="Query segura",
            raw_response="raw",
        )
        assert r.sql == "SELECT 1"
        assert r.explanation == "teste"
        assert r.is_safe is True
        assert r.validation_message == "Query segura"
        assert r.raw_response == "raw"

    def test_raw_response_default(self):
        r = QueryResult(sql="", explanation="", is_safe=True, validation_message="")
        assert r.raw_response == ""
