from langgraph.graph import StateGraph, START, END

from autodoc.agents.architecture import ArchitectureAgent
from autodoc.agents.api_writer import APIWriterAgent
from autodoc.agents.auth_writer import AuthWriterAgent
from autodoc.agents.critic import CriticAgent, MAX_REVISIONS
from autodoc.agents.db_writer import DBWriterAgent
from autodoc.agents.deploy_writer import DeployWriterAgent
from autodoc.agents.planner import planner_node
from autodoc.logger import get_logger
from autodoc.models.doc_state import DocState

logger = get_logger(__name__)

SECTION_KEY_MAP = {
    "architecture": "architecture_doc",
    "api":          "api_doc",
    "db":           "db_doc",
    "auth":         "auth_doc",
    "deploy":       "deploy_doc",
}


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

    sections_to_write = state.get(
        "sections_to_write", list(section_map.keys())
    )

    for key in sections_to_write:
        content = section_map.get(key, "")
        if content:
            final_docs[key] = content
            score = state.get("quality_scores", {}).get(key, "unscored")
            logger.info(
                "Assembled section: %s (%d chars) score: %s",
                key, len(content), score,
            )
        else:
            logger.warning("Section missing or empty: %s", key)

    logger.info(
        "Assembler complete — %d/%d sections written",
        len(final_docs),
        len(sections_to_write),
    )

    return {
        **state,
        "final_docs":  final_docs,
        "is_complete": len(final_docs) > 0,
    }


def revision_router_node(state: DocState) -> DocState:
    """
    Increments revision_count. Writers re-run with critique context
    and overwrite their own state keys.
    """
    sections_to_revise = state.get("sections_to_revise", [])
    current_count = state.get("revision_count", 0)

    logger.info(
        "RevisionRouter — sections to revise: %s | round: %d",
        sections_to_revise,
        current_count + 1,
    )

    return {
        **state,
        "revision_count": current_count + 1,
    }


def should_revise(state: DocState) -> str:
    """
    Conditional edge function called after critic node.
    Returns 'revise' if any sections need work, 'done' otherwise.
    """
    sections_to_revise = state.get("sections_to_revise", [])
    revision_count = state.get("revision_count", 0)

    if sections_to_revise and revision_count < MAX_REVISIONS:
        logger.info(
            "should_revise → revise (sections: %s, round: %d)",
            sections_to_revise, revision_count,
        )
        return "revise"

    logger.info(
        "should_revise → done (no revisions needed or max reached)"
    )
    return "done"


def build_graph() -> StateGraph:
    """
    Wire the full LangGraph pipeline with critic and refinement loop.

    Flow:
    START → planner → arch → api → db → auth → deploy → critic
                                                            ↓
                                              should_revise()
                                             /              \\
                                         revise            done
                                            ↓               ↓
                                    revision_router     assembler → END
                                            ↓
                              (back through all writers)
                                            ↓
                                         critic (again, capped at MAX_REVISIONS)
    """
    logger.info("Building LangGraph pipeline with critic refinement loop")

    arch_agent   = ArchitectureAgent()
    api_agent    = APIWriterAgent()
    db_agent     = DBWriterAgent()
    auth_agent   = AuthWriterAgent()
    deploy_agent = DeployWriterAgent()
    critic_agent = CriticAgent()

    graph = StateGraph(DocState)

    graph.add_node("planner",         planner_node)
    graph.add_node("architecture",    arch_agent.run)
    graph.add_node("api_writer",      api_agent.run)
    graph.add_node("db_writer",       db_agent.run)
    graph.add_node("auth_writer",     auth_agent.run)
    graph.add_node("deploy_writer",   deploy_agent.run)
    graph.add_node("critic",          critic_agent.run)
    graph.add_node("revision_router", revision_router_node)
    graph.add_node("assembler",       assembler_node)

    graph.add_edge(START,            "planner")
    graph.add_edge("planner",        "architecture")
    graph.add_edge("architecture",   "api_writer")
    graph.add_edge("api_writer",     "db_writer")
    graph.add_edge("db_writer",      "auth_writer")
    graph.add_edge("auth_writer",    "deploy_writer")
    graph.add_edge("deploy_writer",  "critic")

    graph.add_conditional_edges(
        "critic",
        should_revise,
        {
            "revise": "revision_router",
            "done":   "assembler",
        }
    )

    graph.add_edge("revision_router", "architecture")
    graph.add_edge("assembler",       END)

    logger.info(
        "Pipeline built — 9 nodes, conditional critic edge, "
        "revision loop capped at %d rounds",
        MAX_REVISIONS,
    )
    return graph.compile()
