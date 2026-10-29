# Phase 1 — Database, Auth, Storage and File-Upload UI

**Goal:** Authenticated users can sign up/in, reserve uploads via short-lived private S3 URLs, complete uploads into `queued` state with job+outbox rows, list/download/delete their own documents—and cannot access another user’s documents.

**Architecture:** Next.js uses `@neondatabase/auth` (Managed Better Auth). Browser sessions stay cookie-based; FastAPI accepts only Bearer JWTs from `authClient.token()`, verified against Neon JWKS. Application `users` is a profile keyed by JWT `sub`. Uploads go browser → Neon Object Storage (presigned PUT); FastAPI verifies HEAD size then commits document + `ingestion_jobs` + `outbox_events` in one transaction. Ingestion **processing** remains Phase 2 (documents stay `queued`).

## Locked decisions

- **Auth:** Remove PropelAuth. Implement Neon Managed Better Auth (`createNeonAuth`, `auth.handler()`, Next 16 `proxy.ts`).
- **JWT verification:** PyJWT + JWKS from `{NEON_AUTH_BASE_URL}/.well-known/jwks.json`.
- **OCR / `.doc`:** Not supported. Allowed: `.md`, `.markdown`, `.txt`, `.pdf`, `.csv`, `.docx` only.
- **Sample `items`:** Drop table and remove module.
- **API prefix:** Keep `/api/v1`.
- **Ingestion:** On complete → `queued` + job + outbox (`document/uploaded.v1`). Best-effort Inngest send; no parse/embed.
- **UI scope:** Auth + documents upload modal/list/download/delete. Chat/settings stubs behind auth.

See the approved Cursor plan for full file lists, DoD, and test commands.
