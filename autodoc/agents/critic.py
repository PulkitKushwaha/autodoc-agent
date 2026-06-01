import json

from autodoc.agents.base import BaseAgent
from autodoc.logger import get_logger
from autodoc.models.doc_state import DocState
from autodoc.models.manifest import CodebaseManifest
from autodoc.utils.prompt_renderer import render_prompt

logger = get_logger(__name__)

REVISION_THRESHOLD = 7
MAX_REVISIONS = 2

SECTION_KEY_MAP = {
    "architecture": "architecture_doc",
    "api":          "api_doc",
    "db":           "db_doc",
    "auth":         "auth_doc",
    "deploy":       "deploy_doc",
}


class CriticAgent(BaseAgent):
    """
    Reviews all generated documentation sections for quality and completeness.

    Scores each section 1-10. Sections below REVISION_THRESHOLD are added
    to sections_to_revise. The pipeline routes those sections back to their
    writer agents for a second pass. Revision capped at MAX_REVISIONS to
    prevent infinite loops.
    """

    _state_key = "critique"
    _system = (
        "You are a strict but fair senior technical writer reviewing "
        "documentation quality. You respond only with valid JSON — "
        "no preamble, no explanation, no markdown code fences. "
        "Raw JSON only."
    )

    def run(self, state: DocState) -> DocState:
        """
        Override base run() — critic has custom state handling since it
        writes to multiple state keys (critique, quality_scores,
        sections_to_revise) rather than just one.
        """
        logger.info(
            "CriticAgent starting — project: %s | revision round: %d",
            state.get("project_name", "unknown"),
            state.get("revision_count", 0),
        )

        if state.get("error"):
            logger.warning(
                "CriticAgent skipping — upstream error: %s",
                state["error"],
            )
            return state

        try:
            manifest = self._load_manifest(state)
            prompt = self._build_prompt_from_state(state, manifest)

            logger.debug(
                "CriticAgent sending prompt — %d chars", len(prompt)
            )

            raw_response = self._llm.complete(
                prompt=prompt,
                system=self._system,
            )

            parsed = self._parse_response(raw_response)
            scores = parsed.get("scores", {})
            critiques = parsed.get("critiques", {})
            overall = parsed.get("overall_assessment", "")

            logger.info(
                "CriticAgent scores — %s",
                {k: v for k, v in scores.items()},
            )
            logger.info("CriticAgent overall: %s", overall)

            current_revisions = state.get("revision_count", 0)
            sections_to_revise = []

            if current_revisions < MAX_REVISIONS:
                sections_to_revise = [
                    section for section, score in scores.items()
                    if score < REVISION_THRESHOLD
                ]
                if sections_to_revise:
                    logger.info(
                        "CriticAgent flagging for revision: %s",
                        sections_to_revise,
                    )
                else:
                    logger.info(
                        "CriticAgent — all sections meet quality threshold"
                    )
            else:
                logger.info(
                    "CriticAgent — max revisions (%d) reached, accepting all",
                    MAX_REVISIONS,
                )

            return {
                **state,
                "critique":           critiques,
                "quality_scores":     scores,
                "sections_to_revise": sections_to_revise,
            }

        except Exception as e:
            logger.exception("CriticAgent failed: %s", e)
            return {
                **state,
                "critique":           {},
                "quality_scores":     {},
                "sections_to_revise": [],
            }

    def _build_prompt(self, manifest: CodebaseManifest) -> str:
        """Not used directly — critic uses _build_prompt_from_state instead."""
        return ""

    def _build_prompt_from_state(
        self,
        state: DocState,
        manifest: CodebaseManifest,
    ) -> str:
        """Build the critic prompt from current state doc sections."""
        sections_to_write = state.get(
            "sections_to_write", list(SECTION_KEY_MAP.keys())
        )

        sections = []
        for section_name in sections_to_write:
            state_key = SECTION_KEY_MAP.get(section_name, f"{section_name}_doc")
            content = state.get(state_key, "")
            if content:
                sections.append({
                    "name":    section_name,
                    "content": content,
                })
                logger.debug(
                    "CriticAgent reviewing section: %s (%d chars)",
                    section_name,
                    len(content),
                )

        return render_prompt("critic.j2", {
            "project_name":     manifest.project_name,
            "manifest_summary": manifest.summary(),
            "sections":         sections,
        })

    def _parse_response(self, raw: str) -> dict:
        """
        Parse the LLM's JSON response.
        Strips markdown code fences if the model included them.
        Returns empty dicts on malformed JSON — pipeline never crashes.
        """
        cleaned = raw.strip()

        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(
                line for line in lines
                if not line.startswith("```")
            ).strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(
                "CriticAgent failed to parse JSON response: %s\nRaw: %s",
                e,
                raw[:200],
            )
            return {"scores": {}, "critiques": {}, "overall_assessment": ""}
