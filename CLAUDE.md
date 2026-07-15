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

1. **What the user does**
   - Describe the user action that starts the flow.

2. **Entry endpoint or component**
   - Identify the backend endpoint, frontend component, or other entry point involved.

3. **Key data flow**
   - Explain the important steps the data passes through, including relevant services, database operations, and external APIs.

4. **Expected successful result**
   - Describe the visible result and any expected data changes.

5. **Possible failure points**
   - List realistic places where the flow could fail and what the user would observe.

6. **Manual testing steps**
   - Provide simple, numbered steps to test the normal flow and important failure cases before merging.

Base the answer on the actual code and PR diff. Do not guess. Keep the explanation concise and beginner-friendly. The user should understand the feature's behavior without needing to understand every line of code.

### gh failures with `x509: OSStatus -26276`: stop retrying, hand the command to the user

The sandbox denies reading `~/Library`, where macOS keeps the Keychain (gh's token) and the
certificate trust store, so `gh` calls fail intermittently with `tls: failed to verify
certificate: x509: OSStatus -26276`. REST vs GraphQL, retry loops, and `curl` + `gh auth token`
all dead-end (see `lab-notebook.md`, 2026-07-15). After ~2 failures with this error, do not keep
trying — print a paste-ready command for the user to run in their own terminal instead.
