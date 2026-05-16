import shutil
import tempfile
from pathlib import Path

import git

from autodoc.logger import get_logger

logger = get_logger(__name__)


def fetch_codebase(input_path: str) -> tuple[Path, bool]:
    """
    Resolve input to a local directory path.

    Accepts either a GitHub URL or a local filesystem path.
    Returns (resolved_path, is_temp): is_temp tells the caller
    whether to call cleanup() when finished.
    """
    logger.info("Fetching codebase from: %s", input_path)

    if input_path.startswith("https://github.com") or input_path.startswith("git@"):
        return _clone_github_repo(input_path)
    else:
        return _resolve_local_path(input_path)


def _clone_github_repo(url: str) -> tuple[Path, bool]:
    temp_dir = Path(tempfile.mkdtemp(prefix="autodoc_"))
    logger.info("Cloning repository: %s", url)
    logger.debug("Temp directory: %s", temp_dir)

    try:
        repo = git.Repo.clone_from(url, temp_dir, depth=1)
        logger.info(
            "Clone successful — branch: %s | commit: %s",
            repo.active_branch.name,
            repo.head.commit.hexsha[:7],
        )
        return temp_dir, True

    except git.GitCommandError as e:
        logger.error("Clone failed for %s: %s", url, e)
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise ValueError(f"Failed to clone repository: {url}") from e


def _resolve_local_path(path_str: str) -> tuple[Path, bool]:
    path = Path(path_str).resolve()
    logger.debug("Resolving local path: %s", path)

    if not path.exists():
        logger.error("Path does not exist: %s", path)
        raise ValueError(f"Path does not exist: {path}")

    if not path.is_dir():
        logger.error("Path is not a directory: %s", path)
        raise ValueError(f"Path is not a directory: {path}")

    logger.info("Using local path: %s", path)
    return path, False


def cleanup(path: Path) -> None:
    """Remove a temporary cloned directory."""
    logger.debug("Cleaning up temp directory: %s", path)
    shutil.rmtree(path, ignore_errors=True)
    logger.info("Temp directory removed: %s", path)
