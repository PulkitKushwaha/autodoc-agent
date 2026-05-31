# Deployment and infrastructure

## Requirements

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.11+ | `tomllib` stdlib requires 3.11 |
| uv | latest | Package manager, replaces pip + venv |
| git | any recent | Required for GitHub URL input mode |
| Anthropic API key | — | Only needed when `AUTODOC_USE_MOCK=false` |

No external services required in mock mode (the default).

## Environment variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| ANTHROPIC_API_KEY | Anthropic API key | Only when `USE_MOCK=false` | empty |
| AUTODOC_USE_MOCK | Use mock LLM responses | No | `true` |
| AUTODOC_OUTPUT_DIR | Output directory for generated docs | No | `./output` |
| AUTODOC_TEMP_DIR | Temp directory for repo clones | No | `./temp_repos` |
| AUTODOC_LOG_LEVEL | Logging verbosity | No | `INFO` |
| AUTODOC_LOG_FILE | Log file path — empty string to disable | No | `./output/autodoc.log` |

## Local setup

**Step 1 — Clone the repository**
```bash
git clone https://github.com/yourusername/autodoc-agent.git
cd autodoc-agent
```

**Step 2 — Install all dependencies**
```bash
uv sync
```
Creates `.venv/` and installs everything from `pyproject.toml`.
Run once initially, then again after any dependency changes.

**Step 3 — Configure environment**
```bash
cp .env.example .env
```
Default values work immediately. No edits needed for mock mode.

**Step 4 — Run against a local project**
```bash
uv run python main.py --input ./path/to/your/project
```

**Step 5 — Run against a GitHub repository**
```bash
uv run python main.py --input https://github.com/username/repo
```

Output is written to `output/` as five numbered Markdown files.

## Running tests

```bash
uv run pytest                           # all 65 tests
uv run pytest -v                        # verbose with test names
uv run pytest --tb=short                # short tracebacks on failure
uv run pytest tests/test_ingestion.py   # ingestion layer — 16 tests
uv run pytest tests/test_agents.py      # agent pipeline — 12 tests
uv run pytest tests/test_writers.py     # prompt + writers — 37 tests
uv run pytest --cov=autodoc             # with coverage report
```

## CI/CD
No CI/CD configuration has been added to this project yet. A recommended
basic pipeline for GitHub Actions:

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v2
      - run: uv sync
      - run: uv run pytest --tb=short
    env:
      AUTODOC_USE_MOCK: "true"
```

## Switching to real LLM mode

Edit `.env`:
```bash
ANTHROPIC_API_KEY=sk-ant-your-key-here
AUTODOC_USE_MOCK=false
```

Zero code changes needed anywhere. The factory in `autodoc/llm/__init__.py`
handles the swap automatically.

## Debug mode

```bash
# In .env
AUTODOC_LOG_LEVEL=DEBUG
```

Surfaces per-file parse results, dependency edges, Jinja2 template
rendering details, prompt lengths, mock routing decisions, and LLM
response sizes. Logs written to both terminal and `output/autodoc.log`.

## Production considerations
AutoDoc has no server component, no database, and no persistent state
between runs. Each invocation is fully self-contained.

For CI/CD pipeline integration:
```bash
uv run python main.py --input .
```

The process exits with code `0` on success and `1` on unhandled error —
standard for pipeline steps.

For Docker:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install uv && uv sync
ENTRYPOINT ["uv", "run", "python", "main.py"]
```
