# Authentication and security

## Overview
AutoDoc is a local command-line tool with no user-facing authentication.
It has no login system, no sessions, and no user accounts. Security
considerations are limited to API key management, safe handling of
cloned repositories, and ensuring no credentials are logged or committed
to version control. The `AuthWriterAgent` is designed to document
authentication in the **target** project being analyzed — not in
AutoDoc itself.

## Authentication mechanism
AutoDoc uses no authentication mechanism for its own operation. The only
credential it handles is the Anthropic API key, which is managed through
environment variables following the twelve-factor app pattern.

## Key components

**`autodoc.config.Settings.anthropic_api_key`** — the only sensitive
field in the codebase. Declared with `alias="ANTHROPIC_API_KEY"` to read
from the standard env var name without the `AUTODOC_` prefix. Populated
by Pydantic `BaseSettings` at startup from the `.env` file.

**`autodoc.llm.get_llm_client()`** — the only function that reads
`AUTODOC_USE_MOCK`. When mock mode is active (`true` by default),
`anthropic_api_key` is never accessed. The API key is only read when
`AUTODOC_USE_MOCK=false` is explicitly set.

**`autodoc.ingestion.fetcher.cleanup()`** — removes temporary cloned
repositories unconditionally via `try/finally` in `main.py`. Ensures
cloned content is never left on disk after a run, whether it succeeds
or fails.

## Security measures

| Measure | Implementation |
|---------|---------------|
| API key never hardcoded | Pydantic `BaseSettings` reads from `.env` only |
| API key never logged | No log statement references `settings.anthropic_api_key` |
| `.env` gitignored | Root `.gitignore` excludes `.env` |
| `.env.example` committed | Documents required variables with empty values |
| Temp repos always cleaned up | `try/finally` block in `main.py` |
| Shallow clone only | `depth=1` in `git.Repo.clone_from()` |
| No outbound network beyond LLM | Only `anthropic` SDK makes external calls |
| `StrictUndefined` in Jinja2 | Prompt variable errors caught at dev time |
| Mock mode on by default | `AUTODOC_USE_MOCK=true` — key never needed in development |

## Notes for developers

**Never commit `.env`** — the `.gitignore` prevents it, but be aware
of tools that bypass gitignore (e.g. `git add -f`).

**Never log sensitive values** — if you add new configuration fields
that hold credentials, ensure no log statement references them directly.
The pattern throughout the codebase is to log the field name or a
redacted indicator, never the value.

**Temp directory hygiene** — if you add new code paths that clone or
copy external content, always use `try/finally` for cleanup. The pattern
is established in `main.py` — follow it.

**Mock mode for CI** — all CI pipelines should run with `AUTODOC_USE_MOCK=true`.
Never put a real API key in CI environment variables for test runs — the
mock client produces deterministic output that is better suited for testing.
