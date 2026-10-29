# ADR: Chat via ChatOpenRouter + AI SDK UI stream

## Status

Accepted for Phase 3+.

## Context

Phase 3 requires request-path streaming grounded answers. Phase 2 already uses OpenRouter embeddings via LangChain.

## Decision

- Generation uses LangChain `ChatOpenRouter` with configurable `CHAT_MODEL_ID`.
- Streaming uses the Vercel AI SDK UI Message Stream protocol (`x-vercel-ai-ui-message-stream: v1`) from FastAPI to Next.js `useChat`.
- Retrieval uses the same OpenRouter embedding model as ingestion and Pinecone owner namespaces.

## Consequences

Frontend must install a matching `ai` package. Chat must not run as an Inngest job.
