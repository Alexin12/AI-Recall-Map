# PRD — M1: Core Loop

Source: `Plan_v1.md`, milestone M1 ("Core loop").

## Problem Statement

A self-directed learner pastes in learning material (an article, notes, docs) and wants to actually remember it later — not just have it stored somewhere. Today they either re-read the material (which doesn't build recall), or manually make flashcards (slow, and they don't know what's actually worth testing or when to review it again). They have no reliable, low-effort way to turn something they just learned into a small set of testable Concepts, get honest feedback on whether they actually know each one, and be told when to come back to it.

## Solution

The user sets a learning Goal once, creates a Topic, and pastes a Material into it. The system extracts a structured set of Concepts (with source snippets and a Goal-relevance tag: irrelevant / supporting / core) and Questions for each. The user reviews this extraction on a confirmation screen — approving, editing, deleting, and choosing which Concepts enter the review schedule. From then on, the user can run a Review (flashcard or written-explanation mode) against due Concepts; the AI grades each answer on a four-tier verdict (fail/partial/pass/strong) with feedback, the user can override the verdict, and the next-due date is set by a fixed rule table. Every attempt is saved. A minimal read-only Concept Map on the Topic page shows the Concepts extracted so far, even if there's only one.

M1 proves the core loop end-to-end (paste → extract → confirm → review → grade → reschedule) for one Topic, one Material at a time — it deliberately excludes dashboards, multi-Material merging, and file types beyond pasted text.

## User Stories

1. As a learner, I want to set a Goal once, so that the system can judge which Concepts in my Materials actually matter to me.
2. As a learner, I want to edit my Goal later, so that I can correct it as my learning direction shifts.
3. As a learner, I want to create a Topic, so that I have a place to group everything I'm learning about one subject.
4. As a learner, I want to paste text into a Topic as a Material, so that I can turn source content into study artifacts without manual note-taking.
5. As a learner, I want to be told when my pasted Material exceeds the size limit, so that I know to split it up before submitting.
6. As a learner, I want the system to extract Concepts from my Material automatically, so that I don't have to manually decide what's worth remembering.
7. As a learner, I want each extracted Concept to keep the exact source snippet it came from, so that I can verify the AI didn't make it up.
8. As a learner, I want each Concept tagged irrelevant/supporting/core relative to my Goal, so that I can focus review time on what matters.
9. As a learner, I want to see extraction progress while it's running, so that I know the system hasn't frozen on a longer paste.
10. As a learner, I want a confirmation screen after extraction, so that I stay in control of what enters my study set.
11. As a learner, I want to approve, edit, or delete any extracted Concept, so that I can fix AI mistakes before they become part of my review schedule.
12. As a learner, I want to toggle which Concepts enter the review schedule, so that I'm not forced to review things I don't care about.
13. As a learner, I want core Concepts pre-checked for scheduling, so that the common case requires no extra clicks.
14. As a learner, I want supporting Concepts to stay browsable but never due, so that I can reference them without review pressure.
15. As a learner, I want irrelevant Concepts excluded by default, so that off-Goal noise doesn't clutter my review queue.
16. As a learner, I want to see the AI's confidence on its own extraction, so that I know how much to double-check it.
17. As a learner, I want to choose between flashcard and written-explanation review modes, so that I can pick the study style that fits the Concept or my mood.
18. As a learner, I want to type a written answer to a Concept question, so that I can explain it in my own words (Feynman-style).
19. As a learner, I want the AI to grade my answer using only the Concept's own explanation and source snippet, so that grading is fast and doesn't depend on unrelated retrieval.
20. As a learner, I want a four-tier verdict (fail/partial/pass/strong) on each answer, so that I get more nuance than pass/fail.
21. As a learner, I want feedback that names what I got right, what I missed, and any misconceptions, so that I actually learn from a wrong or partial answer.
22. As a learner, I want to override the AI's verdict with one click, so that I'm not stuck with a wrong grade.
23. As a learner, I want the next-due date to follow simple, predictable rules (fail→today, partial→tomorrow, pass→3 days, strong→7 days), so that I understand why something is due when it is.
24. As a learner, I want the final (possibly overridden) verdict to be what drives scheduling, so that my own judgment always has the last word.
25. As a learner, I want every review attempt (my answer, the AI's verdict, feedback, timestamp) saved, so that I have a durable history of how I've done on each Concept.
26. As a learner, I want a read-only Concept Map on the Topic page, so that I can see how the Concepts I've learned relate to each other, even early on with just one node.
27. As a learner, I want to click a Concept node on the map to open its detail page, so that I can navigate from the big picture into specifics.
28. As a learner, I want a Concept detail page (name, explanation, mastery state, due state, source link, relationships, questions, review history), so that I have one place to see everything about a Concept.
29. As a learner, I want mastery shown as a simple weak/learning/strong state (no fake percentages), so that I get an honest, non-gameable signal.
30. As a developer maintaining this system, I want request/response shapes defined as Pydantic models, so that the frontend and backend have one unambiguous contract.
31. As a developer, I want extraction and grading to run in-request with streamed progress, so that V1 stays simple with no background job infrastructure.
32. As a developer, I want Row Level Security enforced on all user data in Postgres, so that one user's Materials and Concepts are never visible to another.

## Implementation Decisions

- **Split-stack boundary respected**: all extraction, grading, scheduling, and DB access logic lives in the FastAPI backend. The Next.js frontend only renders backend responses and calls the backend's HTTP API — no business logic added to the frontend in M1.
- **Domain modules to build in Backend**:
  - Goal module: create/edit the single user Goal.
  - Topic module: create Topic, list Topics.
  - Material module: submit pasted text Material into a Topic, enforcing a size limit (limit value to be set by the developer at implementation time, not user-configurable in V1).
  - Extraction module: given a Material, produces structured Concepts (name, explanation, source snippet, Goal-relevance tag, AI confidence) and Questions (flashcard + written-explanation prompts) via Structured Outputs (Pydantic models + `instructor` or direct SDK use). Runs in-request; streams progress over the HTTP response per [ADR-0004](../backend/docs/adr/0004-no-background-job-queue-in-v1.md).
  - Confirmation module: accepts the user's approve/edit/delete/toggle-schedule decisions on extracted Concepts; only confirmed, schedule-toggled Concepts become due-eligible.
  - Review module: serves the next due Question for a Concept in the chosen mode (flashcard or written), accepts the user's answer, calls the grading step, returns verdict + feedback, accepts an optional user override, and persists the Review row (answer, verdict, feedback, timestamp).
  - Grading module: builds the grading prompt strictly from the Concept's explanation + its stored source snippet + the user's answer (no retrieval), per [ADR-0001](../backend/docs/adr/0001-no-rag-for-v1-grading.md). Returns the four-tier verdict and structured feedback (correct points, missing points, misconception warnings).
  - Scheduler module: pure function/service mapping a final verdict to a next-due date using the fixed rule table (fail→+0d, partial→+1d, pass→+3d, strong→+7d). Also derives the Mastery State (weak/learning/strong) from a Concept's review history — exact derivation rule (e.g. based on most recent verdict, or last N verdicts) to be settled during implementation, but must stay a three-state, non-numeric result per Plan_v1.
  - Concept Map module: for M1, returns the set of Concepts and relationship rows for a Topic, structured for React Flow to render read-only (auto-layout, no drag/edit). Relationships are plain Postgres rows, not a graph database, per [ADR-0002](../backend/docs/adr/0002-plain-postgres-rows-not-graph-database.md).
- **Prompts live in code** (versioned Python files), not in the database, per [ADR-0003](../backend/docs/adr/0003-prompts-in-code-not-database.md).
- **Data model**: Concept rows carry a `goal_relevance` (irrelevant/supporting/core), a `scheduled` flag (set at confirmation), an AI `confidence` value, and a link to its source Material and snippet. Review rows carry `answer`, `verdict`, `feedback`, `timestamp`, and a `verdict_overridden` flag (or equivalent) to distinguish AI verdict from user-overridden verdict — the effective/final verdict is what scheduling reads.
- **Frontend pages for M1**: Topic creation/Material paste form; extraction confirmation screen (approve/edit/delete/toggle per Concept, showing confidence and Goal-relevance); Review Flow page (question → typed/flashcard answer → verdict + feedback → optional override → next question); Topic page with read-only Concept Map (React Flow) and Concept list; Concept detail page. Global home dashboard (due queue, mastery squares, 5-day plan) is explicitly M2, not built in M1 — M1 needs only enough of a due list to drive the Review Flow for a single Topic.
- **Auth/RLS**: all new tables get Row Level Security policies scoping rows to the owning user, consistent with Plan_v1's privacy requirements.
- **API contract sync**: Pydantic models define the contract; TypeScript types on the frontend are synced by hand in M1 (no codegen), per Plan_v1's deployment section.

## Testing Decisions

- Good tests here assert on external behavior — the HTTP request/response contract and the observable outcome of a domain operation (a Concept's schedule state, a Review row's stored verdict) — not on internal call sequences or private helper structure.
- **Two test seams, both in scope for M1**:
  1. **API route level**: tests drive the FastAPI endpoints (e.g. `POST` for Material submission, `POST` for confirmation decisions, `POST` for submitting a Review answer) via `TestClient`/`httpx` against a real or test-schema Postgres, asserting on the Pydantic response shape and resulting DB state. This is the highest seam available, since the frontend has no business logic of its own — the API's behavior is the product's behavior from the frontend's point of view.
  2. **Backend internal service/domain functions**: unit tests for the Extraction service, Grading service, and Scheduler directly (not only through the route), since these carry the product's core, easily-regressed logic (Goal-relevance classification, four-tier verdict → next-due mapping, mastery-state derivation). The Scheduler in particular is pure and cheap to test exhaustively (all four verdict cases, including the override path).
- **The one thing mocked**: the LLM call itself (the `instructor`/SDK call for extraction and for grading) is stubbed at both seams. Everything downstream of the model response — Concept persistence, confirmation-toggle logic, verdict-to-schedule mapping — runs as real code against real test data, so tests stay deterministic and don't consume tokens or depend on model behavior drift.
- No frontend automated tests are part of this PRD, since the frontend holds no business logic (per [frontend/CONTEXT.md](../frontend/CONTEXT.md)) — verify frontend pages manually against the running backend.
- No prior test suite exists yet in this repo (backend/frontend are still pre-code scaffolds) — this PRD establishes the first tests, so there's no existing prior-art pattern to match; follow standard FastAPI/pytest conventions (`TestClient`, fixtures for a per-test DB transaction/schema).

## Out of Scope

- Global home dashboard: due queue, mastery squares, next-5-day plan, recently-learned list, Topic list with counts (M2).
- Per-Topic mastery overview (M2).
- Point-by-point grading against source, deeper misconception detection (M3).
- Concept merging across multiple Materials in a Topic (M3).
- Markdown/PDF or any file type beyond pasted text.
- Email or browser-push reminders; only an in-app due list.
- Hour-level forgetting-curve scheduling (1h/9h/... ladder).
- Numeric mastery percentages.
- Background job queue / async extraction (deferred until PDF/large files arrive).
- RAG, embeddings, pgvector.
- Draggable/editable Concept Map (read-only only in M1).
- Account deletion (only Material/artifact deletion is in scope for V1 generally, but not called out as required specifically for M1).

## Further Notes

- The Material size limit is referenced in Plan_v1 ("a clear size limit") but no number is given — this needs to be picked during implementation (e.g. a character or token cap) rather than left open, since it directly bounds extraction latency under the no-queue, in-request architecture ([ADR-0004](../backend/docs/adr/0004-no-background-job-queue-in-v1.md)).
- Mastery State derivation rule (exactly which review(s) determine weak/learning/strong) is not fully specified in Plan_v1 beyond "three states only" — flagged in Implementation Decisions as a detail to settle during implementation, not a blocking open question for this PRD.
- This PRD assumes Goal, Topic, Material, Concept, Question, Review, Concept Map are used exactly as defined in [Plan_v1.md](../Plan_v1.md)'s glossary and [backend/CONTEXT.md](../backend/CONTEXT.md) — no new terms introduced.
