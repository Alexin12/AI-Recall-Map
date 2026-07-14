-- Topic: groups everything a learner studies about one subject.
-- Same RLS baseline as skeleton_ping: users see and create only their own rows.

create table if not exists public.topics (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null default auth.uid() references auth.users (id) on delete cascade,
  name       text not null,
  created_at timestamptz not null default now()
);

alter table public.topics enable row level security;

drop policy if exists topics_select_own on public.topics;
create policy topics_select_own on public.topics
  for select using (auth.uid() = user_id);

drop policy if exists topics_insert_own on public.topics;
create policy topics_insert_own on public.topics
  for insert with check (auth.uid() = user_id);

grant select, insert on public.topics to authenticated;
