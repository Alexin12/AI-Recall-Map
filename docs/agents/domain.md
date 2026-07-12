# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

## Before exploring, read these

- **`CONTEXT-MAP.md`** at the repo root — points at one `CONTEXT.md` per context (frontend, backend). Read each one relevant to the topic.
- **`docs/adr/`** — system-wide decisions. Also check `frontend/docs/adr/` and `backend/docs/adr/` for context-scoped decisions.

`CONTEXT-MAP.md`, `backend/CONTEXT.md`, `frontend/CONTEXT.md`, and an initial set of ADRs (`docs/adr/`, `backend/docs/adr/`) were seeded from Plan_v1.md and Grill_Questions_v1.md on 2026-07-12, before any application code exists — treat them as authoritative over Plan_v1.md/Grill_Questions_v1.md going forward, since those two are the historical planning record, not the maintained reference. Keep extending `CONTEXT.md`/ADRs inline as new terms and decisions arise (per `/grill-with-docs`); no more bulk seeding.

## File structure (multi-context: Next.js frontend + FastAPI backend)

```
/
├── CONTEXT-MAP.md
├── docs/adr/                    ← system-wide decisions
├── frontend/                    ← Next.js, UI rendering only, no business logic
│   ├── CONTEXT.md
│   └── docs/adr/
└── backend/                     ← FastAPI, owns extraction/grading/scheduling/DB
    ├── CONTEXT.md
    └── docs/adr/
```

## Use the glossary's vocabulary

Canonical terms are defined in Plan_v1.md's glossary: Goal, Topic, Material, Concept, Question, Review, Concept Map. Use these exact words — no aliases ("collection", "mind map", "big concept" are retired).

## Flag ADR conflicts

If your output contradicts an existing ADR, surface it explicitly rather than silently overriding.
