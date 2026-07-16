# Git / PR workflow (three modes)

Every task — even a single small step — is developed on its own branch and ships as its own pull request. One step = one branch = one PR. In Serial and Parallel mode, every branch is cut from an up-to-date main and every PR merges straight back into main — there are no intermediate / integration branches. This keeps each PR small, easy to review, and easy to `git revert` on its own.

**Chain mode is the one exception**: it introduces a single long-lived integration branch so an agent can run a sequence of dependent issues unattended, with only one human approval at the end instead of one per issue. See below for when that tradeoff is worth it.

There are three modes. **Default to Serial mode.** Use Parallel mode when multiple independent tasks genuinely need to be in flight at the same time. Use Chain mode when a human explicitly asks for an unattended run through a sequence of *dependent* issues (each blocked by the last).

Rules shared by both modes:

- Name branches with a short, human-readable kebab-case slug that says what the work is about. Good: `ai-interface-chat`, `price-relative-watchlists`, `fix-macd-warmup`. Bad: auto-generated random names like `hopeful-dhawan-73823a`. If a tool defaults to a random name, override it.
- **Worktree names must match their branch name — never a random ID.** One PR = one branch = one worktree, and the worktree directory must be named identically to the branch slug (e.g. branch `fix-macd-warmup` → worktree `.claude/worktrees/fix-macd-warmup`), so a later cleanup pass can tell at a glance which worktree belongs to which branch/PR. Do not use the Agent tool's `isolation: "worktree"` option for this repo's task branches — it mints an opaque random name (e.g. `agent-a59380d9e9fedeb01`) that breaks this mapping. Instead, create the worktree explicitly with `EnterWorktree` or `git worktree add`, naming both the directory and the branch with the task slug, per the Parallel mode steps below.
- Never commit a task directly to main.
- Reference the issue in the commit/PR body with `Closes #<n>` so merging auto-closes it.
- The merge is a human action, done from GitHub. When merging, tick "Delete branch" so the remote feature branch is removed in the same action. No auto-merge.
- Still honor the global rule: only commit/push/open a PR when the user has asked for it — report the work first if unsure.
- **After all tests pass, report completion and hand the user manual E2E test steps.** Once an agent finishes its test run for a task, it must not just say "done" — it must tell the user, in plain language, how to verify the change themselves end-to-end: which branch/worktree to check out, and the concrete path to exercise on the frontend (e.g. which URL/route) and/or backend (e.g. which endpoint/script) for this change. Spell out any non-obvious command or term before handing it over — see "Explain jargon before asking the user to act" in the root CLAUDE.md.
- **After a PR merges, always return worktree-cleanup instructions.** As soon as an agent learns (or the user confirms) that a task's PR has merged, it must proactively tell the user how to remove that task's worktree — both `.git/worktrees/<name>` (git's internal bookkeeping) and `.claude/worktrees/<name>` (the actual checked-out directory) — using `./scripts/cleanup-worktree.sh <worktree> [<branch>]` (see step 7 of Parallel mode below). Do not wait to be asked; do not assume Serial mode's plain `git branch -d` is enough if a worktree was ever created for that task.

## Serial mode (default): plain branch in the main working dir

One task at a time, in the normal working directory. No worktrees, so none of the worktree cleanup friction below applies — `git branch -d` runs fine in the sandbox.

For each task, in order:

1. **Sync main** — before writing any code:
   ```sh
   git checkout main
   git pull            # latest main from origin (includes the last merged PR)
   ```
2. **Create the task branch** off the fresh main:
   ```sh
   git checkout -b <task-slug>
   ```
3. **Work, then commit** — once complete and verified, commit on that branch.
4. **Push** — `git push -u origin <task-slug>`.
5. **Open a PR into main** — `gh pr create --base main`. Human reviews and merges from GitHub.
6. **Clean up** after the merge:
   ```sh
   git checkout main
   git pull --prune                 # latest main + drop stale origin/* tracking refs
   git branch -d <task-slug>        # lowercase -d: refuses unless truly merged
   ```
   If a squash-merge makes `-d` wrongly report "not merged", the branch's upstream shows as `[gone]` after `--prune` (`git branch -vv | grep gone`); use /clean_gone to clear all such branches at once.
7. Next task starts over at 1.

## Parallel mode: one worktree per task

Use only when several **independent** tasks should progress at the same time (tasks that depend on each other stay serial — a dependent task must wait for its prerequisite PR to merge, then cut from the updated main). Each task gets its own worktree on its own branch; the worktree directory uses the same slug as its branch. All worktrees are cut from the same up-to-date main and their PRs can merge in any order.

For each task, in order:

1. **Pre-flight: clean up finished worktrees first.** Before creating a new worktree, check whether any earlier worktree's PR has already merged — do not just pile a new worktree on top:
   ```sh
   git worktree list                                # spot any worktree whose PR has already merged
   gh pr view <prev-branch> --json state,mergedAt   # confirm it's MERGED if unsure
   ```
   If merged, it needs cleanup — but the sandbox blocks writes under `.git/worktrees/`, so `git worktree remove`/`prune` and `git branch -d` fail with "Operation not permitted" no matter how they're invoked, and there is no permission prompt to grant for it. Do not attempt these commands yourself. Ask the user to run the cleanup script in their own terminal:
   ```sh
   ./scripts/cleanup-worktree.sh <prev-worktree> [<prev-branch>]
   ```
   The script removes both paths — `.git/worktrees/<name>` (git's internal bookkeeping) **and** `.claude/worktrees/<name>` (the actual checked-out working directory). Removing only the first leaves an orphaned folder full of files that `git worktree list` no longer knows about but Finder/VS Code still shows (this has bitten us before — see lab-notebook.md). It then runs `git branch -d <branch>` (lowercase `-d`: refuses unless truly merged, as a safety net).
2. **Sync main**:
   ```sh
   git checkout main
   git pull
   ```
3. **Create a new worktree** off the fresh main (EnterWorktree or `git worktree add`), naming both the worktree directory and its branch with the task slug.
4. **Work, then commit** on that branch once complete and verified.
5. **Push** — `git push -u origin <branch>`.
6. **Open a PR into main** — `gh pr create --base main`. Human reviews and merges from GitHub.
7. **Clean up** after the merge. Back on main, sync (this part IS runnable — `git checkout`/`git pull` write to the working tree and refs, not `.git/worktrees/`):
   ```sh
   git checkout main
   git pull --prune
   ```
   Then removing the merged worktree and branch is sandboxed out (see step 1) — ask the user to run:
   ```sh
   ./scripts/cleanup-worktree.sh <feature-worktree> [<feature-branch>]
   ```
   Squash-merge caveat: same as Serial mode step 6 — `[gone]` upstream + /clean_gone.
8. Next task starts over at 1.

## Chain mode: one integration branch, run unattended through a sequence of dependent issues

Use only when a human has explicitly asked for an unattended run through several issues that are genuinely **serial** — each one blocked by the last (check each issue's "Blocked by" field; if two issues in the sequence don't actually depend on each other, their order within the chain doesn't matter, but don't reach for a second worktree to parallelize them — a sibling worktree adds disk/install/rebase overhead with no payoff when nothing downstream is waiting on parallelism). The point of Chain mode is to collapse "one human approval per issue" down to "one human approval for the whole sequence" — it trades per-issue revert granularity on `main` for unattended throughput, so only use it when the user has accepted that tradeoff for this batch.

One worktree for the whole chain, checked out on the integration branch. Do **not** open a second worktree per issue — the issues are dependent, so only one is ever in flight; a sibling worktree per issue just duplicates disk usage and `uv sync`/`npm install` cost and needs constant rebasing as the integration branch moves.

1. **Create the integration branch** off an up-to-date main, named for the sequence (e.g. `m1-core-loop`):
   ```sh
   git checkout main
   git pull
   git checkout -b <integration-branch>
   git push -u origin <integration-branch>
   ```
   If a prior task's branch already contains the first issue's work and the human wants to reuse it as the integration branch, that's fine — just confirm with the human before repurposing an existing branch this way.
2. **For each issue in the sequence, in dependency order:**
   - Sync the integration branch: `git checkout <integration-branch> && git pull`.
   - Cut the issue's branch off the integration branch's current tip: `git checkout -b <issue-slug>`.
   - Work, verify (tests/tsc — see "After all tests pass" rule above), commit.
   - Push and open a PR **into the integration branch**, not main: `gh pr create --base <integration-branch>`.
   - The agent merges this PR itself (it's an internal step within the chain, not the final gate) once tests pass — no human approval needed here.
   - Delete the issue branch locally/remotely after merge, same as the cleanup step in Serial mode.
   - Stop and report to the human if 3 consecutive issues in the chain fail the same way (per the "stop after 3 consecutive failures" rule in the root CLAUDE.md) rather than continuing to burn the run.
3. **After the last issue in the sequence merges into the integration branch**, open the one PR that needs human approval: `gh pr create --base main` from the integration branch. Report completion and hand the human manual E2E test steps covering the whole sequence, same as any other PR.
4. **After that final PR merges**, clean up the integration branch same as any Serial/Parallel branch cleanup — `git branch -d <integration-branch>` (or the worktree cleanup script, if it was ever checked out as a worktree rather than the main working dir).
