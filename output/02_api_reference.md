# API reference

## Overview
AutoDoc exposes a public API surface across its ingestion, prompt rendering,
agent, and pipeline modules. The primary programmatic entry point is
`main.run()`. All public classes and functions are documented below.

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

The root output model of the ingestion engine. Aggregates all parsed
file data, stack detection, and dependency graph into a single validated
object. Serialized to `output/manifest.json` and read by every agent.

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `save` | `path: Path` | `None` | Serializes to indented JSON and writes to disk |
| `load` | `path: Path` | `CodebaseManifest` | Reconstructs typed model from saved JSON |
| `summary` | — | `str` | Human-readable summary for logging |

```python
# Save and reload a manifest
manifest.save(Path("output/manifest.json"))
loaded = CodebaseManifest.load(Path("output/manifest.json"))
print(loaded.summary())
```

---

### `autodoc.models.manifest.DependencyGraph`

```python
class DependencyGraph(BaseModel):
    edges: dict[str, list[str]]
```

Internal import dependency graph of the project. Nodes are module names,
edges represent import relationships between internal modules only.

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `get_entry_points` | — | `list[str]` | Modules nothing else imports — CLI scripts, runners |
| `get_core_modules` | `threshold: int = 3` | `list[str]` | Modules imported by threshold+ other modules |

```python
graph = manifest.dependency_graph
print("Entry points:", graph.get_entry_points())
print("Core modules:", graph.get_core_modules(threshold=2))
```

---

### `autodoc.agents.base.BaseAgent`

```python
class BaseAgent(ABC):
    _state_key: str
    _system: str
```

Abstract base class for all specialist writer agents. Subclasses define
`_state_key` (which `DocState` field to write to), `_system` (system
prompt), and `_build_prompt()` (how to construct the user prompt from
the manifest). The base class handles LLM access, error checking,
logging, and state updates.

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `run` | `state: DocState` | `DocState` | LangGraph node entry point — builds prompt, calls LLM, updates state |
| `_build_prompt` | `manifest: CodebaseManifest` | `str` | Abstract — subclasses implement this |

```python
# All agents follow the same interface
agent = ArchitectureAgent()
updated_state = agent.run(current_state)
print(updated_state["architecture_doc"])
```

---

### `autodoc.llm.base.BaseLLMClient`

```python
class BaseLLMClient(ABC):
    @abstractmethod
    def complete(self, prompt: str, system: str = "") -> str: ...
```

Abstract interface for LLM clients. Two implementations: `AnthropicClient`
(production) and `MockLLMClient` (development). Always obtain via
`get_llm_client()` — never instantiate directly.

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `complete` | `prompt: str`, `system: str = ""` | `str` | Send prompt, return text response |

---

### `autodoc.llm.client.AnthropicClient`

```python
class AnthropicClient(BaseLLMClient):
    MODEL = "claude-sonnet-4-20250514"
    MAX_TOKENS = 4096
```

Production LLM client. Calls the Anthropic Claude API. Handles
`RateLimitError` and `APIStatusError` with structured logging.
Activated by setting `AUTODOC_USE_MOCK=false` and providing
`ANTHROPIC_API_KEY` in `.env`.

---

### `autodoc.llm.mock.MockLLMClient`

```python
class MockLLMClient(BaseLLMClient):
```

Development LLM client. Routes prompts to hardcoded realistic responses
by keyword matching on the prompt text. Activated by default
(`AUTODOC_USE_MOCK=true`). No API key required. The full agent graph
runs — only the API call is replaced.

---

## Functions

### `main.run`

```python
def run(input_path: str) -> dict
```

Orchestrates the full two-phase pipeline. Phase 1 runs the ingestion
engine and saves `manifest.json`. Phase 2 invokes the LangGraph agent
pipeline. Phase 3 writes numbered `.md` files to `output/`.

| Parameter | Type | Description |
|-----------|------|-------------|
| `input_path` | `str` | GitHub URL or local filesystem path |

Returns the final `DocState` dict with all sections in `final_docs`.

---

### `autodoc.ingestion.fetcher.fetch_codebase`

```python
def fetch_codebase(input_path: str) -> tuple[Path, bool]
```

Resolves input to a local directory. GitHub URLs are cloned with
`depth=1`. Returns `(path, is_temp)` — caller must call `cleanup(path)`
when `is_temp` is `True`.

| Parameter | Type | Description |
|-----------|------|-------------|
| `input_path` | `str` | GitHub URL or local path string |

---

### `autodoc.ingestion.fetcher.cleanup`

```python
def cleanup(path: Path) -> None
```

Removes a temporary cloned repository directory. Always called in a
`finally` block to guarantee cleanup on success and failure.

---

### `autodoc.ingestion.parser.parse_codebase`

```python
def parse_codebase(root: Path) -> list[FileInfo]
```

Recursively walks all `.py` files under `root`. Skips virtual
environments, `__pycache__`, `.git`, and migration directories.
Returns one `FileInfo` per successfully parsed file.

---

### `autodoc.ingestion.parser.parse_file`

```python
def parse_file(path: Path, root: Path) -> FileInfo | None
```

Parses a single Python file via `ast.parse()`. Returns `None` on
`SyntaxError` — caller receives `None` and logs a warning, the run
continues with remaining files.

---

### `autodoc.ingestion.graph.build_dependency_graph`

```python
def build_dependency_graph(files: list[FileInfo]) -> DependencyGraph
```

Builds internal import graph. Excludes stdlib and third-party imports —
only tracks relationships between modules within the project.

---

### `autodoc.ingestion.detector.detect_stack`

```python
def detect_stack(root: Path) -> StackInfo
```

Reads `pyproject.toml`, `requirements.txt`, and `setup.cfg`. Normalises
package names (lowercase, hyphens to underscores) and maps to
framework/database/test/queue/other categories.

---

### `autodoc.llm.get_llm_client`

```python
def get_llm_client() -> BaseLLMClient
```

Factory function. The only place `AUTODOC_USE_MOCK` is read. Returns
`MockLLMClient` when mock mode is active, `AnthropicClient` otherwise.
Raises `ValueError` if real mode is requested but `ANTHROPIC_API_KEY`
is not set.

---

### `autodoc.utils.prompt_renderer.render_prompt`

```python
def render_prompt(template_name: str, context: dict) -> str
```

Loads and renders a Jinja2 template from `autodoc/prompts/`.
Uses `StrictUndefined` — missing variables raise `UndefinedError`
immediately. `trim_blocks` and `lstrip_blocks` keep output clean.

| Parameter | Type | Description |
|-----------|------|-------------|
| `template_name` | `str` | Filename in `autodoc/prompts/`, e.g. `"architecture.j2"` |
| `context` | `dict` | Variables the template expects |

---

### `autodoc.logger.setup_logging`

```python
def setup_logging(level: str = "INFO", log_file: Path | None = None) -> None
```

Configures logging for the entire package. Call once at the top of
`main.py` before any other imports. Silences `git`, `httpx`, and
`anthropic` loggers to `WARNING`.

---

### `autodoc.logger.get_logger`

```python
def get_logger(name: str) -> logging.Logger
```

Convenience wrapper. Every module calls `logger = get_logger(__name__)`.

---

### `autodoc.graph.pipeline.build_graph`

```python
def build_graph() -> StateGraph
```

Wires and compiles the full LangGraph pipeline. Returns a compiled
`StateGraph` ready to invoke with an initial `DocState`.

---

## Usage examples

**Run the full pipeline programmatically:**
```python
from main import run

state = run("./my_python_project")

if state["is_complete"]:
    for section, content in state["final_docs"].items():
        print(f"--- {section} ---")
        print(content[:200])
```

**Run against a GitHub repository:**
```python
from main import run

state = run("https://github.com/tiangolo/fastapi")
print(state["final_docs"]["architecture"])
```

**Use the ingestion engine standalone:**
```python
from pathlib import Path
from autodoc.ingestion.parser import parse_codebase
from autodoc.ingestion.graph import build_dependency_graph
from autodoc.ingestion.detector import detect_stack
from autodoc.models.manifest import CodebaseManifest

root = Path("./my_project")
files = parse_codebase(root)
graph = build_dependency_graph(files)
stack = detect_stack(root)

manifest = CodebaseManifest(
    project_name=root.name,
    root_path=str(root),
    source="local",
    total_files=len(files),
    total_lines=sum(f.line_count for f in files),
    files=files,
    stack=stack,
    dependency_graph=graph,
)
manifest.save(Path("output/manifest.json"))
print(manifest.summary())
```

**Render a prompt template directly:**
```python
from autodoc.utils.prompt_renderer import render_prompt

prompt = render_prompt("architecture.j2", {
    "project_name": "myapp",
    "total_files": 10,
    "total_lines": 500,
    "frameworks": ["FastAPI"],
    "databases": ["SQLAlchemy"],
    "test_frameworks": ["pytest"],
    "task_queues": [],
    "other_tools": ["Pydantic"],
    "entry_points": ["main"],
    "core_modules": ["app.utils"],
    "files": [],
    "edges": {},
})
print(prompt[:500])
```
