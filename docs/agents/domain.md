# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

## Before exploring, read these

- **`CONTEXT-MAP.md`** at the repo root — points at one `CONTEXT.md` per context (frontend, backend). Read each one relevant to the topic.
- **`docs/adr/`** — system-wide decisions. Also check `frontend/docs/adr/` and `backend/docs/adr/` for context-scoped decisions.

`CONTEXT-MAP.md`, `backend/CONTEXT.md`, `frontend/CONTEXT.md`, and the ADRs (`docs/adr/`, `backend/docs/adr/`) are the maintained reference for this repo's domain language and decisions. Keep extending `CONTEXT.md`/ADRs inline as new terms and decisions arise (per `/grill-with-docs`). The original planning files (`Plan_v1.md`, `Grill_Questions_v1.md`) have been retired; their locked decisions now live in `DECISIONS.md` at the repo root.

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

Canonical terms are defined in the per-context glossaries (`backend/CONTEXT.md`, `frontend/CONTEXT.md`). Use those exact words — no aliases ("collection", "mind map", "big concept" are retired).

## Flag ADR conflicts

If your output contradicts an existing ADR, surface it explicitly rather than silently overriding.
