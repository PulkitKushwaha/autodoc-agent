from autodoc.agents.base import BaseAgent
from autodoc.models.manifest import CodebaseManifest


class ArchitectureAgent(BaseAgent):
    """
    Writes the system architecture section.

    Covers: project overview, component breakdown, dependency structure,
    entry points, core modules, and key design observations.
    Full prompt engineering happens in Day 3 — this establishes the pattern.
    """

    _state_key = "architecture_doc"
    _system = (
        "You are a senior software architect writing technical documentation. "
        "Your architecture sections are clear, precise, and structured so that "
        "a new developer can understand the entire system within minutes."
    )

    def _build_prompt(self, manifest: CodebaseManifest) -> str:
        entry_points = manifest.dependency_graph.get_entry_points()
        core_modules = manifest.dependency_graph.get_core_modules()

        files_summary = "\n".join(
            f"- {f.module_name} ({f.line_count} lines) — "
            f"{len(f.classes)} classes, {len(f.functions)} functions"
            for f in manifest.files
        )

        return f"""Write a complete system architecture section for the following Python project.

Project: {manifest.project_name}
Total files: {manifest.total_files}
Total lines: {manifest.total_lines}
Tech stack: {', '.join(manifest.stack.frameworks + manifest.stack.databases + manifest.stack.other_tools) or 'not detected'}

Entry points (nothing imports these — they are top-level runners):
{', '.join(entry_points) or 'none detected'}

Core modules (imported by 3+ other modules — high importance):
{', '.join(core_modules) or 'none detected'}

All modules:
{files_summary}

Write the following subsections in Markdown:
1. Overview — what this project does in 2-3 sentences
2. Project structure — how the codebase is organized
3. Core components — what each major module/package does
4. Data flow — how data moves through the system
5. Key design decisions — patterns and architectural choices observed

Be specific. Reference actual module names. Do not invent details not supported by the data above."""
