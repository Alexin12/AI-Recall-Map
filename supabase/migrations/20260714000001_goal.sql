-- Goal: the user's single stated learning goal. One row per user, editable.

create table if not exists public.goals (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null default auth.uid() references auth.users (id) on delete cascade unique,
  content    text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.goals enable row level security;

-- A user may only see, create, and edit their own Goal.
drop policy if exists goals_select_own on public.goals;
create policy goals_select_own on public.goals
  for select using (auth.uid() = user_id);

drop policy if exists goals_insert_own on public.goals;
create policy goals_insert_own on public.goals
  for insert with check (auth.uid() = user_id);

drop policy if exists goals_update_own on public.goals;
create policy goals_update_own on public.goals
  for update using (auth.uid() = user_id) with check (auth.uid() = user_id);

grant select, insert, update on public.goals to authenticated;
