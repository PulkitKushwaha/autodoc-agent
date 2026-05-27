from pathlib import Path
import pytest

from autodoc.models.manifest import (
    CodebaseManifest, StackInfo, DependencyGraph,
    FileInfo, ClassInfo, FunctionInfo, ArgumentInfo, ImportInfo,
)
from autodoc.agents.architecture import ArchitectureAgent
from autodoc.agents.api_writer import APIWriterAgent
from autodoc.agents.planner import planner_node
from autodoc.models.doc_state import DocState
from autodoc.utils.prompt_renderer import render_prompt


def make_rich_manifest(tmp_path: Path) -> tuple[Path, CodebaseManifest]:
    """
    Build a realistic manifest with classes, functions, imports,
    and a dependency graph for testing prompt quality.
    """
    files = [
        FileInfo(
            path="main.py",
            module_name="main",
            docstring="Entry point for the application.",
            classes=[],
            functions=[
                FunctionInfo(
                    name="run",
                    args=[ArgumentInfo(name="input_path", annotation="str")],
                    return_annotation="dict",
                    docstring="Run the full pipeline.",
                    line_number=10,
                    is_method=False,
                )
            ],
            imports=[
                ImportInfo(module="app.service", names=["Service"], is_from_import=True)
            ],
            line_count=40,
        ),
        FileInfo(
            path="app/service.py",
            module_name="app.service",
            docstring="Core service layer.",
            classes=[
                ClassInfo(
                    name="Service",
                    bases=["BaseService"],
                    docstring="Main application service.",
                    methods=[
                        FunctionInfo(
                            name="process",
                            args=[
                                ArgumentInfo(name="data", annotation="dict"),
                            ],
                            return_annotation="str",
                            docstring="Process the input data.",
                            line_number=15,
                            is_method=True,
                        ),
                        FunctionInfo(
                            name="_validate",
                            args=[ArgumentInfo(name="data", annotation="dict")],
                            return_annotation="bool",
                            docstring=None,
                            line_number=25,
                            is_method=True,
                        ),
                    ],
                    line_number=10,
                )
            ],
            functions=[],
            imports=[
                ImportInfo(module="app.utils", names=["helper"], is_from_import=True)
            ],
            line_count=60,
        ),
        FileInfo(
            path="app/utils.py",
            module_name="app.utils",
            docstring="Utility functions.",
            classes=[],
            functions=[
                FunctionInfo(
                    name="helper",
                    args=[ArgumentInfo(name="value", annotation="str")],
                    return_annotation="str",
                    docstring="A helper utility function.",
                    line_number=5,
                    is_method=False,
                ),
                FunctionInfo(
                    name="_internal",
                    args=[],
                    return_annotation="None",
                    docstring=None,
                    line_number=12,
                    is_method=False,
                ),
            ],
            imports=[],
            line_count=25,
        ),
    ]

    graph = DependencyGraph(edges={
        "main":        ["app.service"],
        "app.service": ["app.utils"],
        "app.utils":   [],
    })

    manifest = CodebaseManifest(
        project_name="testapp",
        root_path=str(tmp_path),
        source="local",
        total_files=3,
        total_lines=125,
        files=files,
        stack=StackInfo(
            frameworks=["FastAPI"],
            databases=["SQLAlchemy"],
            test_frameworks=["pytest"],
            other_tools=["Pydantic"],
        ),
        dependency_graph=graph,
    )
    path = tmp_path / "manifest.json"
    manifest.save(path)
    return path, manifest


def make_initial_state(manifest_path: Path) -> DocState:
    return DocState(
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


# ── prompt renderer tests ────────────────────────────────────────

class TestPromptRenderer:
    def test_renders_architecture_template(self, tmp_path):
        rendered = render_prompt("architecture.j2", {
            "project_name":    "myapp",
            "total_files":     5,
            "total_lines":     200,
            "frameworks":      ["FastAPI"],
            "databases":       ["SQLAlchemy"],
            "test_frameworks": ["pytest"],
            "task_queues":     [],
            "other_tools":     ["Pydantic"],
            "entry_points":    ["main"],
            "core_modules":    ["app.utils"],
            "files":           [],
            "edges":           {},
        })
        assert "myapp" in rendered
        assert "FastAPI" in rendered
        assert "main" in rendered

    def test_renders_api_template(self):
        rendered = render_prompt("api.j2", {
            "project_name":       "myapp",
            "total_modules":      2,
            "total_public_items": 3,
            "modules":            [],
        })
        assert "myapp" in rendered
        assert "API reference" in rendered

    def test_strict_undefined_raises_on_missing_var(self):
        from jinja2 import UndefinedError
        with pytest.raises(UndefinedError):
            render_prompt("architecture.j2", {
                "project_name": "myapp",
            })


# ── architecture agent tests ──────────────────────────────────────

class TestArchitectureAgent:
    def test_produces_non_empty_output(self, tmp_path):
        path, manifest = make_rich_manifest(tmp_path)
        state = make_initial_state(path)
        state = planner_node(state)

        agent = ArchitectureAgent()
        result = agent.run(state)

        assert len(result["architecture_doc"]) > 100
        assert result["error"] is None

    def test_output_contains_markdown_headings(self, tmp_path):
        path, manifest = make_rich_manifest(tmp_path)
        state = make_initial_state(path)
        state = planner_node(state)

        agent = ArchitectureAgent()
        result = agent.run(state)
        doc = result["architecture_doc"]

        assert "##" in doc

    def test_prompt_contains_project_name(self, tmp_path):
        _, manifest = make_rich_manifest(tmp_path)
        agent = ArchitectureAgent()
        prompt = agent._build_prompt(manifest)
        assert "testapp" in prompt

    def test_prompt_contains_entry_points(self, tmp_path):
        _, manifest = make_rich_manifest(tmp_path)
        agent = ArchitectureAgent()
        prompt = agent._build_prompt(manifest)
        assert "main" in prompt

    def test_prompt_contains_dependency_edges(self, tmp_path):
        _, manifest = make_rich_manifest(tmp_path)
        agent = ArchitectureAgent()
        prompt = agent._build_prompt(manifest)
        assert "app.service" in prompt

    def test_prompt_contains_all_module_names(self, tmp_path):
        _, manifest = make_rich_manifest(tmp_path)
        agent = ArchitectureAgent()
        prompt = agent._build_prompt(manifest)
        assert "app.utils" in prompt
        assert "app.service" in prompt

    def test_prompt_contains_stack_info(self, tmp_path):
        _, manifest = make_rich_manifest(tmp_path)
        agent = ArchitectureAgent()
        prompt = agent._build_prompt(manifest)
        assert "FastAPI" in prompt
        assert "SQLAlchemy" in prompt


# ── api writer agent tests ────────────────────────────────────────

class TestAPIWriterAgent:
    def test_produces_non_empty_output(self, tmp_path):
        path, _ = make_rich_manifest(tmp_path)
        state = make_initial_state(path)
        state = planner_node(state)

        agent = APIWriterAgent()
        result = agent.run(state)

        assert len(result["api_doc"]) > 100
        assert result["error"] is None

    def test_prompt_includes_public_functions_only(self, tmp_path):
        _, manifest = make_rich_manifest(tmp_path)
        agent = APIWriterAgent()
        prompt = agent._build_prompt(manifest)

        assert "helper" in prompt
        assert "_internal" not in prompt

    def test_prompt_includes_public_methods_only(self, tmp_path):
        _, manifest = make_rich_manifest(tmp_path)
        agent = APIWriterAgent()
        prompt = agent._build_prompt(manifest)

        assert "process" in prompt
        assert "_validate" not in prompt

    def test_prompt_includes_type_annotations(self, tmp_path):
        _, manifest = make_rich_manifest(tmp_path)
        agent = APIWriterAgent()
        prompt = agent._build_prompt(manifest)

        assert "str" in prompt
        assert "dict" in prompt

    def test_prompt_includes_class_names(self, tmp_path):
        _, manifest = make_rich_manifest(tmp_path)
        agent = APIWriterAgent()
        prompt = agent._build_prompt(manifest)

        assert "Service" in prompt

    def test_prompt_includes_docstrings(self, tmp_path):
        _, manifest = make_rich_manifest(tmp_path)
        agent = APIWriterAgent()
        prompt = agent._build_prompt(manifest)

        assert "Process the input data" in prompt

    def test_skips_modules_with_no_public_items(self, tmp_path):
        manifest = CodebaseManifest(
            project_name="empty",
            root_path=str(tmp_path),
            source="local",
            total_files=1,
            total_lines=5,
            files=[
                FileInfo(
                    path="internal.py",
                    module_name="internal",
                    docstring=None,
                    classes=[],
                    functions=[
                        FunctionInfo(
                            name="_private",
                            args=[],
                            return_annotation=None,
                            docstring=None,
                            line_number=1,
                            is_method=False,
                        )
                    ],
                    imports=[],
                    line_count=5,
                )
            ],
        )
        agent = APIWriterAgent()
        prompt = agent._build_prompt(manifest)
        assert "_private" not in prompt
