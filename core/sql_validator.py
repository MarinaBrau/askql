import re

# Dangerous SQL keywords that should NEVER appear in generated queries
BLOCKED_KEYWORDS = [
    "DELETE", "UPDATE", "DROP", "CREATE", "ALTER",
    "INSERT", "MERGE", "TRUNCATE", "GRANT", "REVOKE",
]

# Match keyword anywhere (after stripping comments + string literals)
_BLOCKED_PATTERN = re.compile(
    r"\b(" + "|".join(BLOCKED_KEYWORDS) + r")\b",
    re.IGNORECASE,
)


def validate_sql(sql: str) -> tuple[bool, str]:
    """
    Validate that SQL is safe (SELECT only, no DDL/DML).

    Args:
        sql: The SQL query string to validate

    Returns:
        Tuple of (is_safe: bool, reason: str)
        - (True, "Query segura") if OK
        - (False, "Operacao bloqueada: DROP") if dangerous
    """
    if not sql or not sql.strip():
        return False, "Query vazia"

    # Strip comments and string literals before checking so that keywords
    # mentioned in explanatory text (comments) or filter values like
    # WHERE status = 'DELETED' don't trigger false positives, while actual
    # DDL/DML statements anywhere in the SQL are always caught.
    cleaned = _strip_sql(sql)

    match = _BLOCKED_PATTERN.search(cleaned)
    if match:
        keyword = match.group(1).upper()
        return False, f"Operacao bloqueada: {keyword}. Apenas queries SELECT sao permitidas."

    return True, "Query segura"


def _strip_sql(sql: str) -> str:
    """
    Remove comments and string literals, leaving only structural SQL tokens.

    This prevents:
    - False negatives: DELETE inside a comment like '-- run DELETE later'
    - False positives: WHERE status = 'DELETED' (DELETED != DELETE at word boundary)
    - False positives: column names like create_time, drop_rate (underscore breaks \b)

    Keeps:
    - Backtick identifiers (`project.dataset.table`) — NOT removed
    - Structural keywords (SELECT, FROM, WHERE, JOIN, DELETE, DROP, …)
    """
    # Remove block comments /* ... */
    result = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    # Remove line comments -- ...
    result = re.sub(r"--[^\n]*", " ", result)
    # Remove single-quoted string literals 'value' (handles escaped quotes \')
    result = re.sub(r"'(?:[^'\\]|\\.)*'", "''", result)
    return result
