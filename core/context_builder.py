import yaml
from schemas.loader import load_schema, load_cross_source_relationships, load_cross_source_alignment_rules


def build_context(
    source_name: str,
    project_id: str,
    dataset: str,
    question: str,
    secondary_source: str = None,
    secondary_dataset: str = None,
) -> dict:
    """
    Build the full context (system prompt + user prompt) for Claude.

    Args:
        source_name: Schema source (e.g., 'ga4_bigquery', 'google_ads', 'meta_ads')
        project_id: GCP project ID for SQL references
        dataset: BigQuery dataset name
        question: User's natural language question
        secondary_source: Optional second source for cross-source queries
        secondary_dataset: Optional dataset for the second source

    Returns:
        dict with 'system_prompt' and 'user_prompt' keys
    """
    schema_data = load_schema(source_name)

    # Build the system prompt from parts
    system_parts = []

    # 1. Start with the prompt_context.md (main instructions)
    prompt_context = schema_data["prompt_context"]
    # Replace placeholders in prompt context
    prompt_context = prompt_context.replace("{project_id}", project_id)
    prompt_context = prompt_context.replace("{dataset}", dataset)
    system_parts.append(prompt_context)

    # 2. Add schema reference (formatted from YAML)
    schema_section = _format_schema_reference(schema_data["tables"])
    system_parts.append(f"\n\n## Schema Reference — {schema_data['display_name']}\n\n{schema_section}")

    # 3. Add table relationships (if any)
    relationships = schema_data.get("relationships", [])
    if relationships:
        rel_section = _format_relationships(relationships)
        system_parts.append(f"\n\n## Table Relationships\n\n{rel_section}")

    # 4. Add gotchas as numbered rules (if any)
    if schema_data["gotchas"]:
        gotchas_section = _format_gotchas(schema_data["gotchas"])
        system_parts.append(f"\n\n## Critical Rules (Gotchas)\n\n{gotchas_section}")

    # 5. If cross-source, add secondary schema + cross-source relationships
    if secondary_source and secondary_dataset:
        secondary_data = load_schema(secondary_source)

        # Add concise secondary schema (table names + key fields only)
        secondary_schema = _format_schema_concise(secondary_data["tables"])
        system_parts.append(
            f"\n\n## Secondary Source — {secondary_data['display_name']}\n"
            f"Dataset: `{project_id}.{secondary_dataset}`\n\n{secondary_schema}"
        )

        # Add secondary gotchas (abbreviated)
        if secondary_data["gotchas"]:
            secondary_gotchas = _format_gotchas_concise(secondary_data["gotchas"])
            system_parts.append(f"\n\n## Critical Rules — {secondary_data['display_name']}\n\n{secondary_gotchas}")

        # Add cross-source relationships
        cross_rels = load_cross_source_relationships(source_name, secondary_source)
        if cross_rels:
            cross_section = _format_cross_source_relationships(cross_rels)
            system_parts.append(f"\n\n## Cross-Source Relationships\n\n{cross_section}")

        # Add alignment rules
        alignment = load_cross_source_alignment_rules()
        if alignment:
            align_section = _format_alignment_rules(alignment, source_name, secondary_source)
            system_parts.append(f"\n\n## Data Alignment Rules\n\n{align_section}")

    system_prompt = "\n".join(system_parts)

    # Build user prompt
    user_prompt = _build_user_prompt(
        question, project_id, dataset, source_name,
        secondary_source=secondary_source,
        secondary_dataset=secondary_dataset,
    )

    return {
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
    }


def _format_schema_reference(tables: list) -> str:
    """Format tables/fields into a readable reference for the LLM."""
    lines = []
    for table in tables:
        name = table.get("name", "unknown")
        desc = table.get("description", "")
        lines.append(f"### Table: `{name}`")
        lines.append(f"{desc}")

        fields = table.get("fields", [])
        if isinstance(fields, str):
            # Some tables may reference another table's fields (e.g., events_intraday_*)
            lines.append(f"Fields: {fields}")
            lines.append("")
            continue

        if fields:
            lines.append("")
            lines.append("| Field | Type | Description |")
            lines.append("|-------|------|-------------|")
            for field in fields:
                fname = field.get("name", "")
                ftype = field.get("type", "")
                fdesc = field.get("description", "")
                lines.append(f"| `{fname}` | {ftype} | {fdesc} |")

                # Show sub_fields for STRUCTs
                sub_fields = field.get("sub_fields", [])
                if sub_fields:
                    for sf in sub_fields:
                        sfname = sf.get("name", "")
                        sftype = sf.get("type", "")
                        sfdesc = sf.get("description", "")
                        lines.append(f"| — `{fname}.{sfname}` | {sftype} | {sfdesc} |")

                # Show element_fields for ARRAYs
                element_fields = field.get("element_fields", [])
                if element_fields:
                    for ef in element_fields:
                        efname = ef.get("name", "")
                        eftype = ef.get("type", "")
                        efdesc = ef.get("description", "")
                        lines.append(f"| — (UNNEST) `{efname}` | {eftype} | {efdesc} |")

        lines.append("")

    return "\n".join(lines)


def _format_relationships(relationships: list) -> str:
    """Format table relationships into a readable reference for the LLM."""
    lines = []
    for rel in relationships:
        from_t = rel.get("from_table", "?")
        to_t = rel.get("to_table", "?")
        key = rel.get("join_key", "?")
        key_to = rel.get("join_key_to", key)
        card = rel.get("cardinality", "N:1")
        dedup = rel.get("requires_dedup", False)
        useful = rel.get("useful_fields", [])
        gotcha = rel.get("gotcha", "")
        example = rel.get("example_sql", "")

        join_expr = f"{key}" if key == key_to else f"{key} = {key_to}"
        lines.append(f"### `{from_t}` → `{to_t}`")
        lines.append(f"- **Join key:** {join_expr}")
        lines.append(f"- **Cardinality:** {card}")

        if dedup:
            part_by = rel.get("dedup_partition_by", key)
            order_by = rel.get("dedup_order_by", "_TABLE_SUFFIX DESC")
            lines.append(f"- **Requires dedup:** Yes — use `ROW_NUMBER() OVER (PARTITION BY {part_by} ORDER BY {order_by})` with `rn = 1`")
        else:
            lines.append(f"- **Requires dedup:** No")

        if useful:
            lines.append(f"- **Useful fields from target:** {', '.join(useful)}")

        if gotcha:
            lines.append(f"- **Note:** {gotcha}")

        if example:
            lines.append(f"\n**Example:**\n```sql\n{example.strip()}\n```")

        lines.append("")

    return "\n".join(lines)


def _format_schema_concise(tables: list) -> str:
    """Format tables into a concise reference (table name + key fields only, no sub_fields)."""
    lines = []
    for table in tables:
        name = table.get("name", "unknown")
        desc = table.get("description", "")
        lines.append(f"### `{name}`")
        lines.append(f"{desc}")

        fields = table.get("fields", [])
        if isinstance(fields, str):
            lines.append(f"Fields: {fields}")
            lines.append("")
            continue

        if fields:
            field_names = [f"`{f.get('name', '')}`" for f in fields]
            lines.append(f"Fields: {', '.join(field_names)}")

        lines.append("")

    return "\n".join(lines)


def _format_gotchas_concise(gotchas: list) -> str:
    """Format gotchas as a brief numbered list (no examples, just title + description)."""
    lines = []
    for g in gotchas:
        gid = g.get("id", "?")
        title = g.get("title", "")
        severity = g.get("severity", "high")
        desc = g.get("description", "")
        severity_label = "CRITICO" if severity == "critical" else "IMPORTANTE"
        lines.append(f"{gid}. [{severity_label}] **{title}** — {desc.strip()}")
    return "\n".join(lines)


def _format_cross_source_relationships(relationships: list) -> str:
    """Format cross-source relationships into a readable reference for the LLM."""
    lines = []
    for rel in relationships:
        name = rel.get("name", "?")
        sources = rel.get("sources", [])
        strategy = rel.get("strategy", "?")
        confidence = rel.get("confidence", "?")
        desc = rel.get("description", "")
        conversions = rel.get("required_conversions", [])
        caveat = rel.get("caveat", "")
        example = rel.get("example_sql", "")

        confidence_label = {"high": "ALTA", "medium": "MEDIA", "low": "BAIXA"}.get(confidence, confidence)
        strategy_label = {"date_based": "Agregacao por data", "utm_based": "UTM parameters"}.get(strategy, strategy)

        lines.append(f"### {' + '.join(sources)} ({strategy_label})")
        lines.append(f"- **Confianca:** {confidence_label}")
        lines.append(f"- **Descricao:** {desc}")

        if conversions:
            lines.append(f"- **Conversoes necessarias:**")
            for c in conversions:
                lines.append(f"  - {c}")

        if caveat:
            lines.append(f"- **ATENCAO:** {caveat}")

        if example:
            lines.append(f"\n**Example:**\n```sql\n{example.strip()}\n```")

        lines.append("")

    return "\n".join(lines)


def _format_alignment_rules(alignment: dict, source_a: str, source_b: str) -> str:
    """Format data alignment rules relevant to the two sources."""
    lines = []

    # Date formats
    date_formats = alignment.get("date_formats", {})
    if date_formats:
        lines.append("### Date Format Alignment")
        sources = {source_a, source_b}
        for src in sources:
            fmt = date_formats.get(src, "")
            if fmt:
                lines.append(f"- **{src}:** {fmt}")
        tip = date_formats.get("conversion_tip", "")
        if tip:
            lines.append(f"- **Tip:** {tip}")
        lines.append("")

    # Currency
    currency = alignment.get("currency", {})
    if currency:
        lines.append("### Currency Normalization")
        sources = {source_a, source_b}
        for src in sources:
            cur = currency.get(src, "")
            if cur:
                lines.append(f"- **{src}:** {cur}")
        tip = currency.get("normalization_tip", "")
        if tip:
            lines.append(f"- **Tip:** {tip}")
        lines.append("")

    return "\n".join(lines)


def _format_gotchas(gotchas: list) -> str:
    """Format gotchas into numbered rules with examples."""
    lines = []
    for g in gotchas:
        gid = g.get("id", "?")
        title = g.get("title", "")
        severity = g.get("severity", "high")
        desc = g.get("description", "")
        correct = g.get("correct_example", "")
        incorrect = g.get("incorrect_example", "")

        severity_label = "CRITICO" if severity == "critical" else "IMPORTANTE"
        lines.append(f"### Rule {gid} [{severity_label}]: {title}")
        lines.append(f"{desc.strip()}")

        if correct:
            lines.append(f"\n**Correto:**\n```sql\n{correct.strip()}\n```")
        if incorrect:
            lines.append(f"\n**Errado:**\n```sql\n{incorrect.strip()}\n```")

        lines.append("")

    return "\n".join(lines)


def _build_user_prompt(
    question: str,
    project_id: str,
    dataset: str,
    source_name: str,
    secondary_source: str = None,
    secondary_dataset: str = None,
) -> str:
    """Build the user message with question and context."""
    if secondary_source and secondary_dataset:
        return (
            f"Gere uma query BigQuery SQL que combina dados de **duas fontes** para responder a seguinte pergunta.\n\n"
            f"**Pergunta:** {question}\n\n"
            f"**Configuracao:**\n"
            f"- Project ID: `{project_id}`\n"
            f"- Fonte primaria: {source_name} (dataset: `{dataset}`)\n"
            f"- Fonte secundaria: {secondary_source} (dataset: `{secondary_dataset}`)\n\n"
            f"**IMPORTANTE:** Use CTEs separadas para cada fonte, agregue por data, e faca JOIN entre as CTEs. "
            f"Alinhe formatos de data e normalize unidades monetarias conforme as regras de alinhamento.\n\n"
            f"Retorne sua resposta como JSON valido com os campos `sql` e `explanation`."
        )

    return (
        f"Gere uma query BigQuery SQL para responder a seguinte pergunta.\n\n"
        f"**Pergunta:** {question}\n\n"
        f"**Configuracao:**\n"
        f"- Project ID: `{project_id}`\n"
        f"- Dataset: `{dataset}`\n"
        f"- Source: {source_name}\n\n"
        f"Retorne sua resposta como JSON valido com os campos `sql` e `explanation`."
    )
