from pathlib import Path
from unittest.mock import patch
import pytest

from autodoc.models.doc_state import DocState
from autodoc.agents.planner import planner_node, _determine_sections
from autodoc.agents.architecture import ArchitectureAgent
from autodoc.models.manifest import (
    CodebaseManifest, StackInfo, DependencyGraph,
    FileInfo, ClassInfo, FunctionInfo, ArgumentInfo
)


def make_manifest(tmp_path: Path, **kwargs) -> tuple[Path, CodebaseManifest]:
    manifest = CodebaseManifest(
        project_name=kwargs.get("project_name", "testproject"),
        root_path=str(tmp_path),
        source="local",
        total_files=kwargs.get("total_files", 3),
        total_lines=kwargs.get("total_lines", 100),
        files=kwargs.get("files", []),
        stack=kwargs.get("stack", StackInfo(frameworks=["FastAPI"], databases=["SQLAlchemy"])),
        dependency_graph=kwargs.get("dependency_graph", DependencyGraph()),
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


class TestPlannerNode:
    def test_populates_project_name(self, tmp_path):
        path, _ = make_manifest(tmp_path, project_name="myapp")
        state = make_initial_state(path)
        result = planner_node(state)
        assert result["project_name"] == "myapp"

    def test_populates_manifest_summary(self, tmp_path):
        path, _ = make_manifest(tmp_path)
        state = make_initial_state(path)
        result = planner_node(state)
        assert len(result["manifest_summary"]) > 0

    def test_always_includes_architecture(self, tmp_path):
        path, _ = make_manifest(tmp_path)
        state = make_initial_state(path)
        result = planner_node(state)
        assert "architecture" in result["sections_to_write"]

    def test_includes_db_when_database_detected(self, tmp_path):
        stack = StackInfo(databases=["SQLAlchemy"])
        path, _ = make_manifest(tmp_path, stack=stack)
        state = make_initial_state(path)
        result = planner_node(state)
        assert "db" in result["sections_to_write"]

    def test_skips_db_when_no_database(self, tmp_path):
        stack = StackInfo(databases=[])
        path, _ = make_manifest(tmp_path, stack=stack)
        state = make_initial_state(path)
        result = planner_node(state)
        assert "db" not in result["sections_to_write"]

    def test_error_on_missing_manifest(self, tmp_path):
        state = make_initial_state(tmp_path / "nonexistent.json")
        result = planner_node(state)
        assert result["error"] is not None

    def test_clears_error_field_on_success(self, tmp_path):
        path, _ = make_manifest(tmp_path)
        state = make_initial_state(path)
        result = planner_node(state)
        assert result["error"] is None


class TestBaseAgentErrorHandling:
    def test_agent_skips_on_upstream_error(self, tmp_path):
        path, _ = make_manifest(tmp_path)
        state = make_initial_state(path)
        state["error"] = "upstream failure"

        agent = ArchitectureAgent()
        result = agent.run(state)

        assert result["error"] == "upstream failure"
        assert result["architecture_doc"] == ""

    def test_agent_writes_to_correct_state_key(self, tmp_path):
        path, _ = make_manifest(tmp_path)
        state = make_initial_state(path)
        planner_result = planner_node(state)

        agent = ArchitectureAgent()
        result = agent.run(planner_result)

        assert len(result["architecture_doc"]) > 0
        assert result["error"] is None


class TestAssemblerNode:
    def test_assembles_all_sections(self, tmp_path):
        from autodoc.graph.pipeline import assembler_node
        path, _ = make_manifest(tmp_path)
        state = make_initial_state(path)
        state.update({
            "sections_to_write": ["architecture", "api"],
            "architecture_doc": "## Architecture\ncontent here",
            "api_doc": "## API\ncontent here",
        })
        result = assembler_node(state)
        assert result["is_complete"] is True
        assert "architecture" in result["final_docs"]
        assert "api" in result["final_docs"]

    def test_marks_incomplete_on_upstream_error(self, tmp_path):
        from autodoc.graph.pipeline import assembler_node
        path, _ = make_manifest(tmp_path)
        state = make_initial_state(path)
        state["error"] = "something broke"
        result = assembler_node(state)
        assert result["is_complete"] is False


class TestFullPipeline:
    def test_pipeline_runs_end_to_end(self, tmp_path):
        from autodoc.graph.pipeline import build_graph
        path, _ = make_manifest(tmp_path, project_name="e2e_test")
        initial = make_initial_state(path)

        graph = build_graph()
        result = graph.invoke(initial)

        assert result["project_name"] == "e2e_test"
        assert result["is_complete"] is True
        assert len(result["final_docs"]) > 0
