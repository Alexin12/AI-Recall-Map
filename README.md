# AI Recall Map

Split-stack learning app: FastAPI backend + Next.js frontend + Supabase (Postgres + Auth).

## Prerequisites

- The local Supabase stack running (Docker): `supabase start`.
  Postgres is exposed on `54322`, the API gateway on `54321`, Studio on `54323`.
- Apply the database migrations to the running stack: `supabase db reset`
  (or `supabase migration up`).

## Backend (port 8000)

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

Config is read from `backend/.env` (gitignored); local defaults match a stock
`supabase start`. Run the tests with `uv run pytest`.

## Frontend (port 3000)

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 and click **Run tracer bullet** — it signs a demo
user in via Supabase Auth, then POSTs and GETs a ping through the backend, which
enforces Row Level Security so each user only sees their own rows.
