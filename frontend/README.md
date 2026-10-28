# Frontend (`rag-basic`)

Next.js App Router UI (Bun + TypeScript + shadcn/ui).

## Setup

```bash
cd frontend
cp .env.example .env
# Set NEXT_PUBLIC_API_BASE_URL (default http://localhost:8000)
bun install
bun dev
```

Open [http://localhost:3000](http://localhost:3000).

## Scripts

```bash
bun run lint
bun run build
bun run start
```

Auth UI (Neon Managed Better Auth) and RAG screens land in later phases. Dashboard routes under `src/app/(dashboard)/` are stubs until Phase 1+.
