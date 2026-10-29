# ADR: OpenRouter embeddings via LangChain

## Status

Accepted for Phase 2+.

## Context

`docs/implementation.md` defaults to local `BAAI/bge-small-en-v1.5` (384-d) for embeddings. The project chose LangChain for the ingestion pipeline and OpenRouter for model access.

## Decision

- Use LangChain document loaders and text splitters for parse/chunk.
- Embed via OpenRouter through LangChain (OpenAI-compatible embeddings client against OpenRouter when a dedicated class is unavailable).
- Default model: `openai/text-embedding-3-small` (1536 dimensions, cosine Pinecone index).
- Keep embeddings behind an `EmbeddingProvider` protocol; use fakes in unit tests.
- Chat/generation via `ChatOpenRouter` remains Phase 3; same `OPENROUTER_API_KEY`.

## Consequences

Pinecone indexes must be created with matching dimension. Changing embedding model requires a controlled re-index. CI must not call live OpenRouter.
