# Frontend (`rag-basic`)

Next.js App Router UI (Bun + TypeScript + shadcn/ui + Neon Managed Better Auth + Vercel AI SDK).

## Setup

```bash
cd frontend
cp .env.example .env
# Set NEON_AUTH_BASE_URL, NEON_AUTH_COOKIE_SECRET, NEXT_PUBLIC_API_BASE_URL
# Optional: NEXT_PUBLIC_SENTRY_DSN / SENTRY_DSN
bun install
bun dev
```

Open [http://localhost:3000](http://localhost:3000).

Protected routes: `/documents`, `/chat`, `/settings` (via `src/proxy.ts`).

## Features

- **Documents:** search/filter/list|grid, upload with cancel, ingest polling, download/delete/retry
- **Chat:** sidebar conversations (New Chat), ready-doc selection, streaming answers, Markdown, citations, copy/regenerate, duration
- **Settings:** profile via `GET/PATCH /api/v1/me` (Neon Auth owns credentials)

Supported uploads: `.md`, `.markdown`, `.txt`, `.pdf`, `.csv`, `.docx` only.

## Scripts

```bash
bun run lint
bun run build
bun run start
bun run test:e2e          # Playwright smoke (frontend must be running)
```

### Playwright

```bash
bunx playwright install chromium   # once
bun run dev                        # terminal 1
bun run test:e2e                   # terminal 2 — landing + auth redirects
```

Authenticated smoke (optional):

```bash
# Windows PowerShell
$env:E2E_EMAIL="you@example.com"; $env:E2E_PASSWORD="..."; bun run test:e2e
```

Full upload → ingest → cited chat against live OpenRouter/Pinecone is a **manual** checklist (see backend README recovery section). CI should not require live provider keys for the default smoke suite.
