-- Dashboard input + Concept-level routing (ADR-0005): a Material is a raw,
-- possibly-unsorted input, and a Concept with NULL topic_id is unclassified
-- (the inbox). No separate flag, no system "Inbox" Topic.
-- All statements are idempotent so the file can be re-applied.

alter table public.materials
  alter column topic_id drop not null;

alter table public.concepts
  alter column topic_id drop not null;
