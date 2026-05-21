from autodoc.agents.base import BaseAgent
from autodoc.models.manifest import CodebaseManifest


class DBWriterAgent(BaseAgent):
    """
    Writes the data models and database schema section.
    Detects SQLAlchemy models, Pydantic models, and dataclasses.
    Full implementation in Day 4.
    """

    _state_key = "db_doc"
    _system = (
        "You are a technical writer documenting data models and database schemas. "
        "Your output includes field tables, type information, constraints, "
        "and entity relationships in clear Markdown."
    )

    def _build_prompt(self, manifest: CodebaseManifest) -> str:
        models = self._extract_models(manifest)

        return f"""Write a complete data models section for the following Python project.

Project: {manifest.project_name}
Detected databases: {', '.join(manifest.stack.databases) or 'none detected'}

Data model classes found in source:
{models}

Write the following in Markdown:
1. Overview — what data this system manages
2. Models — for each model class: fields, types, constraints, relationships
3. Database notes — any migration tools, ORM patterns, or schema conventions observed

Use Markdown tables for field listings. Be specific to the models listed above."""

    def _extract_models(self, manifest: CodebaseManifest) -> str:
        model_indicators = {"BaseModel", "Base", "Model", "Schema", "Entity"}
        lines = []
        for file in manifest.files:
            for cls in file.classes:
                if any(base in model_indicators for base in cls.bases) or \
                   any(kw in file.module_name.lower() for kw in ("model", "schema", "entity")):
                    lines.append(f"\n{cls.name}(bases: {', '.join(cls.bases) or 'none'})")
                    for method in cls.methods:
                        lines.append(f"  - {method.name}")
        return "\n".join(lines) if lines else "No model classes detected."
