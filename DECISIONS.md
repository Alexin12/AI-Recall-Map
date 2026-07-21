# Decisions

> **What this file is.** The single index of load-bearing decisions for Recall Map: choices
> made between real alternatives that still constrain future work. Read it before proposing any
> architecture, library, stack, or product-behavior change. Requirements and user stories live
> in the PRD issue, not here; full trade-offs live in the linked `docs/adr/` entry, not here.
>
> **How to use it.**
> - Add a one-line entry the moment a decision is locked. Format: `YYYY-MM-DD (tag): Decision. Why (one clause). [link]`
> - **Active** holds only decisions still in force, newest milestone on top (M3 → M2 → V1).
> - The moment a decision is overturned — even just renamed — move the whole line to
>   **Historical / Superseded** with a note. Never leave a stale line in Active.
> - Prune once per Milestone: drop lines the code now fully embodies and that no longer guide a choice.
>
> **Agent rule** (mirrored in CLAUDE.md): before proposing any architecture, library, stack, or
> product-behavior change, read this file and respect its Active decisions and Hard Rules. Do not
> reopen a Historical decision without saying so explicitly.

## Active Decisions

### M3 — current milestone (source of truth: [issue #69](https://github.com/Alexin12/AI-Recall-Map/issues/69))

- 2026-07-20 (M3): The Concept Map is renamed **Concept Tree** and rendered as a radial mind-map (central Topic, top-level Concepts as the first ring, sub-Concepts as leaves). The ADR-0007 data model is unchanged — one primary parent per Concept, no user-drawn edges, no map editing. Why: the tree is the product's visual signature; only the rendering changed. [ADR-0007](backend/docs/adr/0007-concept-map-as-hierarchy-tree.md)
- 2026-07-20 (M3): Mastery State has four values — `never-reviewed` is distinct from `weak`. Why: "no reviews yet" is a different signal than "reviewed and weak", and the Memory Forest must show it.
- 2026-07-20 (M3): Global Home leads with the review-needed count, one `Start Review`, and the Memory Forest; Material paste/extraction move to a smaller side area. Why: an active-recall gym is review-first, not paste-first.
- 2026-07-20 (M3): The cross-Topic Review queue aggregates existing per-Concept due dates and never recomputes or regenerates a schedule. Why: starting a global Review must not silently reshuffle the plan.
- 2026-07-20 (M3): AI-enriched Concept format uses a fixed field template (keyword, analogy, technical explanation, optional code, optional core claim, source excerpt); each field is extracted when present and generated when absent — except code, which is extract-only and never fabricated — with generated fields marked "AI-supplemented". Why: teach in layers without inventing code or losing source grounding. [ADR-0008](backend/docs/adr/0008-ai-enriched-concept-format.md)
- 2026-07-20 (M3): Extraction progress shows truthful named stages plus per-Concept events, never a fake percentage or ETA. Why: the 15–20s wait must stay honest. (updates #28)
- 2026-07-20 (M3): `Where your concepts landed` is a temporary per-paste receipt that disappears after confirmation or navigation; the permanent Inbox owns only unclassified Concepts. Why: avoid two competing permanent Concept editors. ADR-0005 to be updated.
- 2026-07-20 (M3): Goal input is example-guided (five examples) with no model quality gate; clearing a Goal uses an inline "are you sure?" confirm plus Undo. Why: never block saving a Goal, never lose one by accident.
- 2026-07-20 (M3): Restrained palette (sand `#EADBC8`, olive `#7A8A63`, warm bg `#FAF7F0`, card `#FFFFFF`, deep olive `#556B2F`); mastery color lives primarily on Concept nodes; no large UI framework. Why: avoid a wall of brightly colored cards.
- 2026-07-20: Extraction and grading run on DeepSeek V4 Flash via OpenRouter. Why: latest cost/latency choice for these calls. [PR #68](https://github.com/Alexin12/AI-Recall-Map/pull/68)

### M2 — dashboards & routing redesign

- 2026-07-17 (M2): Material is pasted on Global Home with no Topic chosen; extraction routes each Concept individually into an existing Topic, and `topic_id` is nullable (unmatched Concepts fall to an Inbox). Why: Topics are big, user-owned containers the model fills, not invents. [ADR-0005](backend/docs/adr/0005-dashboard-input-concept-level-routing.md)
- 2026-07-17 (M2): Goal is a per-Topic attribute; relevance is scored in a second phase and auto-applied, overridable on the Topic page. Why: a learner runs parallel subjects that should not share one blended objective. [ADR-0006](backend/docs/adr/0006-goal-per-topic-two-phase-relevance.md)
- 2026-07-14 (M2): Frontend package manager is pnpm. Why: migrated from npm for faster, disk-efficient installs. [PR #66](https://github.com/Alexin12/AI-Recall-Map/pull/66)

### V1 — foundation & core loop

- 2026-07-11 (V1): Split stack — Next.js thin frontend + FastAPI backend. Why: core logic (extraction, grading, scheduling) must live in Python, the only language the developer can verify. [ADR-0001](docs/adr/0001-split-stack-nextjs-frontend-fastapi-backend.md)
- 2026-07-11 (V1): Recall Map is an active-recall gym, not a knowledge organizer. Why: the product makes the human do the retrieval; the moat is behavioral design, not model capability. [ADR-0002](docs/adr/0002-active-recall-gym-not-knowledge-organizer.md)
- 2026-07-11 (V1): Supabase Postgres with Row Level Security on all user data, accessed from FastAPI. Why: one datastore, per-user isolation enforced in the database.
- 2026-07-11 (V1): Concept relationships stored as plain Postgres rows, not a graph database. Why: V1 renders one Topic at a time; graph-native traversal buys nothing yet. [ADR-0002-be](backend/docs/adr/0002-plain-postgres-rows-not-graph-database.md)
- 2026-07-11 (V1): Prompts live in code as Python constants, versioned by git. Why: gets review, diffs, and rollback for free. [ADR-0003-be](backend/docs/adr/0003-prompts-in-code-not-database.md)
- 2026-07-11 (V1): No background job queue — extraction runs in-request and streams progress over the HTTP response. Why: pasted text is small enough; revisit when large files arrive. [ADR-0004-be](backend/docs/adr/0004-no-background-job-queue-in-v1.md)
- 2026-07-11 (V1): AI extracts (not summarizes) structured Concepts, Questions, and source snippets via Structured Outputs. Why: extraction, not summary, is the product's job.
- 2026-07-11 (V1): No RAG for grading — the grading prompt is Concept explanation + stored source snippet + user answer. Why: each Concept carries its own snippet; retrieval adds latency, not speed. [ADR-0001-be](backend/docs/adr/0001-no-rag-for-v1-grading.md)
- 2026-07-11 (V1): Two review modes — flashcard and written (Feynman) explanation — both grade from M1. Why: grading is the differentiation; it cannot wait.
- 2026-07-11 (V1): Grading returns a four-tier verdict (fail / partial / pass / strong) with feedback; the user can override in one click, and scheduling uses the final verdict. Why: the verdict is guidance, not truth.
- 2026-07-11 (V1): Spaced repetition uses simple performance rules only — fail=today, partial=tomorrow, pass=3d, strong=7d. Why: the hour-level forgetting curve needs push/email reminders that don't exist yet.
- 2026-07-11 (V1): Reminders are an in-app due list only. Why: email and browser notifications come later.

## Explicitly Not Doing

- 2026-07-20 (M3): No model-based Goal validation, quality score, or gibberish classifier. Why: quality judgment must not block saving a Goal.
- 2026-07-20 (M3): No gamification / withering mechanics, no question variation from past Reviews, no point-by-point grading gate. Why: out of scope for the Depth milestone.
- 2026-07-17 (M2): No user-drawn Concept edges, multi-parent graph, or map editing. Why: no gradable standard; one primary parent fixes the tree. [ADR-0007](backend/docs/adr/0007-concept-map-as-hierarchy-tree.md)
- 2026-07-11 (V1): No RAG / pgvector in V1. Why: grading needs no retrieval; add pgvector only when cross-Material search is real. [ADR-0001-be](backend/docs/adr/0001-no-rag-for-v1-grading.md)
- 2026-07-11 (V1): No graph database, no background job queue, no file ingestion — pasted text only. Why: none is justified by V1's volume or inputs.
- 2026-07-11 (V1): No numeric mastery percentages — mastery is a small set of named states only. Why: fake precision misleads.
- 2026-07-11 (V1): No Concept merging across Materials or cross-Topic interleaving yet. Why: duplicates are allowed in V1; merging is a later idea.

## Hard Rules

- Every list/dashboard view is served by one purpose-built Backend contract; never derive scheduling state by joining data in React, and never issue one request per Concept.
- Every new or changed contract ships Backend HTTP-seam tests; run Backend tests with `uv`, Frontend type-check + production build with `pnpm`.
- Any drag-and-drop interaction keeps an accessible keyboard / select fallback.
- All user-data tables enforce Row Level Security.
- Prompts stay in code (Python constants), versioned by git — never moved to a database.
- New extraction data or prompt behavior requires an ADR, not just a PRD line.

## Historical / Superseded

- 2026-07-17 → 2026-07-20 (M2 → M3): The user-facing name "Concept Map" was renamed "Concept Tree" (data model unchanged). Older docs may still say "Concept Map".
- 2026-07-11 → 2026-07-20 (V1 → M3): Mastery as three states (weak / learning / strong). Superseded by four states with `never-reviewed` added.
- 2026-07-11 → 2026-07-17 (V1 → M2): Global per-user Goal. Superseded by Goal-per-Topic. [ADR-0006](backend/docs/adr/0006-goal-per-topic-two-phase-relevance.md)
- 2026-07-11 → 2026-07-17 (V1 → M2): Concept Map as a relationship-edge graph (`concept_relationship` table). Superseded by the hierarchy tree (parent reference on each Concept). [ADR-0007](backend/docs/adr/0007-concept-map-as-hierarchy-tree.md)
- 2026-07-11 → 2026-07-17 (V1 → M2): Per-Topic paste flow (create a Topic, then paste inside it). Superseded by dashboard input with Concept-level routing. [ADR-0005](backend/docs/adr/0005-dashboard-input-concept-level-routing.md)
- 2026-07-11 (V1): OpenAI File Search for grading "speed". Rejected before build — retrieval adds latency; use pgvector if retrieval is ever needed.
- 2026-07 model churn: extraction/grading ran on Opus 4.8, then Sonnet 5, now DeepSeek V4 Flash via OpenRouter (current choice is in Active). [PR #68](https://github.com/Alexin12/AI-Recall-Map/pull/68)
