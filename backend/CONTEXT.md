# Backend

FastAPI service owning Recall Map's domain model: extraction, grading, scheduling, and all database reads/writes. The single source of truth for what these words mean, in code, database, and UI.

## Language

_Each term carries a `_Milestone_:` tag — the milestone that realizes its **current** definition. M1 = shipped core loop; M2 = post-M1 redesign (this batch); M3 = dashboards; M4 = grading depth + Concept merging._

**Goal**:
An optional learning goal attached to a **Topic** (e.g. "become an AI engineer in 6 months"). Not a standalone entity — an attribute of a Topic, nullable and editable. Within its Topic it decides which Concepts are worth reviewing and when. A Topic with no Goal has no review plan.
_Avoid_: objective, target, global goal
_Milestone_: M2 (M1 had one global Goal; now per-Topic)

**Topic**:
A broad subject the user is learning (e.g. FastAPI, RAG). Groups Concepts; has its own page and Concept Map, and an optional Goal that drives its review plan. Concepts are routed into a Topic at extraction time.
_Avoid_: collection, subject area
_Milestone_: M1 (gains a Goal and becomes the routing target in M2)

**Material**:
One original source the user pastes on the Global Home. A raw, possibly-unsorted input — it no longer has to belong to a Topic (`topic_id` nullable); its extracted Concepts are routed to Topics individually. Stored as text in a Postgres column in V1.
_Avoid_: document, source, file
_Milestone_: M1 (`topic_id` becomes nullable / raw input in M2)

**Concept**:
One idea extracted from a Material, carrying its source snippet. Routed to exactly one Topic — `concepts.topic_id` is authoritative; if it matches no Topic it is **unclassified** (`topic_id` null) and sits in an inbox. Marked irrelevant / supporting / core relative to its Topic's Goal, or left null when the Topic has no Goal. Duplicate Concepts across Materials are allowed in V1 (merging comes later).
_Avoid_: idea, note
_Milestone_: M1 (Concept-level routing + unclassified state in M2)

**Question**:
One way to test a Concept — flashcard or written explanation.
_Avoid_: prompt, quiz item
_Milestone_: M1

**Review**:
One review attempt: the user's answer, the AI's Review Verdict, feedback, and a timestamp.
_Avoid_: attempt, session
_Milestone_: M1

**Review Verdict**:
The four-tier grading outcome for a Review: fail, partial, pass, strong. Guidance, not truth — the user can override it with one click; scheduling uses the final (possibly overridden) verdict.
_Avoid_: score, grade
_Milestone_: M1

**Mastery State**:
The four-state summary of a Concept's review history: never-reviewed, weak, learning, strong. A Concept with zero Reviews is never-reviewed, never weak. No numeric percentages.
_Avoid_: mastery score, progress percentage
_Milestone_: M3 (M1 had three states; never-reviewed split out of weak)

**Concept Map**:
A hierarchy tree of a Topic's Concepts — a big Concept expands into sub-Concepts — used for navigation (click a node → Concept detail page) and gap-finding. Not a free graph of relationship edges; each Concept has one primary parent.
_Avoid_: relationship graph, mind map, big concept
_Milestone_: M2 (M1 built it as a relationship graph; now a hierarchy tree)

## Rules this context enforces

- No RAG / retrieval for grading — [ADR-0001](./docs/adr/0001-no-rag-for-v1-grading.md).
- Concept relationships are plain Postgres rows, not a graph database — [ADR-0002](./docs/adr/0002-plain-postgres-rows-not-graph-database.md).
- Prompts live in code, not a database table — [ADR-0003](./docs/adr/0003-prompts-in-code-not-database.md).
- No background job queue in V1 — [ADR-0004](./docs/adr/0004-no-background-job-queue-in-v1.md).
- Input is pasted on the dashboard and routed to Topics at the Concept level — [ADR-0005](./docs/adr/0005-dashboard-input-concept-level-routing.md).
- Goal is an attribute of a Topic; relevance scored in a second phase — [ADR-0006](./docs/adr/0006-goal-per-topic-two-phase-relevance.md).
- The Concept Map is a hierarchy tree, not a relationship-edge graph — [ADR-0007](./docs/adr/0007-concept-map-as-hierarchy-tree.md).
