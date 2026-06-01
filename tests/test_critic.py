from pathlib import Path
import json
import pytest

from autodoc.models.doc_state import DocState
from autodoc.models.manifest import (
    CodebaseManifest, StackInfo, DependencyGraph,
)
from autodoc.agents.critic import CriticAgent, REVISION_THRESHOLD, MAX_REVISIONS
from autodoc.graph.pipeline import (
    assembler_node, should_revise, revision_router_node
)


# ── helpers ──────────────────────────────────────────────────────

def make_manifest(tmp_path: Path) -> tuple[Path, CodebaseManifest]:
    manifest = CodebaseManifest(
        project_name="testproject",
        root_path=str(tmp_path),
        source="local",
        total_files=5,
        total_lines=200,
        stack=StackInfo(frameworks=["FastAPI"]),
        dependency_graph=DependencyGraph(),
    )
    path = tmp_path / "manifest.json"
    manifest.save(path)
    return path, manifest


def make_state_with_docs(tmp_path: Path) -> DocState:
    path, _ = make_manifest(tmp_path)
    return DocState(
        project_name="testproject",
        manifest_path=str(path),
        manifest_summary="Test project summary.",
        sections_to_write=["architecture", "api", "db", "auth", "deploy"],
        architecture_doc="## Architecture\nThis is the architecture section.",
        api_doc="## API\nThis is the API reference section.",
        db_doc="## Data models\nThis is the data models section.",
        auth_doc="## Auth\nThis is the authentication section.",
        deploy_doc="## Deployment\nThis is the deployment section.",
        critique={},
        quality_scores={},
        sections_to_revise=[],
        revision_count=0,
        final_docs={},
        is_complete=False,
        error=None,
    )


# ── critic agent tests ───────────────────────────────────────────

class TestCriticAgent:
    def test_produces_scores_for_all_sections(self, tmp_path):
        state = make_state_with_docs(tmp_path)
        agent = CriticAgent()
        result = agent.run(state)

        assert isinstance(result["quality_scores"], dict)
        assert len(result["quality_scores"]) > 0

    def test_produces_critiques_for_all_sections(self, tmp_path):
        state = make_state_with_docs(tmp_path)
        agent = CriticAgent()
        result = agent.run(state)

        assert isinstance(result["critique"], dict)

    def test_flags_low_scoring_sections_for_revision(self, tmp_path):
        state = make_state_with_docs(tmp_path)
        agent = CriticAgent()
        result = agent.run(state)

        for section in result["sections_to_revise"]:
            score = result["quality_scores"].get(section, 10)
            assert score < REVISION_THRESHOLD

    def test_does_not_flag_high_scoring_sections(self, tmp_path):
        state = make_state_with_docs(tmp_path)
        agent = CriticAgent()
        result = agent.run(state)

        for section, score in result["quality_scores"].items():
            if score >= REVISION_THRESHOLD:
                assert section not in result["sections_to_revise"]

    def test_skips_on_upstream_error(self, tmp_path):
        state = make_state_with_docs(tmp_path)
        state["error"] = "upstream failure"

        agent = CriticAgent()
        result = agent.run(state)

        assert result["error"] == "upstream failure"
        assert result["quality_scores"] == {}

    def test_parse_response_handles_json_fences(self, tmp_path):
        agent = CriticAgent()
        raw = '```json\n{"scores": {"arch": 8}, "critiques": {}, "overall_assessment": "ok"}\n```'
        parsed = agent._parse_response(raw)
        assert parsed["scores"]["arch"] == 8

    def test_parse_response_handles_clean_json(self, tmp_path):
        agent = CriticAgent()
        raw = '{"scores": {"arch": 9}, "critiques": {}, "overall_assessment": "good"}'
        parsed = agent._parse_response(raw)
        assert parsed["scores"]["arch"] == 9

    def test_parse_response_handles_malformed_json(self, tmp_path):
        agent = CriticAgent()
        raw = "this is not json at all"
        parsed = agent._parse_response(raw)
        assert parsed == {
            "scores": {},
            "critiques": {},
            "overall_assessment": "",
        }

    def test_max_revisions_prevents_infinite_loop(self, tmp_path):
        state = make_state_with_docs(tmp_path)
        state["revision_count"] = MAX_REVISIONS

        agent = CriticAgent()
        result = agent.run(state)

        assert result["sections_to_revise"] == []


# ── conditional edge tests ───────────────────────────────────────

class TestShouldRevise:
    def test_returns_revise_when_sections_flagged(self, tmp_path):
        state = make_state_with_docs(tmp_path)
        state["sections_to_revise"] = ["db"]
        state["revision_count"] = 0

        assert should_revise(state) == "revise"

    def test_returns_done_when_no_sections_flagged(self, tmp_path):
        state = make_state_with_docs(tmp_path)
        state["sections_to_revise"] = []
        state["revision_count"] = 0

        assert should_revise(state) == "done"

    def test_returns_done_when_max_revisions_reached(self, tmp_path):
        state = make_state_with_docs(tmp_path)
        state["sections_to_revise"] = ["db", "auth"]
        state["revision_count"] = MAX_REVISIONS

        assert should_revise(state) == "done"


# ── revision router tests ────────────────────────────────────────

class TestRevisionRouter:
    def test_increments_revision_count(self, tmp_path):
        state = make_state_with_docs(tmp_path)
        state["revision_count"] = 0

        result = revision_router_node(state)
        assert result["revision_count"] == 1

    def test_preserves_existing_docs(self, tmp_path):
        state = make_state_with_docs(tmp_path)
        state["revision_count"] = 0

        result = revision_router_node(state)
        assert result["architecture_doc"] == state["architecture_doc"]
        assert result["api_doc"] == state["api_doc"]


# ── assembler tests ───────────────────────────────────────────────

class TestAssemblerWithScores:
    def test_includes_quality_scores_in_log(self, tmp_path):
        state = make_state_with_docs(tmp_path)
        state["sections_to_write"] = ["architecture", "api"]
        state["quality_scores"] = {"architecture": 8, "api": 9}

        result = assembler_node(state)
        assert result["is_complete"] is True
        assert "architecture" in result["final_docs"]
        assert "api" in result["final_docs"]

    def test_marks_incomplete_on_upstream_error(self, tmp_path):
        state = make_state_with_docs(tmp_path)
        state["error"] = "something broke"
        result = assembler_node(state)
        assert result["is_complete"] is False


# ── full pipeline with critic loop tests ─────────────────────────

class TestFullPipelineWithCritic:
    def test_pipeline_runs_end_to_end(self, tmp_path):
        from autodoc.graph.pipeline import build_graph

        path, _ = make_manifest(tmp_path)
        initial = DocState(
            project_name="",
            manifest_path=str(path),
            manifest_summary="",
            sections_to_write=[],
            architecture_doc="",
            api_doc="",
            db_doc="",
            auth_doc="",
            deploy_doc="",
            critique={},
            quality_scores={},
            sections_to_revise=[],
            revision_count=0,
            final_docs={},
            is_complete=False,
            error=None,
        )

        graph = build_graph()
        result = graph.invoke(initial)

        assert result["is_complete"] is True
        assert len(result["final_docs"]) > 0
        assert isinstance(result["quality_scores"], dict)

    def test_revision_count_within_bounds(self, tmp_path):
        from autodoc.graph.pipeline import build_graph

        path, _ = make_manifest(tmp_path)
        initial = DocState(
            project_name="",
            manifest_path=str(path),
            manifest_summary="",
            sections_to_write=[],
            architecture_doc="",
            api_doc="",
            db_doc="",
            auth_doc="",
            deploy_doc="",
            critique={},
            quality_scores={},
            sections_to_revise=[],
            revision_count=0,
            final_docs={},
            is_complete=False,
            error=None,
        )

        graph = build_graph()
        result = graph.invoke(initial)

        assert result["revision_count"] >= 0
        assert result["revision_count"] <= MAX_REVISIONS

    def test_db_section_was_revised_in_mock_mode(self, tmp_path):
        from autodoc.graph.pipeline import build_graph

        path, _ = make_manifest(tmp_path)
        initial = DocState(
            project_name="",
            manifest_path=str(path),
            manifest_summary="",
            sections_to_write=[],
            architecture_doc="",
            api_doc="",
            db_doc="",
            auth_doc="",
            deploy_doc="",
            critique={},
            quality_scores={},
            sections_to_revise=[],
            revision_count=0,
            final_docs={},
            is_complete=False,
            error=None,
        )

        graph = build_graph()
        result = graph.invoke(initial)

        # In mock mode, db scores 6 initially (below threshold=7)
        # so revision_count should be at least 1
        assert result["revision_count"] >= 1
