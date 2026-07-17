# Lab notebook — mistakes not to repeat

A running log of concrete mistakes made on this project. Append new entries at the bottom.

## 2026-07-15 — gh write calls fail intermittently inside the sandbox (keychain)

**What happened:** While filing QA issues, `gh issue create` worked but `gh issue comment`
(and every other write retry) kept failing with `tls: failed to verify certificate:
x509: OSStatus -26276`. Multiple workarounds were attempted and all failed: switching from
GraphQL to the REST API (`gh api`), bounded retry loops (5 tries x 4 issues), and bypassing
`gh` with `curl` + `gh auth token`.

**Root cause:** The Bash sandbox denies reading `~/Library`. On macOS, `gh` stores its login
token in the Keychain (files under `~/Library`) and verifies HTTPS certificates through the
macOS security framework, which also depends on that directory. Requests succeed only when a
trust cache happens to be warm (that's why the 5 issue creations went through) and fail once
it isn't. The `curl` bypass dead-ends because `gh auth token` cannot read the Keychain either
("no oauth token found").

**Lesson:** Do not burn a run retrying `gh` against this error. After ~2 failures with
`OSStatus -26276`, stop and hand the user a paste-ready command to run in their own terminal
(outside the sandbox), e.g.:

```bash
for n in 26 27 28 29; do gh issue comment $n -R Alexin12/AI-Recall-Map --body "Found during user acceptance of M1 slice 5 (#7)."; done
```

## 2026-07-17 — false alarm: `git push` "credential storage lock" errors are NON-FATAL

**What happened:** After committing the M2 decision docs on a feature branch, I ran
`git push -u origin <branch> 2>&1 | tail -3`, saw `unable to get credential storage lock in
1000 ms: Operation not permitted` and `could not lock config file .git/config`, then
`Everything up-to-date` on a retry, and concluded the push was blocked by the sandbox. I built
a whole (wrong) root cause around it — even blamed the PR base branch — and handed the push off
to the user. The user proved it false: the same command in another session pushed fine despite
the identical errors.

**Root cause:** The push actually SUCCEEDS. Git reads the credential from `~/.git-credentials`
(which is readable — only `~/Library`, Downloads, etc. are read-denied) and authenticates. The
errors are non-fatal side effects: the credential *store* helper cannot re-lock/cache that file
(writing under `~/` is denied), and `-u` cannot write the upstream bookmark into `.git/config`
(that path is write-denied). Neither stops the object transfer. My real mistakes were (a) piping
push output through `tail`, which chopped off the `* [new branch] ... -> ...` success line, and
(b) misreading `Everything up-to-date` (it meant "already pushed on the first attempt") as
failure. A live test confirmed it: the push prints the errors AND `* [new branch]`, and
`git ls-remote` then shows the ref on the remote.

**Lesson:** `git push` works in the sandbox. Do NOT pipe its output through `tail` — read the
full output and look for the `* [new branch]` / `->` success line. `Everything up-to-date` means
it already pushed, not that it failed. `unable to get credential storage lock` and `could not
lock config file .git/config` are cosmetic (no upstream tracking, no credential cache) — ignore
them. You can `git push` and `gh pr create` directly; do not hand the push off to the user over
these errors. (This is distinct from the 2026-07-15 x509 `OSStatus -26276` entry above, which is
a real failure that does warrant a handoff.)
