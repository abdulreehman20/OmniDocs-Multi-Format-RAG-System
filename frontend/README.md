# Frontend (`rag-basic`)

Next.js App Router UI (Bun + TypeScript + shadcn/ui + Neon Managed Better Auth).

## Setup

```bash
cd frontend
cp .env.example .env
# Set NEON_AUTH_BASE_URL, NEON_AUTH_COOKIE_SECRET, NEXT_PUBLIC_API_BASE_URL
bun install
bun dev
```

Open [http://localhost:3000](http://localhost:3000).

Protected routes: `/documents`, `/chat`, `/settings` (via `src/proxy.ts`).

## Scripts

```bash
bun run lint
bun run build
bun run start
```
