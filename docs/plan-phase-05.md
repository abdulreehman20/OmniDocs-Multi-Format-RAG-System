# Phase 5 — Finish UI and Integration Testing

**Goal:** Complete the user-facing application and verify end-to-end functionality so the full upload → ingest → cited-answer workflow works in a test environment, with no inert UI actions and no unsupported source options.

**Architecture:** Dashboard sidebar shell (New Chat, Documents, conversations, Settings); polished Documents/Chat against reference PNGs; `GET/PATCH /api/v1/me`; Playwright smoke; setup/recovery docs.

**Tech stack:** Next.js App Router, shadcn/ui, Bun, Playwright, react-markdown + sanitize, FastAPI `/me`.

## Locked decisions

- Stay within existing zinc/shadcn language; match PNGs as practical.
- Sidebar shell owns conversation list; chat panel is stream + composer.
- Supported uploads only: md/markdown/txt/pdf/csv/docx.
- Settings via `/me` + Neon Auth for account ops; no auth table recreation.
- Playwright smoke; live providers optional/manual for CI.
- Out of scope: payments, OCR/Sheets/Drive, hybrid RAG, answer-cache on.

## Manual verification

1. Landing copy (no “later phases”); sign-in/up CTAs work.
2. Sidebar: New Chat, Documents, conversations, Settings; mobile drawer.
3. Documents: search/filter/grid|list; upload cancel; ingest vs upload progress.
4. Chat via `?c=`: Markdown answers, duration, citations, copy/regenerate.
5. Settings: load/save `/me` display name + preference.
6. `bun run test:e2e` smoke (auth redirects); optional `E2E_EMAIL`/`E2E_PASSWORD`.

See ADR `docs/decisions/2026-10-29-phase5-playwright.md` and `docs/setup.md`.

