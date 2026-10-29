# Phase 2 — Ingestion and Background Processing

**Goal:** Convert uploaded documents into authorized, retrievable vector chunks reliably so a document becomes `ready` only after its active generation is fully indexed.

**Architecture:** Keep Phase 1 upload/outbox contract. An Inngest function consumes `document/uploaded.v1`, runs durable steps that stage large artifacts in S3, uses **LangChain** for document loaders and chunking, embeds via **OpenRouter through LangChain**, upserts deterministic vectors to Pinecone, and persists `chunks` + job/document status in Postgres. Frontend polls document status every 3–5s.

**Tech stack:** FastAPI/Inngest/SQLModel/Alembic + LangChain loaders/text-splitters, OpenRouter embeddings via LangChain, Pinecone via `langchain-pinecone` behind protocols. Fake embedding + vector-store providers for unit tests.

## Locked decisions

- **Event name:** Keep `document/uploaded.v1`.
- **Loaders / chunking:** LangChain SDK (community loaders + text splitters). Types: `.md` / `.txt` / `.pdf` / `.csv` / `.docx` only. No OCR/HTML.
- **Models:** OpenRouter via LangChain for embeddings (default `openai/text-embedding-3-small`, 1536-d). ChatOpenRouter is Phase 3.
- **Guide deviation:** Supersedes local `BAAI/bge-small-en-v1.5`; see `docs/decisions/` ADR.
- **Vector IDs:** `{document_id}:{generation}:{chunk_index}`.
- **Schema:** Add `chunks` + `ingestion_batches`.
- **Cache:** No Redis; bump `corpus_version` only.
- **Out of Phase 2:** Chat/retrieval/citations, local sentence-transformers, Playwright E2E.

See the approved Cursor plan for full workstreams, DoD, and file lists.
