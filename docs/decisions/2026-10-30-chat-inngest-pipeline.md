# ADR: Chat RAG stages via Inngest

## Status

Accepted (overrides Phase 3 “request-path only” for the RAG pipeline).

## Context

Interactive chat originally embedded, retrieved, and streamed generation entirely in the FastAPI request. Users asked for Inngest-backed stages (embed → search → generate) with visible progress in the UI.

## Decision

- `POST /api/v1/chat` creates user/assistant messages, enqueues `chat/message.requested.v1`, and returns an SSE bridge that polls the assistant message.
- Inngest function `chat-message-requested` runs durable steps: embed+search, then generate (flushing partial `content` for the bridge).
- Stage labels live in `messages.retrieval_config.stage` / `stage_label`.
- `ENVIRONMENT=test` (or injected FakeLLM) runs the same pipeline inline so unit tests do not need the Inngest dev server.

## Consequences

Chat answers depend on Inngest in development/production. Ingestion and other jobs are unchanged. The SSE protocol for the AI SDK UI remains the same.
