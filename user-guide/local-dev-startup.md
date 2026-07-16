# Local Dev Startup Guide

How to start the whole app on your own machine, and how to use the Supabase
Studio dashboard to debug it. Written for someone new to the stack — every tool
is explained in one plain sentence before you're asked to run it.

---

## The mental model: three services, started in order

This app is three separate programs running at the same time, each on its own
port (a port is just a numbered door on your machine that one program listens
behind):

| Service            | What it is                                              | Port  | URL                     |
|--------------------|---------------------------------------------------------|-------|-------------------------|
| **Supabase**       | Your local database + login system (runs in Docker)     | 54321 / 54322 / 54323 | see table below |
| **Backend**        | FastAPI — all the real logic (extraction, grading, DB)  | 8000  | http://localhost:8000   |
| **Frontend**       | Next.js — the web pages you click on                    | 3000  | http://localhost:3000   |

**Start them in this order: Supabase → Backend → Frontend.** The backend can't
talk to a database that isn't up yet, and the frontend calls the backend. Each
one runs in its **own terminal window** and keeps running (don't close it).

---

## One-time setup (only needed the first time)

You need four command-line tools. Check what you already have by running each
line — if it prints a version, you're set:

```bash
docker --version   # Docker: runs the Supabase containers
supabase --version # Supabase CLI: only for CREATING the stack + running migrations
node --version     # Node.js: runs the frontend
uv --version       # uv: runs the Python backend
```

On this machine, `docker`, `node`, and `uv` are already installed. The
`supabase` CLI is **not on the PATH**, and that is fine for daily use — see the
next box for why.

### Do I even need the Supabase CLI? (important)

**"Create the containers" and "turn the containers on/off" are two different
things:**

- **Create** — done once, needs the CLI. `supabase start` reads
  `supabase/config.toml` and builds ~10 Docker containers (Postgres, Auth,
  Studio, the API gateway, …). This project's `supabase/` folder already exists,
  which proves this was already done here at some point.
- **Turn on/off** — everyday, needs only **Docker**. Once the containers exist
  they stay on your machine (their data lives in Docker volumes). Re-opening the
  ports later is just starting those containers again — Docker Desktop or
  `docker start` does it, no CLI required. This is what you've been doing.

> Analogy: the CLI is the **construction crew** that builds the rooms (cold
> store, front desk, control room). Once built, opening up each day is just
> **flipping the wall switch** (Docker) — you don't call the crew back.

**You only need the CLI installed for these jobs:**

- First-time creation on a new machine, or after the containers were deleted →
  `supabase start`.
- **Applying a database schema change (a migration)** → `supabase migration up`
  or `supabase db reset` (see [section 6](#6-changing-the-database-schema-migrations)).
- A clean `supabase stop`.

### Two ways to run the Supabase CLI

You don't have to install anything — you can run it **temporarily with `npx`**,
which is what this project has been doing.

**`npx`** is a command that ships with Node.js. It downloads a package, runs it
for that **one command**, and leaves nothing permanent on your PATH — like
ordering a chef in for a single dish instead of hiring one full-time. That's why
`npx supabase start` works but a bare `supabase` says *command not found*: `npx`
never installed a `supabase` command, it just borrowed the package once.

**Option A — run via `npx` (no install):** prefix every command with `npx`:

```bash
npx supabase --version      # check the version
npx supabase start          # create / start the stack
npx supabase db reset       # replay all migrations (wipes local data)
npx supabase migration up   # apply new migrations (keeps data)
npx supabase stop           # stop the stack
```

**Option B — install it once, then use the bare command:** install with Homebrew
(Homebrew is the macOS app-installer; the command is `brew`). After this,
`supabase ...` works with no `npx` prefix:

```bash
brew install supabase/tap/supabase
supabase --version
```

Both do the same thing — pick one. The commands elsewhere in this guide are
written as bare `supabase ...`; if you're on Option A, just read them as
`npx supabase ...`.

---

## 1. Start Supabase

Supabase runs inside Docker containers, so **Docker Desktop must be open and
running first** (look for the whale icon in your menu bar). If it isn't open,
launch the Docker Desktop app and wait until it says "Docker Desktop is
running".

### Daily case: reopen the ports (no CLI needed)

The containers already exist on your machine, so you just turn them back on:

- **Docker Desktop** → **Containers** tab → find the `supabase_*` group →
  click **Start (▶)**. Wait until each container shows "Running".

That's it — the ports below light up again, with all your previous data intact.

### First-time / rebuild case: create the stack (CLI needed)

Only if the containers don't exist yet (new machine, or they were deleted). From
the **project root** (`AI_Recall_Map/`, the folder that contains the `supabase/`
directory):

```bash
supabase start        # builds + starts the containers (first run: a few minutes)
supabase db reset     # loads the tables (goals, topics, …) into the fresh DB
```

`db reset` wipes the local database and re-applies every migration in
`supabase/migrations/` from scratch. **Only use it when the data is disposable**
— for schema changes on data you want to keep, see
[section 6](#6-changing-the-database-schema-migrations).

**Supabase ports (all on `127.0.0.1` / `localhost`):**

| Port    | What lives here                                                    |
|---------|--------------------------------------------------------------------|
| `54321` | API gateway — the backend and frontend talk to Supabase here       |
| `54322` | Postgres database — the actual data (the backend's `DATABASE_URL`) |
| `54323` | **Studio dashboard** — the web UI you debug with (see section 5)   |
| `54324` | Inbucket — a fake inbox that catches local signup/confirm emails   |

Open **http://localhost:54323** in your browser to see the Studio dashboard.

---

## 2. Start the backend

In a **new terminal**, from the project root:

```bash
cd backend
uv sync          # installs Python dependencies (first time / when they change)
uv run uvicorn app.main:app --reload --port 8000
```

- `uv sync` reads `backend/pyproject.toml` and installs the exact dependency
  versions into a local virtual environment.
- `uvicorn app.main:app` starts the FastAPI server. `app.main:app` means "the
  object named `app` inside `backend/app/main.py`". `--reload` auto-restarts the
  server every time you edit a Python file.

The backend reads its settings from `backend/.env` (keys: `DATABASE_URL`,
`SUPABASE_URL`, `SUPABASE_ANON_KEY`, `ANTHROPIC_API_KEY`). The local defaults
already match a stock `supabase start`, so you normally don't touch it.

Leave this terminal running. Backend is now at **http://localhost:8000**.

---

## 3. Start the frontend

In **another new terminal**, from the project root:

```bash
cd frontend
npm install      # installs JS dependencies (first time / when they change)
npm run dev
```

- `npm install` downloads the frontend's libraries into `node_modules/`.
- `npm run dev` starts the Next.js dev server with hot-reload.

The frontend reads `frontend/.env.local` (keys: `NEXT_PUBLIC_SUPABASE_URL`,
`NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_API_URL`). `NEXT_PUBLIC_API_URL`
must point at the backend (`http://localhost:8000`).

Open **http://localhost:3000** — the app is now fully running.

---

## 4. Quick "is everything up?" check

- Frontend loads at http://localhost:3000 without a connection error.
- Backend responds: open http://localhost:8000/docs — you should see the
  auto-generated FastAPI API docs page.
- Supabase Studio loads at http://localhost:54323.

If any one fails, fix that service before moving on — the ones after it depend
on it.

---

## 5. Debugging with the Supabase Studio dashboard

Studio (http://localhost:54323) is a web control panel over your local
database. These are the sections in the left sidebar, and what each is for **in
this project**. The ones you'll actually use for debugging are marked 🔴.

### 🔴 Table Editor
A spreadsheet-style view of your tables. Pick a table from the left list to see
its rows. This project's tables:

- `goals` — the user's single learning Goal.
- `topics` — subjects the user is learning.
- `materials` — pasted source text inside a Topic.
- `concepts` — ideas extracted from a Material (has `goal_relevance`,
  `scheduled`, `confidence` columns).
- `questions` — review questions generated for each Concept.
- `reviews` — every grading attempt (answer, verdict, feedback, timestamp).
- `concept_relationships` — edges between Concepts for the Concept Map.

**Use it to answer:** "Did extraction actually save Concepts?" "Is this Concept
`scheduled = true`?" "Was my Review row written?" Just open the table and look.

> Note on Row Level Security (RLS): the Table Editor shows rows as an admin, so
> you see *all* users' rows here. The app itself only ever shows a user their
> own rows — so if a row exists here but not in the app, suspect RLS or a
> wrong user id, not missing data.

### 🔴 SQL Editor
A box where you type SQL and run it against the database. Use it when the Table
Editor isn't enough — e.g. joining tables or filtering:

```sql
select c.name, c.goal_relevance, c.scheduled
from concepts c
where c.topic_id = '<paste-a-topic-id>';
```

Click **Run**. Great for checking exactly what the backend wrote.

### 🔴 Authentication
The list of login accounts (under **Users**). Each row is one signed-up user
with their `id` (a uuid) and email. **Use it to:** copy a user's `id` to filter
tables by owner, or confirm a signup actually created a user. Local signup
confirmation emails don't go to a real inbox — they land in **Inbucket** at
http://localhost:54324.

### 🔴 Logs
Live logs from the database, API, and auth services. **Use it when a request
fails and you don't know why** — e.g. a query the backend ran got rejected by an
RLS policy, or a constraint failed. Filter by service (Postgres / Auth / API) to
narrow it down.

### Database
Deeper database internals. The parts worth knowing:

- **Policies** — the RLS rules on each table (who can read/write which rows).
  Check here when a user "can't see their own data" or "sees nothing": a wrong
  or missing policy is the usual cause.
- **Roles**, **Extensions**, **Functions** — advanced; you rarely need these for
  day-to-day debugging.

### Storage
File uploads. **Not used in V1** (pasted text goes in a Postgres column, not
file storage) — you can ignore this tab for now.

### Realtime / Edge Functions / API Docs
- **Realtime** — live row-change subscriptions; not used in V1.
- **Edge Functions** — serverless functions; this project uses FastAPI instead,
  so unused.
- **API Docs** — auto-generated REST docs for your tables; occasionally handy as
  a reference, not needed for debugging.

---

## 6. Changing the database schema (migrations)

You'll hit this when you change the **data model** — for example, moving Goal
from *one-per-user* to *one-per-Topic*, which changes how the `goals` and
`topics` tables relate. In this project a schema change is **not** made by
editing the database by hand; it's a new **migration** file. A migration is one
timestamped `.sql` file describing the change, kept in `supabase/migrations/`,
so the exact same change can be replayed on any machine and stays in git.

**This is the one workflow that genuinely needs the Supabase CLI** (install it
per the One-time setup box if `supabase` isn't found).

### The workflow

1. **Create a new migration file** (this just makes an empty timestamped file
   for you to fill in):

   ```bash
   supabase migration new one_goal_per_topic
   ```

   It creates something like
   `supabase/migrations/20260716120000_one_goal_per_topic.sql`.

2. **Write the SQL change** inside that file. For a data-model change you use
   `alter table` / `create table` — e.g. attaching a Goal to a Topic instead of
   a user might look like:

   ```sql
   -- add a topic_id column so each Goal belongs to one Topic
   alter table public.goals add column topic_id uuid references public.topics(id);
   ```

   (Exact SQL depends on the final design — decide the data model first.)

3. **Apply it.** Two options, pick by whether you care about the current local
   data:

   | Command | What it does | Use when |
   |---------|--------------|----------|
   | `supabase migration up` | Applies **only new** migrations on top of the current DB. **Keeps existing data.** | Normal case — you want to keep your local rows. |
   | `supabase db reset` | Drops everything and replays **all** migrations from scratch. **Deletes all local data.** | You want a clean slate, or a migration is mid-edit and messy. |

4. **Update the code to match.** A schema change usually means the backend must
   change too — the SQLAlchemy/Pydantic models, the Goal/Topic modules, and any
   query that assumed one Goal per user. The database and the backend code have
   to agree, or requests will fail. Change both in the same step.

> ⚠️ Order-of-operations trap: don't hand-edit an **already-applied** migration
> file and expect the DB to update — the database only changes when a migration
> is *run*. Either add a **new** migration for the follow-up change, or
> `db reset` to replay the edited file from scratch (losing data).

---

## 7. Stopping everything

- **Frontend / Backend**: click their terminal and press `Ctrl + C`.
- **Supabase**:
  - Easiest — **Docker Desktop** → **Containers** → `supabase_*` group → **Stop
    (■)**. Keeps your data.
  - Or `supabase stop` (from the project root) if you have the CLI. Also keeps
    your data; add `--no-backup` only if you want to discard the local data too.

---

## 8. Common problems

| Symptom                                             | Likely cause & fix                                                                 |
|-----------------------------------------------------|------------------------------------------------------------------------------------|
| `supabase: command not found`                       | CLI not installed — run the `brew install` step in One-time setup.                 |
| `supabase start` hangs or errors about Docker       | Docker Desktop isn't running — open the app and wait, then retry.                   |
| Studio at :54323 won't load                         | Supabase isn't started, or `supabase start` didn't finish — check its terminal.    |
| Backend errors connecting to the database           | Supabase not up yet, or you skipped `supabase db reset` (tables don't exist).      |
| Frontend loads but every action fails               | Backend isn't running, or `NEXT_PUBLIC_API_URL` doesn't point at `:8000`.          |
| App shows no data but rows exist in Table Editor     | RLS / wrong user — check **Authentication → Users** and **Database → Policies**.   |
