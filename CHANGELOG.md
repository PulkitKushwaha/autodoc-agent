# Changelog

All notable changes to AutoDoc are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [0.1.0] — 2026-05-21

First complete release. AutoDoc ingests a Python codebase and produces
professional technical documentation in Markdown, HTML, and PDF formats
through a self-evaluating multi-agent LangGraph pipeline.

### Added

#### Day 1 — Codebase ingestion engine
- `autodoc/ingestion/fetcher.py` — resolves GitHub URLs (shallow clone via
  gitpython) and local paths to a working directory
- `autodoc/ingestion/parser.py` — AST-based extraction of all classes,
  functions, arguments, type annotations, docstrings, and imports from
  every `.py` file in a project
- `autodoc/ingestion/graph.py` — builds an internal import dependency graph,
  identifies entry points (nothing imports them) and core modules (imported
  by 3+ others)
- `autodoc/ingestion/detector.py` — infers tech stack from `pyproject.toml`,
  `requirements.txt`, and `setup.cfg` using normalised package name matching
- `autodoc/models/manifest.py` — `CodebaseManifest` Pydantic v2 model as the
  typed data contract between ingestion and all downstream agents
- `autodoc/llm/base.py` — `BaseLLMClient` ABC enforcing the `complete()` interface
- `autodoc/llm/client.py` — `AnthropicClient` using `claude-sonnet-4-20250514`
  with rate limit and API error handling
- `autodoc/llm/mock.py` — `MockLLMClient` with keyword-routed realistic
  responses for development without an API key
- `autodoc/llm/__init__.py` — `get_llm_client()` factory, single decision point
  controlled by `AUTODOC_USE_MOCK` environment variable
- `autodoc/config.py` — Pydantic `BaseSettings` reading all config from `.env`
- `autodoc/logger.py` — `RichHandler` terminal logging + optional file handler,
  noisy third-party loggers silenced
- `main.py` — initial CLI entry point orchestrating the ingestion pipeline
- 16 tests covering parser, dependency graph, stack detector, and manifest

#### Day 2 — LangGraph agent orchestration
- `autodoc/models/doc_state.py` — `DocState` TypedDict as single shared state
  object flowing through the entire LangGraph pipeline
- `autodoc/agents/base.py` — `BaseAgent` ABC with shared LLM access, manifest
  loading, upstream error checking, and structured logging
- `autodoc/agents/planner.py` — entry node that loads the manifest, determines
  which sections are worth writing, and seeds all state keys
- `autodoc/agents/architecture.py` — architecture section writer (stub)
- `autodoc/agents/api_writer.py` — API reference writer (stub)
- `autodoc/agents/db_writer.py` — data model writer (stub)
- `autodoc/agents/auth_writer.py` — authentication writer (stub)
- `autodoc/agents/deploy_writer.py` — deployment guide writer (stub)
- `autodoc/graph/pipeline.py` — `StateGraph` wiring with planner, five writers,
  and assembler node; `main.py` updated to run the full pipeline
- 12 tests covering planner, base agent error handling, assembler, and e2e

#### Day 3 — Jinja2 prompt templates + architecture/API writers
- `autodoc/utils/prompt_renderer.py` — centralised Jinja2 renderer with
  `StrictUndefined`, `trim_blocks`, and `lstrip_blocks`
- `autodoc/prompts/architecture.j2` — rich template feeding entry points,
  core modules, per-file breakdown, and dependency edges to the LLM
- `autodoc/prompts/api.j2` — template feeding the complete public API surface
  with full signatures, type annotations, and docstrings
- `autodoc/agents/architecture.py` — rewritten with manifest-aware context
  extraction rendering via Jinja2 template
- `autodoc/agents/api_writer.py` — rewritten with public surface extraction,
  private item filtering, and annotation preservation
- 17 tests covering prompt renderer, architecture agent, and API writer

#### Day 4 — DB, auth, and deployment writers
- `autodoc/prompts/db.j2` — template feeding detected model classes, Pydantic
  models, ORM base class detection, and database stack
- `autodoc/prompts/auth.j2` — template feeding auth-keyword modules/classes
  and cross-referenced auth library detection
- `autodoc/prompts/deploy.j2` — template feeding CI/CD files, package manager
  detection, lockfile presence, and entry points
- `autodoc/agents/db_writer.py` — rewritten with SQLAlchemy `Base` detection,
  Pydantic `BaseModel` detection, and model-file keyword matching
- `autodoc/agents/auth_writer.py` — rewritten with auth module/class name
  detection and known auth library cross-referencing
- `autodoc/agents/deploy_writer.py` — rewritten with CI/CD file detection,
  package manager detection (uv/poetry/pip/pipenv), lockfile detection
- 20 tests covering all three new agents

#### Day 5 — Critic agent and iterative refinement loop
- `autodoc/agents/critic.py` — `CriticAgent` scores sections 1-10, flags below
  `REVISION_THRESHOLD=7` for revision, caps at `MAX_REVISIONS=2`,
  `_parse_response()` strips markdown fences and handles malformed JSON
- `autodoc/prompts/critic.j2` — template requesting raw JSON with scores,
  critiques, and overall assessment in one LLM call
- `autodoc/graph/pipeline.py` — updated with critic node, `revision_router`
  node, `should_revise()` conditional edge function routing to revision
  or assembler; revision loop routes back through all writers
- `autodoc/models/doc_state.py` — four new fields: `critique`, `quality_scores`,
  `sections_to_revise`, `revision_count`
- All five writer templates updated with revision block — critique injected
  via `{{ critique }}` Jinja2 variable on second pass
- `autodoc/llm/mock.py` — `_critic_response()` added with `db` scored 6 to
  demonstrate revision loop in mock mode
- All five writer agents updated with `run()` override storing critique
- 18 tests covering critic scoring, JSON parsing, conditional routing,
  revision counter bounds, and full pipeline e2e

#### Day 6 — Multi-format renderer and Typer CLI
- `autodoc/renderers/markdown.py` — assembles all `final_docs` sections into
  `documentation.md` with table of contents via `doc.md.j2` template
- `autodoc/renderers/html_site.py` — generates multi-page static HTML site:
  index with section cards and quality scores, one page per section with
  sidebar navigation and breadcrumbs; inline Markdown-to-HTML conversion
- `autodoc/renderers/pdf.py` — converts HTML site to PDF via WeasyPrint with
  print-specific CSS: sidebar hidden, A4 page size, page numbers in footer
- `autodoc/templates/doc.md.j2` — Jinja2 template for combined Markdown output
- `autodoc/templates/site/index.html.j2` — HTML index page template
- `autodoc/templates/site/section.html.j2` — HTML section page template
- `autodoc/cli.py` — Typer app: `autodoc run --input --output --format` flags,
  Rich progress bar during pipeline, quality score table after critic,
  `autodoc version` subcommand
- `main.py` — replaced with thin wrapper delegating to `cli.py`, legacy
  `python main.py --input` interface preserved
- `pyproject.toml` — `weasyprint>=61.0` added
- 19 tests covering Markdown assembly, HTML generation, and format parsing

#### Day 7 — Documentation and portfolio wrap-up
- `README.md` — complete project documentation: pipeline architecture ASCII
  diagram, quickstart, usage examples, tech stack table, project structure,
  development guide, roadmap
- `CHANGELOG.md` — this file
- `docs/sample-output/` — sample documentation generated by running AutoDoc
  against itself, committed for portfolio visibility
- `pyproject.toml` — version set to `0.1.0`, homepage and repository URLs added

### Technical decisions

- **Python 3.11+** — required for stdlib `tomllib` (TOML parsing) and improved
  type union syntax (`X | Y`)
- **LangGraph over CrewAI** — fine-grained control over the agent graph,
  conditional edges, and revision loops not easily expressible in higher-level
  frameworks
- **`ast` module over third-party parsers** — zero dependencies, handles any
  valid Python syntax, produces typed structured output
- **Pydantic v2 for data contracts** — validation at construction time means
  bad ingestion data is caught before reaching any agent
- **TypedDict for LangGraph state** — LangGraph requires plain dicts; TypedDict
  gives IDE and type checker coverage at zero runtime cost
- **`AUTODOC_USE_MOCK=true` as default** — the project is fully functional
  and testable without an API key; switching to real requires one env change
