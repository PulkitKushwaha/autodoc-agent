from abc import ABC, abstractmethod


class BaseLLMClient(ABC):
    """
    Abstract base class for all LLM clients in AutoDoc.

    All LLM interaction goes through this interface.
    Swap implementations by changing AUTODOC_USE_MOCK in .env —
    no code changes required anywhere in the codebase.
    """

    @abstractmethod
    def complete(self, prompt: str, system: str = "") -> str:
        """
        Send a prompt and return the model's text response.

        Args:
            prompt: The user message / task description.
            system: Optional system prompt setting the agent's role.

        Returns:
            The model's response as a plain string.
        """
        ...
