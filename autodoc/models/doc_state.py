from typing import TypedDict, Optional


class DocState(TypedDict):
    """
    The single state object that flows through the entire LangGraph pipeline.
    Every node receives this dict, reads what it needs, writes its output
    to its designated key, and returns the updated dict. LangGraph merges
    the returned keys back into the shared state automatically.

    Keys added by each stage:
        main.py        → manifest_path
        planner        → project_name, manifest_summary, sections_to_write
        writer agents  → architecture_doc, api_doc, db_doc, auth_doc, deploy_doc
        critic         → critique, quality_scores, sections_to_revise
        assembler      → final_docs, is_complete
    """
    # — seeded by main.py —
    manifest_path: str

    # — seeded by planner —
    project_name: str
    manifest_summary: str
    sections_to_write: list[str]

    # — written by writer agents —
    architecture_doc: str
    api_doc: str
    db_doc: str
    auth_doc: str
    deploy_doc: str

    # — written by critic —
    critique: dict[str, str]
    quality_scores: dict[str, int]
    sections_to_revise: list[str]
    revision_count: int

    # — written by assembler —
    final_docs: dict[str, str]
    is_complete: bool

    # — written by any node on failure —
    error: Optional[str]
