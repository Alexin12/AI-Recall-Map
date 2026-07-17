# Concept Map is a hierarchy tree, not a relationship graph

The Concept Map is a hierarchy — a big Concept expands into sub-Concepts (RAG → Retrieval → vector databases; Augmentation; Generation) — not the free graph of relationship edges built in M1. Two reasons. First, its job is to let the learner see what Concepts their notes contain and find gaps (e.g. compare their tree against an ideal skill list to spot what is still missing), which a clean, expandable tree serves well. Second, letting users draw their own edges has no gradable standard: a messy freeform graph cannot be judged by the model, and restricting them to one or two trivial links adds nothing they could not do in their head. Decomposition into a hierarchy is also what an LLM does reliably; recovering the full relationship web is not.

In V1 each Concept has one **primary** parent, which fixes where it hangs in the tree. A Concept that naturally has two parents is shown with a slash label ("retrieval / semantic search") for display only. Cross-links — a real many-to-many web — are deferred until there is proven demand.

**Status**: accepted

**Supersedes**: the M1 relationship-edge model (`concept_relationship` table, `concept_map.py`), replaced by a parent reference on Concepts. [ADR-0002](./0002-plain-postgres-rows-not-graph-database.md) (no graph database) still holds — a tree is still plain Postgres rows.

**Consequences**:
- The `concept_relationship` table and `concept_map.py` are reworked from edges to a parent reference on each Concept.
- Colouring the tree by Mastery State — the "memory tree" that greens as you review and withers if neglected — is a deferred, later-milestone idea: recorded here, not built now.
