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

Auth: FastAPI verifies Bearer JWTs from Neon Managed Better Auth (JWKS at `{NEON_AUTH_BASE_URL}/.well-known/jwks.json`).

Swagger-friendly Neon Auth proxy (forwards to Managed Auth; does not store passwords):

- `POST /api/v1/auth/sign-up` — body `{ name, email, password }` → `{ access_token, token_type, user }`
- `POST /api/v1/auth/sign-in` — body `{ email, password }` → same
- `GET /api/v1/auth/token` — uses session cookie from sign-in/up → fresh JWT
- `POST /api/v1/auth/sign-out` — clears session

In `/docs`: call sign-in → copy `access_token` → **Authorize** → Bearer → call protected APIs.

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

## Inngest (ingestion)

```bash
npx --yes inngest-cli@latest dev -u http://127.0.0.1:8000/api/inngest
```

Functions: `document/uploaded.v1` ingestion, `document/delete.requested.v1` cleanup, outbox reconcile (+ cron).

## Embeddings (Phase 2)

OpenRouter via LangChain. Default: **`openai/text-embedding-3-small`** (1536-d). Configure `OPENROUTER_API_KEY`, `EMBEDDING_MODEL_ID`, `EMBEDDING_DIMENSION`, and a matching Pinecone index (`PINECONE_API_KEY` + `PINECONE_INDEX_HOST` or `PINECONE_INDEX_NAME`).

## Chat (Phase 3)

- `POST /api/v1/chat` — SSE UI Message Stream (`x-vercel-ai-ui-message-stream: v1`)
- Conversations CRUD under `/api/v1/conversations`
- Citations: `GET /api/v1/citations/{id}`
- Configure `CHAT_MODEL_ID` (default free Nemotron via OpenRouter)

## Caching / evals / maintenance (Phase 4)

- Optional `REDIS_URL` — fail-open embedding + retrieval cache; answer cache off
- Tenant `users.corpus_version` bumps on ingest promote and document delete
- Eval CLI: `uv run python -m src.evals.run_dataset --max 5`
- Inngest maintenance: abandoned uploads, orphan storage/vectors; outbox reconcile cron

## Profile (Phase 5)

- `GET /api/v1/me`, `PATCH /api/v1/me` — display name + preferences JSON (no passwords)

## Migrations

```bash
uv run alembic upgrade head
```

Latest: Phase 3 chat tables, Phase 4 `users.corpus_version` + `eval_runs`.

## Recovery / ops

- Failed ingestions, eval runs, corpus versions: see [`docs/ops-queries.md`](../docs/ops-queries.md)
- Document delete is tombstone + Inngest cleanup (`document/delete.requested.v1`)
- Re-ingest: use document **Retry** when status is `failed`
- Redis/Sentry outages must not block upload or chat

## Manual end-to-end checklist

1. Sign up / sign in (frontend or `/api/v1/auth/sign-in`)
2. Upload 1–2 supported files → wait until `ready`
3. Chat with those docs selected → streamed answer + citations
4. Open a citation → authorized locator/excerpt
5. Delete a document → status `deleting`/`deleted`; chat cannot use it
