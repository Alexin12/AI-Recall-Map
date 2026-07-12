# Context Map

## Contexts

- [Backend](./backend/CONTEXT.md) — FastAPI service; owns the domain model, extraction, grading, scheduling, and all database access
- [Frontend](./frontend/CONTEXT.md) — Next.js UI; renders the Backend's data, holds no business logic of its own

## Relationships

- **Frontend → Backend**: Frontend calls Backend over HTTP (JSON). Pydantic models on the Backend are the single source of truth for the request/response contract.
- **Backend → Frontend**: For extraction and grading, Backend streams progress back over the HTTP response; Frontend renders it live.
