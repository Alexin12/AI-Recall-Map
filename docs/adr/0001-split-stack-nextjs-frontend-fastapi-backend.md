# Split-stack: Next.js frontend + FastAPI backend

Chosen over a single Next.js app because the developer reads and writes Python only and has never deployed anything — core logic (extraction, grading, scheduling) needs to live in a language they can actually read, debug, and verify themselves, not just prompt an agent to write blindly. Next.js is kept only because the interactive, click-to-navigate Concept Map is a stated V1 differentiator that a pure-Python UI framework (Streamlit/Reflex) would make meaningfully harder to build well.

**Status**: accepted

**Consequences**: two deployments (Vercel + Render/Railway), two sets of env vars, and a Pydantic/TypeScript API contract synced by hand in V1. Accepted explicitly — the developer had no "simple single-deploy baseline" to give up either way, since they'd never deployed anything before this decision either.
