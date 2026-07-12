#!/bin/sh
# Clean up a merged worktree + its branch. Run from anywhere inside the repo,
# in YOUR OWN terminal (the agent sandbox cannot delete under .git/worktrees/).
#
# Usage: ./scripts/cleanup-worktree.sh <worktree-name> [<branch-name>]
# If <branch-name> is omitted, it defaults to <worktree-name>.
set -eu

name="${1:?usage: cleanup-worktree.sh <worktree-name> [<branch-name>]}"
branch="${2:-$name}"

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

echo "Will remove:"
echo "  $repo_root/.git/worktrees/$name"
echo "  $repo_root/.claude/worktrees/$name"
echo "  local branch '$branch' (git branch -d — refuses unless merged)"
printf "Continue? [y/N] "
read -r ans
[ "$ans" = "y" ] || { echo "Aborted."; exit 1; }

rm -rf ".git/worktrees/$name"
rm -rf ".claude/worktrees/$name"
git worktree prune

git branch -d "$branch" || {
  echo "git branch -d refused — likely a squash merge."
  echo "Check: git branch -vv | grep gone   (then use /clean_gone or git branch -D $branch)"
}
