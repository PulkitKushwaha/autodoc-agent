# Data models

## Overview
AutoDoc uses two categories of data models. Pydantic `BaseModel` subclasses
govern all data produced by the ingestion engine and consumed by agents —
validated on construction, serializable to JSON, and the typed contract
between every pipeline stage. A `TypedDict` governs the LangGraph pipeline
state — plain dict at runtime with full IDE and type checker support.

## Models

### `ArgumentInfo`
A single function or method argument extracted from source.

| Field | Type | Description |
|-------|------|-------------|
| name | str | Argument name as written in the signature |
| annotation | str \| None | Type annotation string e.g. `"list[str]"`, `"Path \| None"` |

---

### `FunctionInfo`
A single function or method extracted via AST.

| Field | Type | Description |
|-------|------|-------------|
| name | str | Function or method name |
| args | list[ArgumentInfo] | Arguments, excluding `self` and `cls` |
| return_annotation | str \| None | Return type annotation string |
| docstring | str \| None | Docstring content if present |
| line_number | int | Source line where the function is defined |
| is_method | bool | `True` if defined inside a class body |

---

### `ClassInfo`
A single class definition extracted via AST.

| Field | Type | Description |
|-------|------|-------------|
| name | str | Class name |
| bases | list[str] | Base class name strings e.g. `["BaseModel", "ABC"]` |
| docstring | str \| None | Class-level docstring |
| methods | list[FunctionInfo] | All methods including private ones |
| line_number | int | Source line where the class is defined |

---

### `ImportInfo`
A single import statement extracted via AST.

| Field | Type | Description |
|-------|------|-------------|
| module | str | Module being imported e.g. `"pathlib"`, `"autodoc.logger"` |
| names | list[str] | Names imported e.g. `["Path", "PurePath"]` |
| is_from_import | bool | `True` for `from x import y`, `False` for `import x` |

---

### `FileInfo`
A single parsed Python file — the primary output unit of `parser.py`.

| Field | Type | Description |
|-------|------|-------------|
| path | str | Path relative to project root e.g. `"autodoc/ingestion/parser.py"` |
| module_name | str | Dotted module name e.g. `"autodoc.ingestion.parser"` |
| docstring | str \| None | Module-level docstring |
| classes | list[ClassInfo] | All class definitions in the file |
| functions | list[FunctionInfo] | All top-level function definitions |
| imports | list[ImportInfo] | All import statements |
| line_count | int | Total lines in the file |

---

### `StackInfo`
The detected technology stack of the target project.

| Field | Type | Description |
|-------|------|-------------|
| language | str | Always `"python"` in this version |
| frameworks | list[str] | Web frameworks e.g. `["FastAPI", "Flask"]` |
| databases | list[str] | Database tools e.g. `["SQLAlchemy", "Redis"]` |
| test_frameworks | list[str] | Test tools e.g. `["pytest", "Hypothesis"]` |
| task_queues | list[str] | Queue tools e.g. `["Celery", "arq"]` |
| other_tools | list[str] | Other notable packages e.g. `["Pydantic", "Rich"]` |

---

### `DependencyGraph`
The internal import dependency graph of the target project.

| Field | Type | Description |
|-------|------|-------------|
| edges | dict[str, list[str]] | Maps each module name to the list of internal modules it imports |

Only project-internal edges are tracked. Imports of stdlib modules
(e.g. `os`, `pathlib`) and third-party packages (e.g. `pydantic`,
`fastapi`) are excluded — they do not appear as nodes or edges.

**Methods**

`get_entry_points() -> list[str]`
Set subtraction: all modules minus all modules that appear as an import
target. The remainder are modules nothing imports — entry points.

`get_core_modules(threshold: int = 3) -> list[str]`
Counts incoming edges per module. Returns those with count ≥ threshold.
Default threshold 3 identifies the most-shared utilities.

---

### `CodebaseManifest`
The root output model of the ingestion engine. Single source of truth
for every agent's prompt context.

| Field | Type | Description |
|-------|------|-------------|
| project_name | str | Name of the project root directory |
| root_path | str | Absolute path to the project root |
| source | str | Original input — URL or local path |
| total_files | int | Number of Python files successfully parsed |
| total_lines | int | Sum of line counts across all parsed files |
| files | list[FileInfo] | Per-file parse results |
| stack | StackInfo | Detected technology stack |
| dependency_graph | DependencyGraph | Internal import graph |

**Methods**

`save(path: Path) -> None`
Writes `self.model_dump_json(indent=2)` to disk. Creates a
human-readable JSON file.

`load(path: Path) -> CodebaseManifest`
Calls `model_validate_json(path.read_text())` — reconstructs the
full nested model from a saved JSON file.

`summary() -> str`
Returns a five-line human-readable summary. Used in logging and
terminal output.

---

### `DocState` (TypedDict)
The single state object that flows through the entire LangGraph pipeline.
Every node receives it, reads what it needs, writes to its designated
key, and returns the updated dict. LangGraph merges returned keys back
into shared state automatically.

| Key | Type | Written by | Description |
|-----|------|-----------|-------------|
| project_name | str | planner | Name of the project being documented |
| manifest_path | str | main.py | Path to manifest.json on disk |
| manifest_summary | str | planner | Output of `manifest.summary()` |
| sections_to_write | list[str] | planner | Which sections were determined necessary |
| architecture_doc | str | ArchitectureAgent | Generated architecture section |
| api_doc | str | APIWriterAgent | Generated API reference section |
| db_doc | str | DBWriterAgent | Generated data models section |
| auth_doc | str | AuthWriterAgent | Generated authentication section |
| deploy_doc | str | DeployWriterAgent | Generated deployment section |
| final_docs | dict[str, str] | assembler | All sections keyed by section name |
| is_complete | bool | assembler | True when all expected sections written |
| error | str \| None | any node | Set on failure, checked by every downstream node |

## Database notes
AutoDoc itself has no database. All data is in-memory during a run.
The only persistence artifact is `output/manifest.json` written between
Phase 1 (ingestion) and Phase 2 (agents). The `DBWriterAgent` documents
databases in the **target** project being analyzed — not in AutoDoc itself.
