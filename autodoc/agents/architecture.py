from autodoc.agents.base import BaseAgent
from autodoc.logger import get_logger
from autodoc.models.doc_state import DocState
from autodoc.models.manifest import CodebaseManifest, FileInfo
from autodoc.utils.prompt_renderer import render_prompt

logger = get_logger(__name__)


class ArchitectureAgent(BaseAgent):
    """
    Writes the system architecture section.

    Extracts entry points, core modules, dependency edges, and per-file
    summaries. Renders architecture.j2 with full structural context.
    On revision pass, injects critic feedback via is_revision + critique
    template variables.
    """

    _state_key = "architecture_doc"
    _system = (
        "You are a senior software architect writing technical documentation. "
        "Your architecture sections are clear, precise, and structured so that "
        "a new developer can understand the entire system within minutes. "
        "Always reference actual module names and real design patterns visible "
        "in the code — never use generic placeholders."
    )

    def run(self, state: DocState) -> DocState:
        """Store critique from state before delegating to base run()."""
        critique = state.get("critique", {})
        self._critique = critique.get("architecture", "")
        return super().run(state)

    def _build_prompt(self, manifest: CodebaseManifest) -> str:
        entry_points = manifest.dependency_graph.get_entry_points()
        core_modules = manifest.dependency_graph.get_core_modules()

        logger.debug(
            "ArchitectureAgent context — entry_points: %s | core_modules: %s",
            entry_points,
            core_modules,
        )

        context = {
            "project_name":    manifest.project_name,
            "total_files":     manifest.total_files,
            "total_lines":     manifest.total_lines,
            "frameworks":      manifest.stack.frameworks,
            "databases":       manifest.stack.databases,
            "test_frameworks": manifest.stack.test_frameworks,
            "task_queues":     manifest.stack.task_queues,
            "other_tools":     manifest.stack.other_tools,
            "entry_points":    entry_points,
            "core_modules":    core_modules,
            "files":           [self._build_file_context(f) for f in manifest.files],
            "edges":           {
                module: deps
                for module, deps in manifest.dependency_graph.edges.items()
                if deps
            },
            "critique":    getattr(self, "_critique", ""),
            "is_revision": bool(getattr(self, "_critique", "")),
        }

        return render_prompt("architecture.j2", context)

    def _build_file_context(self, file: FileInfo) -> dict:
        return {
            "module_name": file.module_name,
            "line_count":  file.line_count,
            "docstring":   file.docstring,
            "classes":     [c.name for c in file.classes],
            "functions":   [f.name for f in file.functions],
            "imports":     [
                f"{i.module}" + (
                    f".{', '.join(i.names)}" if i.names else ""
                )
                for i in file.imports
            ],
        }
