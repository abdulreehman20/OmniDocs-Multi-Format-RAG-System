# ADR: Auth provider during Phase 0

## Status

Accepted for Phase 0; revisit in Phase 1.

## Context

`docs/implementation.md` requires Neon Managed Better Auth with JWT verification in FastAPI.
The repository currently uses PropelAuth (`propelauth-fastapi`) for `/whoami` and sample `/items` routes.

## Decision

- Keep PropelAuth for Phase 0 so existing protected sample routes remain wired.
- Do not implement Neon Managed Better Auth, Better Auth UI, or JWKS validation in Phase 0.
- When `ENVIRONMENT=test`, use an offline test auth stub so unit tests and app import do not call PropelAuth over the network.
- Phase 1 replaces PropelAuth with Neon Managed Better Auth and removes the temporary PropelAuth dependency.

## Consequences

- Production-like local runs still need valid `PROPELAUTH_*` credentials until Phase 1.
- `.env.example` documents PropelAuth as temporary.
