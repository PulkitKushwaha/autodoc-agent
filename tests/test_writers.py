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

# ── Day 4 additions — append to the bottom of tests/test_writers.py ──


def make_auth_manifest(tmp_path: Path) -> tuple[Path, CodebaseManifest]:
    """Manifest with auth-related modules and classes."""
    files = [
        FileInfo(
            path="app/auth.py",
            module_name="app.auth",
            docstring="Authentication module.",
            classes=[
                ClassInfo(
                    name="JWTHandler",
                    bases=["BaseHandler"],
                    docstring="Handles JWT token creation and validation.",
                    methods=[
                        FunctionInfo(
                            name="create_token",
                            args=[ArgumentInfo(name="user_id", annotation="str")],
                            return_annotation="str",
                            docstring="Create a signed JWT token.",
                            line_number=10,
                            is_method=True,
                        ),
                        FunctionInfo(
                            name="verify_token",
                            args=[ArgumentInfo(name="token", annotation="str")],
                            return_annotation="bool",
                            docstring="Verify token signature and expiry.",
                            line_number=20,
                            is_method=True,
                        ),
                    ],
                    line_number=5,
                )
            ],
            functions=[
                FunctionInfo(
                    name="get_current_user",
                    args=[ArgumentInfo(name="token", annotation="str")],
                    return_annotation="User",
                    docstring="Dependency: extract current user from token.",
                    line_number=35,
                    is_method=False,
                )
            ],
            imports=[],
            line_count=50,
        ),
        FileInfo(
            path="app/middleware.py",
            module_name="app.middleware",
            docstring="Auth middleware.",
            classes=[
                ClassInfo(
                    name="AuthMiddleware",
                    bases=["BaseMiddleware"],
                    docstring="Validates Bearer token on every request.",
                    methods=[],
                    line_number=5,
                )
            ],
            functions=[],
            imports=[],
            line_count=30,
        ),
    ]

    manifest = CodebaseManifest(
        project_name="authapp",
        root_path=str(tmp_path),
        source="local",
        total_files=2,
        total_lines=80,
        files=files,
        stack=StackInfo(
            frameworks=["FastAPI"],
            other_tools=["PyJWT", "Pydantic"],
        ),
        dependency_graph=DependencyGraph(),
    )
    path = tmp_path / "manifest.json"
    manifest.save(path)
    return path, manifest


def make_db_manifest(tmp_path: Path) -> tuple[Path, CodebaseManifest]:
    """Manifest with SQLAlchemy and Pydantic model classes."""
    files = [
        FileInfo(
            path="app/models.py",
            module_name="app.models",
            docstring="Database models.",
            classes=[
                ClassInfo(
                    name="User",
                    bases=["Base"],
                    docstring="User database model.",
                    methods=[
                        FunctionInfo(
                            name="__repr__",
                            args=[],
                            return_annotation="str",
                            docstring=None,
                            line_number=15,
                            is_method=True,
                        )
                    ],
                    line_number=5,
                ),
                ClassInfo(
                    name="Post",
                    bases=["Base"],
                    docstring="Post database model.",
                    methods=[],
                    line_number=25,
                ),
            ],
            functions=[],
            imports=[],
            line_count=60,
        ),
        FileInfo(
            path="app/schemas.py",
            module_name="app.schemas",
            docstring="Pydantic schemas.",
            classes=[
                ClassInfo(
                    name="UserCreate",
                    bases=["BaseModel"],
                    docstring="Schema for user creation.",
                    methods=[],
                    line_number=5,
                ),
                ClassInfo(
                    name="UserRead",
                    bases=["BaseModel"],
                    docstring="Schema for user read response.",
                    methods=[],
                    line_number=15,
                ),
            ],
            functions=[],
            imports=[],
            line_count=30,
        ),
    ]

    manifest = CodebaseManifest(
        project_name="dbapp",
        root_path=str(tmp_path),
        source="local",
        total_files=2,
        total_lines=90,
        files=files,
        stack=StackInfo(
            databases=["SQLAlchemy", "Alembic"],
            other_tools=["Pydantic"],
        ),
        dependency_graph=DependencyGraph(),
    )
    path = tmp_path / "manifest.json"
    manifest.save(path)
    return path, manifest


class TestDBWriterAgent:
    def test_produces_non_empty_output(self, tmp_path):
        from autodoc.agents.db_writer import DBWriterAgent
        path, _ = make_db_manifest(tmp_path)
        state = make_initial_state(path)
        state = planner_node(state)

        agent = DBWriterAgent()
        result = agent.run(state)

        assert len(result["db_doc"]) > 100
        assert result["error"] is None

    def test_prompt_contains_model_class_names(self, tmp_path):
        from autodoc.agents.db_writer import DBWriterAgent
        _, manifest = make_db_manifest(tmp_path)
        agent = DBWriterAgent()
        prompt = agent._build_prompt(manifest)

        assert "User" in prompt
        assert "Post" in prompt

    def test_prompt_contains_pydantic_models(self, tmp_path):
        from autodoc.agents.db_writer import DBWriterAgent
        _, manifest = make_db_manifest(tmp_path)
        agent = DBWriterAgent()
        prompt = agent._build_prompt(manifest)

        assert "UserCreate" in prompt
        assert "UserRead" in prompt

    def test_prompt_contains_detected_databases(self, tmp_path):
        from autodoc.agents.db_writer import DBWriterAgent
        _, manifest = make_db_manifest(tmp_path)
        agent = DBWriterAgent()
        prompt = agent._build_prompt(manifest)

        assert "SQLAlchemy" in prompt
        assert "Alembic" in prompt

    def test_detects_base_model_inheritance(self, tmp_path):
        from autodoc.agents.db_writer import DBWriterAgent
        _, manifest = make_db_manifest(tmp_path)
        agent = DBWriterAgent()
        pydantic = agent._extract_pydantic_models(manifest)

        names = [m["name"] for m in pydantic]
        assert "UserCreate" in names
        assert "UserRead" in names
        assert "User" not in names

    def test_detects_orm_model_inheritance(self, tmp_path):
        from autodoc.agents.db_writer import DBWriterAgent
        _, manifest = make_db_manifest(tmp_path)
        agent = DBWriterAgent()
        models = agent._extract_model_classes(manifest)

        names = [m["name"] for m in models]
        assert "User" in names
        assert "Post" in names

    def test_no_models_detected_gracefully(self, tmp_path):
        from autodoc.agents.db_writer import DBWriterAgent
        manifest = CodebaseManifest(
            project_name="nomodels",
            root_path=str(tmp_path),
            source="local",
            total_files=1,
            total_lines=10,
            files=[],
        )
        agent = DBWriterAgent()
        prompt = agent._build_prompt(manifest)
        assert "nomodels" in prompt


class TestAuthWriterAgent:
    def test_produces_non_empty_output(self, tmp_path):
        from autodoc.agents.auth_writer import AuthWriterAgent
        path, _ = make_auth_manifest(tmp_path)
        state = make_initial_state(path)
        state = planner_node(state)

        agent = AuthWriterAgent()
        result = agent.run(state)

        assert len(result["auth_doc"]) > 100
        assert result["error"] is None

    def test_detects_auth_modules_by_name(self, tmp_path):
        from autodoc.agents.auth_writer import AuthWriterAgent
        _, manifest = make_auth_manifest(tmp_path)
        agent = AuthWriterAgent()
        modules = agent._extract_auth_modules(manifest)

        module_names = [m["module_name"] for m in modules]
        assert "app.auth" in module_names
        assert "app.middleware" in module_names

    def test_detects_auth_classes_by_name(self, tmp_path):
        from autodoc.agents.auth_writer import AuthWriterAgent
        _, manifest = make_auth_manifest(tmp_path)
        agent = AuthWriterAgent()
        classes = agent._extract_auth_classes(manifest)

        class_names = [c["name"] for c in classes]
        assert "JWTHandler" in class_names
        assert "AuthMiddleware" in class_names

    def test_prompt_contains_auth_class_names(self, tmp_path):
        from autodoc.agents.auth_writer import AuthWriterAgent
        _, manifest = make_auth_manifest(tmp_path)
        agent = AuthWriterAgent()
        prompt = agent._build_prompt(manifest)

        assert "JWTHandler" in prompt
        assert "AuthMiddleware" in prompt

    def test_prompt_contains_auth_function_names(self, tmp_path):
        from autodoc.agents.auth_writer import AuthWriterAgent
        _, manifest = make_auth_manifest(tmp_path)
        agent = AuthWriterAgent()
        prompt = agent._build_prompt(manifest)

        assert "get_current_user" in prompt

    def test_detects_pyjwt_library(self, tmp_path):
        from autodoc.agents.auth_writer import AuthWriterAgent
        _, manifest = make_auth_manifest(tmp_path)
        agent = AuthWriterAgent()
        libraries = agent._detect_auth_libraries(manifest)

        assert any("JWT" in lib for lib in libraries)

    def test_no_auth_modules_handled_gracefully(self, tmp_path):
        from autodoc.agents.auth_writer import AuthWriterAgent
        manifest = CodebaseManifest(
            project_name="noauth",
            root_path=str(tmp_path),
            source="local",
            total_files=1,
            total_lines=10,
            files=[],
        )
        agent = AuthWriterAgent()
        prompt = agent._build_prompt(manifest)
        assert "noauth" in prompt


class TestDeployWriterAgent:
    def test_produces_non_empty_output(self, tmp_path):
        from autodoc.agents.deploy_writer import DeployWriterAgent
        path, _ = make_rich_manifest(tmp_path)
        state = make_initial_state(path)
        state = planner_node(state)

        agent = DeployWriterAgent()
        result = agent.run(state)

        assert len(result["deploy_doc"]) > 100
        assert result["error"] is None

    def test_detects_pyproject_toml(self, tmp_path):
        from autodoc.agents.deploy_writer import DeployWriterAgent
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname="test"\n'
        )
        (tmp_path / "uv.lock").write_text("")
        manifest = CodebaseManifest(
            project_name="test",
            root_path=str(tmp_path),
            source="local",
            total_files=1,
            total_lines=10,
            files=[],
        )
        agent = DeployWriterAgent()
        pm, config, has_lock = agent._detect_package_manager(tmp_path)

        assert pm == "uv"
        assert config == "pyproject.toml"
        assert has_lock is True

    def test_detects_requirements_txt_fallback(self, tmp_path):
        from autodoc.agents.deploy_writer import DeployWriterAgent
        (tmp_path / "requirements.txt").write_text("flask\n")
        manifest = CodebaseManifest(
            project_name="test",
            root_path=str(tmp_path),
            source="local",
            total_files=1,
            total_lines=10,
            files=[],
        )
        agent = DeployWriterAgent()
        pm, config, has_lock = agent._detect_package_manager(tmp_path)

        assert pm == "pip"
        assert config == "requirements.txt"

    def test_detects_dockerfile(self, tmp_path):
        from autodoc.agents.deploy_writer import DeployWriterAgent
        (tmp_path / "Dockerfile").write_text("FROM python:3.11\n")
        manifest = CodebaseManifest(
            project_name="test",
            root_path=str(tmp_path),
            source="local",
            total_files=1,
            total_lines=10,
            files=[],
        )
        agent = DeployWriterAgent()
        cicd = agent._detect_cicd_files(tmp_path)

        assert "Dockerfile" in cicd

    def test_prompt_contains_stack_info(self, tmp_path):
        from autodoc.agents.deploy_writer import DeployWriterAgent
        _, manifest = make_rich_manifest(tmp_path)
        agent = DeployWriterAgent()
        prompt = agent._build_prompt(manifest)

        assert "FastAPI" in prompt
        assert "SQLAlchemy" in prompt

    def test_no_cicd_handled_gracefully(self, tmp_path):
        from autodoc.agents.deploy_writer import DeployWriterAgent
        manifest = CodebaseManifest(
            project_name="bareproject",
            root_path=str(tmp_path),
            source="local",
            total_files=1,
            total_lines=10,
            files=[],
        )
        agent = DeployWriterAgent()
        prompt = agent._build_prompt(manifest)
        assert "bareproject" in prompt
