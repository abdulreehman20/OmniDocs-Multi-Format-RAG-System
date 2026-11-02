# OmniDocs — Multi-Format RAG System

<p align="center">
  <img src="https://img.shields.io/badge/Next.js-000000?style=for-the-badge&logo=nextdotjs&logoColor=white" alt="Next.js" />
  <img src="https://img.shields.io/badge/React-61DAFB?style=for-the-badge&logo=react&logoColor=black" alt="React" />
  <img src="https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white" alt="TypeScript" />
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL" />
</p>

<p align="center">
  <a href="https://skillicons.dev">
    <img src="https://skillicons.dev/icons?i=nextjs,react,ts,tailwind,python,fastapi,postgres,redis,aws,nodejs&perline=10" alt="Skill icons" />
  </a>
</p>

**Goal:** Build a secure, multi-user retrieval-augmented generation (RAG) application where people can upload documents, ask questions in natural language, and get **streamed, grounded answers with citations** tied back to the original sources.

OmniDocs is a full-stack document Q&A product: sign in, upload Markdown/PDF/CSV/Word/text files, watch ingestion complete, select ready documents, chat with streaming answers and a Source panel, revisit conversations, and operate the system with caching, observability, evaluation, and background maintenance.

---

## Features

- Account auth with Neon Managed Better Auth (JWT verified by the API)
- Direct-to-object-storage uploads (presigned S3-compatible URLs)
- Background ingestion: parse → chunk → embed → Pinecone index (Inngest)
- Multi-document chat with streaming answers and `[S1]`, `[S2]`, … citations
- Conversation history, copy / regenerate, document download & delete
- Fail-open Redis caching for embeddings and retrieval
- Request correlation IDs + Sentry for monitoring
- CLI golden-dataset evals (custom metrics + optional RAGAS)
- Background maintenance (outbox reconcile, abandoned uploads, orphan cleanup)

---

## Tech stack

### At a glance

<p align="center">
  <img src="https://img.shields.io/badge/Next.js-000000?style=flat-square&logo=nextdotjs&logoColor=white" alt="Next.js" />
  <img src="https://img.shields.io/badge/React-61DAFB?style=flat-square&logo=react&logoColor=black" alt="React" />
  <img src="https://img.shields.io/badge/TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white" alt="TypeScript" />
  <img src="https://img.shields.io/badge/Bun-000000?style=flat-square&logo=bun&logoColor=white" alt="Bun" />
  <img src="https://img.shields.io/badge/Tailwind_CSS-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white" alt="Tailwind CSS" />
  <img src="https://img.shields.io/badge/shadcn%2Fui-000000?style=flat-square&logo=shadcnui&logoColor=white" alt="shadcn/ui" />
  <img src="https://img.shields.io/badge/Vercel_AI_SDK-000000?style=flat-square&logo=vercel&logoColor=white" alt="Vercel AI SDK" />
  <img src="https://img.shields.io/badge/Playwright-2EAD33?style=flat-square&logo=playwright&logoColor=white" alt="Playwright" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/uv-DE5FE9?style=flat-square&logo=astral&logoColor=white" alt="uv" />
  <img src="https://img.shields.io/badge/SQLModel-E92063?style=flat-square&logo=python&logoColor=white" alt="SQLModel" />
  <img src="https://img.shields.io/badge/Alembic-D71E00?style=flat-square&logo=alembic&logoColor=white" alt="Alembic" />
  <img src="https://img.shields.io/badge/LangChain-1C3C3C?style=flat-square&logo=langchain&logoColor=white" alt="LangChain" />
  <img src="https://img.shields.io/badge/pytest-0A9EDC?style=flat-square&logo=pytest&logoColor=white" alt="pytest" />
  <img src="https://img.shields.io/badge/Ruff-D7FF64?style=flat-square&logo=ruff&logoColor=black" alt="Ruff" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Neon-00E699?style=flat-square&logo=neon&logoColor=black" alt="Neon" />
  <img src="https://img.shields.io/badge/PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/Amazon_S3-569A31?style=flat-square&logo=amazons3&logoColor=white" alt="S3" />
  <img src="https://img.shields.io/badge/Pinecone-000000?style=flat-square&logo=pinecone&logoColor=white" alt="Pinecone" />
  <img src="https://img.shields.io/badge/OpenRouter-6B57FF?style=flat-square&logo=openai&logoColor=white" alt="OpenRouter" />
  <img src="https://img.shields.io/badge/NVIDIA-76B900?style=flat-square&logo=nvidia&logoColor=white" alt="NVIDIA" />
  <img src="https://img.shields.io/badge/Redis-DC382D?style=flat-square&logo=redis&logoColor=white" alt="Redis" />
  <img src="https://img.shields.io/badge/Upstash-00E9A3?style=flat-square&logo=upstash&logoColor=black" alt="Upstash" />
  <img src="https://img.shields.io/badge/Inngest-5B5BD6?style=flat-square&logo=inngest&logoColor=white" alt="Inngest" />
  <img src="https://img.shields.io/badge/Sentry-362D59?style=flat-square&logo=sentry&logoColor=white" alt="Sentry" />
</p>

### Frontend

| | Area | Technology |
|---|------|------------|
| <img src="https://cdn.simpleicons.org/nextdotjs/000000" width="20" height="20" alt="Next.js" /> | Framework | **Next.js** (App Router) **16**, **React 19**, **TypeScript** |
| <img src="https://cdn.simpleicons.org/bun/000000" width="20" height="20" alt="Bun" /> | Package manager | **Bun** |
| <img src="https://cdn.simpleicons.org/tailwindcss/06B6D4" width="20" height="20" alt="Tailwind" /> | UI | **shadcn/ui**, **Tailwind CSS 4**, **Base UI**, **Lucide** icons |
| <img src="https://cdn.simpleicons.org/vercel/000000" width="20" height="20" alt="Vercel" /> | Chat / streaming | **Vercel AI SDK** (`ai`, `@ai-sdk/react`) |
| <img src="https://cdn.simpleicons.org/markdown/000000" width="20" height="20" alt="Markdown" /> | Markdown | **react-markdown**, **remark-gfm**, **rehype-sanitize** |
| <img src="https://cdn.simpleicons.org/neon/00E699" width="20" height="20" alt="Neon" /> | Auth client | **@neondatabase/auth** (Neon Managed Better Auth) |
| <img src="https://cdn.simpleicons.org/sentry/362D59" width="20" height="20" alt="Sentry" /> | Observability | **@sentry/nextjs** |
| <img src="https://cdn.simpleicons.org/biome/60A5FA" width="20" height="20" alt="Biome" /> | Lint / format | **Biome** |
| <img src="https://cdn.simpleicons.org/playwright/2EAD33" width="20" height="20" alt="Playwright" /> | E2E | **Playwright** |

### Backend

| | Area | Technology |
|---|------|------------|
| <img src="https://cdn.simpleicons.org/python/3776AB" width="20" height="20" alt="Python" /> | Runtime | **Python 3.13+**, package manager **uv** |
| <img src="https://cdn.simpleicons.org/fastapi/009688" width="20" height="20" alt="FastAPI" /> | API | **FastAPI**, **Uvicorn** (via FastAPI standard) |
| <img src="https://cdn.simpleicons.org/sqlalchemy/D71F00" width="20" height="20" alt="SQLAlchemy" /> | Data models / DB | **SQLModel**, **SQLAlchemy**, **Alembic**, **psycopg** |
| <img src="https://cdn.simpleicons.org/pydantic/E92063" width="20" height="20" alt="Pydantic" /> | Config | **pydantic-settings** |
| <img src="https://cdn.simpleicons.org/jsonwebtokens/000000" width="20" height="20" alt="JWT" /> | Auth API | **PyJWT** + JWKS (Neon Auth issuer) |
| <img src="https://cdn.simpleicons.org/amazons3/569A31" width="20" height="20" alt="S3" /> | Storage | **boto3** (Neon Object Storage / S3-compatible) |
| <img src="https://cdn.simpleicons.org/inngest/5B5BD6" width="20" height="20" alt="Inngest" /> | Jobs | **Inngest** (Python SDK, served at `/api/inngest`) |
| <img src="https://cdn.simpleicons.org/langchain/1C3C3C" width="20" height="20" alt="LangChain" /> | RAG / LLM glue | **LangChain**, **langchain-openrouter**, **langchain-text-splitters**, **langchain-community** |
| <img src="https://cdn.simpleicons.org/pinecone/000000" width="20" height="20" alt="Pinecone" /> | Vectors | **Pinecone** SDK |
| <img src="https://cdn.simpleicons.org/redis/DC382D" width="20" height="20" alt="Redis" /> | Cache | **Redis** (Upstash or any Redis; fail-open when unset) |
| <img src="https://cdn.simpleicons.org/pytest/0A9EDC" width="20" height="20" alt="pytest" /> | Evaluation | **RAGAS**, golden JSON datasets under `backend/evals/` |
| <img src="https://cdn.simpleicons.org/sentry/362D59" width="20" height="20" alt="Sentry" /> | Observability | **Sentry SDK** |
| <img src="https://cdn.simpleicons.org/adobeacrobatreader/EC1C24" width="20" height="20" alt="PDF" /> | Document parsers | **pypdf**, **python-docx**, CSV/text/Markdown loaders |
| <img src="https://cdn.simpleicons.org/openai/412991" width="20" height="20" alt="tiktoken" /> | Token estimate | **tiktoken** |
| <img src="https://cdn.simpleicons.org/pytest/0A9EDC" width="20" height="20" alt="pytest" /> | Tests | **pytest**, **pytest-asyncio**, **httpx** |
| <img src="https://cdn.simpleicons.org/ruff/D7FF64" width="20" height="20" alt="Ruff" /> | Lint | **Ruff** |

### Platforms & infrastructure

| | Service | Role |
|---|---------|------|
| <img src="https://cdn.simpleicons.org/neon/00E699" width="20" height="20" alt="Neon" /> | **Neon Postgres** | Authoritative app data (users, documents, jobs, chat, citations, evals) |
| <img src="https://cdn.simpleicons.org/neon/00E699" width="20" height="20" alt="Neon Auth" /> | **Neon Managed Better Auth** | Sign-up / sign-in / sessions |
| <img src="https://cdn.simpleicons.org/amazons3/569A31" width="20" height="20" alt="S3" /> | **Neon Object Storage** | Private document bytes (presigned upload/download) |
| <img src="https://cdn.simpleicons.org/pinecone/000000" width="20" height="20" alt="Pinecone" /> | **Pinecone** | Vector index (tenant-scoped namespaces / filters) |
| <img src="https://cdn.simpleicons.org/openai/412991" width="20" height="20" alt="OpenRouter" /> | **OpenRouter** | Embeddings + chat generation (and optional eval LLM) |
| <img src="https://cdn.simpleicons.org/upstash/00E9A3" width="20" height="20" alt="Upstash" /> | **Upstash Redis** (or any Redis) | Best-effort embedding & retrieval cache |
| <img src="https://cdn.simpleicons.org/inngest/5B5BD6" width="20" height="20" alt="Inngest" /> | **Inngest** | Durable ingestion + maintenance workflows |
| <img src="https://cdn.simpleicons.org/sentry/362D59" width="20" height="20" alt="Sentry" /> | **Sentry** | Errors and performance |

### Models (configurable via env)

Defaults used in this project (swap anytime via `.env`):

| | Purpose | Default model ID |
|---|---------|------------------|
| <img src="https://cdn.simpleicons.org/nvidia/76B900" width="20" height="20" alt="NVIDIA" /> | Chat / generation | `nvidia/nemotron-3.5-lightning:free` (OpenRouter) |
| <img src="https://cdn.simpleicons.org/nvidia/76B900" width="20" height="20" alt="NVIDIA" /> | Embeddings | `nvidia/nemotron-3.5-embed-1b:free` (2048-d) |
| <img src="https://cdn.simpleicons.org/nvidia/76B900" width="20" height="20" alt="NVIDIA" /> | Eval judge (CLI) | `nvidia/nemotron-3.5-lightning:free` |

Answer caching is available in config but **disabled by default** (`ANSWER_CACHE_ENABLED=false`).

### Supported uploads

`.md` / `.markdown`, `.txt`, `.pdf`, `.csv`, `.docx` — default limits **25 MiB** and **6 files** per selection (see `GET /api/v1/limits`).

---

## Repository layout

```text
rag-basic/
├── backend/          # FastAPI + Inngest + RAG pipeline
├── frontend/         # Next.js dashboard (documents, chat, settings)
├── docs/             # Implementation guide, plans, ADRs
└── README.md
```

---

## Prerequisites

- **Python 3.13+** and [uv](https://docs.astral.sh/uv/)
- **Bun** (frontend)
- **Node.js** (for Inngest CLI via `npx`)
- Accounts / resources:
  - Neon (Postgres + Auth + Object Storage)
  - OpenRouter API key
  - Pinecone index (dimension must match embedding model, e.g. **2048**)
  - Optional: Upstash Redis, Sentry, Inngest Cloud keys for non-dev

---

## Setup guide

### 1. Clone the repo

```bash
git clone https://github.com/abdulreehman20/OmniDocs-Multi-Format-RAG-System.git
cd OmniDocs-Multi-Format-RAG-System   # or your local folder name
```

### 2. Backend

```bash
cd backend
cp .env.example .env
```

Fill at least:

| Variable | Purpose |
|----------|---------|
| `NEON_AUTH_BASE_URL` | Neon Auth base URL (JWKS derived unless overridden) |
| `DATABASE_URL` | Neon Postgres connection string |
| `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_ENDPOINT_URL_S3`, `S3_BUCKET_DOCUMENTS` | Object storage |
| `OPENROUTER_API_KEY` | Embeddings + chat |
| `PINECONE_API_KEY`, `PINECONE_INDEX_HOST` or `PINECONE_INDEX_NAME`, `PINECONE_DENSE_FIELD` | Vector search |
| `CORS_ORIGINS` | e.g. `http://localhost:3000` |
| `REDIS_URL` | Optional — use `rediss://…` for Upstash TLS |
| `SENTRY_DSN` | Optional |
| `CHAT_MODEL_ID` / `EMBEDDING_MODEL_ID` | Optional overrides |

Install, migrate, run API:

```bash
uv sync --group dev
uv run python -m alembic upgrade head
uv run python -m fastapi dev src/main.py
```

> On some Windows setups, App Control blocks `fastapi.exe` / `alembic.exe`. Prefer `uv run python -m …` as above.

**Inngest Dev Server** (required for ingestion & chat retrieval jobs):

```bash
npx --yes inngest-cli@latest dev -u http://127.0.0.1:8000/api/inngest
```

API default: `http://127.0.0.1:8000`  
Inngest UI default: `http://localhost:8288`

### 3. Frontend

```bash
cd frontend
cp .env.example .env
```

Set Neon Auth public/client vars (per Neon Auth + `@neondatabase/auth` docs) and:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

```bash
bun install
bun dev
```

App default: `http://localhost:3000`

### 4. Smoke path

1. Sign up / sign in  
2. Upload a supported document → wait until status is **ready** (Inngest must be running)  
3. Open **Chat**, select the document, ask a question  
4. Confirm streamed answer + Source citations  
5. Optional: repeat the same question and check Redis (**Data Browser**) for `emb:` / `ret:` keys  

### 5. Evals (CLI)

```bash
cd backend
uv run python -m src.evals.run_dataset --max 5
# Live LLM path (uses OpenRouter):
uv run python -m src.evals.run_dataset --max 5 --llm
```

Results are stored in the `eval_runs` table (see `docs/ops-queries.md`).

### 6. Tests

```bash
# Backend
cd backend && uv run python -m pytest

# Frontend
cd frontend && bunx tsc --noEmit && bun run build

# Playwright (app running)
cd frontend && bun run test:e2e
```

---

## Architecture (short)

```text
Browser (Next.js + AI SDK)
    │  JWT
    ▼
FastAPI ──► Neon Postgres
    │         Neon Object Storage
    ├─► Inngest (ingest / maintenance)
    ├─► OpenRouter (embed + chat stream)
    ├─► Pinecone (retrieve)
    └─► Redis (optional cache)
```

- **Postgres** is source of truth for ownership and product state.  
- **Pinecone** holds derived vectors.  
- **Redis** is best-effort; the app keeps working if Redis is down.  
- Interactive chat generation streams on the **HTTP/SSE request path**; Inngest handles embed+search orchestration and heavy ingest work.

More detail: [`docs/implementation.md`](docs/implementation.md), [`docs/setup.md`](docs/setup.md), and ADRs under [`docs/decisions/`](docs/decisions/).

---

## Author

Built by **Abdul Reehman** ([abdulreehman20](https://github.com/abdulreehman20)).

---

## Want to build a system like this?

If you want a production-minded RAG product — multi-format ingestion, cited streaming chat, auth, caching, and ops hardening — **contact me** and let’s talk about your use case.

- GitHub: [github.com/abdulreehman20](https://github.com/abdulreehman20)  
- Email: abdulreehman20@gmail.com  
