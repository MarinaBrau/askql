"""Query engine — orchestrates the full NL → SQL pipeline."""

from dataclasses import dataclass

from core.context_builder import build_context
from core.claude_client import call_claude
from core.sql_validator import validate_sql
from utils.formatters import format_sql


@dataclass
class QueryResult:
    """Result of a query generation request."""

    sql: str
    explanation: str
    is_safe: bool
    validation_message: str
    raw_response: str = ""


def generate_query(
    source_name: str,
    project_id: str,
    dataset: str,
    question: str,
    model: str = "claude-sonnet-4-5-20250929",
    secondary_source: str = None,
    secondary_dataset: str = None,
) -> QueryResult:
    """
    Generate a BigQuery SQL query from a natural language question.

    Pipeline: question → context_builder → claude → validate → format → result

    Args:
        source_name: Schema source (ga4_bigquery, google_ads, meta_ads)
        project_id: GCP project ID
        dataset: BigQuery dataset name
        question: Natural language question
        model: Claude model ID
        secondary_source: Optional second source for cross-source queries
        secondary_dataset: Optional dataset for the second source

    Returns:
        QueryResult with sql, explanation, safety info
    """
    # 1. Build context (system + user prompts)
    ctx = build_context(
        source_name, project_id, dataset, question,
        secondary_source=secondary_source,
        secondary_dataset=secondary_dataset,
    )

    # 2. Call Claude
    response = call_claude(
        system_prompt=ctx["system_prompt"],
        user_message=ctx["user_prompt"],
        model=model,
    )

    raw_sql = response.get("sql", "")
    explanation = response.get("explanation", "")
    raw_response = response.get("raw_response", "")

    # 3. Validate SQL safety
    is_safe, validation_message = validate_sql(raw_sql)

    if not is_safe:
        return QueryResult(
            sql=raw_sql,
            explanation=explanation,
            is_safe=False,
            validation_message=validation_message,
            raw_response=raw_response,
        )

    # 4. Format SQL
    formatted_sql = format_sql(raw_sql)

    return QueryResult(
        sql=formatted_sql,
        explanation=explanation,
        is_safe=True,
        validation_message=validation_message,
        raw_response=raw_response,
    )
