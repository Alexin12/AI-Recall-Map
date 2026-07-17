-- Concept Map as a hierarchy tree (ADR-0007): each Concept hangs off one
-- primary parent; a second parent is display-only (slash label). The M1
-- relationship-edge model is gone. Idempotent so the file can be re-applied.

alter table public.concepts
  add column if not exists parent_concept_id uuid references public.concepts (id) on delete set null,
  add column if not exists second_parent_name text;

drop table if exists public.concept_relationships;
