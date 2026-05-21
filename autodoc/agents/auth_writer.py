from autodoc.agents.base import BaseAgent
from autodoc.models.manifest import CodebaseManifest


class AuthWriterAgent(BaseAgent):
    """
    Writes the authentication and security section.
    Detects auth patterns from module names and stack.
    Full implementation in Day 4.
    """

    _state_key = "auth_doc"
    _system = (
        "You are a security-focused technical writer. "
        "Your authentication sections are accurate, precise, and cover "
        "token flows, security measures, and implementation details."
    )

    def _build_prompt(self, manifest: CodebaseManifest) -> str:
        auth_modules = [
            f.module_name for f in manifest.files
            if any(kw in f.module_name.lower() for kw in
                   ("auth", "security", "token", "jwt", "permission", "middleware"))
        ]
        auth_classes = [
            f"{cls.name} in {file.module_name}"
            for file in manifest.files
            for cls in file.classes
            if any(kw in cls.name.lower() for kw in
                   ("auth", "token", "permission", "user", "session"))
        ]

        return f"""Write a complete authentication and security section for this project.

Project: {manifest.project_name}
Stack: {', '.join(manifest.stack.frameworks + manifest.stack.other_tools)}

Auth-related modules detected:
{chr(10).join(f'- {m}' for m in auth_modules) or '- none detected'}

Auth-related classes detected:
{chr(10).join(f'- {c}' for c in auth_classes) or '- none detected'}

Write the following in Markdown:
1. Authentication mechanism — what method is used (JWT, session, OAuth, etc.)
2. Token or session flow — step-by-step how auth works
3. Security measures — hashing, rate limiting, HTTPS, token expiry
4. Key classes and functions — what handles auth in this codebase

Base your response only on what is listed above."""
