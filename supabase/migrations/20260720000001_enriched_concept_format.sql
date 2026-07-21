-- AI-enriched Concept format (ADR-0008): a fixed six-field template layered
-- on top of the existing name/explanation/source_snippet shape. `keyword`
-- and `source_excerpt` are exposed on Concept detail as aliases of name and
-- source_snippet (no new columns needed for those two); the other four
-- fields are genuinely new content the extraction prompt now produces.
-- Idempotent so the file can be re-applied.

alter table public.concepts
  add column if not exists analogy text not null default '',
  add column if not exists technical_explanation text not null default '',
  add column if not exists code_snippet text not null default 'none',
  add column if not exists core_claim text,
  add column if not exists ai_supplemented_fields text[] not null default '{}';
