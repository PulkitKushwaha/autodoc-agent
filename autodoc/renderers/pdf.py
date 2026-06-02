from pathlib import Path

from autodoc.logger import get_logger
from autodoc.models.doc_state import DocState

logger = get_logger(__name__)


def render_pdf(state: DocState, output_dir: Path) -> Path:
    """
    Generate a PDF from the HTML site output using WeasyPrint.
    Requires render_html_site() to have been called first.
    Returns the path to the written PDF file.
    """
    try:
        from weasyprint import HTML, CSS
    except ImportError:
        logger.error(
            "WeasyPrint is not installed. Run: uv add weasyprint"
        )
        raise

    site_dir = output_dir / "site"
    index_path = site_dir / "index.html"

    if not index_path.exists():
        raise FileNotFoundError(
            f"HTML site not found at {site_dir}. "
            "Run render_html_site() before render_pdf()."
        )

    project_name = state.get("project_name", "project")
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = output_dir / f"{project_name}_documentation.pdf"

    logger.info("PDFRenderer — generating PDF from HTML site at %s", index_path)

    # Print-specific CSS overrides
    css = CSS(string="""
        @page {
            size: A4;
            margin: 2cm 2cm 2.5cm 2cm;
            @bottom-center {
                content: counter(page) " / " counter(pages);
                font-size: 10px;
                color: #9ca3af;
            }
        }
        .sidebar { display: none !important; }
        .main {
            margin-left: 0 !important;
            padding: 1cm 0 !important;
        }
        body { font-size: 12px; }
        pre { font-size: 10px; page-break-inside: avoid; }
        h1 { font-size: 22px; page-break-after: avoid; }
        h2 { font-size: 16px; page-break-after: avoid; }
        h3 { font-size: 13px; page-break-after: avoid; }
        table { page-break-inside: avoid; }
        a { color: #6366f1; }
    """)

    html_obj = HTML(filename=str(index_path))
    html_obj.write_pdf(
        target=str(pdf_path),
        stylesheets=[css],
    )

    logger.info("PDF written to %s", pdf_path)
    return pdf_path
