# ADR: Phase 5 Playwright smoke strategy

## Status

Accepted for Phase 5+.

## Context

The implementation guide asks for broad E2E coverage. Full live OpenRouter/Pinecone/Inngest in every CI run is costly and flaky.

## Decision

- Ship `@playwright/test` with a **smoke** suite that always covers public landing and auth redirects.
- Authenticated flows run only when `E2E_EMAIL` / `E2E_PASSWORD` are set.
- Live upload → chat → citation against real providers remains a **manual** checklist documented in READMEs.

## Consequences

CI can stay green without provider secrets. Operators run the full workflow locally before release.
