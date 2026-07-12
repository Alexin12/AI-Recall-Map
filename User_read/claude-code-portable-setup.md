# Portable Claude Code Setup — Copy Into Any Repo

Source repo: `Financial_Tools`. This file is self-contained: it includes the actual file
contents you need, not just descriptions. Give this file to a Claude Code agent working in a
different repo and tell it: "Apply the setup described in this file to this repo." It should be
able to create/edit every file listed below without asking you to paste anything else.

Everything here is generic — none of it depends on this repo's business logic (dashboards,
Python, FastAPI, etc.). Adapt only the two placeholders marked `<ADAPT>`.

---

## 1. Safety hook: block `rm -rf` and `git push` to master/main

Blocks two classes of dangerous Bash commands before they run:
- `rm -rf` (any flag order/combo: `-rf`, `-fr`, `-r -f`, `--recursive --force`, mixed) unless
  every path argument is under an allow-listed "scratch" directory.
- `git push` that would land on `master` or `main` — either by explicit ref (`git push origin
  master`) or implicitly (bare `git push` / `git push origin` while `HEAD` is `master`/`main`).

**Create `scripts/claude-hooks/guard-bash.sh`:**

```bash
#!/usr/bin/env bash
# PreToolUse guardrail for the Bash tool, used during unattended agent runs.
# Blocks:
#   1. rm -rf (any -r/-f flag combo) outside <ADAPT: your scratch/worktree dir>/**
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
        # <ADAPT>: replace .claude/worktrees with your project's allow-listed scratch dir
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

exit 0
```

Make it executable: `chmod +x scripts/claude-hooks/guard-bash.sh`.

**Wire it into `.claude/settings.json`** (merge into the `hooks.PreToolUse` array — see full
settings.json block in section 3 below).

---


## 2. Slash command: `/improve` (post-task self-reflection)

Generic, zero repo dependency. Prompts the agent to honestly critique its own efficiency after
finishing a task — separates genuine agent inefficiency (redos, too-granular steps, missed
batching) from constraints imposed by the user or the workflow.

**Create `.claude/commands/improve.md`:**

```markdown
---
description: Reflect on how the just-completed work could have been done faster
---

Ok, great, nice job. How could you have arrived at these conclusions and done everything I just
asked you to do faster?

Reflect honestly and specifically on the work just completed in this session:

- Identify the genuine inefficiencies that were YOURS — redos, too-granular steps, missed
  batching, format guesses that caused rewrites.
- Separate those from constraints set by the skill/workflow or by my own pacing (don't
  blame-shift, but be honest about what you genuinely could not compress).
- Give concrete, actionable speedups for next time, not generic advice.

Keep it tight; no filler.

$ARGUMENTS
```

---

## 3. CLAUDE.md sections to copy verbatim

Add these sections to the target repo's root `CLAUDE.md` (or merge into existing equivalent
sections). They are pure workflow/safety rules with no reference to this repo's code.



### 3a. Autonomous-run hard limits

Use this if the target repo will ever let Claude commit/push/open PRs without asking each time
(e.g. via a `/loop` or scheduled run).

```markdown
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
- **`rm -rf` is confined to `<ADAPT: your allow-listed scratch dir>/**`** — enforced by the
  guard-bash hook (see section 1). Cleanup or resets elsewhere must not use `rm -rf`.
- **Stop after 3 consecutive failures on the same step** (e.g. a test that won't pass, a command
  that won't succeed) instead of retrying indefinitely — write a short summary of what was tried
  and why it's stuck, then end the turn rather than burning the run on a loop.
```


### 3b. Batch edits habit

```markdown
- **Batch edits; don't fragment.** When several file edits or reads are independent, issue them as
  parallel tool calls in a single step instead of many sequential round-trips. Group related
  changes to one file into one pass rather than many tiny edits.
```

### 3c. Command execution rules (explain-assess-execute)

```markdown
## Command Execution Rules

Before invoking the Bash tool or running any terminal command, strictly adhere to:
1. **Explain the Command**: Provide a concise, one-sentence explanation in the chat describing
   exactly what the command does.
2. **Assess Risk**: Briefly evaluate the safety of the command (e.g., whether it is a safe
   read-only operation or if it carries potential risks like modifying or deleting files).
3. **Execute**: Only call the Bash tool *after* you have output the explanation and risk
   assessment to the user.
```


### 3d. Lab notebook (mistakes-not-to-repeat log)

Create an empty `lab-notebook.md` at repo root, and add:

```markdown
## Lab notebook — mistakes not to repeat

A running log of concrete mistakes made on this project, so a future Claude instance does not
retry them. See `lab-notebook.md` at the repo root; append new entries there, newest at the
bottom.
```

---



