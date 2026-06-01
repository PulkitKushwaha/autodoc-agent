from pathlib import Path

from autodoc.agents.base import BaseAgent
from autodoc.logger import get_logger
from autodoc.models.doc_state import DocState
from autodoc.models.manifest import CodebaseManifest
from autodoc.utils.prompt_renderer import render_prompt

logger = get_logger(__name__)

_CICD_FILES = [
    ".github/workflows",
    ".gitlab-ci.yml",
    "Jenkinsfile",
    ".circleci/config.yml",
    "azure-pipelines.yml",
    "bitbucket-pipelines.yml",
    ".travis.yml",
    "Makefile",
]

_INFRA_FILES = [
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "fly.toml",
    "railway.json",
    "render.yaml",
    "heroku.yml",
    "k8s",
    "kubernetes",
]


class DeployWriterAgent(BaseAgent):
    """
    Writes the deployment and infrastructure section.

    Detects CI/CD config files, package manager, infrastructure files,
    and builds a stack-aware deployment guide using deploy.j2 template.
    Revision-aware — passes critique to template on second pass.
    """

    _state_key = "deploy_doc"
    _system = (
        "You are a DevOps-aware technical writer. "
        "Your deployment sections are immediately actionable — "
        "a developer should be able to follow them from a fresh clone. "
        "All commands are in fenced bash code blocks. "
        "You only document what is evidenced by the project structure."
    )

    def run(self, state: DocState) -> DocState:
        """Store critique from state before delegating to base run()."""
        critique = state.get("critique", {})
        self._critique = critique.get("deploy", "")
        return super().run(state)

    def _build_prompt(self, manifest: CodebaseManifest) -> str:
        root = Path(manifest.root_path)
        cicd_files = self._detect_cicd_files(root)
        package_manager, config_file, has_lockfile = self._detect_package_manager(root)
        entry_points = manifest.dependency_graph.get_entry_points()

        logger.debug(
            "DeployWriterAgent context — cicd: %s | pm: %s | entries: %s",
            cicd_files, package_manager, entry_points,
        )

        context = {
            "project_name":    manifest.project_name,
            "total_files":     manifest.total_files,
            "total_lines":     manifest.total_lines,
            "frameworks":      manifest.stack.frameworks,
            "databases":       manifest.stack.databases,
            "task_queues":     manifest.stack.task_queues,
            "test_frameworks": manifest.stack.test_frameworks,
            "other_tools":     manifest.stack.other_tools,
            "cicd_files":      cicd_files,
            "package_manager": package_manager,
            "config_file":     config_file,
            "has_lockfile":    has_lockfile,
            "entry_points":    entry_points,
            "critique":        getattr(self, "_critique", ""),
            "is_revision":     bool(getattr(self, "_critique", "")),
        }

        return render_prompt("deploy.j2", context)

    def _detect_cicd_files(self, root: Path) -> list[str]:
        """Check which CI/CD and infrastructure files exist in the project."""
        found = []
        for target in _CICD_FILES + _INFRA_FILES:
            if (root / target).exists():
                found.append(target)
                logger.debug(
                    "DeployWriterAgent detected infra file: %s", target
                )
        return found

    def _detect_package_manager(
        self, root: Path
    ) -> tuple[str, str, bool]:
        """
        Detect which Python package manager the project uses.
        Returns (manager_name, config_file, has_lockfile).
        """
        if (root / "pyproject.toml").exists():
            has_uv_lock     = (root / "uv.lock").exists()
            has_poetry_lock = (root / "poetry.lock").exists()
            has_lockfile    = has_uv_lock or has_poetry_lock
            if has_uv_lock:
                return "uv", "pyproject.toml", True
            if has_poetry_lock:
                return "poetry", "pyproject.toml", True
            return "uv", "pyproject.toml", False
        if (root / "requirements.txt").exists():
            return "pip", "requirements.txt", False
        if (root / "Pipfile").exists():
            has_lock = (root / "Pipfile.lock").exists()
            return "pipenv", "Pipfile", has_lock
        return "pip", "requirements.txt", False
