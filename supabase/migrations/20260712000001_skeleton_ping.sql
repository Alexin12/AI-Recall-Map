-- Walking-skeleton demo table: one ping row per authenticated user.
-- Proves the frontend -> backend -> Postgres round trip and the RLS baseline
-- that every later domain table will follow.

--create a table
-- auth.uid() get from db
create table if not exists public.skeleton_ping (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null default auth.uid() references auth.users (id) on delete cascade,
  message    text not null,
  created_at timestamptz not null default now()
);

-- add RLS
alter table public.skeleton_ping enable row level security;

-- A user may only see and create their own rows.
create policy skeleton_ping_select_own on public.skeleton_ping
  for select using (auth.uid() = user_id);

-- Only authenticated user can insert 
create policy skeleton_ping_insert_own on public.skeleton_ping
  for insert with check (auth.uid() = user_id);

-- grant see and insert ability to authenticated user
grant select, insert on public.skeleton_ping to authenticated;
