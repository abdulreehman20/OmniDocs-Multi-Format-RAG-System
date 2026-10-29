## Learned User Preferences

- Prefer pydantic-settings (`config.py`) for environment/config over reading `os.environ` directly in app code.
- Work phase-by-phase from `docs/implementation.md`: plan first, wait for explicit approval, then implement; do not edit the attached plan file during implementation.
- Prefer professional git branching (topic/`feat` branches and clear commit messages); often wants step-by-step git guidance rather than silent repo surgery.
- Keep Cursor and VS Code IDE metadata out of git (ignore `.cursor` / `.vscode`).

## Learned Workspace Facts

- Monorepo: `backend/` is Python FastAPI + SQLModel + Alembic managed with `uv`; `frontend/` is Next.js App Router + TypeScript + shadcn/ui managed with Bun.
- `docs/implementation.md` is the authoritative implementation guide; ADRs live under `docs/decisions/`.
- Auth is Neon Managed Better Auth on the frontend (`@neondatabase/auth`) with FastAPI JWT verification via JWKS; PropelAuth was removed after Phase 1.
- Application `users` are profiles keyed by JWT `sub`; credentials/sessions stay in Neon Auth.
- Schema changes go through Alembic only (no runtime `create_all`); database target is Neon Postgres.
- Object storage uses an `ObjectStorage` protocol with boto3/S3 in app code and `FakeObjectStorage` in tests.
- Phase 1 uploads: max 25 MiB and 6 files; allowed types `.md`/`.markdown`/`.txt`/`.pdf`/`.csv`/`.docx`; ingestion stays queued for Phase 2 via jobs/outbox.
- Backend includes Sentry (DSN-gated) and Inngest served at `/api/inngest`.
