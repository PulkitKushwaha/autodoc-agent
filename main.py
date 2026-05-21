import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from autodoc.config import settings
from autodoc.logger import setup_logging, get_logger

setup_logging(level=settings.log_level, log_file=settings.log_file)
logger = get_logger(__name__)

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from autodoc.ingestion.detector import detect_stack
from autodoc.ingestion.fetcher import cleanup, fetch_codebase
from autodoc.ingestion.graph import build_dependency_graph
from autodoc.ingestion.parser import parse_codebase
from autodoc.models.manifest import CodebaseManifest
from autodoc.models.doc_state import DocState
from autodoc.graph.pipeline import build_graph

console = Console()


def run(input_path: str) -> dict:
    logger.info("=" * 60)
    logger.info("AutoDoc run started — input: %s", input_path)
    logger.info("LLM mode: %s", "mock" if settings.use_mock else "real")

    console.print(Panel.fit(
        "[bold]AutoDoc[/bold] — agentic documentation generator",
        border_style="dim",
    ))

    settings.ensure_dirs()

    console.print("\n[bold]Phase 1 — Ingestion[/bold]")
    logger.info("Phase 1 — ingestion starting")

    root, is_temp = fetch_codebase(input_path)

    try:
        files = parse_codebase(root)
        console.print(f"  Parsed [green]{len(files)}[/green] Python files")

        graph_data = build_dependency_graph(files)
        entry_points = graph_data.get_entry_points()
        console.print(
            f"  Entry points: [green]{', '.join(entry_points) or 'none'}[/green]"
        )

        stack = detect_stack(root)
        if stack.frameworks:
            console.print(f"  Frameworks: [green]{', '.join(stack.frameworks)}[/green]")
        if stack.databases:
            console.print(f"  Databases:  [green]{', '.join(stack.databases)}[/green]")

        total_lines = sum(f.line_count for f in files)
        manifest = CodebaseManifest(
            project_name=root.name,
            root_path=str(root),
            source=input_path,
            total_files=len(files),
            total_lines=total_lines,
            files=files,
            stack=stack,
            dependency_graph=graph_data,
        )

        manifest_path = settings.output_dir / "manifest.json"
        manifest.save(manifest_path)
        logger.info("Manifest saved to %s", manifest_path)

        console.print("\n[bold]Phase 2 — Agent pipeline[/bold]")
        logger.info("Phase 2 — agent pipeline starting")

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
            final_docs={},
            is_complete=False,
            error=None,
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Running agent pipeline...", total=None)
            pipeline = build_graph()
            final_state = pipeline.invoke(initial_state)
            progress.update(task, description="Pipeline complete")

        if final_state.get("error"):
            console.print(f"\n[red]Pipeline error:[/red] {final_state['error']}")
            logger.error("Pipeline finished with error: %s", final_state["error"])
            return final_state

        console.print("\n[bold]Phase 3 — Writing output[/bold]")
        logger.info("Phase 3 — writing output files")

        final_docs = final_state.get("final_docs", {})
        section_titles = {
            "architecture": "01_architecture.md",
            "api":          "02_api_reference.md",
            "db":           "03_data_models.md",
            "auth":         "04_authentication.md",
            "deploy":       "05_deployment.md",
        }

        for key, filename in section_titles.items():
            content = final_docs.get(key)
            if content:
                out_path = settings.output_dir / filename
                out_path.write_text(content, encoding="utf-8")
                console.print(
                    f"  [green]Wrote[/green] {filename} "
                    f"([dim]{len(content)} chars[/dim])"
                )
                logger.info("Wrote %s (%d chars)", filename, len(content))

        sections_written = len(final_docs)
        console.print(
            f"\n[green]Done.[/green] {sections_written} sections written "
            f"to [bold]{settings.output_dir}[/bold]"
        )
        logger.info(
            "Run complete — %d sections written to %s",
            sections_written,
            settings.output_dir,
        )
        logger.info("=" * 60)

        return final_state

    except Exception:
        logger.exception("Run failed — unhandled exception")
        raise

    finally:
        if is_temp:
            cleanup(root)


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] != "--input":
        console.print("[red]Usage:[/red] python main.py --input <path-or-github-url>")
        sys.exit(1)
    run(sys.argv[2])
