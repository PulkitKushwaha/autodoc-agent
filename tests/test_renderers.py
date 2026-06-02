from pathlib import Path
import pytest

from autodoc.models.doc_state import DocState


def make_state(tmp_path: Path) -> DocState:
    """Build a realistic DocState with all sections populated."""
    return DocState(
        project_name="testproject",
        manifest_path=str(tmp_path / "manifest.json"),
        manifest_summary="Test project.",
        sections_to_write=["architecture", "api", "db", "auth", "deploy"],
        architecture_doc="## System architecture\n\n### Overview\nThis is a test project.",
        api_doc="## API reference\n\n### Overview\nPublic API surface.",
        db_doc="## Data models\n\n### Overview\nSQLAlchemy models.",
        auth_doc="## Authentication\n\n### Overview\nJWT-based auth.",
        deploy_doc="## Deployment\n\n### Requirements\nPython 3.11+",
        critique={},
        quality_scores={
            "architecture": 8,
            "api":          9,
            "db":           8,
            "auth":         8,
            "deploy":       9,
        },
        sections_to_revise=[],
        revision_count=1,
        final_docs={
            "architecture": "## System architecture\n\n### Overview\nThis is a test project with clear structure.",
            "api":          "## API reference\n\n### Overview\nThree public functions exposed.",
            "db":           "## Data models\n\n### Overview\nSQLAlchemy ORM with User and Post models.",
            "auth":         "## Authentication\n\n### Overview\nJWT RS256 with bcrypt password hashing.",
            "deploy":       "## Deployment\n\n### Requirements\nPython 3.11+, uv, PostgreSQL 15+",
        },
        is_complete=True,
        error=None,
    )


# ── markdown renderer tests ───────────────────────────────────────

class TestMarkdownRenderer:
    def test_produces_output_file(self, tmp_path):
        from autodoc.renderers.markdown import render_markdown
        state = make_state(tmp_path)
        out = render_markdown(state, tmp_path / "output")
        assert out.exists()
        assert out.suffix == ".md"
        assert out.name == "documentation.md"

    def test_output_contains_project_name(self, tmp_path):
        from autodoc.renderers.markdown import render_markdown
        state = make_state(tmp_path)
        out = render_markdown(state, tmp_path / "output")
        content = out.read_text()
        assert "testproject" in content

    def test_output_contains_all_section_titles(self, tmp_path):
        from autodoc.renderers.markdown import render_markdown
        state = make_state(tmp_path)
        out = render_markdown(state, tmp_path / "output")
        content = out.read_text()
        assert "System architecture" in content
        assert "API reference" in content
        assert "Data models" in content
        assert "Authentication and security" in content
        assert "Deployment and infrastructure" in content

    def test_output_contains_table_of_contents(self, tmp_path):
        from autodoc.renderers.markdown import render_markdown
        state = make_state(tmp_path)
        out = render_markdown(state, tmp_path / "output")
        content = out.read_text()
        assert "Table of contents" in content

    def test_output_contains_section_content(self, tmp_path):
        from autodoc.renderers.markdown import render_markdown
        state = make_state(tmp_path)
        out = render_markdown(state, tmp_path / "output")
        content = out.read_text()
        assert "clear structure" in content

    def test_output_contains_autodoc_footer(self, tmp_path):
        from autodoc.renderers.markdown import render_markdown
        state = make_state(tmp_path)
        out = render_markdown(state, tmp_path / "output")
        content = out.read_text()
        assert "AutoDoc" in content

    def test_skips_empty_sections(self, tmp_path):
        from autodoc.renderers.markdown import render_markdown
        state = make_state(tmp_path)
        state["final_docs"] = {
            "architecture": "## Architecture\nContent only."
        }
        out = render_markdown(state, tmp_path / "output")
        content = out.read_text()
        assert "Architecture" in content
        assert "API reference" not in content

    def test_creates_output_dir_if_not_exists(self, tmp_path):
        from autodoc.renderers.markdown import render_markdown
        state = make_state(tmp_path)
        out_dir = tmp_path / "deep" / "nested" / "output"
        assert not out_dir.exists()
        render_markdown(state, out_dir)
        assert out_dir.exists()


# ── html renderer tests ───────────────────────────────────────────

class TestHTMLRenderer:
    def test_produces_index_file(self, tmp_path):
        from autodoc.renderers.html_site import render_html_site
        state = make_state(tmp_path)
        index = render_html_site(state, tmp_path / "output")
        assert index.exists()
        assert index.name == "index.html"

    def test_produces_all_section_files(self, tmp_path):
        from autodoc.renderers.html_site import render_html_site
        state = make_state(tmp_path)
        render_html_site(state, tmp_path / "output")
        site_dir = tmp_path / "output" / "site"
        assert (site_dir / "architecture.html").exists()
        assert (site_dir / "api.html").exists()
        assert (site_dir / "db.html").exists()
        assert (site_dir / "auth.html").exists()
        assert (site_dir / "deploy.html").exists()

    def test_index_contains_project_name(self, tmp_path):
        from autodoc.renderers.html_site import render_html_site
        state = make_state(tmp_path)
        index = render_html_site(state, tmp_path / "output")
        content = index.read_text()
        assert "testproject" in content

    def test_index_contains_section_links(self, tmp_path):
        from autodoc.renderers.html_site import render_html_site
        state = make_state(tmp_path)
        index = render_html_site(state, tmp_path / "output")
        content = index.read_text()
        assert "architecture.html" in content
        assert "api.html" in content
        assert "db.html" in content

    def test_index_contains_quality_scores(self, tmp_path):
        from autodoc.renderers.html_site import render_html_site
        state = make_state(tmp_path)
        index = render_html_site(state, tmp_path / "output")
        content = index.read_text()
        assert "8/10" in content or "9/10" in content

    def test_section_page_contains_project_name(self, tmp_path):
        from autodoc.renderers.html_site import render_html_site
        state = make_state(tmp_path)
        render_html_site(state, tmp_path / "output")
        arch = (tmp_path / "output" / "site" / "architecture.html").read_text()
        assert "testproject" in arch

    def test_section_page_contains_score(self, tmp_path):
        from autodoc.renderers.html_site import render_html_site
        state = make_state(tmp_path)
        render_html_site(state, tmp_path / "output")
        arch = (tmp_path / "output" / "site" / "architecture.html").read_text()
        assert "8/10" in arch

    def test_section_page_has_sidebar_nav(self, tmp_path):
        from autodoc.renderers.html_site import render_html_site
        state = make_state(tmp_path)
        render_html_site(state, tmp_path / "output")
        arch = (tmp_path / "output" / "site" / "architecture.html").read_text()
        assert "sidebar" in arch
        assert "index.html" in arch

    def test_markdown_to_html_headings(self):
        from autodoc.renderers.html_site import _markdown_to_html
        html = _markdown_to_html("## Hello world")
        assert "<h2>Hello world</h2>" in html

    def test_markdown_to_html_code_blocks(self):
        from autodoc.renderers.html_site import _markdown_to_html
        html = _markdown_to_html("```python\nprint('hi')\n```")
        assert "<pre><code>" in html

    def test_markdown_to_html_inline_code(self):
        from autodoc.renderers.html_site import _markdown_to_html
        html = _markdown_to_html("Use `my_function()` to call it.")
        assert "<code>my_function()</code>" in html

    def test_extract_preview_skips_headings(self):
        from autodoc.renderers.html_site import _extract_preview
        content = "## Heading\nThis is the actual preview text."
        preview = _extract_preview(content)
        assert "Heading" not in preview
        assert "preview text" in preview

    def test_extract_preview_truncates_long_lines(self):
        from autodoc.renderers.html_site import _extract_preview
        content = "A" * 200
        preview = _extract_preview(content)
        assert len(preview) <= 124  # 120 + "..."
        assert preview.endswith("...")


# ── format parsing tests ──────────────────────────────────────────

class TestFormatParsing:
    def test_parse_single_format(self):
        from autodoc.cli import _parse_formats
        assert _parse_formats("md") == ["md"]

    def test_parse_multiple_formats(self):
        from autodoc.cli import _parse_formats
        result = _parse_formats("md,html,pdf")
        assert "md" in result
        assert "html" in result
        assert "pdf" in result

    def test_parse_all_format(self):
        from autodoc.cli import _parse_formats
        assert _parse_formats("all") == ["all"]

    def test_parse_with_whitespace(self):
        from autodoc.cli import _parse_formats
        result = _parse_formats("md, html")
        assert "md" in result
        assert "html" in result

    def test_parse_uppercase_normalised(self):
        from autodoc.cli import _parse_formats
        result = _parse_formats("MD,HTML")
        assert "md" in result
        assert "html" in result
