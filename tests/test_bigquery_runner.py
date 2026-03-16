"""Testes para core/bigquery_runner.py — dry_run, run_query, _format_bytes (com mocks)."""

from unittest.mock import patch, MagicMock
import pandas as pd
from core.bigquery_runner import _format_bytes, dry_run_query, run_query


def _mock_bigquery_modules(mock_bq):
    """Helper: create sys.modules dict so 'from google.cloud import bigquery' returns mock_bq."""
    mock_google = MagicMock()
    mock_google_cloud = MagicMock()
    mock_google_cloud.bigquery = mock_bq
    return {
        "google": mock_google,
        "google.cloud": mock_google_cloud,
        "google.cloud.bigquery": mock_bq,
    }


class TestFormatBytes:
    def test_zero(self):
        assert _format_bytes(0) == "0 B"

    def test_bytes(self):
        assert _format_bytes(500) == "500 B"

    def test_kilobytes(self):
        result = _format_bytes(1536)  # 1.5 KB
        assert "KB" in result

    def test_megabytes(self):
        result = _format_bytes(1_500_000)
        assert "MB" in result

    def test_gigabytes(self):
        result = _format_bytes(1_500_000_000)
        assert "GB" in result

    def test_terabytes(self):
        result = _format_bytes(1_500_000_000_000)
        assert "TB" in result


class TestDryRunQuery:
    def test_success(self):
        mock_bq = MagicMock()
        mock_client = MagicMock()
        mock_bq.Client.return_value = mock_client
        mock_bq.QueryJobConfig.return_value = MagicMock()

        mock_job = MagicMock()
        mock_job.total_bytes_processed = 1_073_741_824  # 1 GB
        mock_client.query.return_value = mock_job

        with patch.dict("sys.modules", _mock_bigquery_modules(mock_bq)):
            result = dry_run_query("SELECT 1", project_id="test-project")
            assert result["success"] is True
            assert result["bytes_processed"] == 1_073_741_824
            assert "GB" in result["bytes_display"]
            assert result["error"] is None
            assert result["estimated_cost_usd"] > 0

    def test_error_returns_error_dict(self):
        mock_bq = MagicMock()
        mock_client = MagicMock()
        mock_bq.Client.return_value = mock_client
        mock_bq.QueryJobConfig.return_value = MagicMock()
        mock_client.query.side_effect = Exception("403 Permission denied")

        with patch.dict("sys.modules", _mock_bigquery_modules(mock_bq)):
            result = dry_run_query("SELECT 1", project_id="test-project")
            assert result["success"] is False
            assert result["error"] is not None

    def test_credentials_error_friendly_message(self):
        mock_bq = MagicMock()
        mock_client = MagicMock()
        mock_bq.Client.return_value = mock_client
        mock_bq.QueryJobConfig.return_value = MagicMock()
        mock_client.query.side_effect = Exception("Could not automatically determine credentials")

        with patch.dict("sys.modules", _mock_bigquery_modules(mock_bq)):
            result = dry_run_query("SELECT 1")
            assert result["success"] is False
            assert "gcloud" in result["error"]


class TestRunQuery:
    def test_cost_guard_blocks_expensive(self):
        """run_query refuses execution when cost exceeds limit."""
        mock_bq = MagicMock()
        mock_client = MagicMock()
        mock_bq.Client.return_value = mock_client
        mock_bq.QueryJobConfig.return_value = MagicMock()

        # 10 TB = ~$50, way above $1 limit
        mock_job = MagicMock()
        mock_job.total_bytes_processed = 10 * (1024 ** 4)
        mock_client.query.return_value = mock_job

        with patch.dict("sys.modules", _mock_bigquery_modules(mock_bq)):
            result = run_query("SELECT 1", project_id="test-project", max_cost_usd=1.0)
            assert result["success"] is False
            assert "limite" in result["error"].lower() or "acima" in result["error"].lower()

    def test_success(self):
        """Successful query execution returns dataframe."""
        mock_bq = MagicMock()
        mock_client = MagicMock()
        mock_bq.Client.return_value = mock_client
        mock_bq.QueryJobConfig.return_value = MagicMock()

        # Dry run job (small cost)
        mock_dry_job = MagicMock()
        mock_dry_job.total_bytes_processed = 1_000_000  # 1 MB

        # Real job
        mock_real_job = MagicMock()
        mock_real_job.total_bytes_processed = 1_000_000
        mock_df = pd.DataFrame({"col": [1, 2, 3]})
        mock_real_job.result.return_value.to_dataframe.return_value = mock_df

        mock_client.query.side_effect = [mock_dry_job, mock_real_job]

        with patch.dict("sys.modules", _mock_bigquery_modules(mock_bq)):
            result = run_query("SELECT 1", project_id="test-project")
            assert result["success"] is True
            assert result["rows_returned"] == 3
            assert result["error"] is None

    def test_execution_error(self):
        """Execution errors are handled gracefully."""
        mock_bq = MagicMock()
        mock_client = MagicMock()
        mock_bq.Client.return_value = mock_client
        mock_bq.QueryJobConfig.return_value = MagicMock()

        # Dry run succeeds
        mock_dry_job = MagicMock()
        mock_dry_job.total_bytes_processed = 1_000_000

        # Real execution fails
        mock_client.query.side_effect = [mock_dry_job, Exception("404 Not found: Table not found")]

        with patch.dict("sys.modules", _mock_bigquery_modules(mock_bq)):
            result = run_query("SELECT 1", project_id="test-project")
            assert result["success"] is False
            assert result["error"] is not None

    def test_dry_run_failure_propagates(self):
        """When dry run fails, run_query returns error without executing."""
        mock_bq = MagicMock()
        mock_client = MagicMock()
        mock_bq.Client.return_value = mock_client
        mock_bq.QueryJobConfig.return_value = MagicMock()
        mock_client.query.side_effect = Exception("Connection error")

        with patch.dict("sys.modules", _mock_bigquery_modules(mock_bq)):
            result = run_query("SELECT 1", project_id="test-project")
            assert result["success"] is False
            assert result["dataframe"] is None
