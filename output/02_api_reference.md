# API reference

## Overview
AutoDoc exposes a public Python API across its ingestion, agent, prompt
rendering, and pipeline modules. The primary entry point is `main.run()`.
All public classes and functions are documented below by module.

---

## Classes

### `autodoc.models.manifest.CodebaseManifest`

```python
class CodebaseManifest(BaseModel):
    project_name: str
    root_path: str
    source: str
    total_files: int
    total_lines: int
    files: list[FileInfo]
    stack: StackInfo
    dependency_graph: DependencyGraph
```

Root output model of the ingestion engine. Single source of truth
for every agent's prompt context. Validated by Pydantic on construction.

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `save` | `path: Path` | `None` | Serializes to indented JSON, writes to disk |
| `load` | `path: Path` | `CodebaseManifest` | Reconstructs from saved JSON |
| `summary` | — | `str` | Human-readable 5-line summary for logging |

---

### `autodoc.agents.base.BaseAgent`

```python
class BaseAgent(ABC):
    _state_key: str    # DocState key this agent writes to
    _system: str       # system prompt setting the agent role
```

Abstract base for all writer agents. Subclasses implement `_build_prompt()`.
The base handles LLM access, upstream error checking, logging, state updates.

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `run` | `state: DocState` | `DocState` | LangGraph node entry point |
| `_build_prompt` | `manifest: CodebaseManifest` | `str` | Abstract — build the LLM prompt |

---

### `autodoc.agents.architecture.ArchitectureAgent`

```python
class ArchitectureAgent(BaseAgent):
    _state_key = "architecture_doc"
```

Extracts entry points, core modules, dependency edges, and per-file
summaries. Renders `architecture.j2` with full structural context.

---

### `autodoc.agents.api_writer.APIWriterAgent`

```python
class APIWriterAgent(BaseAgent):
    _state_key = "api_doc"
```

Extracts all public classes and functions with full signatures,
type annotations, and docstrings. Filters private items (leading `_`).
Renders `api.j2`.

---

### `autodoc.agents.db_writer.DBWriterAgent`

```python
class DBWriterAgent(BaseAgent):
    _state_key = "db_doc"
```

Detects SQLAlchemy `Base` subclasses, Pydantic `BaseModel` subclasses,
and classes in model/schema/entity files. Renders `db.j2`.

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `_extract_model_classes` | `manifest` | `list[dict]` | ORM and model-file classes |
| `_extract_pydantic_models` | `manifest` | `list[dict]` | BaseModel subclasses only |

---

### `autodoc.agents.auth_writer.AuthWriterAgent`

```python
class AuthWriterAgent(BaseAgent):
    _state_key = "auth_doc"
```

Scans for auth-keyword modules and classes. Cross-references detected
stack against known auth libraries (PyJWT, passlib, Authlib, etc.).
Renders `auth.j2`.

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `_extract_auth_modules` | `manifest` | `list[dict]` | Files with auth-keyword names |
| `_extract_auth_classes` | `manifest` | `list[dict]` | Classes with auth-keyword names |
| `_detect_auth_libraries` | `manifest` | `list[str]` | Known auth libs in stack |

---

### `autodoc.agents.deploy_writer.DeployWriterAgent`

```python
class DeployWriterAgent(BaseAgent):
    _state_key = "deploy_doc"
```

Detects CI/CD config files, package manager, lockfile presence, and
infrastructure files. Renders `deploy.j2` with full deployment context.

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `_detect_cicd_files` | `root: Path` | `list[str]` | CI/CD + infra files present |
| `_detect_package_manager` | `root: Path` | `tuple[str, str, bool]` | manager, config file, has lockfile |

---

### `autodoc.llm.client.AnthropicClient`

```python
class AnthropicClient(BaseLLMClient):
    MODEL = "claude-sonnet-4-20250514"
    MAX_TOKENS = 4096
```

Production LLM client. Handles `RateLimitError` and `APIStatusError`.
Activated by `AUTODOC_USE_MOCK=false` + `ANTHROPIC_API_KEY` set.

---

### `autodoc.llm.mock.MockLLMClient`

```python
class MockLLMClient(BaseLLMClient):
```

Development client. Routes by keyword, returns realistic responses.
No API key needed. Default mode (`AUTODOC_USE_MOCK=true`).

---

## Functions

### `main.run`

```python
def run(input_path: str) -> dict
```

Full two-phase pipeline. Phase 1: ingestion → manifest.json.
Phase 2: LangGraph agents → 5 .md files in output/.

| Parameter | Type | Description |
|-----------|------|-------------|
| `input_path` | `str` | GitHub URL or local path |

---

### `autodoc.ingestion.fetcher.fetch_codebase`

```python
def fetch_codebase(input_path: str) -> tuple[Path, bool]
```

Returns `(path, is_temp)`. Call `cleanup(path)` when `is_temp` is `True`.

---

### `autodoc.ingestion.parser.parse_codebase`

```python
def parse_codebase(root: Path) -> list[FileInfo]
```

Recursively walks `.py` files, skipping venvs and caches.

---

### `autodoc.ingestion.graph.build_dependency_graph`

```python
def build_dependency_graph(files: list[FileInfo]) -> DependencyGraph
```

Internal imports only — stdlib and third-party excluded.

---

### `autodoc.ingestion.detector.detect_stack`

```python
def detect_stack(root: Path) -> StackInfo
```

Reads `pyproject.toml`, `requirements.txt`, `setup.cfg`.

---

### `autodoc.llm.get_llm_client`

```python
def get_llm_client() -> BaseLLMClient
```

Factory. Reads `AUTODOC_USE_MOCK`. Only decision point in the codebase.

---

### `autodoc.utils.prompt_renderer.render_prompt`

```python
def render_prompt(template_name: str, context: dict) -> str
```

Renders a Jinja2 template from `autodoc/prompts/`.
`StrictUndefined` — missing variables raise immediately.

---

### `autodoc.graph.pipeline.build_graph`

```python
def build_graph() -> StateGraph
```

Wires and compiles the full LangGraph pipeline. Returns compiled graph.

---

## Usage examples

**Full pipeline:**
```python
from main import run

state = run("./my_python_project")
for section, content in state["final_docs"].items():
    print(f"\n=== {section} ===\n{content[:300]}")
```

**Standalone ingestion:**
```python
from pathlib import Path
from autodoc.ingestion.parser import parse_codebase
from autodoc.ingestion.detector import detect_stack
from autodoc.ingestion.graph import build_dependency_graph
from autodoc.models.manifest import CodebaseManifest

root = Path("./myproject")
files = parse_codebase(root)
manifest = CodebaseManifest(
    project_name=root.name,
    root_path=str(root),
    source="local",
    total_files=len(files),
    total_lines=sum(f.line_count for f in files),
    files=files,
    stack=detect_stack(root),
    dependency_graph=build_dependency_graph(files),
)
manifest.save(Path("output/manifest.json"))
```

**Render a prompt template directly:**
```python
from autodoc.utils.prompt_renderer import render_prompt

prompt = render_prompt("db.j2", {
    "project_name": "myapp",
    "total_files": 10,
    "databases": ["SQLAlchemy"],
    "model_classes": [],
    "pydantic_models": [],
})
```
