from autodoc.agents.base import BaseAgent
from autodoc.logger import get_logger
from autodoc.models.manifest import CodebaseManifest, FileInfo, FunctionInfo
from autodoc.utils.prompt_renderer import render_prompt

logger = get_logger(__name__)


class APIWriterAgent(BaseAgent):
    """
    Writes the API reference section.

    Extracts every public class and function from the manifest with
    full signature context — argument names, type annotations, return
    types, docstrings — and renders the api.j2 prompt template.
    Private items (leading underscore) are excluded.
    """

    _state_key = "api_doc"
    _system = (
        "You are a technical writer producing API reference documentation. "
        "Your output is precise, consistent, and complete. "
        "Every public class and function must be documented. "
        "Use standard Markdown with fenced Python code blocks for all signatures. "
        "Tables must have consistent column alignment."
    )

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
                "classes":   [
                    self._build_class_context(cls)
                    for cls in public_classes
                ],
                "functions": [
                    self._build_function_context(fn)
                    for fn in public_functions
                ],
            })

        logger.debug(
            "APIWriterAgent context — modules: %d | public items: %d",
            len(modules_context),
            total_public_items,
        )

        context = {
            "project_name":      manifest.project_name,
            "total_modules":     len(modules_context),
            "total_public_items": total_public_items,
            "modules":           modules_context,
        }

        return render_prompt("api.j2", context)

    def _build_class_context(self, cls) -> dict:
        public_methods = [
            m for m in cls.methods
            if not m.name.startswith("_")
        ]
        return {
            "name":     cls.name,
            "bases":    cls.bases,
            "docstring": cls.docstring,
            "methods":  [
                self._build_function_context(m)
                for m in public_methods
            ],
        }

    def _build_function_context(self, fn: FunctionInfo) -> dict:
        args = []
        for arg in fn.args:
            if arg.annotation:
                args.append(f"{arg.name}: {arg.annotation}")
            else:
                args.append(arg.name)
        return {
            "name":              fn.name,
            "args":              args,
            "return_annotation": fn.return_annotation,
            "docstring":         fn.docstring,
        }
