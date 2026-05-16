from autodoc.llm.base import BaseLLMClient
from autodoc.logger import get_logger

logger = get_logger(__name__)


class MockLLMClient(BaseLLMClient):
    """
    Mock LLM client for development without an API key.

    Routes prompts to realistic hardcoded responses by keyword matching.
    The full agent graph runs — only the API call is replaced.
    Activate with AUTODOC_USE_MOCK=true in .env (the default).
    """

    def complete(self, prompt: str, system: str = "") -> str:
        logger.debug(
            "MockLLMClient.complete called — prompt: %d chars, system: %d chars",
            len(prompt),
            len(system),
        )

        prompt_lower = prompt.lower()
        response = self._route(prompt_lower)

        logger.debug("Mock response selected — %d chars", len(response))
        return response

    def _route(self, prompt_lower: str) -> str:
        if "architecture" in prompt_lower or "system overview" in prompt_lower:
            return self._architecture_response()
        if "api" in prompt_lower and (
            "endpoint" in prompt_lower or "reference" in prompt_lower
        ):
            return self._api_response()
        if any(k in prompt_lower for k in ("database", "schema", "data model")):
            return self._database_response()
        if any(k in prompt_lower for k in ("auth", "security", "authentication")):
            return self._auth_response()
        if any(k in prompt_lower for k in ("deploy", "infrastructure", "ci/cd")):
            return self._deployment_response()
        if any(k in prompt_lower for k in ("test", "testing", "coverage")):
            return self._testing_response()
        if any(k in prompt_lower for k in ("critique", "review", "quality", "improve")):
            return self._critique_response()

        logger.debug("No keyword match — returning generic mock response")
        return self._generic_response()

    def _architecture_response(self) -> str:
        return """## System architecture

### Overview
This system follows a layered architecture with clear separation between
the API layer, business logic, and data access layer.

### Components

**API layer** — Handles incoming HTTP requests, validates input, and delegates
to the service layer. Built with FastAPI for automatic OpenAPI documentation.

**Service layer** — Contains all business logic. Services are stateless and
depend only on repository interfaces, making them fully testable in isolation.

**Repository layer** — Abstracts all database operations. SQLAlchemy models
are confined to this layer and never leak into business logic.

### Data flow
