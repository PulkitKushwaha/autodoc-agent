import sys
from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table

load_dotenv()

from autodoc.config import settings
from autodoc.logger import setup_logging, get_logger

setup_logging(level=settings.log_level, log_file=settings.log_file)
logger = get_logger(__name__)

app = typer.Typer(
    name="autodoc",
    help="AI agent that generates technical documentation for Python codebases.",
    add_completion=False,
)

console = Console()

FORMAT_CHOICES = ["md", "html", "pdf", "all"]


@app.command()
def run(
    input_path: str = typer.Option(
        ...,
        "--input", "-i",
        help="GitHub URL or local path to the Python project.",
    ),
    output_dir: Path = typer.Option(
        None,
        "--output", "-o",
        help="Output directory. Defaults to AUTODOC_OUTPUT_DIR from .env.",
    ),
    formats: str = typer.Option(
        "md",
        "--format", "-f",
        help="Output formats — comma separated. Choices: md, html, pdf, all.",
    ),
    log_level: Optional[str] = typer.Option(
        None,
        "--log-level",
        help="Override log level (DEBUG, INFO, WARNING, ERROR).",
    ),
) -> None:
    """
    Generate technical documentation for a Python codebase.

    Examples:

      autodoc run --input ./myproject

      autodoc run --input https://github.com/user/repo --format md,html

      autodoc run --input ./myproject --format all --output ./docs
    """
    if log_level:
        setup_logging(level=log_level, log_file=settings.log_file)

    out_dir = output_dir or settings.output_dir
    requested_formats = _parse_formats(formats)

    console.print(Panel.fit(
        f"[bold]AutoDoc[/bold] — agentic documentation generator\n"
        f"[dim]Input:[/dim]   {input_path}\n"
        f"[dim]Output:[/dim]  {out_dir}\n"
        f"[dim]Formats:[/dim] {', '.join(requested_formats)}\n"
        f"[dim]LLM:[/dim]     {'mock' if settings.use_mock else 'real (Anthropic Claude)'}",
        border_style="dim",
    ))

    settings.ensure_dirs()
    out_dir.mkdir(parents=True, exist_ok=True)

    # ── Phase 1: ingestion ───────────────────────────────────────
    logger.info("Phase 1 — ingestion starting")
    console.print("\n[bold]Phase 1 — ingestion[/bold]")

    from autodoc.ingestion.fetcher import fetch_codebase, cleanup
    from autodoc.ingestion.parser import parse_codebase
    from autodoc.ingestion.graph import build_dependency_graph
    from autodoc.ingestion.detector import detect_stack
    from autodoc.models.manifest import CodebaseManifest
    from autodoc.models.doc_state import DocState

    root, is_temp = fetch_codebase(input_path)

    try:
        files = parse_codebase(root)
        console.print(f"  Parsed [green]{len(files)}[/green] Python files")

        graph = build_dependency_graph(files)
        entries = graph.get_entry_points()
        console.print(
            f"  Entry points: [green]{', '.join(entries) or 'none'}[/green]"
        )

        stack = detect_stack(root)
        if stack.frameworks:
            console.print(
                f"  Frameworks:   [green]{', '.join(stack.frameworks)}[/green]"
            )
        if stack.databases:
            console.print(
                f"  Databases:    [green]{', '.join(stack.databases)}[/green]"
            )

        total_lines = sum(f.line_count for f in files)
        manifest = CodebaseManifest(
            project_name=root.name,
            root_path=str(root),
            source=input_path,
            total_files=len(files),
            total_lines=total_lines,
            files=files,
            stack=stack,
            dependency_graph=graph,
        )

        manifest_path = out_dir / "manifest.json"
        manifest.save(manifest_path)
        logger.info("Manifest saved to %s", manifest_path)

        # ── Phase 2: agent pipeline ──────────────────────────────
        logger.info("Phase 2 — agent pipeline starting")
        console.print("\n[bold]Phase 2 — agent pipeline[/bold]")

        from autodoc.graph.pipeline import build_graph

        initial_state = DocState(
            project_name="",
            manifest_path=str(manifest_path),
            manifest_summary="",
            sections_to_write=[],
            architecture_doc="",
            api_doc="",
            db_doc="",
            auth_doc="",
            deploy_doc="",
            critique={},
            quality_scores={},
            sections_to_revise=[],
            revision_count=0,
            final_docs={},
            is_complete=False,
            error=None,
        )

        pipeline = build_graph()
        final_state = _run_with_progress(pipeline, initial_state)

        if final_state.get("error"):
            console.print(
                f"\n[red]Pipeline error:[/red] {final_state['error']}"
            )
            logger.error("Pipeline error: %s", final_state["error"])
            raise typer.Exit(code=1)

        _print_quality_scores(final_state)

        # ── Phase 3: rendering ───────────────────────────────────
        logger.info("Phase 3 — rendering output")
        console.print("\n[bold]Phase 3 — rendering[/bold]")

        _render_outputs(final_state, out_dir, requested_formats)

        console.print(
            f"\n[green]Done.[/green] Documentation written to "
            f"[bold]{out_dir}[/bold]"
        )
        logger.info("Run complete — output at %s", out_dir)

    except Exception:
        logger.exception("Run failed")
        raise

    finally:
        if is_temp:
            cleanup(root)


def _run_with_progress(pipeline, initial_state: dict) -> dict:
    """Run the LangGraph pipeline with a Rich progress bar."""
    nodes = [
        "planner", "architecture", "api", "db",
        "auth", "deploy", "critic", "assembler",
    ]

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task(
            "Running agent pipeline...",
            total=len(nodes),
        )

        final_state = pipeline.invoke(
            initial_state,
            config={"callbacks": []},
        )

        progress.update(
            task,
            completed=len(nodes),
            description="Pipeline complete",
        )

    return final_state


def _render_outputs(
    state: dict,
    out_dir: Path,
    formats: list[str],
) -> None:
    """Render all requested output formats."""
    from autodoc.renderers.markdown import render_markdown
    from autodoc.renderers.html_site import render_html_site
    from autodoc.renderers.pdf import render_pdf

    if "md" in formats or "all" in formats:
        path = render_markdown(state, out_dir)
        console.print(f"  [green]Markdown[/green]  → {path}")

    if "html" in formats or "all" in formats:
        path = render_html_site(state, out_dir)
        console.print(f"  [green]HTML site[/green] → {path}")

    if "pdf" in formats or "all" in formats:
        if "html" not in formats and "all" not in formats:
            render_html_site(state, out_dir)
        path = render_pdf(state, out_dir)
        console.print(f"  [green]PDF[/green]       → {path}")


def _print_quality_scores(state: dict) -> None:
    """Print a Rich table of quality scores from the critic agent."""
    scores = state.get("quality_scores", {})
    revision_count = state.get("revision_count", 0)

    if not scores:
        return

    table = Table(
        title="Quality scores",
        show_header=True,
        header_style="bold",
    )
    table.add_column("Section", style="dim")
    table.add_column("Score", justify="center")
    table.add_column("Status", justify="center")

    for section, score in scores.items():
        status = (
            "[green]✓ passed[/green]"
            if score >= 7
            else "[yellow]revised[/yellow]"
        )
        table.add_row(section, f"{score}/10", status)

    console.print(table)

    if revision_count > 0:
        console.print(f"  [dim]Revision rounds completed: {revision_count}[/dim]")


def _parse_formats(formats_str: str) -> list[str]:
    """Parse and validate the --format flag value."""
    parts = [f.strip().lower() for f in formats_str.split(",")]
    invalid = [f for f in parts if f not in FORMAT_CHOICES]
    if invalid:
        console.print(
            f"[red]Invalid format(s):[/red] {', '.join(invalid)}. "
            f"Valid choices: {', '.join(FORMAT_CHOICES)}"
        )
        raise typer.Exit(code=1)
    return parts


@app.command()
def version() -> None:
    """Show AutoDoc version."""
    console.print("AutoDoc [bold]0.1.0[/bold]")


if __name__ == "__main__":
    app()
