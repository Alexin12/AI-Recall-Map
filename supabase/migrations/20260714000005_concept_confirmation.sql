-- Confirmation state on Concepts: scheduled (enters review) and confirmed
-- (user approved on the confirmation screen). Due-eligible = confirmed AND scheduled.
-- Users may edit and delete their own Concepts before confirming.

alter table public.concepts
  add column if not exists scheduled boolean not null default false,
  add column if not exists confirmed boolean not null default false;

drop policy if exists concepts_update_own on public.concepts;
create policy concepts_update_own on public.concepts
  for update using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists concepts_delete_own on public.concepts;
create policy concepts_delete_own on public.concepts
  for delete using (auth.uid() = user_id);

grant update, delete on public.concepts to authenticated;
