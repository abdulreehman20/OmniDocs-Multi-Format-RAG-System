# Backend (`rag-basic`)

FastAPI + SQLModel + Alembic application for the RAG system.

## Prerequisites

- Python 3.13+ (see `.python-version`)
- [uv](https://docs.astral.sh/uv/)
- Isolated Neon Postgres development branch/project
- Private Neon Object Storage bucket (Phase 1+ upload flows)
- Optional: [Inngest Dev Server](https://www.inngest.com/docs/dev-server), Redis, Sentry

## Setup

```bash
cd backend
cp .env.example .env
# Fill PROPELAUTH_*, DATABASE_URL, DATABASE_URL_POOLED (required to start outside ENVIRONMENT=test)
uv sync --group dev
uv run alembic upgrade head
uv run fastapi dev src/main.py
```

Health:

- `GET /api/v1/health/live` — process up
- `GET /api/v1/health/ready` — database reachable (no provider details leaked)

## Lint and tests

```bash
uv run ruff check .
uv run ruff format .
uv run pytest
```

Unit tests set `ENVIRONMENT=test` so PropelAuth is not contacted over the network.

## Inngest (smoke)

1. Start the API (`fastapi dev src/main.py`).
2. In another terminal, start the Dev Server (example):

   ```bash
   npx --yes inngest-cli@latest dev -u http://127.0.0.1:8000/api/inngest
   ```

3. Confirm the `demo-hello` function (event `demo/hello`) appears and can be invoked.

Inngest is served from the FastAPI app via the official `inngest.fast_api.serve` integration (default path `/api/inngest`).

## Sentry

Set `SENTRY_DSN` for exception reporting. `GET /sentry-debug` deliberately raises only when `ENVIRONMENT` is `development` or `test`.

## Auth note

PropelAuth is temporary. Phase 1 migrates to Neon Managed Better Auth (see `docs/decisions/2026-10-28-auth-provider.md`).

## Embeddings (later phases)

Default embedding model: **`BAAI/bge-small-en-v1.5`** (384 dimensions, local). Chat generation uses OpenRouter; do not use OpenRouter as the default embedding provider.

## Operator: Neon isolation

Create separate development and production Neon branches/projects and private Object Storage buckets. Point `.env` at the development resources only. Never mix test and production buckets.
