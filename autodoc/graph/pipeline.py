from langgraph.graph import StateGraph, START, END

from autodoc.agents.architecture import ArchitectureAgent
from autodoc.agents.api_writer import APIWriterAgent
from autodoc.agents.auth_writer import AuthWriterAgent
from autodoc.agents.db_writer import DBWriterAgent
from autodoc.agents.deploy_writer import DeployWriterAgent
from autodoc.agents.planner import planner_node
from autodoc.logger import get_logger
from autodoc.models.doc_state import DocState

logger = get_logger(__name__)


def assembler_node(state: DocState) -> DocState:
    """
    Final node — collects all written sections into final_docs dict
    and marks the pipeline as complete.
    """
    logger.info("Assembler running — collecting all sections")

    if state.get("error"):
        logger.error("Assembler found upstream error: %s", state["error"])
        return {**state, "is_complete": False}

    final_docs: dict[str, str] = {}

    section_map = {
        "architecture": state.get("architecture_doc", ""),
        "api":          state.get("api_doc", ""),
        "db":           state.get("db_doc", ""),
        "auth":         state.get("auth_doc", ""),
        "deploy":       state.get("deploy_doc", ""),
    }

    sections_written = state.get("sections_to_write", list(section_map.keys()))
    for key in sections_written:
        content = section_map.get(key, "")
        if content:
            final_docs[key] = content
            logger.info("Assembled section: %s (%d chars)", key, len(content))
        else:
            logger.warning("Section missing or empty: %s", key)

    logger.info(
        "Assembler complete — %d/%d sections written",
        len(final_docs),
        len(sections_written),
    )

    return {
        **state,
        "final_docs": final_docs,
        "is_complete": len(final_docs) > 0,
    }


def build_graph() -> StateGraph:
    """
    Wire the full LangGraph pipeline.

    Flow: START → planner → [5 writers in parallel] → assembler → END

    Note: LangGraph runs nodes added without conditional edges sequentially
    in the order they were added. True parallel execution requires
    Send() API — added in Day 5 when we have the full writer set.
    For now, nodes run sequentially which is correct for development.
    """
    logger.info("Building LangGraph pipeline")

    arch_agent   = ArchitectureAgent()
    api_agent    = APIWriterAgent()
    db_agent     = DBWriterAgent()
    auth_agent   = AuthWriterAgent()
    deploy_agent = DeployWriterAgent()

    graph = StateGraph(DocState)

    graph.add_node("planner",      planner_node)
    graph.add_node("architecture", arch_agent.run)
    graph.add_node("api_writer",   api_agent.run)
    graph.add_node("db_writer",    db_agent.run)
    graph.add_node("auth_writer",  auth_agent.run)
    graph.add_node("deploy_writer",deploy_agent.run)
    graph.add_node("assembler",    assembler_node)

    graph.add_edge(START,           "planner")
    graph.add_edge("planner",       "architecture")
    graph.add_edge("architecture",  "api_writer")
    graph.add_edge("api_writer",    "db_writer")
    graph.add_edge("db_writer",     "auth_writer")
    graph.add_edge("auth_writer",   "deploy_writer")
    graph.add_edge("deploy_writer", "assembler")
    graph.add_edge("assembler",     END)

    logger.info("Pipeline built — 7 nodes, 8 edges")
    return graph.compile()
