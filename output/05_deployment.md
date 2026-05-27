# Deployment and infrastructure

## Requirements

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.11+ | `tomllib` stdlib requires 3.11 |
| uv | latest | Package manager and venv |
| git | any | Required for GitHub URL input |

No external services needed in mock mode. Real mode requires an
Anthropic API key from `https://console.anthropic.com`.

## Environment variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| ANTHROPIC_API_KEY | Anthropic API key | Only when `USE_MOCK=false` | empty |
| AUTODOC_USE_MOCK | Use mock LLM responses | No | `true` |
| AUTODOC_OUTPUT_DIR | Output directory for docs | No | `./output` |
| AUTODOC_TEMP_DIR | Temp dir for repo clones | No | `./temp_repos` |
| AUTODOC_LOG_LEVEL | Logging verbosity | No | `INFO` |
| AUTODOC_LOG_FILE | Log file path (empty to disable) | No | `./output/autodoc.log` |

## Local setup

**Step 1 — Clone**
```bash
git clone https://github.com/yourusername/autodoc-agent.git
cd autodoc-agent
```

**Step 2 — Install dependencies**
```bash
uv sync
```
Creates `.venv/` and installs all packages from `pyproject.toml`.
Run once, or again after any dependency change.

**Step 3 — Configure**
```bash
cp .env.example .env
```
Default values work immediately for mock mode. No edits needed.

**Step 4 — Run**
```bash
# Against a local project
uv run python main.py --input ./path/to/project

# Against a GitHub repository
uv run python main.py --input https://github.com/username/repo
```

Output files are written to `output/` as numbered Markdown files.

## Running tests

```bash
uv run pytest                          # all tests
uv run pytest -v                       # verbose
uv run pytest --tb=short               # short tracebacks on failure
uv run pytest tests/test_ingestion.py  # ingestion only
uv run pytest tests/test_agents.py     # agent pipeline only
uv run pytest tests/test_writers.py    # prompt + writer tests only
```

Current test count: 45 tests across 3 files.

## Switching to real LLM mode

Edit `.env`:
```bash
ANTHROPIC_API_KEY=sk-ant-your-key-here
AUTODOC_USE_MOCK=false
```

Zero code changes needed. The factory in `autodoc/llm/__init__.py`
handles the swap automatically.

## Debug mode

```bash
# In .env
AUTODOC_LOG_LEVEL=DEBUG
```

Surfaces per-file parse results, dependency edges, prompt lengths,
mock routing decisions, and LLM response sizes. Written to both
terminal and `output/autodoc.log`.

## Production notes

AutoDoc has no server component, no database, and no persistent state
between runs. Each run is fully self-contained.

For CI/CD pipeline integration:
```bash
uv run python main.py --input . 
```

The exit code is 0 on success, 1 on error — standard for pipeline steps.
