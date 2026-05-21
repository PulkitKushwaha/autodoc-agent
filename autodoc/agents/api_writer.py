from autodoc.agents.base import BaseAgent
from autodoc.models.manifest import CodebaseManifest, FunctionInfo


class APIWriterAgent(BaseAgent):
    """
    Writes the API reference section.

    Extracts all public functions and classes from the manifest
    and documents each with its signature, parameters, return type,
    and docstring. Full prompt refinement in Day 3.
    """

    _state_key = "api_doc"
    _system = (
        "You are a technical writer producing API reference documentation. "
        "Your output is precise, consistent, and uses standard Markdown "
        "with code blocks for all signatures and examples."
    )

    def _build_prompt(self, manifest: CodebaseManifest) -> str:
        public_api = self._extract_public_api(manifest)

        return f"""Write a complete API reference section for the following Python project.

Project: {manifest.project_name}

Public API surface (classes and functions extracted from source):
{public_api}

Write the following in Markdown:
1. Overview — one sentence describing the API surface
2. Classes — for each class: description, constructor args, public methods
3. Functions — for each public function: signature, parameters, return type, description
4. Usage examples — 2-3 short code examples showing common usage patterns

Use fenced code blocks for all signatures and examples.
Only document what is listed above — do not invent additional APIs."""

    def _extract_public_api(self, manifest: CodebaseManifest) -> str:
        lines = []
        for file in manifest.files:
            if not file.classes and not file.functions:
                continue
            lines.append(f"\n### {file.module_name}")
            for cls in file.classes:
                bases = f"({', '.join(cls.bases)})" if cls.bases else ""
                lines.append(f"\nclass {cls.name}{bases}:")
                if cls.docstring:
                    lines.append(f'    """{cls.docstring}"""')
                for method in cls.methods:
                    if not method.name.startswith("_"):
                        lines.append(f"    {self._format_fn(method)}")
            for fn in file.functions:
                if not fn.name.startswith("_"):
                    lines.append(self._format_fn(fn))
        return "\n".join(lines) if lines else "No public API surface detected."

    def _format_fn(self, fn: FunctionInfo) -> str:
        args = ", ".join(
            f"{a.name}: {a.annotation}" if a.annotation else a.name
            for a in fn.args
        )
        ret = f" -> {fn.return_annotation}" if fn.return_annotation else ""
        sig = f"def {fn.name}({args}){ret}"
        if fn.docstring:
            return f'{sig}\n    """{fn.docstring}"""'
        return sig
