import yaml
from pathlib import Path

SCHEMAS_DIR = Path(__file__).parent.parent / "schemas"


class TemplateLibrary:
    """Loads and manages query templates from all sources."""

    def __init__(self):
        self._cache = {}

    def get_templates(self, source_name: str) -> list[dict]:
        """Load templates for a given source. Returns empty list if none found."""
        if source_name in self._cache:
            return self._cache[source_name]

        templates_path = SCHEMAS_DIR / source_name / "common_queries.yaml"
        if not templates_path.exists():
            self._cache[source_name] = []
            return []

        with open(templates_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        templates = data.get("templates", [])
        self._cache[source_name] = templates
        return templates

    def get_categories(self, source_name: str) -> list[str]:
        """Get unique categories for a source, sorted."""
        templates = self.get_templates(source_name)
        categories = sorted(set(t.get("category", "") for t in templates))
        return categories

    def filter_by_category(self, source_name: str, category: str) -> list[dict]:
        """Filter templates by category. If category is empty/None, return all."""
        templates = self.get_templates(source_name)
        if not category:
            return templates
        return [t for t in templates if t.get("category") == category]

    def search(self, source_name: str, query: str) -> list[dict]:
        """Search templates by text in title, description, natural_language."""
        templates = self.get_templates(source_name)
        query_lower = query.lower()
        return [
            t for t in templates
            if query_lower in t.get("title", "").lower()
            or query_lower in t.get("description", "").lower()
            or query_lower in t.get("natural_language", "").lower()
        ]
