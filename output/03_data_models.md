# Data models

## Overview
AutoDoc uses Pydantic `BaseModel` subclasses for all ingestion output —
validated on construction, serializable to JSON, and the typed contract
between every pipeline stage. A `TypedDict` governs the LangGraph pipeline
state. AutoDoc itself has no database — all data is in-memory per run
with `manifest.json` as the only persistence artifact.

## Models

### `ArgumentInfo`

| Field | Type | Description |
|-------|------|-------------|
| name | str | Argument name as written in the signature |
| annotation | str \| None | Type annotation e.g. `"list[str]"`, `"Path \| None"` |

---

### `FunctionInfo`

| Field | Type | Description |
|-------|------|-------------|
| name | str | Function or method name |
| args | list[ArgumentInfo] | Arguments, excluding `self` and `cls` |
| return_annotation | str \| None | Return type annotation string |
| docstring | str \| None | Docstring content if present |
| line_number | int | Source line where defined |
| is_method | bool | `True` if defined inside a class |

---

### `ClassInfo`

| Field | Type | Description |
|-------|------|-------------|
| name | str | Class name |
| bases | list[str] | Base class names e.g. `["BaseModel", "ABC"]` |
| docstring | str \| None | Class-level docstring |
| methods | list[FunctionInfo] | All methods including private ones |
| line_number | int | Source line where defined |

---

### `ImportInfo`

| Field | Type | Description |
|-------|------|-------------|
| module | str | Module being imported |
| names | list[str] | Names imported (for from-imports) |
| is_from_import | bool | `True` for `from x import y` |

---

### `FileInfo`

| Field | Type | Description |
|-------|------|-------------|
| path | str | Relative path from project root |
| module_name | str | Dotted module name e.g. `"autodoc.ingestion.parser"` |
| docstring | str \| None | Module-level docstring |
| classes | list[ClassInfo] | All class definitions |
| functions | list[FunctionInfo] | All top-level functions |
| imports | list[ImportInfo] | All import statements |
| line_count | int | Total lines in the file |

---

### `StackInfo`

| Field | Type | Description |
|-------|------|-------------|
| language | str | Always `"python"` in this version |
| frameworks | list[str] | Web frameworks e.g. `["FastAPI"]` |
| databases | list[str] | Database tools e.g. `["SQLAlchemy", "Alembic"]` |
| test_frameworks | list[str] | Test tools e.g. `["pytest"]` |
| task_queues | list[str] | Queue tools e.g. `["Celery"]` |
| other_tools | list[str] | Other notable packages |

---

### `DependencyGraph`

| Field | Type | Description |
|-------|------|-------------|
| edges | dict[str, list[str]] | Maps each module to its internal imports |

**Methods**

`get_entry_points() -> list[str]`
Modules that nothing else imports — CLI scripts and app runners.

`get_core_modules(threshold: int = 3) -> list[str]`
Modules imported by `threshold` or more others — most-shared utilities.

---

### `CodebaseManifest`

| Field | Type | Description |
|-------|------|-------------|
| project_name | str | Project root directory name |
| root_path | str | Absolute path to project root |
| source | str | Original input — URL or local path |
| total_files | int | Files successfully parsed |
| total_lines | int | Sum of line counts |
| files | list[FileInfo] | Per-file parse results |
| stack | StackInfo | Detected technology stack |
| dependency_graph | DependencyGraph | Internal import graph |

**Methods**

`save(path: Path) -> None` — writes `model_dump_json(indent=2)` to disk.
`load(path: Path) -> CodebaseManifest` — reconstructs from JSON.
`summary() -> str` — five-line human-readable summary.

---

### `DocState` (TypedDict)

| Key | Type | Written by |
|-----|------|-----------|
| project_name | str | planner |
| manifest_path | str | main.py |
| manifest_summary | str | planner |
| sections_to_write | list[str] | planner |
| architecture_doc | str | ArchitectureAgent |
| api_doc | str | APIWriterAgent |
| db_doc | str | DBWriterAgent |
| auth_doc | str | AuthWriterAgent |
| deploy_doc | str | DeployWriterAgent |
| final_docs | dict[str, str] | assembler |
| is_complete | bool | assembler |
| error | str \| None | any node on failure |

## Pydantic schemas
AutoDoc's own codebase is heavily modelled with Pydantic v2.
The full `CodebaseManifest` hierarchy (`ArgumentInfo` → `FunctionInfo`
→ `ClassInfo` → `FileInfo` → `CodebaseManifest`) represents every
structural element of a Python project that AutoDoc can parse and document.

## Database notes
AutoDoc has no database. The `DBWriterAgent` is designed to document
databases in the **target** project being analyzed — not in AutoDoc itself.
Detection heuristics: classes inheriting from `Base`, `BaseModel`, `Model`,
`Schema`, or `Entity`, and files named `model`, `schema`, or `entity`.
