from autodoc.logger import get_logger
from autodoc.models.doc_state import DocState
from autodoc.models.manifest import CodebaseManifest
from pathlib import Path

logger = get_logger(__name__)

SECTIONS = [
    "architecture",
    "api",
    "db",
    "auth",
    "deploy",
]


def planner_node(state: DocState) -> DocState:
    """
    Entry node of the LangGraph pipeline.

    Loads the CodebaseManifest, populates the initial DocState fields
    that all downstream agents depend on, and determines which sections
    need to be written based on what the codebase actually contains.
    """
    logger.info("Planner starting — manifest: %s", state["manifest_path"])

    try:
        manifest = CodebaseManifest.load(Path(state["manifest_path"]))
    except Exception as e:
        logger.error("Planner failed to load manifest: %s", e)
        return {**state, "error": f"Failed to load manifest: {e}"}

    sections = _determine_sections(manifest)
    logger.info("Planner determined sections to write: %s", sections)

    updated = {
        **state,
        "project_name": manifest.project_name,
        "manifest_summary": manifest.summary(),
        "sections_to_write": sections,
        "architecture_doc": "",
        "api_doc": "",
        "db_doc": "",
        "auth_doc": "",
        "deploy_doc": "",
        "final_docs": {},
        "is_complete": False,
        "error": None,
    }

    logger.info(
        "Planner complete — project: %s | sections: %d | "
        "files: %d | lines: %d",
        manifest.project_name,
        len(sections),
        manifest.total_files,
        manifest.total_lines,
    )
    return updated


def _determine_sections(manifest: CodebaseManifest) -> list[str]:
    """
    Decide which sections are worth writing based on what
    the manifest actually detected in the codebase.
    Always includes architecture. Others are conditional.
    """
    sections = ["architecture"]

    has_functions = any(f.functions or f.classes for f in manifest.files)
    if has_functions:
        sections.append("api")

    if manifest.stack.databases:
        sections.append("db")

    has_auth = any(
        "auth" in f.module_name.lower() or "security" in f.module_name.lower()
        for f in manifest.files
    ) or any(
        kw in str(manifest.stack.other_tools).lower()
        for kw in ("jwt", "oauth", "auth")
    )
    if has_auth:
        sections.append("auth")

    sections.append("deploy")

    logger.debug("Section determination — %s", sections)
    return sections
