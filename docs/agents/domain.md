# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

## Before exploring, read these

- **`CONTEXT-MAP.md`** at the repo root — points at one `CONTEXT.md` per context (frontend, backend). Read each one relevant to the topic.
- **`docs/adr/`** — system-wide decisions. Also check `frontend/docs/adr/` and `backend/docs/adr/` for context-scoped decisions.

None of `CONTEXT-MAP.md`, `CONTEXT.md`, or `docs/adr/` exist yet — this repo is pre-code. Until they're generated, treat [Plan_v1.md](../../Plan_v1.md) and [Grill_Questions_v1.md](../../Grill_Questions_v1.md) as the working domain reference: Plan_v1.md holds the canonical glossary and resolved architecture decisions, Grill_Questions_v1.md holds the reasoning behind each decision. `CONTEXT.md`/ADRs get created lazily by `/grill-with-docs` once code exists to attach them to — don't flag their absence, don't suggest creating them upfront.

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
