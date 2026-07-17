# Recall Map Grill Questions v1 — Resolved

All questions below are decided (interview completed 2026-07-11). [Plan_v1.md](Plan_v1.md) is the single source of truth for the full design; this file records each question's final answer and, where relevant, why.

> **⚠️ Post-M1 redesign (2026-07-17):** a large architecture change supersedes several answers below — dashboard input + Concept-level auto-routing, Goal moved down to per-Topic, and the Concept Map changed from a relationship graph to a hierarchy tree. Superseded answers are flagged inline. See [Wayfinder map #44](https://github.com/Alexin12/AI-Recall-Map/issues/44), [User_read/Changes_before_M2.md](User_read/Changes_before_M2.md), and ADRs [0002 product identity](docs/adr/0002-active-recall-gym-not-knowledge-organizer.md), [0005 routing](backend/docs/adr/0005-dashboard-input-concept-level-routing.md), [0006 goal-per-Topic](backend/docs/adr/0006-goal-per-topic-two-phase-relevance.md), [0007 concept tree](backend/docs/adr/0007-concept-map-as-hierarchy-tree.md).

Canonical terms (defined in Plan_v1.md): Goal, Topic, Material, Concept, Question, Review, Concept Map.

## Product Definition

### 1. Who is the first user?
A self-directed learner (online courses, articles, transcripts) who forgets material later, whether or not they already use AI while learning.

### 2. What is the main pain?
Not "I need summaries" — "I learned something, but I have no reliable way to recall, test, and reconnect it later."

### 3. What promise should Recall Map make?
It turns learning material into active recall questions, concept explanations, and concept relationships, then brings them back when review is due.

### 4. What should the product not become?
A general notes app, a chatbot over documents, or a file storage app.

### 5. What does "review" mean in this app?
The learner retrieves knowledge from memory (flashcard or written explanation, Feynman-style), the LLM judges the answer, and the learner iterates. Review is triggered either by the user picking a Concept manually or by the app's due schedule. Scheduling follows Q22 performance rules only; the hour-level forgetting-curve schedule (1h/9h/...) is deferred until push or email reminders exist — with only an in-app due list, users won't return within an hour.

### 6. What does "understanding" mean in this app?
The learner can recognize the concept (flashcard), explain it in their own words with key points and no major misconceptions (written explanation), and connect it to related concepts.

### 7. What does "concept map" mean?
A visual graph of Concepts and relationship edges inside a Topic, used for navigation: click a node to open that Concept's detail page. Not decoration.
> **Superseded (ADR-0007):** the Concept Map is now a **hierarchy tree** (big Concept expands into sub-Concepts), not a relationship-edge graph. Navigation-by-click and gap-finding remain; user-drawn edges are dropped.

### 8. What is the first successful session?
Add one Material → get useful Concepts and Questions → answer by typing → review at least one Concept and see what is due next → see a basic read-only map (one node counts).

## Scope

### 9. What should V1 input support?
Pasted text only. Markdown and PDF next. Word, Google Docs, Excel, and images wait.

### 10. Should PDF be in the first build?
No. Only after pasted text and Markdown work.

### 11. Should Google Docs be in V1?
No — auth, permissions, import edge cases, privacy concerns.

### 12. Should image OCR be in V1?
No — accuracy problems before the review loop is proven.

### 13. Should Excel be in V1?
No — structured data, not learning text; a separate later importer.

### 14. Should reminders be email, in-app, or browser notifications?
In-app due list in V1. Email later. No browser notifications.

### 15. Should users edit AI-generated concepts?
Yes: approve, edit, or delete on the post-extraction confirmation screen.

### 16. Should every concept become a review item?
No. The user sets a Goal (e.g. "become an AI engineer within a year"). The LLM uses the Goal to mark each Concept irrelevant / supporting / core. On the confirmation screen, core Concepts are pre-checked for scheduling; the user can toggle, edit, or delete. Confirmed core Concepts enter the schedule; supporting ones stay browsable but never due.
> **Superseded (ADR-0006):** Goal is now **per-Topic**, not global. Relevance is scored in a second phase (only for Topics with a Goal) and **auto-applied** after confirm — the pre-check/toggle no longer lives on the confirmation screen; the user overrides on the **Topic page** via a per-Concept relevance column. A Topic with no Goal schedules nothing and leaves `goal_relevance` null.

## Learning System

### 17. What review modes should V1 include?
Flashcard and written explanation, user picks. Both ship in milestone 1 with basic AI grading — grading is the product's differentiation, so it cannot wait for milestone 3.

### 18. Should AI decide if the learner passes?
Yes, as guidance: the AI shows a four-tier verdict (fail / partial / pass / strong) with feedback, and the user can override it with one click. Scheduling uses the final verdict.

### 19. What should AI feedback include?
Verdict, correct points, missing points, misconception warnings, and next review date.

### 20. What should the learner see after failing?
What was missing, a short source-based explanation, and the Concept stays due soon.

### 21. What should the learner see after passing?
Brief confirmation; the Concept moves to a later review date.

### 22. How complex should spaced repetition be first?
Simple performance rules only: fail = today again, partial = tomorrow, pass = 3 days, strong = 7 days.

### 23. Should the app show mastery score?
Yes, three states only: weak / learning / strong. No fake percentages in V1; per-concept numeric scores are a V2+ idea.

## AI Behavior

### 24. Should the AI summarize or extract?
Extract: structured Concepts, Questions, relationships, and source snippets.

### 25. Should extraction use Structured Outputs?
Yes — AI SDK `generateObject` returning a schema the app saves. Schema fields are defined in Plan_v1.md's glossary and data decisions.

### 26. Should the app use RAG in V1?
No. Grading needs no retrieval: each Concept stores its source snippet, and the grading prompt contains concept explanation + source snippet + user answer.

### 27. When is RAG actually needed?
When the app must search across many saved Materials. Not for V1 grading.

### 28. Should the app use OpenAI File Search or Supabase pgvector?
pgvector, when retrieval is needed at all. The earlier "File Search because grading needs speed" reasoning was wrong: retrieval adds a round trip and latency. pgvector also keeps all user data in Supabase, matching the privacy promise.

### 29. Should prompts be stored in code or database?
In code: TypeScript constants, versioned by git. A prompts table plus admin UI only pays off when non-engineers tune prompts frequently.

### 30. Should model output be trusted automatically?
No. Save AI confidence; the user confirms and can edit generated Concepts.

## Data And Domain Model

### 31. Material vs concept?
Material is the original source; Concept is an idea extracted from it.

### 32. Concept vs question?
A Concept is what to understand; a Question is one way to test it.

### 33. Collection vs material?
"Collection" is retired. Topic is the canonical grouping (it also replaces "big concept"); a Material is one source inside a Topic.

### 34. What should be the canonical domain terms?
Goal, Topic, Material, Concept, Question, Review, Concept Map — used identically in code, database, UI, and docs.

### 35. "Mind Map" or "Concept Map"?
Concept Map.
> **Note (ADR-0007):** the name "Concept Map" is kept, but its structure is now a hierarchy tree rather than a relationship-edge graph.

### 36. Should a concept belong to one material or many?
Created from one Material; merging across Materials comes in milestone 3.

### 37. Should duplicate concepts be allowed?
Allowed in V1 (different Materials cover the same concept from different angles). Milestone 3 merges them into one Concept combining both sources.

### 38. Should original material be stored forever?
Stored by default, user can delete.

### 39. Should the app store learner answers?
Yes — needed for review history and progress.

### 40. Should the app store AI feedback?
Yes — stored with each Review attempt.

## UI And Experience

### 41. What is the first screen after sign-in?
The global home: today's due queue, mastery squares (red = failed last time, blue = normal pass, green = strong pass), next-5-days review plan, recently learned list, and Topic list.
> **Superseded (ADR-0005):** the Global Home is now also the **single input point** — the user pastes new Material here, and its Concepts are auto-routed to Topics. The per-Topic paste path is removed.

### 42. What should the dashboard prioritize?
Due queue first, then recently learned Concepts, then Topics.

### 43. Should the app show time tabs like yesterday and last week?
Not in V1. The recently learned list covers most of that need; full time-tab views (with per-period maps) are V2.

### 44. What should a concept card show?
Name, one-line explanation, analogy, mastery state, due state, source link.

### 45. What happens when the user clicks a concept?
From anywhere (home, flashcard, map), it opens the Concept detail page: explanation, analogy, source, relationships, questions, review history.

### 46. Should the concept map be on the dashboard?
Not on the global home. Each Topic page holds its own Concept Map, reached from the Topic list.

### 47. What should the app avoid showing?
Long AI summaries, walls of text, too many metrics.

## Technical Architecture

**Revised 2026-07-11.** The original answers below (single Next.js app, Server Actions, AI SDK v6) assumed the developer could read and maintain TypeScript. A follow-up discussion surfaced a hard constraint: the developer reads and writes Python only, has never deployed anything, and relies on the coding agent to locate bugs rather than reading stack traces themselves. That changes the calculus — see updated answers.

### 48. One Next.js app or separate frontend/backend?
Separate: Next.js as a thin frontend, FastAPI as the backend holding all business logic. Reasoning: if the core logic (extraction, grading, scheduling) were written in TypeScript, the developer could never independently verify it — only confirm the agent's described behavior. Writing it in FastAPI means the developer can actually read, debug, and own the product's core logic. The traded-off cost — two deployments, two sets of env vars, two log dashboards, manual API contract sync — was weighed explicitly against this and accepted, because the developer has never deployed anything before either way, so there's no "simple baseline" being given up; see Plan_v1.md's Deployment section for how each cost is minimized (one-click deploys, dashboard-entered keys, accepted manual sync at V1 scale).

A pure-Python single-deployment alternative (FastAPI + a Python UI framework like Streamlit/Reflex, no Next.js at all) was considered and rejected: it would have solved the deployment-complexity problem too, but makes the interactive, click-to-navigate Concept Map (Q7, Q46) — a stated V1 differentiator — meaningfully harder to build well.

### 49. Server Actions or Route Handlers?
Moot — no longer applicable. Next.js has no business logic to expose via Server Actions; it calls FastAPI endpoints over HTTP for everything.

### 50. Background jobs immediately?
No. Extraction runs in-request inside FastAPI, streamed back over the HTTP response; pasted text is small (Q56). Add a queue only when PDF/large files arrive.

### 51. Supabase Row Level Security?
Yes, on all user data, enforced at the database layer regardless of which service (FastAPI) connects to it.

### 52. Graph database?
No. Relationships are plain Postgres rows.

### 53. AI SDK v6?
No — that was TypeScript-specific and is dropped with the architecture change. FastAPI uses Pydantic models + the `instructor` library (or the OpenAI/Anthropic SDKs directly) for structured extraction — the Python equivalent of `generateObject`, with the same benefit: the model's output is forced into a schema the app can save.

### 54. Embeddings immediately?
No. Only when cross-material search is needed (then pgvector, per Q28).

### 55. Uploaded files into Supabase Storage?
Not in V1 — pasted text goes in a Postgres text column. Storage is for real files (PDF, images) later.

### 56. Large files allowed?
No. Small pasted text with a clear size limit.

## Privacy And Trust

### 57. What privacy promise should V1 make?
User materials are private to the user and used only to generate their study artifacts.

### 58. Should users be warned about AI mistakes?
Yes, briefly, and incorrect Concepts are editable.

### 59. Should user material be used for public examples?
No.

### 60. Should the app support deleting all user data?
V1: delete Materials and generated study artifacts. Full account deletion later.

## MVP Decision

> **Superseded — milestones renumbered (2026-07-17, Wayfinder map #44):** M1 (core loop) is done. The post-M1 redesign becomes the **new M2** (re-foundation, 3 slices: Goal→Topic; Home input + Concept-level auto-routing + inbox; Concept Map → hierarchy tree). The old M2 (dashboards) → **M3**; the old M3 (grading depth + Concept merging) → **M4**; interleaving and the "memory tree" gamification land in M4/later. Q62–Q66 below describe the *old* numbering.

### 61. Which plan should be built first?
The rewritten Plan_v1.md, milestone 1 first.

### 62. What is the first milestone?
Core loop: Goal + Topic + pasted Material in → Concepts and Questions out → confirmation → both review modes with basic grading → Review saved → read-only mini map.

### 63. What is the second milestone?
Dashboards: global home (due queue, mastery squares, 5-day plan) and Topic page mastery overview.

### 64. What is the third milestone?
Grading depth (point-by-point source comparison, better misconception detection) and Concept merging across Materials with a fuller map.

### 65. What should be delayed until after real usage?
RAG/pgvector, all file types, email reminders, time tabs, mobile, collaboration, sharing, payments, advanced analytics.

### 66. UI design
Two layers, not three dashboards per topic: global home → Topic page (mastery overview + read-only Concept Map). Review/testing is a flow page, not a dashboard. Full layout in Plan_v1.md.
