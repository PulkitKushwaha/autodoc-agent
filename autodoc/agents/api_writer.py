from autodoc.agents.base import BaseAgent
from autodoc.logger import get_logger
from autodoc.models.doc_state import DocState
from autodoc.models.manifest import CodebaseManifest, FunctionInfo
from autodoc.utils.prompt_renderer import render_prompt

logger = get_logger(__name__)


class APIWriterAgent(BaseAgent):
    """
    Writes the API reference section.

    Extracts all public classes and functions with full signatures,
    type annotations, and docstrings. Filters private items.
    Revision-aware — passes critique to template on second pass.
    """

    _state_key = "api_doc"
    _system = (
        "You are a technical writer producing API reference documentation. "
        "Your output is precise, consistent, and complete. "
        "Every public class and function must be documented. "
        "Use standard Markdown with fenced Python code blocks for all signatures. "
        "Tables must have consistent column alignment."
    )

    def run(self, state: DocState) -> DocState:
        """Store critique from state before delegating to base run()."""
        critique = state.get("critique", {})
        self._critique = critique.get("api", "")
        return super().run(state)

    def _build_prompt(self, manifest: CodebaseManifest) -> str:
        modules_context = []
        total_public_items = 0

        for file in manifest.files:
            public_classes = [
                c for c in file.classes
                if not c.name.startswith("_")
            ]
            public_functions = [
                f for f in file.functions
                if not f.name.startswith("_")
            ]

            if not public_classes and not public_functions:
                continue

            total_public_items += len(public_classes) + len(public_functions)
            modules_context.append({
                "name":      file.module_name,
                "classes":   [self._build_class_context(cls) for cls in public_classes],
                "functions": [self._build_function_context(fn) for fn in public_functions],
            })

        logger.debug(
            "APIWriterAgent context — modules: %d | public items: %d",
            len(modules_context),
            total_public_items,
        )

        context = {
            "project_name":       manifest.project_name,
            "total_modules":      len(modules_context),
            "total_public_items": total_public_items,
            "modules":            modules_context,
            "critique":           getattr(self, "_critique", ""),
            "is_revision":        bool(getattr(self, "_critique", "")),
        }

        return render_prompt("api.j2", context)

    def _build_class_context(self, cls) -> dict:
        return {
            "name":      cls.name,
            "bases":     cls.bases,
            "docstring": cls.docstring,
            "methods":   [
                self._build_function_context(m)
                for m in cls.methods
                if not m.name.startswith("_")
            ],
        }

    def _build_function_context(self, fn: FunctionInfo) -> dict:
        args = [
            f"{a.name}: {a.annotation}" if a.annotation else a.name
            for a in fn.args
        ]
        return {
            "name":              fn.name,
            "args":              args,
            "return_annotation": fn.return_annotation,
            "docstring":         fn.docstring,
        }
