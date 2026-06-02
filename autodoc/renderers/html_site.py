import re
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from autodoc.logger import get_logger
from autodoc.models.doc_state import DocState
from autodoc.renderers.markdown import SECTION_TITLES

logger = get_logger(__name__)

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "site"


def _markdown_to_html(md: str) -> str:
    """
    Minimal Markdown to HTML conversion for the HTML site.
    Handles headings, fenced code blocks, inline code, bold, and paragraphs.
    """
    html = md

    # Fenced code blocks — must come before inline code
    html = re.sub(
        r"```(\w+)?\n(.*?)```",
        lambda m: f"<pre><code>{_escape(m.group(2))}</code></pre>",
        html,
        flags=re.DOTALL,
    )

    # Headings — process highest level first to avoid partial matches
    for level in range(4, 0, -1):
        pattern = r"^{} (.+)$".format("#" * level)
        tag = f"h{level}"
        html = re.sub(
            pattern, rf"<{tag}>\1</{tag}>", html, flags=re.MULTILINE
        )

    # Markdown tables — header cells
    html = re.sub(
        r"^\|(.+)\|$",
        lambda m: "<tr>"
        + "".join(f"<th>{c.strip()}</th>" for c in m.group(1).split("|"))
        + "</tr>",
        html,
        flags=re.MULTILINE,
    )
    # Remove separator rows (|---|---|)
    html = re.sub(r"^\|[-| :]+\|$", "", html, flags=re.MULTILINE)

    # Inline code
    html = re.sub(r"`([^`]+)`", r"<code>\1</code>", html)

    # Bold
    html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)

    # Wrap bare lines in <p> tags
    lines = html.split("\n")
    result = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            result.append("")
        elif stripped.startswith("<"):
            result.append(stripped)
        else:
            result.append(f"<p>{stripped}</p>")

    return "\n".join(result)


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
    )


def _extract_preview(content: str, max_chars: int = 120) -> str:
    """Extract a short preview text from Markdown for the index card."""
    for line in content.splitlines():
        stripped = line.strip()
        if (
            stripped
            and not stripped.startswith("#")
            and not stripped.startswith("```")
            and not stripped.startswith("|")
        ):
            preview = stripped[:max_chars]
            return preview + "..." if len(stripped) > max_chars else preview
    return ""


def render_html_site(state: DocState, output_dir: Path) -> Path:
    """
    Generate a multi-page static HTML documentation site.
    Returns the path to the index.html file.
    """
    site_dir = output_dir / "site"
    site_dir.mkdir(parents=True, exist_ok=True)

    final_docs = state.get("final_docs", {})
    project_name = state.get("project_name", "project")
    quality_scores = state.get("quality_scores", {})
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    logger.info(
        "HTMLRenderer — generating site for project: %s | sections: %d",
        project_name,
        len(final_docs),
    )

    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    sections = []
    for key, title in SECTION_TITLES.items():
        content = final_docs.get(key, "")
        if content:
            filename = f"{key}.html"
            sections.append({
                "key":      key,
                "title":    title,
                "filename": filename,
                "preview":  _extract_preview(content),
                "score":    quality_scores.get(key),
                "content":  content,
            })
            logger.debug("Prepared section: %s → %s", key, filename)

    # Write index page
    index_template = env.get_template("index.html.j2")
    index_html = index_template.render(
        project_name=project_name,
        generated_at=generated_at,
        sections=sections,
    )
    index_path = site_dir / "index.html"
    index_path.write_text(index_html, encoding="utf-8")
    logger.info("Wrote index.html")

    # Write individual section pages
    section_template = env.get_template("section.html.j2")
    for section in sections:
        content_html = _markdown_to_html(section["content"])
        section_html = section_template.render(
            project_name=project_name,
            section_title=section["title"],
            content_html=content_html,
            score=section["score"],
            all_sections=sections,
        )
        page_path = site_dir / section["filename"]
        page_path.write_text(section_html, encoding="utf-8")
        logger.info("Wrote %s", section["filename"])

    logger.info("HTML site written to %s", site_dir)
    return index_path
