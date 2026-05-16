import anthropic

from autodoc.llm.base import BaseLLMClient
from autodoc.logger import get_logger

logger = get_logger(__name__)


class AnthropicClient(BaseLLMClient):
    """
    Production LLM client using the Anthropic Claude API.

    Activate by setting AUTODOC_USE_MOCK=false and
    ANTHROPIC_API_KEY=<your-key> in .env.
    """

    MODEL = "claude-sonnet-4-20250514"
    MAX_TOKENS = 4096

    def __init__(self, api_key: str) -> None:
        self._client = anthropic.Anthropic(api_key=api_key)
        logger.info("AnthropicClient initialized — model: %s", self.MODEL)

    def complete(self, prompt: str, system: str = "") -> str:
        logger.debug(
            "Sending request to Claude — prompt: %d chars, system: %d chars",
            len(prompt),
            len(system),
        )

        kwargs: dict = {
            "model": self.MODEL,
            "max_tokens": self.MAX_TOKENS,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system

        try:
            response = self._client.messages.create(**kwargs)
            result = response.content[0].text
            logger.debug(
                "Response received — %d chars, stop_reason: %s",
                len(result),
                response.stop_reason,
            )
            return result

        except anthropic.RateLimitError as e:
            logger.error("Rate limit hit: %s", e)
            raise
        except anthropic.APIStatusError as e:
            logger.error("Anthropic API error %d: %s", e.status_code, e.message)
            raise
        except Exception as e:
            logger.exception("Unexpected error calling Anthropic API: %s", e)
            raise
