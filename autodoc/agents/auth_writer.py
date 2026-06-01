from autodoc.agents.base import BaseAgent
from autodoc.logger import get_logger
from autodoc.models.doc_state import DocState
from autodoc.models.manifest import CodebaseManifest
from autodoc.utils.prompt_renderer import render_prompt

logger = get_logger(__name__)

_AUTH_MODULE_KEYWORDS = {
    "auth", "security", "token", "jwt", "permission",
    "middleware", "session", "login", "oauth", "credential",
}

_AUTH_CLASS_KEYWORDS = {
    "auth", "token", "permission", "user", "session",
    "credential", "login", "jwt", "middleware", "bearer",
}

_AUTH_LIBRARIES = {
    "python_jose":        "python-jose (JWT)",
    "jwt":                "PyJWT",
    "passlib":            "passlib (password hashing)",
    "bcrypt":             "bcrypt",
    "authlib":            "Authlib (OAuth)",
    "fastapi_users":      "FastAPI Users",
    "django_allauth":     "django-allauth",
    "flask_login":        "Flask-Login",
    "flask_jwt_extended": "Flask-JWT-Extended",
    "casbin":             "Casbin (authorization)",
    "pyjwt":              "PyJWT",
}


class AuthWriterAgent(BaseAgent):
    """
    Writes the authentication and security section.

    Detects auth patterns by scanning module names, class names,
    and dependency stack for known auth libraries.
    Revision-aware — passes critique to template on second pass.
    """

    _state_key = "auth_doc"
    _system = (
        "You are a security-focused technical writer. "
        "Your authentication sections are accurate and honest about uncertainty. "
        "You document what is actually present in the code — "
        "you never assume an auth mechanism not evidenced by the data. "
        "Your security measures table is specific and actionable."
    )

    def run(self, state: DocState) -> DocState:
        """Store critique from state before delegating to base run()."""
        critique = state.get("critique", {})
        self._critique = critique.get("auth", "")
        return super().run(state)

    def _build_prompt(self, manifest: CodebaseManifest) -> str:
        auth_modules   = self._extract_auth_modules(manifest)
        auth_classes   = self._extract_auth_classes(manifest)
        auth_libraries = self._detect_auth_libraries(manifest)

        logger.debug(
            "AuthWriterAgent context — auth modules: %d | "
            "auth classes: %d | auth libraries: %s",
            len(auth_modules), len(auth_classes), auth_libraries,
        )

        context = {
            "project_name":   manifest.project_name,
            "frameworks":     manifest.stack.frameworks,
            "other_tools":    manifest.stack.other_tools,
            "auth_modules":   auth_modules,
            "auth_classes":   auth_classes,
            "auth_libraries": auth_libraries,
            "critique":       getattr(self, "_critique", ""),
            "is_revision":    bool(getattr(self, "_critique", "")),
        }

        return render_prompt("auth.j2", context)

    def _extract_auth_modules(self, manifest: CodebaseManifest) -> list[dict]:
        """Find files whose module name contains auth-related keywords."""
        auth_modules = []
        for file in manifest.files:
            name_lower = file.module_name.lower()
            if any(kw in name_lower for kw in _AUTH_MODULE_KEYWORDS):
                auth_modules.append({
                    "module_name": file.module_name,
                    "docstring":   file.docstring,
                    "classes": [
                        {
                            "name":      cls.name,
                            "bases":     cls.bases,
                            "docstring": cls.docstring,
                            "methods":   [
                                m.name for m in cls.methods
                                if not m.name.startswith("__")
                            ],
                        }
                        for cls in file.classes
                    ],
                    "functions": [
                        {
                            "name":              fn.name,
                            "args":              [
                                f"{a.name}: {a.annotation}"
                                if a.annotation else a.name
                                for a in fn.args
                            ],
                            "return_annotation": fn.return_annotation,
                            "docstring":         fn.docstring,
                        }
                        for fn in file.functions
                        if not fn.name.startswith("_")
                    ],
                })
                logger.debug(
                    "AuthWriterAgent detected auth module: %s",
                    file.module_name,
                )
        return auth_modules

    def _extract_auth_classes(self, manifest: CodebaseManifest) -> list[dict]:
        """Find classes with auth-related names across all modules."""
        auth_classes = []
        for file in manifest.files:
            for cls in file.classes:
                name_lower = cls.name.lower()
                if any(kw in name_lower for kw in _AUTH_CLASS_KEYWORDS):
                    auth_classes.append({
                        "name":      cls.name,
                        "module":    file.module_name,
                        "docstring": cls.docstring,
                    })
                    logger.debug(
                        "AuthWriterAgent detected auth class: %s in %s",
                        cls.name, file.module_name,
                    )
        return auth_classes

    def _detect_auth_libraries(self, manifest: CodebaseManifest) -> list[str]:
        """Cross-reference detected stack against known auth libraries."""
        all_tools = (
            manifest.stack.frameworks
            + manifest.stack.other_tools
            + manifest.stack.databases
        )
        normalised = [
            t.lower().replace("-", "_").replace(" ", "_")
            for t in all_tools
        ]
        return [
            label for pkg, label in _AUTH_LIBRARIES.items()
            if any(pkg in tool for tool in normalised)
        ]
