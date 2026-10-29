# Phase 4 — Caching, Observability, Evaluation and Background Maintenance

**Goal:** Make the app efficient, observable, and measurable before public beta: fail-open Redis, correlatable Sentry traces, a versioned golden eval baseline (CLI/CI), and safe background cleanup—without breaking uploads, ingest, or chat when Redis/Sentry/evals fail.

**Architecture:** `Cache` protocol + Redis (fail-open) on embedding and retrieval paths; tenant `users.corpus_version` for invalidation; Sentry correlation IDs; `eval_runs` + RAGAS CLI; separate Inngest maintenance jobs; fixed outbox cron helper.

**Tech stack:** Redis client, existing Sentry, RAGAS (CLI/CI only), Inngest maintenance.

## Locked decisions

- Redis non-authoritative; fail-open.
- Embedding + retrieval cache; **answer cache off**.
- Tenant `users.corpus_version` bumped on promote + delete.
- Eval: golden JSON + CLI; **no** scheduled/online RAGAS in Phase 4.
- Out of scope: Settings UI, Playwright, hybrid retrieval, answer-cache enabled.

## Manual verification

1. `alembic upgrade head` (migration `d4e5f6a7b8c9`).
2. Optional Redis: set `REDIS_URL`, repeat the same chat query → retrieval/embed cache hit (no Pinecone/OpenRouter embed call on second hit).
3. Delete a ready doc → `users.corpus_version` increments; next retrieval misses old keys.
4. Force `/sentry-debug` (dev) → event includes `request_id` tag when DSN set.
5. `uv run python -m src.evals.run_dataset --max 5` → writes `eval_runs` with custom metrics.

See ADR `docs/decisions/2026-10-29-phase4-cache-evals.md` and `docs/ops-queries.md`.
