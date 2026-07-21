You are continuing work on the AI_Recall_Map project (/Users/Alexy/Projects/Own_Products/AI_Recall_Map). Focus: build the Playwright e2e testing layer whose design was just fully agreed with the user via a grill-me session. NO CODE has been written yet.

## Ground rules for this project (read these files, don't re-derive)
- Project + user CLAUDE.md rules apply. The user is a BEGINNER (no coding background): explain any non-obvious term/command in plain language before asking them to run it, and prefer making changes yourself over handing them commands. Respond mainly in Chinese; keep technical terms in English. Never use em dash.
- Git/PR workflow: one step = one branch = one PR cut from up-to-date main; a human merges on GitHub (no auto-merge). Never commit/push unless explicitly told. Follow the `pr-message` skill for PR text.
- Write locked decisions back to DECISIONS.md; write an ADR for architecturally significant ones (the e2e decisions below are marked "Needs a new ADR").

## The agreed design (already recorded — do not re-litigate)
The full A–J decision set and build order is in DECISIONS.md (three `2026-07-21 (M3, e2e)` lines under M3 Active) and in the plan file `~/.claude/plans/claude-code-hidden-mccarthy.md`. Summary:
- Playwright, Chromium-only, co-located in `frontend/` (`pnpm test:e2e`), selectors by `data-testid`/role/text never CSS/position, ONE core happy-path spec first (mirror `backend/tests/test_e2e_core_loop.py`: goal→paste→extract→confirm→review→map).
- Auth in e2e: do nothing — the app has no login page; every page's `getToken()` auto-signs-up a throwaway demo user, session in localStorage; one browser context reuses one demo user for the whole test.
- LLM determinism: add an `LLM_FAKE=1` env toggle guarding the entry of all 5 seam functions in `backend/app/llm.py` (extract_concepts, grade_answer, score_relevance, route_concepts, propose_topics), returning canned Pydantic objects defined INLINE (lift the literals from backend/tests/test_extraction.py `STUB_CONCEPTS` and test_reviews.py `STUB_GRADE`; do NOT import test code into app). Default off, production unaffected. Guarding at function entry short-circuits before `_client()`, so e2e backend needs NO OPENROUTER_API_KEY.
- Services: Playwright `webServer` starts backend (with `LLM_FAKE=1`) + frontend; Supabase started separately via `supabase start` and left running. Ports: Supabase 54321, backend 8000, frontend 3000.
- No test-data cleanup (fresh isolated demo user per run + RLS; CI DB ephemeral).
- Gate into no-mistakes: `commands.test` in `.no-mistakes.yaml` runs a `scripts/nm-test.sh` (backend pytest + `pnpm test:e2e`); set `test.evidence.store_in_repo: true` so Playwright traces/screenshots land on the PR.
- CI: new `.github/workflows/e2e.yml` using `supabase start` for the full auth stack; triggers = PR→main + manual dispatch. Build LOCAL-GREEN-FIRST, CI last.

## Build order (each = its own branch + PR)
1. Backend `LLM_FAKE` toggle in `backend/app/llm.py` (verify with `cd backend && uv run pytest`).
2. Add `data-testid` to the key interactive elements on the happy-path.
3. Playwright skeleton: `frontend/playwright.config.ts` (Chromium, webServer) + `frontend/e2e/` + one happy-path spec.
4. Get it green locally (user runs `supabase start` first, then `pnpm test:e2e` on the host).
5. `scripts/nm-test.sh` + `.no-mistakes.yaml` `commands.test` wiring.
6. `.github/workflows/e2e.yml`.

## Environment constraints (important)
- This runs in a Claude Code sandbox: Docker CLI is BLOCKED, so Supabase/backend e2e cannot actually run inside the sandbox — the user runs them on their real Mac (or CI). Do local verification steps by handing the user copy-paste commands and reading their output. See memory `project_sandbox_dev_constraints.md` and `project_no_mistakes_workflow.md`.
- no-mistakes is installed and drivable from the sandbox via `no-mistakes axi run` (NOT `init`, which writes `.git/config` and is sandbox-blocked); it was already init'd once from the user's terminal. Its daemon runs the pipeline on the host.
- Redirect caches: `UV_CACHE_DIR="$TMPDIR/uv-cache"`, npm/pnpm cache to `$TMPDIR`.

## FIRST ACTIONS (do these before writing any code)
1. The user said "no need to code yet" — confirm they're ready to start implementing before touching code.
2. There is ONE pending decision: whether to add a reusable "Playwright e2e defaults" block to the GLOBAL `~/.claude/CLAUDE.md` (proposed and shown to the user; awaiting their yes/where — global vs this project's CLAUDE.md). Resolve this with the user first. The proposed block is the reusable half of the A–J decisions (selectors, chromium-only, one happy-path first, co-location, env-var stub toggle for live-server e2e, webServer for light servers + long-lived DB, skip cleanup with isolated users, build order).
3. Then start at build step 1 (LLM_FAKE toggle), incrementally, one branch/PR at a time, validating each step before the next.

## Suggested skills to invoke
- `understandv2` / `drill-down` when the beginner user needs a concept explained (writes to `/Users/Alexy/Projects/QA_records/`).
- `run` to launch the app and `verify` to exercise the e2e flow end-to-end before declaring a step done.
- `no-mistakes` to gate a finished branch (`axi run`).
- `pr-message` when opening each PR; `review` / `code-review` before merge.
