# Milestone workflow

How a Milestone is planned, built, and closed on this project. Read this before starting or
finishing any Milestone.

## The flow per Milestone

**Ground → PRD → Issues → Build → Close.**

1. **Ground** — Stress-test the plan and lock the human product decisions before any PRD
   exists. Use a grilling skill (`grill-me`, `grill-with-docs`, or `batch-grill-me`). Input may
   be a throwaway scratch plan (e.g. an `*-overall-plan.md`); its only job is to feed the
   grilling. Output is a set of **locked decisions** held in the conversation. A scratch plan is
   disposable — once the PRD issue exists, move it to `Deprecated/` so it cannot become a stale
   competing source.

2. **PRD** — Synthesize the locked decisions into a **self-contained** PRD with `/to-prd` and
   publish it as a GitHub issue labelled `ready-for-agent`. An agent must be able to break it
   into tasks by reading the PRD issue only.

3. **Issues** — Slice the PRD into independently-grabbable vertical slices with `/to-issues`.
   One feature per slice; do not split into backend-only and frontend-only layers. Reuse
   existing open issues instead of creating duplicates.

4. **Build** — One slice = one branch = one PR, cut from an up-to-date `main`; a human merges on
   GitHub. See `git-workflow.md`, `issue-tracker.md`, `triage-labels.md`.

5. **Close** — Append the Milestone's locked decisions to `DECISIONS.md` (one line each, newest
   milestone on top), and move any decisions they supersede to its Historical section. Write an
   ADR under `docs/adr/` or `backend/docs/adr/` for each architecturally significant decision
   (the trade-offs that a one-liner can't hold), and link it from the `DECISIONS.md` entry. Then
   close the PRD issue and its slice issues. A Milestone is done only when its decisions are
   captured in `DECISIONS.md`, not just in a closed issue.

## Decisions

`DECISIONS.md` at the repo root is the single index of load-bearing decisions — read it before
starting a Milestone and update it at Close. Everything else about how decisions are recorded
lives there, not in this file.
