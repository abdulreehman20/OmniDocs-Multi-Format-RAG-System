# ADR: Auth provider

## Status

Supersedes Phase 0 temporary PropelAuth decision. Accepted for Phase 1+.

## Context

`docs/implementation.md` requires Neon Managed Better Auth with JWT verification in FastAPI.

## Decision

- Frontend: `@neondatabase/auth` (`createNeonAuth`, `auth.handler()`, Next.js 16 `proxy.ts`).
- Backend: verify Bearer JWTs with PyJWT against `{NEON_AUTH_BASE_URL}/.well-known/jwks.json` (EdDSA/RS256/ES256).
- JWT `iss` / `aud` must be the Auth URL **origin** (e.g. `https://ep-xx.neonauth….neon.tech`), not the full `/neondb/auth` path — see Neon JWT plugin docs.
- `ENVIRONMENT=test` may use `JWT_TEST_SECRET` (HS256) so unit tests do not call Neon.
- Application `users` table is a profile keyed by JWT `sub`; credentials/sessions stay in Neon Auth schema. Upsert happens in FastAPI `get_current_user` on authenticated API calls (sign-in sync + dashboard layout).
- PropelAuth dependency and env vars are removed.

## Consequences

Operators must enable Neon Auth on the Neon branch and set `NEON_AUTH_BASE_URL` / cookie secret on the frontend.
