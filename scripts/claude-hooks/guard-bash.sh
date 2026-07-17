#!/usr/bin/env bash
# PreToolUse guardrail for the Bash tool, used during unattended agent runs.
# Blocks:
#   1. rm -rf (any -r/-f flag combo) outside .claude/worktrees/**
#   2. git push that would land on master/main (explicit ref or current branch)
# Read-only otherwise: any other command passes through untouched.
set -euo pipefail

input=$(cat)
command=$(printf '%s' "$input" | jq -r '.tool_input.command // empty')

deny() {
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}\n' "$1"
  exit 0
}

# --- Guard 1: rm -rf (or -r -f, --recursive --force, any combo/order) outside the allow-listed dir ---
while IFS= read -r rm_segment; do
  [ -z "$rm_segment" ] && continue
  args=$(printf '%s' "$rm_segment" | sed -E 's/^rm[[:space:]]+//')
  has_r=0
  has_f=0
  paths=""
  for tok in $args; do
    case "$tok" in
      --recursive) has_r=1 ;;
      --force) has_f=1 ;;
      -*)
        case "$tok" in *r*|*R*) has_r=1 ;; esac
        case "$tok" in *f*) has_f=1 ;; esac
        ;;
      *) paths="$paths$tok"$'\n' ;;
    esac
  done
  if [ "$has_r" -eq 1 ] && [ "$has_f" -eq 1 ]; then
    bad=0
    [ -z "$paths" ] && bad=1
    while IFS= read -r p; do
      [ -z "$p" ] && continue
      case "$p" in
        .claude/worktrees/*|*/.claude/worktrees/*) ;;
        *) bad=1 ;;
      esac
    done <<< "$paths"
    if [ "$bad" -eq 1 ]; then
      deny "rm -rf is only allowed inside .claude/worktrees/** — blocked by project guardrail hook (scripts/claude-hooks/guard-bash.sh)."
    fi
  fi
done <<< "$(printf '%s' "$command" | grep -oE '(^|[;&|]|&&|\|\|)[[:space:]]*rm[[:space:]]+[^;&|]*' | sed -E 's/^[;&|]+[[:space:]]*//')"

# --- Guard 2: git push landing on master/main ---
if printf '%s' "$command" | grep -qE '(^|[;&|]|&&|\|\|)\s*git\s+push\b'; then
  if printf '%s' "$command" | grep -qE 'git\s+push[^;&|]*\b(origin\s+)?(master|main)\b'; then
    deny "git push to master/main is blocked by project guardrail hook — push a feature branch and open a PR instead."
  fi
  push_args=$(printf '%s' "$command" | grep -oE 'git\s+push[^;&|]*' | sed -E 's/^git[[:space:]]+push//' | tr ' ' '\n' | grep -vE '^(-|$)' || true)
  ref_arg_count=$(printf '%s\n' "$push_args" | grep -cv '^$' || true)
  if [ "$ref_arg_count" -le 1 ]; then
    branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
    if [ "$branch" = "master" ] || [ "$branch" = "main" ]; then
      deny "git push while checked out on master/main is blocked by project guardrail hook."
    fi
  fi
fi

# --- Reminder: force the lab-notebook GitHub lessons in front of any github action ---
# Non-blocking: injects context (additionalContext) before git push/pull/fetch or any gh call.
if printf '%s' "$command" | grep -qE '(^|[;&|]|&&|\|\|)[[:space:]]*(git[[:space:]]+(push|pull|fetch)|gh[[:space:]])'; then
  reminder='Before this GitHub action, recall lab-notebook.md: (1) git push SUCCEEDS in this sandbox — "unable to get credential storage lock" and "could not lock config file .git/config" are NON-FATAL; the push still lands. Do NOT pipe push output through tail; read the full output and look for the "* [new branch]" / "->" success line. "Everything up-to-date" means it already pushed, not that it failed. You may run git push and gh pr create directly — do not hand the push off to the user over these errors. (2) If a gh WRITE fails with x509 OSStatus -26276, stop after ~2 tries and hand the user a paste-ready command to run in their own terminal.'
  jq -cn --arg ctx "$reminder" '{hookSpecificOutput:{hookEventName:"PreToolUse",additionalContext:$ctx}}'
  exit 0
fi

exit 0
