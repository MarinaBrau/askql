"""Testes para templates/template_library.py — TemplateLibrary."""

from templates.template_library import TemplateLibrary


class TestGetTemplates:
    def test_ga4_returns_nonempty(self):
        lib = TemplateLibrary()
        templates = lib.get_templates("ga4_bigquery")
        assert len(templates) > 0

    def test_template_has_required_fields(self):
        lib = TemplateLibrary()
        templates = lib.get_templates("ga4_bigquery")
        for t in templates:
            assert "title" in t, f"Missing 'title' in template: {t}"
            assert "category" in t, f"Missing 'category' in template: {t}"
            assert "sql" in t, f"Missing 'sql' in template: {t}"

    def test_nonexistent_source_returns_empty(self):
        lib = TemplateLibrary()
        templates = lib.get_templates("fonte_inexistente")
        assert templates == []

    def test_cache_works(self):
        lib = TemplateLibrary()
        first = lib.get_templates("ga4_bigquery")
        second = lib.get_templates("ga4_bigquery")
        assert first is second  # Same object (from cache)


class TestGetCategories:
    def test_returns_list_of_strings(self):
        lib = TemplateLibrary()
        categories = lib.get_categories("ga4_bigquery")
        assert isinstance(categories, list)
        assert len(categories) > 0
        for c in categories:
            assert isinstance(c, str)

    def test_sorted(self):
        lib = TemplateLibrary()
        categories = lib.get_categories("ga4_bigquery")
        assert categories == sorted(categories)


class TestFilterByCategory:
    def test_filters_correctly(self):
        lib = TemplateLibrary()
        categories = lib.get_categories("ga4_bigquery")
        if categories:
            cat = categories[0]
            filtered = lib.filter_by_category("ga4_bigquery", cat)
            assert len(filtered) > 0
            for t in filtered:
                assert t["category"] == cat

    def test_empty_category_returns_all(self):
        lib = TemplateLibrary()
        all_templates = lib.get_templates("ga4_bigquery")
        unfiltered = lib.filter_by_category("ga4_bigquery", "")
        assert len(unfiltered) == len(all_templates)


class TestSearch:
    def test_finds_results(self):
        lib = TemplateLibrary()
        # "trafego" should match at least one GA4 template
        results = lib.search("ga4_bigquery", "trafego")
        assert len(results) > 0

    def test_no_results_for_nonsense(self):
        lib = TemplateLibrary()
        results = lib.search("ga4_bigquery", "xyznonexistent12345")
        assert results == []
