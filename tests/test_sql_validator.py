"""Testes para core/sql_validator.py — validate_sql() e _strip_sql()."""

from core.sql_validator import validate_sql, _strip_sql

# Alias para compatibilidade com testes existentes
_remove_comments = _strip_sql


class TestValidateSqlSafe:
    def test_simple_select(self, sample_safe_sql):
        is_safe, msg = validate_sql(sample_safe_sql)
        assert is_safe is True
        assert msg == "Query segura"

    def test_select_with_subquery(self):
        sql = """
        SELECT * FROM (
            SELECT event_date, COUNT(*) AS cnt
            FROM `project.dataset.events_*`
            GROUP BY 1
        ) sub
        WHERE cnt > 10
        """
        is_safe, msg = validate_sql(sql)
        assert is_safe is True

    def test_select_with_cte(self):
        sql = """
        WITH daily AS (
            SELECT event_date, COUNT(*) AS cnt
            FROM `project.dataset.events_*`
            GROUP BY 1
        )
        SELECT * FROM daily WHERE cnt > 10
        """
        is_safe, msg = validate_sql(sql)
        assert is_safe is True

    def test_select_with_join(self):
        sql = """
        SELECT a.event_date, b.campaign_name
        FROM `project.dataset.events_*` a
        JOIN `project.dataset.campaigns` b ON a.campaign_id = b.campaign_id
        """
        is_safe, msg = validate_sql(sql)
        assert is_safe is True


class TestValidateSqlUnsafe:
    def test_delete(self, sample_unsafe_sql_delete):
        is_safe, msg = validate_sql(sample_unsafe_sql_delete)
        assert is_safe is False
        assert "DELETE" in msg

    def test_drop(self, sample_unsafe_sql_drop):
        is_safe, msg = validate_sql(sample_unsafe_sql_drop)
        assert is_safe is False
        assert "DROP" in msg

    def test_update(self, sample_unsafe_sql_update):
        is_safe, msg = validate_sql(sample_unsafe_sql_update)
        assert is_safe is False
        assert "UPDATE" in msg

    def test_insert(self, sample_unsafe_sql_insert):
        is_safe, msg = validate_sql(sample_unsafe_sql_insert)
        assert is_safe is False
        assert "INSERT" in msg

    def test_create_table(self):
        sql = "CREATE TABLE `project.dataset.new_table` AS SELECT 1"
        is_safe, msg = validate_sql(sql)
        assert is_safe is False
        assert "CREATE" in msg

    def test_truncate(self):
        sql = "TRUNCATE TABLE `project.dataset.events_20240101`"
        is_safe, msg = validate_sql(sql)
        assert is_safe is False
        assert "TRUNCATE" in msg


class TestValidateSqlEdgeCases:
    def test_empty_string(self):
        is_safe, msg = validate_sql("")
        assert is_safe is False
        assert "vazia" in msg.lower()

    def test_whitespace_only(self):
        is_safe, msg = validate_sql("   \n\t  ")
        assert is_safe is False
        assert "vazia" in msg.lower()

    def test_keyword_in_line_comment(self):
        sql = """
        -- This query does not DELETE anything
        SELECT * FROM `project.dataset.events_*`
        """
        is_safe, msg = validate_sql(sql)
        assert is_safe is True

    def test_keyword_in_block_comment(self):
        sql = """
        /* WARNING: do not DROP this table */
        SELECT * FROM `project.dataset.events_*`
        """
        is_safe, msg = validate_sql(sql)
        assert is_safe is True


class TestValidateSqlNewEdgeCases:
    """Casos de borda adicionados após detecção de falsos negativos no validator."""

    def test_delete_after_select_no_semicolon(self):
        """DELETE sem ponto-e-vírgula separador ainda deve ser bloqueado."""
        sql = (
            "SELECT id, name FROM campaigns WHERE status = 'DELETED'\n"
            "DELETE FROM campaigns WHERE status = 'DELETED'"
        )
        is_safe, msg = validate_sql(sql)
        assert is_safe is False
        assert "DELETE" in msg

    def test_delete_after_select_with_semicolon(self):
        """DELETE separado por ; deve ser bloqueado."""
        sql = (
            "SELECT id FROM campaigns WHERE status = 'DELETED';\n"
            "DELETE FROM campaigns WHERE status = 'DELETED';"
        )
        is_safe, msg = validate_sql(sql)
        assert is_safe is False
        assert "DELETE" in msg

    def test_delete_in_string_literal_is_safe(self):
        """DELETE dentro de string literal NÃO deve bloquear."""
        sql = "SELECT 'Operacao DELETE nao suportada' AS aviso FROM campaigns"
        is_safe, msg = validate_sql(sql)
        assert is_safe is True

    def test_deleted_status_filter_is_safe(self):
        """WHERE status = 'DELETED' é filtro legítimo, não DDL."""
        sql = "SELECT id, name FROM campaigns WHERE status = 'DELETED'"
        is_safe, msg = validate_sql(sql)
        assert is_safe is True

    def test_drop_in_string_explanation_is_safe(self):
        """DROP mencionado em string de aviso não deve bloquear."""
        sql = "SELECT 'Use DROP TABLE apenas no console do BigQuery' AS aviso"
        is_safe, msg = validate_sql(sql)
        assert is_safe is True

    def test_update_as_actual_statement_is_blocked(self):
        """UPDATE como statement real deve ser bloqueado."""
        sql = (
            "-- Nota: BigQuery eh read-only\n"
            "UPDATE campaigns SET budget = 1000 WHERE status = 'ENABLED'"
        )
        is_safe, msg = validate_sql(sql)
        assert is_safe is False
        assert "UPDATE" in msg

    def test_create_time_column_is_safe(self):
        """Coluna 'create_time' não deve disparar o check de CREATE."""
        sql = "SELECT create_time, update_time FROM orders WHERE status = 'paid'"
        is_safe, msg = validate_sql(sql)
        assert is_safe is True

    def test_drop_rate_column_is_safe(self):
        """Coluna 'drop_rate' não deve disparar o check de DROP."""
        sql = "SELECT campaign_name, drop_rate FROM performance_metrics"
        is_safe, msg = validate_sql(sql)
        assert is_safe is True


class TestStripSql:
    def test_removes_line_comment(self):
        sql = "SELECT * FROM t -- DELETE this\nWHERE 1=1"
        result = _strip_sql(sql)
        assert "DELETE" not in result
        assert "SELECT" in result

    def test_removes_block_comment(self):
        sql = "SELECT * /* DROP TABLE t */ FROM t"
        result = _strip_sql(sql)
        assert "DROP" not in result
        assert "SELECT" in result

    def test_removes_string_literal(self):
        sql = "SELECT 'DELETE FROM table' AS msg FROM t"
        result = _strip_sql(sql)
        assert "DELETE FROM table" not in result
        assert "SELECT" in result

    def test_preserves_backtick_identifiers(self):
        sql = "SELECT * FROM `project.dataset.events_*`"
        result = _strip_sql(sql)
        assert "`project.dataset.events_*`" in result

    def test_preserves_query_structure(self):
        sql = "SELECT event_date FROM `project.dataset.events_*`"
        result = _strip_sql(sql)
        assert "SELECT" in result
        assert "event_date" in result


class TestRemoveComments:
    """Alias mantido para compatibilidade — aponta para _strip_sql."""

    def test_removes_line_comment(self):
        sql = "SELECT * FROM t -- DELETE this\nWHERE 1=1"
        result = _remove_comments(sql)
        assert "DELETE" not in result
        assert "SELECT" in result

    def test_removes_block_comment(self):
        sql = "SELECT * /* DROP TABLE t */ FROM t"
        result = _remove_comments(sql)
        assert "DROP" not in result
        assert "SELECT" in result

    def test_preserves_query(self):
        sql = "SELECT event_date FROM `project.dataset.events_*`"
        result = _remove_comments(sql)
        assert "SELECT" in result
        assert "event_date" in result
