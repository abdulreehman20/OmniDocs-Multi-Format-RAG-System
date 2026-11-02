# Phase 0 — Audit, setup and compatibility

**Goal:** A new developer can start frontend/backend, migrate the DB with Alembic, run lint/tests, hit live/ready health, and see an Inngest Dev Server smoke function—without inventing Phase 1+ features.

**Architecture:** Keep `backend/` + `frontend/` as-is. Canonical Python package root remains `backend/src`. Fix import graph so models live under `src.db.models`. Serve Inngest from the FastAPI app. Auth stays on **PropelAuth for Phase 0 only**; Neon Managed Better Auth is deferred to Phase 1 (recorded in `docs/decisions/`).

**Tech stack (locked versions from lockfiles):** FastAPI 0.162, SQLModel 0.0.48, Alembic 1.20.1, Inngest 0.5.19, psycopg3, Sentry, uv, Bun/Next 16. Add **ruff**, **pytest**, **pytest-asyncio**, **httpx** as direct backend deps. Do not add Better Auth, Playwright, AI SDK, or document parsers in Phase 0.

## Locked decisions (from audit)

- **OCR / HTML / payments / Sheets / Drive / URL / camera:** out of scope (final guide confirmation).
- **Auth:** keep PropelAuth wiring for `/whoami` and `/items`; do not migrate to Better Auth in Phase 0.
- **API prefix:** keep `/api/v1` (do not rename to bare `/v1`).
- **Schema:** remove `SQLModel.metadata.create_all` from lifespan; Alembic is the only schema path.
- **Neon buckets / branches:** document operator steps + settings fields; do not attempt cloud provisioning from the repo.
- **Embeddings note in `backend/README.md`:** replace OpenRouter-embed suggestion with guide default `BAAI/bge-small-en-v1.5` (docs-only; no embedder implementation yet).

## 1. Phase objective and expected outcome

Make foundations reproducible and the broken scaffold bootable. Deliverables: fixed package layout, validated settings, `/health/live` + `/health/ready`, Ruff + pytest harness, fake-provider pattern, Inngest smoke function, expanded `.env.example` files, short setup docs, ADR for auth deferral. Audit report already delivered in chat (skip duplicate audit file).

## 2. Existing functionality, gaps, requirements

| Area | Today | Phase 0 action |
|---|---|---|
| Imports / boot | `main.py` missing `SQLModel` import; `from src.db import engine` with no `db/__init__.py`; `items`/`alembic` import nonexistent `src.models` | Fix package exports and import paths |
| Health | `GET /api/v1/health` only | Add live + ready |
| Alembic | Users/items migration exists; `create_all` still runs | Drop `create_all`; keep migration; fix `env.py` model imports |
| Auth | PropelAuth required in settings | Keep; document required env; health routes do not call auth |
| Tests / Ruff | Absent | Add |
| Inngest | Dep only | Client + serve + smoke fn |
| Storage / Redis | Empty stubs | Protocols + fakes only; no real Neon S3/Redis integration |
| Frontend | Boots; empty `.env.example`; stub dashboard pages | Fill `.env.example`; leave pages stubbed |

## 3. Exact files to create / modify / remove

### Create
- `backend/src/db/__init__.py` — export `engine`, `get_session`
- `backend/src/db/models/__init__.py` — export `User`, `Item`, …
- `backend/src/auth/__init__.py` — export `auth`
- `backend/src/inngest/client.py` — Inngest client from settings
- `backend/src/inngest/smoke.py` — no-provider hello function
- `backend/src/inngest/serve.py` — register functions with FastAPI
- `backend/src/providers/__init__.py` + `protocols.py` + `fakes.py` — `ObjectStorage` protocol + in-memory fake
- `backend/tests/unit/test_health.py`
- `backend/tests/unit/test_fake_storage.py`
- `backend/tests/conftest.py`
- `docs/decisions/2026-10-28-auth-provider.md`
- `docs/decisions/2026-10-28-phase-0-foundations.md`
- `docs/plan-phase-00.md` — this file

### Modify
- `backend/src/main.py` — fix imports; remove `create_all`; mount Inngest; gate `/sentry-debug`
- `backend/src/config.py` — env-distinct settings; optional Inngest/Redis/S3/Sentry; storage bucket names
- `backend/src/api/v1/health.py` — `/health/live`, `/health/ready`
- `backend/src/api/v1/items.py` — imports → `src.db.models`
- `backend/alembic/env.py` — import `src.db.models`
- `backend/src/db/s3_storage.py` — re-export protocol / stub note
- `backend/pyproject.toml` — ruff, pytest, pytest-asyncio, httpx
- `backend/.env.example` — complete keys (no secrets)
- `frontend/.env.example` — API base URL + Sentry public placeholders
- `backend/README.md` — setup commands; correct embedding default
- `frontend/README.md` — Bun start + env pointer

## 4–10. See approved Cursor plan

Full DoD, security, tests, env keys, and out-of-scope list are in the approved Phase 0 plan. Implementation follows that plan without expanding scope.
