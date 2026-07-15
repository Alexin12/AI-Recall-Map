-- Review flow: Concepts carry a next-due date; each attempt persists a Review row.

alter table public.concepts
  add column if not exists next_due_at timestamptz not null default now();

create table if not exists public.reviews (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null default auth.uid() references auth.users (id) on delete cascade,
  concept_id  uuid not null references public.concepts (id) on delete cascade,
  question_id uuid not null references public.questions (id) on delete cascade,
  answer      text not null,
  verdict     text not null check (verdict in ('fail', 'partial', 'pass', 'strong')),
  feedback    jsonb not null,
  created_at  timestamptz not null default now()
);

alter table public.reviews enable row level security;

drop policy if exists reviews_select_own on public.reviews;
create policy reviews_select_own on public.reviews
  for select using (auth.uid() = user_id);

drop policy if exists reviews_insert_own on public.reviews;
create policy reviews_insert_own on public.reviews
  for insert with check (auth.uid() = user_id);

grant select, insert on public.reviews to authenticated;
