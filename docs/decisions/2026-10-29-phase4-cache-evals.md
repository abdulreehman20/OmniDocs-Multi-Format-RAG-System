# ADR: Phase 4 Redis fail-open, answer-cache off, CLI-only RAGAS

## Status

Accepted for Phase 4+.

## Context

Phase 4 needs caching and evaluation without risking chat correctness or OpenRouter free-tier exhaustion.

## Decision

- Redis is best-effort; failures never block core paths.
- Answer caching remains disabled (`ANSWER_CACHE_ENABLED=false`) until conversational correctness is proven.
- RAGAS runs via CLI/CI only; no scheduled Inngest or online sampling in Phase 4.
- Tenant `users.corpus_version` invalidates retrieval cache keys without scanning Redis.

## Consequences

Operators must run evals manually or in CI. Interactive chat stays request-path and cache-optional.
