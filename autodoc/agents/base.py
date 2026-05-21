from abc import ABC, abstractmethod

from autodoc.llm import get_llm_client
from autodoc.llm.base import BaseLLMClient
from autodoc.logger import get_logger
from autodoc.models.doc_state import DocState
from autodoc.models.manifest import CodebaseManifest

logger = get_logger(__name__)


class BaseAgent(ABC):
    """
    Shared base for all specialist writer agents.

    Each subclass defines:
        _state_key   — which DocState field it writes to
        _system      — the system prompt that sets the agent's role
        _build_prompt(manifest) — constructs the user prompt from the manifest

    The base class handles: LLM client access, logging, error handling,
    and writing the result back into DocState.
    """

    _state_key: str = ""
    _system: str = "You are a technical documentation writer."

    def __init__(self) -> None:
        self._llm: BaseLLMClient = get_llm_client()
        logger.debug(
            "%s initialized — state_key: %s, llm: %s",
            self.__class__.__name__,
            self._state_key,
            self._llm.__class__.__name__,
        )

    def run(self, state: DocState) -> DocState:
        """
        Entry point called by LangGraph. Reads the manifest from state,
        builds the prompt, calls the LLM, and writes the result back.
        """
        logger.info(
            "%s starting — project: %s",
            self.__class__.__name__,
            state.get("project_name", "unknown"),
        )

        if state.get("error"):
            logger.warning(
                "%s skipping — upstream error: %s",
                self.__class__.__name__,
                state["error"],
            )
            return state

        try:
            manifest = self._load_manifest(state)
            prompt = self._build_prompt(manifest)

            logger.debug(
                "%s sending prompt — %d chars",
                self.__class__.__name__,
                len(prompt),
            )

            response = self._llm.complete(prompt=prompt, system=self._system)

            logger.info(
                "%s complete — wrote %d chars to state['%s']",
                self.__class__.__name__,
                len(response),
                self._state_key,
            )

            return {**state, self._state_key: response}

        except Exception as e:
            logger.exception(
                "%s failed: %s", self.__class__.__name__, e
            )
            return {**state, "error": f"{self.__class__.__name__} failed: {e}"}

    def _load_manifest(self, state: DocState) -> CodebaseManifest:
        from pathlib import Path
        manifest_path = Path(state["manifest_path"])
        logger.debug("Loading manifest from %s", manifest_path)
        return CodebaseManifest.load(manifest_path)

    @abstractmethod
    def _build_prompt(self, manifest: CodebaseManifest) -> str:
        """Build the LLM prompt from the codebase manifest."""
        ...
