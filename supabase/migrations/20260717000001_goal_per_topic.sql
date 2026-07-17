-- Goal per Topic (ADR-0006): the Goal moves from the user level onto each
-- Topic. A Topic's goal is optional; NULL means "browse only, never due".
-- All statements are idempotent so the file can be re-applied.

alter table public.topics
  add column if not exists goal text;

-- Setting/clearing a Topic's Goal needs UPDATE, which topics lacked until now.
drop policy if exists topics_update_own on public.topics;
create policy topics_update_own on public.topics
  for update using (auth.uid() = user_id) with check (auth.uid() = user_id);

grant update on public.topics to authenticated;

-- Relevance is judged against the Topic's Goal; with no Goal it is unknowable,
-- so the column becomes nullable (NULL = unscored, ADR-0006).
alter table public.concepts
  alter column goal_relevance drop not null;

-- The user-level Goal is gone; existing global-goal data is deliberately
-- abandoned, no migration (ADR-0006).
drop table if exists public.goals;
