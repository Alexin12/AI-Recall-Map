# Dashboard input, routed to Topics at the Concept level

The user pastes Material on the Global Home with no Topic chosen first — this replaces the M1 flow of creating a Topic and pasting inside it. Extraction routes each extracted Concept individually, so `concepts.topic_id` is the authoritative Topic assignment and `materials.topic_id` becomes nullable (a Material is a raw, possibly-unsorted input).

**Topics are big and user-owned; the model fills them, it does not invent them.** A Topic is a broad container (e.g. "AI Engineer", "Accounting") that grows a Concept Map tree beneath it. The model must not decide Topic granularity from a few pasted Concepts — from `pass parameter`, `query parameter`, `dependency injection` it would mint a narrow "FastAPI" Topic at the wrong altitude, and multiply such Topics without end as more Material arrives. So the router's job is: attribute each Concept to one of the user's **existing** Topics, and build the sub-tree inside it. Mid-level grouping nodes ("FastAPI", "Retrieval") live *inside* a Topic's tree, not as Topics.

Cold start (the user has no Topics yet): the model proposes a **few, deliberately high-level** Topics from the dump; the user confirms them, renames one with a click, or creates their own instead, then routing fills them. After setup the user can always rename a Topic, create new ones, and drag Concepts from one Topic to another (including moving them out of a Topic the model chose).

A Concept that matches no Topic and is not worth a Topic of its own is left **unclassified** — `concepts.topic_id IS NULL`, shown in an inbox. Orphans land here rather than spawning junk Topics; the user later drags them into a Topic, or promotes a cluster of them into a new one. This is why `topic_id` is nullable and why unclassified is a real, reachable state — not a dead branch.

**Status**: accepted

**Consequences**:
- `materials.topic_id` and `concepts.topic_id` become nullable; every query that assumed a Concept always has a Topic (`concept_map`, `list_concepts`) must tolerate NULL.
- In V1 a Concept belongs to exactly one Topic (the highest-relevance match); many-to-many is deferred.
- The model never auto-commits a new Topic — high-level Topic proposals are always confirmed by the user; leftovers fall to the inbox, not to new Topics.
- The old per-Topic paste path is removed. Risk accepted: when the user already knows a Material's Topic, forced routing is slower; revisit adding the direct path back if that friction proves real.
