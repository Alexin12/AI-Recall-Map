# Git / PR workflow (dual-mode)

Every task — even a single small step — is developed on its own branch and ships as its own pull request. One step = one branch = one PR, always cut from an up-to-date main. There are no intermediate / integration branches (e.g. no long-lived phase-one-dashboard-one): every branch starts from main and every PR merges back into main. This keeps each PR small, easy to review, and easy to `git revert` on its own.

There are two modes. **Default to Serial mode.** Only use Parallel mode when multiple independent tasks genuinely need to be in flight at the same time.

Rules shared by both modes:

- Name branches with a short, human-readable kebab-case slug that says what the work is about. Good: `ai-interface-chat`, `price-relative-watchlists`, `fix-macd-warmup`. Bad: auto-generated random names like `hopeful-dhawan-73823a`. If a tool defaults to a random name, override it.
- Never commit a task directly to main.
- Reference the issue in the commit/PR body with `Closes #<n>` so merging auto-closes it.
- The merge is a human action, done from GitHub. When merging, tick "Delete branch" so the remote feature branch is removed in the same action. No auto-merge.
- Still honor the global rule: only commit/push/open a PR when the user has asked for it — report the work first if unsure.

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
