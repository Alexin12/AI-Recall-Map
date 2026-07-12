# Backend

FastAPI service owning Recall Map's domain model: extraction, grading, scheduling, and all database reads/writes. The single source of truth for what these words mean, in code, database, and UI.

## Language

**Goal**:
The user's stated learning goal (e.g. "become an AI engineer within a year"). Set once, editable, guides Concept importance.
_Avoid_: objective, target

**Topic**:
A broad subject the user is learning (e.g. FastAPI, RAG). Groups Materials and Concepts; has its own page and Concept Map.
_Avoid_: collection, subject area

**Material**:
One original source pasted into a Topic by the user. Stored as text in a Postgres column in V1.
_Avoid_: document, source, file

**Concept**:
One idea extracted from a Material, carrying its source snippet. Marked irrelevant / supporting / core relative to the user's Goal. Duplicate Concepts across Materials are allowed in V1 (merging comes in milestone 3).
_Avoid_: idea, note

**Question**:
One way to test a Concept — flashcard or written explanation.
_Avoid_: prompt, quiz item

**Review**:
One review attempt: the user's answer, the AI's Review Verdict, feedback, and a timestamp.
_Avoid_: attempt, session

**Review Verdict**:
The four-tier grading outcome for a Review: fail, partial, pass, strong. Guidance, not truth — the user can override it with one click; scheduling uses the final (possibly overridden) verdict.
_Avoid_: score, grade

**Mastery State**:
The three-state summary of a Concept's review history: weak, learning, strong. No numeric percentages in V1.
_Avoid_: mastery score, progress percentage

**Concept Map**:
A visual graph of Concepts and their relationship edges inside a Topic, used for navigation (click a node → Concept detail page).
_Avoid_: mind map, big concept

## Rules this context enforces

- No RAG / retrieval for grading — [ADR-0001](./docs/adr/0001-no-rag-for-v1-grading.md).
- Concept relationships are plain Postgres rows, not a graph database — [ADR-0002](./docs/adr/0002-plain-postgres-rows-not-graph-database.md).
- Prompts live in code, not a database table — [ADR-0003](./docs/adr/0003-prompts-in-code-not-database.md).
- No background job queue in V1 — [ADR-0004](./docs/adr/0004-no-background-job-queue-in-v1.md).
