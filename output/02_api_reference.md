# API reference

## Overview
AutoDoc exposes a Python API surface across its ingestion, agent, and LLM
modules. The primary entry point for programmatic use is `main.run()`.
All other public interfaces are documented below by module.

## Functions

### `main`

```python
def run(input_path: str) -> dict
```
Orchestrates the full two-phase pipeline — ingestion followed by the agent
graph. Accepts a GitHub URL or local path. Returns the final `DocState` dict
containing all generated documentation sections.

**Parameters**
- `input_path: str` — GitHub URL (`https://github.com/...`) or local path

**Returns**
- `dict` — the final `DocState` with `final_docs`, `is_complete`, and all
  section keys populated

---

### `autodoc.ingestion.fetcher`

```python
def fetch_codebase(input_path: str) -> tuple[Path, bool]
```
Resolves the input to a local directory. Clones GitHub URLs via gitpython.
Returns `(resolved_path, is_temp)` — `is_temp` tells the caller whether
to call `cleanup()` when finished.

```python
def cleanup(path: Path) -> None
```
Removes a temporary cloned directory. Only call this when `is_temp` is
`True` from `fetch_codebase`.

---

### `autodoc.ingestion.parser`

```python
def parse_codebase(root: Path) -> list[FileInfo]
```
Recursively walks all `.py` files under `root`, skipping virtual
environments and cache directories. Returns a list of `FileInfo` objects,
one per file.

```python
def parse_file(path: Path, root: Path) -> FileInfo | None
```
Parses a single Python file using the `ast` module. Returns `None` if the
file has a syntax error.

---

### `autodoc.ingestion.graph`

```python
def build_dependency_graph(files: list[FileInfo]) -> DependencyGraph
```
Builds an internal import dependency graph from parsed file data. Only
tracks imports between modules within the project — stdlib and third-party
imports are excluded.

---

### `autodoc.ingestion.detector`

```python
def detect_stack(root: Path) -> StackInfo
```
Infers the tech stack by reading `pyproject.toml`, `requirements.txt`,
and `setup.cfg`. Maps known package names to framework, database, test,
and task queue categories.

---

### `autodoc.llm`

```python
def get_llm_client() -> BaseLLMClient
```
Factory function. Returns `MockLLMClient` when `AUTODOC_USE_MOCK=true`,
otherwise returns `AnthropicClient`. This is the only place in the codebase
that reads the mock flag.

---

### `autodoc.logger`

```python
def setup_logging(level: str = "INFO", log_file: Path | None = None) -> None
```
Configures logging for the entire package. Call once at the top of
`main.py` before any other imports. Sets up `RichHandler` for the terminal
and an optional file handler.

```python
def get_logger(name: str) -> logging.Logger
```
Convenience wrapper. Every module calls `logger = get_logger(__name__)`.

---

## Classes

### `autodoc.models.manifest.CodebaseManifest`

The primary output of the ingestion engine and the input to every agent.

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

**Methods**

```python
def save(self, path: Path) -> None
```
Serializes to indented JSON and writes to disk.

```python
@classmethod
def load(cls, path: Path) -> CodebaseManifest
```
Reconstructs a fully typed manifest from a saved JSON file.

```python
def summary(self) -> str
```
Returns a human-readable summary string suitable for logging.

---

### `autodoc.agents.base.BaseAgent`

Abstract base class for all specialist writer agents.

```python
class BaseAgent(ABC):
    _state_key: str          # which DocState field this agent writes to
    _system: str             # system prompt setting the agent's role
```

**Methods**

```python
def run(self, state: DocState) -> DocState
```
Entry point called by LangGraph. Loads the manifest, builds the prompt,
calls the LLM, writes the result to `state[_state_key]`, and returns the
updated state. Handles upstream errors gracefully — skips execution if
`state["error"]` is set.

---

### `autodoc.llm.base.BaseLLMClient`

```python
class BaseLLMClient(ABC):
    @abstractmethod
    def complete(self, prompt: str, system: str = "") -> str: ...
```

Abstract interface for all LLM clients. Subclasses: `AnthropicClient`,
`MockLLMClient`.

---

## Usage examples

**Run against a local project:**
```python
from main import run
state = run("./my_python_project")
print(state["final_docs"]["architecture"])
```

**Run against a GitHub repository:**
```python
from main import run
state = run("https://github.com/username/repo")
```

**Use the ingestion engine standalone:**
```python
from pathlib import Path
from autodoc.ingestion.parser import parse_codebase
from autodoc.ingestion.detector import detect_stack
from autodoc.models.manifest import CodebaseManifest

root = Path("./my_project")
files = parse_codebase(root)
stack = detect_stack(root)
manifest = CodebaseManifest(
    project_name="my_project",
    root_path=str(root),
    source="local",
    total_files=len(files),
    total_lines=sum(f.line_count for f in files),
    files=files,
    stack=stack,
)
manifest.save(Path("./output/manifest.json"))
```
