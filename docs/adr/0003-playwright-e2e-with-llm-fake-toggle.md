# Browser e2e tests use Playwright with a backend LLM_FAKE toggle, not mocks

Backend tests already cover the API surface with `pytest` + `monkeypatch`, but nothing exercised the real browser: real React state, real streaming fetch parsing, real routing between pages. Playwright fills that gap with one Chromium-only, co-located suite in `frontend/` (`pnpm test:e2e`), starting with a single happy-path spec that mirrors `backend/tests/test_e2e_core_loop.py` (goal → paste → extract → confirm → review → map).

The hard problem is determinism: extraction and grading call a real LLM, and a live server process can't be `monkeypatch`ed the way pytest stubs it — `monkeypatch` only reaches code running inside the same test process. The fix is a `LLM_FAKE=1` environment toggle that short-circuits all five LLM seams in `backend/app/llm.py` (`extract_concepts`, `grade_answer`, `score_relevance`, `route_concepts`, `propose_topics`) before they build a client, returning canned Pydantic objects defined inline. Default off, so production and pytest (which still uses `monkeypatch`) are unaffected; the e2e backend needs no `OPENROUTER_API_KEY`.

Auth needed no new test scaffolding: every page's `getToken()` already auto-signs-up a throwaway demo user on first use, so one browser context naturally gets one isolated demo user per run. Combined with RLS, this also means no test-data cleanup step is needed — a fresh user each run has nothing to collide with.

Playwright's `webServer` option starts the backend (with `LLM_FAKE=1`) and the frontend directly; Supabase is heavier (Docker-backed) and is started separately with `supabase start` and left running rather than being torn up per run. Selectors are `data-testid`/role/text only, never CSS or DOM position, so the suite doesn't pin itself to a still-changing UI.

**Status**: accepted

**Consequences**:
- `backend/app/llm.py` carries a small amount of test-only branching (`_fake_enabled()` guards) permanently; this is the accepted cost of deterministic e2e output.
- `commands.test` in the repo's `.no-mistakes.yaml` runs `scripts/nm-test.sh` (backend pytest + `pnpm test:e2e`), with `test.evidence.store_in_repo: true` so Playwright traces/screenshots land on the PR.
- `.github/workflows/e2e.yml` runs the same suite in CI using `supabase/setup-cli` + `supabase start` for the full auth stack, on PR→main and manual dispatch.
- Future e2e specs beyond the one happy path should extend this same LLM_FAKE/webServer/no-cleanup setup rather than inventing a parallel harness.
