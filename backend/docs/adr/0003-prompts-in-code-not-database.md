# Prompts live in code, not a database

Extraction and grading prompts are Python constants, versioned by git — not rows in a database with an admin UI. A prompts table plus admin UI only pays off when non-engineers need to tune prompts frequently; that's not the case here, and code-versioned prompts get review, diffs, and rollback for free.

**Status**: accepted
