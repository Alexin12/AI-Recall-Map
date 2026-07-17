# Frontend

Next.js UI for Recall Map. Renders the Backend's data and calls its HTTP API; holds no business logic, no extraction/grading/scheduling code of its own.

## Language

Domain terms (Goal, Topic, Material, Concept, Question, Review, Review Verdict, Mastery State, Concept Map) are owned by [Backend](../backend/CONTEXT.md) — this context uses them identically and never redefines them.

**Global Home**:
The first screen after sign-in and the single input point: a paste box for new Material, plus today's due queue, mastery squares, next-5-days review plan, recently learned Concepts, Topic list.
_Avoid_: dashboard, home page
_Milestone_: paste input = **M2**; due queue / mastery squares / 5-day plan / recently-learned list = **M3** (tags per [backend/CONTEXT.md](../backend/CONTEXT.md))

**Topic Page**:
The second UI layer: a Topic's mastery overview, its Concept Map (a hierarchy tree), and a Concept list with a relevance column the user can toggle (irrelevant / supporting / core) to override the AI's scheduling.
_Avoid_: topic dashboard
_Milestone_: relevance column + tree Concept Map = **M2**; full mastery overview = **M3**

**Confirmation Screen**:
Shown after a paste is extracted: the user edits the proposed Topic breakdown (rename, move Concepts between Topics, delete) and optionally sets a Goal per new Topic. Per-Concept scheduling is not decided here — relevance is scored automatically after confirm and overridden later on the Topic Page.
_Avoid_: review screen, quiz confirmation
_Milestone_: M2

**Review Flow**:
The review UI: a flow page (question → answer → verdict → next), not a dashboard.
_Avoid_: quiz page, test page
_Milestone_: M1

## Rules this context enforces

- No business logic in the frontend — every extraction, grading, or scheduling decision is a call to the Backend, per [the split-stack ADR](../docs/adr/0001-split-stack-nextjs-frontend-fastapi-backend.md).
