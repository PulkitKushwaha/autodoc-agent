# System architecture

## Overview
AutoDoc is an agentic documentation generator that ingests Python codebases
and produces comprehensive technical documentation across five sections:
architecture, API reference, data models, authentication, and deployment.
It uses a LangGraph multi-agent pipeline where a planner node seeds shared
state and five specialist writer agents — each powered by a Jinja2 prompt
template feeding real manifest context to Claude — produce structured
Markdown documentation before an assembler node collects the final output.

## Project structure

```
autodoc-agent/
├── main.py                      — CLI entry point, Phase 1 + Phase 2 orchestration
├── pyproject.toml               — dependencies, ruff, pytest config
├── .env.example                 — environment variable documentation
├── autodoc/
│   ├── config.py                — Pydantic BaseSettings, single settings instance
│   ├── logger.py                — RichHandler + file handler, per-module loggers
│   ├── ingestion/
│   │   ├── fetcher.py           — GitHub URL clone + local path resolution
│   │   ├── parser.py            — AST extraction of classes, functions, imports
│   │   ├── graph.py             — internal import dependency graph
│   │   └── detector.py          — tech stack inference from dependency files
│   ├── models/
│   │   ├── manifest.py          — CodebaseManifest and all nested Pydantic models
│   │   └── doc_state.py         — DocState TypedDict for LangGraph state
│   ├── agents/
│   │   ├── base.py              — BaseAgent ABC: LLM, error handling, logging
│   │   ├── planner.py           — seeds DocState, determines sections
│   │   ├── architecture.py      — system overview writer
│   │   ├── api_writer.py        — API reference writer
│   │   ├── db_writer.py         — data model writer (SQLAlchemy + Pydantic)
│   │   ├── auth_writer.py       — auth/security writer (JWT/OAuth detection)
│   │   └── deploy_writer.py     — deployment writer (CI/CD + package manager)
│   ├── graph/
│   │   └── pipeline.py          — StateGraph wiring, assembler node
│   ├── prompts/
│   │   ├── architecture.j2      — architecture agent Jinja2 template
│   │   ├── api.j2               — API reference agent Jinja2 template
│   │   ├── db.j2                — data model agent Jinja2 template
│   │   ├── auth.j2              — auth agent Jinja2 template
│   │   └── deploy.j2            — deployment agent Jinja2 template
│   ├── utils/
│   │   └── prompt_renderer.py   — centralised Jinja2 renderer, StrictUndefined
│   └── llm/
│       ├── base.py              — BaseLLMClient ABC
│       ├── client.py            — AnthropicClient (production)
│       └── mock.py              — MockLLMClient (development)
└── tests/
    ├── test_ingestion.py        — 16 tests
    ├── test_agents.py           — 12 tests
    └── test_writers.py          — 37 tests
```

## Core components

### Ingestion engine (`autodoc/ingestion/`)
Accepts a GitHub URL or local path, parses every `.py` file using
Python's `ast` module, builds an internal import dependency graph,
and infers the tech stack from `pyproject.toml` or `requirements.txt`.
Produces a `CodebaseManifest` — a fully validated Pydantic model saved
to `output/manifest.json` as the single source of truth for all agents.

### Prompt engineering layer (`autodoc/prompts/`, `autodoc/utils/`)
Five Jinja2 `.j2` templates — one per documentation section. Each template
defines exactly what structural context the LLM receives. `render_prompt()`
in `utils/prompt_renderer.py` is the single entry point for all template
rendering, using `StrictUndefined` to catch missing variables immediately.
All five agents now feed rich, codebase-specific context rather than
generic descriptions.

### Agent pipeline (`autodoc/agents/`, `autodoc/graph/`)
A LangGraph `StateGraph` with `DocState` as shared state. The planner
determines which sections to write. Five specialist agents run
sequentially — each inheriting from `BaseAgent`, each rendering its
own Jinja2 template with manifest-extracted context before calling the
LLM. The assembler collects all sections into `final_docs`.

### LLM abstraction layer (`autodoc/llm/`)
Strategy pattern: `BaseLLMClient` ABC, `AnthropicClient` (real),
`MockLLMClient` (development). `get_llm_client()` is the only decision
point. One env var (`AUTODOC_USE_MOCK`) controls which runs.

## Dependency structure

```
main                              ← sole entry point
  ├── autodoc.ingestion.*         ← Phase 1: ingest and parse
  └── autodoc.graph.pipeline      ← Phase 2: agent pipeline
        ├── autodoc.agents.*      ← 5 specialist writers + planner
        │     ├── autodoc.llm     ← LLM abstraction
        │     └── autodoc.utils   ← Jinja2 prompt rendering
        │           └── autodoc.prompts  ← .j2 template files
        └── autodoc.models.*      ← data contracts (core — imported everywhere)
              autodoc.logger      ← logging utility (core — imported everywhere)
```

`autodoc.logger` and `autodoc.models.manifest` are the two core modules
— imported by five or more modules each. They are the shared
infrastructure the entire system depends on.

## Data flow

```
1.  main.py — receives --input <path-or-url>
2.  fetcher.py — resolves to local directory
3.  parser.py — AST walk → list[FileInfo]
4.  graph.py — builds DependencyGraph from imports
5.  detector.py — reads pyproject.toml → StackInfo
6.  CodebaseManifest — validated, saved to output/manifest.json
7.  LangGraph pipeline invoked with initial DocState
8.  planner_node — loads manifest, seeds state, sets sections_to_write
9.  ArchitectureAgent — renders architecture.j2 → LLM → architecture_doc
10. APIWriterAgent — renders api.j2 → LLM → api_doc
11. DBWriterAgent — detects models → renders db.j2 → LLM → db_doc
12. AuthWriterAgent — detects auth patterns → renders auth.j2 → LLM → auth_doc
13. DeployWriterAgent — detects CI/CD → renders deploy.j2 → LLM → deploy_doc
14. assembler_node — collects all *_doc fields → final_docs
15. main.py — writes 5 numbered .md files to output/
```

## Key design decisions

**AST over regex** — `parser.py` uses Python's stdlib `ast` module.
Typed, structured access to every class, function, and import.
Zero external dependencies, handles any valid Python 3.11+ syntax.

**Jinja2 templates for all prompts** — all five agents use `.j2` files.
Prompts are readable, editable documents independent of Python code.
`StrictUndefined` catches missing variables at development time.
Context is extracted from real manifest data — actual names and edges.

**Specialist extraction per agent** — each agent applies its own lens
to the manifest. DBWriterAgent looks for `BaseModel`/`Base` subclasses.
AuthWriterAgent scans for auth-keyword modules and classes. DeployWriterAgent
detects CI/CD files and package managers. The LLM receives only what
is relevant to its section.

**Strategy pattern for LLM** — `BaseLLMClient` ABC, one factory function,
one env var. No agent ever imports a concrete LLM client directly.

**Pydantic v2 contracts** — all cross-module data is validated on
construction. `TypedDict` for LangGraph state — plain dict at runtime,
full IDE coverage at development time.

**Error propagation via state** — any node writes to `state["error"]`
on failure and returns. Every downstream node checks this first.
The pipeline never crashes mid-run.
