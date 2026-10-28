# ADR: Phase 0 foundation choices

## Status

Accepted.

## Decisions

1. **Schema:** Remove `SQLModel.metadata.create_all` from the FastAPI lifespan. Alembic is the only schema evolution path.
2. **API prefix:** Keep `/api/v1` (do not rename to bare `/v1` from the guide diagrams).
3. **OCR / HTML:** Excluded per final scope confirmation in `docs/implementation.md`. Scanned PDFs without extractable text fail clearly in Phase 2; no OCR module.
4. **Neon storage buckets / branches:** Operators create isolated Neon Postgres branches/projects and private Object Storage buckets outside the repo. Application settings carry bucket/endpoint names only.
5. **Default embeddings (docs only):** Prefer local `BAAI/bge-small-en-v1.5` (384-d). Do not use OpenRouter embedding endpoints as the default. Implementation starts in Phase 2.

## Consequences

Local setup requires running `uv run alembic upgrade head` against a configured database. Cloud resource provisioning remains a documented operator step.
