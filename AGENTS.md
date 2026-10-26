## Learned User Preferences

- Prefer Pydantic Settings in `backend/src/config.py` over raw `os.environ` for backend config and secrets
- Prefer `fastapi[standard]` with SQLModel for the backend stack
- Prefer in-memory storage for early CRUD until a database is explicitly requested

## Learned Workspace Facts

- `rag-basic` is a monorepo with `frontend/` (Next.js) and `backend/` (FastAPI managed with uv)
- Backend entrypoint is `backend/src/main.py`; API routes mount under `/api/v1` (health plus in-memory items CRUD)
- Backend uses `[tool.uv] package = false`; run from `backend/` with `uv run fastapi dev src/main.py`
- On this Windows machine, Application Control (os error 4551) can block uv-managed CPython; recreate the venv with the officially installed Python (currently pythoncore 3.15)
- Keep secrets in gitignored `backend/.env`; never hardcode DSNs or API keys in source
