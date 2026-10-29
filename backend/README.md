# Backend (`rag-basic`)

FastAPI + SQLModel + Alembic application for the RAG system.

## Prerequisites

- Python 3.13+ (see `.python-version`)
- [uv](https://docs.astral.sh/uv/)
- Isolated Neon Postgres development branch/project with **Neon Auth enabled**
- Private Neon Object Storage bucket
- Optional: [Inngest Dev Server](https://www.inngest.com/docs/dev-server), Redis, Sentry

## Setup

```bash
cd backend
cp .env.example .env
# Fill NEON_AUTH_BASE_URL, DATABASE_URL, DATABASE_URL_POOLED, AWS_* / S3_BUCKET_DOCUMENTS
uv sync --group dev
uv run alembic upgrade head
uv run fastapi dev src/main.py
```

Health:

- `GET /api/v1/health/live` — process up
- `GET /api/v1/health/ready` — database reachable (no provider details leaked)

Auth: FastAPI accepts Bearer JWTs from Neon Managed Better Auth (`authClient.token()`). JWKS at `{NEON_AUTH_BASE_URL}/.well-known/jwks.json`.

## Lint and tests

```bash
uv run ruff check .
uv run ruff format .
uv run pytest
```

`ENVIRONMENT=test` uses `JWT_TEST_SECRET` (HS256) and an in-memory FakeObjectStorage.

## Uploads (Phase 1)

- `POST /api/v1/uploads/init`
- `POST /api/v1/documents/{id}/complete` → `queued` + job + outbox
- `GET /api/v1/documents`, download, delete
- Allowed types: `.md`, `.markdown`, `.txt`, `.pdf`, `.csv`, `.docx`

## Inngest (smoke)

```bash
npx --yes inngest-cli@latest dev -u http://127.0.0.1:8000/api/inngest
```

## Embeddings (later phases)

Default: **`BAAI/bge-small-en-v1.5`** (local, 384-d).
