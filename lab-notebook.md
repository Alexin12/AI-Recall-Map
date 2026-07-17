# Lab notebook — mistakes not to repeat

A running log of concrete mistakes made on this project. Append new entries at the bottom.

## 2026-07-15 — `gh issue comment` fails inside the sandbox (keychain), but plain git is fine

**Scope note:** This is *not* a general Git or `gh` failure. Plain `git` (clone, fetch, branch,
commit, push) reaches GitHub without trouble and should be used normally. The error is specific
to `gh` writes that hit the GitHub API — commenting on an issue is the case that bit us.

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
