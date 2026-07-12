# Recall Map — Plan v1

Rewritten after resolving all contradictions between the old Plan_v1 and Grill_Questions_v1 (interview completed 2026-07-11). Technical Architecture updated 2026-07-11 after a follow-up architecture discussion — see the note there.

## Goal

Recall Map turns pasted learning material into active recall questions, concept explanations, and concept relationships, then brings them back when review is due.

It is for self-directed learners who learn something but have no reliable way to recall, test, and reconnect it later.

It is NOT a general notes app, a chatbot over documents, or a file storage app.

## Glossary (canonical terms)

Use these exact words in code, database, UI, and docs. No aliases (drop "collection", "mind map", "big concept").

| Term | Meaning |
|---|---|
| Goal | The user's learning goal (e.g. "become an AI engineer within a year"). Set once, editable. Guides concept importance. |
| Topic | A broad subject the user is learning (e.g. FastAPI, RAG). Groups materials and concepts. Has its own page and concept map. |
| Material | One original source (pasted text in V1) inside a Topic. |
| Concept | One idea extracted from a Material. Carries its source snippet. |
| Question | One way to test a Concept (flashcard or written explanation). |
| Review | One review attempt: user answer + AI verdict + feedback + timestamp. |
| Concept Map | Visual graph of Concepts and their relationships inside a Topic. |

## Resolved Decisions

### Input (V1)
- Pasted text only, with a clear size limit.
- Markdown and PDF come after the review loop is proven. No Word, Google Docs, Excel, or image OCR.
- Material text is stored in a Postgres text column (no Supabase Storage until file uploads exist).

### Extraction and concept selection
- AI extracts (not summarizes) structured Concepts, Questions, relationships, and source snippets via Structured Outputs.
- The LLM uses the user's Goal to mark each Concept: irrelevant to goal, supporting, or core.
- After extraction the user sees a confirmation screen: approve / edit / delete each Concept, and toggle which ones enter the review schedule (core are pre-checked).
- Confirmed core Concepts enter the review schedule. Supporting Concepts stay browsable in the Topic but are never due.
- AI confidence is saved; model output is never trusted blindly.

### Review loop (the heart of the product)
- Two modes in V1, user picks: flashcard and written explanation (Feynman-style).
- Grading: zero RAG. The grading prompt contains the Concept explanation + its stored source snippet + the user's answer. No retrieval, no OpenAI File Search.
- AI returns a four-tier verdict: fail / partial / pass / strong, plus feedback: correct points, missing points, misconception warnings, and next review date.
- The verdict is guidance, not truth: the user can override it with one click. Scheduling uses the final verdict.
- Spaced repetition uses simple performance rules only:
  - fail → due again today
  - partial → tomorrow
  - pass → 3 days
  - strong → 7 days
- The hour-level forgetting-curve schedule (1h / 9h / ...) is deferred until push or email reminders exist.
- Mastery is shown as three states only: weak / learning / strong. No fake percentages in V1.
- All answers and AI feedback are stored per Review attempt.

### Reminders
- V1: in-app due list only. Email later. No browser notifications.

## UI (two layers)

### Layer 1 — Global home (first screen after sign-in)
- Today's due queue with a "start review" button.
- Mastery squares: red (failed last time) / blue (normal pass) / green (strong pass).
- Next-5-days review plan (how many red/blue/green due each day).
- Recently learned Concepts list (replaces the old yesterday/last-week time tabs, which are deferred to V2).
- Topic list with per-Topic concept counts and due counts.

### Layer 2 — Topic page
- Mastery overview for the Topic.
- Read-only Concept Map (auto-layout, React Flow): nodes + relationship edges, click a node to open its Concept detail. No dragging/editing in V1.
- Concept list and a "review this Topic" button.

### Concept detail page
- Name, one-line explanation, analogy, mastery state, due state, source link, relationships, questions, review history.
- Reachable by clicking a Concept anywhere: home, flashcard, map.

### Review flow
- A flow page (not a dashboard): question → user answers by typing → AI verdict + feedback → user may override → next question.

### Avoid
- Long AI summaries, walls of text, too many metrics.

## Technical Architecture

- **Split stack: Next.js thin frontend + FastAPI backend.** Chosen over a single Next.js app because the developer reads and maintains Python only, not TypeScript — all core logic must stay in a language they can actually verify, not just prompt an agent to write blindly.
- Next.js owns UI rendering and calls the FastAPI backend over HTTP (JSON). It holds no business logic — no extraction, grading, or scheduling code.
- FastAPI owns everything that matters: extraction, grading, scheduling, and all database reads/writes. Request/response shapes are Pydantic models — the single source of truth for the API contract.
- Structured extraction output uses Pydantic models + the `instructor` library (or the OpenAI/Anthropic SDKs directly) — the Python-side equivalent of Vercel AI SDK's `generateObject`. Prompts live in code (Python files, versioned by git).
- Supabase Postgres with Row Level Security on all user data, accessed from FastAPI. Relationships stored as plain rows (no graph database).
- No background job queue in V1: extraction runs in-request, FastAPI streams progress back over the HTTP response. Add a queue only when PDF/large files arrive.
- No embeddings, no pgvector in V1. When cross-material search is needed later, use Supabase pgvector, queried from FastAPI (not OpenAI File Search — keeps data in one place, retrieval adds latency not speed).
- Duplicate concepts across Materials are allowed in V1; merging (combining knowledge from multiple materials into one Concept) is milestone 3.

### Deployment (two independent one-click deploys, chosen for a first-time deployer)
- Next.js → Vercel (push to deploy).
- FastAPI → Render or Railway (push to deploy, no Dockerfile needed).
- Separate `.env` per side for local dev (not committed); production keys entered directly in each platform's dashboard, not managed by hand.
- V1 accepts manual sync of the Pydantic/TypeScript contract — no codegen tooling yet. Revisit if the API surface outgrows what's easy to keep in sync by hand.

## Privacy

- User materials are private and used only to generate that user's study artifacts. Never used as public examples.
- Short AI-mistake warning in the UI; incorrect concepts are editable.
- V1 supports deleting Materials and generated study artifacts; full account deletion later.

## Milestones

### M1 — Core loop
- Set Goal, create Topic, paste text Material.
- Extraction → confirmation screen → core Concepts scheduled.
- Both review modes with basic AI grading (four-tier verdict + feedback, user override).
- Review attempts saved; simple scheduling rules applied.
- Read-only mini Concept Map on the Topic page (even one node counts).

### M2 — Dashboards
- Global home: due queue, mastery squares, 5-day plan, recent list, Topic list.
- Topic page: mastery overview per Topic.

### M3 — Depth
- Grading depth: point-by-point comparison against source, better misconception detection.
- Concept merging across Materials; fuller Concept Map for Topics with multiple Materials.

## Deferred (after real usage)

RAG / pgvector search, Markdown/PDF and all other file types, email reminders, time-tab review views (yesterday / last week), numeric mastery scores, forgetting-curve hour-level schedule, background jobs, Supabase Storage, mobile app, collaboration, public sharing, payments, advanced analytics.
