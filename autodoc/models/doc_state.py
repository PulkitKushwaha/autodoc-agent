from typing import TypedDict, Optional


class DocState(TypedDict):
    """
    The single state object that flows through the entire LangGraph pipeline.

    Every node receives this dict, reads what it needs, writes its output
    to its designated key, and returns the updated dict. LangGraph merges
    the returned keys back into the shared state automatically.

    Keys added by each stage:
        planner        → project_name, manifest_summary, sections_to_write
        writer agents  → architecture_doc, api_doc, db_doc, auth_doc, deploy_doc
        assembler      → final_docs, is_complete
    """
    project_name: str
    manifest_path: str
    manifest_summary: str
    sections_to_write: list[str]

    architecture_doc: str
    api_doc: str
    db_doc: str
    auth_doc: str
    deploy_doc: str

    final_docs: dict[str, str]
    is_complete: bool
    error: Optional[str]
