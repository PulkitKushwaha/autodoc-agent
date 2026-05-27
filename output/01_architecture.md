# System architecture

## Overview
AutoDoc is an agentic documentation generator that ingests Python codebases
and produces comprehensive, structured technical documentation using a
multi-agent LangGraph pipeline. It accepts a GitHub URL or local path,
parses every Python file using AST analysis, builds a dependency graph,
infers the tech stack, and coordinates five specialist LLM-powered writer
agents, each responsible for one documentation section, before assembling
the final output. The system is built on Claude (Anthropic) with a full
mock mode for development without an API key.

## Project structure

```
autodoc-agent/
├── main.py                    — CLI entry point, orchestrates ingestion + pipeline
├── pyproject.toml             — dependencies, ruff, pytest configuration
├── .env.example               — environment variable documentation
├── autodoc/
│   ├── config.py              — Pydantic BaseSettings, single settings instance
│   ├── logger.py              — RichHandler + file handler, per-module loggers
│   ├── ingestion/
│   │   ├── fetcher.py         — GitHub URL clone (gitpython) + local path resolution
│   │   ├── parser.py          — AST extraction: classes, functions, imports, docstrings
│   │   ├── graph.py           — internal import dependency graph builder
│   │   └── detector.py        — tech stack inference from pyproject/requirements
│   ├── models/
│   │   ├── manifest.py        — CodebaseManifest and all nested Pydantic models
│   │   └── doc_state.py       — DocState TypedDict for LangGraph pipeline state
│   ├── agents/
│   │   ├── base.py            — BaseAgent ABC: LLM access, error handling, logging
│   │   ├── planner.py         — seeds DocState, determines sections to write
│   │   ├── architecture.py    — system overview writer, Jinja2 prompt
│   │   ├── api_writer.py      — API reference writer, Jinja2 prompt
│   │   ├── db_writer.py       — data model writer (stub, Day 4)
│   │   ├── auth_writer.py     — auth section writer (stub, Day 4)
│   │   └── deploy_writer.py   — deployment guide writer (stub, Day 4)
│   ├── graph/
│   │   └── pipeline.py        — StateGraph wiring, assembler node
│   ├── prompts/
│   │   ├── architecture.j2    — Jinja2 template for architecture agent
│   │   └── api.j2             — Jinja2 template for API reference agent
│   ├── utils/
│   │   └── prompt_renderer.py — centralised Jinja2 renderer, StrictUndefined
│   └── llm/
│       ├── base.py            — BaseLLMClient ABC
│       ├── client.py          — AnthropicClient (real API, claude-sonnet-4)
│       └── mock.py            — MockLLMClient (keyword-routed responses)
└── tests/
    ├── test_ingestion.py      — 16 tests: parser, graph, detector, manifest
    ├── test_agents.py         — 12 tests: planner, base agent, assembler, e2e
    └── test_writers.py        — 17 tests: prompt renderer, architecture, API writer
```

## Core components

### Ingestion engine (`autodoc/ingestion/`)
The foundation of the entire system. `fetcher.py` resolves the input —
cloning via `gitpython` with `depth=1` for GitHub URLs, or resolving and
validating a local path. `parser.py` uses Python's stdlib `ast` module to
extract every class (`ClassInfo`), function (`FunctionInfo`), import
(`ImportInfo`), and docstring from every `.py` file, producing a list of
`FileInfo` objects. `graph.py` builds an internal import dependency graph
— only tracking project-internal imports, excluding stdlib and third-party.
`detector.py` reads `pyproject.toml`, `requirements.txt`, and `setup.cfg`,
normalising package names and mapping them to framework, database, test,
and queue categories. All output is assembled into a `CodebaseManifest` —
a fully validated Pydantic model saved to `output/manifest.json`.

### LLM abstraction layer (`autodoc/llm/`)
Implements the strategy pattern. `BaseLLMClient` is an ABC with one method:
`complete(prompt, system) -> str`. `AnthropicClient` calls the Claude API
using `claude-sonnet-4-20250514`. `MockLLMClient` routes by keyword and
returns realistic hardcoded responses. `get_llm_client()` in
`llm/__init__.py` reads `AUTODOC_USE_MOCK` and returns the right
implementation — the only place this decision is made. Every agent calls
`get_llm_client()` once in `__init__` and never knows which it holds.

### Prompt engineering layer (`autodoc/prompts/`, `autodoc/utils/`)
Introduced in Day 3. Jinja2 `.j2` template files define what context is
fed to each agent. `prompt_renderer.py` provides a single `render_prompt()`
function used by all agents. `StrictUndefined` ensures any missing template
variable raises immediately rather than rendering silently as empty.
`trim_blocks` and `lstrip_blocks` keep rendered prompts clean. Prompts
feed the LLM real structural data — actual module names, actual dependency
edges, actual function signatures — rather than generic descriptions.

### Agent pipeline (`autodoc/agents/`, `autodoc/graph/`)
A LangGraph `StateGraph` with `DocState` (TypedDict) as shared state.
`planner_node` runs first — loads the manifest, determines which sections
are worth writing based on what the codebase actually contains, and seeds
all state keys. Five specialist agents run sequentially, each inheriting
from `BaseAgent` which handles LLM access, error propagation, and logging.
`assembler_node` collects all populated sections into `final_docs` and
marks the pipeline complete. Conditional routing and parallel execution
via `Send()` API is added in Day 5.

### Configuration (`autodoc/config.py`, `autodoc/logger.py`)
`Settings` (Pydantic `BaseSettings`) reads all config from `.env` — one
instance, imported everywhere. `setup_logging()` configures `RichHandler`
for the terminal and an optional file handler for `output/autodoc.log`.
Every module calls `get_logger(__name__)` — log lines carry the exact
module and line number where they originated.

## Dependency structure

```
main                              ← entry point (nothing imports it)
  └── autodoc.ingestion.*         ← ingestion layer
  └── autodoc.graph.pipeline      ← agent orchestration
        └── autodoc.agents.*      ← specialist writers
              └── autodoc.llm     ← LLM abstraction
              └── autodoc.utils   ← prompt rendering
                    └── autodoc.prompts  ← Jinja2 templates
        └── autodoc.models.*      ← data contracts (imported by everything)
              ← autodoc.logger    ← logging utility (imported by everything)
```

`autodoc.logger` and `autodoc.models.manifest` are the two core modules —
imported by four or more other modules each. They are the shared
infrastructure the entire system depends on.

`main` is the sole entry point — nothing imports it. It is the only module
that orchestrates both phases (ingestion + agent pipeline).

## Data flow

```
1. main.py receives --input <path-or-url>
2. fetcher.py resolves to a local directory (clones if GitHub URL)
3. parser.py walks all .py files → list[FileInfo] via AST extraction
4. graph.py builds DependencyGraph from import statements
5. detector.py reads pyproject.toml → StackInfo
6. CodebaseManifest assembled, validated by Pydantic, saved to manifest.json
7. LangGraph pipeline invoked with initial DocState (manifest_path set)
8. planner_node loads manifest → seeds DocState, sets sections_to_write
9. ArchitectureAgent: renders architecture.j2 with manifest context → LLM → architecture_doc
10. APIWriterAgent: renders api.j2 with public surface context → LLM → api_doc
11. DBWriterAgent → auth_writer → deploy_writer (same pattern)
12. assembler_node collects all *_doc fields → final_docs dict
13. main.py writes one numbered .md file per section to output/
```

## Key design decisions

**AST over regex** — `parser.py` uses Python's stdlib `ast` module
exclusively. This gives typed, structured access to every syntactic element
without a single regex. It handles any valid Python 3.11+ syntax reliably
and adds zero dependencies.

**Strategy pattern for LLM** — `BaseLLMClient` ABC with `complete()` as
the sole interface. Mock and real implementations are interchangeable.
One env var (`AUTODOC_USE_MOCK`) controls which runs. No agent ever imports
`MockLLMClient` or `AnthropicClient` directly — only the factory.

**Jinja2 templates for prompts** — prompts are `.j2` files, not f-strings.
They are readable documents that can be edited independently of Python code.
`StrictUndefined` catches missing variables at development time.
Context is built from real manifest data — actual names, actual edges.

**Pydantic v2 data contracts** — all cross-module data is a Pydantic model.
Validation happens at construction. `CodebaseManifest` nests six model
types. Invalid ingestion output is caught before reaching any agent.

**TypedDict for LangGraph state** — `DocState` is a `TypedDict` rather than
a Pydantic model because LangGraph requires plain dicts. TypedDict gives
IDE autocomplete and type checker coverage at zero runtime cost per
state update.

**Error propagation via state** — any node that fails writes to
`state["error"]` and returns. Every downstream agent checks this field
first and short-circuits. The pipeline never crashes mid-run — errors
surface cleanly at the assembler.
