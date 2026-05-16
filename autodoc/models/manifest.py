from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class ArgumentInfo(BaseModel):
    name: str
    annotation: Optional[str] = None


class FunctionInfo(BaseModel):
    name: str
    args: list[ArgumentInfo] = Field(default_factory=list)
    return_annotation: Optional[str] = None
    docstring: Optional[str] = None
    line_number: int
    is_method: bool = False


class ClassInfo(BaseModel):
    name: str
    bases: list[str] = Field(default_factory=list)
    docstring: Optional[str] = None
    methods: list[FunctionInfo] = Field(default_factory=list)
    line_number: int


class ImportInfo(BaseModel):
    module: str
    names: list[str] = Field(default_factory=list)
    is_from_import: bool = False


class FileInfo(BaseModel):
    path: str
    module_name: str
    docstring: Optional[str] = None
    classes: list[ClassInfo] = Field(default_factory=list)
    functions: list[FunctionInfo] = Field(default_factory=list)
    imports: list[ImportInfo] = Field(default_factory=list)
    line_count: int = 0


class StackInfo(BaseModel):
    language: str = "python"
    frameworks: list[str] = Field(default_factory=list)
    databases: list[str] = Field(default_factory=list)
    test_frameworks: list[str] = Field(default_factory=list)
    task_queues: list[str] = Field(default_factory=list)
    other_tools: list[str] = Field(default_factory=list)


class DependencyGraph(BaseModel):
    edges: dict[str, list[str]] = Field(default_factory=dict)

    def get_entry_points(self) -> list[str]:
        """Modules that nothing else imports — CLI scripts, app entry points."""
        all_modules = set(self.edges.keys())
        imported_modules = {
            dep for deps in self.edges.values() for dep in deps
        }
        return sorted(all_modules - imported_modules)

    def get_core_modules(self, threshold: int = 3) -> list[str]:
        """Modules imported by threshold or more other modules."""
        import_counts: dict[str, int] = {}
        for deps in self.edges.values():
            for dep in deps:
                import_counts[dep] = import_counts.get(dep, 0) + 1
        return [
            mod for mod, count in import_counts.items()
            if count >= threshold
        ]


class CodebaseManifest(BaseModel):
    project_name: str
    root_path: str
    source: str
    total_files: int
    total_lines: int
    files: list[FileInfo] = Field(default_factory=list)
    stack: StackInfo = Field(default_factory=StackInfo)
    dependency_graph: DependencyGraph = Field(default_factory=DependencyGraph)

    def save(self, path: Path) -> None:
        """Serialize to JSON and write to disk."""
        path.write_text(
            self.model_dump_json(indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: Path) -> "CodebaseManifest":
        """Reconstruct a full typed manifest from a saved JSON file."""
        return cls.model_validate_json(path.read_text(encoding="utf-8"))

    def summary(self) -> str:
        """One-paragraph human-readable summary for logging."""
        entry_points = self.dependency_graph.get_entry_points()
        core_mods = self.dependency_graph.get_core_modules()
        return (
            f"Project : {self.project_name}\n"
            f"Files   : {self.total_files} | Lines: {self.total_lines}\n"
            f"Stack   : {', '.join(self.stack.frameworks) or 'none detected'}\n"
            f"Entries : {', '.join(entry_points) or 'none'}\n"
            f"Core    : {', '.join(core_mods) or 'none'}"
        )
