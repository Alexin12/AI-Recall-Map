-- Concept relationships: plain Postgres rows, not a graph database (ADR-0002).
-- M1 renders them read-only on the Concept Map; nothing creates them via API yet.

create table if not exists public.concept_relationships (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null default auth.uid() references auth.users (id) on delete cascade,
  topic_id        uuid not null references public.topics (id) on delete cascade,
  from_concept_id uuid not null references public.concepts (id) on delete cascade,
  to_concept_id   uuid not null references public.concepts (id) on delete cascade,
  kind            text not null,
  created_at      timestamptz not null default now()
);

alter table public.concept_relationships enable row level security;

drop policy if exists concept_relationships_select_own on public.concept_relationships;
create policy concept_relationships_select_own on public.concept_relationships
  for select using (auth.uid() = user_id);

drop policy if exists concept_relationships_insert_own on public.concept_relationships;
create policy concept_relationships_insert_own on public.concept_relationships
  for insert with check (auth.uid() = user_id);

grant select, insert on public.concept_relationships to authenticated;
