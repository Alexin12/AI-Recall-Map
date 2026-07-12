# cleanup-worktree.sh — Usage

Script: `scripts/cleanup-worktree.sh`

## What it does

Cleans up a git worktree (an extra checked-out working directory tied to a
branch) after its PR has merged, in one step:

1. Removes `.git/worktrees/<name>` — git's internal bookkeeping.
2. Removes `.claude/worktrees/<name>` — the actual checked-out folder.
3. Runs `git worktree prune`.
4. Runs `git branch -d <branch>` (lowercase `-d`: refuses unless the branch
   is truly merged — a safety net, not a formality).

## Why run it yourself, not the agent

Sandbox write rules block anything under `.git/worktrees/`, with no prompt
to approve it. Only your own terminal can run this.

## When to use it

Only in **Parallel mode** (multiple worktrees in flight at once). Serial
mode uses a plain branch in the main working dir — no worktree, no need for
this script (`git branch -d` there just works).

## Usage

```sh
./scripts/cleanup-worktree.sh <worktree-name> [<branch-name>]
```

`<branch-name>` defaults to `<worktree-name>` — by convention the worktree
directory and its branch always share the same slug, so in practice you
only ever pass one argument. Pass the second only if that convention was
broken when the worktree was created (e.g. a tool auto-generated a
different branch name).

## Example

Worktree and branch both named `price-relative-watchlists`, PR already
merged on GitHub:

```sh
./scripts/cleanup-worktree.sh price-relative-watchlists
```

```
Will remove:
  <repo>/.git/worktrees/price-relative-watchlists
  <repo>/.claude/worktrees/price-relative-watchlists
  local branch 'price-relative-watchlists' (git branch -d — refuses unless merged)
Continue? [y/N]
```

Type `y` — all three are removed.

Diverging names (worktree `wt1`, branch `fix-macd-warmup`):

```sh
./scripts/cleanup-worktree.sh wt1 fix-macd-warmup
```

## Common failure

`git branch -d` refuses with "not fully merged" — usually because GitHub
squash-merged the PR, so local git can't see it as merged. Fix:

```sh
git branch -vv | grep gone   # confirms the branch's upstream is gone
```

Then either run `/clean_gone` (batch-cleans all such branches) or force it
manually: `git branch -D <branch>`.
