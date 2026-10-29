# Phase 3 — Retrieval, Streaming Chat, Citations and History

**Goal:** Users select ready documents, ask questions, receive streamed grounded answers with verifiable citations, and revisit conversation history—without Inngest for chat.

**Architecture:** FastAPI request path embeds the query with the same OpenRouter embedding model used at ingest, queries Pinecone in the server-derived `owner_id` namespace with ownership + active-generation (+ document) filters, hydrates chunk text/locators from Postgres, runs a LangChain generation chain via `ChatOpenRouter`, and streams SSE to Next.js using the Vercel AI SDK UI Message Stream protocol. Citations are validated against the retrieved set only.

**Tech stack:** LangChain + OpenRouter (embeddings + chat) + Pinecone; Neon Auth JWT; Next.js + Vercel AI SDK UI (`useChat` / `DefaultChatTransport`).

## Locked decisions

- **RAG stack:** LangChain retriever + generation; OpenRouter for embeddings and chat; Pinecone for vectors. No local BGE, no alternate vector DB.
- **Chat is request-path only** — never an Inngest job.
- **Same embedding model/dimension** as indexed chunks (`settings.embedding_model_id` / document metadata).
- **Namespace:** server-derived `owner_id`; client cannot pass unrestricted Pinecone namespace/filters.
- **Default chat model:** `nvidia/nemotron-3-ultra-550b-a55b:free` via `ChatOpenRouter` (`CHAT_MODEL_ID`).
- **Streaming protocol:** Vercel AI SDK UI Message Stream (`x-vercel-ai-ui-message-stream: v1`) with start / text-delta / finish / error / DONE.
- **Schema:** Add `conversations`, `messages`, `message_citations`, `prompt_versions` (chunks already exist from Phase 2).
- **Out of Phase 3:** Redis/answer cache, RAGAS/evals, hybrid/rerank/query-rewrite, Playwright E2E.

## Workstreams delivered

1. Schema + chat settings (`chat_model_id`, retrieval/history limits).
2. `VectorStore.query` + `backend/src/ai/rag/` (retrieval, prompts, generation, citations).
3. Conversations CRUD + streaming `/api/v1/chat`, regenerate, citation resolve.
4. Frontend chat UI with document multi-select, stream, citations, copy/regenerate.
5. Unit tests for authz, citation validation, abstention, and stream fakes.

## DoD

- Answer tokens stream on the FastAPI request path.
- Every shown citation resolves to an authorized retrieved chunk/locator.
- Foreign conversation/document/citation IDs return 403/404 without leakage.

## Manual verification (live)

1. Apply migration `c3d4e5f6a7b8`.
2. Ensure OpenRouter + Pinecone env are set; have 1–2 `ready` documents.
3. Open `/chat`, select docs, ask a question — tokens stream in UI.
4. Open a citation — locator/excerpt authorized.
5. Cancel mid-stream — assistant message ends `partial`/`failed`.
6. Regenerate — no duplicate user message.

See ADR `docs/decisions/2026-10-29-chat-openrouter-streaming.md`.
