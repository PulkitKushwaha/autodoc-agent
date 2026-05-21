# Data models

## Overview
AutoDoc uses two categories of data models. Pydantic models govern all
data produced by the ingestion engine and consumed by agents — they are
validated, serializable, and form the contract between pipeline stages.
A TypedDict governs the LangGraph pipeline state — it flows through every
node and accumulates documentation output as the graph executes.

## Models

### `ArgumentInfo`
Represents a single function or method argument.

| Field | Type | Description |
|-------|------|-------------|
| name | str | Argument name as it appears in the signature |
| annotation | str \| None | Type annotation string, e.g. `"list[str]"` |

---

### `FunctionInfo`
Represents a single function or method extracted from source.

| Field | Type | Description |
|-------|------|-------------|
| name | str | Function name |
| args | list[ArgumentInfo] | All arguments excluding `self` and `cls` |
| return_annotation | str \| None | Return type annotation string |
| docstring | str \| None | Docstring if present |
| line_number | int | Line where the function is defined |
| is_method | bool | True if defined inside a class |

---

### `ClassInfo`
Represents a single class extracted from source.

| Field | Type | Description |
|-------|------|-------------|
| name | str | Class name |
| bases | list[str] | Base class names, e.g. `["BaseModel", "ABC"]` |
| docstring | str \| None | Class-level docstring |
| methods | list[FunctionInfo] | All methods defined in the class |
| line_number | int | Line where the class is defined |

---

### `ImportInfo`
Represents a single import statement.

| Field | Type | Description |
|-------|------|-------------|
| module | str | Module being imported, e.g. `"pathlib"` |
| names | list[str] | Names imported, e.g. `["Path", "PurePath"]` |
| is_from_import | bool | True for `from x import y`, False for `import x` |

---

### `FileInfo`
Represents a single parsed Python file. This is the primary output unit
of `parser.py`.

| Field | Type | Description |
|-------|------|-------------|
| path | str | Relative path from project root |
| module_name | str | Dotted module name, e.g. `"autodoc.ingestion.parser"` |
| docstring | str \| None | Module-level docstring |
| classes | list[ClassInfo] | All classes defined in the file |
| functions | list[FunctionInfo] | All top-level functions |
| imports | list[ImportInfo] | All import statements |
| line_count | int | Total lines in the file |

---

### `StackInfo`
Represents the detected technology stack.

| Field | Type | Description |
|-------|------|-------------|
| language | str | Always `"python"` in this version |
| frameworks | list[str] | Web frameworks, e.g. `["FastAPI"]` |
| databases | list[str] | Database tools, e.g. `["SQLAlchemy", "Redis"]` |
| test_frameworks | list[str] | Test tools, e.g. `["pytest"]` |
| task_queues | list[str] | Queue tools, e.g. `["Celery"]` |
| other_tools | list[str] | Other notable packages |

---

### `DependencyGraph`
Represents the internal import dependency graph of the project.

| Field | Type | Description |
|-------|------|-------------|
| edges | dict[str, list[str]] | Maps each module to the list of internal modules it imports |

**Methods**

`get_entry_points() -> list[str]`
Returns modules that no other module imports — typically CLI scripts and
application startup files.

`get_core_modules(threshold: int = 3) -> list[str]`
Returns modules imported by `threshold` or more other modules — the most
critical shared utilities in the codebase.

---

### `CodebaseManifest`
The root model. Aggregates all ingestion output into a single validated
object that is serialized to `output/manifest.json`.

| Field | Type | Description |
|-------|------|-------------|
| project_name | str | Name of the project root directory |
| root_path | str | Absolute path to the project root |
| source | str | Original input — URL or local path |
| total_files | int | Number of Python files parsed |
| total_lines | int | Total lines across all parsed files |
| files | list[FileInfo] | Per-file parse results |
| stack | StackInfo | Detected technology stack |
| dependency_graph | DependencyGraph | Internal import graph |

---

### `DocState` (TypedDict)
The single state object that flows through the LangGraph pipeline. Every
node reads from it and writes back to it.

| Key | Type | Written by |
|-----|------|-----------|
| project_name | str | planner |
| manifest_path | str | main.py (initial seed) |
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

## Database notes
AutoDoc itself does not use a database. The data model layer is entirely
in-memory during a run, with `manifest.json` as the only persistence
artifact. The `DBWriterAgent` is designed to document databases in the
target project being analyzed, not in AutoDoc itself.
