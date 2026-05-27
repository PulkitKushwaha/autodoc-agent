# Authentication and security

## Overview
AutoDoc is a local command-line tool with no user-facing authentication.
Security considerations are confined to API key management, safe handling
of cloned repositories, and ensuring no credentials are logged or committed.

## API key management

The only sensitive credential AutoDoc handles is the Anthropic API key.

**Storage** — stored exclusively in `.env`, listed in `.gitignore`,
never committed. `.env.example` documents the variable with an empty value.

**Access pattern** — read once at startup by Pydantic `BaseSettings`
in `config.py`. No other module calls `os.getenv("ANTHROPIC_API_KEY")`.
The key is accessed from exactly one place in the codebase.

**Mock mode** — `AUTODOC_USE_MOCK=true` (the default) means the key
is never read or used. `get_llm_client()` returns `MockLLMClient`
without touching the key field. The project is safe to develop, test,
and demonstrate with no credential exposure.

**Logging** — no log statement anywhere in the codebase references
`settings.anthropic_api_key`. The key never appears in `output/autodoc.log`.

## Repository access

GitHub URLs are cloned with `depth=1` (shallow) into a `tempfile.mkdtemp()`
directory. The temp directory is always removed in a `try/finally` block
in `main.py` — on success and on any exception. AutoDoc passes no
credentials to git — private repos require the user's local git config.

## Security measures

| Measure | Implementation |
|---------|---------------|
| API key never hardcoded | Pydantic BaseSettings + .env |
| API key never logged | No log call references the key field |
| .env gitignored | Root `.gitignore` entry |
| Temp repos always removed | `try/finally` in `main.py` |
| Shallow clone only | `depth=1` in `git.Repo.clone_from()` |
| No outbound network beyond LLM | Only `anthropic` SDK makes external calls |
| StrictUndefined in Jinja2 | Prompt variables caught at dev time not runtime |

## Key classes and functions

`autodoc.config.Settings.anthropic_api_key` — declared with
`alias="ANTHROPIC_API_KEY"` to bypass the `AUTODOC_` prefix. The only
field holding a sensitive value.

`autodoc.llm.get_llm_client()` — the only function reading
`AUTODOC_USE_MOCK`. When mock mode is active, `anthropic_api_key`
is never accessed.

`autodoc.ingestion.fetcher.cleanup()` — removes temp directories.
Called unconditionally in `main.py`'s `finally` block.
