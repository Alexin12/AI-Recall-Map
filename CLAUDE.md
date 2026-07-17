## Agent skills

### Issue tracker

Issues live as GitHub issues in Alexin12/AI-Recall-Map, managed via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Git / PR workflow

Dual-mode: Serial (default, plain branch) and Parallel (one worktree per task). One step = one branch = one PR, always cut from an up-to-date main; a human merges from GitHub, no auto-merge. See `docs/agents/git-workflow.md`.

### Triage labels

Default label vocabulary (needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix). See `docs/agents/triage-labels.md`.

### Domain docs

Multi-context layout — `CONTEXT-MAP.md` at root points to `frontend/CONTEXT.md` and `backend/CONTEXT.md`. See `docs/agents/domain.md`.

### Unattended / autonomous runs

When explicitly authorized to run unattended for a long stretch, the following stay hard limits
regardless of autonomy level:

- **Never push or merge directly to `master`/`main`.** Merging a PR is always a human action on
  GitHub.
- **Never force-push.** `git push --force`/`--force-with-lease` is forbidden by policy regardless
  of autonomy level.
- **Never commit `.env`, credentials, API keys, or other secret files.** Check `git status`/`git
  diff` for anything that looks like a secret before every autonomous commit; when in doubt, leave
  it uncommitted and flag it in the summary instead of committing.
- **`rm -rf` is confined to `.claude/worktrees/**`** — enforced by the guard-bash hook
  (`scripts/claude-hooks/guard-bash.sh`). Cleanup or resets elsewhere must not use `rm -rf`.
- **Stop after 3 consecutive failures on the same step** (e.g. a test that won't pass, a command
  that won't succeed) instead of retrying indefinitely — write a short summary of what was tried
  and why it's stuck, then end the turn rather than burning the run on a loop.

### Explain jargon before asking the user to act

The user is a beginner (no prior coding/deployment background) learning this stack as they go. Before asking them to run a command or change a config themselves, explain any non-obvious term in it (tool names like `jq`, `Docker`, config keys like `allowLocalBinding`, `sandbox.network`) in plain language first — what it is and why this step needs it — rather than just handing over the command. Prefer making the change directly when possible over asking the user to run it.

### Lab notebook — mistakes not to repeat

A running log of concrete mistakes made on this project, so a future Claude instance does not
retry them. See `lab-notebook.md` at the repo root; append new entries there, newest at the
bottom.


### PR Testing Guidance

Whenever the user asks how to test a PR before merging, inspect the actual PR changes first and explain the testing plan using this exact structure:


1. **Expected successful result**
   - Describe the visible result and any expected data changes.

2. **Possible failure points**
   - List realistic places where the flow could fail and what the user would observe.

Base the answer on the actual code and PR diff. Do not guess. Keep the explanation concise and beginner-friendly. The user should understand the feature's behavior without needing to understand every line of code.

In addition to the 2-part structure above, whenever the user asks how to test an issue or PR, always also provide:

**A. The exact terminal command to run the whole test suite for those PRs.** Give a copy-paste block, not a description. For this repo's backend that is:

```bash
cd backend
UV_CACHE_DIR="$TMPDIR/uv-cache" uv run pytest tests/test_confirmation.py -v
```

Swap in the test file(s) that actually cover the PR, or run the whole suite with `uv run pytest -v`. Passing tests are necessary but not sufficient — a green suite can still hide an end-to-end gap (e.g. no test asserts the rule the user cares about), so say so when it applies.

**B. A suspect-location table** mapping each acceptance-criteria bullet to the files to inspect and the exact place a bug would live. Four columns, in this order:

| Bullet point (from the issue/PR) | What it means (plain language) | Related file(s) | Suspect location — function/variable names only, no code, and why |
|---|---|---|---|

- Column 1: one acceptance-criteria bullet from the issue/PR, copied as-is.
- Column 2: the same bullet restated in plain language, or as an everyday analogy — what feature this checks and what "working" looks like, written for someone who does not know terms like "route", "verdict", "stub", or "LLM". No jargon; if a technical word is unavoidable, gloss it in the same cell.
- Column 3: the file(s) that implement that bullet.
- Column 4: the specific place a bug would show up. Never assume the reader knows what a function does. Write it as: (1) name the first suspect function/SQL clause/variable **and say in a few plain words what that function does**; (2) name the second one **and say what it does too**; then (3) one short "why" — why these two are where this bullet would break. Names only, never pasted code.

The point of the table is that when a bullet misbehaves end-to-end, the user can read column 2 to understand what should happen, then jump straight to the file and function in columns 3–4 to inspect (backend route vs. scheduler vs. frontend component) instead of guessing.

### `gh` commenting on an issue fails with `x509: OSStatus -26276`: stop retrying, hand the command to the user

Plain `git` operations work fine — clone, fetch, branch, commit, push all reach GitHub without
trouble, so use them normally. The x509 error is **not** a general Git or `gh` failure; it shows
up specifically when using `gh` to comment on an issue (`gh issue comment`, and similar
API-backed writes). The cause is that the sandbox denies reading `~/Library`, where macOS keeps
the Keychain (gh's token) and the certificate trust store, so those `gh` calls fail with `tls:
failed to verify certificate: x509: OSStatus -26276`. REST vs GraphQL, retry loops, and `curl` +
`gh auth token` all dead-end (see `lab-notebook.md`, 2026-07-15). After ~2 failures with this
error, do not keep trying — print a paste-ready command for the user to run in their own terminal
instead.
