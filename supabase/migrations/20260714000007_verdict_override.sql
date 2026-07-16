-- Verdict override: reviews keep the AI's verdict alongside the final verdict.
-- `verdict` stays the final verdict (what the Scheduler reads); `ai_verdict`
-- records what the AI originally said.

alter table public.reviews
  add column if not exists ai_verdict text
    check (ai_verdict in ('fail', 'partial', 'pass', 'strong'));

update public.reviews set ai_verdict = verdict where ai_verdict is null;

alter table public.reviews alter column ai_verdict set not null;

drop policy if exists reviews_update_own on public.reviews;
create policy reviews_update_own on public.reviews
  for update using (auth.uid() = user_id) with check (auth.uid() = user_id);

grant update on public.reviews to authenticated;
