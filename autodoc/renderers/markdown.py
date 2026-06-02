from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from autodoc.logger import get_logger
from autodoc.models.doc_state import DocState

logger = get_logger(__name__)

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"

SECTION_TITLES = {
    "architecture": "System architecture",
    "api":          "API reference",
    "db":           "Data models",
    "auth":         "Authentication and security",
    "deploy":       "Deployment and infrastructure",
}


def render_markdown(state: DocState, output_dir: Path) -> Path:
    """
    Assemble all final_docs sections into a single Markdown file
    with a table of contents. Returns the path of the written file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    final_docs = state.get("final_docs", {})
    project_name = state.get("project_name", "project")
    quality_scores = state.get("quality_scores", {})

    logger.info(
        "MarkdownRenderer — assembling %d sections for project: %s",
        len(final_docs),
        project_name,
    )

    sections = []
    for key, title in SECTION_TITLES.items():
        content = final_docs.get(key, "")
        if content:
            sections.append({
                "title":   title,
                "anchor":  title.lower().replace(" ", "-").replace("/", ""),
                "content": content,
                "score":   quality_scores.get(key),
            })
            logger.debug("Adding section: %s (%d chars)", key, len(content))

    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("doc.md.j2")
    rendered = template.render(
        project_name=project_name,
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        sections=sections,
    )

    output_path = output_dir / "documentation.md"
    output_path.write_text(rendered, encoding="utf-8")

    logger.info(
        "Markdown written to %s (%d chars)", output_path, len(rendered)
    )
    return output_path
