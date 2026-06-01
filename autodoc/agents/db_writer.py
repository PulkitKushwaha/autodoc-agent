from autodoc.agents.base import BaseAgent
from autodoc.logger import get_logger
from autodoc.models.doc_state import DocState
from autodoc.models.manifest import CodebaseManifest
from autodoc.utils.prompt_renderer import render_prompt

logger = get_logger(__name__)

_MODEL_BASE_NAMES = {
    "BaseModel", "Base", "Model", "Schema",
    "Entity", "Document", "TimestampMixin",
}

_MODEL_FILE_KEYWORDS = {
    "model", "schema", "entity", "document", "record",
}


class DBWriterAgent(BaseAgent):
    """
    Writes the data models and database schema section.

    Detects SQLAlchemy ORM models, Pydantic models, and dataclasses.
    Extracts class hierarchies, field definitions, and relationships.
    Revision-aware — passes critique to template on second pass.
    """

    _state_key = "db_doc"
    _system = (
        "You are a technical writer documenting data models and database schemas. "
        "Your output is precise, well-structured, and uses Markdown tables "
        "for all field listings. You reference only what is actually present "
        "in the codebase — you never invent fields or relationships."
    )

    def run(self, state: DocState) -> DocState:
        """Store critique from state before delegating to base run()."""
        critique = state.get("critique", {})
        self._critique = critique.get("db", "")
        return super().run(state)

    def _build_prompt(self, manifest: CodebaseManifest) -> str:
        model_classes = self._extract_model_classes(manifest)
        pydantic_models = self._extract_pydantic_models(manifest)

        logger.debug(
            "DBWriterAgent context — model classes: %d | pydantic models: %d",
            len(model_classes),
            len(pydantic_models),
        )

        context = {
            "project_name":    manifest.project_name,
            "total_files":     manifest.total_files,
            "databases":       manifest.stack.databases,
            "model_classes":   model_classes,
            "pydantic_models": pydantic_models,
            "critique":        getattr(self, "_critique", ""),
            "is_revision":     bool(getattr(self, "_critique", "")),
        }

        return render_prompt("db.j2", context)

    def _extract_model_classes(self, manifest: CodebaseManifest) -> list[dict]:
        """
        Find classes that are likely database models based on:
        - Inheriting from known ORM base classes
        - Living in files with model-related names
        """
        models = []
        for file in manifest.files:
            is_model_file = any(
                kw in file.module_name.lower()
                for kw in _MODEL_FILE_KEYWORDS
            )
            for cls in file.classes:
                is_model_class = any(
                    base in _MODEL_BASE_NAMES for base in cls.bases
                )
                if is_model_class or is_model_file:
                    public_methods = [
                        {
                            "name":              m.name,
                            "return_annotation": m.return_annotation,
                            "docstring":         m.docstring,
                        }
                        for m in cls.methods
                        if not m.name.startswith("_")
                        or m.name in ("__str__", "__repr__")
                    ]
                    models.append({
                        "name":      cls.name,
                        "module":    file.module_name,
                        "bases":     cls.bases,
                        "docstring": cls.docstring,
                        "methods":   public_methods,
                    })
                    logger.debug(
                        "DBWriterAgent detected model: %s in %s",
                        cls.name, file.module_name,
                    )
        return models

    def _extract_pydantic_models(self, manifest: CodebaseManifest) -> list[dict]:
        """Find all classes inheriting from BaseModel specifically."""
        pydantic = []
        for file in manifest.files:
            for cls in file.classes:
                if "BaseModel" in cls.bases:
                    pydantic.append({
                        "name":   cls.name,
                        "module": file.module_name,
                        "bases":  cls.bases,
                    })
        return pydantic
