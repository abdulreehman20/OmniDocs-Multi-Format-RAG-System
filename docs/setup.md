# Local setup (Phases 0–5)

## Backend

```bash
cd backend
cp .env.example .env
# Required: NEON_AUTH_BASE_URL, DATABASE_URL, AWS_*/S3_BUCKET_DOCUMENTS
# Chat/ingest: OPENROUTER_API_KEY, PINECONE_*
# Optional: REDIS_URL, SENTRY_DSN, INNGEST_*
uv sync --group dev
uv run alembic upgrade head
uv run fastapi dev src/main.py
```

Inngest Dev Server:

```bash
npx --yes inngest-cli@latest dev -u http://127.0.0.1:8000/api/inngest
```

## Frontend

```bash
cd frontend
cp .env.example .env
# NEON_AUTH_*, NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
bun install
bun dev
```

## Supported file types

`.md`, `.markdown`, `.txt`, `.pdf`, `.csv`, `.docx` — max size and count from `GET /api/v1/limits`.

## Testing

```bash
# Backend
cd backend && uv run pytest

# Frontend typecheck / build
cd frontend && bunx tsc --noEmit && bun run build

# Playwright smoke (frontend running)
cd frontend && bun run test:e2e
```

## Recovery

See [ops-queries.md](ops-queries.md) and backend README “Recovery / ops”.
