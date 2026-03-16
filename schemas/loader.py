import os
import yaml
from pathlib import Path
from functools import lru_cache

SCHEMAS_DIR = Path(__file__).parent


@lru_cache(maxsize=16)
def load_schema(source_name: str) -> dict:
    source_dir = SCHEMAS_DIR / source_name
    if not source_dir.exists():
        raise FileNotFoundError(f"Source '{source_name}' nao encontrada em {SCHEMAS_DIR}")

    schema_path = source_dir / "schema.yaml"
    if not schema_path.exists():
        raise FileNotFoundError(f"schema.yaml nao encontrado para source '{source_name}'")

    with open(schema_path, "r", encoding="utf-8") as f:
        schema_data = yaml.safe_load(f)

    # Load gotchas (optional)
    gotchas_path = source_dir / "gotchas.yaml"
    gotchas = []
    if gotchas_path.exists():
        with open(gotchas_path, "r", encoding="utf-8") as f:
            gotchas_data = yaml.safe_load(f)
            gotchas = gotchas_data.get("gotchas", [])

    # Load prompt context (required)
    prompt_path = source_dir / "prompt_context.md"
    if not prompt_path.exists():
        raise FileNotFoundError(f"prompt_context.md nao encontrado para source '{source_name}'")

    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt_context = f.read()

    # Load relationships (optional)
    relationships_path = source_dir / "relationships.yaml"
    relationships = []
    if relationships_path.exists():
        with open(relationships_path, "r", encoding="utf-8") as f:
            rel_data = yaml.safe_load(f)
            relationships = rel_data.get("relationships", [])

    return {
        "source_name": schema_data.get("source_name", source_name),
        "display_name": schema_data.get("display_name", source_name),
        "description": schema_data.get("description", ""),
        "tables": schema_data.get("tables", []),
        "gotchas": gotchas,
        "relationships": relationships,
        "prompt_context": prompt_context,
    }


def load_cross_source_relationships(source_a: str, source_b: str) -> list:
    """
    Load cross-source relationships filtered by a pair of sources.

    Lookup is symmetric: (ga4_bigquery, google_ads) == (google_ads, ga4_bigquery).
    Returns empty list if file doesn't exist.
    """
    return _load_cross_source_relationships_cached(frozenset((source_a, source_b)))


@lru_cache(maxsize=16)
def _load_cross_source_relationships_cached(pair: frozenset) -> list:
    cross_path = SCHEMAS_DIR / "cross_source" / "relationships.yaml"
    if not cross_path.exists():
        return []

    with open(cross_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    all_rels = data.get("relationships", [])
    return [r for r in all_rels if set(r.get("sources", [])) == pair]


@lru_cache(maxsize=1)
def load_cross_source_alignment_rules() -> dict:
    """Load the alignment_rules section from cross-source relationships."""
    cross_path = SCHEMAS_DIR / "cross_source" / "relationships.yaml"
    if not cross_path.exists():
        return {}

    with open(cross_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return data.get("alignment_rules", {})


@lru_cache(maxsize=1)
def list_sources() -> list[str]:
    sources = []
    for entry in sorted(SCHEMAS_DIR.iterdir()):
        if entry.is_dir() and (entry / "schema.yaml").exists():
            sources.append(entry.name)
    return sources
