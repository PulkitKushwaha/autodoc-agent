from autodoc.agents.base import BaseAgent
from autodoc.models.manifest import CodebaseManifest


class DeployWriterAgent(BaseAgent):
    """
    Writes the deployment and infrastructure section.
    Covers requirements, env vars, local setup, and production notes.
    Full implementation in Day 4.
    """

    _state_key = "deploy_doc"
    _system = (
        "You are a DevOps-aware technical writer. "
        "Your deployment sections are actionable — a developer should be able "
        "to follow them to get the project running from scratch."
    )

    def _build_prompt(self, manifest: CodebaseManifest) -> str:
        return f"""Write a complete deployment and infrastructure section for this project.

Project: {manifest.project_name}
Language: Python 3.11+
Frameworks: {', '.join(manifest.stack.frameworks) or 'none detected'}
Databases: {', '.join(manifest.stack.databases) or 'none detected'}
Task queues: {', '.join(manifest.stack.task_queues) or 'none'}
Other tools: {', '.join(manifest.stack.other_tools) or 'none'}
Total modules: {manifest.total_files}

Write the following in Markdown:
1. Requirements — Python version, system dependencies, external services needed
2. Environment variables — table of all variables the project likely needs
3. Local setup — step-by-step commands to get it running locally
4. Running tests — how to execute the test suite
5. Production notes — any deployment considerations (Docker, cloud, workers)

Be practical and specific. Use code blocks for all commands."""
