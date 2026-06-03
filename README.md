# AutoDoc — AI-powered technical documentation agent

> Point it at any Python repository. Get back complete technical documentation — architecture, API reference, data models, deployment guide, and more.

AutoDoc is a multi-agent system built on LangGraph that ingests a Python codebase, coordinates five specialist LLM-powered writer agents, passes all generated sections through a critic agent that scores quality and triggers revision on weak sections, then renders the final output as Markdown, a static HTML site, and PDF.

---

## Demo

Running AutoDoc against itself:

```
$ autodoc run --input ./autodoc --format all

╭─────────────────────────────────────────────────────╮
│ AutoDoc — agentic documentation generator           │
│ Input:   ./autodoc                                  │
│ Output:  ./output                                   │
│ Formats: md, html, pdf                              │
│ LLM:     mock (Anthropic Claude)                    │
╰─────────────────────────────────────────────────────╯

Phase 1 — ingestion
  Parsed 33 Python files
  Entry points: main
  Other tools: Pydantic, LangGraph, Anthropic, Rich, Typer

Phase 2 — agent pipeline
  ⠸ Running agent pipeline... ████████░░ 7/8

  ┌─────────────────────────────────────────┐
  │ Quality scores                          │
  ├──────────────────┬────────┬─────────────┤
  │ Section          │ Score  │ Status      │
  ├──────────────────┼────────┼─────────────┤
  │ architecture     │ 8/10   │ ✓ passed    │
  │ api              │ 9/10   │ ✓ passed    │
  │ db               │ 8/10   │ revised     │
  │ auth             │ 8/10   │ ✓ passed    │
  │ deploy           │ 9/10   │ ✓ passed    │
  └──────────────────┴────────┴─────────────┘
  Revision rounds completed: 1

Phase 3 — rendering
  Markdown  → output/documentation.md
  HTML site → output/site/index.html
  PDF       → output/autodoc_documentation.pdf

Done. Documentation written to output/
```

Sample output is committed in [`docs/sample-output/`](docs/sample-output/).

---

## Quickstart

```bash
git clone https://github.com/yourusername/autodoc-agent.git
cd autodoc-agent
uv sync
cp .env.example .env
autodoc run --input ./your-python-project
```

No API key needed — AutoDoc runs in mock mode by default.

---

## How it works

```
Input (GitHub URL or local path)
         │
         ▼
┌─────────────────────────────────┐
│         Ingestion engine        │
│  fetcher → parser → graph →     │
│  detector → CodebaseManifest    │
└──────────────┬──────────────────┘
               │  manifest.json
               ▼
┌─────────────────────────────────────────────────────────┐
│                  LangGraph pipeline                     │
│                                                         │
│  planner                                                │
│     │                                                   │
│     ▼                                                   │
│  architecture → api → db → auth → deploy                │
│                                   │                     │
│                                   ▼                     │
│                                critic                   │
│                               ╱       ╲                 │
│                          revise       done              │
│                            │            │               │
│                    revision_router   assembler           │
│                            │            │               │
│                    (writers again)   final_docs          │
└─────────────────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│           Renderers             │
│  Markdown │ HTML site │ PDF     │
└─────────────────────────────────┘
               │
               ▼
         output/
```

### Pipeline stages

**Ingestion** — `fetcher.py` clones a GitHub URL or resolves a local path. `parser.py` uses Python's stdlib `ast` module to extract every class, function, argument, and import from every `.py` file. `graph.py` builds an internal import dependency graph. `detector.py` infers the tech stack from `pyproject.toml` or `requirements.txt`. Everything is assembled into a `CodebaseManifest` — a typed, validated Pydantic model saved to `manifest.json`.

**Planner** — reads the manifest, determines which documentation sections are worth writing based on what the codebase actually contains (no database detected → no DB section), and seeds the shared `DocState`.

**Writer agents** — five specialist agents, each rendering a Jinja2 template with real manifest data before calling the LLM. The architecture agent feeds entry points, dependency edges, and per-file summaries. The API agent extracts the full public surface with signatures and docstrings. The DB agent detects SQLAlchemy and Pydantic models. The auth agent scans for JWT/OAuth patterns. The deploy agent detects CI/CD files and package managers.

**Critic** — reviews all five sections in one LLM call, scores each 1-10, and returns structured JSON with specific feedback per section. Sections below score 7 are sent back to their writer with the critique injected into the Jinja2 template. Capped at 2 revision rounds.

**Renderers** — `render_markdown()` assembles all sections into a single `documentation.md` with table of contents. `render_html_site()` generates a multi-page static site. `render_pdf()` converts the HTML site to PDF via WeasyPrint.

---

## Installation

**Requirements:** Python 3.11+, [uv](https://docs.astral.sh/uv/)

```bash
git clone https://github.com/yourusername/autodoc-agent.git
cd autodoc-agent
uv sync
```

For PDF generation, WeasyPrint requires system libraries:

```bash
# Ubuntu / Debian
sudo apt-get install libpango-1.0-0 libpangoft2-1.0-0

# macOS
brew install pango
```

---

## Usage

```bash
# Generate Markdown documentation (default)
autodoc run --input ./myproject

# Generate all formats
autodoc run --input ./myproject --format all

# Specific formats
autodoc run --input ./myproject --format md,html

# From a GitHub URL
autodoc run --input https://github.com/tiangolo/fastapi --format md

# Custom output directory
autodoc run --input ./myproject --output ./docs --format all

# Verbose logging
autodoc run --input ./myproject --log-level DEBUG

# Show version
autodoc version
```

### Output structure

```
output/
├── manifest.json                  ← structured codebase analysis
├── autodoc.log                    ← full run log (append-only)
├── documentation.md               ← combined Markdown document
├── site/
│   ├── index.html                 ← HTML site homepage
│   ├── architecture.html
│   ├── api.html
│   ├── db.html
│   ├── auth.html
│   └── deploy.html
└── projectname_documentation.pdf  ← PDF export
```

---

## Configuration

Copy `.env.example` to `.env` and edit as needed.

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Anthropic API key | empty |
| `AUTODOC_USE_MOCK` | Use mock LLM responses | `true` |
| `AUTODOC_OUTPUT_DIR` | Output directory | `./output` |
| `AUTODOC_TEMP_DIR` | Temp dir for repo clones | `./temp_repos` |
| `AUTODOC_LOG_LEVEL` | Log verbosity | `INFO` |
| `AUTODOC_LOG_FILE` | Log file path | `./output/autodoc.log` |

### Switching to real LLM

```bash
# In .env
ANTHROPIC_API_KEY=sk-ant-your-key-here
AUTODOC_USE_MOCK=false
```

No code changes needed anywhere. The factory in `autodoc/llm/__init__.py` handles the swap.

---

## Tech stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Agent orchestration | LangGraph | Fine-grained control over agent graph, conditional edges, revision loops |
| LLM | Anthropic Claude (Sonnet 4) | Best-in-class instruction following for structured output |
| Code parsing | Python `ast` (stdlib) | Zero dependencies, handles any valid Python 3.11+ syntax |
| Data validation | Pydantic v2 | Typed contracts between pipeline stages, JSON serialization |
| Prompt templates | Jinja2 | Readable, editable prompt files separate from Python code |
| CLI | Typer + Rich | Type-annotated CLI with live progress bars |
| PDF generation | WeasyPrint | Pure Python HTML→PDF, no external browser needed |
| Package manager | uv | Fast, reproducible installs from `pyproject.toml` |

---

## Project structure

```
autodoc-agent/
├── autodoc/
│   ├── cli.py                 — Typer CLI application
│   ├── config.py              — Pydantic BaseSettings, env config
│   ├── logger.py              — structured logging setup
│   ├── agents/
│   │   ├── base.py            — BaseAgent ABC
│   │   ├── planner.py         — seeds pipeline state
│   │   ├── architecture.py    — system overview writer
│   │   ├── api_writer.py      — API reference writer
│   │   ├── db_writer.py       — data model writer
│   │   ├── auth_writer.py     — auth/security writer
│   │   ├── deploy_writer.py   — deployment guide writer
│   │   └── critic.py          — quality scorer + revision trigger
│   ├── graph/
│   │   └── pipeline.py        — LangGraph StateGraph wiring
│   ├── ingestion/
│   │   ├── fetcher.py         — GitHub URL clone / local path
│   │   ├── parser.py          — AST extraction
│   │   ├── graph.py           — dependency graph builder
│   │   └── detector.py        — tech stack inference
│   ├── llm/
│   │   ├── base.py            — BaseLLMClient ABC
│   │   ├── client.py          — AnthropicClient (real)
│   │   └── mock.py            — MockLLMClient (dev)
│   ├── models/
│   │   ├── manifest.py        — CodebaseManifest Pydantic model
│   │   └── doc_state.py       — DocState TypedDict
│   ├── prompts/               — Jinja2 prompt templates (.j2)
│   ├── renderers/
│   │   ├── markdown.py        — Markdown assembler
│   │   ├── html_site.py       — static HTML site generator
│   │   └── pdf.py             — WeasyPrint PDF renderer
│   ├── templates/             — Jinja2 output templates (.j2)
│   └── utils/
│       └── prompt_renderer.py — centralised Jinja2 renderer
├── docs/
│   └── sample-output/         — sample docs generated by AutoDoc
├── tests/
│   ├── test_ingestion.py      — 16 tests
│   ├── test_agents.py         — 12 tests
│   ├── test_writers.py        — 37 tests
│   ├── test_critic.py         — 18 tests
│   └── test_renderers.py      — 19 tests
├── main.py                    — legacy entry point
├── pyproject.toml
└── .env.example
```

---

## Development

**Run all tests:**
```bash
uv run pytest
uv run pytest -v --tb=short
uv run pytest --cov=autodoc
```

**Adding a new writer agent:**
1. Create `autodoc/agents/mywriter.py` inheriting from `BaseAgent`
2. Set `_state_key`, `_system`, implement `_build_prompt()`
3. Add a corresponding `autodoc/prompts/mywriter.j2` template
4. Add `run()` override to store critique: `self._critique = state.get("critique", {}).get("mykey", "")`
5. Register the node in `autodoc/graph/pipeline.py`
6. Add the new key to `DocState` in `autodoc/models/doc_state.py`
7. Add tests in `tests/test_writers.py`

**Debug a specific agent:**
```bash
AUTODOC_LOG_LEVEL=DEBUG autodoc run --input ./myproject
```

---

## Roadmap

- [ ] Multi-language support (JavaScript, TypeScript, Go)
- [ ] GitHub Actions integration — auto-generate docs on push
- [ ] Notion and GitHub Wiki export
- [ ] Parallel agent execution via LangGraph `Send()` API
- [ ] VS Code extension

---

## License

MIT — see [LICENSE](LICENSE)
