"""BigQuery query runner — dry-run estimation and real execution."""


def _translate_bq_error(error_msg: str) -> str:
    """Traduz mensagens de erro comuns do BigQuery para pt-BR."""
    if "Could not automatically determine credentials" in error_msg:
        return (
            "Credenciais GCP nao configuradas. Execute: "
            "gcloud auth application-default login"
        )
    if "403" in error_msg or "Permission" in error_msg.lower() or "Access Denied" in error_msg:
        return f"Sem permissao para acessar o BigQuery: {error_msg}"
    if "Syntax error" in error_msg:
        return f"Erro de sintaxe SQL: {error_msg}"
    if "Not found: Table" in error_msg or "Table not found" in error_msg:
        return f"Tabela nao encontrada: {error_msg}"
    if "404" in error_msg or "Not found" in error_msg:
        return f"Projeto ou dataset nao encontrado: {error_msg}"
    if "Quota exceeded" in error_msg or "quota" in error_msg.lower():
        return "Cota do BigQuery excedida. Tente novamente em alguns minutos."
    if "Invalid project" in error_msg:
        return f"Projeto GCP invalido: {error_msg}"
    return f"Erro no BigQuery: {error_msg}"


def dry_run_query(sql: str, project_id: str | None = None) -> dict:
    """
    Execute a dry-run of a SQL query on BigQuery to estimate processing cost.

    NEVER executes the query for real — only dry_run=True.

    Args:
        sql: The SQL query to estimate
        project_id: GCP project ID (uses default if None)

    Returns:
        dict with keys:
            - success (bool): whether dry-run succeeded
            - bytes_processed (int): estimated bytes to be processed
            - bytes_display (str): human-readable size (e.g., "1.5 GB")
            - estimated_cost_usd (float): estimated cost at $5/TB
            - estimated_cost_display (str): formatted cost string
            - error (str | None): error message if failed
    """
    try:
        from google.cloud import bigquery
    except ImportError:
        return {
            "success": False,
            "bytes_processed": 0,
            "bytes_display": "N/A",
            "estimated_cost_usd": 0.0,
            "estimated_cost_display": "N/A",
            "error": "google-cloud-bigquery nao instalado. Instale com: pip install google-cloud-bigquery",
        }

    try:
        client_kwargs = {}
        if project_id:
            client_kwargs["project"] = project_id

        client = bigquery.Client(**client_kwargs)

        job_config = bigquery.QueryJobConfig(
            dry_run=True,
            use_query_cache=False,
        )

        query_job = client.query(sql, job_config=job_config)

        total_bytes = query_job.total_bytes_processed
        cost_usd = (total_bytes / (1024 ** 4)) * 5.0  # $5 per TB

        return {
            "success": True,
            "bytes_processed": total_bytes,
            "bytes_display": _format_bytes(total_bytes),
            "estimated_cost_usd": round(cost_usd, 4),
            "estimated_cost_display": f"US$ {cost_usd:.4f}" if cost_usd < 0.01 else f"US$ {cost_usd:.2f}",
            "error": None,
        }

    except Exception as e:
        return {
            "success": False,
            "bytes_processed": 0,
            "bytes_display": "N/A",
            "estimated_cost_usd": 0.0,
            "estimated_cost_display": "N/A",
            "error": _translate_bq_error(str(e)),
        }


def run_query(
    sql: str,
    project_id: str | None = None,
    max_cost_usd: float = 1.0,
) -> dict:
    """
    Execute a SQL query on BigQuery with cost guard.

    Runs a dry-run first to estimate cost. If cost exceeds max_cost_usd,
    the query is NOT executed and an error is returned.

    Args:
        sql: The SQL query to execute
        project_id: GCP project ID (uses default if None)
        max_cost_usd: Maximum allowed cost in USD (default $1.00)

    Returns:
        dict with keys:
            - success (bool)
            - dataframe (pd.DataFrame | None)
            - rows_returned (int)
            - bytes_processed (int)
            - cost_usd (float)
            - error (str | None)
    """
    # Step 1: dry-run to check cost
    estimate = dry_run_query(sql, project_id=project_id)
    if not estimate["success"]:
        return {
            "success": False,
            "dataframe": None,
            "rows_returned": 0,
            "bytes_processed": 0,
            "cost_usd": 0.0,
            "error": estimate["error"],
        }

    if estimate["estimated_cost_usd"] > max_cost_usd:
        return {
            "success": False,
            "dataframe": None,
            "rows_returned": 0,
            "bytes_processed": estimate["bytes_processed"],
            "cost_usd": estimate["estimated_cost_usd"],
            "error": (
                f"Consulta estimada em US$ {estimate['estimated_cost_usd']:.4f} "
                f"({estimate['bytes_display']}), acima do limite de US$ {max_cost_usd:.2f}. "
                f"Consulta nao executada por seguranca."
            ),
        }

    # Step 2: execute for real
    try:
        from google.cloud import bigquery

        client_kwargs = {}
        if project_id:
            client_kwargs["project"] = project_id

        client = bigquery.Client(**client_kwargs)
        query_job = client.query(sql)
        df = query_job.result(max_results=10_000).to_dataframe()

        total_bytes = query_job.total_bytes_processed or 0
        cost_usd = (total_bytes / (1024**4)) * 5.0

        return {
            "success": True,
            "dataframe": df,
            "rows_returned": len(df),
            "bytes_processed": total_bytes,
            "cost_usd": round(cost_usd, 4),
            "error": None,
        }

    except Exception as e:
        return {
            "success": False,
            "dataframe": None,
            "rows_returned": 0,
            "bytes_processed": 0,
            "cost_usd": 0.0,
            "error": _translate_bq_error(str(e)),
        }


def _format_bytes(num_bytes: int) -> str:
    """Format bytes into human-readable string."""
    if num_bytes == 0:
        return "0 B"

    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    size = float(num_bytes)
    unit_index = 0

    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    if unit_index == 0:
        return f"{int(size)} B"
    return f"{size:.1f} {units[unit_index]}"
