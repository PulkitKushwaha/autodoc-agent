from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from autodoc.logger import get_logger

logger = get_logger(__name__)

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def _get_env() -> Environment:
    """
    Create a Jinja2 environment pointed at the prompts directory.

    StrictUndefined means any template variable that is not provided
    raises an error immediately rather than silently rendering as empty.
    This catches prompt bugs at development time, not in production.
    """
    return Environment(
        loader=FileSystemLoader(str(_PROMPTS_DIR)),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_prompt(template_name: str, context: dict) -> str:
    """
    Render a Jinja2 prompt template with the given context.

    Args:
        template_name: filename inside autodoc/prompts/, e.g. 'architecture.j2'
        context: dict of variables the template expects

    Returns:
        Fully rendered prompt string ready to send to the LLM.
    """
    logger.debug("Rendering prompt template: %s", template_name)
    env = _get_env()
    template = env.get_template(template_name)
    rendered = template.render(**context)
    logger.debug(
        "Prompt rendered — template: %s | length: %d chars",
        template_name,
        len(rendered),
    )
    return rendered
