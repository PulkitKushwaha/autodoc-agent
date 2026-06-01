import json

from autodoc.llm.base import BaseLLMClient
from autodoc.logger import get_logger

logger = get_logger(__name__)


class MockLLMClient(BaseLLMClient):
    """
    Mock LLM client for development without an API key.

    Routes prompts to realistic hardcoded responses by keyword matching.
    The full agent graph runs — only the API call is replaced.
    Includes a critic response with db scored 6 to demonstrate the
    revision loop working end to end in mock mode.
    Activate with AUTODOC_USE_MOCK=true in .env (the default).
    """

    def complete(self, prompt: str, system: str = "") -> str:
        logger.debug(
            "MockLLMClient.complete called — prompt: %d chars, system: %d chars",
            len(prompt),
            len(system),
        )

        response = self._route(prompt.lower())

        logger.debug("Mock response selected — %d chars", len(response))
        return response

    def _route(self, prompt_lower: str) -> str:
        if any(k in prompt_lower for k in ("scores", "critiques", "review each section")):
            return self._critic_response()
        if "architecture" in prompt_lower or "system overview" in prompt_lower:
            return self._architecture_response()
        if "api" in prompt_lower and (
            "endpoint" in prompt_lower or "reference" in prompt_lower
        ):
            return self._api_response()
        if any(k in prompt_lower for k in ("database", "schema", "data model")):
            return self._database_response()
        if any(k in prompt_lower for k in ("auth", "security", "authentication")):
            return self._auth_response()
        if any(k in prompt_lower for k in ("deploy", "infrastructure", "ci/cd")):
            return self._deployment_response()
        if any(k in prompt_lower for k in ("test", "testing", "coverage")):
            return self._testing_response()

        logger.debug("No keyword match — returning generic mock response")
        return self._generic_response()

    def _critic_response(self) -> str:
        return json.dumps({
            "scores": {
                "architecture": 8,
                "api":          9,
                "db":           6,
                "auth":         8,
                "deploy":       9,
            },
            "critiques": {
                "architecture": "No significant gaps.",
                "api":          "No significant gaps.",
                "db":           "Missing relationship descriptions between models. Field types not documented.",
                "auth":         "No significant gaps.",
                "deploy":       "No significant gaps.",
            },
            "overall_assessment": (
                "Documentation is comprehensive. "
                "Data models section needs relationship and field type details."
            ),
        })

    def _architecture_response(self) -> str:
        return """## System architecture

### Overview
This system follows a layered architecture pattern with clear separation between
the API layer, business logic, and data access layer.

### Components

**API layer** — Handles all incoming HTTP requests, validates input, and delegates
to the service layer. Built with FastAPI, providing automatic OpenAPI documentation.

**Service layer** — Contains all business logic. Services are stateless and depend
only on repository interfaces, making them fully testable in isolation.

**Repository layer** — Abstracts all database operations behind typed interfaces.
SQLAlchemy models are confined to this layer and never leak into business logic.

### Data flow
```
Client → Router → Service → Repository → Database
                ↓
            Pydantic schema validation at entry and exit points
```

### Key design decisions
- All inter-layer communication uses Pydantic models, not ORM objects
- Services receive dependencies via constructor injection for testability
- Async throughout — all I/O operations use async/await"""

    def _api_response(self) -> str:
        return """## API reference

### Authentication
All endpoints except `/health` and `/auth/login` require a Bearer token in the
`Authorization` header.

### Endpoints

#### `POST /auth/login`
Authenticates a user and returns a JWT token.

**Request body**
```json
{ "email": "string", "password": "string" }
```

**Response `200`**
```json
{ "access_token": "string", "token_type": "bearer", "expires_in": 3600 }
```

**Response `401`**
```json
{ "detail": "Invalid credentials" }
```

#### `GET /users/{user_id}`
Returns a single user record. Requires authentication.

**Path parameters**
- `user_id` (UUID) — the user's unique identifier

**Response `200`**
```json
{ "id": "uuid", "email": "string", "created_at": "datetime" }
```

**Response `404`**
```json
{ "detail": "User not found" }
```"""

    def _database_response(self) -> str:
        return """## Data models

### User
| Field | Type | Constraints |
|-------|------|-------------|
| id | UUID | Primary key, auto-generated |
| email | VARCHAR(255) | Unique, not null |
| password_hash | VARCHAR(255) | Not null |
| created_at | TIMESTAMP | Default: now() |
| updated_at | TIMESTAMP | Auto-updated on write |

### Relationships
- `User` has many `Session` records (one-to-many)
- `User` has many `AuditLog` entries (one-to-many)

### Migrations
Managed via Alembic. Apply all pending migrations with:
```bash
alembic upgrade head
```"""

    def _auth_response(self) -> str:
        return """## Authentication and security

### Mechanism
JWT-based authentication with RS256 signing. Access tokens expire
after 1 hour. Refresh tokens expire after 30 days and are stored
server-side in Redis for explicit revocation support.

### Token flow
1. Client posts credentials to `POST /auth/login`
2. Server validates against bcrypt hash in database
3. Server issues signed JWT: `user_id`, `email`, `iat`, `exp`
4. Client sends `Authorization: Bearer <token>` on every request
5. Middleware validates signature and expiry before routing

### Security measures
- Passwords hashed with bcrypt, cost factor 12
- Rate limiting on auth endpoints: 5 attempts per minute per IP
- All active tokens invalidated immediately on password change
- HTTPS enforced in all non-local environments"""

    def _deployment_response(self) -> str:
        return """## Deployment and infrastructure

### Requirements
- Python 3.11+
- PostgreSQL 15+
- Redis 7+

### Environment variables
| Variable | Description | Required |
|----------|-------------|----------|
| DATABASE_URL | PostgreSQL connection string | Yes |
| REDIS_URL | Redis connection string | Yes |
| SECRET_KEY | JWT signing secret | Yes |
| DEBUG | Enable debug mode | No (default: false) |

### Running locally
```bash
uv sync
cp .env.example .env
uv run alembic upgrade head
uv run python main.py
```

### Docker
```bash
docker compose up --build
```"""

    def _testing_response(self) -> str:
        return """## Testing

### Structure
```
tests/
├── unit/          # Pure logic, no I/O
├── integration/   # Real database, mocked external services
└── e2e/           # Full stack against a running test server
```

### Running tests
```bash
uv run pytest                     # all tests
uv run pytest tests/unit          # unit only
uv run pytest -v --tb=short       # verbose with short tracebacks
uv run pytest --cov=autodoc       # with coverage report
```

### Coverage
Minimum threshold enforced at 80%. Checked in CI on every pull request."""

    def _generic_response(self) -> str:
        return """## Documentation section

This component follows established Python best practices with clear
separation of concerns, typed interfaces, and comprehensive error handling.
Each public method is documented with its inputs, outputs, and side effects."""
