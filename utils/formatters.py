import sqlparse

def format_sql(sql: str) -> str:
    """
    Format SQL for display: indent, uppercase keywords.

    Args:
        sql: Raw SQL string

    Returns:
        Formatted SQL string
    """
    if not sql or not sql.strip():
        return sql

    return sqlparse.format(
        sql,
        reindent=True,
        keyword_case="upper",
        indent_width=2,
        wrap_after=80,
    )
