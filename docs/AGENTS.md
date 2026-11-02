## Learned User Preferences

- Prefer pydantic-settings (`config.py`) for environment/config over reading `os.environ` directly in app code.
- Work phase-by-phase from `docs/implementation.md`: plan first, wait for explicit approval, then implement; do not edit the attached plan file during implementation.
- Prefer professional git branching (topic/`feat` branches and clear commit messages); often wants step-by-step git guidance rather than silent repo surgery.
- Keep Cursor and VS Code IDE metadata out of git (ignore `.cursor` / `.vscode`).
- Prefer OpenRouter free models for chat/embeddings/evals; keep `config.py`, `.env`, and `.env.example` model IDs aligned.
- When merging phase branches, keep the current branch as source of truth except for the explicitly requested feature slice.

## Learned Workspace Facts

- Monorepo: `backend/` is Python FastAPI + SQLModel + Alembic managed with `uv`; `frontend/` is Next.js App Router + TypeScript + shadcn/ui managed with Bun.
- `docs/implementation.md` is the authoritative implementation guide; ADRs live under `docs/decisions/`; phase plans live under `docs/plan/` (copies also under `docs/`).
- Auth is Neon Managed Better Auth on the frontend (`@neondatabase/auth`) with FastAPI JWT verification via JWKS; PropelAuth was removed after Phase 1.
- Application `users` are profiles keyed by JWT `sub`; credentials/sessions stay in Neon Auth.
- Schema changes go through Alembic only (no runtime `create_all`); database target is Neon Postgres.
- Object storage uses an `ObjectStorage` protocol with boto3/S3 in app code and `FakeObjectStorage` in tests.
- Uploads: max 25 MiB and 6 files; allowed types `.md`/`.markdown`/`.txt`/`.pdf`/`.csv`/`.docx`; ingestion runs via Inngest (`document/uploaded.v1`) with LangChain loaders/chunking and OpenRouter embeddings into Pinecone.
- Backend includes Sentry (DSN-gated) and Inngest served at `/api/inngest`.
- Chat/RAG uses Inngest `chat/message.requested.v1` (embed → Pinecone search → LLM) with UI progress stages; default chat/eval model IDs are OpenRouter free models.
- Phase 4 caching uses optional Redis (`REDIS_URL`, often Upstash) and fails open when unset; evals live under `backend/evals` and `backend/src/evals`.
