# Authentication and security

## Overview
AutoDoc itself has no user-facing authentication — it is a command-line
tool that runs locally. Security considerations are limited to API key
management and safe handling of cloned repository content.

## API key management

The only sensitive credential AutoDoc handles is the Anthropic API key.

**Storage** — the key is stored exclusively in the `.env` file which is
listed in `.gitignore` and never committed to version control. The
`.env.example` file documents the required variable with an empty value.

**Access pattern** — the key is read once at startup by Pydantic
`BaseSettings` in `config.py` and stored on the `settings` instance. No
other module calls `os.getenv("ANTHROPIC_API_KEY")` directly. This ensures
the key is accessed from exactly one place in the codebase.

**Mock mode** — when `AUTODOC_USE_MOCK=true` (the default), the API key
is never read or used. `get_llm_client()` returns `MockLLMClient` without
touching the key field at all. This means the project is safe to develop,
test, and demonstrate without ever exposing a real credential.

## Repository access

When a GitHub URL is provided as input, AutoDoc clones the repository
into a temporary directory using `gitpython` with `depth=1` (shallow
clone). The temporary directory is always cleaned up in a `try/finally`
block in `main.py` regardless of whether the run succeeds or fails.

Private repositories require the user's git credentials to be configured
in their local git environment — AutoDoc passes no credentials itself and
stores nothing beyond the temporary clone lifetime.

## Security measures

| Measure | Implementation |
|---------|---------------|
| API key never hardcoded | Pydantic BaseSettings + .env pattern |
| API key never logged | logger calls never reference the key field |
| .env gitignored | Enforced in .gitignore at project root |
| Temp repos always cleaned up | try/finally in main.py |
| No outbound requests beyond LLM | Only anthropic SDK makes network calls |
| Shallow clone only | depth=1 limits exposure to latest commit |

## Key classes and functions

`autodoc.config.Settings.anthropic_api_key` — the only field that holds
the API key. Declared with `alias="ANTHROPIC_API_KEY"` to map from the
standard env var name without the `AUTODOC_` prefix.

`autodoc.llm.get_llm_client()` — the only function that reads
`AUTODOC_USE_MOCK` and decides whether the API key is needed. If mock
mode is active, the key is never accessed.

`autodoc.ingestion.fetcher.cleanup()` — ensures cloned repositories are
removed from disk. Called in `main.py`'s `finally` block so cleanup
happens even when exceptions occur mid-run.
