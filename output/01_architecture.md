# System architecture
 
## Overview
AutoDoc is an agentic documentation generator that ingests Python codebases
and produces comprehensive technical documentation. It uses a multi-agent
pipeline built on LangGraph where specialist agents each handle one section
of the documentation, coordinated by a planner that reads a structured
manifest of the codebase produced by an AST-based ingestion engine.
 
## Project structure
 
```
autodoc-agent/
├── autodoc/
│   ├── config.py          — centralised settings via Pydantic BaseSettings
│   ├── logger.py          — structured logging, RichHandler + file handler
│   ├── ingestion/         — codebase parsing and analysis
│   │   ├── fetcher.py     — GitHub URL clone or local path resolution
│   │   ├── parser.py      — AST-based extraction of classes, functions, imports
│   │   ├── graph.py       — internal import dependency graph builder
│   │   └── detector.py    — tech stack inference from dependency files
│   ├── models/
│   │   ├── manifest.py    — CodebaseManifest Pydantic model (ingestion output)
│   │   └── doc_state.py   — DocState TypedDict (LangGraph pipeline state)
│   ├── agents/            — specialist writer agents
│   │   ├── base.py        — BaseAgent ABC with shared LLM and error handling
│   │   ├── planner.py     — reads manifest, seeds DocState
│   │   ├── architecture.py
│   │   ├── api_writer.py
│   │   ├── db_writer.py
│   │   ├── auth_writer.py
│   │   └── deploy_writer.py
│   ├── graph/
│   │   └── pipeline.py    — StateGraph wiring, assembler node
│   └── llm/
│       ├── base.py        — BaseLLMClient ABC
│       ├── client.py      — AnthropicClient (real API)
│       └── mock.py        — MockLLMClient (development)
├── main.py                — CLI entry point, orchestrates both phases
└── tests/                 — pytest test suite
```
 
## Core components
 
### Ingestion engine (`autodoc/ingestion/`)
The foundation of the entire system. Accepts a GitHub URL or local path,
recursively parses every Python file using Python's built-in `ast` module,
builds an internal import dependency graph, and infers the tech stack from
`pyproject.toml` or `requirements.txt`. Produces a `CodebaseManifest` — a
fully validated Pydantic model serialized to `output/manifest.json`.
 
### LLM abstraction layer (`autodoc/llm/`)
Implements the strategy pattern via `BaseLLMClient`. `get_llm_client()` in
`llm/__init__.py` is the single decision point — it reads `AUTODOC_USE_MOCK`
from the environment and returns either `MockLLMClient` or `AnthropicClient`.
Every agent calls this factory and never knows which implementation it holds.
Switching from mock to real requires one environment variable change.
 
### Agent pipeline (`autodoc/agents/`, `autodoc/graph/`)
A LangGraph `StateGraph` where each node is a Python function that reads
from `DocState`, calls the LLM, and writes its output back into the state.
The planner node runs first to seed the state. Five specialist writer agents
run sequentially. The assembler node collects all sections into `final_docs`.
 
### Data models (`autodoc/models/`)
Two contracts govern data flow through the system. `CodebaseManifest` is a
Pydantic model — validated on construction, serializable to JSON, the source
of truth for every agent's prompt. `DocState` is a `TypedDict` — required
by LangGraph, holds all intermediate and final documentation output.
 
### Configuration (`autodoc/config.py`)
A single `Settings` instance backed by Pydantic `BaseSettings` reads all
configuration from the environment and `.env` file. No scattered
`os.getenv()` calls exist anywhere else in the codebase.
 
## Data flow
 
```
Input (GitHub URL or local path)
    ↓
fetcher.py — resolve to local directory
    ↓
parser.py — AST extraction → list[FileInfo]
    ↓
graph.py — dependency graph → DependencyGraph
    ↓
detector.py — stack inference → StackInfo
    ↓
CodebaseManifest — validated, saved to manifest.json
    ↓
planner_node — reads manifest, seeds DocState
    ↓
ArchitectureAgent → api_writer → db_writer → auth_writer → deploy_writer
    ↓
assembler_node — collects all sections into final_docs
    ↓
main.py — writes one .md file per section to output/
```
 
## Key design decisions
 
**AST over regex for parsing** — Python's stdlib `ast` module gives typed
access to every class, function, argument, and annotation in the source.
It is reliable, has zero external dependencies, and handles any valid
Python 3.11+ syntax without a single regex.
 
**Strategy pattern for LLM clients** — `BaseLLMClient` is an ABC with one
method. Mock and real clients are interchangeable. The factory function is
the only place the decision is made. This enables full end-to-end testing
with zero API cost and a zero-code switch to production.
 
**Pydantic v2 as the data contract** — all data that crosses a module
boundary is a Pydantic model. Validation happens at construction time.
Bad data from the ingestion engine is caught before it reaches any agent.
 
**TypedDict for LangGraph state** — LangGraph requires plain dicts for
state. `DocState` is a `TypedDict` which gives IDE autocomplete and type
checker coverage without Pydantic's runtime overhead on every state update.
 
**Sequential agent execution** — writers currently run sequentially in the
graph. True parallel execution via LangGraph's `Send()` API is added in
Day 5 when the full writer and critic set is in place.
 
