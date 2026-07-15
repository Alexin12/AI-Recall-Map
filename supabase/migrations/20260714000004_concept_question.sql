-- Concept: one idea extracted from a Material; Question: one way to test a Concept.
-- Same RLS baseline as materials: users see and create only their own rows.

create table if not exists public.concepts (
  id             uuid primary key default gen_random_uuid(),
  user_id        uuid not null default auth.uid() references auth.users (id) on delete cascade,
  topic_id       uuid not null references public.topics (id) on delete cascade,
  material_id    uuid not null references public.materials (id) on delete cascade,
  name           text not null,
  explanation    text not null,
  source_snippet text not null,
  goal_relevance text not null check (goal_relevance in ('irrelevant', 'supporting', 'core')),
  confidence     double precision not null check (confidence >= 0 and confidence <= 1),
  created_at     timestamptz not null default now()
);

alter table public.concepts enable row level security;

drop policy if exists concepts_select_own on public.concepts;
create policy concepts_select_own on public.concepts
  for select using (auth.uid() = user_id);

drop policy if exists concepts_insert_own on public.concepts;
create policy concepts_insert_own on public.concepts
  for insert with check (auth.uid() = user_id);

grant select, insert on public.concepts to authenticated;

create table if not exists public.questions (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null default auth.uid() references auth.users (id) on delete cascade,
  concept_id uuid not null references public.concepts (id) on delete cascade,
  kind       text not null check (kind in ('flashcard', 'written')),
  prompt     text not null,
  created_at timestamptz not null default now()
);

alter table public.questions enable row level security;

drop policy if exists questions_select_own on public.questions;
create policy questions_select_own on public.questions
  for select using (auth.uid() = user_id);

drop policy if exists questions_insert_own on public.questions;
create policy questions_insert_own on public.questions
  for insert with check (auth.uid() = user_id);

grant select, insert on public.questions to authenticated;
