# PRD — Recall Map, Milestone 1: Core Loop

**Status:** Draft
**Source:** `Plan_v1.md` (Recall Map — Plan v1)
**Milestone:** M1 — Core loop
**Author:** Generated from Plan_v1.md
**Date:** 2026-07-12

---

## 1. Summary

Milestone 1 delivers the end-to-end learning loop that is the heart of Recall Map: a
self-directed learner sets a Goal, creates a Topic, pastes text, and the system extracts
Concepts, lets the user confirm them, schedules the core ones for review, then runs the
two review modes with AI grading and simple spaced-repetition scheduling. A read-only
mini Concept Map on the Topic page rounds out the milestone.

M1 is the smallest slice that proves the product's core claim: *pasted material →
active recall → review-when-due actually works.*

## 2. Goal & Non-Goals

### Goal
Turn one pasted text Material into confirmed Concepts, testable Questions, and a working
review loop with AI grading and scheduling — for a single self-directed learner.

### Non-Goals (explicitly out of M1)
- Global home dashboards, mastery squares, 5-day plan, recent list (→ M2).
- Grading depth: point-by-point source comparison, richer misconception detection (→ M3).
- Concept merging across Materials; multi-Material Concept Maps (→ M3).
- RAG / pgvector, Markdown/PDF/other file types, email reminders, numeric mastery scores,
  forgetting-curve hour-level schedule, background jobs, Supabase Storage (all Deferred).

## 3. Users & Context

**Primary user:** a self-directed learner who has learned something but has no reliable
way to recall, test, and reconnect it later.

Recall Map is **not** a general notes app, a chatbot over documents, or a file storage app.

## 4. Canonical Terms (use verbatim in code, DB, UI, docs)

| Term | Meaning |
|---|---|
| Goal | The user's learning goal. Set once, editable. Guides Concept importance. |
| Topic | A broad subject. Groups Materials and Concepts. Has its own page and Concept Map. |
| Material | One original source (pasted text in V1) inside a Topic. |
| Concept | One idea extracted from a Material. Carries its source snippet. |
| Question | One way to test a Concept (flashcard or written explanation). |
| Review | One review attempt: user answer + AI verdict + feedback + timestamp. |
| Concept Map | Visual graph of Concepts and their relationships inside a Topic. |

No aliases (do not use "collection", "mind map", "big concept").

## 5. Functional Requirements

### 5.1 Goal
- **FR-1** User can set a Goal (once) and edit it later.
- **FR-2** The Goal is passed to extraction to mark Concept importance.

### 5.2 Topic & Material
- **FR-3** User can create a Topic.
- **FR-4** User can paste a text Material into a Topic. Pasted text only.
- **FR-5** Enforce a clear size limit on pasted text (limit surfaced in the UI before submit).
- **FR-6** Material text is stored in a Postgres text column (no Supabase Storage).

### 5.3 Extraction
- **FR-7** AI **extracts** (not summarizes) structured Concepts, Questions, relationships,
  and source snippets via Structured Outputs (Pydantic models).
- **FR-8** Using the user's Goal, the LLM marks each Concept as one of:
  *irrelevant to goal / supporting / core.*
- **FR-9** Each Concept stores its source snippet from the Material.
- **FR-10** AI confidence is saved per Concept; model output is never trusted blindly.
- **FR-11** Extraction runs in-request (no job queue); FastAPI streams progress back over
  the HTTP response.

### 5.4 Confirmation Screen
- **FR-12** After extraction the user sees a confirmation screen listing extracted Concepts.
- **FR-13** User can approve / edit / delete each Concept.
- **FR-14** User can toggle which Concepts enter the review schedule; **core** Concepts are
  pre-checked.
- **FR-15** Confirmed **core** Concepts enter the review schedule. **Supporting** Concepts
  remain browsable in the Topic but are never due.

### 5.5 Review Loop (two modes)
- **FR-16** User picks one of two review modes: **flashcard** or **written explanation**
  (Feynman-style).
- **FR-17** Review is a flow page (not a dashboard): question → user types answer →
  AI verdict + feedback → optional override → next question.
- **FR-18** Grading uses **zero RAG**. The grading prompt contains only: the Concept
  explanation + its stored source snippet + the user's answer.
- **FR-19** AI returns a four-tier verdict: **fail / partial / pass / strong**, plus
  feedback: correct points, missing points, misconception warnings, and next review date.
- **FR-20** User can override the verdict with one click; the **final** verdict drives scheduling.
- **FR-21** Every Review attempt (user answer, AI verdict, feedback, timestamp) is stored.

### 5.6 Scheduling
- **FR-22** Spaced repetition uses simple performance rules only:
  - fail → due again today
  - partial → tomorrow
  - pass → 3 days
  - strong → 7 days
- **FR-23** Mastery is shown as three states only: **weak / learning / strong**
  (no numeric percentages).

### 5.7 Topic Page — mini Concept Map
- **FR-24** Topic page shows a **read-only** mini Concept Map (React Flow, auto-layout):
  nodes + relationship edges. Even a single node satisfies M1.
- **FR-25** Clicking a node opens that Concept's detail. No dragging/editing in V1.

### 5.8 Concept detail
- **FR-26** Concept detail page shows: name, one-line explanation, analogy, mastery state,
  due state, source link, relationships, questions, and review history.
- **FR-27** Concept detail is reachable by clicking a Concept anywhere it appears
  (flashcard, map, lists).

### 5.9 Reminders / due surface (M1 scope)
- **FR-28** V1 provides an in-app due list only. No email, no browser notifications.

### 5.10 Privacy (applies from M1)
- **FR-29** User materials are private; used only to generate that user's study artifacts,
  never as public examples.
- **FR-30** A short AI-mistake warning is shown in the UI; incorrect Concepts are editable.
- **FR-31** User can delete Materials and generated study artifacts.

## 6. UX Notes / Avoid
- Review is a focused flow page, not a dashboard.
- Avoid long AI summaries, walls of text, and too many metrics.

## 7. Technical Architecture (constraints for M1)

- **Split stack:** Next.js thin frontend + FastAPI backend. Frontend holds no business
  logic (no extraction, grading, or scheduling). It renders UI and calls FastAPI over
  HTTP (JSON).
- **FastAPI owns** extraction, grading, scheduling, and all DB reads/writes. Request/response
  shapes are Pydantic models — the single source of truth for the API contract.
- **Structured extraction** uses Pydantic models + `instructor` (or OpenAI/Anthropic SDKs
  directly). Prompts live in code (Python files, versioned in git).
- **Supabase Postgres** with Row Level Security on all user data, accessed from FastAPI.
  Relationships stored as plain rows (no graph database).
- **No background job queue** in V1; extraction runs in-request with streamed progress.
- **No embeddings / pgvector** in V1.
- Duplicate Concepts across Materials are allowed in V1 (merging is M3).
- Contract sync (Pydantic ↔ TypeScript) is manual in V1; no codegen.

## 8. Acceptance Criteria (M1 "done")

A single user can, end to end:
1. Set a Goal and edit it.
2. Create a Topic and paste a text Material (within the size limit).
3. Trigger extraction and see streamed progress, then a confirmation screen of Concepts
   marked irrelevant / supporting / core with source snippets and saved AI confidence.
4. Approve / edit / delete Concepts and toggle which enter the schedule (core pre-checked);
   confirmed core Concepts become schedulable, supporting Concepts never become due.
5. Run both review modes (flashcard and written explanation) and receive a four-tier
   verdict + feedback, with one-click override.
6. Have every Review attempt stored, and the next-due date set by the simple scheduling
   rules based on the final verdict.
7. See mastery as weak / learning / strong (no percentages).
8. View a read-only mini Concept Map on the Topic page (≥1 node) and click through to a
   Concept detail page showing name, explanation, analogy, mastery, due state, source link,
   relationships, questions, and review history.
9. Delete a Material and its generated study artifacts.

## 9. Open Questions
- Exact pasted-text size limit (character/token count) to enforce in FR-5.
- Copy/threshold rules mapping verdict history → weak / learning / strong states (FR-23).
- Minimum relationship coverage required from extraction to render a useful mini map (FR-24).
