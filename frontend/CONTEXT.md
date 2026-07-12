# Frontend

Next.js UI for Recall Map. Renders the Backend's data and calls its HTTP API; holds no business logic, no extraction/grading/scheduling code of its own.

## Language

Domain terms (Goal, Topic, Material, Concept, Question, Review, Review Verdict, Mastery State, Concept Map) are owned by [Backend](../backend/CONTEXT.md) — this context uses them identically and never redefines them.

**Global Home**:
The first screen after sign-in: today's due queue, mastery squares, next-5-days review plan, recently learned Concepts, Topic list.
_Avoid_: dashboard, home page

**Topic Page**:
The second UI layer: a Topic's mastery overview and its read-only Concept Map.
_Avoid_: topic dashboard

**Review Flow**:
The review UI: a flow page (question → answer → verdict → next), not a dashboard.
_Avoid_: quiz page, test page

## Rules this context enforces

- No business logic in the frontend — every extraction, grading, or scheduling decision is a call to the Backend, per [the split-stack ADR](../docs/adr/0001-split-stack-nextjs-frontend-fastapi-backend.md).
