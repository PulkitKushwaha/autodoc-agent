import configparser
import tomllib
from pathlib import Path

from autodoc.logger import get_logger
from autodoc.models.manifest import StackInfo

logger = get_logger(__name__)

FRAMEWORK_MAP: dict[str, str] = {
    "fastapi": "FastAPI",
    "flask": "Flask",
    "django": "Django",
    "starlette": "Starlette",
    "tornado": "Tornado",
    "aiohttp": "aiohttp",
    "litestar": "Litestar",
}

DATABASE_MAP: dict[str, str] = {
    "sqlalchemy": "SQLAlchemy",
    "alembic": "Alembic",
    "pymongo": "MongoDB",
    "motor": "MongoDB (async)",
    "redis": "Redis",
    "aioredis": "Redis (async)",
    "psycopg2": "PostgreSQL",
    "psycopg": "PostgreSQL",
    "asyncpg": "PostgreSQL (async)",
    "pymysql": "MySQL",
    "tortoise": "Tortoise ORM",
    "beanie": "Beanie (MongoDB)",
    "databases": "databases",
}

TEST_MAP: dict[str, str] = {
    "pytest": "pytest",
    "unittest": "unittest",
    "hypothesis": "Hypothesis",
    "factory_boy": "factory_boy",
    "faker": "Faker",
}

TASK_QUEUE_MAP: dict[str, str] = {
    "celery": "Celery",
    "dramatiq": "Dramatiq",
    "rq": "RQ",
    "arq": "arq",
    "apscheduler": "APScheduler",
}

OTHER_MAP: dict[str, str] = {
    "pydantic": "Pydantic",
    "langchain": "LangChain",
    "langgraph": "LangGraph",
    "anthropic": "Anthropic",
    "openai": "OpenAI",
    "typer": "Typer",
    "click": "Click",
    "rich": "Rich",
    "httpx": "HTTPX",
    "requests": "Requests",
}


def detect_stack(root: Path) -> StackInfo:
    """
    Infer the tech stack by reading dependency declaration files.
    Checks pyproject.toml, requirements.txt, and setup.cfg in order.
    """
    logger.info("Detecting tech stack from: %s", root)
    deps = _collect_dependencies(root)
    logger.debug("Normalized dependencies collected: %d packages", len(deps))
    stack = _map_to_stack(deps)
    logger.info(
        "Stack detected — frameworks: %s | databases: %s | "
        "test: %s | queues: %s | other: %s",
        stack.frameworks,
        stack.databases,
        stack.test_frameworks,
        stack.task_queues,
        stack.other_tools,
    )
    return stack


def _collect_dependencies(root: Path) -> set[str]:
    deps: set[str] = set()

    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        logger.debug("Reading pyproject.toml")
        deps.update(_parse_pyproject(pyproject))

    requirements = root / "requirements.txt"
    if requirements.exists():
        logger.debug("Reading requirements.txt")
        deps.update(_parse_requirements(requirements))

    setup_cfg = root / "setup.cfg"
    if setup_cfg.exists():
        logger.debug("Reading setup.cfg")
        deps.update(_parse_setup_cfg(setup_cfg))

    if not deps:
        logger.warning(
            "No dependency files found in %s — stack detection may be incomplete", root
        )

    return deps


def _parse_pyproject(path: Path) -> list[str]:
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
        raw_deps = data.get("project", {}).get("dependencies", []) + list(
            data.get("tool", {}).get("poetry", {}).get("dependencies", {}).keys()
        )
        normalized = [_normalize(d) for d in raw_deps]
        logger.debug("pyproject.toml — found %d deps", len(normalized))
        return normalized
    except Exception as e:
        logger.warning("Failed to parse pyproject.toml: %s", e)
        return []


def _parse_requirements(path: Path) -> list[str]:
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        deps = []
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue
            deps.append(_normalize(line))
        logger.debug("requirements.txt — found %d deps", len(deps))
        return deps
    except Exception as e:
        logger.warning("Failed to parse requirements.txt: %s", e)
        return []


def _parse_setup_cfg(path: Path) -> list[str]:
    try:
        config = configparser.ConfigParser()
        config.read(path, encoding="utf-8")
        raw = config.get("options", "install_requires", fallback="")
        deps = [_normalize(d.strip()) for d in raw.splitlines() if d.strip()]
        logger.debug("setup.cfg — found %d deps", len(deps))
        return deps
    except Exception as e:
        logger.warning("Failed to parse setup.cfg: %s", e)
        return []


def _normalize(dep: str) -> str:
    name = dep.split(">=")[0].split("==")[0].split("<=")[0].split("[")[0].strip()
    return name.lower().replace("-", "_").replace(".", "_")


def _map_to_stack(deps: set[str]) -> StackInfo:
    def match(mapping: dict[str, str]) -> list[str]:
        return [
            label for pkg, label in mapping.items()
            if pkg.replace("-", "_") in deps
        ]

    return StackInfo(
        frameworks=match(FRAMEWORK_MAP),
        databases=match(DATABASE_MAP),
        test_frameworks=match(TEST_MAP),
        task_queues=match(TASK_QUEUE_MAP),
        other_tools=match(OTHER_MAP),
    )
