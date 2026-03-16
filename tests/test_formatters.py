"""Testes para utils/formatters.py — format_sql()."""

from utils.formatters import format_sql


class TestFormatSql:
    def test_uppercase_keywords(self):
        sql = "select event_date from `project.dataset.events_*` where 1=1"
        result = format_sql(sql)
        assert "SELECT" in result
        assert "FROM" in result
        assert "WHERE" in result

    def test_multiple_columns_indented(self):
        sql = "select a, b, c from t where x = 1 group by a, b order by c"
        result = format_sql(sql)
        assert "SELECT" in result
        assert "GROUP BY" in result

    def test_empty_string(self):
        result = format_sql("")
        assert result == ""

    def test_none_input(self):
        result = format_sql(None)
        assert result is None

    def test_whitespace_only(self):
        result = format_sql("   ")
        assert result == "   "

    def test_idempotent(self):
        sql = "select a from t where x = 1"
        first = format_sql(sql)
        second = format_sql(first)
        assert first == second
