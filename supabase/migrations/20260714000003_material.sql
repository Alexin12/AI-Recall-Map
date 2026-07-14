-- Material: one pasted source of text, belonging to a Topic.
-- Same RLS baseline as topics: users see and create only their own rows.

create table if not exists public.materials (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null default auth.uid() references auth.users (id) on delete cascade,
  topic_id   uuid not null references public.topics (id) on delete cascade,
  content    text not null,
  created_at timestamptz not null default now()
);

alter table public.materials enable row level security;

drop policy if exists materials_select_own on public.materials;
create policy materials_select_own on public.materials
  for select using (auth.uid() = user_id);

drop policy if exists materials_insert_own on public.materials;
create policy materials_insert_own on public.materials
  for insert with check (auth.uid() = user_id);

grant select, insert on public.materials to authenticated;
